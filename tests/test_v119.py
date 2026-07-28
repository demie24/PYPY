# tests/test_v119.py
"""
PYPY V11.9 — Commercial Launch Readiness
Pytest test suite validating all commercial launch components:
  1. V11.9 DB Models (UserNotification, SupportTicket, WorkspaceProfile)
  2. Email templates (8 templates, HTML structure, required fields)
  3. Billing adapters (ToyyibPay/Stripe abstractions, pricing constants)
  4. Analytics routes (import, structure)
  5. Admin portal routes (import, structure)
  6. Auth route extensions (/me, /workspace/setup, /notifications)
  7. File integrity (all V11.9 files present)
  8. Brand config (TypeScript file present and complete)
  9. Legal documents (5 docs, minimum word counts)
  10. Documentation (5 docs, minimum word counts)
"""

import os
import sys
import uuid
import json
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../core")))
_core = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../core")
if _core not in sys.path:
    sys.path.insert(0, _core)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


# ─── Test Database ────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def db():
    from services.auth.models import Base
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture(scope="module")
def seed_tenant_user(db):
    from services.auth.models import Tenant, User
    import bcrypt
    tenant = Tenant(
        id=uuid.uuid4(),
        name="V119 Test Tenant",
        subdomain=f"v119-{uuid.uuid4().hex[:6]}",
        plan_tier="academic_premium",
    )
    db.add(tenant)
    db.flush()
    user = User(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        email=f"v119-{uuid.uuid4().hex[:6]}@test.com",
        password_hash=bcrypt.hashpw(b"testpass123", bcrypt.gensalt()).decode(),
        role="admin",
        email_verified=True,
    )
    db.add(user)
    db.commit()
    return tenant, user


# ═══════════════════════════════════════════════════════════════════════════════
# 1. V11.9 Database Models
# ═══════════════════════════════════════════════════════════════════════════════

class TestV119Models:
    def test_all_v119_models_importable(self):
        """UserNotification, SupportTicket, WorkspaceProfile must be importable."""
        from services.auth.models import UserNotification, SupportTicket, WorkspaceProfile
        for cls in [UserNotification, SupportTicket, WorkspaceProfile]:
            assert hasattr(cls, "__tablename__")

    def test_user_notification_insert(self, db, seed_tenant_user):
        from services.auth.models import UserNotification
        tenant, user = seed_tenant_user
        n = UserNotification(
            user_id=user.id,
            tenant_id=tenant.id,
            type="billing",
            title="Subscription activated",
            message="Your Academic Premium plan is now active.",
            read=False,
        )
        db.add(n)
        db.commit()
        fetched = db.query(UserNotification).filter(UserNotification.user_id == user.id).first()
        assert fetched is not None
        assert fetched.type == "billing"

    def test_support_ticket_insert(self, db, seed_tenant_user):
        from services.auth.models import SupportTicket
        tenant, user = seed_tenant_user
        t = SupportTicket(
            tenant_id=tenant.id,
            user_id=user.id,
            subject="Cannot access IEEE-39 simulation",
            description="Getting 503 error when launching simulation.",
            category="technical",
            priority="high",
            status="open",
        )
        db.add(t)
        db.commit()
        fetched = db.query(SupportTicket).filter(SupportTicket.user_id == user.id).first()
        assert fetched is not None
        assert fetched.priority == "high"
        assert fetched.status == "open"

    def test_workspace_profile_insert_and_update(self, db, seed_tenant_user):
        from services.auth.models import WorkspaceProfile
        _, user = seed_tenant_user
        wp = WorkspaceProfile(
            user_id=user.id,
            institution="Universiti Malaya",
            research_focus="grid_security",
            country="Malaysia",
            preferred_grid="IEEE39",
            setup_completed=True,
        )
        db.add(wp)
        db.commit()
        fetched = db.query(WorkspaceProfile).filter(WorkspaceProfile.user_id == user.id).first()
        assert fetched is not None
        assert fetched.setup_completed is True
        assert fetched.preferred_grid == "IEEE39"

    def test_v119_tables_exist(self, db):
        from services.auth.models import Base
        tables = list(Base.metadata.tables.keys())
        for expected in ["user_notifications", "support_tickets", "workspace_profiles"]:
            assert expected in tables, f"Table '{expected}' missing from schema"


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Email Templates
# ═══════════════════════════════════════════════════════════════════════════════

