# workers/billing/tasks.py

import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from services.auth.models import Tenant, Subscription, Experiment, AuditTrail
from services.auth.session import get_db_context

logger = logging.getLogger("workers.billing")

from workers.simulation.tasks import app

@app.task(name="workers.billing.tasks.check_expired_trials_task")
def check_expired_trials_task():
    logger.info("Executing periodic billing check_expired_trials_task")
    check_expired_trials()

app.conf.beat_schedule = {
    'check-expired-trials-every-hour': {
        'task': 'workers.billing.tasks.check_expired_trials_task',
        'schedule': 3600.0,
    },
}

def check_expired_trials():
    """
    Scans the database for expired trial/active subscriptions.
    Downgrades corresponding tenants to the 'free' tier and locks excess experiments.
    """
    now = datetime.now(timezone.utc)
    
    with get_db_context() as db:
        expired_subs = db.query(Subscription).filter(
            Subscription.expires_at < now,
            Subscription.status.in_(["active", "trial"])
        ).all()
        
        for sub in expired_subs:
            tenant = db.query(Tenant).filter(Tenant.id == sub.tenant_id).first()
            if tenant and tenant.plan_tier != "free":
                logger.info(f"Subscription expired for Tenant {tenant.name} ({tenant.id}). Downgrading to free.")
                
                # 1. Update status
                sub.status = "expired"
                tenant.plan_tier = "free"
                
                # 2. Add security audit event
                audit = AuditTrail(
                    tenant_id=tenant.id,
                    action="TRIAL_EXPIRED_PLAN_DOWNGRADED",
                    ip_address="127.0.0.1",
                    user_agent="pypy-billing-worker",
                    timestamp=now
                )
                db.add(audit)
                
                # 3. Lock excess experiments exceeding Free tier limits (10 experiments max)
                lock_excess_experiments(db, tenant.id)
                
                # 4. Send trial expiring/expired email
                try:
                    from services.auth.models import User
                    from services.email.email_service import get_email_provider
                    from services.email.templates import subscription_expiring
                    admin_user = db.query(User).filter(User.tenant_id == tenant.id, User.role == "admin").first()
                    if admin_user:
                        provider = get_email_provider()
                        subject, html, text = subscription_expiring(
                            admin_user.first_name or "Researcher",
                            sub.plan_name,
                            0,
                            "https://pypygrid.com/settings/billing"
                        )
                        provider.send_email(admin_user.email, subject, text, html)
                except Exception:
                    pass
                
        db.commit()

def lock_excess_experiments(db: Session, tenant_id):
    """
    Archives and locks historical experiments exceeding the Free tier limit (10 experiments).
    Keep the 10 newest experiments unlocked, lock everything else.
    """
    # Query all tenant experiments sorted by created date descending
    experiments = db.query(Experiment).filter(
        Experiment.tenant_id == tenant_id
    ).order_by(Experiment.created_at.desc()).all()
    
    if len(experiments) > 10:
        excess_experiments = experiments[10:]
        for exp in excess_experiments:
            exp.archived = True
            exp.locked = True
            exp.read_only = True
            logger.info(f"Locked excess experiment {exp.id} for Tenant {tenant_id}")
        db.flush()

def unlock_tenant_experiments(db: Session, tenant_id):
    """
    Unlocks and restores all locked experiments back to normal state after plan upgrade.
    """
    db.query(Experiment).filter(
        Experiment.tenant_id == tenant_id,
        Experiment.locked == True
    ).update({
        "archived": False,
        "locked": False,
        "read_only": False
    }, synchronize_session=False)
    logger.info(f"Unlocked all experiments for Tenant {tenant_id}")
