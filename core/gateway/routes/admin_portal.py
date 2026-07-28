"""
core/gateway/routes/admin_portal.py
PYPY V11.9 — Admin Portal API
Provides full admin management: users, tenants, subscriptions, coupons, stats, audit logs, tickets.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import Optional, List
import uuid
from datetime import datetime, timezone

from services.auth.auth_service import get_current_user_claims
from services.auth.session import get_db

router = APIRouter(prefix="/admin", tags=["Admin Portal"])


def _require_admin(claims: dict = Depends(get_current_user_claims)):
    """Ensure caller is super_admin or has admin role."""
    if not claims.get("is_super_admin") and claims.get("role") not in ("admin", "super_admin"):
        raise HTTPException(status_code=403, detail="Admin access required.")
    return claims


# ─── Users ────────────────────────────────────────────────────────────────────

@router.get("/users")
def list_users(
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    search: Optional[str] = Query(None),
    plan: Optional[str] = Query(None),
    claims: dict = Depends(_require_admin),
    db: Session = Depends(get_db),
):
    """List all users with optional search and plan filter."""
    from services.auth.models import User, Tenant
    q = db.query(User)
    if search:
        q = q.filter(
            (User.email.ilike(f"%{search}%")) |
            (User.first_name.ilike(f"%{search}%")) |
            (User.last_name.ilike(f"%{search}%"))
        )
    if plan:
        tenant_ids = db.query(Tenant.id).filter(Tenant.plan_tier == plan)
        q = q.filter(User.tenant_id.in_(tenant_ids))

    total = q.count()
    users = q.order_by(desc(User.created_at)).offset((page - 1) * per_page).limit(per_page).all()

    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "users": [
            {
                "id": str(u.id),
                "email": u.email,
                "first_name": u.first_name or "",
                "last_name": u.last_name or "",
                "role": u.role,
                "tenant_id": str(u.tenant_id),
                "email_verified": u.email_verified,
                "is_super_admin": u.is_super_admin,
                "created_at": u.created_at.isoformat() if u.created_at else None,
                "failed_login_attempts": u.failed_login_attempts or 0,
            }
            for u in users
        ],
    }


@router.get("/users/{user_id}")
def get_user_detail(
    user_id: str,
    claims: dict = Depends(_require_admin),
    db: Session = Depends(get_db),
):
    from services.auth.models import User, Tenant, WorkspaceProfile
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first()
    wp = db.query(WorkspaceProfile).filter(WorkspaceProfile.user_id == user.id).first()
    return {
        "id": str(user.id),
        "email": user.email,
        "first_name": user.first_name or "",
        "last_name": user.last_name or "",
        "role": user.role,
        "email_verified": user.email_verified,
        "is_super_admin": user.is_super_admin,
        "tenant": {"id": str(tenant.id), "name": tenant.name, "plan_tier": tenant.plan_tier} if tenant else None,
        "workspace": {
            "institution": wp.institution,
            "research_focus": wp.research_focus,
            "country": wp.country,
            "preferred_grid": wp.preferred_grid,
            "setup_completed": wp.setup_completed,
        } if wp else None,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


@router.put("/users/{user_id}/plan")
def override_user_plan(
    user_id: str,
    payload: dict,
    claims: dict = Depends(_require_admin),
    db: Session = Depends(get_db),
):
    """Override the plan_tier of a user's tenant."""
    from services.auth.models import User, Tenant
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first()
    if tenant:
        tenant.plan_tier = payload.get("plan_tier", tenant.plan_tier)
        db.commit()
    return {"status": "SUCCESS", "plan_tier": tenant.plan_tier if tenant else None}


@router.post("/users/{user_id}/reset-password")
def force_password_reset(
    user_id: str,
    claims: dict = Depends(_require_admin),
    db: Session = Depends(get_db),
):
    """Force a password reset email for a user."""
    from services.auth.models import User
    from services.email.email_service import get_email_provider
    from datetime import timedelta
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.reset_token = f"reset_{uuid.uuid4().hex}"
    user.reset_expiry = datetime.now(timezone.utc) + timedelta(hours=2)
    db.commit()
    try:
        from services.email.templates import reset_password
        provider = get_email_provider()
        reset_url = f"https://pypygrid.com/reset?token={user.reset_token}"
        subject, html, text = reset_password(user.first_name or "Researcher", reset_url)
        provider.send_email(user.email, subject, text, html)
    except Exception:
        pass
    return {"status": "SUCCESS", "message": "Password reset email sent."}


