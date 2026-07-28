# core/gateway/routes/experiments.py

import os
import csv
import json
import uuid
import io
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from services.auth.session import get_db
from services.auth.auth_service import get_current_user_claims
from services.auth.models import Experiment, ExperimentResult, ExperimentTag, ExperimentShare, Tenant, User

logger = logging.getLogger("gateway.routes.experiments")
router = APIRouter(prefix="/experiments", tags=["experiments"])

class ExperimentCreateSchema(BaseModel):
    name: str
    grid_type: str
    description: Optional[str] = ""
    tags: Optional[List[str]] = []

class ExperimentUpdateSchema(BaseModel):
    name: str
    description: Optional[str] = ""
    tags: Optional[List[str]] = []

class SharePayload(BaseModel):
    shared_with_user_id: Optional[str] = None
    shared_with_tenant_id: Optional[str] = None

class ComparePayload(BaseModel):
    experiment_ids: List[str]

@router.get("")
def list_experiments(
    search: Optional[str] = None,
    tag: Optional[str] = None,
    claims: dict = Depends(get_current_user_claims),
    db: Session = Depends(get_db)
):
    tenant_id_str = claims.get("tenant_id")
    if not tenant_id_str:
        raise HTTPException(status_code=400, detail="Missing tenant claim.")
    tenant_uuid = uuid.UUID(tenant_id_str)
    
    # Base query for tenant's own experiments
    query = db.query(Experiment).filter(Experiment.tenant_id == tenant_uuid)
    
    # Union with shared experiments
    shared_expr_ids = db.query(ExperimentShare.experiment_id).filter(
        (ExperimentShare.shared_with_tenant_id == tenant_uuid) |
        (ExperimentShare.shared_with_user_id == uuid.UUID(claims.get("user_id")))
    ).subquery()
    
    query = db.query(Experiment).filter(
        (Experiment.tenant_id == tenant_uuid) |
        (Experiment.id.in_(shared_expr_ids))
    )
    
    if search:
        query = query.filter(
            Experiment.name.ilike(f"%{search}%") |
            Experiment.description.ilike(f"%{search}%")
        )
        
    results = query.all()
    
    # Filter by tag post-query for simplicity, or via joins
    filtered = []
    for exp in results:
        tags = [t.tag for t in db.query(ExperimentTag).filter(ExperimentTag.experiment_id == exp.id).all()]
        if tag and tag not in tags:
            continue
        filtered.append({
            "id": str(exp.id),
            "name": exp.name,
            "description": exp.description,
            "grid_type": exp.grid_type,
            "created_at": exp.created_at.isoformat(),
            "locked": exp.locked,
            "tags": tags
        })
        
    return filtered

@router.post("")
def create_experiment(
    payload: ExperimentCreateSchema,
    claims: dict = Depends(get_current_user_claims),
    db: Session = Depends(get_db)
):
    tenant_id_str = claims.get("tenant_id")
    user_id_str = claims.get("user_id")
    if not tenant_id_str or not user_id_str:
        raise HTTPException(status_code=400, detail="Missing claims.")
    tenant_uuid = uuid.UUID(tenant_id_str)
    user_uuid = uuid.UUID(user_id_str)
    
    tenant = db.query(Tenant).filter(Tenant.id == tenant_uuid).first()
    plan_tier = (tenant.plan_tier or "free").lower()
    
    # Enforce quota limits
    if plan_tier == "free":
        current_count = db.query(Experiment).filter(Experiment.tenant_id == tenant_uuid).count()
        if current_count >= 10:
            raise HTTPException(
                status_code=403,
                detail="Storage limit exceeded. Free tier is capped at 10 saved experiments."
            )
            
    exp = Experiment(
        id=uuid.uuid4(),
        tenant_id=tenant_uuid,
        user_id=user_uuid,
        name=payload.name,
        description=payload.description,
        grid_type=payload.grid_type,
        archived=False,
        locked=False,
        read_only=False
    )
    db.add(exp)
    db.flush()
    
    # Save tags
    for t in payload.tags:
        tag_obj = ExperimentTag(id=uuid.uuid4(), experiment_id=exp.id, tag=t)
        db.add(tag_obj)
        
    # Create default mock experiment result
    res = ExperimentResult(
        id=uuid.uuid4(),
        tenant_id=tenant_uuid,
        experiment_id=exp.id,
        resilience_score=85.5,
        rto_seconds=45,
        rpo_seconds=10,
        total_load_shed_mwh=12.5,
        financial_loss=45000.0,
        verdict="DEGRADED",
        detection_rate=92.4,
        recovery_time_seconds=30,
        attack_success_rate=45.0,
        telemetry_history=[{"step": i, "voltage": 1.0 + i*0.002, "frequency": 60.0 - i*0.005} for i in range(10)],
        scada_events=["T10: Generator 2 power set to 150MW", "T45: Breaker 8 closed"],
        attack_events=["T20: Injection on Bus 5 vector"],
        flisr_actions=["T30: FLISR switch 3 isolated faulted line"]
    )
    db.add(res)
    db.commit()
    
    return {"status": "SUCCESS", "experiment_id": str(exp.id)}

