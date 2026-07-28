# core/gateway/routes/billing.py

from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from services.auth.session import get_db
from services.auth.auth_service import get_current_user_claims
from services.billing.billing_service import redeem_promo_coupon, ManualBillingProvider
from services.auth.models import UsageMetric, Subscription, Tenant
from datetime import datetime, timezone

router = APIRouter(prefix="/billing", tags=["billing"])

class CouponRedeemSchema(BaseModel):
    code: str

class PlanUpgradeSchema(BaseModel):
    plan_name: str

@router.post("/redeem-coupon")
def redeem_coupon(payload: CouponRedeemSchema, claims: dict = Depends(get_current_user_claims), db: Session = Depends(get_db)):
    tenant_id = claims.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=400, detail="User JWT lacks tenant identity claims.")
    try:
        result = redeem_promo_coupon(db, tenant_id, payload.code)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/checkout")
def create_checkout(payload: PlanUpgradeSchema, claims: dict = Depends(get_current_user_claims), db: Session = Depends(get_db)):
    tenant_id = claims.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=400, detail="User JWT lacks tenant identity claims.")
        
    # Check plan tier valid options
    valid_plans = ["free", "academic_premium", "research_lab", "enterprise"]
    if payload.plan_name not in valid_plans:
        raise HTTPException(status_code=400, detail=f"Invalid plan name. Choose from {valid_plans}")

    # Determine amount (RM 19 for academic_premium, RM 49 for research_lab)
    if payload.plan_name == "academic_premium":
        amount = 19.00
    elif payload.plan_name == "research_lab":
        amount = 49.00
    else:
        amount = 0.00
        
    # Agnostic checkout selection via providers
    from services.billing.billing_service import StripeProvider, ToyyibPayProvider, ManualBillingProvider
    import os
    
    provider_type = os.getenv("BILLING_PROVIDER", "manual").lower()
    if provider_type == "stripe":
        provider = StripeProvider()
    elif provider_type == "toyyibpay":
        provider = ToyyibPayProvider()
    else:
        provider = ManualBillingProvider()
        
    checkout = provider.create_checkout_session(tenant_id, payload.plan_name, "monthly", amount)
    return checkout

@router.post("/webhook/stripe")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    import json
    import os
    body = await request.body()
    payload = json.loads(body.decode("utf-8"))
    
    # Verify Stripe Signature if configured
    sig_header = request.headers.get("stripe-signature")
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
    if webhook_secret and sig_header:
        import stripe
        try:
            event = stripe.Webhook.construct_event(body, sig_header, webhook_secret)
            payload = event.to_dict()
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Stripe Webhook Signature Verification Failed: {str(e)}")
            
    # Process event
    event_type = payload.get("type")
    data_obj = payload.get("data", {}).get("object", {})
    
    if event_type == "checkout.session.completed":
        metadata = data_obj.get("metadata", {})
        tenant_uuid_str = metadata.get("tenant_id")
        plan_name = metadata.get("plan_name", "academic_premium")
        cycle = metadata.get("billing_cycle", "monthly")
        amount = float(metadata.get("amount", "19.00"))
        
        if tenant_uuid_str:
            import uuid
            tenant_id = uuid.UUID(tenant_uuid_str)
            tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
            if tenant:
                tenant.plan_tier = plan_name
                
                # Deactivate older subscriptions
                db.query(Subscription).filter(
                    Subscription.tenant_id == tenant_id,
                    Subscription.status.in_(["active", "trial"])
                ).update({"status": "cancelled"}, synchronize_session=False)
                
                # Insert active subscription
                started_at = datetime.now(timezone.utc)
                expires_at = started_at + timedelta(days=365 if cycle == "yearly" else 30)
                
                sub = Subscription(
                    tenant_id=tenant_id,
                    plan_name=plan_name,
                    billing_cycle=cycle,
                    amount=amount,
                    status="active",
                    payment_provider="stripe",
                    payment_reference=data_obj.get("id", f"ST_{uuid.uuid4().hex[:8].upper()}"),
                    started_at=started_at,
                    expires_at=expires_at,
                    auto_renew=True
                )
                db.add(sub)
                db.commit()
                
                # Unlock archived runs
                from workers.billing.tasks import unlock_tenant_experiments
                unlock_tenant_experiments(db, tenant_id)

                # Send email notifications for subscription activated and invoice
                try:
                    from services.auth.models import User
                    from services.email.email_service import get_email_provider
                    from services.email.templates import subscription_activated, invoice_email
                    admin_user = db.query(User).filter(User.tenant_id == tenant_id, User.role == "admin").first()
                    if admin_user:
                        provider = get_email_provider()
                        expires_str = expires_at.strftime("%Y-%m-%d")
                        sub_subject, sub_html, sub_text = subscription_activated(
                            admin_user.first_name or "Researcher", plan_name, expires_str
                        )
                        provider.send_email(admin_user.email, sub_subject, sub_text, sub_html)
                        
                        inv_ref = sub.payment_reference or f"INV_{uuid.uuid4().hex[:8].upper()}"
                        inv_subject, inv_html, inv_text = invoice_email(
                            admin_user.first_name or "Researcher",
                            inv_ref,
                            amount,
                            plan_name,
                            cycle,
                            started_at.strftime("%Y-%m-%d")
                        )
                        provider.send_email(admin_user.email, inv_subject, inv_text, inv_html)
                except Exception:
                    pass
                
    elif event_type in ("customer.subscription.deleted", "customer.subscription.updated"):
        # Handle subscription cancel/expiry
        status_str = data_obj.get("status")
        if status_str in ("canceled", "unpaid", "incomplete_expired"):
            # Revert to Free
            sub_id = data_obj.get("id")
            sub = db.query(Subscription).filter(Subscription.payment_reference == sub_id).first()
            if sub:
                sub.status = "expired"
                tenant = db.query(Tenant).filter(Tenant.id == sub.tenant_id).first()
                if tenant:
                    tenant.plan_tier = "free"
                    db.commit()
                    # Trigger lockout archive task
                    from workers.billing.tasks import lock_excess_tenant_experiments
                    lock_excess_tenant_experiments(db, tenant.id)
                    
    return {"status": "SUCCESS"}

