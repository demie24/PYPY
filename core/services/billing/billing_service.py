# core/services/billing/billing_service.py
# PYPY V11.9 — Production Billing Adapters (ToyyibPay + Stripe)

import os
import uuid
import hashlib
import hmac
import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# ─── Pricing Constants ────────────────────────────────────────────────────────

PLAN_PRICES: Dict[str, float] = {
    "free": 0.0,
    "academic_premium": 19.00,
    "research_lab": 49.00,
    "enterprise": 0.0,  # custom quote
}

PLAN_DISPLAY_NAMES: Dict[str, str] = {
    "free": "Free",
    "academic_premium": "Academic Premium",
    "research_lab": "Research Lab",
    "enterprise": "Enterprise",
}


# ─── Provider Abstraction ─────────────────────────────────────────────────────

class BillingProvider(ABC):
    """Abstract billing provider interface."""

    @abstractmethod
    def create_checkout_session(
        self, tenant_id: uuid.UUID, plan_name: str, cycle: str, amount: float
    ) -> Dict[str, Any]:
        """Create a hosted checkout session and return session data including payment URL."""
        pass

    @abstractmethod
    def verify_payment(self, payload: Dict[str, Any]) -> bool:
        """Verify an incoming webhook/callback payload. Returns True if payment is confirmed."""
        pass

    def verify_webhook_signature(self, raw_body: bytes, signature: str) -> bool:
        """Optional webhook signature verification. Override in production providers."""
        return True


# ─── Manual / Fallback Provider ───────────────────────────────────────────────

class ManualBillingProvider(BillingProvider):
    """Manual / offline billing (bank transfer, invoice). No real gateway."""

    def create_checkout_session(
        self, tenant_id: uuid.UUID, plan_name: str, cycle: str, amount: float
    ) -> Dict[str, Any]:
        ref = f"MANUAL_{uuid.uuid4().hex[:8].upper()}"
        return {
            "provider": "manual",
            "reference": ref,
            "url": f"/settings/billing?status=manual_pending&plan={plan_name}&ref={ref}",
            "instructions": "Please bank transfer to account details provided by admin.",
        }

    def verify_payment(self, payload: Dict[str, Any]) -> bool:
        return payload.get("admin_confirmed", True) is True


# ─── ToyyibPay Provider ───────────────────────────────────────────────────────

class ToyyibPayProvider(BillingProvider):
    """
    ToyyibPay billing adapter.
    Real API: https://toyyibpay.com/apireference/
    Env vars: TOYYIBPAY_USER_SECRET_KEY, TOYYIBPAY_CATEGORY_CODE
    """

    TOYYIBPAY_URL = "https://toyyibpay.com"

    def __init__(
        self,
        secret_key: str = None,
        category_code: str = None,
        sandbox: bool = None,
    ):
        self.secret_key = secret_key or os.environ.get("TOYYIBPAY_USER_SECRET_KEY", "mock_toyyibpay_secret")
        self.category_code = category_code or os.environ.get("TOYYIBPAY_CATEGORY_CODE", "MOCK_CAT")
        self.sandbox = sandbox if sandbox is not None else (os.environ.get("TOYYIBPAY_SANDBOX", "true").lower() == "true")
        self.base_url = "https://dev.toyyibpay.com" if self.sandbox else self.TOYYIBPAY_URL

    def create_checkout_session(
        self, tenant_id: uuid.UUID, plan_name: str, cycle: str, amount: float
    ) -> Dict[str, Any]:
        """Create a ToyyibPay bill and return redirect URL."""
        bill_code = f"BILL_{uuid.uuid4().hex[:8].upper()}"
        amount_cents = int(amount * 100)  # ToyyibPay uses cents

        # Attempt real API call
        try:
            import urllib.request
            import urllib.parse
            bill_ref = f"PYPY-{tenant_id.hex[:8].upper()}-{uuid.uuid4().hex[:4].upper()}"
            data = urllib.parse.urlencode({
                "userSecretKey": self.secret_key,
                "categoryCode": self.category_code,
                "billName": f"PYPY Grid {PLAN_DISPLAY_NAMES.get(plan_name, plan_name)}",
                "billDescription": f"PYPY Grid {plan_name} subscription ({cycle})",
                "billPriceSetting": 1,
                "billPayorInfo": 1,
                "billAmount": amount_cents,
                "billReturnUrl": f"https://pypygrid.com/billing/callback/toyyibpay",
                "billCallbackUrl": f"https://pypygrid.com/api/billing/webhook/toyyibpay",
                "billExternalReferenceNo": bill_ref,
                "billTo": "",
                "billEmail": "",
                "billPhone": "",
                "billSplitPayment": 0,
                "billPaymentChannel": 0,
                "billContentEmail": f"Thank you for subscribing to PYPY Grid {plan_name}.",
                "billChargeToCustomer": 1,
            }).encode()

            req = urllib.request.Request(
                f"{self.base_url}/index.php/api/createBill",
                data=data,
                method="POST",
            )
            req.add_header("Content-Type", "application/x-www-form-urlencoded")
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read().decode())
                if result and len(result) > 0 and "BillCode" in result[0]:
                    real_bill_code = result[0]["BillCode"]
                    return {
                        "provider": "toyyibpay",
                        "bill_code": real_bill_code,
                        "url": f"{self.base_url}/{real_bill_code}",
                        "amount": amount,
                        "plan": plan_name,
                    }
        except Exception as e:
            logger.warning(f"ToyyibPay API call failed ({e}), using mock bill code")

        # Fallback: mock for development/testing
        return {
            "provider": "toyyibpay",
            "bill_code": bill_code,
            "url": f"{self.base_url}/mock-gateway/{bill_code}",
            "amount": amount,
            "plan": plan_name,
            "_mock": True,
        }

    def verify_payment(self, payload: Dict[str, Any]) -> bool:
        """
        Verify ToyyibPay callback.
        ToyyibPay sends: status_id (1=success), billcode, order_id, msg, transaction_id
        """
        status_id = str(payload.get("status_id", payload.get("status", "0")))
        return status_id == "1"

    def verify_webhook_signature(self, raw_body: bytes, signature: str) -> bool:
        """Validate ToyyibPay callback using secret key hash."""
        try:
            params = dict(p.split("=") for p in raw_body.decode().split("&") if "=" in p)
            bill_code = params.get("billcode", "")
            expected = hashlib.md5(f"{bill_code}{self.secret_key}".encode()).hexdigest()
            return hmac.compare_digest(expected.lower(), signature.lower())
        except Exception:
            return False


