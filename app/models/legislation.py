"""
Legislation Model - Environmental laws and regulations
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Enum as SQLEnum
from datetime import datetime, timezone
import enum

from app.database import Base


class LegislationStatus(str, enum.Enum):
    VIGENTE = "VIGENTE"
    REVOGADA = "REVOGADA"
    EM_ATUALIZACAO = "EM_ATUALIZACAO"


class JurisdictionScope(str, enum.Enum):
    FEDERAL = "FEDERAL"
    ESTADUAL = "ESTADUAL"
    MUNICIPAL = "MUNICIPAL"


class ComplianceLevel(str, enum.Enum):
    ALTA = "ALTA"
    MEDIA = "MEDIA"
    BAIXA = "BAIXA"


class Legislation(Base):
    __tablename__ = "legislations"

    id = Column(Integer, primary_key=True, index=True)
    
    title = Column(String(500), nullable=False)
    type = Column(String(100), nullable=False)  # Lei, Decreto, Resolução, etc.
    code = Column(String(100), nullable=True)  # e.g., "Lei 12.651/2012"
    
    status = Column(SQLEnum(LegislationStatus), default=LegislationStatus.VIGENTE, nullable=False)
    summary = Column(Text, nullable=False)
    
    # Jurisdiction
    jurisdiction_scope = Column(SQLEnum(JurisdictionScope), default=JurisdictionScope.FEDERAL, nullable=False)
    jurisdiction_state = Column(String(2), nullable=True)  # UF code
    jurisdiction_city = Column(String(255), nullable=True)
    
    issued_by = Column(String(255), nullable=True)  # Órgão emissor
    reference_url = Column(String(512), nullable=True)
    
    tags = Column(Text, nullable=True)  # JSON array as string
    
    compliance_level = Column(SQLEnum(ComplianceLevel), nullable=True)
    
    published_at = Column(DateTime(timezone=True), nullable=False)
    effective_at = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))




