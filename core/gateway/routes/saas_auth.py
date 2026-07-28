# core/gateway/routes/saas_auth.py

import os
import time
import uuid
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from services.auth.session import get_db
from services.auth.auth_service import verify_password, hash_password, create_jwt_token, get_current_user_claims
from services.tenant.tenant_service import onboard_new_tenant
from services.users.user_service import get_user_by_email
from services.auth.models import User
from services.email.email_service import get_email_provider

router = APIRouter(prefix="/auth", tags=["auth"])

IP_REQUESTS = defaultdict(list)

def auth_rate_limiter(request: Request):
    ip = request.client.host if request.client else "unknown"
    now = time.time()
    # Clean up older requests (older than 60 seconds)
    IP_REQUESTS[ip] = [t for t in IP_REQUESTS[ip] if now - t < 60]
    if len(IP_REQUESTS[ip]) >= 100:  # Allow max 100 requests per minute
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many authentication requests. Please try again later."
        )
    IP_REQUESTS[ip].append(now)

class TenantOnboardSchema(BaseModel):
    # Original schema
    name: str | None = None
    subdomain: str | None = None
    admin_email: str | None = None
    admin_password: str | None = None
    
    # Frontend schema
    email: str | None = None
    password: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    organization_name: str | None = None
    plan_tier: str | None = None

class LoginSchema(BaseModel):
    email: str
    password: str

class VerifyEmailSchema(BaseModel):
    token: str

class ResendVerificationSchema(BaseModel):
    email: str

class ForgotPasswordSchema(BaseModel):
    email: str

class ResetPasswordSchema(BaseModel):
    token: str
    new_password: str

@router.post("/register", dependencies=[Depends(auth_rate_limiter)])
def register_tenant(payload: TenantOnboardSchema, db: Session = Depends(get_db)):
    try:
        # Extract variables from either schema structure
        admin_email = payload.admin_email or payload.email
        admin_password = payload.admin_password or payload.password
        name = payload.name or payload.organization_name
        if not name and payload.first_name:
            name = f"{payload.first_name}'s Lab"
        
        # Subdomain generation if not provided
        subdomain = payload.subdomain
        if not subdomain and name:
            import re
            # clean name to alphanumeric
            clean_name = re.sub(r'[^a-zA-Z0-9]', '', name).lower()
            if not clean_name:
                clean_name = "tenant"
            
            # append email prefix to avoid conflicts
            email_part = admin_email.split('@')[0] if admin_email else "user"
            clean_email = re.sub(r'[^a-zA-Z0-9]', '', email_part).lower()
            subdomain = f"{clean_name}-{clean_email}"
            
        if not admin_email or not admin_password or not name or not subdomain:
            raise ValueError("Missing required fields for tenant registration.")
            
        # Ensure subdomain format and length is reasonable
        subdomain = subdomain[:30]
        
        tenant = onboard_new_tenant(
            db=db,
            name=name,
            subdomain=subdomain,
            admin_email=admin_email,
            admin_password=admin_password
        )
        
        # Post-onboard: generate email verification token
        user = db.query(User).filter(User.tenant_id == tenant.id, User.role == "admin").first()
        if user:
            # Save first/last name if provided from frontend
            if payload.first_name:
                user.first_name = payload.first_name
            if payload.last_name:
                user.last_name = payload.last_name
                
            user.email_verified = False  # Start unverified
            user.verification_token = f"verify_{uuid.uuid4().hex}"
            user.verification_expiry = datetime.now(timezone.utc) + timedelta(hours=24)
            db.commit()
            
            # Send real email via provider
            try:
                from services.email.templates import verify_email
                provider = get_email_provider()
                verify_url = f"https://pypygrid.com/verify?token={user.verification_token}"
                subject, html, text = verify_email(user.first_name or "Researcher", verify_url)
                provider.send_email(user.email, subject, text, html)
            except Exception as e:
                logger.error(f"Error sending verification email: {e}")
            
        return {
            "status": "SUCCESS",
            "message": "Tenant onboarded successfully. Please verify your email before logging in.",
            "tenant_id": str(tenant.id),
            "subdomain": tenant.subdomain,
            "verification_token": user.verification_token if user else None
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/token", dependencies=[Depends(auth_rate_limiter)])
def login_for_token(payload: LoginSchema, db: Session = Depends(get_db)):
    user = get_user_by_email(db, payload.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password configuration."
        )
        
    # Check Lockout Brute-Force
    if user.lockout_until:
        lockout_time = user.lockout_until.replace(tzinfo=timezone.utc) if user.lockout_until.tzinfo is None else user.lockout_until
        if datetime.now(timezone.utc) < lockout_time:
            minutes_left = int((lockout_time - datetime.now(timezone.utc)).total_seconds() / 60) + 1
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Account is temporarily locked due to multiple failed login attempts. Try again in {minutes_left} minutes."
            )
            
    if not verify_password(payload.password, user.password_hash):
        # Increment failed attempts
        user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
        if user.failed_login_attempts >= 5:
            user.lockout_until = datetime.now(timezone.utc) + timedelta(minutes=15)
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is temporarily locked due to 5 failed login attempts. Try again in 15 minutes."
            )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password configuration."
        )
        
    # Reset failed login attempts on success
    user.failed_login_attempts = 0
    user.lockout_until = None
    db.commit()
    
    # Check Email verification
    if not user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email address not verified. Please verify your email before logging in."
        )
        
    # Generate token payload
    token_claims = {
        "user_id": str(user.id),
        "tenant_id": str(user.tenant_id),
        "role": user.role,
        "email": user.email,
        "plan_tier": user.tenant.plan_tier,
        "is_super_admin": user.is_super_admin,
        "is_founder": user.is_founder
    }
    
    token = create_jwt_token(token_claims)
    return {
        "access_token": token,
        "token_type": "bearer",
        "plan_tier": user.tenant.plan_tier,
        "is_super_admin": user.is_super_admin,
        "is_founder": user.is_founder
    }