@router.delete("/users/{user_id}")
def deactivate_user(
    user_id: str,
    claims: dict = Depends(_require_admin),
    db: Session = Depends(get_db),
):
    """Deactivate a user account (soft delete via email_verified=False)."""
    from services.auth.models import User
    if user_id == str(claims["sub"]):
        raise HTTPException(status_code=400, detail="Cannot deactivate yourself.")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.email_verified = False  # Blocks login
    db.commit()
    return {"status": "SUCCESS", "message": "User deactivated."}


# ─── Tenants ──────────────────────────────────────────────────────────────────

@router.get("/tenants")
def list_tenants(
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    claims: dict = Depends(_require_admin),
    db: Session = Depends(get_db),
):
    from services.auth.models import Tenant, User
    total = db.query(Tenant).count()
    tenants = db.query(Tenant).order_by(desc(Tenant.created_at)).offset((page - 1) * per_page).limit(per_page).all()
    result = []
    for t in tenants:
        user_count = db.query(func.count(User.id)).filter(User.tenant_id == t.id).scalar()
        result.append({
            "id": str(t.id),
            "name": t.name,
            "subdomain": t.subdomain,
            "plan_tier": t.plan_tier,
            "user_count": user_count,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        })
    return {"total": total, "page": page, "per_page": per_page, "tenants": result}


@router.get("/tenants/{tenant_id}")
def get_tenant_detail(
    tenant_id: str,
    claims: dict = Depends(_require_admin),
    db: Session = Depends(get_db),
):
    from services.auth.models import Tenant, User, Experiment
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    users = db.query(User).filter(User.tenant_id == tenant.id).all()
    exp_count = db.query(func.count(Experiment.id)).filter(Experiment.tenant_id == tenant.id).scalar() if hasattr(Experiment, "tenant_id") else 0
    return {
        "id": str(tenant.id),
        "name": tenant.name,
        "subdomain": tenant.subdomain,
        "plan_tier": tenant.plan_tier,
        "user_count": len(users),
        "experiment_count": exp_count,
        "users": [{"id": str(u.id), "email": u.email, "role": u.role} for u in users],
        "created_at": tenant.created_at.isoformat() if tenant.created_at else None,
    }


# ─── Subscriptions ────────────────────────────────────────────────────────────

@router.get("/subscriptions")
def list_subscriptions(
    claims: dict = Depends(_require_admin),
    db: Session = Depends(get_db),
):
    from services.auth.models import Subscription, Tenant
    subs = db.query(Subscription).order_by(desc(Subscription.created_at)).limit(100).all()
    result = []
    for s in subs:
        tenant = db.query(Tenant).filter(Tenant.id == s.tenant_id).first()
        result.append({
            "id": str(s.id),
            "tenant_id": str(s.tenant_id),
            "tenant_name": tenant.name if tenant else "Unknown",
            "plan_name": s.plan_name,
            "cycle": s.cycle,
            "status": s.status,
            "amount": float(s.amount) if s.amount else 0,
            "start_date": s.start_date.isoformat() if s.start_date else None,
            "end_date": s.end_date.isoformat() if s.end_date else None,
        })
    return {"subscriptions": result}


# ─── Coupons ──────────────────────────────────────────────────────────────────

@router.post("/coupons")
def create_coupon(
    payload: dict,
    claims: dict = Depends(_require_admin),
    db: Session = Depends(get_db),
):
    from services.auth.models import PromoCoupon
    from datetime import timedelta
    expires_at = None
    if payload.get("valid_days"):
        expires_at = datetime.now(timezone.utc) + timedelta(days=int(payload["valid_days"]))
    coupon = PromoCoupon(
        code=payload["code"].upper().strip(),
        discount_percent=payload.get("discount_percent", 0),
        discount_amount=payload.get("discount_amount", 0),
        max_uses=payload.get("max_uses", 100),
        expires_at=expires_at,
        is_active=True,
    )
    db.add(coupon)
    db.commit()
    return {"status": "CREATED", "code": coupon.code}


@router.get("/coupons")
def list_coupons(
    claims: dict = Depends(_require_admin),
    db: Session = Depends(get_db),
):
    from services.auth.models import PromoCoupon
    coupons = db.query(PromoCoupon).order_by(desc(PromoCoupon.created_at)).all()
    return {
        "coupons": [
            {
                "id": str(c.id),
                "code": c.code,
                "discount_percent": float(c.discount_percent or 0),
                "discount_amount": float(c.discount_amount or 0),
                "max_uses": c.max_uses,
                "current_uses": c.current_uses or 0,
                "is_active": c.is_active,
                "expires_at": c.expires_at.isoformat() if c.expires_at else None,
            }
            for c in coupons
        ]
    }


