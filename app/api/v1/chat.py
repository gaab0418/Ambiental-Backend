from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List
import asyncio
from app.database import get_db
from app.models.user import User
from app.models.chat_thread import ChatThread
from app.models.chat_message import ChatMessage, MessageRole
from app.schemas.chat import (
    ChatThreadCreate, ChatThreadResponse,
    ChatMessageCreate, ChatMessageResponse, ChatMessagesResponse
)
from app.dependencies.auth import get_current_active_user
from app.utils.audit_logger import AuditLogger

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
    
    return threads


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
    
    # Create thread
    thread = ChatThread(
        user_id=current_user.id,
        organization_id=current_user.organization_id,
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
        organization_id=current_user.organization_id,
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
    """Send a message to a chat thread and get AI response."""
    
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
        organization_id=current_user.organization_id,
        changes={"role": "USER", "thread_id": thread_id}
    )
    
    # Simulate AI processing with 500ms delay
    await asyncio.sleep(0.5)
    
    # Create assistant response (placeholder for actual AI API)
    assistant_message = ChatMessage(
        thread_id=thread_id,
        role=MessageRole.ASSISTANT,
        content="callback da api"
    )
    
    db.add(assistant_message)
    db.commit()
    db.refresh(assistant_message)
    
    # Log audit
    AuditLogger.log_create(
        db=db,
        entity_type="ChatMessage",
        entity_id=assistant_message.id,
        user_id=current_user.id,
        organization_id=current_user.organization_id,
        changes={"role": "ASSISTANT", "thread_id": thread_id}
    )
    
    # Update thread updated_at
    from datetime import datetime
    thread.updated_at = datetime.utcnow()
    db.commit()
    
    return [user_message, assistant_message]


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
    
    # Log audit
    AuditLogger.log_delete(
        db=db,
        entity_type="ChatThread",
        entity_id=thread.id,
        user_id=current_user.id,
        organization_id=current_user.organization_id,
        changes={"title": thread.title}
    )
    
    return {"message": "Chat thread deleted successfully"}


