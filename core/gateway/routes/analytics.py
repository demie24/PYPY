# core/gateway/routes/analytics.py
# PYPY Grid V11.9 — Analytics API
# All endpoints require admin or super_admin role.

import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, cast, Date
from sqlalchemy.orm import Session

from services.auth.session import get_db
from services.auth.auth_service import get_current_user_claims
from services.auth.models import (
    User, Tenant, Subscription, Scenario, SimulatorRun, CopilotMessage,
    UsageMetric, ExperimentResult,
)

logger = logging.getLogger("gateway.analytics")

router = APIRouter(prefix="/analytics", tags=["analytics"])


# ─────────────────────────────────────────────────────────────────────────────
# Auth guard
# ─────────────────────────────────────────────────────────────────────────────

def require_admin(claims: Dict[str, Any] = Depends(get_current_user_claims)) -> Dict[str, Any]:
    role = claims.get("role", "operator")
    is_super = claims.get("is_super_admin", False)
    if role not in ("admin", "super_admin") and not is_super:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or super_admin role required to access analytics."
        )
    return claims


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _month_label(year: int, month: int) -> str:
    return datetime(year, month, 1).strftime("%b %Y")


def _last_n_months(n: int) -> List[Dict[str, Any]]:
    """Return list of {year, month, label} dicts going back n months from now (inclusive)."""
    now = datetime.now(timezone.utc)
    months = []
    for i in range(n - 1, -1, -1):
        dt = now.replace(day=1) - timedelta(days=i * 28)
        months.append({"year": dt.year, "month": dt.month, "label": _month_label(dt.year, dt.month)})
    # Deduplicate on (year, month) while preserving order
    seen = set()
    result = []
    for m in months:
        key = (m["year"], m["month"])
        if key not in seen:
            seen.add(key)
            result.append(m)
    return result[-n:]


