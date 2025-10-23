from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    cnpj_cpf = Column(String(20), unique=True, nullable=False, index=True)  # CNPJ ou CPF - chave única
    email = Column(String(255), nullable=False, index=True)
    phone = Column(String(20), nullable=True)
    address = Column(String(500), nullable=True)
    logo_url = Column(String(500), nullable=True)
    website = Column(String(200), nullable=True)
    company_size = Column(String(50), nullable=True)  # MICRO, SMALL, MEDIUM, LARGE, ENTERPRISE
    industry = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    users = relationship("User", back_populates="organization")
    subscriptions = relationship("Subscription", back_populates="organization")
    licenses = relationship("License", back_populates="organization")
