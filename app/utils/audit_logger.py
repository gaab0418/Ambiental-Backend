"""
Audit Logger Utility
Logs audit events for security and compliance tracking
"""

from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional, Dict, Any
from app.models.audit_log import AuditLog
from app.models.user import User


class AuditLogger:
    """Centralized audit logging utility"""
    
    @staticmethod
    def log_event(
        db: Session,
        user_id: int,
        action: str,
        resource_type: str,
        resource_id: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None
    ) -> AuditLog:
        """
        Log an audit event
        
        Args:
            db: Database session
            user_id: ID of user performing action
            action: Action performed (e.g., "CREATE", "UPDATE", "DELETE", "VIEW")
            resource_type: Type of resource (e.g., "USER", "ORGANIZATION", "TEMPLATE")
            resource_id: Optional ID of the resource
            details: Optional additional details as JSON
            ip_address: Optional IP address of the request
            
        Returns:
            Created AuditLog instance
        """
        audit_log = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            ip_address=ip_address,
            timestamp=datetime.utcnow()
        )
        
        db.add(audit_log)
        db.commit()
        db.refresh(audit_log)
        
        return audit_log
    
    @staticmethod
    def log_login(
        db: Session,
        user_id: int,
        success: bool,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> AuditLog:
        """Log a login attempt"""
        return AuditLogger.log_event(
            db=db,
            user_id=user_id,
            action="LOGIN_SUCCESS" if success else "LOGIN_FAILED",
            resource_type="AUTH",
            details={
                "success": success,
                "user_agent": user_agent
            },
            ip_address=ip_address
        )
    
    @staticmethod
    def log_create(
        db: Session,
        user_id: int,
        resource_type: str,
        resource_id: int,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None
    ) -> AuditLog:
        """Log resource creation"""
        return AuditLogger.log_event(
            db=db,
            user_id=user_id,
            action="CREATE",
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            ip_address=ip_address
        )
    
    @staticmethod
    def log_update(
        db: Session,
        user_id: int,
        resource_type: str,
        resource_id: int,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None
    ) -> AuditLog:
        """Log resource update"""
        return AuditLogger.log_event(
            db=db,
            user_id=user_id,
            action="UPDATE",
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            ip_address=ip_address
        )
    
    @staticmethod
    def log_delete(
        db: Session,
        user_id: int,
        resource_type: str,
        resource_id: int,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None
    ) -> AuditLog:
        """Log resource deletion"""
        return AuditLogger.log_event(
            db=db,
            user_id=user_id,
            action="DELETE",
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            ip_address=ip_address
        )

