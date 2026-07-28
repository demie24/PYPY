# core/gateway/routes/simulation.py

import os
import json
import uuid
import logging
from typing import List, Dict, Any
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
import redis

from services.auth.session import get_db
from services.auth.auth_service import get_current_user_claims
from services.simulation.launcher import launch_grid_scenario, stop_grid_scenario
from services.auth.models import SimulatorRun, SimulationAuditLog, Scenario
from services.simulation.audit import log_simulation_audit

logger = logging.getLogger("gateway.routes.simulation")
router = APIRouter(prefix="/simulation", tags=["simulation"])

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
r = redis.from_url(REDIS_URL)

class LaunchSimulationSchema(BaseModel):
    scenario_id: str

@router.post("/launch")
def launch_simulation(payload: LaunchSimulationSchema, claims: dict = Depends(get_current_user_claims), db: Session = Depends(get_db)):
    tenant_id_str = claims.get("tenant_id")
    user_id_str = claims.get("user_id")
    
    if not tenant_id_str or not user_id_str:
        raise HTTPException(status_code=400, detail="User JWT lacks required identity claims.")
        
    tenant_uuid = uuid.UUID(tenant_id_str)
    user_uuid = uuid.UUID(user_id_str)
    scenario_uuid = uuid.UUID(payload.scenario_id)
    
    try:
        # Audit log: JOB_CREATED
        log_simulation_audit(db, tenant_uuid, scenario_uuid, "JOB_CREATED", actor=claims.get("email", "user"), details=f"Initiating launch of scenario {payload.scenario_id}")
        
        run = launch_grid_scenario(db, tenant_uuid, user_uuid, scenario_uuid)
        return {
            "status": "SUCCESS",
            "job_id": str(run.id),
            "celery_task_id": run.celery_task_id,
            "state": run.status
        }
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error launching simulation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Simulation launch failed: {str(e)}")

@router.post("/{job_id}/cancel")
def cancel_simulation(job_id: str, claims: dict = Depends(get_current_user_claims), db: Session = Depends(get_db)):
    tenant_id_str = claims.get("tenant_id")
    if not tenant_id_str:
        raise HTTPException(status_code=400, detail="User JWT lacks required identity claims.")
        
    tenant_uuid = uuid.UUID(tenant_id_str)
    job_uuid = uuid.UUID(job_id)
    
    try:
        run = stop_grid_scenario(db, tenant_uuid, job_uuid)
        log_simulation_audit(db, tenant_uuid, job_uuid, "JOB_CANCELLED", actor=claims.get("email", "user"), details="User requested cancellation.")
        return {
            "status": "SUCCESS",
            "job_id": str(run.id),
            "state": run.status
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error cancelling simulation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/jobs")
def get_jobs_by_tenant(claims: dict = Depends(get_current_user_claims), db: Session = Depends(get_db)):
    tenant_id_str = claims.get("tenant_id")
    if not tenant_id_str:
        raise HTTPException(status_code=400, detail="User JWT lacks required identity claims.")
        
    tenant_uuid = uuid.UUID(tenant_id_str)
    runs = db.query(SimulatorRun).filter(SimulatorRun.tenant_id == tenant_uuid).order_by(SimulatorRun.started_at.desc()).all()
    return [
        {
            "id": str(run.id),
            "scenario_id": str(run.scenario_id),
            "status": run.status,
            "progress_percentage": run.progress_percentage,
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "stopped_at": run.stopped_at.isoformat() if run.stopped_at else None,
            "grid_name": run.scenario.grid_type if run.scenario else "Unknown"
        }
        for run in runs
    ]

@router.get("/queue/status")
def get_queue_status(db: Session = Depends(get_db)):
    try:
        queued_jobs = r.llen("celery")
    except Exception:
        queued_jobs = 0
        
    running_jobs = db.query(SimulatorRun).filter(SimulatorRun.status == "RUNNING").count()
    completed_jobs = db.query(SimulatorRun).filter(SimulatorRun.status == "COMPLETED").count()
    failed_jobs = db.query(SimulatorRun).filter(SimulatorRun.status == "FAILED").count()
    
    # Active workers
    try:
        workers_info = r.hgetall("pypy:worker:status")
        active_workers = len(workers_info)
    except Exception:
        active_workers = 0
        
    return {
        "active_workers": active_workers,
        "running_jobs": running_jobs,
        "queued_jobs": queued_jobs,
        "completed_jobs": completed_jobs,
        "failed_jobs": failed_jobs
    }

@router.get("/workers/status")
def get_workers_status():
    try:
        workers_info = r.hgetall("pypy:worker:status")
    except Exception:
        workers_info = {}
        
    results = []
    now = datetime.now(timezone.utc)
    for k, v in workers_info.items():
        try:
            data = json.loads(v.decode("utf-8"))
            hb_time = datetime.fromisoformat(data["last_heartbeat"])
            if (now - hb_time).total_seconds() > 15:
                data["status"] = "OFFLINE"
            results.append(data)
        except Exception:
            pass
    return results

@router.get("/{job_id}/progress")
def get_job_progress(job_id: str, db: Session = Depends(get_db)):
    job_uuid = uuid.UUID(job_id)
    run = db.query(SimulatorRun).filter(SimulatorRun.id == job_uuid).first()
    if not run:
        raise HTTPException(status_code=404, detail="Simulation run not found")
    return {
        "job_id": job_id,
        "status": run.status,
        "progress_percentage": run.progress_percentage
    }

@router.get("/audit/{job_id}")
def get_job_audit_logs(job_id: str, db: Session = Depends(get_db)):
    job_uuid = uuid.UUID(job_id)
    logs = db.query(SimulationAuditLog).filter(SimulationAuditLog.job_id == job_uuid).order_by(SimulationAuditLog.timestamp.asc()).all()
    return [
        {
            "action": log.action,
            "timestamp": log.timestamp.isoformat(),
            "actor": log.actor,
            "details": log.details
        }
        for log in logs
    ]

@router.get("/{job_id}")
def get_job_details(job_id: str, claims: dict = Depends(get_current_user_claims), db: Session = Depends(get_db)):
    tenant_id_str = claims.get("tenant_id")
    if not tenant_id_str:
        raise HTTPException(status_code=400, detail="User JWT lacks required identity claims.")
        
    tenant_uuid = uuid.UUID(tenant_id_str)
    job_uuid = uuid.UUID(job_id)
    run = db.query(SimulatorRun).filter(SimulatorRun.id == job_uuid, SimulatorRun.tenant_id == tenant_uuid).first()
    if not run:
        raise HTTPException(status_code=404, detail="Simulation run not found")
        
    return {
        "id": str(run.id),
        "status": run.status,
        "progress_percentage": run.progress_percentage,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "stopped_at": run.stopped_at.isoformat() if run.stopped_at else None,
        "grid_name": run.scenario.grid_type if run.scenario else "Unknown",
        "config": run.scenario.config if run.scenario else {}
    }
