from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from typing import Optional, Tuple
from app.database import get_db
from app.models.user import User
from app.core.security import verify_token
from app.schemas.auth import TokenData

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/token")


def get_organization_from_token(request: Request) -> Optional[int]:
    """Extract organization_id from the JWT token in the request."""
    try:
        authorization = request.headers.get("Authorization", "")
        if not authorization.startswith("Bearer "):
            return None
        
        token = authorization.split(" ")[1]
        payload = verify_token(token, "access")
        
        if payload:
            return payload.get("organization_id")
        return None
    except Exception:
        return None


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    payload = verify_token(token, "access")
    if payload is None:
        raise credentials_exception
    
    user_id: str = payload.get("sub")
    if user_id is None:
        raise credentials_exception
    
    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current active user."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user


def require_role(required_roles: list[str]):
    """Dependency factory for role-based access control.
    
    NOTE: Checks if user has ANY of the required roles in ANY organization.
    """
    def role_checker(current_user: User = Depends(get_current_active_user)) -> User:
        from app.models.user_organization_association import UserOrganizationAssociation
        from app.models.role import Role
        from app.database import SessionLocal
        
        db = SessionLocal()
        try:
            user_orgs = db.query(UserOrganizationAssociation).filter(
                UserOrganizationAssociation.user_id == current_user.id
            ).all()
            
            for assoc in user_orgs:
                role = db.query(Role).filter(Role.id == assoc.role_id).first()
                if role and role.name in required_roles:
                    return current_user
            
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
        finally:
            db.close()
    return role_checker


def require_admin_role(current_user: User = Depends(get_current_active_user)) -> User:
    """Require admin role.
    
    NOTE: This function checks if user has admin role in ANY organization.
    For organization-specific role checks, verify role through UserOrganizationAssociation
    in the endpoint itself using get_organization_from_token().
    """
    # Check if user has admin role in at least one organization
    from app.models.user_organization_association import UserOrganizationAssociation
    from app.models.role import Role
    from app.database import SessionLocal
    
    db = SessionLocal()
    try:
        user_orgs = db.query(UserOrganizationAssociation).filter(
            UserOrganizationAssociation.user_id == current_user.id
        ).all()
        
        for assoc in user_orgs:
            role = db.query(Role).filter(Role.id == assoc.role_id).first()
            if role and role.name in ["ADMIN", "ADMINISTRATOR", "MANAGER"]:
                return current_user
        
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required"
        )
    finally:
        db.close()


def require_manager_or_admin(current_user: User = Depends(get_current_active_user)) -> User:
    """Require manager or admin role.
    
    NOTE: Checks if user has manager/admin role in ANY organization.
    """
    from app.models.user_organization_association import UserOrganizationAssociation
    from app.models.role import Role
    from app.database import SessionLocal
    
    db = SessionLocal()
    try:
        user_orgs = db.query(UserOrganizationAssociation).filter(
            UserOrganizationAssociation.user_id == current_user.id
        ).all()
        
        for assoc in user_orgs:
            role = db.query(Role).filter(Role.id == assoc.role_id).first()
            if role and role.name in ["ADMIN", "MANAGER", "ADMINISTRATOR"]:
                return current_user
        
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Manager or Admin role required"
        )
    finally:
        db.close()


def require_super_admin(current_user: User = Depends(get_current_active_user)) -> User:
    """Require system administrator role.
    
    NOTE: Checks if user has ADMINISTRATOR role in ANY organization.
    """
    from app.models.user_organization_association import UserOrganizationAssociation
    from app.models.role import Role
    from app.database import SessionLocal
    
    db = SessionLocal()
    try:
        user_orgs = db.query(UserOrganizationAssociation).filter(
            UserOrganizationAssociation.user_id == current_user.id
        ).all()
        
        for assoc in user_orgs:
            role = db.query(Role).filter(Role.id == assoc.role_id).first()
            if role and role.name == "ADMINISTRATOR":
                return current_user
        
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="System Administrator role required"
        )
    finally:
        db.close()


async def get_current_user_optional(request: Request, db: Session = Depends(get_db)) -> Optional[User]:
    """Get current user if authenticated, otherwise return None."""
    try:
        # Extract token from Authorization header
        authorization = request.headers.get("Authorization")
        if not authorization or not authorization.startswith("Bearer "):
            return None
        
        token = authorization.split(" ")[1]
        
        payload = verify_token(token, "access")
        if payload is None:
            return None
        
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
        
        user = db.query(User).filter(User.id == int(user_id)).first()
        if user is None or not user.is_active:
            return None
        
        return user
    except Exception:
        return None


