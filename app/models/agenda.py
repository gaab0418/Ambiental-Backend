"""
Agenda Model - Events, deadlines, and environmental commitments
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum

from app.database import Base


class AgendaStatus(str, enum.Enum):
    PENDENTE = "PENDENTE"
    EM_ANDAMENTO = "EM_ANDAMENTO"
    CONCLUIDO = "CONCLUIDO"
    ATRASADO = "ATRASADO"


class AgendaPriority(str, enum.Enum):
    BAIXA = "BAIXA"
    MEDIA = "MEDIA"
    ALTA = "ALTA"
    CRITICA = "CRITICA"


class AgendaEvent(Base):
    __tablename__ = "agenda_events"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    event_type = Column(String(100), nullable=False, default="GERAL")
    
    status = Column(SQLEnum(AgendaStatus), default=AgendaStatus.PENDENTE, nullable=False)
    priority = Column(SQLEnum(AgendaPriority), default=AgendaPriority.MEDIA, nullable=False)
    
    starts_at = Column(DateTime(timezone=True), nullable=False)
    ends_at = Column(DateTime(timezone=True), nullable=True)
    location = Column(String(255), nullable=True)
    
    related_process_id = Column(Integer, ForeignKey("processes.id"), nullable=True)
    related_document_id = Column(Integer, ForeignKey("documents.id"), nullable=True)
    
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    organization = relationship("Organization", back_populates="agenda_events")
    created_by = relationship("User", backref="created_agenda_events")



