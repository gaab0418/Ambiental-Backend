from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)  # Null for system actions
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)
    action = Column(String(100), nullable=False, index=True)  # CREATE, UPDATE, DELETE, LOGIN, LOGOUT, etc
    entity_type = Column(String(100), nullable=False, index=True)  # User, Organization, Plan, etc
    entity_id = Column(Integer, nullable=True, index=True)
    changes = Column(Text, nullable=True)  # JSON with before/after
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    # Relationships
    user = relationship("User", backref="audit_logs")
    organization = relationship("Organization", backref="audit_logs")

