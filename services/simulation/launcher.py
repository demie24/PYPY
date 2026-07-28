# core/services/simulation/launcher.py

import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from services.auth.models import Tenant, Scenario, SimulatorRun, AuditTrail, User
from workers.simulation.tasks import run_grid_simulation

def launch_grid_scenario(db: Session, tenant_id: uuid.UUID, user_id: uuid.UUID, scenario_id: uuid.UUID) -> SimulatorRun:
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    scenario = db.query(Scenario).filter(Scenario.id == scenario_id, Scenario.tenant_id == tenant_id).first()
    
    if not tenant or not scenario:
        raise ValueError("Invalid tenant or scenario reference.")
        
    user = db.query(User).filter(User.id == user_id).first()
    is_founder = user.is_founder if user else False
    
    plan = tenant.plan_tier.lower()
    
    # 1. Enforce Subscription Concurrency Quotas
    active_runs = db.query(SimulatorRun).filter(
        SimulatorRun.tenant_id == tenant_id,
        SimulatorRun.status == "RUNNING"
    ).count()
    
    if not is_founder:
        if plan == "free" and active_runs >= 1:
            raise PermissionError("Free Plan concurrency limit reached. Only 1 active simulation allowed.")
        elif plan == "academic_premium" and active_runs >= 3:
            raise PermissionError("Academic Premium Plan concurrency limit reached. Max 3 active runs allowed.")
        elif plan == "research_lab" and active_runs >= 5:
            raise PermissionError("Research Lab Plan concurrency limit reached. Max 5 active runs allowed.")
        
    # 2. Check Scenario Grid Access Constraints
    allowed_grids_free = ["IEEE14", "IEEE39"]
    grid_name = scenario.grid_type.upper()
    if not is_founder:
        if plan == "free" and grid_name not in allowed_grids_free:
            raise PermissionError(f"Grid {grid_name} is locked in Free Plan. Upgrade to Academic Premium to access.")
        
    # 3. Create SimulatorRun Log
    run = SimulatorRun(
        tenant_id=tenant_id,
        scenario_id=scenario_id,
        status="PENDING",
        started_at=datetime.now(timezone.utc)
    )
    db.add(run)
    db.flush()
    
    # 4. Trigger Celery Task
    task = run_grid_simulation.delay(
        tenant_id=str(tenant_id),
        run_id=str(run.id),
        grid_name=scenario.grid_type,
        config=scenario.config
    )
    
    run.celery_task_id = task.id
    run.status = "RUNNING"
    
    # 5. Log Security Audit
    audit = AuditTrail(
        tenant_id=tenant_id,
        user_id=user_id,
        action=f"LAUNCHED_SCENARIO_{grid_name}",
        ip_address="127.0.0.1",
        timestamp=datetime.now(timezone.utc)
    )
    db.add(audit)
    db.commit()
    
    return run

def stop_grid_scenario(db: Session, tenant_id: uuid.UUID, run_id: uuid.UUID) -> SimulatorRun:
    run = db.query(SimulatorRun).filter(
        SimulatorRun.id == run_id,
        SimulatorRun.tenant_id == tenant_id
    ).first()
    
    if not run:
        raise ValueError("Simulator run not found.")
        
    if run.status == "RUNNING":
        from workers.simulation.tasks import app
        app.control.revoke(run.celery_task_id, terminate=True)
        
        run.status = "STOPPED"
        run.stopped_at = datetime.now(timezone.utc)
        db.commit()
        
    return run