class TestEmailTemplates:
    @pytest.fixture(autouse=True)
    def import_templates(self):
        from services.email import templates
        self.templates = templates

    def test_welcome_email_returns_tuple(self):
        result = self.templates.welcome_email("Alice", "https://pypygrid.com")
        assert isinstance(result, tuple) and len(result) == 3
        subject, html, text = result
        assert "PYPY" in html or "Protect" in html
        assert "Alice" in html

    def test_verify_email_contains_link(self):
        url = "https://pypygrid.com/verify?token=abc123"
        _, html, text = self.templates.verify_email("Bob", url)
        assert url in html or url in text

    def test_reset_password_contains_link(self):
        url = "https://pypygrid.com/reset?token=xyz"
        _, html, text = self.templates.reset_password("Carol", url)
        assert url in html or url in text

    def test_subscription_activated_contains_plan(self):
        _, html, text = self.templates.subscription_activated("Dave", "Academic Premium", "2026-08-01")
        assert "Academic Premium" in html

    def test_subscription_expiring_contains_days(self):
        _, html, text = self.templates.subscription_expiring("Eve", "Research Lab", 7, "https://pypygrid.com/billing")
        assert "7" in html or "7" in text

    def test_invoice_email_contains_amount(self):
        _, html, text = self.templates.invoice_email("Frank", "INV-2026-001", 19.00, "Academic Premium", "Jul 2026", "2026-07-01")
        assert "19" in html or "19.00" in html

    def test_backup_completed_contains_filename(self):
        _, html, text = self.templates.backup_completed("Grace", "backup_20260701.sql.gz", 4.2, "2026-07-01")
        assert "backup_20260701.sql.gz" in html or "backup_20260701.sql.gz" in text

    def test_simulation_finished_contains_score(self):
        _, html, text = self.templates.simulation_finished("Henry", "Coordinated Tripping", "DEGRADED", 91.5, "run-abc123")
        assert "91" in html or "91.5" in html or "91.5" in text

    def test_all_templates_have_html_structure(self):
        templates_funcs = [
            lambda: self.templates.welcome_email("Test", "https://pypygrid.com"),
            lambda: self.templates.verify_email("Test", "https://pypygrid.com/verify"),
            lambda: self.templates.reset_password("Test", "https://pypygrid.com/reset"),
            lambda: self.templates.subscription_activated("Test", "Free", "2026-08-01"),
            lambda: self.templates.subscription_expiring("Test", "Free", 3, "https://pypygrid.com"),
            lambda: self.templates.invoice_email("Test", "INV-001", 0, "Free", "Jul 2026", "2026-07-01"),
            lambda: self.templates.backup_completed("Test", "backup.sql.gz", 1.0, "2026-07-01"),
            lambda: self.templates.simulation_finished("Test", "Scenario", "NOMINAL", 100.0, "run-1"),
        ]
        for fn in templates_funcs:
            subject, html, text = fn()
            assert "<html" in html.lower() or "<div" in html.lower(), "Template missing HTML structure"
            assert len(subject) > 0
            assert len(text) > 0


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Billing Service
# ═══════════════════════════════════════════════════════════════════════════════

class TestBillingService:
    def test_plan_prices_constant_exists(self):
        from services.billing.billing_service import PLAN_PRICES
        assert "free" in PLAN_PRICES
        assert "academic_premium" in PLAN_PRICES
        assert "research_lab" in PLAN_PRICES
        assert PLAN_PRICES["free"] == 0
        assert PLAN_PRICES["academic_premium"] == pytest.approx(19.00, abs=0.01)
        assert PLAN_PRICES["research_lab"] == pytest.approx(49.00, abs=0.01)

    def test_toyyibpay_provider_has_required_methods(self):
        from services.billing.billing_service import ToyyibPayProvider
        provider = ToyyibPayProvider()
        assert callable(getattr(provider, "create_checkout_session", None))
        assert callable(getattr(provider, "verify_payment", None))

    def test_stripe_provider_has_required_methods(self):
        from services.billing.billing_service import StripeProvider
        provider = StripeProvider()
        assert callable(getattr(provider, "create_checkout_session", None))
        assert callable(getattr(provider, "verify_payment", None))

    def test_toyyibpay_checkout_session_structure(self):
        from services.billing.billing_service import ToyyibPayProvider
        provider = ToyyibPayProvider()
        session = provider.create_checkout_session(uuid.uuid4(), "academic_premium", "monthly", 19.00)
        assert "provider" in session
        assert session["provider"] == "toyyibpay"
        assert "url" in session

    def test_stripe_checkout_session_structure(self):
        from services.billing.billing_service import StripeProvider
        provider = StripeProvider()
        session = provider.create_checkout_session(uuid.uuid4(), "research_lab", "monthly", 49.00)
        assert "provider" in session
        assert session["provider"] == "stripe"
        assert "url" in session

    def test_get_billing_provider_factory_returns_provider(self):
        from services.billing.billing_service import get_billing_provider
        provider = get_billing_provider()
        assert callable(getattr(provider, "create_checkout_session", None))

    def test_billing_provider_env_switching(self, monkeypatch):
        monkeypatch.setenv("BILLING_PROVIDER", "toyyibpay")
        from services.billing import billing_service
        import importlib
        importlib.reload(billing_service)
        provider = billing_service.get_billing_provider()
        assert provider.__class__.__name__ == "ToyyibPayProvider"


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Analytics Routes
# ═══════════════════════════════════════════════════════════════════════════════

