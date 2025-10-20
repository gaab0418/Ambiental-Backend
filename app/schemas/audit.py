from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class AuditLogResponse(BaseModel):
    id: int
    user_id: Optional[int] = None
    organization_id: Optional[int] = None
    action: str
    entity_type: str
    entity_id: Optional[int] = None
    changes: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime
    
    # Related data (optional, populated in responses)
    user_email: Optional[str] = None
    organization_name: Optional[str] = None

    class Config:
        from_attributes = True


class AuditLogQuery(BaseModel):
    user_id: Optional[int] = None
    organization_id: Optional[int] = None
    action: Optional[str] = None
    entity_type: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class AuditLogCreate(BaseModel):
    user_id: Optional[int] = None
    organization_id: Optional[int] = None
    action: str
    entity_type: str
    entity_id: Optional[int] = None
    changes: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


