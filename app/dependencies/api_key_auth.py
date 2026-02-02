"""
API Key Authentication Dependency

Provides authentication via X-API-Key header for third-party integrations.
"""

from fastapi import Header, HTTPException, status, Depends
from sqlalchemy.orm import Session
from typing import Optional, Tuple
import hashlib
from datetime import datetime, timezone

from app.database import get_db
from app.models.api_key import ApiKey
from app.models.organization import Organization


def hash_api_key(key: str) -> str:
    """Hash an API key using SHA256."""
    return hashlib.sha256(key.encode()).hexdigest()


async def verify_api_key(
    x_api_key: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> Tuple[ApiKey, Organization]:
    """
    Verify API key from X-API-Key header.
    
    Returns:
        Tuple of (ApiKey, Organization) if valid
        
    Raises:
        HTTPException: If key is invalid or inactive
    """
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key required. Include X-API-Key header."
        )
    
    # Hash the provided key
    key_hash = hash_api_key(x_api_key)
    
    # Find API key in database
    api_key = db.query(ApiKey).filter(
        ApiKey.key_hash == key_hash,
        ApiKey.is_active == True
    ).first()
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key"
        )
    
    # Check expiration
    if api_key.expires_at and api_key.expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key has expired"
        )
    
    # Update last used timestamp
    api_key.last_used_at = datetime.now(timezone.utc)
    db.commit()
    
    # Get organization
    organization = db.query(Organization).filter(
        Organization.id == api_key.organization_id
    ).first()
    
    if not organization or not organization.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization is not active"
        )
    
    return api_key, organization
