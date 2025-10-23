from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class ChatThreadCreate(BaseModel):
    title: Optional[str] = Field(None, max_length=120)


class ChatThreadResponse(BaseModel):
    id: int
    user_id: int
    organization_id: int
    title: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ChatMessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


class ChatMessageResponse(BaseModel):
    id: int
    thread_id: int
    role: str
    content: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class ChatMessagesResponse(BaseModel):
    messages: List[ChatMessageResponse]
    total: int
    limit: int
    offset: int


