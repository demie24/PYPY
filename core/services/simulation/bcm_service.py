# core/services/simulation/bcm_service.py

import uuid
from sqlalchemy import func
from sqlalchemy.orm import Session
from services.auth.models import SimulatorRun

COST_PER_MWH = 150.00  # unserved MWh cost

def calculate_estimated_loss(load_shed_mwh: float) -> float:
    return float(load_shed_mwh * COST_PER_MWH)

def get_bcm_metrics_summary(db: Session, tenant_id: uuid.UUID) -> dict:
    # Query averages and totals from completed simulator runs
    res = db.query(
        func.avg(SimulatorRun.bcm_rto_seconds).label("avg_rto"),
        func.avg(SimulatorRun.bcm_rpo_seconds).label("avg_rpo"),
        func.sum(SimulatorRun.total_load_shed_mwh).label("total_shed"),
        func.sum(SimulatorRun.estimated_financial_loss).label("total_loss")
    ).filter(
        SimulatorRun.tenant_id == tenant_id,
        SimulatorRun.status == "COMPLETED"
    ).first()
    
    return {
        "average_rto": float(res.avg_rto or 0.0),
        "average_rpo": float(res.avg_rpo or 0.0),
        "total_load_shed_mwh": float(res.total_shed or 0.0),
        "total_financial_loss": float(res.total_loss or 0.0)
    }
