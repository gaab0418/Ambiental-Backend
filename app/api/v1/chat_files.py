from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Header, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone
import io
import logging

from app.database import get_db
from app.models.user import User
from app.models.chat_thread import ChatThread
from app.models.chat_file import ChatFile
from app.schemas.chat import ChatFileResponse
from app.dependencies.auth import get_current_active_user
from app.models.user_organization_association import UserOrganizationAssociation
from app.utils.audit_logger import AuditLogger
from app.utils.secure_storage import secure_storage, StorageError
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


# File upload limits
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB
MAX_FILES_PER_THREAD = 50


@router.post("/threads/{thread_id}/files", response_model=List[ChatFileResponse])
async def upload_chat_files(
    thread_id: int,
    files: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Upload one or more files to a chat thread.
    Files are encrypted before storage.
    """
    # Check if thread exists and belongs to user
    thread = db.query(ChatThread).filter(
        ChatThread.id == thread_id,
        ChatThread.user_id == current_user.id,
        ChatThread.is_active == True
    ).first()
    
    if not thread:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat thread not found"
        )
    
    # Get user's organization
    user_assoc = db.query(UserOrganizationAssociation).filter(
        UserOrganizationAssociation.user_id == current_user.id
    ).first()
    
    if not user_assoc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not associated with any organization"
        )
    
    # Check current file count
    current_file_count = db.query(ChatFile).filter(
        ChatFile.thread_id == thread_id,
        ChatFile.is_active == True
    ).count()
    
    if current_file_count + len(files) > MAX_FILES_PER_THREAD:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum {MAX_FILES_PER_THREAD} files per thread allowed"
        )
    
    # Validate and upload files
    uploaded_files = []
    
    for file in files:
        # Read file content
        try:
            content = await file.read()
        except Exception as e:
            logger.error(f"Failed to read file {file.filename}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to read file: {file.filename}"
            )
        
        # Check file size
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File {file.filename} exceeds maximum size of {MAX_FILE_SIZE / 1024 / 1024} MB"
            )
        
        if len(content) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File {file.filename} is empty"
            )
        
        # Get MIME type
        mime_type = file.content_type or "application/octet-stream"
        
        # Store file with encryption
        try:
            storage_path, size_bytes, checksum, iv_b64, tag_b64 = secure_storage.store_file(
                org_id=user_assoc.organization_id,
                thread_id=thread_id,
                file_bytes=content,
                filename=file.filename,
                mime_type=mime_type
            )
        except StorageError as e:
            logger.error(f"Storage failed for file {file.filename}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to store file securely"
            )
        
        # Create database record
        chat_file = ChatFile(
            thread_id=thread_id,
            organization_id=user_assoc.organization_id,
            user_id=current_user.id,
            original_filename=file.filename,
            mime_type=mime_type,
            size_bytes=size_bytes,
            storage_path=storage_path,
            encryption_iv=iv_b64,
            encryption_tag=tag_b64,
            encryption_algo="AES-256-GCM",
            key_version="v1",
            checksum=checksum,
            is_active=True
        )
        
        db.add(chat_file)
        db.flush()  # Get the ID
        
        uploaded_files.append(chat_file)
        
        # Log audit
        AuditLogger.log_create(
            db=db,
            entity_type="ChatFile",
            entity_id=chat_file.id,
            user_id=current_user.id,
            organization_id=user_assoc.organization_id,
            changes={
                "filename": file.filename,
                "size": size_bytes,
                "thread_id": thread_id
            }
        )
    
    
    # Update thread timestamp
    thread.updated_at = datetime.now(timezone.utc)
    
    db.commit()
    
    # Refresh all uploaded files
    for file_obj in uploaded_files:
        db.refresh(file_obj)
    
    return uploaded_files


@router.get("/threads/{thread_id}/files", response_model=List[ChatFileResponse])
async def list_chat_files(
    thread_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    List all files in a chat thread.
    """
    # Check if thread exists and belongs to user
    thread = db.query(ChatThread).filter(
        ChatThread.id == thread_id,
        ChatThread.user_id == current_user.id
    ).first()
    
    if not thread:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat thread not found"
        )
    
    # Get all files for this thread
    files = db.query(ChatFile).filter(
        ChatFile.thread_id == thread_id,
        ChatFile.is_active == True
    ).order_by(ChatFile.created_at.desc()).all()
    
    return files


