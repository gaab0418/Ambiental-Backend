from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
from app.database import get_db
from app.models.user import User
from app.schemas.metrics import MetricsDashboard, FinancialMetrics, UsageMetrics
from app.dependencies.auth import require_administrator, get_current_user
from app.utils.metrics_collector import MetricsCollector

router = APIRouter()


@router.get("/dashboard", response_model=MetricsDashboard)
async def get_dashboard_metrics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get dashboard metrics (authenticated users only)."""
    
    metrics = MetricsCollector.collect_dashboard_metrics(db)
    return metrics


@router.get("/financial", response_model=FinancialMetrics)
async def get_financial_metrics(
    current_user: User = Depends(require_administrator),
    db: Session = Depends(get_db)
):
    """Get financial metrics (ADMINISTRATOR only)."""
    
    metrics = MetricsCollector.collect_financial_metrics(db)
    return metrics


@router.get("/usage", response_model=list[UsageMetrics])
async def get_usage_metrics(
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    metric_type: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(require_administrator),
    db: Session = Depends(get_db)
):
    """Get usage metrics for a date range (ADMINISTRATOR only)."""
    
    # Validate date range
    if date_from and date_to and date_from > date_to:
        raise HTTPException(
            status_code=400,
            detail="date_from must be before date_to"
        )
    
    metrics = MetricsCollector.get_usage_metrics(
        db=db,
        date_from=date_from,
        date_to=date_to,
        metric_type=metric_type,
        limit=limit
    )
    
    return metrics


@router.post("/record")
async def record_metric(
    metric_data: dict,
    current_user: User = Depends(require_administrator),
    db: Session = Depends(get_db)
):
    """Record a system metric (ADMINISTRATOR only)."""
    
    try:
        metric = MetricsCollector.record_metric(
            db=db,
            metric_type=metric_data.get("metric_type"),
            value=metric_data.get("value"),
            metadata=metric_data.get("metadata")
        )
        
        return {"message": "Metric recorded successfully", "id": metric.id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))



