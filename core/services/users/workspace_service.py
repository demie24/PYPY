# core/services/users/workspace_service.py

import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from services.auth.models import Experiment, UsageMetric, Tenant, User

def get_tenant_experiments(db: Session, tenant_id: uuid.UUID) -> list:
    return db.query(Experiment).filter(
        Experiment.tenant_id == tenant_id
    ).order_by(Experiment.created_at.desc()).all()

def check_experiment_access(db: Session, experiment_id: uuid.UUID, user_id: uuid.UUID = None) -> Experiment:
    exp = db.query(Experiment).filter(Experiment.id == experiment_id).first()
    if not exp:
        raise ValueError("Experiment not found.")
        
    is_founder = False
    if user_id:
        user = db.query(User).filter(User.id == user_id).first()
        is_founder = user.is_founder if user else False
        
    if not is_founder and (exp.locked or exp.read_only):
        raise PermissionError("Access blocked. This historical experiment is archived and read-only.")
    return exp

def increment_ai_copilot_usage(db: Session, tenant_id: uuid.UUID, user_id: uuid.UUID = None) -> int:
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise ValueError("Tenant not found.")
        
    is_founder = False
    if user_id:
        user = db.query(User).filter(User.id == user_id).first()
        is_founder = user.is_founder if user else False
        
    now = datetime.now(timezone.utc)
    current_period = now.strftime("%Y-%m")
    
    # Get or create usage metrics
    usage = db.query(UsageMetric).filter(
        UsageMetric.tenant_id == tenant_id,
        UsageMetric.period == current_period
    ).first()
    
    if not usage:
        usage = UsageMetric(tenant_id=tenant_id, period=current_period)
        db.add(usage)
        db.flush()
        
    if not is_founder and tenant.plan_tier.lower() == "free" and usage.ai_messages_used >= 10:
        raise PermissionError("Daily Free AI Copilot message quota reached. Upgrade to Academic Premium to unlock.")
        
    usage.ai_messages_used += 1
    db.commit()
    return usage.ai_messages_used
