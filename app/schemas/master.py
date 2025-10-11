from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from decimal import Decimal


class MasterOrganizationResponse(BaseModel):
    id: int
    name: str
    slug: str
    email: str
    phone: Optional[str] = None
    address: Optional[str] = None
    is_active: bool
    created_at: datetime
    user_count: int
    subscription_status: str

    class Config:
        from_attributes = True


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

    class Config:
        from_attributes = True


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

    class Config:
        from_attributes = True
