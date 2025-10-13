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
    MasterSubscriptionResponse, MasterUserResponse,
    MasterOrganizationCreateRequest, MasterUserCreateRequest,
    MasterUserUpdateRequest, MasterOrganizationUpdateRequest,
    PlanCreateRequest, PlanUpdateRequest, PlanResponse
)
from app.core.security import get_password_hash
from app.models.license import License, LicenseStatus
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
            cnpj_cpf=org.cnpj_cpf,
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
        cnpj_cpf=organization.cnpj_cpf,
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


@router.put("/organizations/{org_id}", response_model=MasterOrganizationResponse)
async def update_organization(
    org_id: int,
    org_data: MasterOrganizationUpdateRequest,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """Update organization details (Master only)."""
    organization = db.query(Organization).filter(Organization.id == org_id).first()
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    # Check if CNPJ/CPF already exists (if changing)
    if org_data.cnpj_cpf and org_data.cnpj_cpf != organization.cnpj_cpf:
        existing_cnpj = db.query(Organization).filter(Organization.cnpj_cpf == org_data.cnpj_cpf).first()
        if existing_cnpj:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="CNPJ/CPF already registered"
            )
        organization.cnpj_cpf = org_data.cnpj_cpf
    
    # Update fields
    if org_data.name:
        organization.name = org_data.name
        # Update slug
        import re
        slug = re.sub(r'[^a-zA-Z0-9\-]', '', org_data.name.lower().replace(' ', '-'))
        organization.slug = slug
    
    if org_data.email:
        organization.email = org_data.email
    
    if org_data.phone is not None:
        organization.phone = org_data.phone
    
    if org_data.address is not None:
        organization.address = org_data.address
    
    organization.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(organization)
    
    # Get user count and subscription status
    user_count = db.query(User).filter(User.organization_id == organization.id).count()
    subscription = db.query(Subscription).filter(Subscription.organization_id == organization.id).first()
    subscription_status = subscription.status.value if subscription else "none"
    
    return MasterOrganizationResponse(
        id=organization.id,
        name=organization.name,
        slug=organization.slug,
        cnpj_cpf=organization.cnpj_cpf,
        email=organization.email,
        phone=organization.phone,
        address=organization.address,
        is_active=organization.is_active,
        created_at=organization.created_at,
        user_count=user_count,
        subscription_status=subscription_status
    )


@router.delete("/organizations/{org_id}")
async def delete_organization_permanently(
    org_id: int,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """Permanently delete an organization from the database (Master only)."""
    organization = db.query(Organization).filter(Organization.id == org_id).first()
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    # Check if organization has active users
    active_users = db.query(User).filter(
        User.organization_id == org_id,
        User.is_active == True
    ).count()
    
    if active_users > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete organization with {active_users} active users. Deactivate all users first."
        )
    
    org_name = organization.name
    
    # Delete all related data
    # 1. Delete licenses
    db.query(License).filter(License.organization_id == org_id).delete()
    
    # 2. Delete subscriptions
    db.query(Subscription).filter(Subscription.organization_id == org_id).delete()
    
    # 3. Delete users
    db.query(User).filter(User.organization_id == org_id).delete()
    
    # 4. Delete organization
    db.delete(organization)
    db.commit()
    
    return {"message": f"Organization {org_name} and all related data deleted permanently"}


@router.post("/organizations", response_model=MasterOrganizationResponse)
async def create_organization(
    org_data: MasterOrganizationCreateRequest,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """Create a new organization (Master only)."""
    # Check if CNPJ/CPF already exists
    existing_cnpj = db.query(Organization).filter(Organization.cnpj_cpf == org_data.cnpj_cpf).first()
    if existing_cnpj:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CNPJ/CPF already registered"
        )
    
    # Create slug from name
    import re
    slug = re.sub(r'[^a-zA-Z0-9\-]', '', org_data.name.lower().replace(' ', '-'))
    
    # Check if slug already exists
    existing_slug = db.query(Organization).filter(Organization.slug == slug).first()
    if existing_slug:
        # Add random suffix if slug exists
        import random
        slug = f"{slug}-{random.randint(1000, 9999)}"
    
    # Create organization
    organization = Organization(
        name=org_data.name,
        slug=slug,
        cnpj_cpf=org_data.cnpj_cpf,
        email=org_data.email,
        phone=org_data.phone,
        address=org_data.address,
        is_active=True
    )
    db.add(organization)
    db.commit()
    db.refresh(organization)
    
    # Get user count and subscription status
    user_count = db.query(User).filter(User.organization_id == organization.id).count()
    subscription = db.query(Subscription).filter(Subscription.organization_id == organization.id).first()
    subscription_status = subscription.status.value if subscription else "none"
    
    return MasterOrganizationResponse(
        id=organization.id,
        name=organization.name,
        slug=organization.slug,
        cnpj_cpf=organization.cnpj_cpf,
        email=organization.email,
        phone=organization.phone,
        address=organization.address,
        is_active=organization.is_active,
        created_at=organization.created_at,
        user_count=user_count,
        subscription_status=subscription_status
    )


