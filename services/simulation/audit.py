# core/services/simulation/audit.py

import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from services.auth.models import SimulationAuditLog

def log_simulation_audit(db: Session, tenant_id: uuid.UUID, job_id: uuid.UUID, action: str, actor: str = "system", details: str = None):
    log = SimulationAuditLog(
        tenant_id=tenant_id,
        job_id=job_id,
        action=action,
        timestamp=datetime.now(timezone.utc),
        actor=actor,
        details=details
    )
    db.add(log)
    db.commit()
