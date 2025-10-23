from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db
from app.models.document_template import DocumentTemplate
from app.models.user import User
from app.schemas.template import TemplateCreate, TemplateUpdate, TemplateResponse
from app.dependencies.auth import get_current_active_user, require_consultant, require_administrator
from app.utils.audit_logger import AuditLogger

router = APIRouter()


@router.get("", response_model=dict)
async def get_templates(
    is_global: Optional[str] = Query(None),
    is_active: Optional[str] = Query("true"),
    organization_id: Optional[str] = Query(None),
    created_by_user_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get templates with filters and pagination."""
    
    query = db.query(DocumentTemplate)
    
    # Parse is_global from string
    is_global_bool = None
    if is_global is not None:
        is_global_bool = is_global.lower() in ('true', '1', 'yes')
    
    # Parse is_active from string
    is_active_bool = None
    if is_active is not None:
        is_active_bool = is_active.lower() in ('true', '1', 'yes')
    
    # Parse organization_id - accept 'me' or numeric
    org_id_filter = None
    if organization_id:
        if organization_id.lower() == 'me':
            org_id_filter = current_user.organization_id
        else:
            try:
                org_id_filter = int(organization_id)
                # Check permission if accessing another org's data
                if org_id_filter != current_user.organization_id:
                    if current_user.role.name not in ["CONSULTANT", "ADMINISTRATOR"]:
                        raise HTTPException(
                            status_code=403,
                            detail="Not authorized to access other organization's templates"
                        )
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid organization_id")
    
    # Parse created_by_user_id - accept 'me' or numeric
    user_id_filter = None
    if created_by_user_id:
        if created_by_user_id.lower() == 'me':
            user_id_filter = current_user.id
        else:
            try:
                user_id_filter = int(created_by_user_id)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid created_by_user_id")
    
    # Apply filters
    if is_global_bool is not None:
        query = query.filter(DocumentTemplate.is_global == is_global_bool)
    
    if is_active_bool is not None:
        query = query.filter(DocumentTemplate.is_active == is_active_bool)
    
    if org_id_filter:
        query = query.filter(DocumentTemplate.organization_id == org_id_filter)
    elif not is_global_bool:
        # If not filtering for global templates, show user's organization templates + global
        query = query.filter(
            (DocumentTemplate.organization_id == current_user.organization_id) |
            (DocumentTemplate.is_global == True)
        )
    
    if user_id_filter:
        query = query.filter(DocumentTemplate.created_by_user_id == user_id_filter)
    
    # Get total count
    total = query.count()
    
    # Get paginated results
    templates = query.order_by(DocumentTemplate.created_at.desc()).offset(offset).limit(limit).all()
    
    # Convert to response format
    templates_data = []
    for template in templates:
        template_dict = {
            "id": template.id,
            "name": template.name,
            "description": template.description,
            "content": template.content,
            "created_by_user_id": template.created_by_user_id,
            "organization_id": template.organization_id,
            "is_global": template.is_global,
            "is_active": template.is_active,
            "created_at": template.created_at.isoformat() if template.created_at else None,
            "updated_at": template.updated_at.isoformat() if template.updated_at else None,
        }
        
        # Add related data
        if template.created_by_user:
            template_dict["created_by_user_name"] = template.created_by_user.full_name
        
        if template.organization:
            template_dict["organization_name"] = template.organization.name
        
        templates_data.append(template_dict)
    
    return {
        "templates": templates_data,
        "total": total,
        "limit": limit,
        "offset": offset
    }


@router.get("/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get template by ID."""
    
    template = db.query(DocumentTemplate).filter(DocumentTemplate.id == template_id).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Check access permissions
    if not template.is_global and template.organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Not authorized to access this template")
    
    return template


@router.post("", response_model=TemplateResponse)
async def create_template(
    template_data: TemplateCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create new template (CONSULTANT+ can create global templates)."""
    
    # Check if user can create global templates
    if template_data.is_global and current_user.role.name not in ["CONSULTANT", "ADMINISTRATOR"]:
        raise HTTPException(
            status_code=403,
            detail="Only CONSULTANT and ADMINISTRATOR can create global templates"
        )
    
    # Create template
    template = DocumentTemplate(
        name=template_data.name,
        description=template_data.description,
        content=template_data.content,
        created_by_user_id=current_user.id,
        organization_id=None if template_data.is_global else current_user.organization_id,
        is_global=template_data.is_global,
        is_active=True
    )
    
    db.add(template)
    db.commit()
    db.refresh(template)
    
    # Log audit
    AuditLogger.log_create(
        db=db,
        entity_type="DocumentTemplate",
        entity_id=template.id,
        user_id=current_user.id,
        organization_id=current_user.organization_id,
        changes={"name": template.name, "is_global": template.is_global}
    )
    
    return template


@router.put("/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: int,
    template_data: TemplateUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update template (creator or CONSULTANT+)."""
    
    template = db.query(DocumentTemplate).filter(DocumentTemplate.id == template_id).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Check permissions
    is_creator = template.created_by_user_id == current_user.id
    is_consultant_or_admin = current_user.role.name in ["CONSULTANT", "ADMINISTRATOR"]
    
    if not (is_creator or is_consultant_or_admin):
        raise HTTPException(status_code=403, detail="Not authorized to update this template")
    
    # Track changes for audit
    changes = {}
    
    # Update fields
    if template_data.name is not None:
        changes["name"] = {"old": template.name, "new": template_data.name}
        template.name = template_data.name
    
    if template_data.description is not None:
        template.description = template_data.description
    
    if template_data.content is not None:
        template.content = template_data.content
    
    if template_data.is_active is not None:
        changes["is_active"] = {"old": template.is_active, "new": template_data.is_active}
        template.is_active = template_data.is_active
    
    db.commit()
    db.refresh(template)
    
    # Log audit
    AuditLogger.log_update(
        db=db,
        entity_type="DocumentTemplate",
        entity_id=template.id,
        changes=changes,
        user_id=current_user.id,
        organization_id=current_user.organization_id
    )
    
    return template


@router.delete("/{template_id}")
async def delete_template(
    template_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete template (creator or ADMINISTRATOR)."""
    
    template = db.query(DocumentTemplate).filter(DocumentTemplate.id == template_id).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Check permissions
    is_creator = template.created_by_user_id == current_user.id
    is_administrator = current_user.role.name == "ADMINISTRATOR"
    
    if not (is_creator or is_administrator):
        raise HTTPException(status_code=403, detail="Not authorized to delete this template")
    
    # Log audit before deletion
    AuditLogger.log_delete(
        db=db,
        entity_type="DocumentTemplate",
        entity_id=template.id,
        user_id=current_user.id,
        organization_id=current_user.organization_id,
        changes={"name": template.name, "is_global": template.is_global}
    )
    
    db.delete(template)
    db.commit()
    
    return {"message": "Template deleted successfully"}



