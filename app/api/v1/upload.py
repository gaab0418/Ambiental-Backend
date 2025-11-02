from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Request
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.dependencies.auth import get_current_active_user, get_organization_from_token
from app.models.user_organization_association import UserOrganizationAssociation
from app.models.role import Role
from app.utils.file_upload import FileUploadUtils

router = APIRouter()


@router.post("/profile-image")
async def upload_profile_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Upload profile image (authenticated users)."""
    
    try:
        # Save file using the correct method
        file_url = await FileUploadUtils.save_profile_image(file)
        
        # Update user profile
        current_user.profile_image_url = file_url
        db.commit()
        db.refresh(current_user)
        
        return {
            "url": file_url,
            "filename": file.filename
        }
    
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading file: {str(e)}")


@router.post("/organization-logo")
async def upload_organization_logo(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Upload organization logo (authenticated users)."""
    from app.models.organization import Organization
    
    # Get organization_id from token
    current_org_id = get_organization_from_token(request)
    if not current_org_id:
        raise HTTPException(
            status_code=400,
            detail="Organization context required"
        )
    
    # Verify user has access to this organization
    user_assoc = db.query(UserOrganizationAssociation).filter(
        UserOrganizationAssociation.user_id == current_user.id,
        UserOrganizationAssociation.organization_id == current_org_id
    ).first()
    
    if not user_assoc:
        raise HTTPException(
            status_code=403,
            detail="Not authorized"
        )
    
    # Check role permissions
    role = db.query(Role).filter(Role.id == user_assoc.role_id).first()
    if not role or role.name not in ["MANAGER", "ADMIN", "ADMINISTRATOR"]:
        raise HTTPException(
            status_code=403,
            detail="Only MANAGER and ADMINISTRATOR can upload organization logo"
        )
    
    try:
        # Save file using the correct method
        file_url = await FileUploadUtils.save_logo(file)
        
        # Update organization logo
        organization = db.query(Organization).filter(
            Organization.id == current_org_id
        ).first()
        
        if organization:
            organization.logo_url = file_url
            db.commit()
        
        return {
            "url": file_url,
            "filename": file.filename
        }
    
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading file: {str(e)}")



