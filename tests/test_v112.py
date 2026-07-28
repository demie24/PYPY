# tests/test_v112.py

import os
import sys
import uuid
import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Ensure core/ is in Python path for test execution context
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../core")))

from services.auth.models import Base, Tenant, User, Coupon, Subscription, Experiment
from services.billing.billing_service import (
    ManualBillingProvider, ToyyibPayProvider, StripeProvider, redeem_promo_coupon
)
from workers.billing.tasks import check_expired_trials

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    # Pre-populate some standard V11 coupons
    coupons = [
        Coupon(code="PYPY_ACADEMIC_FREE_30", target_plan="academic_premium", duration_days=30, usage_limit=10, is_active=True),
        Coupon(code="PYPY_ACADEMIC_FREE_90", target_plan="academic_premium", duration_days=90, usage_limit=10, is_active=True),
        Coupon(code="ENTERPRISE_DEMO_30", target_plan="enterprise", duration_days=30, usage_limit=10, is_active=True),
        Coupon(code="UNIMAP_RESEARCH_180", target_plan="academic_premium", duration_days=180, usage_limit=10, is_active=True),
        Coupon(code="UNIMAP2026", target_plan="academic_premium", duration_days=365, usage_limit=100, is_active=True),
        Coupon(code="USM2026", target_plan="academic_premium", duration_days=365, usage_limit=100, is_active=True),
        Coupon(code="UTM2026", target_plan="academic_premium", duration_days=365, usage_limit=100, is_active=True),
        Coupon(code="RESEARCH_LAB_2026", target_plan="research_lab", duration_days=365, usage_limit=100, is_active=True)
    ]
    for c in coupons:
        session.add(c)
    session.commit()
    
    try:
        yield session
    finally:
        session.close()

def test_payment_provider_agnosticism():
    tenant_id = uuid.uuid4()
    
    # 1. Test Manual provider
    manual = ManualBillingProvider()
    res = manual.create_checkout_session(tenant_id, "academic_premium", "monthly", 49.00)
    assert res["provider"] == "manual"
    assert "manual_pending" in res["url"]
    assert manual.verify_payment({}) is True
    
    # 2. Test ToyyibPay provider
    toyyib = ToyyibPayProvider()
    res_t = toyyib.create_checkout_session(tenant_id, "academic_premium", "monthly", 49.00)
    assert res_t["provider"] == "toyyibpay"
    assert "mock-gateway" in res_t["url"]
    assert toyyib.verify_payment({"status": "1"}) is True
    assert toyyib.verify_payment({"status": "0"}) is False
    
    # 3. Test Stripe provider
    stripe = StripeProvider()
    res_s = stripe.create_checkout_session(tenant_id, "academic_premium", "monthly", 49.00)
    assert res_s["provider"] == "stripe"
    assert "checkout.stripe.com" in res_s["url"]
    assert stripe.verify_payment({"payment_status": "paid"}) is True
    assert stripe.verify_payment({"payment_status": "unpaid"}) is False

def test_coupon_redemption_and_unlocked_experiments(db_session):
    # Setup tenant
    tenant = Tenant(name="Test University", subdomain="testuni", plan_tier="free")
    db_session.add(tenant)
    db_session.flush()
    
    # Setup user
    user = User(tenant_id=tenant.id, email="user@testuni.edu", password_hash="hash")
    db_session.add(user)
    db_session.flush()
    
    # Add a mock locked experiment (excess)
    exp = Experiment(
        tenant_id=tenant.id,
        user_id=user.id,
        name="Locked Analysis",
        grid_type="IEEE118",
        archived=True,
        locked=True,
        read_only=True
    )
    db_session.add(exp)
    db_session.commit()
    
    # Redeem coupon
    res = redeem_promo_coupon(db_session, tenant.id, "UNIMAP_RESEARCH_180")
    assert res["status"] == "SUCCESS"
    assert res["plan_tier"] == "academic_premium"
    
    # Verify tenant state is upgraded
    assert tenant.plan_tier == "academic_premium"
    
    # Verify experiment is unlocked
    db_session.refresh(exp)
    assert exp.locked is False
    assert exp.archived is False
    assert exp.read_only is False

def test_expired_trial_downgrade_and_locking(db_session):
    # Setup tenant
    tenant = Tenant(name="Expired Lab", subdomain="expired", plan_tier="academic_premium")
    db_session.add(tenant)
    db_session.flush()
    
    # Setup user
    user = User(tenant_id=tenant.id, email="user@expired.edu", password_hash="hash")
    db_session.add(user)
    db_session.flush()
    
    # Create expired trial subscription
    expired_time = datetime.now(timezone.utc) - timedelta(hours=2)
    expired_sub = Subscription(
        tenant_id=tenant.id,
        plan_name="academic_premium",
        billing_cycle="one-time",
        amount=0.00,
        status="trial",
        payment_provider="manual",
        payment_reference="TRIAL_EXPIRED_REF",
        started_at=expired_time - timedelta(days=30),
        expires_at=expired_time,
        auto_renew=False
    )
    db_session.add(expired_sub)
    
    # Add 12 experiments (limit is 10 for free plan)
    for i in range(12):
        exp = Experiment(
            tenant_id=tenant.id,
            user_id=user.id,
            name=f"Exp {i}",
            grid_type="IEEE14",
            created_at=datetime.now(timezone.utc) - timedelta(minutes=i)
        )
        db_session.add(exp)
        
    db_session.commit()
    
    # Run the worker trial expiration task logic (mocking the context manager)
    # We patch workers.billing.tasks.get_db_context inside test logic
    import workers.billing.tasks
    from contextlib import contextmanager
    @contextmanager
    def mock_db_ctx():
        yield db_session
    
    original_get_db = getattr(workers.billing.tasks, "get_db_context", None)
    workers.billing.tasks.get_db_context = mock_db_ctx
    
    try:
        check_expired_trials()
    finally:
        if original_get_db:
            workers.billing.tasks.get_db_context = original_get_db
        
    # Verify tenant downgraded
    db_session.refresh(tenant)
    assert tenant.plan_tier == "free"
    
    # Verify subscription status is expired
    db_session.refresh(expired_sub)
    assert expired_sub.status == "expired"
    
    # Verify 2 oldest experiments are archived and locked (since we ordered by desc, the oldest 2 in index 10: are locked)
    locked_count = db_session.query(Experiment).filter(
        Experiment.tenant_id == tenant.id,
        Experiment.locked == True
    ).count()
    assert locked_count == 2

def test_academic_coupons_redemption(db_session):
    # Setup tenant
    tenant = Tenant(name="UTM Laboratory", subdomain="utmlab", plan_tier="free")
    db_session.add(tenant)
    db_session.commit()

    # Redeem USM2026
    res = redeem_promo_coupon(db_session, tenant.id, "USM2026")
    assert res["status"] == "SUCCESS"
    assert res["plan_tier"] == "academic_premium"
    assert tenant.plan_tier == "academic_premium"

    # Redeem RESEARCH_LAB_2026
    res_lab = redeem_promo_coupon(db_session, tenant.id, "RESEARCH_LAB_2026")
    assert res_lab["status"] == "SUCCESS"
    assert res_lab["plan_tier"] == "research_lab"
    assert tenant.plan_tier == "research_lab"

