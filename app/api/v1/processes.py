"""
Processes API - Environmental processes and workflows
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, timezone
import json

from app.database import get_db
from app.models.user import User
from app.models.process import Process, ProcessStatus, ProcessPriority, ProcessTimelineEntry
from app.schemas.processes import (
    ProcessCreate, ProcessUpdate, ProcessResponse,
    ProcessListResponse, ProcessStatusUpdate, ProcessProgressUpdate,
    ProcessTimelineEntryCreate, ProcessTimelineEntryResponse,
    ProcessStatusEnum, ProcessPriorityEnum
)
from app.dependencies.auth import get_current_active_user, get_organization_from_token
from app.utils.audit_logger import AuditLogger

router = APIRouter()


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


def process_to_response(proc: Process) -> ProcessResponse:
    """Convert Process model to response schema."""
    return ProcessResponse(
        id=proc.id,
        title=proc.title,
        protocol=proc.protocol,
        status=ProcessStatusEnum(proc.status.value),
        priority=ProcessPriorityEnum(proc.priority.value),
        progress=proc.progress,
        responsible=proc.responsible,
        location=proc.location,
        tags=parse_tags(proc.tags),
        summary=proc.summary,
        deadline=proc.deadline,
        created_at=proc.created_at,
        updated_at=proc.updated_at
    )


@router.get("", response_model=ProcessListResponse)
async def list_processes(
    request: Request,
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    from_date: Optional[str] = Query(None, alias="from"),
    to_date: Optional[str] = Query(None, alias="to"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List processes with filters."""
    org_id = get_organization_from_token(request)
    
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization context required"
        )
    
    query = db.query(Process).filter(Process.organization_id == org_id)
    
    # Apply filters
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            Process.title.ilike(search_pattern) |
            Process.protocol.ilike(search_pattern) |
            Process.summary.ilike(search_pattern)
        )
    
    if status:
        try:
            status_enum = ProcessStatus(status)
            query = query.filter(Process.status == status_enum)
        except ValueError:
            pass
    
    if priority:
        try:
            priority_enum = ProcessPriority(priority)
            query = query.filter(Process.priority == priority_enum)
        except ValueError:
            pass
    
    if from_date:
        try:
            from_dt = datetime.fromisoformat(from_date.replace('Z', '+00:00'))
            query = query.filter(Process.created_at >= from_dt)
        except ValueError:
            pass
    
    if to_date:
        try:
            to_dt = datetime.fromisoformat(to_date.replace('Z', '+00:00'))
            query = query.filter(Process.created_at <= to_dt)
        except ValueError:
            pass
    
    # Get total count
    total = query.count()
    
    # Get paginated results
    processes = query.order_by(Process.created_at.desc()).offset(offset).limit(limit).all()
    
    return ProcessListResponse(
        items=[process_to_response(proc) for proc in processes],
        total=total,
        limit=limit,
        offset=offset
    )


@router.post("", response_model=ProcessResponse, status_code=status.HTTP_201_CREATED)
async def create_process(
    request: Request,
    process_data: ProcessCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new process."""
    org_id = get_organization_from_token(request)
    
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization context required"
        )
    
    # Check if protocol already exists
    existing = db.query(Process).filter(Process.protocol == process_data.protocol).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Protocol already exists"
        )
    
    # Create process
    process = Process(
        organization_id=org_id,
        title=process_data.title,
        protocol=process_data.protocol,
        status=ProcessStatus(process_data.status.value),
        priority=ProcessPriority(process_data.priority.value),
        progress=process_data.progress,
        responsible=process_data.responsible,
        location=process_data.location,
        tags=serialize_tags(process_data.tags),
        summary=process_data.summary,
        deadline=process_data.deadline,
        created_by_user_id=current_user.id
    )
    
    db.add(process)
    db.commit()
    db.refresh(process)
    
    # Create initial timeline entry
    timeline_entry = ProcessTimelineEntry(
        process_id=process.id,
        title="Processo criado",
        description=f"Processo '{process.title}' criado por {current_user.full_name}",
        status=process.status
    )
    db.add(timeline_entry)
    db.commit()
    
    # Log audit
    AuditLogger.log_create(
        db=db,
        entity_type="Process",
        entity_id=process.id,
        user_id=current_user.id,
        organization_id=org_id,
        changes={"title": process.title, "protocol": process.protocol}
    )
    
    return process_to_response(process)


@router.get("/{process_id}", response_model=ProcessResponse)
async def get_process(
    request: Request,
    process_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get a specific process."""
    org_id = get_organization_from_token(request)
    
    process = db.query(Process).filter(
        Process.id == process_id,
        Process.organization_id == org_id
    ).first()
    
    if not process:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Process not found"
        )
    
    return process_to_response(process)


