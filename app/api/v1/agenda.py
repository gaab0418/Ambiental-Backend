"""
Agenda API - Events, deadlines, and environmental commitments
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timezone
import json

from app.database import get_db
from app.models.user import User
from app.models.agenda import AgendaEvent, AgendaStatus, AgendaPriority
from app.schemas.agenda import (
    AgendaEventCreate, AgendaEventUpdate, AgendaEventResponse,
    AgendaEventListResponse, AgendaEventStatusUpdate, AgendaStatusEnum
)
from app.dependencies.auth import get_current_active_user, get_organization_from_token
from app.utils.audit_logger import AuditLogger

router = APIRouter()


@router.get("", response_model=AgendaEventListResponse)
async def list_agenda_events(
    request: Request,
    from_date: Optional[str] = Query(None, alias="from"),
    to_date: Optional[str] = Query(None, alias="to"),
    status: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List agenda events with filters."""
    org_id = get_organization_from_token(request)
    
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization context required"
        )
    
    query = db.query(AgendaEvent).filter(AgendaEvent.organization_id == org_id)
    
    # Apply filters
    if from_date:
        try:
            from_dt = datetime.fromisoformat(from_date.replace('Z', '+00:00'))
            query = query.filter(AgendaEvent.starts_at >= from_dt)
        except ValueError:
            pass
    
    if to_date:
        try:
            to_dt = datetime.fromisoformat(to_date.replace('Z', '+00:00'))
            query = query.filter(AgendaEvent.starts_at <= to_dt)
        except ValueError:
            pass
    
    if status:
        try:
            status_enum = AgendaStatus(status)
            query = query.filter(AgendaEvent.status == status_enum)
        except ValueError:
            pass
    
    if type:
        query = query.filter(AgendaEvent.event_type == type)
    
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            AgendaEvent.title.ilike(search_pattern) |
            AgendaEvent.description.ilike(search_pattern)
        )
    
    # Get total count
    total = query.count()
    
    # Get paginated results
    events = query.order_by(AgendaEvent.starts_at.asc()).offset(offset).limit(limit).all()
    
    return AgendaEventListResponse(
        items=[AgendaEventResponse.model_validate(e) for e in events],
        total=total,
        limit=limit,
        offset=offset
    )


@router.post("", response_model=AgendaEventResponse, status_code=status.HTTP_201_CREATED)
async def create_agenda_event(
    request: Request,
    event_data: AgendaEventCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new agenda event."""
    org_id = get_organization_from_token(request)
    
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization context required"
        )
    
    # Create event
    event = AgendaEvent(
        organization_id=org_id,
        title=event_data.title,
        description=event_data.description,
        event_type=event_data.event_type,
        status=AgendaStatus(event_data.status.value),
        priority=AgendaPriority(event_data.priority.value),
        starts_at=event_data.starts_at,
        ends_at=event_data.ends_at,
        location=event_data.location,
        related_process_id=event_data.related_process_id,
        related_document_id=event_data.related_document_id,
        created_by_user_id=current_user.id
    )
    
    db.add(event)
    db.commit()
    db.refresh(event)
    
    # Log audit
    AuditLogger.log_create(
        db=db,
        entity_type="AgendaEvent",
        entity_id=event.id,
        user_id=current_user.id,
        organization_id=org_id,
        changes={"title": event.title, "event_type": event.event_type}
    )
    
    return AgendaEventResponse.model_validate(event)


@router.get("/{event_id}", response_model=AgendaEventResponse)
async def get_agenda_event(
    request: Request,
    event_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get a specific agenda event."""
    org_id = get_organization_from_token(request)
    
    event = db.query(AgendaEvent).filter(
        AgendaEvent.id == event_id,
        AgendaEvent.organization_id == org_id
    ).first()
    
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agenda event not found"
        )
    
    return AgendaEventResponse.model_validate(event)


@router.put("/{event_id}", response_model=AgendaEventResponse)
async def update_agenda_event(
    request: Request,
    event_id: int,
    event_data: AgendaEventUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update an agenda event."""
    org_id = get_organization_from_token(request)
    
    event = db.query(AgendaEvent).filter(
        AgendaEvent.id == event_id,
        AgendaEvent.organization_id == org_id
    ).first()
    
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agenda event not found"
        )
    
    # Update fields
    update_data = event_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "status" and value:
            setattr(event, field, AgendaStatus(value.value))
        elif field == "priority" and value:
            setattr(event, field, AgendaPriority(value.value))
        else:
            setattr(event, field, value)
    
    event.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(event)
    
    # Log audit
    AuditLogger.log_update(
        db=db,
        entity_type="AgendaEvent",
        entity_id=event.id,
        changes=update_data,
        user_id=current_user.id,
        organization_id=org_id
    )
    
    return AgendaEventResponse.model_validate(event)


@router.put("/{event_id}/status", response_model=AgendaEventResponse)
async def update_agenda_event_status(
    request: Request,
    event_id: int,
    status_data: AgendaEventStatusUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update the status of an agenda event."""
    org_id = get_organization_from_token(request)
    
    event = db.query(AgendaEvent).filter(
        AgendaEvent.id == event_id,
        AgendaEvent.organization_id == org_id
    ).first()
    
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agenda event not found"
        )
    
    old_status = event.status.value
    event.status = AgendaStatus(status_data.status.value)
    event.updated_at = datetime.now(timezone.utc)
    
    db.commit()
    db.refresh(event)
    
    # Log audit
    AuditLogger.log_update(
        db=db,
        entity_type="AgendaEvent",
        entity_id=event.id,
        changes={"status": {"old": old_status, "new": event.status.value}},
        user_id=current_user.id,
        organization_id=org_id
    )
    
    return AgendaEventResponse.model_validate(event)


@router.delete("/{event_id}")
async def delete_agenda_event(
    request: Request,
    event_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete an agenda event."""
    org_id = get_organization_from_token(request)
    
    event = db.query(AgendaEvent).filter(
        AgendaEvent.id == event_id,
        AgendaEvent.organization_id == org_id
    ).first()
    
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agenda event not found"
        )
    
    event_title = event.title
    
    # Log audit before deletion
    AuditLogger.log_delete(
        db=db,
        entity_type="AgendaEvent",
        entity_id=event.id,
        user_id=current_user.id,
        organization_id=org_id,
        changes={"title": event_title}
    )
    
    db.delete(event)
    db.commit()
    
    return {"message": f"Agenda event '{event_title}' deleted successfully"}



