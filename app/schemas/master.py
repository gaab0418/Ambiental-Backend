from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional, List
from datetime import datetime
from decimal import Decimal


class MasterOrganizationResponse(BaseModel):
    id: int
    name: str
    slug: str
    cnpj_cpf: str
    email: str
    phone: Optional[str] = None
    address: Optional[str] = None
    is_active: bool
    created_at: datetime
    user_count: int
    subscription_status: str

    model_config = ConfigDict(from_attributes=True)


class MasterOrganizationCreateRequest(BaseModel):
    name: str
    cnpj_cpf: str
    email: EmailStr
    phone: Optional[str] = None
    address: Optional[str] = None


class MasterUserCreateRequest(BaseModel):
    email: EmailStr
    full_name: str
    password: str
    organization_id: int
    role_id: int


class MasterUserUpdateRequest(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    role_id: Optional[int] = None


class MasterOrganizationUpdateRequest(BaseModel):
    name: Optional[str] = None
    cnpj_cpf: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None


class PlanCreateRequest(BaseModel):
    name: str
    display_name: str
    description: Optional[str] = None
    price: Decimal
    currency: str = "BRL"
    max_users: int
    max_storage_gb: Optional[int] = None
    features: Optional[dict] = None


class PlanUpdateRequest(BaseModel):
    display_name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[Decimal] = None
    max_users: Optional[int] = None
    max_storage_gb: Optional[int] = None
    features: Optional[dict] = None
    is_active: Optional[bool] = None


class PlanResponse(BaseModel):
    id: int
    name: str
    display_name: str
    description: Optional[str] = None
    price: Decimal
    currency: str
    max_users: int
    max_storage_gb: Optional[int] = None
    features: Optional[str] = None  # JSON string
    is_active: bool
    is_system: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MasterSubscriptionUpdateRequest(BaseModel):
    plan_id: int
    status: str  # active, inactive, past_due, canceled, trial
    current_period_end: Optional[datetime] = None
    trial_end: Optional[datetime] = None


class MasterSubscriptionResponse(BaseModel):
    id: int
    status: str
    current_period_start: datetime
    current_period_end: datetime
    trial_end: Optional[datetime] = None
    canceled_at: Optional[datetime] = None
    plan_name: str
    plan_price: Decimal
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MasterUserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    is_active: bool
    is_verified: bool
    role_name: str
    organization_name: str
    created_at: datetime
    last_login_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
