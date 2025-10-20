"""
Metrics Collector Utility
Collects and aggregates system metrics for dashboard and reports
"""

from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from app.models.user import User
from app.models.organization import Organization
from app.models.subscription import Subscription, SubscriptionStatus
from app.models.license import License, LicenseStatus
from app.models.plan import Plan


class MetricsCollector:
    """Collects system metrics for dashboards and reports"""
    
    @staticmethod
    def collect_dashboard_metrics(db: Session) -> dict:
        """Collect main dashboard metrics"""
        
        # Count totals
        total_users = db.query(User).count()
        active_users = db.query(User).filter(User.is_active == True).count()
        total_organizations = db.query(Organization).count()
        active_organizations = db.query(Organization).filter(Organization.is_active == True).count()
        
        # Subscription metrics
        active_subscriptions = db.query(Subscription).filter(
            Subscription.status == SubscriptionStatus.ACTIVE
        ).count()
        
        trial_subscriptions = db.query(Subscription).filter(
            Subscription.status == SubscriptionStatus.TRIAL
        ).count()
        
        # License metrics
        total_licenses = db.query(License).count()
        active_licenses = db.query(License).filter(
            License.status == LicenseStatus.ACTIVE
        ).count()
        
        return {
            "total_users": total_users,
            "active_users": active_users,
            "total_organizations": total_organizations,
            "active_organizations": active_organizations,
            "active_subscriptions": active_subscriptions,
            "trial_subscriptions": trial_subscriptions,
            "total_licenses": total_licenses,
            "active_licenses": active_licenses,
            "license_utilization_rate": round((active_licenses / total_licenses * 100) if total_licenses > 0 else 0, 2)
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

