from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.dependencies.auth import get_current_active_user
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
        # Save file
        file_url = FileUploadUtils.save_uploaded_file(
            file=file,
            file_type="profile",
            user_id=current_user.id
        )
        
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
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Upload organization logo (authenticated users)."""
    
    # Check if user has permission to update organization
    if current_user.role.name not in ["MANAGER", "ADMINISTRATOR"]:
        raise HTTPException(
            status_code=403,
            detail="Only MANAGER and ADMINISTRATOR can upload organization logo"
        )
    
    try:
        # Save file
        file_url = FileUploadUtils.save_uploaded_file(
            file=file,
            file_type="logo",
            org_id=current_user.organization_id
        )
        
        return {
            "url": file_url,
            "filename": file.filename
        }
    
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading file: {str(e)}")



