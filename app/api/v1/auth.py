from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from app.database import get_db
from app.models.user import User
from app.models.organization import Organization
from app.models.role import Role
from app.models.plan import Plan
from app.models.subscription import Subscription, SubscriptionStatus
from app.models.license import License
from app.core.security import (
    verify_password, get_password_hash,
    create_access_token, create_refresh_token, verify_token
)
from app.schemas.auth import (
    Token, UserRegister, UserResponse, RefreshTokenRequest, 
    UserSelfUpdateRequest, UserProfileUpdate, PasswordChangeRequest,
    OrganizationSelection, OrganizationSelectionRequest
)
from app.models.user_organization_association import UserOrganizationAssociation
from app.dependencies.auth import get_current_user
from app.config import settings

router = APIRouter()


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    """Authenticate user with email and password."""
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Login endpoint for OAuth2 password flow.
    
    Returns a list of organizations if user belongs to multiple organizations.
    Client should then call /select-organization with the chosen organization_id.
    """
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    # Update last login
    login_time = datetime.now(timezone.utc)
    user.last_login_at = login_time
    try:
        db.commit()
        db.refresh(user)
        if user.last_login_at != login_time:
            db.rollback()
            db.query(User).filter(User.id == user.id).update({"last_login_at": login_time})
            db.commit()
            db.refresh(user)
    except Exception as e:
        db.rollback()
        raise e
    
    # Get all organizations the user belongs to
    user_orgs = db.query(UserOrganizationAssociation).filter(
        UserOrganizationAssociation.user_id == user.id
    ).all()
    
    if not user_orgs:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with any organization"
        )
    
    # Determine which organization to use
    selected_assoc = None
    
    # If user has multiple organizations, select the last used one (if exists and still accessible)
    if len(user_orgs) > 1 and user.last_organization_id:
        # Try to use the last organization if user still has access
        for assoc in user_orgs:
            if assoc.organization_id == user.last_organization_id:
                selected_assoc = assoc
                break
    
    # If no last organization or not found, use the first one
    if selected_assoc is None:
        selected_assoc = user_orgs[0]
    
    # Get the role for the selected organization
    role = db.query(Role).filter(Role.id == selected_assoc.role_id).first()
    
    # Update last_organization_id for next time
    user.last_organization_id = selected_assoc.organization_id
    db.commit()
    
    # Generate full access and refresh tokens
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "organization_id": selected_assoc.organization_id,
            "role": role.name if role else "USER"
        },
        expires_delta=access_token_expires
    )
    
    refresh_token = create_refresh_token(
        data={
            "sub": str(user.id),
            "organization_id": selected_assoc.organization_id
        }
    )
    
    # If user has multiple organizations, include the list for easy switching
    available_orgs = []
    if len(user_orgs) > 1:
        for assoc in user_orgs:
            org = db.query(Organization).filter(Organization.id == assoc.organization_id).first()
            role_obj = db.query(Role).filter(Role.id == assoc.role_id).first()
            if org and role_obj:
                available_orgs.append(OrganizationSelection(
                    id=org.id,
                    name=org.name,
                    cnpj_cpf=org.cnpj_cpf,
                    role_name=role_obj.name
                ))
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        requires_org_selection=False,
        available_organizations=available_orgs
    )


@router.post("/select-organization", response_model=Token)
async def select_organization(
    org_selection: OrganizationSelectionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Select an organization after initial authentication.
    
    This endpoint should be called after /token returns requires_org_selection=True.
    """
    # Verify user has access to the selected organization
    assoc = db.query(UserOrganizationAssociation).filter(
        UserOrganizationAssociation.user_id == current_user.id,
        UserOrganizationAssociation.organization_id == org_selection.organization_id
    ).first()
    
    if not assoc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not have access to this organization"
        )
    
    # Get the role for this organization
    role = db.query(Role).filter(Role.id == assoc.role_id).first()
    
    # Update last_organization_id for next login
    current_user.last_organization_id = org_selection.organization_id
    db.commit()
    
    # Create full access tokens with organization context
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={
            "sub": str(current_user.id),
            "organization_id": org_selection.organization_id,
            "role": role.name if role else "USER"
        },
        expires_delta=access_token_expires
    )
    
    refresh_token = create_refresh_token(
        data={
            "sub": str(current_user.id),
            "organization_id": org_selection.organization_id
        }
    )
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        requires_org_selection=False,
        available_organizations=[]
    )


