from sqlalchemy import Column, Integer, String, DateTime, Text, Float
from sqlalchemy.sql import func
from app.database import Base

class RequestLog(Base):
    __tablename__ = "request_logs"

    id = Column(Integer, primary_key=True, index=True)
    correlation_id = Column(String(36), index=True, nullable=False)
    
    # Request details
    method = Column(String(10), nullable=False, index=True)
    url = Column(Text, nullable=False)
    request_headers = Column(Text, nullable=True)  # JSON string
    request_body = Column(Text, nullable=True)
    
    # Response details
    status_code = Column(Integer, nullable=True, index=True)
    response_headers = Column(Text, nullable=True)  # JSON string
    response_body = Column(Text, nullable=True)
    duration_ms = Column(Float, nullable=True)
    
    # Context
    ip_address = Column(String(50), nullable=True)
    direction = Column(String(10), nullable=False, default="INCOMING")  # INCOMING or OUTGOING
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