class TestAnalyticsRoutes:
    def test_analytics_router_importable(self):
        import gateway.routes.analytics
        with patch("gateway.routes.analytics.get_db"), \
             patch("gateway.routes.analytics.get_current_user_claims"):
            from gateway.routes.analytics import router
            assert router.prefix in ("/analytics", "/api/analytics", "")

    def test_analytics_routes_defined(self):
        import gateway.routes.analytics
        with patch("gateway.routes.analytics.get_db"), \
             patch("gateway.routes.analytics.get_current_user_claims"):
            from gateway.routes.analytics import router
            paths = [r.path for r in router.routes]
            for expected in ["/overview", "/revenue", "/users", "/simulations", "/plan-distribution"]:
                assert any(expected in p for p in paths), f"Route {expected} missing"


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Admin Portal Routes
# ═══════════════════════════════════════════════════════════════════════════════

class TestAdminPortalRoutes:
    def test_admin_router_importable(self):
        import gateway.routes.admin_portal
        with patch("gateway.routes.admin_portal.get_db"), \
             patch("gateway.routes.admin_portal.get_current_user_claims"):
            from gateway.routes.admin_portal import router
            assert router.prefix in ("/admin", "/api/admin", "")

    def test_admin_routes_defined(self):
        import gateway.routes.admin_portal
        with patch("gateway.routes.admin_portal.get_db"), \
             patch("gateway.routes.admin_portal.get_current_user_claims"):
            from gateway.routes.admin_portal import router
            paths = [r.path for r in router.routes]
            for expected in ["/users", "/tenants", "/subscriptions", "/coupons", "/statistics"]:
                assert any(expected in p for p in paths), f"Admin route {expected} missing"


# ═══════════════════════════════════════════════════════════════════════════════
# 6. File Integrity — All V11.9 files must exist
# ═══════════════════════════════════════════════════════════════════════════════

class TestFileIntegrity:
    REQUIRED_FILES = [
        # Backend
        "core/services/email/templates.py",
        "core/gateway/routes/analytics.py",
        "core/gateway/routes/admin_portal.py",
        # Frontend
        "dashboard/src/components/LandingPage.tsx",
        "dashboard/src/components/AuthPages.tsx",
        "dashboard/src/components/UserDashboard.tsx",
        "dashboard/src/components/WorkspaceSetupWizard.tsx",
        "dashboard/src/components/BusinessAnalytics.tsx",
        # Content
        "docs/legal/privacy_policy.md",
        "docs/legal/terms_of_service.md",
        "docs/legal/cookie_policy.md",
        "docs/legal/acceptable_use_policy.md",
        "docs/legal/academic_license.md",
        "docs/USER_GUIDE.md",
        "docs/ADMIN_GUIDE.md",
        "docs/DEPLOYMENT_CHECKLIST.md",
        "docs/COMMERCIAL_READINESS.md",
        ".env.production",
        ".env.example",
        "nginx/pypy_grid_production.conf",
    ]

    @pytest.mark.parametrize("filepath", REQUIRED_FILES)
    def test_required_file_exists(self, filepath):
        full = os.path.join(PROJECT_ROOT, filepath)
        assert os.path.exists(full), f"Required file missing: {filepath}"

    def test_branding_config_exists(self):
        """BrandingConfig.ts or BrandingConfig.tsx must exist."""
        ts = os.path.join(PROJECT_ROOT, "dashboard/src/BrandingConfig.ts")
        tsx = os.path.join(PROJECT_ROOT, "dashboard/src/BrandingConfig.tsx")
        assert os.path.exists(ts) or os.path.exists(tsx), "BrandingConfig.ts missing"


