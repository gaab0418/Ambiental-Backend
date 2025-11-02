from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.organization import Organization
from app.models.user import User
from app.schemas.organization import OrganizationResponse, OrganizationFullUpdate
from app.dependencies.auth import require_consultant, get_organization_from_token
from app.utils.audit_logger import AuditLogger

router = APIRouter()


@router.get("/organizations", response_model=list[OrganizationResponse])
async def get_organizations(
    current_user: User = Depends(require_consultant),
    db: Session = Depends(get_db)
):
    """Get organizations that the consultant has access to."""
    
    # For now, return all active organizations
    # In a production system, you would have a mapping table for consultant-organization relationships
    organizations = db.query(Organization).filter(Organization.is_active == True).all()
    
    return organizations


@router.get("/organizations/{org_id}/details", response_model=OrganizationResponse)
async def get_organization_details(
    org_id: int,
    current_user: User = Depends(require_consultant),
    db: Session = Depends(get_db)
):
    """Get organization details by ID."""
    
    organization = db.query(Organization).filter(Organization.id == org_id).first()
    
    if not organization:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    # TODO: In production, verify consultant has access to this organization
    
    return organization


@router.put("/organizations/{org_id}", response_model=OrganizationResponse)
async def update_organization(
    request: Request,
    org_id: int,
    org_data: OrganizationFullUpdate,
    current_user: User = Depends(require_consultant),
    db: Session = Depends(get_db)
):
    """Update organization data (not users)."""
    
    organization = db.query(Organization).filter(Organization.id == org_id).first()
    
    if not organization:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    # TODO: In production, verify consultant has access to this organization
    
    # Track changes for audit
    changes = {}
    
    # Update fields
    if org_data.name is not None:
        changes["name"] = {"old": organization.name, "new": org_data.name}
        organization.name = org_data.name
    
    if org_data.email is not None:
        changes["email"] = {"old": organization.email, "new": org_data.email}
        organization.email = org_data.email
    
    if org_data.phone is not None:
        organization.phone = org_data.phone
    
    if org_data.address is not None:
        organization.address = org_data.address
    
    if org_data.website is not None:
        organization.website = org_data.website
    
    if org_data.company_size is not None:
        organization.company_size = org_data.company_size
    
    if org_data.industry is not None:
        organization.industry = org_data.industry
    
    if org_data.description is not None:
        organization.description = org_data.description
    
    if org_data.logo_url is not None:
        organization.logo_url = org_data.logo_url
    
    db.commit()
    db.refresh(organization)
    
    # Get organization_id from token
    current_org_id = get_organization_from_token(request)
    
    # Log audit
    AuditLogger.log_update(
        db=db,
        entity_type="Organization",
        entity_id=organization.id,
        changes=changes,
        user_id=current_user.id,
        organization_id=current_org_id
    )
    
    return organization


@router.get("/organizations/assigned", response_model=list[OrganizationResponse])
async def get_assigned_organizations(
    current_user: User = Depends(require_consultant),
    db: Session = Depends(get_db)
):
    """Get organizations assigned to consultant with basic info."""
    
    # For now, return all active organizations
    # In production, this would filter based on consultant-organization assignments
    organizations = db.query(Organization).filter(Organization.is_active == True).all()
    
    return organizations



