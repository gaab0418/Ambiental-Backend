from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


class MetricsDashboard(BaseModel):
    uptime_hours: float
    total_organizations: int
    active_organizations: int
    total_users: int
    active_users_today: int
    api_calls_today: int
    storage_used_gb: float


class FinancialMetrics(BaseModel):
    monthly_revenue: float = 0.0  # Placeholder for future payment integration
    subscriptions_by_plan: Dict[str, int] = {}
    churn_rate: float = 0.0  # Placeholder
    total_revenue: float = 0.0  # Placeholder


class UsageMetrics(BaseModel):
    metric_type: str
    value: float
    metadata_json: Optional[str] = None
    recorded_at: datetime

    class Config:
        from_attributes = True


class UsageMetricsQuery(BaseModel):
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    metric_type: Optional[str] = None
    limit: int = Field(default=100, ge=1, le=1000)


class SystemMetricCreate(BaseModel):
    metric_type: str
    value: float
    metadata_json: Optional[Dict[str, Any]] = None


