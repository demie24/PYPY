# core/gateway/routes/scenarios.py

import os
import uuid
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from services.auth.session import get_db
from services.auth.auth_service import get_current_user_claims
from services.auth.models import ScenarioTemplate, FavoriteScenario, Scenario, Tenant
from services.simulation.launcher import launch_grid_scenario

logger = logging.getLogger("gateway.routes.scenarios")
router = APIRouter(prefix="/scenarios", tags=["scenarios"])

class FavoritePayload(BaseModel):
    template_id: str

PLAN_RANKINGS = {
    "free": 0,
    "academic_premium": 1,
    "research_lab": 2,
    "enterprise": 3
}

def check_subscription_access(user_tier: str, required_tier: str) -> bool:
    user_rank = PLAN_RANKINGS.get(user_tier.lower(), 0)
    req_rank = PLAN_RANKINGS.get(required_tier.lower(), 0)
    return user_rank >= req_rank

@router.get("")
def list_scenarios(
    search: Optional[str] = None,
    category: Optional[str] = None,
    difficulty: Optional[str] = None,
    grid_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(ScenarioTemplate)
    if search:
        query = query.filter(
            ScenarioTemplate.name.ilike(f"%{search}%") | 
            ScenarioTemplate.description.ilike(f"%{search}%")
        )
    if category:
        query = query.filter(ScenarioTemplate.category.ilike(category))
    if difficulty:
        query = query.filter(ScenarioTemplate.difficulty.ilike(difficulty))
    if grid_type:
        query = query.filter(ScenarioTemplate.grid_type.ilike(grid_type))
    return query.all()

@router.get("/favorites")
def list_favorites(claims: dict = Depends(get_current_user_claims), db: Session = Depends(get_db)):
    tenant_id_str = claims.get("tenant_id")
    user_id_str = claims.get("user_id")
    if not tenant_id_str or not user_id_str:
        raise HTTPException(status_code=400, detail="User claims missing tenant or user identity.")
        
    tenant_uuid = uuid.UUID(tenant_id_str)
    user_uuid = uuid.UUID(user_id_str)
    
    favs = db.query(FavoriteScenario).filter(
        FavoriteScenario.tenant_id == tenant_uuid,
        FavoriteScenario.user_id == user_uuid
    ).all()
    
    return [fav.template for fav in favs if fav.template]

@router.post("/favorites")
def add_favorite(payload: FavoritePayload, claims: dict = Depends(get_current_user_claims), db: Session = Depends(get_db)):
    tenant_id_str = claims.get("tenant_id")
    user_id_str = claims.get("user_id")
    if not tenant_id_str or not user_id_str:
        raise HTTPException(status_code=400, detail="User claims missing tenant or user identity.")
        
    tenant_uuid = uuid.UUID(tenant_id_str)
    user_uuid = uuid.UUID(user_id_str)
    tmpl_uuid = uuid.UUID(payload.template_id)
    
    # Verify template exists
    tmpl = db.query(ScenarioTemplate).filter(ScenarioTemplate.id == tmpl_uuid).first()
    if not tmpl:
        raise HTTPException(status_code=404, detail="Scenario template not found")
        
    # Check if already favorited
    existing = db.query(FavoriteScenario).filter(
        FavoriteScenario.tenant_id == tenant_uuid,
        FavoriteScenario.user_id == user_uuid,
        FavoriteScenario.template_id == tmpl_uuid
    ).first()
    
    if existing:
        return {"status": "ALREADY_FAVORITED"}
        
    fav = FavoriteScenario(
        id=uuid.uuid4(),
        tenant_id=tenant_uuid,
        user_id=user_uuid,
        template_id=tmpl_uuid
    )
    db.add(fav)
    db.commit()
    return {"status": "SUCCESS"}

@router.delete("/favorites/{id}")
def delete_favorite(id: str, claims: dict = Depends(get_current_user_claims), db: Session = Depends(get_db)):
    tenant_id_str = claims.get("tenant_id")
    user_id_str = claims.get("user_id")
    if not tenant_id_str or not user_id_str:
        raise HTTPException(status_code=400, detail="User claims missing tenant or user identity.")
        
    tenant_uuid = uuid.UUID(tenant_id_str)
    user_uuid = uuid.UUID(user_id_str)
    tmpl_uuid = uuid.UUID(id)
    
    fav = db.query(FavoriteScenario).filter(
        FavoriteScenario.tenant_id == tenant_uuid,
        FavoriteScenario.user_id == user_uuid,
        FavoriteScenario.template_id == tmpl_uuid
    ).first()
    
    if not fav:
        raise HTTPException(status_code=404, detail="Favorite not found")
        
    db.delete(fav)
    db.commit()
    return {"status": "SUCCESS"}

@router.get("/{id}")
def get_scenario(id: str, db: Session = Depends(get_db)):
    tmpl_uuid = uuid.UUID(id)
    tmpl = db.query(ScenarioTemplate).filter(ScenarioTemplate.id == tmpl_uuid).first()
    if not tmpl:
        raise HTTPException(status_code=404, detail="Scenario template not found")
    return tmpl

@router.post("/{id}/launch")
def launch_scenario_template(id: str, claims: dict = Depends(get_current_user_claims), db: Session = Depends(get_db)):
    tenant_id_str = claims.get("tenant_id")
    user_id_str = claims.get("user_id")
    if not tenant_id_str or not user_id_str:
        raise HTTPException(status_code=400, detail="User claims missing tenant or user identity.")
        
    tenant_uuid = uuid.UUID(tenant_id_str)
    user_uuid = uuid.UUID(user_id_str)
    tmpl_uuid = uuid.UUID(id)
    
    # 1. Fetch template details
    tmpl = db.query(ScenarioTemplate).filter(ScenarioTemplate.id == tmpl_uuid).first()
    if not tmpl:
        raise HTTPException(status_code=404, detail="Scenario template not found")
        
    # 2. Fetch tenant plan tier
    tenant = db.query(Tenant).filter(Tenant.id == tenant_uuid).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant record not found")
        
    user_tier = tenant.plan_tier or "free"
    
    # 3. Enforce plan restriction
    if not check_subscription_access(user_tier, tmpl.required_plan):
        raise HTTPException(
            status_code=403, 
            detail=f"Subscription upgrade required: {tmpl.name} requires at least the {tmpl.required_plan.replace('_', ' ').title()} tier."
        )
        
    # 4. Instantiate template scenario
    new_scenario = Scenario(
        id=uuid.uuid4(),
        tenant_id=tenant_uuid,
        name=tmpl.name,
        grid_type=tmpl.grid_type,
        description=tmpl.description,
        config=tmpl.config,
        is_marketplace_template=True
    )
    db.add(new_scenario)
    db.commit()
    
    # 5. Launch using simulation orchestration engine
    try:
        run = launch_grid_scenario(db, tenant_uuid, user_uuid, new_scenario.id)
        return {
            "status": "SUCCESS",
            "job_id": str(run.id),
            "celery_task_id": run.celery_task_id,
            "state": run.status
        }
    except Exception as e:
        logger.error(f"Error launching template scenario: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Simulation orchestrator launch failed: {str(e)}")
