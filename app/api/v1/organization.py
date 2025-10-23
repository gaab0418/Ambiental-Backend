from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from app.database import get_db
from app.models.user import User
from app.models.organization import Organization
from app.models.role import Role
from app.models.license import License, LicenseStatus
from app.models.subscription import Subscription
from app.core.security import get_password_hash
from app.schemas.organization import (
    OrganizationResponse, UserInviteRequest, UserInviteResponse, RoleResponse,
    UserUpdateRequest, OrganizationUpdateRequest, UserRoleChangeRequest
)
from app.dependencies.auth import require_manager_or_admin

router = APIRouter()


@router.get("/me", response_model=OrganizationResponse)
async def get_organization_info(
    current_user: User = Depends(require_manager_or_admin),
    db: Session = Depends(get_db)
):
    """Get current organization information."""
    organization = db.query(Organization).filter(
        Organization.id == current_user.organization_id
    ).first()
    
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    return organization


@router.get("/users", response_model=List[UserInviteResponse])
async def get_organization_users(
    current_user: User = Depends(require_manager_or_admin),
    db: Session = Depends(get_db)
):
    """Get all users from the current organization."""
    users = db.query(User).filter(
        User.organization_id == current_user.organization_id
    ).all()
    
    return users


@router.get("/roles", response_model=List[RoleResponse])
async def get_available_roles(
    current_user: User = Depends(require_manager_or_admin),
    db: Session = Depends(get_db)
):
    """Get available roles for user assignment."""
    # Return all roles except SUPER_ADMIN (only super admins can assign that)
    roles = db.query(Role).filter(Role.name != "SUPER_ADMIN").all()
    return roles


@router.post("/users/invite", response_model=UserInviteResponse)
async def invite_user(
    user_data: UserInviteRequest,
    current_user: User = Depends(require_manager_or_admin),
    db: Session = Depends(get_db)
):
    """Invite a new user to the organization."""
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )
    
    # Check if role exists and is valid
    role = db.query(Role).filter(Role.id == user_data.role_id).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role"
        )
    
    # Check subscription and available licenses
    subscription = db.query(Subscription).filter(
        Subscription.organization_id == current_user.organization_id,
        Subscription.status.in_(["active", "trial"])
    ).first()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active subscription found"
        )
    
    # Check available licenses
    available_licenses = db.query(License).filter(
        License.organization_id == current_user.organization_id,
        License.status == LicenseStatus.INACTIVE,
        License.user_id.is_(None)
    ).count()
    
    if available_licenses == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No available licenses. Please purchase more licenses."
        )
    
    # Get an available license
    available_license = db.query(License).filter(
        License.organization_id == current_user.organization_id,
        License.status == LicenseStatus.INACTIVE,
        License.user_id.is_(None)
    ).first()
    
    # Create user with provided password (validated by schema)
    hashed_password = get_password_hash(user_data.password)
    
    new_user = User(
        email=user_data.email,
        full_name=user_data.full_name,
        hashed_password=hashed_password,
        organization_id=current_user.organization_id,
        role_id=user_data.role_id,
        is_verified=False  # User needs to verify email and set password
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Assign license to user
    available_license.user_id = new_user.id
    available_license.status = LicenseStatus.ACTIVE
    available_license.activated_at = datetime.utcnow()
    
    db.commit()
    
    # TODO: Send invitation email with verification link
    
    return new_user


@router.delete("/users/{user_id}")
async def remove_user(
    user_id: int,
    current_user: User = Depends(require_manager_or_admin),
    db: Session = Depends(get_db)
):
    """Remove a user from the organization."""
    # Check if user exists and belongs to the same organization
    user_to_remove = db.query(User).filter(
        User.id == user_id,
        User.organization_id == current_user.organization_id
    ).first()
    
    if not user_to_remove:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in this organization"
        )
    
    # Prevent removing yourself
    if user_to_remove.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove yourself"
        )
    
    # Find and deactivate user's license
    user_license = db.query(License).filter(
        License.organization_id == current_user.organization_id,
        License.user_id == user_id,
        License.status == LicenseStatus.ACTIVE
    ).first()
    
    if user_license:
        user_license.status = LicenseStatus.INACTIVE
        user_license.user_id = None
        user_license.deactivated_at = datetime.utcnow()
    
    # Deactivate user
    user_to_remove.is_active = False
    
    db.commit()
    
    return {"message": "User removed successfully"}


