from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class FlowMetric(Base):
    """Metrics for n8n workflow executions"""
    __tablename__ = "flow_metrics"

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    flow_name = Column(String(100), nullable=False, index=True)
    execution_id = Column(String(100), nullable=True)
    tokens_used = Column(Integer, nullable=True)
    execution_time_ms = Column(Integer, nullable=True)
    status = Column(String(20), nullable=False)
    error_message = Column(Text, nullable=True)
    metadata_json = Column(JSONB, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    # Relationships
    organization = relationship("Organization", back_populates="flow_metrics")