# ─── Stripe Provider ──────────────────────────────────────────────────────────

class StripeProvider(BillingProvider):
    """
    Stripe billing adapter.
    Env vars: STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET
    """

    STRIPE_PRICE_IDS: Dict[str, Dict[str, str]] = {
        # Map plan_name+cycle → Stripe Price ID (configure in Stripe Dashboard)
        "academic_premium_monthly": os.environ.get("STRIPE_PRICE_ACADEMIC_MONTHLY", "price_academic_monthly"),
        "academic_premium_yearly": os.environ.get("STRIPE_PRICE_ACADEMIC_YEARLY", "price_academic_yearly"),
        "research_lab_monthly": os.environ.get("STRIPE_PRICE_RESEARCH_MONTHLY", "price_research_monthly"),
        "research_lab_yearly": os.environ.get("STRIPE_PRICE_RESEARCH_YEARLY", "price_research_yearly"),
    }

    def __init__(self, api_key: str = None, webhook_secret: str = None):
        self.api_key = api_key or os.environ.get("STRIPE_SECRET_KEY", "sk_test_mock")
        self.webhook_secret = webhook_secret or os.environ.get("STRIPE_WEBHOOK_SECRET", "whsec_mock")

    def create_checkout_session(
        self, tenant_id: uuid.UUID, plan_name: str, cycle: str, amount: float
    ) -> Dict[str, Any]:
        """Create Stripe Checkout Session. Falls back to mock if stripe SDK not installed."""
        price_key = f"{plan_name}_{cycle}"
        price_id = self.STRIPE_PRICE_IDS.get(price_key)

        try:
            import stripe
            stripe.api_key = self.api_key
            session = stripe.checkout.Session.create(
                mode="subscription",
                line_items=[{"price": price_id, "quantity": 1}] if price_id else [
                    {
                        "price_data": {
                            "currency": "myr",
                            "unit_amount": int(amount * 100),
                            "recurring": {"interval": "month" if cycle == "monthly" else "year"},
                            "product_data": {
                                "name": f"PYPY Grid {PLAN_DISPLAY_NAMES.get(plan_name, plan_name)}",
                                "description": f"PYPY Grid {plan_name} ({cycle}) subscription",
                            },
                        },
                        "quantity": 1,
                    }
                ],
                success_url="https://pypygrid.com/billing/callback/stripe?session_id={CHECKOUT_SESSION_ID}&status=success",
                cancel_url="https://pypygrid.com/settings/billing?status=cancelled",
                metadata={"tenant_id": str(tenant_id), "plan_name": plan_name, "cycle": cycle},
                client_reference_id=str(tenant_id),
            )
            return {
                "provider": "stripe",
                "session_id": session.id,
                "url": session.url,
                "amount": amount,
                "plan": plan_name,
            }
        except ImportError:
            logger.warning("stripe SDK not installed, using mock session")
        except Exception as e:
            logger.warning(f"Stripe API call failed ({e}), using mock session")

        # Fallback mock
        session_id = f"cs_test_{uuid.uuid4().hex}"
        return {
            "provider": "stripe",
            "session_id": session_id,
            "url": f"https://checkout.stripe.com/pay/{session_id}",
            "amount": amount,
            "plan": plan_name,
            "_mock": True,
        }

    def verify_payment(self, payload: Dict[str, Any]) -> bool:
        """Verify Stripe payment. Checks payment_status == 'paid' or event type."""
        return payload.get("payment_status") == "paid" or payload.get("type") == "checkout.session.completed"

    def verify_webhook_signature(self, raw_body: bytes, signature: str) -> bool:
        """Verify Stripe webhook signature using HMAC-SHA256."""
        try:
            import stripe
            stripe.Webhook.construct_event(raw_body, signature, self.webhook_secret)
            return True
        except ImportError:
            # Manual verification fallback
            try:
                parts = dict(p.split("=", 1) for p in signature.split(",") if "=" in p)
                timestamp = parts.get("t", "")
                v1_sig = parts.get("v1", "")
                signed_payload = f"{timestamp}.{raw_body.decode()}"
                expected = hmac.new(
                    self.webhook_secret.encode(),
                    signed_payload.encode(),
                    hashlib.sha256,
                ).hexdigest()
                return hmac.compare_digest(expected, v1_sig)
            except Exception:
                return False
        except Exception:
            return False