@router.put("/users/{user_id}/activate")
async def activate_user(
    user_id: int,
    current_user: User = Depends(require_manager_or_admin),
    db: Session = Depends(get_db)
):
    """Activate a user in the organization."""
    # Check if user exists and belongs to the same organization
    user_to_activate = db.query(User).filter(
        User.id == user_id,
        User.organization_id == current_user.organization_id
    ).first()
    
    if not user_to_activate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in this organization"
        )
    
    # Check if there's an available license
    available_license = db.query(License).filter(
        License.organization_id == current_user.organization_id,
        License.status == LicenseStatus.INACTIVE,
        License.user_id.is_(None)
    ).first()
    
    if not available_license:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No available licenses"
        )
    
    # Activate user
    user_to_activate.is_active = True
    
    # Assign license
    available_license.user_id = user_id
    available_license.status = LicenseStatus.ACTIVE
    available_license.activated_at = datetime.utcnow()
    
    db.commit()
    
    return {"message": "User activated successfully"}


@router.put("/me", response_model=OrganizationResponse)
async def update_organization_info(
    org_data: OrganizationUpdateRequest,
    current_user: User = Depends(require_manager_or_admin),
    db: Session = Depends(get_db)
):
    """Update organization information."""
    organization = db.query(Organization).filter(
        Organization.id == current_user.organization_id
    ).first()
    
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
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
    
    return organization


# Alias endpoints matching frontend expectations
@router.get("/me/users", response_model=List[UserInviteResponse])
async def get_organization_users_me(
    current_user: User = Depends(require_manager_or_admin),
    db: Session = Depends(get_db)
):
    """Get all users from the current organization (alias for /users)."""
    return await get_organization_users(current_user, db)


@router.post("/me/users/invite", response_model=UserInviteResponse)
async def invite_user_me(
    user_data: UserInviteRequest,
    current_user: User = Depends(require_manager_or_admin),
    db: Session = Depends(get_db)
):
    """Invite a new user to the organization (alias for /users/invite)."""
    return await invite_user(user_data, current_user, db)


@router.delete("/me/users/{user_id}")
async def remove_user_me(
    user_id: int,
    current_user: User = Depends(require_manager_or_admin),
    db: Session = Depends(get_db)
):
    """Remove a user from the organization (alias for /users/{user_id})."""
    return await remove_user(user_id, current_user, db)


@router.put("/me/users/{user_id}/role", response_model=UserInviteResponse)
async def change_user_role(
    user_id: int,
    role_data: UserRoleChangeRequest,
    current_user: User = Depends(require_manager_or_admin),
    db: Session = Depends(get_db)
):
    """Change a user's role within the organization."""
    # Check if user exists and belongs to the same organization
    user_to_update = db.query(User).filter(
        User.id == user_id,
        User.organization_id == current_user.organization_id
    ).first()
    
    if not user_to_update:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in this organization"
        )
    
    # Prevent changing own role
    if user_to_update.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change your own role"
        )
    
    # Validate role exists
    role = db.query(Role).filter(Role.id == role_data.role_id).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role"
        )
    
    # Don't allow assigning SUPER_ADMIN or ADMINISTRATOR
    if role.name in ["SUPER_ADMIN", "ADMINISTRATOR"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot assign system-level roles"
        )
    
    # Update role
    user_to_update.role_id = role_data.role_id
    db.commit()
    db.refresh(user_to_update)
    
    return user_to_update
