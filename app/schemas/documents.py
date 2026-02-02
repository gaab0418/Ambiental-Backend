"""
Documents Schemas - Pydantic models for documents API
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class DocumentStatusEnum(str, Enum):
    VALIDADO = "VALIDADO"
    PENDENTE = "PENDENTE"
    EXPIRADO = "EXPIRADO"
    EM_ANALISE = "EM_ANALISE"


class DocumentBase(BaseModel):
    name: str = Field(..., max_length=255)
    category: str = Field(default="GERAL", max_length=100)
    status: DocumentStatusEnum = DocumentStatusEnum.PENDENTE
    owner_name: Optional[str] = Field(None, max_length=255)
    expires_at: Optional[datetime] = None
    tags: Optional[List[str]] = None


class DocumentCreate(DocumentBase):
    pass


class GeneratedDocumentCreate(BaseModel):
    """Schema for saving a document generated from a template."""
    name: str = Field(..., max_length=255, description="Nome do documento")
    category: str = Field(default="GERAL", max_length=100)
    content: str = Field(..., description="Conteúdo HTML/Markdown do documento gerado")
    template_id: Optional[int] = Field(None, description="ID do template usado")
    template_name: Optional[str] = Field(None, description="Nome do template usado")


class DocumentUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    category: Optional[str] = Field(None, max_length=100)
    status: Optional[DocumentStatusEnum] = None
    owner_name: Optional[str] = Field(None, max_length=255)
    expires_at: Optional[datetime] = None
    tags: Optional[List[str]] = None


class DocumentResponse(BaseModel):
    id: int
    name: str
    category: str
    status: DocumentStatusEnum
    size_bytes: int
    uploaded_at: datetime
    owner_name: Optional[str] = None
    tags: Optional[List[str]] = None
    download_url: Optional[str] = None
    expires_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    items: List[DocumentResponse]
    total: int
    limit: int
    offset: int




