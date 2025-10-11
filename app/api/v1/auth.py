from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
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
from app.schemas.auth import Token, UserRegister, UserResponse, RefreshTokenRequest
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
    user.last_login_at = datetime.utcnow()
    db.commit()
    
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
    current_user: User = Depends(get_current_user)
):
    """Get current user information."""
    return current_user
