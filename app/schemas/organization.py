from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime


class OrganizationResponse(BaseModel):
    id: int
    name: str
    slug: str
    email: str
    phone: Optional[str] = None
    address: Optional[str] = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class UserInviteRequest(BaseModel):
    email: EmailStr
    full_name: str
    role_id: int


class UserInviteResponse(BaseModel):
    id: int
    email: str
    full_name: str
    is_active: bool
    is_verified: bool
    role_id: int
    organization_id: int
    created_at: datetime
    last_login_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class RoleResponse(BaseModel):
    id: int
    name: str
    display_name: str
    description: Optional[str] = None

    class Config:
        from_attributes = True
