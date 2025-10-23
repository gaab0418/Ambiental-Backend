from fastapi import APIRouter, Depends, HTTPException, status
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
from app.schemas.auth import Token, UserRegister, UserResponse, RefreshTokenRequest, UserSelfUpdateRequest, UserProfileUpdate, PasswordChangeRequest
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
    """Login endpoint for OAuth2 password flow."""
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
        # Verify the update
        if user.last_login_at != login_time:
            db.rollback()
            # Try alternative approach
            db.query(User).filter(User.id == user.id).update({"last_login_at": login_time})
            db.commit()
            db.refresh(user)
    except Exception as e:
        db.rollback()
        raise e
    
    # Create tokens
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "organization_id": user.organization_id,
            "role": user.role.name
        },
        expires_delta=access_token_expires
    )
    
    refresh_token = create_refresh_token(
        data={
            "sub": str(user.id),
            "organization_id": user.organization_id
        }
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


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
        organization_id=organization.id,
        role_id=admin_role.id,
        is_verified=True  # Auto-verify for registration
    )
    db.add(admin_user)
    db.commit()
    db.refresh(admin_user)
    
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
            "organization_id": admin_user.organization_id,
            "role": admin_role.name
        },
        expires_delta=access_token_expires
    )
    
    refresh_token = create_refresh_token(
        data={
            "sub": str(admin_user.id),
            "organization_id": admin_user.organization_id
        }
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


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
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    # Create new access token
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "organization_id": user.organization_id,
            "role": user.role.name
        },
        expires_delta=access_token_expires
    )
    
    # Create new refresh token
    refresh_token = create_refresh_token(
        data={
            "sub": str(user.id),
            "organization_id": user.organization_id
        }
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user information."""
    # Load related data
    user_with_relations = db.query(User).filter(User.id == current_user.id).first()
    
    # Create response with populated fields
    response_data = {
        "id": user_with_relations.id,
        "email": user_with_relations.email,
        "full_name": user_with_relations.full_name,
        "is_active": user_with_relations.is_active,
        "is_verified": user_with_relations.is_verified,
        "organization_id": user_with_relations.organization_id,
        "role_id": user_with_relations.role_id,
        "profile_image_url": user_with_relations.profile_image_url,
        "phone": user_with_relations.phone,
        "bio": user_with_relations.bio,
        "created_at": user_with_relations.created_at,
        "last_login_at": user_with_relations.last_login_at,
        "role_name": user_with_relations.role.name if user_with_relations.role else None,
        "organization_name": user_with_relations.organization.name if user_with_relations.organization else None
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
    profile_data: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user profile with extended fields."""
    from app.utils.audit_logger import AuditLogger
    
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
    AuditLogger.log_update(
        db=db,
        entity_type="User",
        entity_id=current_user.id,
        changes=changes,
        user_id=current_user.id,
        organization_id=current_user.organization_id
    )
    
    return current_user


@router.put("/me/password", response_model=dict)
async def change_password(
    password_data: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Change user password."""
    from app.utils.audit_logger import AuditLogger
    
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
    AuditLogger.log_update(
        db=db,
        entity_type="User",
        entity_id=current_user.id,
        changes={"action": "password_changed"},
        user_id=current_user.id,
        organization_id=current_user.organization_id
    )
    
    return {"message": "Password changed successfully"}