# ─── Factory ──────────────────────────────────────────────────────────────────

def get_billing_provider() -> BillingProvider:
    """
    Factory function: returns the configured billing provider.
    Reads BILLING_PROVIDER env var: 'toyyibpay' | 'stripe' | 'manual' | 'mock'
    """
    provider_name = os.environ.get("BILLING_PROVIDER", "manual").lower()
    if provider_name == "toyyibpay":
        return ToyyibPayProvider()
    elif provider_name == "stripe":
        return StripeProvider()
    else:
        return ManualBillingProvider()


# ─── Coupon Redemption ────────────────────────────────────────────────────────

def redeem_promo_coupon(db: Session, tenant_id: uuid.UUID, code: str) -> Dict[str, Any]:
    from services.auth.models import Coupon, CouponRedemption, Subscription, Tenant
    now = datetime.now(timezone.utc)

    coupon = db.query(Coupon).filter(Coupon.code == code).first()
    if not coupon or not coupon.is_active:
        raise ValueError("Invalid or inactive coupon code.")

    if coupon.valid_until and coupon.valid_until < now:
        raise ValueError("Coupon code has expired.")

    if coupon.used_count >= coupon.usage_limit:
        raise ValueError("Coupon usage limit has been reached.")

    redemption = db.query(CouponRedemption).filter(
        CouponRedemption.coupon_id == coupon.id,
        CouponRedemption.tenant_id == tenant_id
    ).first()
    if redemption:
        raise ValueError("Organization has already redeemed this coupon.")

    redemption = CouponRedemption(
        coupon_id=coupon.id,
        tenant_id=tenant_id,
        redeemed_at=now
    )
    db.add(redemption)

    coupon.used_count += 1
    if coupon.used_count >= coupon.usage_limit:
        coupon.is_active = False

    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    tenant.plan_tier = coupon.target_plan

    db.query(Subscription).filter(
        Subscription.tenant_id == tenant_id,
        Subscription.status.in_(["active", "trial"])
    ).update({"status": "cancelled"}, synchronize_session=False)

    expires_at = now + timedelta(days=coupon.duration_days)
    sub = Subscription(
        tenant_id=tenant_id,
        plan_name=coupon.target_plan,
        billing_cycle="one-time",
        amount=0.00,
        status="active",
        payment_provider="manual",
        payment_reference=f"COUPON_{code}",
        started_at=now,
        expires_at=expires_at,
        auto_renew=False
    )
    db.add(sub)
    db.commit()

    try:
        from workers.billing.tasks import unlock_tenant_experiments
        unlock_tenant_experiments(db, tenant_id)
    except Exception:
        pass

    return {
        "status": "SUCCESS",
        "plan_tier": coupon.target_plan,
        "expires_at": expires_at.isoformat()
    }

