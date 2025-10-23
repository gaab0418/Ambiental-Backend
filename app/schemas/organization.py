from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime


class OrganizationResponse(BaseModel):
    id: int
    name: str
    slug: str
    cnpj_cpf: str
    email: str
    phone: Optional[str] = None
    address: Optional[str] = None
    logo_url: Optional[str] = None
    website: Optional[str] = None
    company_size: Optional[str] = None
    industry: Optional[str] = None
    description: Optional[str] = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class UserInviteRequest(BaseModel):
    email: EmailStr
    full_name: str
    role_id: int
    password: str = Field(min_length=8, max_length=128)


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


class UserUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None


class OrganizationUpdateRequest(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None


class OrganizationFullUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = Field(None, max_length=500)
    website: Optional[str] = Field(None, max_length=200)
    company_size: Optional[str] = Field(None, max_length=50)
    industry: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    logo_url: Optional[str] = Field(None, max_length=500)


class UserRoleChangeRequest(BaseModel):
    role_id: int = Field(gt=0)