@router.get("/{id}")
def get_experiment_details(id: str, db: Session = Depends(get_db)):
    exp_uuid = uuid.UUID(id)
    exp = db.query(Experiment).filter(Experiment.id == exp_uuid).first()
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")
        
    result = db.query(ExperimentResult).filter(ExperimentResult.experiment_id == exp_uuid).first()
    tags = [t.tag for t in db.query(ExperimentTag).filter(ExperimentTag.experiment_id == exp_uuid).all()]
    
    return {
        "id": str(exp.id),
        "name": exp.name,
        "description": exp.description,
        "grid_type": exp.grid_type,
        "created_at": exp.created_at.isoformat(),
        "tags": tags,
        "metrics": {
            "resilience_score": float(result.resilience_score) if result else 0.0,
            "detection_rate": float(result.detection_rate) if result else 0.0,
            "recovery_time_seconds": result.recovery_time_seconds if result else 0,
            "financial_loss": float(result.financial_loss) if result else 0.0,
            "attack_success_rate": float(result.attack_success_rate) if result else 0.0
        } if result else None
    }

@router.put("/{id}")
def update_experiment(id: str, payload: ExperimentUpdateSchema, db: Session = Depends(get_db)):
    exp_uuid = uuid.UUID(id)
    exp = db.query(Experiment).filter(Experiment.id == exp_uuid).first()
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")
        
    exp.name = payload.name
    exp.description = payload.description
    
    # Update tags (flush old tags and write new ones)
    db.query(ExperimentTag).filter(ExperimentTag.experiment_id == exp_uuid).delete()
    for t in payload.tags:
        tag_obj = ExperimentTag(id=uuid.uuid4(), experiment_id=exp_uuid, tag=t)
        db.add(tag_obj)
        
    db.commit()
    return {"status": "SUCCESS"}

@router.delete("/{id}")
def delete_experiment(id: str, db: Session = Depends(get_db)):
    exp_uuid = uuid.UUID(id)
    exp = db.query(Experiment).filter(Experiment.id == exp_uuid).first()
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")
        
    db.delete(exp)
    db.commit()
    return {"status": "SUCCESS"}

@router.post("/{id}/share")
def share_experiment(
    id: str,
    payload: SharePayload,
    claims: dict = Depends(get_current_user_claims),
    db: Session = Depends(get_db)
):
    tenant_id_str = claims.get("tenant_id")
    user_id_str = claims.get("user_id")
    if not tenant_id_str or not user_id_str:
        raise HTTPException(status_code=400, detail="Missing claims.")
    tenant_uuid = uuid.UUID(tenant_id_str)
    user_uuid = uuid.UUID(user_id_str)
    exp_uuid = uuid.UUID(id)
    
    tenant = db.query(Tenant).filter(Tenant.id == tenant_uuid).first()
    plan_tier = (tenant.plan_tier or "free").lower()
    
    # Subscription share rules
    if plan_tier in ["free", "academic_premium"]:
        raise HTTPException(
            status_code=403,
            detail="Sharing is restricted to Research Lab and Enterprise subscribers."
        )
        
    target_tenant_uuid = uuid.UUID(payload.shared_with_tenant_id) if payload.shared_with_tenant_id else None
    target_user_uuid = uuid.UUID(payload.shared_with_user_id) if payload.shared_with_user_id else None
    
    # For Research Lab, restrict sharing to team members (same tenant ID)
    if plan_tier == "research_lab":
        if target_tenant_uuid and target_tenant_uuid != tenant_uuid:
            raise HTTPException(status_code=403, detail="Research Lab accounts can only share within their own team.")
        if target_user_uuid:
            target_user = db.query(User).filter(User.id == target_user_uuid).first()
            if not target_user or target_user.tenant_id != tenant_uuid:
                raise HTTPException(status_code=403, detail="Research Lab accounts can only share with team members.")
                
    share = ExperimentShare(
        id=uuid.uuid4(),
        experiment_id=exp_uuid,
        shared_with_tenant_id=target_tenant_uuid or tenant_uuid,
        shared_with_user_id=target_user_uuid,
        shared_by_user_id=user_uuid
    )
    db.add(share)
    db.commit()
    return {"status": "SUCCESS"}

