from sqlalchemy import Column, Integer, String, Text, Boolean, Date, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from app.database import Base


class MunicipalInstruction(Base):
    """Municipal environmental regulations (INs) by city"""
    __tablename__ = "municipal_instructions"

    id = Column(Integer, primary_key=True, index=True)
    municipality = Column(String(100), nullable=False, index=True)
    state = Column(String(2), nullable=False)
    instruction_number = Column(String(50), nullable=False)
    version = Column(String(20), nullable=False)
    valid_from = Column(Date, nullable=False)
    valid_until = Column(Date, nullable=True)
    is_current = Column(Boolean, default=True, nullable=False, index=True)
    
    content_text = Column(Text, nullable=True)
    content_url = Column(String(500), nullable=True)
    metadata_json = Column(JSONB, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)



