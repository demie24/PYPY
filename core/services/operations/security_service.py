# core/services/operations/security_service.py
"""
V11.8 — Security Hardening Service
Handles brute-force detection, JWT blacklisting, IP blocking,
rate abuse detection, and security audit trail.
"""

import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List
from sqlalchemy.orm import Session

logger = logging.getLogger("operations.security")

# ─── Constants ────────────────────────────────────────────────────────────────

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 15
IP_BLOCK_THRESHOLD = 50          # requests in window before auto-block
IP_BLOCK_WINDOW_MINUTES = 5


# ─── Brute Force Protection ───────────────────────────────────────────────────

def record_failed_login(db: Session, user_id: uuid.UUID, ip_address: str) -> dict:
    """
    Record a failed login attempt.
    Auto-locks account after MAX_FAILED_ATTEMPTS.
    Returns {"locked": bool, "attempts": int, "lockout_until": str|None}
    """
    from services.auth.models import User
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return {"locked": False, "attempts": 0, "lockout_until": None}

    user.failed_login_attempts = (user.failed_login_attempts or 0) + 1

    if user.failed_login_attempts >= MAX_FAILED_ATTEMPTS:
        lockout_until = datetime.now(timezone.utc) + timedelta(minutes=LOCKOUT_MINUTES)
        user.lockout_until = lockout_until
        db.commit()
        _log_security_event(db, user_id, "ACCOUNT_LOCKED",
                            f"Account locked after {user.failed_login_attempts} failed attempts from {ip_address}",
                            ip_address)
        logger.warning(f"Account locked: {user.email} (IP: {ip_address})")
        return {"locked": True, "attempts": user.failed_login_attempts,
                "lockout_until": lockout_until.isoformat()}

    db.commit()
    return {"locked": False, "attempts": user.failed_login_attempts, "lockout_until": None}


def reset_failed_login(db: Session, user_id: uuid.UUID):
    """Reset failed login counter after successful authentication."""
    from services.auth.models import User
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.failed_login_attempts = 0
        user.lockout_until = None
        db.commit()


def is_account_locked(db: Session, user_id: uuid.UUID) -> bool:
    """Check if a user account is currently locked out."""
    from services.auth.models import User
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.lockout_until:
        return False
    # Handle both timezone-aware (Postgres) and naive (SQLite) datetimes
    lockout = user.lockout_until
    now = datetime.now(timezone.utc)
    if lockout.tzinfo is None:
        lockout = lockout.replace(tzinfo=timezone.utc)
    if now < lockout:
        return True
    # Auto-unlock if lockout expired
    user.lockout_until = None
    user.failed_login_attempts = 0
    db.commit()
    return False


# ─── JWT Blacklist ────────────────────────────────────────────────────────────

def blacklist_token(db: Session, jti: str, expires_at: datetime, user_id: Optional[uuid.UUID] = None, reason: str = "logout"):
    """Add a JWT token ID to the blacklist (e.g., on logout or revocation)."""
    try:
        from services.auth.models import JWTBlacklist
        entry = JWTBlacklist(
            jti=jti,
            user_id=user_id,
            expires_at=expires_at,
            blacklisted_at=datetime.now(timezone.utc),
            reason=reason,
        )
        db.add(entry)
        db.commit()
        logger.info(f"JWT blacklisted: {jti} (reason: {reason})")
    except Exception as e:
        logger.error(f"Failed to blacklist JWT: {e}")


def is_token_blacklisted(db: Session, jti: str) -> bool:
    """Returns True if the given JTI is in the blacklist."""
    try:
        from services.auth.models import JWTBlacklist
        entry = db.query(JWTBlacklist).filter(JWTBlacklist.jti == jti).first()
        return entry is not None
    except Exception as e:
        logger.error(f"Failed to check JWT blacklist: {e}")
        return False


def purge_expired_blacklist_entries(db: Session) -> int:
    """Remove JWT blacklist entries whose tokens have already expired (cleanup)."""
    try:
        from services.auth.models import JWTBlacklist
        deleted = db.query(JWTBlacklist).filter(
            JWTBlacklist.expires_at < datetime.now(timezone.utc)
        ).delete(synchronize_session=False)
        db.commit()
        logger.info(f"Purged {deleted} expired JWT blacklist entries.")
        return deleted
    except Exception as e:
        logger.error(f"Failed to purge JWT blacklist: {e}")
        return 0


# ─── IP Blocking ──────────────────────────────────────────────────────────────