@router.post("/register", response_model=Token)
async def register_new_organization(
    user_data: UserRegister,
    db: Session = Depends(get_db)
):
    """Register a new organization and admin user."""
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Check if CNPJ/CPF already exists
    existing_cnpj = db.query(Organization).filter(Organization.cnpj_cpf == user_data.cnpj_cpf).first()
    if existing_cnpj:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CNPJ/CPF already registered"
        )
    
    # Check if organization slug already exists
    import re
    slug = re.sub(r'[^a-zA-Z0-9\-]', '', user_data.organization_name.lower().replace(' ', '-'))
    existing_org = db.query(Organization).filter(Organization.slug == slug).first()
    if existing_org:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization name already taken"
        )
    
    # Get default plan (Trial)
    trial_plan = db.query(Plan).filter(Plan.name == "TRIAL").first()
    if not trial_plan:
        # Create trial plan if it doesn't exist
        trial_plan = Plan(
            name="TRIAL",
            display_name="Trial",
            description="Free trial plan",
            price=0.00,
            max_users=5,
            is_system=True
        )
        db.add(trial_plan)
        db.commit()
        db.refresh(trial_plan)
    
    # Get ADMIN role
    admin_role = db.query(Role).filter(Role.name == "ADMIN").first()
    if not admin_role:
        # Create ADMIN role if it doesn't exist
        admin_role = Role(
            name="ADMIN",
            display_name="Administrator",
            description="Full access to organization",
            is_system=True
        )
        db.add(admin_role)
        db.commit()
        db.refresh(admin_role)
    
    # Create organization
    organization = Organization(
        name=user_data.organization_name,
        slug=slug,
        cnpj_cpf=user_data.cnpj_cpf,
        email=user_data.email
    )
    db.add(organization)
    db.commit()
    db.refresh(organization)
    
    # Create subscription
    now = datetime.utcnow()
    trial_end = now + timedelta(days=30)  # 30 days trial
    subscription = Subscription(
        organization_id=organization.id,
        plan_id=trial_plan.id,
        status=SubscriptionStatus.TRIAL,
        current_period_start=now,
        current_period_end=trial_end,
        trial_end=trial_end
    )
    db.add(subscription)
    db.commit()
    
    # Create admin user
    hashed_password = get_password_hash(user_data.password)
    admin_user = User(
        email=user_data.email,
        full_name=user_data.full_name,
        hashed_password=hashed_password,
        is_verified=True  # Auto-verify for registration
    )
    db.add(admin_user)
    db.commit()
    db.refresh(admin_user)
    
    # Create user-organization association
    user_org_assoc = UserOrganizationAssociation(
        user_id=admin_user.id,
        organization_id=organization.id,
        role_id=admin_role.id
    )
    db.add(user_org_assoc)
    db.commit()
    
    # Create initial licenses
    for i in range(trial_plan.max_users):
        license_obj = License(
            organization_id=organization.id,
            user_id=admin_user.id if i == 0 else None,  # First license for admin
            status="active" if i == 0 else "inactive"
        )
        db.add(license_obj)
    
    db.commit()
    
    # Create tokens for the new admin user
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={
            "sub": str(admin_user.id),
            "organization_id": organization.id,
            "role": admin_role.name
        },
        expires_delta=access_token_expires
    )
    
    refresh_token = create_refresh_token(
        data={
            "sub": str(admin_user.id),
            "organization_id": organization.id
        }
    )
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        requires_org_selection=False,
        available_organizations=[]
    )


