"""
Documents API - Environmental document management
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile, File, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, timezone
import os
import uuid
import io
import json
import hashlib

from app.database import get_db
from app.models.user import User
from app.models.document import Document, DocumentStatus
from app.schemas.documents import (
    DocumentCreate, DocumentUpdate, DocumentResponse,
    DocumentListResponse, DocumentStatusEnum
)
from app.dependencies.auth import get_current_active_user, get_organization_from_token
from app.utils.audit_logger import AuditLogger
from app.config import settings

router = APIRouter()

# Upload directory
DOCUMENTS_UPLOAD_DIR = os.path.join(os.getcwd(), "uploads", "documents")
os.makedirs(DOCUMENTS_UPLOAD_DIR, exist_ok=True)

MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB


def parse_tags(tags_str: Optional[str]) -> Optional[List[str]]:
    """Parse JSON tags string to list."""
    if not tags_str:
        return None
    try:
        return json.loads(tags_str)
    except:
        return None


def serialize_tags(tags: Optional[List[str]]) -> Optional[str]:
    """Serialize tags list to JSON string."""
    if not tags:
        return None
    return json.dumps(tags)


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    request: Request,
    search: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List documents with filters."""
    org_id = get_organization_from_token(request)
    
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization context required"
        )
    
    query = db.query(Document).filter(Document.organization_id == org_id)
    
    # Apply filters
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            Document.name.ilike(search_pattern) |
            Document.category.ilike(search_pattern)
        )
    
    if category:
        query = query.filter(Document.category == category)
    
    if status:
        try:
            status_enum = DocumentStatus(status)
            query = query.filter(Document.status == status_enum)
        except ValueError:
            pass
    
    # Get total count
    total = query.count()
    
    # Get paginated results
    documents = query.order_by(Document.created_at.desc()).offset(offset).limit(limit).all()
    
    # Build response with download URLs
    items = []
    for doc in documents:
        doc_response = DocumentResponse(
            id=doc.id,
            name=doc.name,
            category=doc.category,
            status=DocumentStatusEnum(doc.status.value),
            size_bytes=doc.size_bytes,
            uploaded_at=doc.created_at,
            owner_name=doc.owner_name,
            tags=parse_tags(doc.tags),
            download_url=f"/api/documents/{doc.id}/content",
            expires_at=doc.expires_at
        )
        items.append(doc_response)
    
    return DocumentListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset
    )


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    name: Optional[str] = None,
    category: str = "GERAL",
    owner_name: Optional[str] = None,
    tags: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Upload a new document."""
    org_id = get_organization_from_token(request)
    
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization context required"
        )
    
    # Read file content
    content = await file.read()
    
    # Check file size
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File exceeds maximum size of {MAX_FILE_SIZE / 1024 / 1024} MB"
        )
    
    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is empty"
        )
    
    # Generate unique filename
    file_ext = os.path.splitext(file.filename)[1] if file.filename else ""
    stored_filename = f"{uuid.uuid4()}{file_ext}"
    
    # Create org-specific directory
    org_upload_dir = os.path.join(DOCUMENTS_UPLOAD_DIR, str(org_id))
    os.makedirs(org_upload_dir, exist_ok=True)
    
    storage_path = os.path.join(org_upload_dir, stored_filename)
    
    # Calculate checksum
    checksum = hashlib.sha256(content).hexdigest()
    
    # Save file
    with open(storage_path, "wb") as f:
        f.write(content)
    
    # Parse tags if provided
    tags_list = None
    if tags:
        try:
            tags_list = json.loads(tags)
        except:
            tags_list = [t.strip() for t in tags.split(",") if t.strip()]
    
    # Create document record
    document = Document(
        organization_id=org_id,
        name=name or file.filename or "Untitled",
        category=category,
        status=DocumentStatus.PENDENTE,
        original_filename=file.filename or "unknown",
        stored_filename=stored_filename,
        storage_path=storage_path,
        mime_type=file.content_type or "application/octet-stream",
        size_bytes=len(content),
        checksum=checksum,
        tags=serialize_tags(tags_list),
        owner_name=owner_name,
        uploaded_by_user_id=current_user.id
    )
    
    db.add(document)
    db.commit()
    db.refresh(document)
    
    # Log audit
    AuditLogger.log_create(
        db=db,
        entity_type="Document",
        entity_id=document.id,
        user_id=current_user.id,
        organization_id=org_id,
        changes={"name": document.name, "category": document.category, "size": document.size_bytes}
    )
    
    return DocumentResponse(
        id=document.id,
        name=document.name,
        category=document.category,
        status=DocumentStatusEnum(document.status.value),
        size_bytes=document.size_bytes,
        uploaded_at=document.created_at,
        owner_name=document.owner_name,
        tags=parse_tags(document.tags),
        download_url=f"/api/documents/{document.id}/content",
        expires_at=document.expires_at
    )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    request: Request,
    document_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get a specific document."""
    org_id = get_organization_from_token(request)
    
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.organization_id == org_id
    ).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    return DocumentResponse(
        id=document.id,
        name=document.name,
        category=document.category,
        status=DocumentStatusEnum(document.status.value),
        size_bytes=document.size_bytes,
        uploaded_at=document.created_at,
        owner_name=document.owner_name,
        tags=parse_tags(document.tags),
        download_url=f"/api/documents/{document.id}/content",
        expires_at=document.expires_at
    )


