from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
from decimal import Decimal
from app.database import get_db
from app.models.user import User
from app.models.subscription import Subscription
from app.models.license import License, LicenseStatus
from app.schemas.billing import (
    BillingStatusResponse, SubscriptionResponse, LicenseUsageResponse,
    PurchaseLicenseRequest, PurchaseLicenseResponse, PlanResponse
)
from app.dependencies.auth import require_admin_role

router = APIRouter()


@router.get("/subscription", response_model=BillingStatusResponse)
async def get_subscription_status(
    current_user: User = Depends(require_admin_role),
    db: Session = Depends(get_db)
):
    """Get current subscription status and license usage."""
    # Get current subscription
    subscription = db.query(Subscription).filter(
        Subscription.organization_id == current_user.organization_id
    ).first()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No subscription found"
        )
    
    # Get license usage
    total_licenses = db.query(License).filter(
        License.organization_id == current_user.organization_id
    ).count()
    
    active_licenses = db.query(License).filter(
        License.organization_id == current_user.organization_id,
        License.status == LicenseStatus.ACTIVE
    ).count()
    
    inactive_licenses = db.query(License).filter(
        License.organization_id == current_user.organization_id,
        License.status == LicenseStatus.INACTIVE
    ).count()
    
    available_licenses = db.query(License).filter(
        License.organization_id == current_user.organization_id,
        License.status == LicenseStatus.INACTIVE,
        License.user_id.is_(None)
    ).count()
    
    # Build subscription response
    subscription_response = SubscriptionResponse(
        id=subscription.id,
        status=subscription.status.value,
        current_period_start=subscription.current_period_start,
        current_period_end=subscription.current_period_end,
        trial_end=subscription.trial_end,
        canceled_at=subscription.canceled_at,
        plan=PlanResponse(
            id=subscription.plan.id,
            name=subscription.plan.name,
            display_name=subscription.plan.display_name,
            description=subscription.plan.description,
            price=subscription.plan.price,
            currency=subscription.plan.currency,
            max_users=subscription.plan.max_users,
            max_storage_gb=subscription.plan.max_storage_gb,
            features=subscription.plan.features,
            is_active=subscription.plan.is_active,
            is_system=subscription.plan.is_system
        ),
        created_at=subscription.created_at
    )
    
    # Build license usage response
    license_usage = LicenseUsageResponse(
        total_licenses=total_licenses,
        active_licenses=active_licenses,
        inactive_licenses=inactive_licenses,
        available_licenses=available_licenses
    )
    
    return BillingStatusResponse(
        subscription=subscription_response,
        license_usage=license_usage,
        plan_limit=subscription.plan.max_users
    )


@router.post("/licenses/purchase", response_model=PurchaseLicenseResponse)
async def purchase_additional_licenses(
    purchase_data: PurchaseLicenseRequest,
    current_user: User = Depends(require_admin_role),
    db: Session = Depends(get_db)
):
    """Purchase additional licenses for the organization."""
    if purchase_data.quantity <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Quantity must be greater than 0"
        )
    
    # Get current subscription
    subscription = db.query(Subscription).filter(
        Subscription.organization_id == current_user.organization_id
    ).first()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No subscription found"
        )
    
    if subscription.status.value not in ["active", "trial"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot purchase licenses with inactive subscription"
        )
    
    # Calculate cost (example: $10 per license)
    license_price = Decimal("10.00")
    total_cost = license_price * purchase_data.quantity
    
    # Create new inactive licenses
    new_licenses = []
    for _ in range(purchase_data.quantity):
        new_license = License(
            organization_id=current_user.organization_id,
            status=LicenseStatus.INACTIVE
        )
        new_licenses.append(new_license)
        db.add(new_license)
    
    db.commit()
    
    # Get new total count
    new_license_count = db.query(License).filter(
        License.organization_id == current_user.organization_id
    ).count()
    
    return PurchaseLicenseResponse(
        message=f"Successfully purchased {purchase_data.quantity} additional licenses",
        new_license_count=new_license_count,
        total_cost=total_cost
    )


@router.get("/plans", response_model=list[PlanResponse])
async def get_available_plans(
    current_user: User = Depends(require_admin_role),
    db: Session = Depends(get_db)
):
    """Get all available subscription plans."""
    from app.models.plan import Plan
    
    plans = db.query(Plan).filter(Plan.is_active == True).all()
    return plans


@router.post("/subscription/upgrade")
async def upgrade_subscription(
    plan_id: int,
    current_user: User = Depends(require_admin_role),
    db: Session = Depends(get_db)
):
    """Upgrade subscription to a different plan."""
    from app.models.plan import Plan
    
    # Get the new plan
    new_plan = db.query(Plan).filter(
        Plan.id == plan_id,
        Plan.is_active == True
    ).first()
    
    if not new_plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan not found"
        )
    
    # Get current subscription
    subscription = db.query(Subscription).filter(
        Subscription.organization_id == current_user.organization_id
    ).first()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No subscription found"
        )
    
    # Update subscription
    subscription.plan_id = new_plan.id
    subscription.updated_at = datetime.utcnow()
    
    # If upgrading to a plan with more users, create additional licenses
    current_license_count = db.query(License).filter(
        License.organization_id == current_user.organization_id
    ).count()
    
    if new_plan.max_users > current_license_count:
        licenses_to_add = new_plan.max_users - current_license_count
        for _ in range(licenses_to_add):
            new_license = License(
                organization_id=current_user.organization_id,
                status=LicenseStatus.INACTIVE
            )
            db.add(new_license)
    
    db.commit()
    
    return {"message": f"Successfully upgraded to {new_plan.display_name} plan"}


@router.post("/subscription/cancel")
async def cancel_subscription(
    current_user: User = Depends(require_admin_role),
    db: Session = Depends(get_db)
):
    """Cancel current subscription."""
    from app.models.subscription import SubscriptionStatus
    
    # Get current subscription
    subscription = db.query(Subscription).filter(
        Subscription.organization_id == current_user.organization_id
    ).first()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No subscription found"
        )
    
    if subscription.status == SubscriptionStatus.CANCELED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Subscription already canceled"
        )
    
    # Cancel subscription
    subscription.status = SubscriptionStatus.CANCELED
    subscription.canceled_at = datetime.utcnow()
    subscription.updated_at = datetime.utcnow()
    
    db.commit()
    
    return {"message": "Subscription canceled successfully", "canceled_at": subscription.canceled_at}