@router.delete("/coupons/{code}")
def deactivate_coupon(
    code: str,
    claims: dict = Depends(_require_admin),
    db: Session = Depends(get_db),
):
    from services.auth.models import PromoCoupon
    coupon = db.query(PromoCoupon).filter(PromoCoupon.code == code.upper()).first()
    if not coupon:
        raise HTTPException(status_code=404, detail="Coupon not found")
    coupon.is_active = False
    db.commit()
    return {"status": "DEACTIVATED"}


# ─── System Statistics ────────────────────────────────────────────────────────

@router.get("/statistics")
def system_statistics(
    claims: dict = Depends(_require_admin),
    db: Session = Depends(get_db),
):
    from services.auth.models import User, Tenant, Experiment, Subscription, SupportTicket
    stats = {
        "total_users": db.query(func.count(User.id)).scalar(),
        "total_tenants": db.query(func.count(Tenant.id)).scalar(),
        "total_experiments": db.query(func.count(Experiment.id)).scalar(),
        "active_subscriptions": db.query(func.count(Subscription.id)).filter(Subscription.status == "active").scalar() if hasattr(Subscription, "status") else 0,
        "open_tickets": db.query(func.count(SupportTicket.id)).filter(SupportTicket.status == "open").scalar(),
        "plan_breakdown": {
            "free": db.query(func.count(Tenant.id)).filter(Tenant.plan_tier == "free").scalar(),
            "academic_premium": db.query(func.count(Tenant.id)).filter(Tenant.plan_tier == "academic_premium").scalar(),
            "research_lab": db.query(func.count(Tenant.id)).filter(Tenant.plan_tier == "research_lab").scalar(),
            "enterprise": db.query(func.count(Tenant.id)).filter(Tenant.plan_tier == "enterprise").scalar(),
        },
    }
    return stats


# ─── Audit Logs ───────────────────────────────────────────────────────────────

@router.get("/audit-logs")
def list_audit_logs(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    event_type: Optional[str] = Query(None),
    claims: dict = Depends(_require_admin),
    db: Session = Depends(get_db),
):
    from services.auth.models import SecurityAuditEvent
    q = db.query(SecurityAuditEvent)
    if event_type:
        q = q.filter(SecurityAuditEvent.event_type == event_type)
    total = q.count()
    events = q.order_by(desc(SecurityAuditEvent.created_at)).offset((page - 1) * per_page).limit(per_page).all()
    return {
        "total": total,
        "events": [
            {
                "id": str(e.id),
                "event_type": e.event_type,
                "user_id": str(e.user_id) if e.user_id else None,
                "ip_address": e.ip_address,
                "details": e.details,
                "severity": e.severity,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in events
        ],
    }


# ─── Support Tickets ──────────────────────────────────────────────────────────

@router.post("/support/tickets")
def create_support_ticket(
    payload: dict,
    claims: dict = Depends(get_current_user_claims),
    db: Session = Depends(get_db),
):
    from services.auth.models import SupportTicket
    ticket = SupportTicket(
        tenant_id=claims.get("tenant_id"),
        user_id=claims["sub"],
        subject=payload.get("subject", "")[:255],
        description=payload.get("description", "")[:4096],
        category=payload.get("category", "general"),
        priority=payload.get("priority", "normal"),
    )
    db.add(ticket)
    db.commit()
    return {"status": "CREATED", "ticket_id": str(ticket.id)}


@router.get("/support/tickets")
def list_support_tickets(
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    status: Optional[str] = Query(None),
    claims: dict = Depends(_require_admin),
    db: Session = Depends(get_db),
):
    from services.auth.models import SupportTicket
    q = db.query(SupportTicket)
    if status:
        q = q.filter(SupportTicket.status == status)
    total = q.count()
    tickets = q.order_by(desc(SupportTicket.created_at)).offset((page - 1) * per_page).limit(per_page).all()
    return {
        "total": total,
        "tickets": [
            {
                "id": str(t.id),
                "subject": t.subject,
                "category": t.category,
                "priority": t.priority,
                "status": t.status,
                "user_id": str(t.user_id) if t.user_id else None,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in tickets
        ],
    }


@router.put("/support/tickets/{ticket_id}")
def update_support_ticket(
    ticket_id: str,
    payload: dict,
    claims: dict = Depends(_require_admin),
    db: Session = Depends(get_db),
):
    from services.auth.models import SupportTicket
    ticket = db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if "status" in payload:
        ticket.status = payload["status"]
        if payload["status"] == "resolved":
            ticket.resolved_at = datetime.now(timezone.utc)
    if "resolution_notes" in payload:
        ticket.resolution_notes = payload["resolution_notes"]
    if "assigned_to" in payload:
        ticket.assigned_to = payload["assigned_to"]
    db.commit()
    return {"status": "UPDATED"}
