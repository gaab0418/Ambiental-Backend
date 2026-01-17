from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class ChatThread(Base):
    __tablename__ = "chat_threads"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    title = Column(String(120), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Context columns
    type = Column(String(50), default="general", nullable=False, index=True)  # general, process, legislation
    process_code = Column(String(50), nullable=True, index=True)
    process_id = Column(Integer, ForeignKey("processes.id"), nullable=True)
    law_id = Column(Integer, ForeignKey("legislations.id"), nullable=True)

    # Relationships
    user = relationship("User", backref="chat_threads")
    organization = relationship("Organization", backref="chat_threads")
    process = relationship("Process", backref="chat_threads")
    legislation = relationship("Legislation", backref="chat_threads")
    messages = relationship("ChatMessage", back_populates="thread", cascade="all, delete-orphan")
    files = relationship("ChatFile", back_populates="thread", cascade="all, delete-orphan")


