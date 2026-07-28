# core/gateway/routes/security_hardening.py
"""
V11.8 — Security Hardening API Routes
Exposes endpoints for:
- JWT token blacklisting (logout + revocation)
- IP blocking management (list, block, unblock)
- Security audit events viewer
- Security health summary
"""

import uuid
import logging
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from services.auth.session import get_db
from services.auth.auth_service import get_current_user_claims
from services.operations.security_service import (
    block_ip,
    unblock_ip,
    is_ip_blocked,
    list_ip_blocks,
    blacklist_token,
    is_token_blacklisted,
    purge_expired_blacklist_entries,
    get_recent_security_events,
    log_admin_action,
)

router = APIRouter(prefix="/security", tags=["security"])
logger = logging.getLogger("gateway.security")


# ─── JWT Blacklist ────────────────────────────────────────────────────────────

class LogoutSchema(BaseModel):
    jti: str                     # JWT ID claim from the token payload
    expires_at: datetime         # Token expiry datetime (for TTL pruning)
    reason: Optional[str] = "logout"


@router.post("/jwt/blacklist")
def revoke_jwt_token(
    payload: LogoutSchema,
    claims: dict = Depends(get_current_user_claims),
    db: Session = Depends(get_db),
):
    """
    Blacklist a JWT token (logout or manual revocation).
    The JTI is stored in the blacklist table and checked on future requests.
    """
    user_id_str = claims.get("user_id") or claims.get("sub")
    user_id = uuid.UUID(user_id_str) if user_id_str else None

    blacklist_token(db, payload.jti, payload.expires_at, user_id=user_id, reason=payload.reason)
    logger.info(f"JWT {payload.jti} blacklisted (reason: {payload.reason})")
    return {"blacklisted": True, "jti": payload.jti, "reason": payload.reason}


@router.get("/jwt/blacklist/check/{jti}")
def check_jwt_blacklist(
    jti: str,
    claims: dict = Depends(get_current_user_claims),
    db: Session = Depends(get_db),
):
    """Check whether a specific JTI is blacklisted."""
    return {"jti": jti, "blacklisted": is_token_blacklisted(db, jti)}


@router.post("/jwt/blacklist/purge")
def purge_jwt_blacklist(
    claims: dict = Depends(get_current_user_claims),
    db: Session = Depends(get_db),
):
    """Remove expired JWT blacklist entries (maintenance operation)."""
    deleted = purge_expired_blacklist_entries(db)
    return {"purged": deleted, "message": f"Removed {deleted} expired JWT blacklist entries."}


# ─── IP Blocking ──────────────────────────────────────────────────────────────

class IPBlockSchema(BaseModel):
    ip_address: str
    reason: Optional[str] = "manual_block"
    blocked_hours: int = 24


@router.get("/ip-blocks")
def get_ip_blocks(
    claims: dict = Depends(get_current_user_claims),
    db: Session = Depends(get_db),
):
    """List all currently active IP blocks."""
    return list_ip_blocks(db)


@router.post("/ip-blocks")
def add_ip_block(
    payload: IPBlockSchema,
    claims: dict = Depends(get_current_user_claims),
    db: Session = Depends(get_db),
):
    """Block an IP address manually."""
    user_id_str = claims.get("user_id") or claims.get("sub")
    user_id = uuid.UUID(user_id_str) if user_id_str else None
    result = block_ip(db, payload.ip_address, payload.reason, payload.blocked_hours)
    if user_id:
        log_admin_action(db, user_id, "IP_BLOCK", f"Manually blocked {payload.ip_address}: {payload.reason}")
    return result


@router.delete("/ip-blocks/{ip_address}")
def remove_ip_block(
    ip_address: str,
    claims: dict = Depends(get_current_user_claims),
    db: Session = Depends(get_db),
):
    """Unblock a specific IP address."""
    user_id_str = claims.get("user_id") or claims.get("sub")
    user_id = uuid.UUID(user_id_str) if user_id_str else None
    success = unblock_ip(db, ip_address)
    if not success:
        raise HTTPException(status_code=404, detail=f"No active block found for IP: {ip_address}")
    if user_id:
        log_admin_action(db, user_id, "IP_UNBLOCK", f"Unblocked IP {ip_address}")
    return {"unblocked": True, "ip_address": ip_address}


@router.get("/ip-blocks/check/{ip_address}")
def check_ip_block(
    ip_address: str,
    claims: dict = Depends(get_current_user_claims),
    db: Session = Depends(get_db),
):
    """Check whether an IP address is currently blocked."""
    return {"ip_address": ip_address, "blocked": is_ip_blocked(db, ip_address)}


# ─── Security Audit Events ───────────────────────────────────────────────────

@router.get("/audit-events")
def get_security_audit_events(
    limit: int = Query(default=100, le=500),
    claims: dict = Depends(get_current_user_claims),
    db: Session = Depends(get_db),
):
    """Retrieve recent security audit events."""
    return get_recent_security_events(db, limit=limit)


# ─── Security Health Summary ─────────────────────────────────────────────────

@router.get("/health")
def get_security_health_summary(
    claims: dict = Depends(get_current_user_claims),
    db: Session = Depends(get_db),
):
    """Summary of current security posture."""
    try:
        from services.auth.models import JWTBlacklist, IPBlock, SecurityAuditEvent
        blacklisted_count = db.query(JWTBlacklist).count()
        active_blocks = db.query(IPBlock).filter(IPBlock.active == True).count()
        recent_failures = db.query(SecurityAuditEvent).filter(
            SecurityAuditEvent.event_type == "LOGIN_FAILURE"
        ).count()
        recent_locks = db.query(SecurityAuditEvent).filter(
            SecurityAuditEvent.event_type == "ACCOUNT_LOCKED"
        ).count()
    except Exception:
        blacklisted_count = active_blocks = recent_failures = recent_locks = 0

    return {
        "jwt_blacklist_entries": blacklisted_count,
        "active_ip_blocks": active_blocks,
        "login_failures_total": recent_failures,
        "account_lockouts_total": recent_locks,
        "rate_limiting": "enabled (150 req/min)",
        "jwt_expiry": "900s (15 minutes)",
        "brute_force_threshold": "5 attempts → 15 min lockout",
        "security_headers": ["HSTS", "X-Frame-Options DENY", "nosniff", "XSS protection"],
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }
