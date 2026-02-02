"""
Legislations Schemas - Pydantic models for legislations API
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class LegislationStatusEnum(str, Enum):
    VIGENTE = "VIGENTE"
    REVOGADA = "REVOGADA"
    EM_ATUALIZACAO = "EM_ATUALIZACAO"


class JurisdictionScopeEnum(str, Enum):
    FEDERAL = "FEDERAL"
    ESTADUAL = "ESTADUAL"
    MUNICIPAL = "MUNICIPAL"


class ComplianceLevelEnum(str, Enum):
    ALTA = "ALTA"
    MEDIA = "MEDIA"
    BAIXA = "BAIXA"


class JurisdictionSchema(BaseModel):
    scope: JurisdictionScopeEnum
    state: Optional[str] = Field(None, max_length=2)
    city: Optional[str] = Field(None, max_length=255)


class LegislationBase(BaseModel):
    title: str = Field(..., max_length=500)
    type: str = Field(..., max_length=100)
    code: Optional[str] = Field(None, max_length=100)
    status: LegislationStatusEnum = LegislationStatusEnum.VIGENTE
    summary: str
    jurisdiction: JurisdictionSchema
    issued_by: Optional[str] = Field(None, max_length=255)
    reference_url: Optional[str] = Field(None, max_length=512)
    tags: Optional[List[str]] = None
    compliance_level: Optional[ComplianceLevelEnum] = None
    published_at: datetime
    effective_at: Optional[datetime] = None


class LegislationCreate(LegislationBase):
    pass


class LegislationUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=500)
    type: Optional[str] = Field(None, max_length=100)
    code: Optional[str] = Field(None, max_length=100)
    status: Optional[LegislationStatusEnum] = None
    summary: Optional[str] = None
    jurisdiction: Optional[JurisdictionSchema] = None
    issued_by: Optional[str] = Field(None, max_length=255)
    reference_url: Optional[str] = Field(None, max_length=512)
    tags: Optional[List[str]] = None
    compliance_level: Optional[ComplianceLevelEnum] = None
    published_at: Optional[datetime] = None
    effective_at: Optional[datetime] = None


class LegislationResponse(BaseModel):
    id: int
    title: str
    type: str
    code: Optional[str] = None
    status: LegislationStatusEnum
    summary: str
    jurisdiction: JurisdictionSchema
    issued_by: Optional[str] = None
    reference_url: Optional[str] = None
    tags: Optional[List[str]] = None
    compliance_level: Optional[ComplianceLevelEnum] = None
    published_at: datetime
    effective_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class LegislationListResponse(BaseModel):
    items: List[LegislationResponse]
    total: int
    limit: int
    offset: int


class LegislationStatsResponse(BaseModel):
    total: int
    vigentes: int
    emAtualizacao: int
    revogadas: int




