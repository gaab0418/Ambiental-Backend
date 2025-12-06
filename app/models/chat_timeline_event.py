from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum


class TimelineEventType(str, enum.Enum):
    STAGE = "stage"
    SYSTEM = "system"
    FILE = "file"
    DECISION = "decision"
    AI_PROCESSING = "ai_processing"
    ERROR = "error"


class TimelineEventStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ERROR = "error"
    CANCELLED = "cancelled"


class ChatTimelineEvent(Base):
    __tablename__ = "chat_timeline_events"

    id = Column(Integer, primary_key=True, index=True)
    thread_id = Column(Integer, ForeignKey("chat_threads.id"), nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    
    # Event details
    type = Column(SQLEnum(TimelineEventType), nullable=False, index=True)
    status = Column(SQLEnum(TimelineEventStatus), nullable=False, default=TimelineEventStatus.PENDING, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Ordering
    order_index = Column(Integer, nullable=False, default=0, index=True)
    
    # Additional data (JSON payload for extra info)
    event_metadata = Column(JSONB, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    thread = relationship("ChatThread", back_populates="timeline_events")
    organization = relationship("Organization")

