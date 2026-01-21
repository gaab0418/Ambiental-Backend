"""
Processes Schemas - Pydantic models for processes API
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class ProcessStatusEnum(str, Enum):
    EM_ANDAMENTO = "EM_ANDAMENTO"
    AGUARDANDO_ANALISE = "AGUARDANDO_ANALISE"
    APROVADO = "APROVADO"
    PENDENTE = "PENDENTE"
    ATRASADO = "ATRASADO"
    CANCELADO = "CANCELADO"


class ProcessPriorityEnum(str, Enum):
    BAIXA = "BAIXA"
    MEDIA = "MEDIA"
    ALTA = "ALTA"
    CRITICA = "CRITICA"


class ProcessBase(BaseModel):
    title: str = Field(..., max_length=255)
    protocol: str = Field(..., max_length=100)
    status: ProcessStatusEnum = ProcessStatusEnum.PENDENTE
    priority: ProcessPriorityEnum = ProcessPriorityEnum.MEDIA
    progress: int = Field(default=0, ge=0, le=100)
    responsible: Optional[str] = Field(None, max_length=255)
    location: Optional[str] = Field(None, max_length=255)
    tags: Optional[List[str]] = None
    summary: Optional[str] = None
    deadline: Optional[datetime] = None


class ProcessCreate(ProcessBase):
    pass


class ProcessUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    protocol: Optional[str] = Field(None, max_length=100)
    status: Optional[ProcessStatusEnum] = None
    priority: Optional[ProcessPriorityEnum] = None
    progress: Optional[int] = Field(None, ge=0, le=100)
    responsible: Optional[str] = Field(None, max_length=255)
    location: Optional[str] = Field(None, max_length=255)
    tags: Optional[List[str]] = None
    summary: Optional[str] = None
    deadline: Optional[datetime] = None


class ProcessStatusUpdate(BaseModel):
    status: ProcessStatusEnum


class ProcessProgressUpdate(BaseModel):
    progress: int = Field(..., ge=0, le=100)


class ProcessResponse(BaseModel):
    id: int
    title: str
    protocol: str
    status: ProcessStatusEnum
    priority: ProcessPriorityEnum
    progress: int
    responsible: Optional[str] = None
    location: Optional[str] = None
    tags: Optional[List[str]] = None
    in_type: Optional[str] = None
    summary: Optional[str] = None
    deadline: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    checklist_total: int = 0
    checklist_completed: int = 0
    checklist_pending: int = 0

    class Config:
        from_attributes = True


class ProcessListResponse(BaseModel):
    items: List[ProcessResponse]
    total: int
    limit: int
    offset: int







