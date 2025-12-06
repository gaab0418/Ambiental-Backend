"""
Agenda Schemas - Pydantic models for agenda API
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class AgendaStatusEnum(str, Enum):
    PENDENTE = "PENDENTE"
    EM_ANDAMENTO = "EM_ANDAMENTO"
    CONCLUIDO = "CONCLUIDO"
    ATRASADO = "ATRASADO"


class AgendaPriorityEnum(str, Enum):
    BAIXA = "BAIXA"
    MEDIA = "MEDIA"
    ALTA = "ALTA"
    CRITICA = "CRITICA"


class AgendaEventBase(BaseModel):
    title: str = Field(..., max_length=255)
    description: Optional[str] = None
    event_type: str = Field(default="GERAL", max_length=100)
    status: AgendaStatusEnum = AgendaStatusEnum.PENDENTE
    priority: AgendaPriorityEnum = AgendaPriorityEnum.MEDIA
    starts_at: datetime
    ends_at: Optional[datetime] = None
    location: Optional[str] = Field(None, max_length=255)
    related_process_id: Optional[int] = None
    related_document_id: Optional[int] = None


class AgendaEventCreate(AgendaEventBase):
    pass


class AgendaEventUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    event_type: Optional[str] = Field(None, max_length=100)
    status: Optional[AgendaStatusEnum] = None
    priority: Optional[AgendaPriorityEnum] = None
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    location: Optional[str] = Field(None, max_length=255)
    related_process_id: Optional[int] = None
    related_document_id: Optional[int] = None


class AgendaEventStatusUpdate(BaseModel):
    status: AgendaStatusEnum


class AgendaEventResponse(AgendaEventBase):
    id: int
    organization_id: int
    created_by_user_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AgendaEventListResponse(BaseModel):
    items: List[AgendaEventResponse]
    total: int
    limit: int
    offset: int



