from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, BigInteger
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class ChatFile(Base):
    __tablename__ = "chat_files"

    id = Column(Integer, primary_key=True, index=True)
    thread_id = Column(Integer, ForeignKey("chat_threads.id"), nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # File metadata
    original_filename = Column(String(255), nullable=False)
    mime_type = Column(String(100), nullable=False)
    size_bytes = Column(BigInteger, nullable=False)
    
    # Storage and encryption
    storage_path = Column(String(500), nullable=False)
    encryption_iv = Column(String(255), nullable=False)  # Base64-encoded IV
    encryption_tag = Column(String(255), nullable=False)  # Base64-encoded auth tag
    encryption_algo = Column(String(50), nullable=False, default="AES-256-GCM")
    key_version = Column(String(50), nullable=False, default="v1")
    
    # Integrity
    checksum = Column(String(64), nullable=False)  # SHA-256 hex
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    # Relationships
    thread = relationship("ChatThread", back_populates="files")
    organization = relationship("Organization")
    user = relationship("User")