@router.post("/{id}/replay")
def get_replay_logs(id: str, db: Session = Depends(get_db)):
    exp_uuid = uuid.UUID(id)
    res = db.query(ExperimentResult).filter(ExperimentResult.experiment_id == exp_uuid).first()
    if not res:
        raise HTTPException(status_code=404, detail="Replay data not found for this experiment")
        
    return {
        "telemetry_history": res.telemetry_history or [],
        "scada_events": res.scada_events or [],
        "attack_events": res.attack_events or [],
        "flisr_actions": res.flisr_actions or []
    }

@router.post("/compare")
def compare_experiments(payload: ComparePayload, db: Session = Depends(get_db)):
    if len(payload.experiment_ids) != 2:
        raise HTTPException(status_code=400, detail="Comparison engine requires exactly 2 experiment IDs")
        
    exp1_uuid = uuid.UUID(payload.experiment_ids[0])
    exp2_uuid = uuid.UUID(payload.experiment_ids[1])
    
    res1 = db.query(ExperimentResult).filter(ExperimentResult.experiment_id == exp1_uuid).first()
    res2 = db.query(ExperimentResult).filter(ExperimentResult.experiment_id == exp2_uuid).first()
    
    if not res1 or not res2:
        raise HTTPException(status_code=404, detail="One or both experiments do not have valid result metrics recorded")
        
    return {
        "experiment_a": {
            "id": str(exp1_uuid),
            "detection_rate": float(res1.detection_rate),
            "resilience_score": float(res1.resilience_score),
            "recovery_time": res1.recovery_time_seconds,
            "financial_loss": float(res1.financial_loss),
            "attack_success_rate": float(res1.attack_success_rate)
        },
        "experiment_b": {
            "id": str(exp2_uuid),
            "detection_rate": float(res2.detection_rate),
            "resilience_score": float(res2.resilience_score),
            "recovery_time": res2.recovery_time_seconds,
            "financial_loss": float(res2.financial_loss),
            "attack_success_rate": float(res2.attack_success_rate)
        }
    }

@router.get("/{id}/export/pdf")
def export_pdf(id: str, db: Session = Depends(get_db)):
    exp_uuid = uuid.UUID(id)
    exp = db.query(Experiment).filter(Experiment.id == exp_uuid).first()
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")
        
    # Generate mock PDF payload structure
    pdf_buffer = io.BytesIO()
    pdf_buffer.write(f"%PDF-1.4\n%PYPY Grid Cyber-Range PDF Export\nExperiment: {exp.name}\nDescription: {exp.description}\n".encode())
    pdf_buffer.seek(0)
    
    headers = {
        "Content-Disposition": f"attachment; filename=experiment_{id}.pdf"
    }
    return Response(content=pdf_buffer.getvalue(), media_type="application/pdf", headers=headers)

@router.get("/{id}/export/csv")
def export_csv(id: str, db: Session = Depends(get_db)):
    exp_uuid = uuid.UUID(id)
    res = db.query(ExperimentResult).filter(ExperimentResult.experiment_id == exp_uuid).first()
    if not res or not res.telemetry_history:
        raise HTTPException(status_code=404, detail="Telemetry time-series history not found")
        
    csv_buffer = io.StringIO()
    writer = csv.writer(csv_buffer)
    writer.writerow(["Step", "Voltage", "Frequency"])
    for row in res.telemetry_history:
        writer.writerow([row.get("step"), row.get("voltage"), row.get("frequency")])
        
    headers = {
        "Content-Disposition": f"attachment; filename=experiment_{id}.csv"
    }
    return Response(content=csv_buffer.getvalue(), media_type="text/csv", headers=headers)

@router.get("/{id}/export/json")
def export_json(id: str, db: Session = Depends(get_db)):
    exp_uuid = uuid.UUID(id)
    exp = db.query(Experiment).filter(Experiment.id == exp_uuid).first()
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")
        
    result = db.query(ExperimentResult).filter(ExperimentResult.experiment_id == exp_uuid).first()
    
    data = {
        "id": str(exp.id),
        "name": exp.name,
        "description": exp.description,
        "grid_type": exp.grid_type,
        "created_at": exp.created_at.isoformat(),
        "metrics": {
            "resilience_score": float(result.resilience_score) if result else 0.0,
            "detection_rate": float(result.detection_rate) if result else 0.0,
            "recovery_time_seconds": result.recovery_time_seconds if result else 0,
            "financial_loss": float(result.financial_loss) if result else 0.0,
            "attack_success_rate": float(result.attack_success_rate) if result else 0.0
        } if result else {}
    }
    
    headers = {
        "Content-Disposition": f"attachment; filename=experiment_{id}.json"
    }
    return Response(content=json.dumps(data, indent=2), media_type="application/json", headers=headers)