# ═══════════════════════════════════════════════════════════════════════════════
# 7. Documentation Minimum Word Counts
# ═══════════════════════════════════════════════════════════════════════════════

class TestDocumentationQuality:
    DOC_MINIMUMS = {
        "docs/USER_GUIDE.md": 2500,
        "docs/ADMIN_GUIDE.md": 2000,
        "docs/DEPLOYMENT_CHECKLIST.md": 1500,
        "docs/COMMERCIAL_READINESS.md": 2000,
        "docs/legal/privacy_policy.md": 2000,
        "docs/legal/terms_of_service.md": 2000,
        "docs/legal/cookie_policy.md": 800,
        "docs/legal/acceptable_use_policy.md": 800,
        "docs/legal/academic_license.md": 800,
    }

    @pytest.mark.parametrize("filepath,min_words", list(DOC_MINIMUMS.items()))
    def test_document_meets_minimum_word_count(self, filepath, min_words):
        full = os.path.join(PROJECT_ROOT, filepath)
        if not os.path.exists(full):
            pytest.skip(f"File not yet created: {filepath}")
        content = open(full).read()
        word_count = len(content.split())
        assert word_count >= min_words, f"{filepath}: {word_count} words < {min_words} minimum"


# ═══════════════════════════════════════════════════════════════════════════════
# 8. LandingPage Component Completeness
# ═══════════════════════════════════════════════════════════════════════════════

class TestLandingPageCompleteness:
    def test_landing_page_has_all_sections(self):
        path = os.path.join(PROJECT_ROOT, "dashboard/src/components/LandingPage.tsx")
        if not os.path.exists(path):
            pytest.skip("LandingPage.tsx not yet created")
        content = open(path).read().lower()
        for section in ["hero", "feature", "pricing", "faq", "footer", "testimonial"]:
            assert section in content, f"Landing page missing section: {section}"

    def test_landing_page_has_pricing_tiers(self):
        path = os.path.join(PROJECT_ROOT, "dashboard/src/components/LandingPage.tsx")
        if not os.path.exists(path):
            pytest.skip("LandingPage.tsx not yet created")
        content = open(path).read()
        for tier in ["Free", "Academic", "Research"]:
            assert tier in content, f"Missing pricing tier: {tier}"

    def test_landing_page_has_cta_buttons(self):
        path = os.path.join(PROJECT_ROOT, "dashboard/src/components/LandingPage.tsx")
        if not os.path.exists(path):
            pytest.skip("LandingPage.tsx not yet created")
        content = open(path).read()
        for cta in ["Start Free", "onNavigate"]:
            assert cta in content, f"Missing CTA: {cta}"


# ═══════════════════════════════════════════════════════════════════════════════
# 9. Auth Pages Component
# ═══════════════════════════════════════════════════════════════════════════════

class TestAuthPagesComponent:
    def test_auth_pages_has_all_modes(self):
        path = os.path.join(PROJECT_ROOT, "dashboard/src/components/AuthPages.tsx")
        if not os.path.exists(path):
            pytest.skip("AuthPages.tsx not yet created")
        content = open(path).read()
        for mode in ["login", "register", "forgot_password", "reset_password", "verify_email"]:
            assert mode in content, f"AuthPages missing mode: {mode}"


# ═══════════════════════════════════════════════════════════════════════════════
# 10. Environment Files Completeness
# ═══════════════════════════════════════════════════════════════════════════════

class TestEnvFiles:
    REQUIRED_ENV_VARS = [
        "DATABASE_URL", "SECRET_KEY", "REDIS_URL",
        "BILLING_PROVIDER", "SENDGRID_API_KEY",
        "SMTP_HOST", "TOYYIBPAY_API_KEY", "STRIPE_SECRET_KEY",
    ]

    def test_env_production_has_required_vars(self):
        path = os.path.join(PROJECT_ROOT, ".env.production")
        if not os.path.exists(path):
            pytest.skip(".env.production not yet created")
        content = open(path).read()
        for var in self.REQUIRED_ENV_VARS:
            assert var in content, f".env.production missing: {var}"

    def test_env_example_has_required_vars(self):
        path = os.path.join(PROJECT_ROOT, ".env.example")
        if not os.path.exists(path):
            pytest.skip(".env.example not yet created")
        content = open(path).read()
        for var in self.REQUIRED_ENV_VARS:
            assert var in content, f".env.example missing: {var}"