@router.post("/users", response_model=MasterUserResponse)
async def create_user(
    user_data: MasterUserCreateRequest,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """Create a new user in any organization (Master only)."""
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Verify organization exists
    organization = db.query(Organization).filter(Organization.id == user_data.organization_id).first()
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    # Verify role exists
    from app.models.role import Role
    role = db.query(Role).filter(Role.id == user_data.role_id).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    
    # Create user
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        email=user_data.email,
        full_name=user_data.full_name,
        hashed_password=hashed_password,
        organization_id=user_data.organization_id,
        role_id=user_data.role_id,
        is_active=True,
        is_verified=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Check if there are available licenses
    available_license = db.query(License).filter(
        License.organization_id == user_data.organization_id,
        License.status == LicenseStatus.INACTIVE,
        License.user_id.is_(None)
    ).first()
    
    # Assign license if available
    if available_license:
        available_license.user_id = new_user.id
        available_license.status = LicenseStatus.ACTIVE
        available_license.activated_at = datetime.utcnow()
        db.commit()
    
    return MasterUserResponse(
        id=new_user.id,
        email=new_user.email,
        full_name=new_user.full_name,
        is_active=new_user.is_active,
        is_verified=new_user.is_verified,
        role_name=new_user.role.name,
        organization_name=new_user.organization.name,
        created_at=new_user.created_at,
        last_login_at=new_user.last_login_at
    )


@router.put("/users/{user_id}/activate")
async def activate_user(
    user_id: int,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """Activate a user (Master only)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user.is_active = True
    db.commit()
    
    return {"message": f"User {user.email} activated successfully"}


@router.put("/users/{user_id}/deactivate")
async def deactivate_user(
    user_id: int,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """Deactivate a user (Master only)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Don't allow deactivating super admins
    if user.role.name == "SUPER_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot deactivate super admin users"
        )
    
    user.is_active = False
    db.commit()
    
    return {"message": f"User {user.email} deactivated successfully"}


@router.put("/users/{user_id}/change-organization")
async def change_user_organization(
    user_id: int,
    new_organization_id: int,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """Change user's organization (Master only)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Verify new organization exists
    new_organization = db.query(Organization).filter(Organization.id == new_organization_id).first()
    if not new_organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    # Don't allow moving super admins
    if user.role.name == "SUPER_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot change organization for super admin users"
        )
    
    old_org_id = user.organization_id
    
    # Release license from old organization
    old_license = db.query(License).filter(
        License.organization_id == old_org_id,
        License.user_id == user_id,
        License.status == LicenseStatus.ACTIVE
    ).first()
    
    if old_license:
        old_license.status = LicenseStatus.INACTIVE
        old_license.user_id = None
        old_license.deactivated_at = datetime.utcnow()
    
    # Change user organization
    user.organization_id = new_organization_id
    
    # Try to assign license in new organization
    new_license = db.query(License).filter(
        License.organization_id == new_organization_id,
        License.status == LicenseStatus.INACTIVE,
        License.user_id.is_(None)
    ).first()
    
    if new_license:
        new_license.user_id = user_id
        new_license.status = LicenseStatus.ACTIVE
        new_license.activated_at = datetime.utcnow()
    
    db.commit()
    
    return {
        "message": f"User {user.email} moved to {new_organization.name}",
        "license_assigned": new_license is not None
    }


@router.get("/users/{user_id}", response_model=MasterUserResponse)
async def get_user_details(
    user_id: int,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """Get user details (Master only)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return MasterUserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        is_verified=user.is_verified,
        role_name=user.role.name,
        organization_name=user.organization.name,
        created_at=user.created_at,
        last_login_at=user.last_login_at
    )


@router.put("/users/{user_id}", response_model=MasterUserResponse)
async def update_user(
    user_id: int,
    user_data: MasterUserUpdateRequest,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """Update user details (Master only)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check if email already exists (if changing email)
    if user_data.email and user_data.email != user.email:
        existing_user = db.query(User).filter(User.email == user_data.email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        user.email = user_data.email
    
    # Update fields
    if user_data.full_name:
        user.full_name = user_data.full_name
    
    if user_data.phone is not None:
        user.phone = user_data.phone
    
    if user_data.role_id:
        # Verify role exists
        from app.models.role import Role
        role = db.query(Role).filter(Role.id == user_data.role_id).first()
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role not found"
            )
        
        # Don't allow changing super admin role
        if user.role.name == "SUPER_ADMIN":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot change role of super admin users"
            )
        
        user.role_id = user_data.role_id
    
    user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user)
    
    return MasterUserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        is_verified=user.is_verified,
        role_name=user.role.name,
        organization_name=user.organization.name,
        created_at=user.created_at,
        last_login_at=user.last_login_at
    )


@router.delete("/users/{user_id}")
async def delete_user_permanently(
    user_id: int,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """Permanently delete a user from the database (Master only)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Don't allow deleting super admins
    if user.role.name == "SUPER_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete super admin users"
        )
    
    # Release licenses
    licenses = db.query(License).filter(License.user_id == user_id).all()
    for license in licenses:
        license.status = LicenseStatus.INACTIVE
        license.user_id = None
        license.deactivated_at = datetime.utcnow()
    
    # Delete user permanently
    user_email = user.email
    db.delete(user)
    db.commit()
    
    return {"message": f"User {user_email} deleted permanently"}


# ==================== CRUD DE PLANOS ====================

@router.get("/plans", response_model=List[PlanResponse])
async def get_all_plans(
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """Get all plans (Master only)."""
    plans = db.query(Plan).all()
    return plans


@router.get("/plans/{plan_id}", response_model=PlanResponse)
async def get_plan_details(
    plan_id: int,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """Get plan details (Master only)."""
    plan = db.query(Plan).filter(Plan.id == plan_id).first()
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan not found"
        )
    return plan


@router.post("/plans", response_model=PlanResponse)
async def create_plan(
    plan_data: PlanCreateRequest,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """Create a new plan (Master only)."""
    # Check if plan name already exists
    existing_plan = db.query(Plan).filter(Plan.name == plan_data.name).first()
    if existing_plan:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Plan name already exists"
        )
    
    # Create plan
    import json
    features_str = json.dumps(plan_data.features) if plan_data.features else None
    
    new_plan = Plan(
        name=plan_data.name,
        display_name=plan_data.display_name,
        description=plan_data.description,
        price=plan_data.price,
        currency=plan_data.currency,
        max_users=plan_data.max_users,
        max_storage_gb=plan_data.max_storage_gb,
        features=features_str,
        is_active=True,
        is_system=False
    )
    
    db.add(new_plan)
    db.commit()
    db.refresh(new_plan)
    
    return new_plan


@router.put("/plans/{plan_id}", response_model=PlanResponse)
async def update_plan(
    plan_id: int,
    plan_data: PlanUpdateRequest,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """Update plan details (Master only)."""
    plan = db.query(Plan).filter(Plan.id == plan_id).first()
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan not found"
        )
    
    # Don't allow modifying system plans
    if plan.is_system:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot modify system plans"
        )
    
    # Update fields
    if plan_data.display_name:
        plan.display_name = plan_data.display_name
    
    if plan_data.description is not None:
        plan.description = plan_data.description
    
    if plan_data.price is not None:
        plan.price = plan_data.price
    
    if plan_data.max_users is not None:
        plan.max_users = plan_data.max_users
    
    if plan_data.max_storage_gb is not None:
        plan.max_storage_gb = plan_data.max_storage_gb
    
    if plan_data.features is not None:
        import json
        plan.features = json.dumps(plan_data.features)
    
    if plan_data.is_active is not None:
        plan.is_active = plan_data.is_active
    
    plan.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(plan)
    
    return plan


@router.delete("/plans/{plan_id}")
async def delete_plan(
    plan_id: int,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """Delete a plan (Master only)."""
    plan = db.query(Plan).filter(Plan.id == plan_id).first()
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan not found"
        )
    
    # Don't allow deleting system plans
    if plan.is_system:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete system plans"
        )
    
    # Check if plan has active subscriptions
    active_subscriptions = db.query(Subscription).filter(
        Subscription.plan_id == plan_id,
        Subscription.status.in_(["active", "trial"])
    ).count()
    
    if active_subscriptions > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete plan with {active_subscriptions} active subscriptions"
        )
    
    plan_name = plan.display_name
    db.delete(plan)
    db.commit()
    
    return {"message": f"Plan {plan_name} deleted successfully"}
