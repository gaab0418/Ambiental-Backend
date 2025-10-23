"""
Audit Logger Utility
Logs audit events for security and compliance tracking
"""

from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional, Dict, Any
import json
from app.models.audit_log import AuditLog


class AuditLogger:
    """Centralized audit logging utility"""
    
    @staticmethod
    def log_action(
        db: Session,
        action: str,
        entity_type: str,
        entity_id: Optional[int] = None,
        user_id: Optional[int] = None,
        organization_id: Optional[int] = None,
        changes: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Optional[AuditLog]:
        """
        Log an audit action
        
        Args:
            db: Database session
            action: Action performed (e.g., "CREATE", "UPDATE", "DELETE", "LOGIN")
            entity_type: Type of entity (e.g., "User", "Organization", "DocumentTemplate")
            entity_id: Optional ID of the entity
            user_id: ID of user performing action
            organization_id: ID of organization
            changes: Optional changes as dict (will be JSON serialized)
            ip_address: Optional IP address
            user_agent: Optional user agent string
            
        Returns:
            Created AuditLog instance or None on error
        """
        try:
            # Serialize changes to JSON string
            changes_json = json.dumps(changes) if changes else None
            
            audit_log = AuditLog(
                user_id=user_id,
                organization_id=organization_id,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                changes=changes_json,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            db.add(audit_log)
            db.commit()
            db.refresh(audit_log)
            
            return audit_log
        except Exception as e:
            # Log error but don't break the request
            print(f"Audit logging error: {e}")
            db.rollback()
            return None
    
    @staticmethod
    def log_create(
        db: Session,
        entity_type: str,
        entity_id: int,
        user_id: Optional[int] = None,
        organization_id: Optional[int] = None,
        changes: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Optional[AuditLog]:
        """Log resource creation"""
        return AuditLogger.log_action(
            db=db,
            action="CREATE",
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=user_id,
            organization_id=organization_id,
            changes=changes,
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    @staticmethod
    def log_update(
        db: Session,
        entity_type: str,
        entity_id: int,
        changes: Optional[Dict[str, Any]] = None,
        user_id: Optional[int] = None,
        organization_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Optional[AuditLog]:
        """Log resource update"""
        return AuditLogger.log_action(
            db=db,
            action="UPDATE",
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=user_id,
            organization_id=organization_id,
            changes=changes,
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    @staticmethod
    def log_delete(
        db: Session,
        entity_type: str,
        entity_id: int,
        changes: Optional[Dict[str, Any]] = None,
        user_id: Optional[int] = None,
        organization_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Optional[AuditLog]:
        """Log resource deletion"""
        return AuditLogger.log_action(
            db=db,
            action="DELETE",
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=user_id,
            organization_id=organization_id,
            changes=changes,
            ip_address=ip_address,
            user_agent=user_agent
        )

