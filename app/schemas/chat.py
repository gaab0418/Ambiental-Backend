from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime


class ChatThreadCreate(BaseModel):
    title: Optional[str] = Field(None, max_length=120)
    type: Optional[str] = Field("general", description="Chat type: general, process, legislation")
    process_code: Optional[str] = None
    process_id: Optional[int] = None
    law_id: Optional[int] = None


class ChatThreadUpdate(BaseModel):
    title: str = Field(..., min_length=1, max_length=120)


class ChatThreadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    user_id: int
    organization_id: int
    title: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    files_count: Optional[int] = 0
    has_timeline: Optional[bool] = False
    
    # Context
    type: str
    process_code: Optional[str]
    process_id: Optional[int]
    law_id: Optional[int]


class ChatMessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


class ChatMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    thread_id: int
    role: str
    content: str
    created_at: datetime


class ChatMessagesResponse(BaseModel):
    messages: List[ChatMessageResponse]
    total: int
    limit: int
    offset: int


# Chat File Schemas
class ChatFileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    thread_id: int
    original_filename: str
    mime_type: str
    size_bytes: int
    checksum: str
    created_at: datetime


# Timeline Event Schemas
class ChatTimelineEventCreate(BaseModel):
    type: str = Field(..., description="Event type: stage, system, file, decision, ai_processing, error")
    status: str = Field(default="pending", description="Status: pending, in_progress, completed, error, cancelled")
    title: str = Field(..., max_length=255)
    description: Optional[str] = None
    order_index: int = Field(default=0)
    metadata: Optional[Dict[str, Any]] = None


class ChatTimelineEventUpdate(BaseModel):
    status: Optional[str] = None
    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    order_index: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


class ChatTimelineEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    thread_id: int
    organization_id: int
    type: str
    status: str
    title: str
    description: Optional[str]
    order_index: int
    event_metadata: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime


# N8N Callback Schemas
class N8NCallbackMessage(BaseModel):
    assistant_message: str
    timeline_events: Optional[List[ChatTimelineEventCreate]] = None
    metadata: Optional[Dict[str, Any]] = None


