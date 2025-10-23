"""
Metrics Collector Utility
Collects and aggregates system metrics for dashboard and reports
"""

from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from typing import Optional, List
import json
from app.models.user import User
from app.models.organization import Organization
from app.models.subscription import Subscription, SubscriptionStatus
from app.models.license import License, LicenseStatus
from app.models.plan import Plan
from app.models.system_metric import SystemMetric
from app.models.audit_log import AuditLog


class MetricsCollector:
    """Collects system metrics for dashboards and reports"""
    
    @staticmethod
    def collect_dashboard_metrics(db: Session) -> dict:
        """Collect main dashboard metrics matching MetricsDashboard schema"""
        
        # Count totals
        total_users = db.query(User).count()
        total_organizations = db.query(Organization).count()
        active_organizations = db.query(Organization).filter(Organization.is_active == True).count()
        
        # Active users today (logged in today)
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        active_users_today = db.query(User).filter(
            User.is_active == True,
            User.last_login_at >= today_start
        ).count()
        
        # API calls today (audit log entries)
        api_calls_today = db.query(AuditLog).filter(
            AuditLog.created_at >= today_start
        ).count()
        
        # Uptime hours (placeholder - in production, track app start time)
        uptime_hours = 0.0
        
        # Storage used GB (placeholder - in production, calculate actual storage)
        storage_used_gb = 0.0
        
        return {
            "uptime_hours": uptime_hours,
            "total_organizations": total_organizations,
            "active_organizations": active_organizations,
            "total_users": total_users,
            "active_users_today": active_users_today,
            "api_calls_today": api_calls_today,
            "storage_used_gb": storage_used_gb
        }
    
    @staticmethod
    def collect_financial_metrics(db: Session, period_days: int = 30) -> dict:
        """Collect financial metrics"""
        
        # Get active subscriptions with plans
        active_subscriptions = db.query(Subscription).filter(
            Subscription.status == SubscriptionStatus.ACTIVE
        ).all()
        
        # Calculate monthly recurring revenue (MRR)
        mrr = 0
        for subscription in active_subscriptions:
            if subscription.plan:
                mrr += subscription.plan.price
        
        # Calculate annual recurring revenue (ARR)
        arr = mrr * 12
        
        # Get plan distribution
        plan_distribution = db.query(
            Plan.name,
            func.count(Subscription.id).label('count')
        ).join(
            Subscription, Plan.id == Subscription.plan_id
        ).filter(
            Subscription.status == SubscriptionStatus.ACTIVE
        ).group_by(
            Plan.name
        ).all()
        
        plan_stats = {plan_name: count for plan_name, count in plan_distribution}
        
        return {
            "monthly_recurring_revenue": round(mrr, 2),
            "annual_recurring_revenue": round(arr, 2),
            "total_active_subscriptions": len(active_subscriptions),
            "plan_distribution": plan_stats,
            "average_revenue_per_subscription": round(mrr / len(active_subscriptions), 2) if active_subscriptions else 0
        }
    
    @staticmethod
    def collect_usage_metrics(db: Session, period_days: int = 30) -> dict:
        """Collect usage metrics for the specified period"""
        
        start_date = datetime.utcnow() - timedelta(days=period_days)
        
        # Users created in period
        new_users = db.query(User).filter(
            User.created_at >= start_date
        ).count()
        
        # Organizations created in period
        new_organizations = db.query(Organization).filter(
            Organization.created_at >= start_date
        ).count()
        
        # Active users (logged in during period)
        active_in_period = db.query(User).filter(
            User.last_login_at >= start_date,
            User.is_active == True
        ).count()
        
        # Total active users
        total_active = db.query(User).filter(User.is_active == True).count()
        
        return {
            "period_days": period_days,
            "new_users": new_users,
            "new_organizations": new_organizations,
            "active_users_in_period": active_in_period,
            "total_active_users": total_active,
            "user_engagement_rate": round((active_in_period / total_active * 100) if total_active > 0 else 0, 2)
        }
    
    @staticmethod
    def get_usage_metrics(
        db: Session,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        metric_type: Optional[str] = None,
        limit: int = 100
    ) -> List[SystemMetric]:
        """Get usage metrics for a date range"""
        
        # Validate limit
        if limit < 1:
            limit = 1
        elif limit > 1000:
            limit = 1000
        
        # Build query
        query = db.query(SystemMetric)
        
        # Apply filters
        if date_from:
            query = query.filter(SystemMetric.recorded_at >= date_from)
        
        if date_to:
            query = query.filter(SystemMetric.recorded_at <= date_to)
        
        if metric_type:
            query = query.filter(SystemMetric.metric_type == metric_type)
        
        # Order by most recent first and limit
        metrics = query.order_by(SystemMetric.recorded_at.desc()).limit(limit).all()
        
        return metrics
    
    @staticmethod
    def record_metric(
        db: Session,
        metric_type: str,
        value: float,
        metadata: Optional[dict] = None
    ) -> SystemMetric:
        """Record a system metric"""
        
        # Validate metric_type
        if not metric_type or not metric_type.strip():
            raise ValueError("metric_type cannot be empty")
        
        # Validate value is finite
        if not isinstance(value, (int, float)) or value != value:  # NaN check
            raise ValueError("value must be a finite number")
        
        # Serialize metadata if provided
        metadata_json = None
        if metadata:
            try:
                metadata_json = json.dumps(metadata)
            except (TypeError, ValueError) as e:
                raise ValueError(f"metadata must be JSON-serializable: {str(e)}")
        
        # Create metric
        metric = SystemMetric(
            metric_type=metric_type,
            value=float(value),
            metadata_json=metadata_json
        )
        
        db.add(metric)
        db.commit()
        db.refresh(metric)
        
        return metric

