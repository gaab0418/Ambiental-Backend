"""
Document Model - Environmental document management
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum as SQLEnum, BigInteger
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum

from app.database import Base


class DocumentStatus(str, enum.Enum):
    VALIDADO = "VALIDADO"
    PENDENTE = "PENDENTE"
    EXPIRADO = "EXPIRADO"
    EM_ANALISE = "EM_ANALISE"


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    
    name = Column(String(255), nullable=False)
    category = Column(String(100), nullable=False, default="GERAL")
    status = Column(SQLEnum(DocumentStatus), default=DocumentStatus.PENDENTE, nullable=False)
    
    # File info
    original_filename = Column(String(255), nullable=False)
    stored_filename = Column(String(255), nullable=False)
    storage_path = Column(String(512), nullable=False)
    mime_type = Column(String(100), nullable=False, default="application/octet-stream")
    size_bytes = Column(BigInteger, nullable=False, default=0)
    
    # Encryption (optional)
    encryption_iv = Column(String(64), nullable=True)
    encryption_tag = Column(String(64), nullable=True)
    checksum = Column(String(128), nullable=True)
    
    # Metadata
    tags = Column(Text, nullable=True)  # JSON array as string
    owner_name = Column(String(255), nullable=True)
    
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    uploaded_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    organization = relationship("Organization", back_populates="documents")
    uploaded_by = relationship("User", backref="uploaded_documents")