@router.post("/refresh", response_model=Token)
async def refresh_access_token(
    refresh_data: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """Refresh access token using refresh token."""
    payload = verify_token(refresh_data.refresh_token, "refresh")
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    user_id = payload.get("sub")
    organization_id = payload.get("organization_id")
    
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    # Verify user still has access to this organization
    assoc = db.query(UserOrganizationAssociation).filter(
        UserOrganizationAssociation.user_id == user.id,
        UserOrganizationAssociation.organization_id == organization_id
    ).first()
    
    if not assoc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User no longer has access to this organization"
        )
    
    role = db.query(Role).filter(Role.id == assoc.role_id).first()
    
    # Create new access token
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "organization_id": organization_id,
            "role": role.name if role else "USER"
        },
        expires_delta=access_token_expires
    )
    
    # Create new refresh token
    refresh_token = create_refresh_token(
        data={
            "sub": str(user.id),
            "organization_id": organization_id
        }
    )
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        requires_org_selection=False,
        available_organizations=[]
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user information with current session context."""
    # Extract organization_id from token
    authorization = request.headers.get("Authorization", "")
    current_org_id = None
    current_role_name = None
    current_org_name = None
    
    if authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
        try:
            payload = verify_token(token, "access")
            if payload:
                current_org_id = payload.get("organization_id")
                current_role_name = payload.get("role")
                
                if current_org_id:
                    org = db.query(Organization).filter(Organization.id == current_org_id).first()
                    if org:
                        current_org_name = org.name
        except:
            pass
    
    # Get all organizations the user belongs to
    user_orgs = db.query(UserOrganizationAssociation).filter(
        UserOrganizationAssociation.user_id == current_user.id
    ).all()
    
    organizations_list = []
    is_system_admin = False
    
    for assoc in user_orgs:
        org = db.query(Organization).filter(Organization.id == assoc.organization_id).first()
        role = db.query(Role).filter(Role.id == assoc.role_id).first()
        if org and role:
            organizations_list.append(OrganizationSelection(
                id=org.id,
                name=org.name,
                cnpj_cpf=org.cnpj_cpf,
                role_name=role.name
            ))
            # Check if user has ADMINISTRATOR role in any organization
            if role.name == "ADMINISTRATOR":
                is_system_admin = True
    
    response_data = {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "is_active": current_user.is_active,
        "is_verified": current_user.is_verified,
        "profile_image_url": current_user.profile_image_url,
        "phone": current_user.phone,
        "bio": current_user.bio,
        "created_at": current_user.created_at,
        "last_login_at": current_user.last_login_at,
        "current_organization_id": current_org_id,
        "current_role_name": current_role_name,
        "current_organization_name": current_org_name,
        "organizations": organizations_list,
        "is_system_admin": is_system_admin
    }
    
    return UserResponse(**response_data)


@router.post("/test-update-login")
async def test_update_last_login(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Test endpoint to manually update last_login_at."""
    login_time = datetime.now(timezone.utc)
    current_user.last_login_at = login_time
    db.commit()
    db.refresh(current_user)
    return {
        "message": "Last login updated",
        "user_id": current_user.id,
        "last_login_at": current_user.last_login_at
    }


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_data: UserSelfUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update current user information."""
    # Update fields
    if user_data.full_name:
        current_user.full_name = user_data.full_name
    
    if user_data.phone is not None:
        current_user.phone = user_data.phone
    
    if user_data.password:
        current_user.hashed_password = get_password_hash(user_data.password)
    
    current_user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(current_user)
    
    return current_user


@router.put("/me/profile", response_model=UserResponse)
async def update_user_profile(
    request: Request,
    profile_data: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user profile with extended fields."""
    from app.utils.audit_logger import AuditLogger
    
    # Get current organization from token
    authorization = request.headers.get("Authorization", "")
    current_org_id = None
    
    if authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
        try:
            payload = verify_token(token, "access")
            if payload:
                current_org_id = payload.get("organization_id")
        except:
            pass
    
    # Track changes for audit
    changes = {}
    
    # Update fields
    if profile_data.full_name is not None:
        changes["full_name"] = {"old": current_user.full_name, "new": profile_data.full_name}
        current_user.full_name = profile_data.full_name
    
    if profile_data.email is not None:
        changes["email"] = {"old": current_user.email, "new": profile_data.email}
        current_user.email = profile_data.email
    
    if profile_data.phone is not None:
        current_user.phone = profile_data.phone
    
    if profile_data.bio is not None:
        current_user.bio = profile_data.bio
    
    if profile_data.profile_image_url is not None:
        current_user.profile_image_url = profile_data.profile_image_url
    
    current_user.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(current_user)
    
    # Log audit
    if current_org_id:
        AuditLogger.log_update(
            db=db,
            entity_type="User",
            entity_id=current_user.id,
            changes=changes,
            user_id=current_user.id,
            organization_id=current_org_id
        )
    
    # Return updated user info
    return await get_current_user_info(request, current_user, db)


@router.post("/switch-organization", response_model=Token)
async def switch_organization(
    org_selection: OrganizationSelectionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Switch to a different organization after authentication.
    
    This endpoint allows users with multiple organizations to switch between them.
    """
    # Verify user has access to the selected organization
    assoc = db.query(UserOrganizationAssociation).filter(
        UserOrganizationAssociation.user_id == current_user.id,
        UserOrganizationAssociation.organization_id == org_selection.organization_id
    ).first()
    
    if not assoc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not have access to this organization"
        )
    
    # Get the role for this organization
    role = db.query(Role).filter(Role.id == assoc.role_id).first()
    
    # Update last_organization_id for next login
    current_user.last_organization_id = org_selection.organization_id
    db.commit()
    
    # Create new access tokens with the new organization context
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={
            "sub": str(current_user.id),
            "organization_id": org_selection.organization_id,
            "role": role.name if role else "USER"
        },
        expires_delta=access_token_expires
    )
    
    refresh_token = create_refresh_token(
        data={
            "sub": str(current_user.id),
            "organization_id": org_selection.organization_id
        }
    )
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        requires_org_selection=False,
        available_organizations=[]
    )


@router.put("/me/password", response_model=dict)
async def change_password(
    request: Request,
    password_data: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Change user password."""
    from app.utils.audit_logger import AuditLogger
    
    # Get current organization from token
    authorization = request.headers.get("Authorization", "")
    current_org_id = None
    
    if authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
        try:
            payload = verify_token(token, "access")
            if payload:
                current_org_id = payload.get("organization_id")
        except:
            pass
    
    # Verify old password
    if not verify_password(password_data.old_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password"
        )
    
    # Validate new password strength (minimum 8 characters)
    if len(password_data.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long"
        )
    
    # Update password
    current_user.hashed_password = get_password_hash(password_data.new_password)
    current_user.updated_at = datetime.now(timezone.utc)
    db.commit()
    
    # Log audit
    if current_org_id:
        AuditLogger.log_update(
            db=db,
            entity_type="User",
            entity_id=current_user.id,
            changes={"action": "password_changed"},
            user_id=current_user.id,
            organization_id=current_org_id
        )
    
    return {"message": "Password changed successfully"}