@router.post("/webhook/toyyibpay")
async def toyyibpay_webhook(request: Request, db: Session = Depends(get_db)):
    import os
    import uuid
    # Parse form elements or query params
    form_data = await request.form()
    
    # Required keys mapping: status, billcode, refno, amount, reason, transaction_time
    status_code = form_data.get("status")
    bill_code = form_data.get("billcode")
    ref_no = form_data.get("refno")
    
    # Process only successful status = 1
    if status_code == "1" and bill_code:
        # Find matching subscription reference
        sub = db.query(Subscription).filter(Subscription.payment_reference == bill_code).first()
        if sub:
            sub.status = "active"
            tenant = db.query(Tenant).filter(Tenant.id == sub.tenant_id).first()
            if tenant:
                tenant.plan_tier = sub.plan_name
                
                # Re-activate expired / lock scenarios
                from workers.billing.tasks import unlock_tenant_experiments
                unlock_tenant_experiments(db, sub.tenant_id)
                
                db.commit()

                # Send email notifications for subscription activated and invoice
                try:
                    from services.auth.models import User
                    from services.email.email_service import get_email_provider
                    from services.email.templates import subscription_activated, invoice_email
                    admin_user = db.query(User).filter(User.tenant_id == sub.tenant_id, User.role == "admin").first()
                    if admin_user:
                        provider = get_email_provider()
                        expires_str = sub.expires_at.strftime("%Y-%m-%d") if sub.expires_at else "N/A"
                        sub_subject, sub_html, sub_text = subscription_activated(
                            admin_user.first_name or "Researcher", sub.plan_name, expires_str
                        )
                        provider.send_email(admin_user.email, sub_subject, sub_text, sub_html)
                        
                        inv_subject, inv_html, inv_text = invoice_email(
                            admin_user.first_name or "Researcher",
                            sub.payment_reference,
                            float(sub.amount) if sub.amount else 0.0,
                            sub.plan_name,
                            sub.billing_cycle or "monthly",
                            datetime.now(timezone.utc).strftime("%Y-%m-%d")
                        )
                        provider.send_email(admin_user.email, inv_subject, inv_text, inv_html)
                except Exception:
                    pass
                
    return {"status": "SUCCESS"}

@router.get("/metrics")
def get_billing_metrics(claims: dict = Depends(get_current_user_claims), db: Session = Depends(get_db)):
    tenant_id = claims.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=400, detail="User JWT lacks tenant identity claims.")
        
    current_period = datetime.now(timezone.utc).strftime("%Y-%m")
    
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    sub = db.query(Subscription).filter(
        Subscription.tenant_id == tenant_id,
        Subscription.status.in_(["active", "trial"])
    ).first()
    
    metrics = db.query(UsageMetric).filter(
        UsageMetric.tenant_id == tenant_id,
        UsageMetric.period == current_period
    ).first()
    
    days_remaining = 0
    if sub and sub.expires_at:
        now = datetime.now(sub.expires_at.tzinfo or timezone.utc)
        delta = sub.expires_at - now
        days_remaining = max(0, delta.days)
        
    return {
        "plan_tier": tenant.plan_tier if tenant else "free",
        "subscription_status": sub.status if sub else "inactive",
        "expires_at": sub.expires_at.isoformat() if sub and sub.expires_at else None,
        "days_remaining": days_remaining,
        "usage": {
            "simulations_run": metrics.simulations_run if metrics else 0,
            "ai_messages_used": metrics.ai_messages_used if metrics else 0,
            "reports_generated": metrics.reports_generated if metrics else 0,
            "storage_used_mb": float(metrics.storage_used_mb) if metrics and metrics.storage_used_mb else 0.0
        }
    }
