from sqlalchemy import Column, Integer, String, DateTime, Float, Text
from sqlalchemy.sql import func
from app.database import Base


class SystemMetric(Base):
    __tablename__ = "system_metrics"

    id = Column(Integer, primary_key=True, index=True)
    metric_type = Column(String(50), nullable=False, index=True)  # uptime, api_calls, storage_used, active_users
    value = Column(Float, nullable=False)
    metadata_json = Column(Text, nullable=True)  # JSON with additional data
    recorded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