@router.put("/{process_id}", response_model=ProcessResponse)
async def update_process(
    request: Request,
    process_id: int,
    process_data: ProcessUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update a process."""
    org_id = get_organization_from_token(request)
    
    process = db.query(Process).filter(
        Process.id == process_id,
        Process.organization_id == org_id
    ).first()
    
    if not process:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Process not found"
        )
    
    # Check protocol uniqueness if changing
    if process_data.protocol and process_data.protocol != process.protocol:
        existing = db.query(Process).filter(Process.protocol == process_data.protocol).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Protocol already exists"
            )
    
    # Update fields
    update_data = process_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "status" and value:
            setattr(process, field, ProcessStatus(value.value))
        elif field == "priority" and value:
            setattr(process, field, ProcessPriority(value.value))
        elif field == "tags":
            setattr(process, field, serialize_tags(value))
        else:
            setattr(process, field, value)
    
    process.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(process)
    
    # Log audit
    AuditLogger.log_update(
        db=db,
        entity_type="Process",
        entity_id=process.id,
        changes=update_data,
        user_id=current_user.id,
        organization_id=org_id
    )
    
    return process_to_response(process)


@router.put("/{process_id}/status", response_model=ProcessResponse)
async def update_process_status(
    request: Request,
    process_id: int,
    status_data: ProcessStatusUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update the status of a process."""
    org_id = get_organization_from_token(request)
    
    process = db.query(Process).filter(
        Process.id == process_id,
        Process.organization_id == org_id
    ).first()
    
    if not process:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Process not found"
        )
    
    old_status = process.status.value
    new_status = ProcessStatus(status_data.status.value)
    process.status = new_status
    process.updated_at = datetime.now(timezone.utc)
    
    # Create timeline entry for status change
    timeline_entry = ProcessTimelineEntry(
        process_id=process.id,
        title=f"Status alterado para {new_status.value}",
        description=f"Status alterado de {old_status} para {new_status.value} por {current_user.full_name}",
        status=new_status
    )
    db.add(timeline_entry)
    
    db.commit()
    db.refresh(process)
    
    # Log audit
    AuditLogger.log_update(
        db=db,
        entity_type="Process",
        entity_id=process.id,
        changes={"status": {"old": old_status, "new": new_status.value}},
        user_id=current_user.id,
        organization_id=org_id
    )
    
    return process_to_response(process)


@router.put("/{process_id}/progress", response_model=ProcessResponse)
async def update_process_progress(
    request: Request,
    process_id: int,
    progress_data: ProcessProgressUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update the progress of a process."""
    org_id = get_organization_from_token(request)
    
    process = db.query(Process).filter(
        Process.id == process_id,
        Process.organization_id == org_id
    ).first()
    
    if not process:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Process not found"
        )
    
    old_progress = process.progress
    process.progress = progress_data.progress
    process.updated_at = datetime.now(timezone.utc)
    
    db.commit()
    db.refresh(process)
    
    # Log audit
    AuditLogger.log_update(
        db=db,
        entity_type="Process",
        entity_id=process.id,
        changes={"progress": {"old": old_progress, "new": process.progress}},
        user_id=current_user.id,
        organization_id=org_id
    )
    
    return process_to_response(process)


@router.get("/{process_id}/timeline", response_model=List[ProcessTimelineEntryResponse])
async def get_process_timeline(
    request: Request,
    process_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get timeline entries for a process."""
    org_id = get_organization_from_token(request)
    
    process = db.query(Process).filter(
        Process.id == process_id,
        Process.organization_id == org_id
    ).first()
    
    if not process:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Process not found"
        )
    
    entries = db.query(ProcessTimelineEntry).filter(
        ProcessTimelineEntry.process_id == process_id
    ).order_by(ProcessTimelineEntry.created_at.desc()).all()
    
    return [
        ProcessTimelineEntryResponse(
            id=entry.id,
            process_id=entry.process_id,
            title=entry.title,
            description=entry.description,
            status=ProcessStatusEnum(entry.status.value),
            created_at=entry.created_at
        )
        for entry in entries
    ]


@router.post("/{process_id}/timeline", response_model=ProcessTimelineEntryResponse, status_code=status.HTTP_201_CREATED)
async def add_timeline_entry(
    request: Request,
    process_id: int,
    entry_data: ProcessTimelineEntryCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Add a timeline entry to a process."""
    org_id = get_organization_from_token(request)
    
    process = db.query(Process).filter(
        Process.id == process_id,
        Process.organization_id == org_id
    ).first()
    
    if not process:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Process not found"
        )
    
    entry = ProcessTimelineEntry(
        process_id=process_id,
        title=entry_data.title,
        description=entry_data.description,
        status=ProcessStatus(entry_data.status.value)
    )
    
    db.add(entry)
    db.commit()
    db.refresh(entry)
    
    return ProcessTimelineEntryResponse(
        id=entry.id,
        process_id=entry.process_id,
        title=entry.title,
        description=entry.description,
        status=ProcessStatusEnum(entry.status.value),
        created_at=entry.created_at
    )


@router.delete("/{process_id}")
async def delete_process(
    request: Request,
    process_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete a process."""
    org_id = get_organization_from_token(request)
    
    process = db.query(Process).filter(
        Process.id == process_id,
        Process.organization_id == org_id
    ).first()
    
    if not process:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Process not found"
        )
    
    process_title = process.title
    
    # Log audit before deletion
    AuditLogger.log_delete(
        db=db,
        entity_type="Process",
        entity_id=process.id,
        user_id=current_user.id,
        organization_id=org_id,
        changes={"title": process_title, "protocol": process.protocol}
    )
    
    # Delete process (timeline entries will be cascade deleted)
    db.delete(process)
    db.commit()
    
    return {"message": f"Process '{process_title}' deleted successfully"}



