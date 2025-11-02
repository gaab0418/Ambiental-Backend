from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class OrganizationSelection(BaseModel):
    """Organization details for selection after login."""
    id: int
    name: str
    cnpj_cpf: str
    role_name: str
    
    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    requires_org_selection: bool = False
    available_organizations: list[OrganizationSelection] = []


class TokenData(BaseModel):
    sub: Optional[str] = None
    organization_id: Optional[int] = None
    role: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserRegister(BaseModel):
    email: EmailStr
    full_name: str
    password: str
    organization_name: str
    cnpj_cpf: str  # CNPJ ou CPF da organização


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class OrganizationSelectionRequest(BaseModel):
    """Request to select an organization after initial authentication."""
    organization_id: int


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    is_active: bool
    is_verified: bool
    profile_image_url: Optional[str] = None
    phone: Optional[str] = None
    bio: Optional[str] = None
    created_at: datetime
    last_login_at: Optional[datetime] = None
    
    # Current session context (from token)
    current_organization_id: Optional[int] = None
    current_role_name: Optional[str] = None
    current_organization_name: Optional[str] = None
    
    # All organizations the user belongs to
    organizations: list[OrganizationSelection] = []
    
    # Flag indicating if user is a system administrator
    is_system_admin: bool = False

    class Config:
        from_attributes = True


class UserSelfUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    bio: Optional[str] = None
    password: Optional[str] = None  # Para trocar senha


class UserProfileUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=50)
    bio: Optional[str] = None
    profile_image_url: Optional[str] = Field(None, max_length=500)


class PasswordChangeRequest(BaseModel):
    old_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8, max_length=128)
