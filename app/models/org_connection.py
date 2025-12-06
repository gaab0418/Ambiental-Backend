from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class OrgConnection(Base):
    """Database connection credentials for organizations (SaaS or on-prem)"""
    __tablename__ = "org_connections"

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    db_type = Column(String(50), nullable=False, index=True)  # app, vector, logs
    location = Column(String(20), nullable=False)  # cloud, on_prem
    
    # Encrypted connection details
    host_encrypted = Column(Text, nullable=True)
    port = Column(Integer, nullable=True)
    database_name_encrypted = Column(Text, nullable=True)
    username_encrypted = Column(Text, nullable=True)
    password_encrypted = Column(Text, nullable=True)
    connection_string_encrypted = Column(Text, nullable=True)
    
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    organization = relationship("Organization", back_populates="connections")



