from fastapi import APIRouter, Depends, HTTPException, status, Request, Header
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timezone
import logging

from app.database import get_db
from app.models.user import User
from app.models.chat_thread import ChatThread
from app.models.chat_timeline_event import ChatTimelineEvent, TimelineEventType, TimelineEventStatus
from app.schemas.chat import ChatTimelineEventCreate, ChatTimelineEventUpdate, ChatTimelineEventResponse
from app.dependencies.auth import get_current_active_user
from app.utils.n8n_client import verify_n8n_callback_signature
from app.utils.audit_logger import AuditLogger
from app.models.user_organization_association import UserOrganizationAssociation

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/threads/{thread_id}/timeline", response_model=List[ChatTimelineEventResponse])
async def get_thread_timeline(
    thread_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get timeline events for a chat thread.
    Public endpoint for users to view timeline.
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
    
    # Get all timeline events ordered by order_index and created_at
    events = db.query(ChatTimelineEvent).filter(
        ChatTimelineEvent.thread_id == thread_id
    ).order_by(
        ChatTimelineEvent.order_index.asc(),
        ChatTimelineEvent.created_at.asc()
    ).all()
    
    return events


@router.post("/threads/{thread_id}/timeline", response_model=ChatTimelineEventResponse)
async def create_timeline_event(
    thread_id: int,
    request: Request,
    event_data: ChatTimelineEventCreate,
    x_signature: str = Header(...),
    x_timestamp: str = Header(...),
    db: Session = Depends(get_db)
):
    """
    Create a new timeline event for a chat thread.
    Internal endpoint for N8N - protected by HMAC signature.
    """
    # Read raw body for signature verification
    body = await request.body()
    payload_str = body.decode('utf-8')
    
    # Verify HMAC signature
    if not verify_n8n_callback_signature(payload_str, x_timestamp, x_signature):
        logger.warning(f"Invalid N8N callback signature for timeline create on thread {thread_id}")
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
    
    # Validate event type and status
    try:
        event_type = TimelineEventType[event_data.type.upper()]
        event_status = TimelineEventStatus[event_data.status.upper()]
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid event type or status"
        )
    
    # Create timeline event
    timeline_event = ChatTimelineEvent(
        thread_id=thread_id,
        organization_id=thread.organization_id,
        type=event_type,
        status=event_status,
        title=event_data.title,
        description=event_data.description,
        order_index=event_data.order_index,
        event_metadata=event_data.metadata
    )
    
    db.add(timeline_event)
    db.commit()
    db.refresh(timeline_event)
    
    # Log audit
    AuditLogger.log_create(
        db=db,
        entity_type="ChatTimelineEvent",
        entity_id=timeline_event.id,
        user_id=thread.user_id,
        organization_id=thread.organization_id,
        changes={
            "type": event_data.type,
            "status": event_data.status,
            "title": event_data.title,
            "source": "n8n"
        }
    )
    
    # Update thread timestamp
    from datetime import datetime
    thread.updated_at = datetime.now(timezone.utc)
    db.commit()
    
    logger.info(f"Timeline event created by N8N for thread {thread_id}: {timeline_event.id}")
    
    return timeline_event


@router.patch("/threads/{thread_id}/timeline/{event_id}", response_model=ChatTimelineEventResponse)
async def update_timeline_event(
    thread_id: int,
    event_id: int,
    request: Request,
    event_update: ChatTimelineEventUpdate,
    x_signature: str = Header(...),
    x_timestamp: str = Header(...),
    db: Session = Depends(get_db)
):
    """
    Update an existing timeline event.
    Internal endpoint for N8N - protected by HMAC signature.
    """
    # Read raw body for signature verification
    body = await request.body()
    payload_str = body.decode('utf-8')
    
    # Verify HMAC signature
    if not verify_n8n_callback_signature(payload_str, x_timestamp, x_signature):
        logger.warning(f"Invalid N8N callback signature for timeline update on thread {thread_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid signature"
        )
    
    # Check if event exists and belongs to thread
    event = db.query(ChatTimelineEvent).filter(
        ChatTimelineEvent.id == event_id,
        ChatTimelineEvent.thread_id == thread_id
    ).first()
    
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Timeline event not found"
        )
    
    # Update fields if provided
    changes = {}
    
    if event_update.status is not None:
        try:
            event.status = TimelineEventStatus[event_update.status.upper()]
            changes["status"] = event_update.status
        except KeyError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid status value"
            )
    
    if event_update.title is not None:
        event.title = event_update.title
        changes["title"] = event_update.title
    
    if event_update.description is not None:
        event.description = event_update.description
        changes["description"] = event_update.description
    
    if event_update.order_index is not None:
        event.order_index = event_update.order_index
        changes["order_index"] = event_update.order_index
    
    if event_update.metadata is not None:
        event.event_metadata = event_update.metadata
        changes["metadata"] = event_update.metadata
    
    db.commit()
    db.refresh(event)
    
    # Log audit
    AuditLogger.log_update(
        db=db,
        entity_type="ChatTimelineEvent",
        entity_id=event.id,
        user_id=event.thread.user_id,
        organization_id=event.organization_id,
        changes={**changes, "source": "n8n"}
    )
    
    # Update thread timestamp
    event.thread.updated_at = datetime.now(timezone.utc)
    db.commit()
    
    logger.info(f"Timeline event updated by N8N for thread {thread_id}: {event_id}")
    
    return event


@router.get("/threads/{thread_id}/timeline/summary")
async def get_timeline_summary(
    thread_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get a summary of timeline events for a chat thread.
    Returns counts by status and type.
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
    
    # Get all events
    events = db.query(ChatTimelineEvent).filter(
        ChatTimelineEvent.thread_id == thread_id
    ).all()
    
    # Calculate summary
    total_events = len(events)
    
    status_counts = {}
    for status in TimelineEventStatus:
        status_counts[status.value] = sum(1 for e in events if e.status == status)
    
    type_counts = {}
    for event_type in TimelineEventType:
        type_counts[event_type.value] = sum(1 for e in events if e.type == event_type)
    
    # Get latest event
    latest_event = None
    if events:
        latest = max(events, key=lambda e: e.created_at)
        latest_event = {
            "id": latest.id,
            "type": latest.type.value,
            "status": latest.status.value,
            "title": latest.title,
            "created_at": latest.created_at.isoformat()
        }
    
    return {
        "thread_id": thread_id,
        "total_events": total_events,
        "status_counts": status_counts,
        "type_counts": type_counts,
        "latest_event": latest_event
    }

