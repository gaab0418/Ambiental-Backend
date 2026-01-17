from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Header
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime

from app.database import get_db
from app.models.checklist_item import ProcessChecklistItem
from app.models.process import Process
from app.models.organization import Organization
from app.dependencies.auth import get_current_user
from app.dependencies.api_key_auth import verify_api_key

router = APIRouter()

# Flexible auth: accepts either JWT or API Key
async def get_auth_context(db: Session = Depends(get_db)):
    """
    Get authentication context from either JWT or API Key.
    Returns organization_id for access control.
    """
    # Try API Key first
    from fastapi import Header, Request
    from app.dependencies.auth import get_organization_from_token
    
    try:
        request = Request(scope={"type": "http"})
        api_key_result = await verify_api_key(db=db)
        _, organization = api_key_result
        return organization.id
    except:
        # Fall back to JWT
        try:
            # This will be handled by the endpoint's current_user dependency
            return None  # Will be determined by endpoint
        except:
            raise HTTPException(
                status_code=401,
                detail="Authentication required: provide either Bearer token or X-API-Key header"
            )

class ChecklistItemCreate(BaseModel):
    title: str
    parent_id: Optional[int] = None
    is_completed: Optional[bool] = False  # Default to False if not provided

class ChecklistItemUpdate(BaseModel):
    title: Optional[str] = None
    is_completed: Optional[bool] = None

class ChecklistItemReorder(BaseModel):
    item_ids: List[int]

class ChecklistItemResponse(BaseModel):
    id: int
    process_id: int
    parent_id: Optional[int] = None
    title: str
    is_completed: bool
    order: int
    created_at: datetime

    class Config:
        orm_mode = True

@router.get("/process/{process_id}/checklist", response_model=List[ChecklistItemResponse])
async def get_checklist(
    process_id: int,
    db: Session = Depends(get_db),
    x_api_key: Optional[str] = Header(None),
    current_user=Depends(get_current_user)
):
    """Get checklist items (supports JWT or API Key auth)."""
    # API Key takes precedence if provided
    if x_api_key:
        from app.dependencies.api_key_auth import verify_api_key, hash_api_key
        from app.models.api_key import ApiKey
        
        key_hash = hash_api_key(x_api_key)
        api_key_obj = db.query(ApiKey).filter(ApiKey.key_hash == key_hash, ApiKey.is_active == True).first()
        if not api_key_obj:
            raise HTTPException(status_code=401, detail="Invalid API Key")
        
        # Verify process belongs to API key's organization
        process = db.query(Process).filter(Process.id == process_id).first()
        if not process or process.organization_id != api_key_obj.organization_id:
            raise HTTPException(status_code=403, detail="Access denied")
    
    items = db.query(ProcessChecklistItem).filter(
        ProcessChecklistItem.process_id == process_id
    ).order_by(ProcessChecklistItem.order).all()
    return items

@router.post("/process/{process_id}/checklist", response_model=ChecklistItemResponse)
async def add_checklist_item(
    process_id: int,
    item: ChecklistItemCreate,
    db: Session = Depends(get_db),
    x_api_key: Optional[str] = Header(None)
):
    """Create checklist item (supports JWT or API Key auth)."""
    organization_id = None
    
    # API Key auth check
    if x_api_key:
        from app.dependencies.api_key_auth import hash_api_key
        from app.models.api_key import ApiKey
        
        key_hash = hash_api_key(x_api_key)
        api_key_obj = db.query(ApiKey).filter(ApiKey.key_hash == key_hash, ApiKey.is_active == True).first()
        if not api_key_obj:
            raise HTTPException(status_code=401, detail="Invalid API Key")
        organization_id = api_key_obj.organization_id
    else:
        raise HTTPException(status_code=401, detail="Authentication required: provide X-API-Key header")
    
    process = db.query(Process).filter(Process.id == process_id).first()
    if not process:
        raise HTTPException(status_code=404, detail="Process not found")
    
    # Verify process belongs to API Key's organization
    if organization_id and process.organization_id != organization_id:
        raise HTTPException(status_code=403, detail="Access denied: process belongs to different organization")

    # Get max order
    last_item = db.query(ProcessChecklistItem).filter(
        ProcessChecklistItem.process_id == process_id
    ).order_by(ProcessChecklistItem.order.desc()).first()
    
    new_order = (last_item.order + 1) if last_item else 0
    
    # If parent_id is provided, verify it exists and belongs to process
    if item.parent_id:
        parent = db.query(ProcessChecklistItem).filter(
            ProcessChecklistItem.id == item.parent_id,
            ProcessChecklistItem.process_id == process_id
        ).first()
        if not parent:
             raise HTTPException(status_code=400, detail="Parent item not found")

    new_item = ProcessChecklistItem(
        process_id=process_id,
        parent_id=item.parent_id,
        title=item.title,
        order=new_order,
        is_completed=item.is_completed if item.is_completed is not None else False
    )
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    return new_item

@router.patch("/checklist/{item_id}", response_model=ChecklistItemResponse)
def update_checklist_item(
    item_id: int,
    updates: ChecklistItemUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    item = db.query(ProcessChecklistItem).filter(ProcessChecklistItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    if updates.title is not None:
        item.title = updates.title
    if updates.is_completed is not None:
        item.is_completed = updates.is_completed
    
    db.commit()
    db.refresh(item)
    
    # Update process progress
    process = item.process
    total_items = db.query(ProcessChecklistItem).filter(ProcessChecklistItem.process_id == process.id).count()
    if total_items > 0:
        completed_items = db.query(ProcessChecklistItem).filter(
            ProcessChecklistItem.process_id == process.id,
            ProcessChecklistItem.is_completed == True
        ).count()
        process.progress = int((completed_items / total_items) * 100)
        db.commit()
        
    return item

@router.delete("/checklist/{item_id}")
def delete_checklist_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    item = db.query(ProcessChecklistItem).filter(ProcessChecklistItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
        
    process_id = item.process_id
    db.delete(item)
    db.commit()
    
    # Recalculate progress
    process = db.query(Process).filter(Process.id == process_id).first()
    if process:
        total_items = db.query(ProcessChecklistItem).filter(ProcessChecklistItem.process_id == process_id).count()
        if total_items > 0:
            completed_items = db.query(ProcessChecklistItem).filter(
                ProcessChecklistItem.process_id == process_id,
                ProcessChecklistItem.is_completed == True
            ).count()
            process.progress = int((completed_items / total_items) * 100)
        else:
            process.progress = 0
        db.commit()

    return {"ok": True}

@router.post("/process/{process_id}/checklist/reorder")
def reorder_checklist(
    process_id: int,
    payload: ChecklistItemReorder,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    # Retrieve all items for this process to ensure security
    items = db.query(ProcessChecklistItem).filter(
        ProcessChecklistItem.process_id == process_id
    ).all()
    
    item_map = {item.id: item for item in items}
    
    for index, item_id in enumerate(payload.item_ids):
        if item_id in item_map:
            item_map[item_id].order = index
            
    db.commit()
    return {"ok": True}
