from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from app.database import get_db
from app.models.user import User
from app.models.organization import Organization
from app.models.subscription import Subscription, SubscriptionStatus
from app.models.plan import Plan
from app.schemas.master import (
    MasterOrganizationResponse, MasterSubscriptionUpdateRequest,
    MasterSubscriptionResponse, MasterUserResponse
)
from app.dependencies.auth import require_super_admin

router = APIRouter()


@router.get("/organizations", response_model=List[MasterOrganizationResponse])
async def get_all_organizations(
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    """Get all organizations in the platform."""
    organizations = db.query(Organization).offset(skip).limit(limit).all()
    
    result = []
    for org in organizations:
        # Get user count
        user_count = db.query(User).filter(
            User.organization_id == org.id
        ).count()
        
        # Get subscription status
        subscription = db.query(Subscription).filter(
            Subscription.organization_id == org.id
        ).first()
        
        subscription_status = "none"
        if subscription:
            subscription_status = subscription.status.value
        
        result.append(MasterOrganizationResponse(
            id=org.id,
            name=org.name,
            slug=org.slug,
            email=org.email,
            phone=org.phone,
            address=org.address,
            is_active=org.is_active,
            created_at=org.created_at,
            user_count=user_count,
            subscription_status=subscription_status
        ))
    
    return result


@router.get("/organizations/{org_id}", response_model=MasterOrganizationResponse)
async def get_organization_details(
    org_id: int,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """Get detailed information about a specific organization."""
    organization = db.query(Organization).filter(Organization.id == org_id).first()
    
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    # Get user count
    user_count = db.query(User).filter(
        User.organization_id == organization.id
    ).count()
    
    # Get subscription status
    subscription = db.query(Subscription).filter(
        Subscription.organization_id == organization.id
    ).first()
    
    subscription_status = "none"
    if subscription:
        subscription_status = subscription.status.value
    
    return MasterOrganizationResponse(
        id=organization.id,
        name=organization.name,
        slug=organization.slug,
        email=organization.email,
        phone=organization.phone,
        address=organization.address,
        is_active=organization.is_active,
        created_at=organization.created_at,
        user_count=user_count,
        subscription_status=subscription_status
    )


@router.get("/organizations/{org_id}/subscription", response_model=MasterSubscriptionResponse)
async def get_organization_subscription(
    org_id: int,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """Get subscription details for a specific organization."""
    subscription = db.query(Subscription).filter(
        Subscription.organization_id == org_id
    ).first()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No subscription found for this organization"
        )
    
    return MasterSubscriptionResponse(
        id=subscription.id,
        status=subscription.status.value,
        current_period_start=subscription.current_period_start,
        current_period_end=subscription.current_period_end,
        trial_end=subscription.trial_end,
        canceled_at=subscription.canceled_at,
        plan_name=subscription.plan.name,
        plan_price=subscription.plan.price,
        created_at=subscription.created_at
    )


@router.put("/organizations/{org_id}/subscription")
async def update_organization_subscription(
    org_id: int,
    subscription_data: MasterSubscriptionUpdateRequest,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """Update subscription for a specific organization."""
    # Verify organization exists
    organization = db.query(Organization).filter(Organization.id == org_id).first()
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    # Verify plan exists
    plan = db.query(Plan).filter(Plan.id == subscription_data.plan_id).first()
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan not found"
        )
    
    # Get or create subscription
    subscription = db.query(Subscription).filter(
        Subscription.organization_id == org_id
    ).first()
    
    if not subscription:
        # Create new subscription
        subscription = Subscription(
            organization_id=org_id,
            plan_id=subscription_data.plan_id,
            status=SubscriptionStatus(subscription_data.status),
            current_period_start=datetime.utcnow(),
            current_period_end=subscription_data.current_period_end or datetime.utcnow(),
            trial_end=subscription_data.trial_end
        )
        db.add(subscription)
    else:
        # Update existing subscription
        subscription.plan_id = subscription_data.plan_id
        subscription.status = SubscriptionStatus(subscription_data.status)
        subscription.updated_at = datetime.utcnow()
        
        if subscription_data.current_period_end:
            subscription.current_period_end = subscription_data.current_period_end
        
        if subscription_data.trial_end:
            subscription.trial_end = subscription_data.trial_end
        
        if subscription_data.status == "canceled":
            subscription.canceled_at = datetime.utcnow()
    
    db.commit()
    db.refresh(subscription)
    
    return {"message": "Subscription updated successfully"}


@router.get("/organizations/{org_id}/users", response_model=List[MasterUserResponse])
async def get_organization_users(
    org_id: int,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """Get all users from a specific organization."""
    # Verify organization exists
    organization = db.query(Organization).filter(Organization.id == org_id).first()
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    users = db.query(User).filter(User.organization_id == org_id).all()
    
    result = []
    for user in users:
        result.append(MasterUserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            is_verified=user.is_verified,
            role_name=user.role.name,
            organization_name=user.organization.name,
            created_at=user.created_at,
            last_login_at=user.last_login_at
        ))
    
    return result


@router.put("/organizations/{org_id}/activate")
async def activate_organization(
    org_id: int,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """Activate an organization."""
    organization = db.query(Organization).filter(Organization.id == org_id).first()
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    organization.is_active = True
    organization.updated_at = datetime.utcnow()
    
    db.commit()
    
    return {"message": "Organization activated successfully"}


@router.put("/organizations/{org_id}/deactivate")
async def deactivate_organization(
    org_id: int,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """Deactivate an organization."""
    organization = db.query(Organization).filter(Organization.id == org_id).first()
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    organization.is_active = False
    organization.updated_at = datetime.utcnow()
    
    # Also deactivate all users in the organization
    users = db.query(User).filter(User.organization_id == org_id).all()
    for user in users:
        user.is_active = False
    
    db.commit()
    
    return {"message": "Organization deactivated successfully"}