# ─────────────────────────────────────────────────────────────────────────────
# GET /analytics/overview
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/overview")
def analytics_overview(
    _claims: Dict[str, Any] = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """High-level platform KPIs: DAU, MAU, totals, revenue, trial count."""
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_label = now.strftime("%Y-%m")

    try:
        # Total users & tenants
        total_users = db.query(func.count(User.id)).scalar() or 0
        total_tenants = db.query(func.count(Tenant.id)).scalar() or 0

        # DAU — unique users who logged in today (approximated via is_active and created_at fallback)
        # We use updated_at as a proxy for last activity since full session tracking isn't in scope
        try:
            dau = (
                db.query(func.count(User.id))
                .filter(User.updated_at >= today_start, User.is_active == True)
                .scalar()
                or 0
            )
        except Exception:
            dau = 0

        # MAU — users active this calendar month
        try:
            mau = (
                db.query(func.count(User.id))
                .filter(User.updated_at >= month_start, User.is_active == True)
                .scalar()
                or 0
            )
        except Exception:
            mau = 0

        # Active trials
        trial_count = (
            db.query(func.count(Subscription.id))
            .filter(Subscription.status == "trial")
            .scalar()
            or 0
        )

        # Revenue this month — sum of active paid subscriptions (amount * is paid)
        revenue_row = (
            db.query(func.coalesce(func.sum(Subscription.amount), 0))
            .filter(
                Subscription.status == "active",
                Subscription.amount > 0,
                Subscription.started_at >= month_start,
            )
            .scalar()
        )
        revenue_this_month = float(revenue_row or 0)

    except Exception as exc:
        logger.error(f"analytics_overview DB error: {exc}")
        raise HTTPException(status_code=500, detail=f"Analytics query failed: {str(exc)}")

    return {
        "dau": dau,
        "mau": mau,
        "total_users": total_users,
        "total_tenants": total_tenants,
        "revenue_this_month": revenue_this_month,
        "trial_count": trial_count,
        "period": month_label,
        "generated_at": now.isoformat(),
    }


# ─────────────────────────────────────────────────────────────────────────────
# GET /analytics/revenue
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/revenue")
def analytics_revenue(
    _claims: Dict[str, Any] = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Monthly revenue totals for last 12 months — chart-ready data."""
    months = _last_n_months(12)
    data: List[Dict[str, Any]] = []

    try:
        for m in months:
            period_str = f"{m['year']}-{m['month']:02d}"
            amount = (
                db.query(func.coalesce(func.sum(Subscription.amount), 0))
                .filter(
                    Subscription.status == "active",
                    Subscription.amount > 0,
                    func.strftime("%Y-%m", Subscription.started_at) == period_str
                    if "sqlite" in str(db.bind.url)
                    else func.to_char(Subscription.started_at, "YYYY-MM") == period_str,
                )
                .scalar()
            )
            data.append({
                "label": m["label"],
                "period": period_str,
                "revenue": float(amount or 0),
            })
    except Exception:
        # Fallback: compute from UsageMetric or return zeros
        data = [{"label": m["label"], "period": f"{m['year']}-{m['month']:02d}", "revenue": 0.0} for m in months]

    total = sum(d["revenue"] for d in data)
    return {"chart_data": data, "total_12m": total}


# ─────────────────────────────────────────────────────────────────────────────
# GET /analytics/users
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/users")
def analytics_users(
    _claims: Dict[str, Any] = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Daily new user registrations for the last 30 days."""
    now = datetime.now(timezone.utc)
    data: List[Dict[str, Any]] = []

    try:
        for i in range(29, -1, -1):
            day = (now - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day + timedelta(days=1)
            count = (
                db.query(func.count(User.id))
                .filter(User.created_at >= day, User.created_at < day_end)
                .scalar()
                or 0
            )
            data.append({
                "date": day.strftime("%Y-%m-%d"),
                "label": day.strftime("%b %d"),
                "new_users": count,
            })
    except Exception as exc:
        logger.error(f"analytics_users DB error: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))

    total_new = sum(d["new_users"] for d in data)
    return {"chart_data": data, "total_new_30d": total_new}


# ─────────────────────────────────────────────────────────────────────────────
# GET /analytics/simulations
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/simulations")
def analytics_simulations(
    _claims: Dict[str, Any] = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Daily simulation run counts for the last 30 days."""
    now = datetime.now(timezone.utc)
    data: List[Dict[str, Any]] = []

    try:
        for i in range(29, -1, -1):
            day = (now - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day + timedelta(days=1)
            total = (
                db.query(func.count(SimulatorRun.id))
                .filter(SimulatorRun.started_at >= day, SimulatorRun.started_at < day_end)
                .scalar()
                or 0
            )
            completed = (
                db.query(func.count(SimulatorRun.id))
                .filter(
                    SimulatorRun.started_at >= day,
                    SimulatorRun.started_at < day_end,
                    SimulatorRun.status == "STOPPED",
                )
                .scalar()
                or 0
            )
            data.append({
                "date": day.strftime("%Y-%m-%d"),
                "label": day.strftime("%b %d"),
                "simulations": total,
                "completed": completed,
            })
    except Exception as exc:
        logger.error(f"analytics_simulations DB error: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))

    return {
        "chart_data": data,
        "total_30d": sum(d["simulations"] for d in data),
        "completed_30d": sum(d["completed"] for d in data),
    }


# ─────────────────────────────────────────────────────────────────────────────
# GET /analytics/ai-usage
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/ai-usage")
def analytics_ai_usage(
    _claims: Dict[str, Any] = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Daily AI Copilot message counts (user role only) for the last 30 days."""
    now = datetime.now(timezone.utc)
    data: List[Dict[str, Any]] = []

    try:
        for i in range(29, -1, -1):
            day = (now - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day + timedelta(days=1)
            count = (
                db.query(func.count(CopilotMessage.id))
                .filter(
                    CopilotMessage.created_at >= day,
                    CopilotMessage.created_at < day_end,
                    CopilotMessage.role == "user",
                )
                .scalar()
                or 0
            )
            data.append({
                "date": day.strftime("%Y-%m-%d"),
                "label": day.strftime("%b %d"),
                "messages": count,
            })
    except Exception:
        # CopilotMessage table may not exist in all envs; fall back to UsageMetric aggregates
        data = []
        try:
            months = _last_n_months(1)
            m = months[0]
            period_str = f"{m['year']}-{m['month']:02d}"
            total_ai = (
                db.query(func.coalesce(func.sum(UsageMetric.ai_messages_used), 0))
                .filter(UsageMetric.period == period_str)
                .scalar()
                or 0
            )
            # Spread evenly across 30 days as estimation
            for i in range(29, -1, -1):
                day = (now - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
                data.append({
                    "date": day.strftime("%Y-%m-%d"),
                    "label": day.strftime("%b %d"),
                    "messages": int(total_ai) // 30,
                })
        except Exception:
            for i in range(29, -1, -1):
                day = (now - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
                data.append({"date": day.strftime("%Y-%m-%d"), "label": day.strftime("%b %d"), "messages": 0})

    return {
        "chart_data": data,
        "total_30d": sum(d["messages"] for d in data),
    }


# ─────────────────────────────────────────────────────────────────────────────
# GET /analytics/conversions
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/conversions")
def analytics_conversions(
    _claims: Dict[str, Any] = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Trial-to-paid conversion statistics."""
    try:
        total_tenants = db.query(func.count(Tenant.id)).scalar() or 1
        paid_tenants = (
            db.query(func.count(Tenant.id))
            .filter(Tenant.plan_tier.in_(["academic_premium", "research_lab", "enterprise"]))
            .scalar()
            or 0
        )
        free_tenants = (
            db.query(func.count(Tenant.id))
            .filter(Tenant.plan_tier == "free")
            .scalar()
            or 0
        )
        trial_count = (
            db.query(func.count(Subscription.id))
            .filter(Subscription.status == "trial")
            .scalar()
            or 0
        )
        expired_trials = (
            db.query(func.count(Subscription.id))
            .filter(Subscription.status == "expired", Subscription.plan_name == "trial")
            .scalar()
            or 0
        )
        conversion_rate = round(paid_tenants / max(total_tenants, 1) * 100, 2)
    except Exception as exc:
        logger.error(f"analytics_conversions DB error: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))

    return {
        "total_tenants": total_tenants,
        "paid_tenants": paid_tenants,
        "free_tenants": free_tenants,
        "active_trials": trial_count,
        "expired_trials": expired_trials,
        "conversion_rate_pct": conversion_rate,
    }


# ─────────────────────────────────────────────────────────────────────────────
# GET /analytics/top-scenarios
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/top-scenarios")
def analytics_top_scenarios(
    _claims: Dict[str, Any] = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Top 10 most-launched simulation scenarios (by run count)."""
    try:
        rows = (
            db.query(
                Scenario.name,
                Scenario.grid_type,
                func.count(SimulatorRun.id).label("run_count"),
            )
            .outerjoin(SimulatorRun, SimulatorRun.scenario_id == Scenario.id)
            .group_by(Scenario.id, Scenario.name, Scenario.grid_type)
            .order_by(func.count(SimulatorRun.id).desc())
            .limit(10)
            .all()
        )
        scenarios = [
            {"name": r.name, "grid_type": r.grid_type, "run_count": r.run_count}
            for r in rows
        ]
    except Exception as exc:
        logger.error(f"analytics_top_scenarios DB error: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))

    return {"top_scenarios": scenarios}


# ─────────────────────────────────────────────────────────────────────────────
# GET /analytics/plan-distribution
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/plan-distribution")
def analytics_plan_distribution(
    _claims: Dict[str, Any] = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """User (tenant) count broken down by plan tier."""
    try:
        rows = (
            db.query(Tenant.plan_tier, func.count(Tenant.id).label("count"))
            .group_by(Tenant.plan_tier)
            .order_by(func.count(Tenant.id).desc())
            .all()
        )
        distribution = [{"plan": r.plan_tier, "count": r.count} for r in rows]
        total = sum(r["count"] for r in distribution)
        for d in distribution:
            d["percentage"] = round(d["count"] / max(total, 1) * 100, 1)
    except Exception as exc:
        logger.error(f"analytics_plan_distribution DB error: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))

    return {"plan_distribution": distribution, "total_tenants": total}