def require_consultant(current_user: User = Depends(get_current_active_user)) -> User:
    """Require consultant role.
    
    NOTE: Checks if user has CONSULTANT role in ANY organization.
    """
    from app.models.user_organization_association import UserOrganizationAssociation
    from app.models.role import Role
    from app.database import SessionLocal
    
    db = SessionLocal()
    try:
        user_orgs = db.query(UserOrganizationAssociation).filter(
            UserOrganizationAssociation.user_id == current_user.id
        ).all()
        
        for assoc in user_orgs:
            role = db.query(Role).filter(Role.id == assoc.role_id).first()
            if role and role.name in ["CONSULTANT", "ADMINISTRATOR"]:
                return current_user
        
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Consultant role required"
        )
    finally:
        db.close()


def require_manager_or_consultant(current_user: User = Depends(get_current_active_user)) -> User:
    """Require manager or consultant role.
    
    NOTE: Checks if user has manager/consultant role in ANY organization.
    """
    from app.models.user_organization_association import UserOrganizationAssociation
    from app.models.role import Role
    from app.database import SessionLocal
    
    db = SessionLocal()
    try:
        user_orgs = db.query(UserOrganizationAssociation).filter(
            UserOrganizationAssociation.user_id == current_user.id
        ).all()
        
        for assoc in user_orgs:
            role = db.query(Role).filter(Role.id == assoc.role_id).first()
            if role and role.name in ["MANAGER", "CONSULTANT", "ADMINISTRATOR"]:
                return current_user
        
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Manager or Consultant role required"
        )
    finally:
        db.close()


def require_administrator(current_user: User = Depends(get_current_active_user)) -> User:
    """Require administrator role.
    
    NOTE: Checks if user has ADMINISTRATOR role in ANY organization.
    """
    from app.models.user_organization_association import UserOrganizationAssociation
    from app.models.role import Role
    from app.database import SessionLocal
    
    db = SessionLocal()
    try:
        user_orgs = db.query(UserOrganizationAssociation).filter(
            UserOrganizationAssociation.user_id == current_user.id
        ).all()
        
        for assoc in user_orgs:
            role = db.query(Role).filter(Role.id == assoc.role_id).first()
            if role and role.name == "ADMINISTRATOR":
                return current_user
        
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator role required"
        )
    finally:
        db.close()


def require_role_in_current_org(required_roles: list[str]):
    """Dependency factory for organization-specific role-based access control.
    
    Validates that the user has one of the required roles in the CURRENT organization
    from the JWT token. ADMINISTRATOR role always has access regardless of organization.
    
    Args:
        required_roles: List of role names (e.g., ['MANAGER', 'ADMIN'])
    
    Returns:
        Dependency function that checks organization-specific role
    """
    def checker(request: Request, current_user: User = Depends(get_current_active_user)) -> User:
        from app.models.user_organization_association import UserOrganizationAssociation
        from app.models.role import Role
        from app.database import SessionLocal
        
        # Get organization ID from token
        org_id = get_organization_from_token(request)
        if not org_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Organization context required"
            )
        
        db = SessionLocal()
        try:
            # Find user's role in this specific organization
            assoc = db.query(UserOrganizationAssociation).filter(
                UserOrganizationAssociation.user_id == current_user.id,
                UserOrganizationAssociation.organization_id == org_id
            ).first()
            
            if not assoc:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not a member of this organization"
                )
            
            role = db.query(Role).filter(Role.id == assoc.role_id).first()
            
            # Check if user has one of the required roles or is ADMINISTRATOR
            if role and (role.name in required_roles or role.name == "ADMINISTRATOR"):
                return current_user
            
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions in this organization. Required: {', '.join(required_roles)}"
            )
        finally:
            db.close()
    
    return checker


async def get_current_user_with_org(
    request: Request,
    current_user: User = Depends(get_current_active_user)
) -> Tuple[User, Optional[int]]:
    """Get current user and their current organization ID from token."""
    org_id = get_organization_from_token(request)
    return (current_user, org_id)
