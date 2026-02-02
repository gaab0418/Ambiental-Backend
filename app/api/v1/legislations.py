"""
Legislations API - Environmental laws and regulations
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, timezone
import json

from app.database import get_db
from app.models.user import User
from app.models.legislation import Legislation, LegislationStatus, JurisdictionScope, ComplianceLevel
from app.schemas.legislations import (
    LegislationCreate, LegislationUpdate, LegislationResponse,
    LegislationListResponse, LegislationStatsResponse,
    LegislationStatusEnum, JurisdictionSchema, JurisdictionScopeEnum, ComplianceLevelEnum
)
from app.dependencies.auth import get_current_active_user

router = APIRouter()


def parse_tags(tags_str: Optional[str]) -> Optional[List[str]]:
    """Parse JSON tags string to list."""
    if not tags_str:
        return None
    try:
        return json.loads(tags_str)
    except:
        return None


def serialize_tags(tags: Optional[List[str]]) -> Optional[str]:
    """Serialize tags list to JSON string."""
    if not tags:
        return None
    return json.dumps(tags)


def legislation_to_response(leg: Legislation) -> LegislationResponse:
    """Convert Legislation model to response schema."""
    return LegislationResponse(
        id=leg.id,
        title=leg.title,
        type=leg.type,
        code=leg.code,
        status=LegislationStatusEnum(leg.status.value),
        summary=leg.summary,
        jurisdiction=JurisdictionSchema(
            scope=JurisdictionScopeEnum(leg.jurisdiction_scope.value),
            state=leg.jurisdiction_state,
            city=leg.jurisdiction_city
        ),
        issued_by=leg.issued_by,
        reference_url=leg.reference_url,
        tags=parse_tags(leg.tags),
        compliance_level=ComplianceLevelEnum(leg.compliance_level.value) if leg.compliance_level else None,
        published_at=leg.published_at,
        effective_at=leg.effective_at,
        updated_at=leg.updated_at
    )


@router.get("", response_model=LegislationListResponse)
async def list_legislations(
    request: Request,
    search: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List legislations with filters."""
    query = db.query(Legislation)
    
    # Apply filters
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            Legislation.title.ilike(search_pattern) |
            Legislation.summary.ilike(search_pattern) |
            Legislation.code.ilike(search_pattern)
        )
    
    if state:
        query = query.filter(Legislation.jurisdiction_state == state.upper())
    
    if city:
        query = query.filter(Legislation.jurisdiction_city.ilike(f"%{city}%"))
    
    if type:
        query = query.filter(Legislation.type == type)
    
    if status:
        try:
            status_enum = LegislationStatus(status)
            query = query.filter(Legislation.status == status_enum)
        except ValueError:
            pass
    
    # Get total count
    total = query.count()
    
    # Get paginated results
    legislations = query.order_by(Legislation.published_at.desc()).offset(offset).limit(limit).all()
    
    return LegislationListResponse(
        items=[legislation_to_response(leg) for leg in legislations],
        total=total,
        limit=limit,
        offset=offset
    )


@router.get("/stats", response_model=LegislationStatsResponse)
async def get_legislation_stats(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get legislation statistics."""
    total = db.query(Legislation).count()
    vigentes = db.query(Legislation).filter(Legislation.status == LegislationStatus.VIGENTE).count()
    em_atualizacao = db.query(Legislation).filter(Legislation.status == LegislationStatus.EM_ATUALIZACAO).count()
    revogadas = db.query(Legislation).filter(Legislation.status == LegislationStatus.REVOGADA).count()
    
    return LegislationStatsResponse(
        total=total,
        vigentes=vigentes,
        emAtualizacao=em_atualizacao,
        revogadas=revogadas
    )


@router.get("/{legislation_id}", response_model=LegislationResponse)
async def get_legislation(
    legislation_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get a specific legislation."""
    legislation = db.query(Legislation).filter(Legislation.id == legislation_id).first()
    
    if not legislation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Legislation not found"
        )
    
    return legislation_to_response(legislation)


@router.post("", response_model=LegislationResponse, status_code=status.HTTP_201_CREATED)
async def create_legislation(
    legislation_data: LegislationCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new legislation (admin only in production)."""
    # Create legislation
    legislation = Legislation(
        title=legislation_data.title,
        type=legislation_data.type,
        code=legislation_data.code,
        status=LegislationStatus(legislation_data.status.value),
        summary=legislation_data.summary,
        jurisdiction_scope=JurisdictionScope(legislation_data.jurisdiction.scope.value),
        jurisdiction_state=legislation_data.jurisdiction.state,
        jurisdiction_city=legislation_data.jurisdiction.city,
        issued_by=legislation_data.issued_by,
        reference_url=legislation_data.reference_url,
        tags=serialize_tags(legislation_data.tags),
        compliance_level=ComplianceLevel(legislation_data.compliance_level.value) if legislation_data.compliance_level else None,
        published_at=legislation_data.published_at,
        effective_at=legislation_data.effective_at
    )
    
    db.add(legislation)
    db.commit()
    db.refresh(legislation)
    
    return legislation_to_response(legislation)


@router.put("/{legislation_id}", response_model=LegislationResponse)
async def update_legislation(
    legislation_id: int,
    legislation_data: LegislationUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update a legislation."""
    legislation = db.query(Legislation).filter(Legislation.id == legislation_id).first()
    
    if not legislation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Legislation not found"
        )
    
    # Update fields
    update_data = legislation_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "status" and value:
            setattr(legislation, field, LegislationStatus(value.value))
        elif field == "jurisdiction" and value:
            legislation.jurisdiction_scope = JurisdictionScope(value.scope.value)
            legislation.jurisdiction_state = value.state
            legislation.jurisdiction_city = value.city
        elif field == "tags":
            setattr(legislation, field, serialize_tags(value))
        elif field == "compliance_level" and value:
            setattr(legislation, field, ComplianceLevel(value.value))
        else:
            setattr(legislation, field, value)
    
    legislation.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(legislation)
    
    return legislation_to_response(legislation)


@router.delete("/{legislation_id}")
async def delete_legislation(
    legislation_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete a legislation."""
    legislation = db.query(Legislation).filter(Legislation.id == legislation_id).first()
    
    if not legislation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Legislation not found"
        )
    
    leg_title = legislation.title
    
    db.delete(legislation)
    db.commit()
    
    return {"message": f"Legislation '{leg_title}' deleted successfully"}




