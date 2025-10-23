from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
from app.database import get_db
from app.models.audit_log import AuditLog
from app.models.user import User
from app.schemas.audit import AuditLogResponse, AuditLogQuery
from app.dependencies.auth import get_current_active_user, require_administrator

router = APIRouter()


@router.get("/audit", response_model=dict)
async def get_audit_logs(
    user_id: Optional[int] = Query(None),
    organization_id: Optional[int] = Query(None),
    action: Optional[str] = Query(None),
    entity_type: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_administrator),
    db: Session = Depends(get_db)
):
    """Get audit logs with filters and pagination (ADMINISTRATOR only)."""
    
    query = db.query(AuditLog)
    
    # Apply filters
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    if organization_id:
        query = query.filter(AuditLog.organization_id == organization_id)
    if action:
        query = query.filter(AuditLog.action == action)
    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type)
    if date_from:
        query = query.filter(AuditLog.created_at >= date_from)
    if date_to:
        query = query.filter(AuditLog.created_at <= date_to)
    
    # Get total count
    total = query.count()
    
    # Get paginated results
    logs = query.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit).all()
    
    # Convert to response format
    logs_data = []
    for log in logs:
        log_dict = {
            "id": log.id,
            "user_id": log.user_id,
            "organization_id": log.organization_id,
            "action": log.action,
            "entity_type": log.entity_type,
            "entity_id": log.entity_id,
            "changes": log.changes,
            "ip_address": log.ip_address,
            "user_agent": log.user_agent,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        
        # Add related user email if available
        if log.user:
            log_dict["user_email"] = log.user.email
        
        # Add related organization name if available
        if log.organization:
            log_dict["organization_name"] = log.organization.name
        
        logs_data.append(log_dict)
    
    return {
        "logs": logs_data,
        "total": total,
        "limit": limit,
        "offset": offset
    }


@router.get("/audit/{log_id}", response_model=AuditLogResponse)
async def get_audit_log(
    log_id: int,
    current_user: User = Depends(require_administrator),
    db: Session = Depends(get_db)
):
    """Get audit log by ID (ADMINISTRATOR only)."""
    
    log = db.query(AuditLog).filter(AuditLog.id == log_id).first()
    
    if not log:
        raise HTTPException(status_code=404, detail="Audit log not found")
    
    return log


@router.get("/my-activity", response_model=dict)
async def get_my_activity(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get current user's activity logs."""
    
    query = db.query(AuditLog).filter(AuditLog.user_id == current_user.id)
    
    # Get total count
    total = query.count()
    
    # Get paginated results
    logs = query.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit).all()
    
    # Convert to response format
    logs_data = []
    for log in logs:
        logs_data.append({
            "id": log.id,
            "action": log.action,
            "entity_type": log.entity_type,
            "entity_id": log.entity_id,
            "changes": log.changes,
            "ip_address": log.ip_address,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        })
    
    return {
        "logs": logs_data,
        "total": total,
        "limit": limit,
        "offset": offset
    }



