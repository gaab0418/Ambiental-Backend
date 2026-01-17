"""
Process Model - Environmental processes and workflows
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum

from app.database import Base


class ProcessStatus(str, enum.Enum):
    EM_ANDAMENTO = "EM_ANDAMENTO"
    AGUARDANDO_ANALISE = "AGUARDANDO_ANALISE"
    APROVADO = "APROVADO"
    PENDENTE = "PENDENTE"
    ATRASADO = "ATRASADO"
    CANCELADO = "CANCELADO"


class ProcessPriority(str, enum.Enum):
    BAIXA = "BAIXA"
    MEDIA = "MEDIA"
    ALTA = "ALTA"
    CRITICA = "CRITICA"


class Process(Base):
    __tablename__ = "processes"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    
    title = Column(String(255), nullable=False)
    protocol = Column(String(100), nullable=False, unique=True)
    
    status = Column(SQLEnum(ProcessStatus), default=ProcessStatus.PENDENTE, nullable=False)
    priority = Column(SQLEnum(ProcessPriority), default=ProcessPriority.MEDIA, nullable=False)
    progress = Column(Integer, default=0)  # 0-100
    
    responsible = Column(String(255), nullable=True)
    location = Column(String(255), nullable=True)
    
    tags = Column(Text, nullable=True)  # JSON array as string
    summary = Column(Text, nullable=True)
    
    in_type = Column(String(50), nullable=True)  # Hardcoded IN type key
    
    deadline = Column(DateTime(timezone=True), nullable=True)
    
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    organization = relationship("Organization", back_populates="processes")
    created_by = relationship("User", backref="created_processes")
    checklist_items = relationship("ProcessChecklistItem", back_populates="process", cascade="all, delete-orphan")
    documents = relationship("Document", backref="process", cascade="all, delete-orphan")