def block_ip(db: Session, ip_address: str, reason: str = "abuse", blocked_hours: int = 24) -> dict:
    """Block an IP address for a given number of hours."""
    try:
        from services.auth.models import IPBlock
        existing = db.query(IPBlock).filter(IPBlock.ip_address == ip_address, IPBlock.active == True).first()
        if existing:
            return {"blocked": True, "id": str(existing.id), "already_blocked": True}

        block = IPBlock(
            id=uuid.uuid4(),
            ip_address=ip_address,
            reason=reason,
            blocked_until=datetime.now(timezone.utc) + timedelta(hours=blocked_hours),
            active=True,
            blocked_at=datetime.now(timezone.utc),
        )
        db.add(block)
        db.commit()
        logger.warning(f"IP blocked: {ip_address} for {blocked_hours}h (reason: {reason})")
        return {"blocked": True, "id": str(block.id), "already_blocked": False}
    except Exception as e:
        logger.error(f"Failed to block IP: {e}")
        return {"blocked": False, "error": str(e)}


def unblock_ip(db: Session, ip_address: str) -> bool:
    """Remove an active IP block."""
    try:
        from services.auth.models import IPBlock
        blocks = db.query(IPBlock).filter(IPBlock.ip_address == ip_address, IPBlock.active == True).all()
        for b in blocks:
            b.active = False
        db.commit()
        return True
    except Exception as e:
        logger.error(f"Failed to unblock IP: {e}")
        return False


def is_ip_blocked(db: Session, ip_address: str) -> bool:
    """Returns True if an IP address is currently blocked."""
    try:
        from services.auth.models import IPBlock
        now = datetime.now(timezone.utc)
        blocks = db.query(IPBlock).filter(
            IPBlock.ip_address == ip_address,
            IPBlock.active == True,
        ).all()
        for block in blocks:
            if block.blocked_until is None:
                return True
            bu = block.blocked_until
            if bu.tzinfo is None:
                bu = bu.replace(tzinfo=timezone.utc)
            if now < bu:
                return True
        return False
    except Exception:
        return False


def list_ip_blocks(db: Session) -> List[dict]:
    """Return all currently active IP blocks."""
    try:
        from services.auth.models import IPBlock
        blocks = db.query(IPBlock).filter(IPBlock.active == True).all()
        return [
            {
                "id": str(b.id),
                "ip_address": b.ip_address,
                "reason": b.reason,
                "blocked_until": b.blocked_until.isoformat() if b.blocked_until else None,
                "blocked_at": b.blocked_at.isoformat() if b.blocked_at else None,
            }
            for b in blocks
        ]
    except Exception as e:
        logger.error(f"Failed to list IP blocks: {e}")
        return []


# ─── Security Audit Trail ─────────────────────────────────────────────────────

def _log_security_event(
    db: Session,
    user_id: Optional[uuid.UUID],
    event_type: str,
    description: str,
    ip_address: str = "unknown",
    tenant_id: Optional[uuid.UUID] = None,
):
    """Persist a security audit event."""
    try:
        from services.auth.models import SecurityAuditEvent
        event = SecurityAuditEvent(
            id=uuid.uuid4(),
            user_id=user_id,
            tenant_id=tenant_id,
            event_type=event_type,
            description=description,
            ip_address=ip_address,
            occurred_at=datetime.now(timezone.utc),
        )
        db.add(event)
        db.commit()
    except Exception as e:
        logger.error(f"Failed to log security event: {e}")


def log_login_success(db: Session, user_id: uuid.UUID, ip_address: str, tenant_id: Optional[uuid.UUID] = None):
    _log_security_event(db, user_id, "LOGIN_SUCCESS", f"Successful login from {ip_address}", ip_address, tenant_id)


def log_login_failure(db: Session, email: str, ip_address: str):
    _log_security_event(db, None, "LOGIN_FAILURE", f"Failed login attempt for {email} from {ip_address}", ip_address)


def log_logout(db: Session, user_id: uuid.UUID, ip_address: str, tenant_id: Optional[uuid.UUID] = None):
    _log_security_event(db, user_id, "LOGOUT", f"User logged out from {ip_address}", ip_address, tenant_id)


def log_admin_action(db: Session, user_id: uuid.UUID, action: str, detail: str, ip_address: str = "unknown"):
    _log_security_event(db, user_id, f"ADMIN_{action.upper()}", detail, ip_address)


def get_recent_security_events(db: Session, limit: int = 100) -> List[dict]:
    """Fetch recent security audit events."""
    try:
        from services.auth.models import SecurityAuditEvent
        events = db.query(SecurityAuditEvent).order_by(
            SecurityAuditEvent.occurred_at.desc()
        ).limit(limit).all()
        return [
            {
                "id": str(e.id),
                "event_type": e.event_type,
                "description": e.description,
                "ip_address": e.ip_address,
                "user_id": str(e.user_id) if e.user_id else None,
                "occurred_at": e.occurred_at.isoformat() if e.occurred_at else None,
            }
            for e in events
        ]
    except Exception as e:
        logger.error(f"Failed to fetch security events: {e}")
        return []
