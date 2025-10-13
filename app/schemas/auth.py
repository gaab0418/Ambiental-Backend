from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


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


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    is_active: bool
    is_verified: bool
    organization_id: int
    role_id: int
    created_at: datetime
    last_login_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserSelfUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    password: Optional[str] = None  # Para trocar senha
