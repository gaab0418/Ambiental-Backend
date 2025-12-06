"""
Organization activation endpoints for on-prem deployments.
"""

import secrets
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.database import get_db
from app.models.organization import Organization
from app.models.user import User
from app.dependencies.auth import get_current_user
from app.utils.org_credentials_resolver import OrgCredentialsResolver

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/activation", tags=["activation"])


class ActivationKeyRequest(BaseModel):
    """Request to generate activation key for an organization"""
    org_id: int = Field(..., description="Organization ID")


class ActivationKeyResponse(BaseModel):
    """Response with activation key"""
    activation_key: str = Field(..., description="Activation key (show once)")
    org_id: int
    org_name: str
    expires_at: Optional[datetime] = None


class ActivateRequest(BaseModel):
    """Request to activate on-prem installation"""
    activation_key: str = Field(..., description="Activation key")


class ActivateResponse(BaseModel):
    """Response after activation"""
    org_id: int
    org_name: str
    mode: str
    status: str
    message: str


class ConnectionConfigRequest(BaseModel):
    """Request to configure on-prem database connection"""
    activation_key: str = Field(..., description="Activation key for validation")
    db_type: str = Field(..., description="Database type: app, vector, or logs")
    host: str
    port: int = Field(default=5432)
    database: str
    username: str
    password: str


class ConnectionConfigResponse(BaseModel):
    """Response after configuring connection"""
    org_id: int
    db_type: str
    message: str


@router.post("/generate-key", response_model=ActivationKeyResponse)
async def generate_activation_key(
    request: ActivationKeyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generate activation key for an organization (admin only).
    This key is used by on-prem installations to activate.
    """
    # Check if user is admin/master
    if current_user.role.name not in ["master", "administrator"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can generate activation keys"
        )
    
    # Get organization
    org = db.query(Organization).filter(Organization.id == request.org_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organization {request.org_id} not found"
        )
    
    # Generate secure activation key
    activation_key = secrets.token_urlsafe(32)  # 256-bit key
    
    # Hash the key before storing
    key_hash = hashlib.sha256(activation_key.encode()).hexdigest()
    
    # Update organization
    org.activation_key_hash = key_hash
    org.mode = "on_prem"
    
    db.commit()
    
    logger.info(f"Generated activation key for organization {org.id} by user {current_user.id}")
    
    return ActivationKeyResponse(
        activation_key=activation_key,
        org_id=org.id,
        org_name=org.name,
        expires_at=None  # Keys don't expire by default; can add expiry if needed
    )


@router.post("/activate", response_model=ActivateResponse)
async def activate_organization(
    request: ActivateRequest,
    db: Session = Depends(get_db)
):
    """
    Activate an on-prem installation using activation key.
    This endpoint is called by the on-prem installer/setup wizard.
    """
    # Hash the provided key
    key_hash = hashlib.sha256(request.activation_key.encode()).hexdigest()
    
    # Find organization with matching key
    org = db.query(Organization).filter(
        Organization.activation_key_hash == key_hash
    ).first()
    
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid activation key"
        )
    
    # Update organization status
    if org.status == "trial" or org.status == "pending":
        org.status = "active"
        db.commit()
    
    logger.info(f"Organization {org.id} activated via activation key")
    
    return ActivateResponse(
        org_id=org.id,
        org_name=org.name,
        mode=org.mode,
        status=org.status,
        message="Organization activated successfully"
    )


@router.post("/configure-connection", response_model=ConnectionConfigResponse)
async def configure_connection(
    request: ConnectionConfigRequest,
    db: Session = Depends(get_db)
):
    """
    Configure database connection for on-prem organization.
    Called after activation to set up connection details.
    """
    # Hash the provided key
    key_hash = hashlib.sha256(request.activation_key.encode()).hexdigest()
    
    # Find organization with matching key
    org = db.query(Organization).filter(
        Organization.activation_key_hash == key_hash
    ).first()
    
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid activation key"
        )
    
    if org.mode != "on_prem":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization is not configured for on-prem mode"
        )
    
    # Validate db_type
    if request.db_type not in ["app", "vector", "logs"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="db_type must be one of: app, vector, logs"
        )
    
    # Add connection credentials
    resolver = OrgCredentialsResolver(db)
    
    try:
        resolver.add_onprem_connection(
            org_id=org.id,
            db_type=request.db_type,
            location="on_prem",
            host=request.host,
            port=request.port,
            database=request.database,
            username=request.username,
            password=request.password
        )
        
        logger.info(
            f"Configured {request.db_type} connection for organization {org.id}"
        )
        
        return ConnectionConfigResponse(
            org_id=org.id,
            db_type=request.db_type,
            message=f"{request.db_type} connection configured successfully"
        )
    
    except Exception as e:
        logger.error(f"Failed to configure connection: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to configure connection"
        )


@router.get("/connections/{org_id}")
async def get_organization_connections(
    org_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all configured connections for an organization (admin only).
    """
    # Check if user is admin or belongs to the organization
    if current_user.role.name not in ["master", "administrator"]:
        # Check if user belongs to the organization
        user_orgs = [assoc.organization_id for assoc in current_user.organization_associations]
        if org_id not in user_orgs:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
    
    resolver = OrgCredentialsResolver(db)
    connections = resolver.get_all_connections(org_id)
    
    # Return safe info (without decrypted credentials)
    return [
        {
            "id": conn.id,
            "db_type": conn.db_type,
            "location": conn.location,
            "is_active": conn.is_active,
            "created_at": conn.created_at,
            "updated_at": conn.updated_at
        }
        for conn in connections
    ]