@router.get("/threads/{thread_id}/files/{file_id}/content")
async def download_chat_file(
    thread_id: int,
    file_id: int,
    current_user: User = Depends(get_current_active_user),
    x_internal_n8n_token: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """
    Download a file from a chat thread.
    Supports both user authentication and N8N internal token.
    """
    # Check if thread exists
    thread = db.query(ChatThread).filter(ChatThread.id == thread_id).first()
    
    if not thread:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat thread not found"
        )
    
    # Verify access: either user owns the thread or N8N internal token is valid
    if current_user:
        # User authentication - check ownership
        if thread.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this file"
            )
    elif x_internal_n8n_token:
        # N8N internal token authentication
        # For now, simple token check. In production, use more secure method
        if not settings.n8n_jwt_token or x_internal_n8n_token != settings.n8n_jwt_token:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid internal token"
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    # Get file record
    chat_file = db.query(ChatFile).filter(
        ChatFile.id == file_id,
        ChatFile.thread_id == thread_id,
        ChatFile.is_active == True
    ).first()
    
    if not chat_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    # Load and decrypt file
    try:
        file_bytes = secure_storage.load_file(
            storage_path=chat_file.storage_path,
            iv_b64=chat_file.encryption_iv,
            tag_b64=chat_file.encryption_tag,
            checksum=chat_file.checksum
        )
    except StorageError as e:
        logger.error(f"Failed to load file {file_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load file"
        )
    
    # Log audit if user is downloading (not N8N)
    if current_user:
        user_assoc = db.query(UserOrganizationAssociation).filter(
            UserOrganizationAssociation.user_id == current_user.id
        ).first()
        
        if user_assoc:
            AuditLogger.log_read(
                db=db,
                entity_type="ChatFile",
                entity_id=chat_file.id,
                user_id=current_user.id,
                organization_id=user_assoc.organization_id,
                changes={"action": "download"}
            )
    
    # Return file as streaming response
    return StreamingResponse(
        io.BytesIO(file_bytes),
        media_type=chat_file.mime_type,
        headers={
            "Content-Disposition": f'attachment; filename="{chat_file.original_filename}"'
        }
    )


@router.delete("/threads/{thread_id}/files/{file_id}")
async def delete_chat_file(
    thread_id: int,
    file_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Delete a file from a chat thread (soft delete).
    """
    # Check if thread exists and belongs to user
    thread = db.query(ChatThread).filter(
        ChatThread.id == thread_id,
        ChatThread.user_id == current_user.id
    ).first()
    
    if not thread:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat thread not found"
        )
    
    # Get file record
    chat_file = db.query(ChatFile).filter(
        ChatFile.id == file_id,
        ChatFile.thread_id == thread_id,
        ChatFile.is_active == True
    ).first()
    
    if not chat_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    # Soft delete
    chat_file.is_active = False
    
    # Get user's organization for audit
    user_assoc = db.query(UserOrganizationAssociation).filter(
        UserOrganizationAssociation.user_id == current_user.id
    ).first()
    
    # Log audit
    if user_assoc:
        AuditLogger.log_delete(
            db=db,
            entity_type="ChatFile",
            entity_id=chat_file.id,
            user_id=current_user.id,
            organization_id=user_assoc.organization_id,
            changes={"filename": chat_file.original_filename}
        )
    
    db.commit()
    
    return {"message": "File deleted successfully"}

