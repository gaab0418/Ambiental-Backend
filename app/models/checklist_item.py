from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship, backref
from datetime import datetime, timezone

from app.database import Base

class ProcessChecklistItem(Base):
    __tablename__ = "process_checklist_items"

    id = Column(Integer, primary_key=True, index=True)
    process_id = Column(Integer, ForeignKey("processes.id"), nullable=False)
    parent_id = Column(Integer, ForeignKey("process_checklist_items.id"), nullable=True)
    
    title = Column(String(500), nullable=False)
    is_completed = Column(Boolean, default=False, nullable=False)
    order = Column(Integer, default=0, nullable=False)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    process = relationship("Process", back_populates="checklist_items")
    children = relationship("ProcessChecklistItem", 
                          backref=backref("parent", remote_side=[id]),
                          cascade="all, delete-orphan")