@router.get("/{document_id}/content")
async def download_document(
    request: Request,
    document_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Download a document."""
    org_id = get_organization_from_token(request)
    
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.organization_id == org_id
    ).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Check if file exists
    if not os.path.exists(document.storage_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document file not found"
        )
    
    # Read file
    with open(document.storage_path, "rb") as f:
        file_content = f.read()
    
    # Log audit
    AuditLogger.log_read(
        db=db,
        entity_type="Document",
        entity_id=document.id,
        user_id=current_user.id,
        organization_id=org_id,
        changes={"action": "download"}
    )
    
    return StreamingResponse(
        io.BytesIO(file_content),
        media_type=document.mime_type,
        headers={
            "Content-Disposition": f'attachment; filename="{document.original_filename}"'
        }
    )


@router.put("/{document_id}", response_model=DocumentResponse)
async def update_document(
    request: Request,
    document_id: int,
    document_data: DocumentUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update a document's metadata."""
    org_id = get_organization_from_token(request)
    
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.organization_id == org_id
    ).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Update fields
    update_data = document_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "status" and value:
            setattr(document, field, DocumentStatus(value.value))
        elif field == "tags":
            setattr(document, field, serialize_tags(value))
        else:
            setattr(document, field, value)
    
    document.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(document)
    
    # Log audit
    AuditLogger.log_update(
        db=db,
        entity_type="Document",
        entity_id=document.id,
        changes=update_data,
        user_id=current_user.id,
        organization_id=org_id
    )
    
    return DocumentResponse(
        id=document.id,
        name=document.name,
        category=document.category,
        status=DocumentStatusEnum(document.status.value),
        size_bytes=document.size_bytes,
        uploaded_at=document.created_at,
        owner_name=document.owner_name,
        tags=parse_tags(document.tags),
        download_url=f"/api/documents/{document.id}/content",
        expires_at=document.expires_at
    )


@router.delete("/{document_id}")
async def delete_document(
    request: Request,
    document_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete a document."""
    org_id = get_organization_from_token(request)
    
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.organization_id == org_id
    ).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    doc_name = document.name
    storage_path = document.storage_path
    
    # Log audit before deletion
    AuditLogger.log_delete(
        db=db,
        entity_type="Document",
        entity_id=document.id,
        user_id=current_user.id,
        organization_id=org_id,
        changes={"name": doc_name}
    )
    
    # Delete from database
    db.delete(document)
    db.commit()
    
    # Delete file from storage
    try:
        if os.path.exists(storage_path):
            os.remove(storage_path)
    except Exception:
        pass  # Log error but don't fail the request
    
    return {"message": f"Document '{doc_name}' deleted successfully"}



