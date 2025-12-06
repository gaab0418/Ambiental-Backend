from fastapi import APIRouter, Depends, HTTPException, Query, status, Request, Header
from sqlalchemy.orm import Session
from typing import List, Optional
import asyncio
import httpx
import logging
from datetime import datetime, timezone

from app.database import get_db
from app.models.user import User
from app.models.chat_thread import ChatThread
from app.models.chat_message import ChatMessage, MessageRole
from app.models.chat_file import ChatFile
from app.models.chat_timeline_event import ChatTimelineEvent, TimelineEventType, TimelineEventStatus
from app.schemas.chat import (
    ChatThreadCreate, ChatThreadResponse,
    ChatMessageCreate, ChatMessageResponse, ChatMessagesResponse,
    N8NCallbackMessage
)
from app.dependencies.auth import get_current_active_user
from app.models.user_organization_association import UserOrganizationAssociation
from app.utils.audit_logger import AuditLogger
from app.utils.n8n_client import n8n_client, verify_n8n_callback_signature, N8NClientError
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/threads", response_model=List[ChatThreadResponse])
async def get_chat_threads(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all chat threads for the current user."""
    threads = db.query(ChatThread).filter(
        ChatThread.user_id == current_user.id,
        ChatThread.is_active == True
    ).order_by(ChatThread.updated_at.desc()).all()
    
    # Enrich with aggregated data
    result = []
    for thread in threads:
        thread_dict = {
            "id": thread.id,
            "user_id": thread.user_id,
            "organization_id": thread.organization_id,
            "title": thread.title,
            "is_active": thread.is_active,
            "created_at": thread.created_at,
            "updated_at": thread.updated_at,
            "files_count": db.query(ChatFile).filter(
                ChatFile.thread_id == thread.id,
                ChatFile.is_active == True
            ).count(),
            "has_timeline": db.query(ChatTimelineEvent).filter(
                ChatTimelineEvent.thread_id == thread.id
            ).count() > 0
        }
        result.append(thread_dict)
    
    return result


@router.post("/threads", response_model=ChatThreadResponse)
async def create_chat_thread(
    thread_data: ChatThreadCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new chat thread."""
    
    # Validate title length if provided
    if thread_data.title and len(thread_data.title) > 120:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Title must be 120 characters or less"
        )
    
    # Get user's current organization
    user_assoc = db.query(UserOrganizationAssociation).filter(
        UserOrganizationAssociation.user_id == current_user.id
    ).first()
    
    if not user_assoc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not associated with any organization"
        )
    
    # Create thread
    thread = ChatThread(
        user_id=current_user.id,
        organization_id=user_assoc.organization_id,
        title=thread_data.title or "New Chat",
        is_active=True
    )
    
    db.add(thread)
    db.commit()
    db.refresh(thread)
    
    # Log audit
    AuditLogger.log_create(
        db=db,
        entity_type="ChatThread",
        entity_id=thread.id,
        user_id=current_user.id,
        organization_id=user_assoc.organization_id,
        changes={"title": thread.title}
    )
    
    return thread


@router.get("/threads/{thread_id}/messages", response_model=ChatMessagesResponse)
async def get_chat_messages(
    thread_id: int,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get messages from a chat thread."""
    
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
    
    # Get total count
    total = db.query(ChatMessage).filter(ChatMessage.thread_id == thread_id).count()
    
    # Get paginated messages
    messages = db.query(ChatMessage).filter(
        ChatMessage.thread_id == thread_id
    ).order_by(ChatMessage.created_at.asc()).offset(offset).limit(limit).all()
    
    return {
        "messages": messages,
        "total": total,
        "limit": limit,
        "offset": offset
    }


@router.post("/threads/{thread_id}/messages", response_model=List[ChatMessageResponse])
async def send_chat_message(
    thread_id: int,
    message_data: ChatMessageCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Send a message to a chat thread and trigger AI processing via N8N."""
    
    # Validate message content
    if not message_data.content.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message content cannot be empty"
        )
    
    if len(message_data.content) > 4000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message content must be 4000 characters or less"
        )
    
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
    
    # Get user's organization
    user_assoc = db.query(UserOrganizationAssociation).filter(
        UserOrganizationAssociation.user_id == current_user.id
    ).first()
    
    if not user_assoc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not associated with any organization"
        )
    
    # Create user message
    user_message = ChatMessage(
        thread_id=thread_id,
        role=MessageRole.USER,
        content=message_data.content.strip()
    )
    
    db.add(user_message)
    db.commit()
    db.refresh(user_message)
    
    # Log audit
    AuditLogger.log_create(
        db=db,
        entity_type="ChatMessage",
        entity_id=user_message.id,
        user_id=current_user.id,
        organization_id=user_assoc.organization_id,
        changes={"role": "USER", "thread_id": thread_id}
    )
    
    # Get chat files for context
    chat_files = db.query(ChatFile).filter(
        ChatFile.thread_id == thread_id,
        ChatFile.is_active == True
    ).all()
    
    # Create timeline event for AI processing
    timeline_event = ChatTimelineEvent(
        thread_id=thread_id,
        organization_id=user_assoc.organization_id,
        type=TimelineEventType.AI_PROCESSING,
        status=TimelineEventStatus.IN_PROGRESS,
        title="Processando mensagem",
        description="Enviando para o assistente virtual..."
    )
    db.add(timeline_event)
    db.commit()
    
    # Call N8N Webhook Synchronously
    try:
        # Prepare simple payload as requested
        payload = {
            "thread_id": thread_id,
            "message": message_data.content.strip()
        }
        
        # Make synchronous request to N8N
        # We use a new client here to ensure we don't have async issues if running in a sync context, 
        # but since this is an async path, we should use AsyncClient
        webhook_url = f"{settings.n8n_webhook_url.rstrip('/')}/chat"
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                webhook_url,
                json=payload
            )
            response.raise_for_status()
            response_data = response.json()
            
        # Extract output
        assistant_text = response_data.get("output", "")
        
        if not assistant_text:
            logger.warning(f"N8N response missing 'output' field: {response_data}")
            assistant_text = "Desculpe, não consegui processar sua resposta."

        # Create assistant message
        assistant_message = ChatMessage(
            thread_id=thread_id,
            role=MessageRole.ASSISTANT,
            content=assistant_text
        )
        
        db.add(assistant_message)
        db.commit()
        db.refresh(assistant_message)
        
        # Log audit for assistant message
        AuditLogger.log_create(
            db=db,
            entity_type="ChatMessage",
            entity_id=assistant_message.id,
            user_id=current_user.id,
            organization_id=user_assoc.organization_id,
            changes={"role": "ASSISTANT", "thread_id": thread_id, "source": "n8n_sync"}
        )
        
        # Update thread timestamp
        thread.updated_at = datetime.now(timezone.utc)
        db.commit()
        
        return [user_message, assistant_message]

    except Exception as e:
        logger.error(f"Failed to call N8N webhook: {str(e)}")
        
        # Return just the user message in case of error, or raise?
        # Let's raise an error to let the user know it failed
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Erro ao comunicar com o assistente: {str(e)}"
        )