@router.post("/verify-email")
def verify_email(payload: VerifyEmailSchema, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.verification_token == payload.token).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid verification token.")
        
    expiry = user.verification_expiry.replace(tzinfo=timezone.utc) if user.verification_expiry.tzinfo is None else user.verification_expiry
    if expiry and datetime.now(timezone.utc) > expiry:
        raise HTTPException(status_code=400, detail="Verification token has expired. Please request a new one.")
        
    user.email_verified = True
    user.verification_token = None
    user.verification_expiry = None
    db.commit()

    # Send Welcome Email
    try:
        from services.email.templates import welcome_email
        provider = get_email_provider()
        subject, html, text = welcome_email(user.first_name or "Researcher", "https://pypygrid.com")
        provider.send_email(user.email, subject, text, html)
    except Exception as e:
        logger.error(f"Error sending welcome email: {e}")
    return {"status": "SUCCESS", "message": "Email verified successfully. You can now login."}

@router.post("/resend-verification")
def resend_verification(payload: ResendVerificationSchema, db: Session = Depends(get_db)):
    user = get_user_by_email(db, payload.email)
    if not user:
        raise HTTPException(status_code=400, detail="User not found.")
        
    if user.email_verified:
        return {"status": "SUCCESS", "message": "Email is already verified."}
        
    user.verification_token = f"verify_{uuid.uuid4().hex}"
    user.verification_expiry = datetime.now(timezone.utc) + timedelta(hours=24)
    db.commit()
    
    # Send verification email via provider
    try:
        from services.email.templates import verify_email
        provider = get_email_provider()
        verify_url = f"https://pypygrid.com/verify?token={user.verification_token}"
        subject, html, text = verify_email(user.first_name or "Researcher", verify_url)
        provider.send_email(user.email, subject, text, html)
    except Exception as e:
        logger.error(f"Error resending verification email: {e}")

    return {
        "status": "SUCCESS", 
        "message": "Verification email sent.",
        "verification_token": user.verification_token
    }

