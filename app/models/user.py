from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    
    # Profile fields
    profile_image_url = Column(String(500), nullable=True)
    phone = Column(String(50), nullable=True)
    bio = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    
    # Last organization preference for multi-organization users
    last_organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True)

    # Relationships - Many-to-many with organizations through association table
    organization_associations = relationship("UserOrganizationAssociation", back_populates="user", cascade="all, delete-orphan")
    organizations = relationship("Organization", secondary="user_organization_association", back_populates="users", viewonly=True)
    licenses = relationship("License", back_populates="user")
    last_organization = relationship("Organization", foreign_keys=[last_organization_id])
