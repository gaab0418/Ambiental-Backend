from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime


class TemplateCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    content: str = Field(..., min_length=1)
    is_global: bool = False


class TemplateUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    content: Optional[str] = Field(None, min_length=1)
    is_active: Optional[bool] = None


class TemplateResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    content: str
    created_by_user_id: int
    organization_id: Optional[int] = None
    is_global: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    # Related data (optional, populated in responses)
    created_by_user_name: Optional[str] = None
    organization_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class TemplateQuery(BaseModel):
    is_global: Optional[bool] = None
    is_active: Optional[bool] = None
    organization_id: Optional[int] = None
    created_by_user_id: Optional[int] = None
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


