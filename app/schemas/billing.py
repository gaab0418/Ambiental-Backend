from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from decimal import Decimal


class PlanResponse(BaseModel):
    id: int
    name: str
    display_name: str
    description: Optional[str] = None
    price: Decimal
    currency: str
    max_users: int
    max_storage_gb: Optional[int] = None
    features: Optional[str] = None
    is_active: bool

    class Config:
        from_attributes = True


class SubscriptionResponse(BaseModel):
    id: int
    status: str
    current_period_start: datetime
    current_period_end: datetime
    trial_end: Optional[datetime] = None
    canceled_at: Optional[datetime] = None
    plan: PlanResponse
    created_at: datetime

    class Config:
        from_attributes = True


class LicenseUsageResponse(BaseModel):
    total_licenses: int
    active_licenses: int
    inactive_licenses: int
    available_licenses: int


class BillingStatusResponse(BaseModel):
    subscription: SubscriptionResponse
    license_usage: LicenseUsageResponse
    plan_limit: int


class PurchaseLicenseRequest(BaseModel):
    quantity: int


class PurchaseLicenseResponse(BaseModel):
    message: str
    new_license_count: int
    total_cost: Decimal
