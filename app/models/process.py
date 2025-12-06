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
    
    deadline = Column(DateTime(timezone=True), nullable=True)
    
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    organization = relationship("Organization", back_populates="processes")
    created_by = relationship("User", backref="created_processes")
    timeline_entries = relationship("ProcessTimelineEntry", back_populates="process", cascade="all, delete-orphan")


class ProcessTimelineEntry(Base):
    __tablename__ = "process_timeline_entries"

    id = Column(Integer, primary_key=True, index=True)
    process_id = Column(Integer, ForeignKey("processes.id"), nullable=False)
    
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(SQLEnum(ProcessStatus), nullable=False)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    process = relationship("Process", back_populates="timeline_entries")




