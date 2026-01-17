"""
API Keys Management Endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel
import secrets
import hashlib

from app.database import get_db
from app.models.user import User
from app.models.api_key import ApiKey
from app.dependencies.auth import get_current_active_user, require_administrator, get_organization_from_token
from app.utils.audit_logger import AuditLogger

router = APIRouter()


class ApiKeyCreate(BaseModel):
    name: str
    expires_in_days: int | None = None  # None = never expires


class ApiKeyResponse(BaseModel):
    id: int
    name: str
    key: str | None = None  # Only returned on creation
    organization_id: int
    created_by_user_id: int
    is_active: bool
    last_used_at: datetime | None
    expires_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True


def hash_key(key: str) -> str:
    """Hash an API key using SHA256."""
    return hashlib.sha256(key.encode()).hexdigest()


def generate_api_key() -> str:
    """Generate a secure random API key."""
    return f"nak_{secrets.token_urlsafe(32)}"  # nak = NormaHub API Key


@router.post("", response_model=ApiKeyResponse, dependencies=[Depends(require_administrator)])
async def create_api_key(
    request: Request,
    data: ApiKeyCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create a new API key (Administrator only).
    
    The generated key is only shown once during creation.
    Store it securely as it cannot be retrieved later.
    """
    org_id = get_organization_from_token(request)
    
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization context required"
        )
    
    # Generate key
    api_key_plain = generate_api_key()
    key_hash = hash_key(api_key_plain)
    
    # Calculate expiration
    expires_at = None
    if data.expires_in_days:
        expires_at = datetime.now(timezone.utc) + timedelta(days=data.expires_in_days)
    
    # Create API key
    api_key = ApiKey(
        name=data.name,
        key_hash=key_hash,
        organization_id=org_id,
        created_by_user_id=current_user.id,
        is_active=True,
        expires_at=expires_at
    )
    
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    
    # Log audit
    AuditLogger.log_create(
        db=db,
        entity_type="ApiKey",
        entity_id=api_key.id,
        user_id=current_user.id,
        organization_id=org_id,
        changes={"name": api_key.name, "expires_at": str(expires_at) if expires_at else "never"}
    )
    
    # Return response with plain key (only time it's visible)
    response = ApiKeyResponse.from_orm(api_key)
    response.key = api_key_plain  # Include plain key in response
    
    return response


@router.get("", response_model=List[ApiKeyResponse])
async def list_api_keys(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List all API keys for the current organization."""
    org_id = get_organization_from_token(request)
    
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization context required"
        )
    
    api_keys = db.query(ApiKey).filter(
        ApiKey.organization_id == org_id
    ).order_by(ApiKey.created_at.desc()).all()
    
    # Don't include the plain key in list responses
    return [ApiKeyResponse.from_orm(key) for key in api_keys]


@router.delete("/{key_id}", dependencies=[Depends(require_administrator)])
async def revoke_api_key(
    request: Request,
    key_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Revoke (delete) an API key (Administrator only)."""
    org_id = get_organization_from_token(request)
    
    api_key = db.query(ApiKey).filter(
        ApiKey.id == key_id,
        ApiKey.organization_id == org_id
    ).first()
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API Key not found"
        )
    
    key_name = api_key.name
    
    # Log audit before deletion
    AuditLogger.log_delete(
        db=db,
        entity_type="ApiKey",
        entity_id=api_key.id,
        user_id=current_user.id,
        organization_id=org_id,
        changes={"name": key_name}
    )
    
    db.delete(api_key)
    db.commit()
    
    return {"message": f"API Key '{key_name}' revoked successfully"}