@router.delete("/threads/{thread_id}")
async def delete_chat_thread(
    thread_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete (deactivate) a chat thread."""
    
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
    
    # Soft delete by marking as inactive
    thread.is_active = False
    db.commit()
    
    # Get user's organization for audit
    user_assoc = db.query(UserOrganizationAssociation).filter(
        UserOrganizationAssociation.user_id == current_user.id
    ).first()
    
    # Log audit
    AuditLogger.log_delete(
        db=db,
        entity_type="ChatThread",
        entity_id=thread.id,
        user_id=current_user.id,
        organization_id=user_assoc.organization_id if user_assoc else None,
        changes={"title": thread.title}
    )
    
    return {"message": "Chat thread deleted successfully"}


@router.post("/threads/{thread_id}/messages/callback")
async def n8n_message_callback(
    thread_id: int,
    request: Request,
    callback_data: N8NCallbackMessage,
    x_signature: str = Header(...),
    x_timestamp: str = Header(...),
    db: Session = Depends(get_db)
):
    """
    Callback endpoint for N8N to deliver AI-generated responses.
    Protected by HMAC signature verification.
    """
    # Read raw body for signature verification
    body = await request.body()
    payload_str = body.decode('utf-8')
    
    # Verify HMAC signature
    if not verify_n8n_callback_signature(payload_str, x_timestamp, x_signature):
        logger.warning(f"Invalid N8N callback signature for thread {thread_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid signature"
        )
    
    # Check if thread exists
    thread = db.query(ChatThread).filter(ChatThread.id == thread_id).first()
    
    if not thread:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat thread not found"
        )
    
    # Create assistant message
    assistant_message = ChatMessage(
        thread_id=thread_id,
        role=MessageRole.ASSISTANT,
        content=callback_data.assistant_message
    )
    
    db.add(assistant_message)
    db.commit()
    db.refresh(assistant_message)
    
    # Log audit
    AuditLogger.log_create(
        db=db,
        entity_type="ChatMessage",
        entity_id=assistant_message.id,
        user_id=thread.user_id,
        organization_id=thread.organization_id,
        changes={"role": "ASSISTANT", "thread_id": thread_id, "source": "n8n_callback"}
    )
    
    # Update or complete AI processing timeline event if it exists
    processing_event = db.query(ChatTimelineEvent).filter(
        ChatTimelineEvent.thread_id == thread_id,
        ChatTimelineEvent.type == TimelineEventType.AI_PROCESSING,
        ChatTimelineEvent.status == TimelineEventStatus.IN_PROGRESS
    ).order_by(ChatTimelineEvent.created_at.desc()).first()
    
    if processing_event:
        processing_event.status = TimelineEventStatus.COMPLETED
        processing_event.title = "Resposta da IA recebida"
        processing_event.description = "Processamento concluído com sucesso"
    
    # Create timeline events if provided
    if callback_data.timeline_events:
        for event_data in callback_data.timeline_events:
            timeline_event = ChatTimelineEvent(
                thread_id=thread_id,
                organization_id=thread.organization_id,
                type=TimelineEventType[event_data.type.upper()],
                status=TimelineEventStatus[event_data.status.upper()],
                title=event_data.title,
                description=event_data.description,
                order_index=event_data.order_index,
                event_metadata=event_data.metadata
            )
            db.add(timeline_event)
    
    # Update thread timestamp
    thread.updated_at = datetime.now(timezone.utc)
    
    db.commit()
    
    logger.info(f"N8N callback processed for thread {thread_id}")
    
    return {
        "status": "success",
        "message_id": assistant_message.id,
        "thread_id": thread_id
    }