@router.post("/forgot-password")
def forgot_password(payload: ForgotPasswordSchema, db: Session = Depends(get_db)):
    user = get_user_by_email(db, payload.email)
    if not user:
        raise HTTPException(status_code=400, detail="User not found.")
        
    user.reset_token = f"reset_{uuid.uuid4().hex}"
    user.reset_expiry = datetime.now(timezone.utc) + timedelta(hours=2)
    db.commit()
    
    # Send reset email via provider
    try:
        from services.email.templates import reset_password
        provider = get_email_provider()
        reset_url = f"https://pypygrid.com/reset?token={user.reset_token}"
        subject, html, text = reset_password(user.first_name or "Researcher", reset_url)
        provider.send_email(user.email, subject, text, html)
    except Exception as e:
        logger.error(f"Error sending forgot password email: {e}")

    return {
        "status": "SUCCESS",
        "message": "Password reset email sent.",
        "reset_token": user.reset_token
    }

@router.post("/reset-password")
def reset_password(payload: ResetPasswordSchema, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.reset_token == payload.token).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid reset token.")
        
    expiry = user.reset_expiry.replace(tzinfo=timezone.utc) if user.reset_expiry.tzinfo is None else user.reset_expiry
    if expiry and datetime.now(timezone.utc) > expiry:
        raise HTTPException(status_code=400, detail="Reset token has expired.")
        
    user.password_hash = hash_password(payload.new_password)
    user.reset_token = None
    user.reset_expiry = None
    user.failed_login_attempts = 0
    user.lockout_until = None
    db.commit()
    return {"status": "SUCCESS", "message": "Password has been reset successfully."}

@router.get("/profile")
def get_user_profile(claims: dict = Depends(get_current_user_claims)):
    return claims


@router.get("/me")
def get_me(claims: dict = Depends(get_current_user_claims), db: Session = Depends(get_db)):
    """Return full user profile including workspace setup status."""
    from services.auth.models import User, WorkspaceProfile
    user = db.query(User).filter(User.id == claims["sub"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    wp = db.query(WorkspaceProfile).filter(WorkspaceProfile.user_id == user.id).first()
    return {
        "id": str(user.id),
        "email": user.email,
        "first_name": user.first_name or "",
        "last_name": user.last_name or "",
        "role": user.role,
        "tenant_id": str(user.tenant_id),
        "email_verified": user.email_verified,
        "is_super_admin": user.is_super_admin,
        "setup_completed": wp.setup_completed if wp else False,
        "institution": wp.institution if wp else None,
        "preferred_grid": wp.preferred_grid if wp else "IEEE39",
    }


@router.post("/workspace/setup")
def complete_workspace_setup(
    payload: dict,
    claims: dict = Depends(get_current_user_claims),
    db: Session = Depends(get_db)
):
    """Complete first-time workspace setup wizard."""
    from services.auth.models import WorkspaceProfile
    wp = db.query(WorkspaceProfile).filter(WorkspaceProfile.user_id == claims["sub"]).first()
    if not wp:
        wp = WorkspaceProfile(user_id=claims["sub"])
        db.add(wp)
    wp.institution = payload.get("institution", "")
    wp.research_focus = payload.get("research_focus", "")
    wp.country = payload.get("country", "")
    wp.preferred_grid = payload.get("preferred_grid", "IEEE39")
    wp.setup_completed = True
    db.commit()
    return {"status": "SUCCESS", "message": "Workspace setup completed."}


@router.get("/notifications")
def get_notifications(
    limit: int = 20,
    claims: dict = Depends(get_current_user_claims),
    db: Session = Depends(get_db)
):
    """Fetch user notifications."""
    from services.auth.models import UserNotification
    notifs = db.query(UserNotification).filter(
        UserNotification.user_id == claims["sub"]
    ).order_by(UserNotification.created_at.desc()).limit(limit).all()
    return [
        {
            "id": str(n.id),
            "type": n.type,
            "title": n.title,
            "message": n.message,
            "read": n.read,
            "action_url": n.action_url,
            "created_at": n.created_at.isoformat() if n.created_at else None,
        }
        for n in notifs
    ]


@router.post("/notifications/{notification_id}/read")
def mark_notification_read(
    notification_id: str,
    claims: dict = Depends(get_current_user_claims),
    db: Session = Depends(get_db)
):
    """Mark a notification as read."""
    from services.auth.models import UserNotification
    notif = db.query(UserNotification).filter(
        UserNotification.id == notification_id,
        UserNotification.user_id == claims["sub"]
    ).first()
    if notif:
        notif.read = True
        db.commit()
    return {"status": "OK"}
