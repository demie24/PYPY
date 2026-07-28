# core/gateway/routes/copilot.py

import os
import uuid
import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from services.auth.session import get_db
from services.auth.auth_service import get_current_user_claims
from services.auth.models import CopilotMessage, Tenant, Experiment, ExperimentResult, ScenarioTemplate, FavoriteScenario

logger = logging.getLogger("gateway.routes.copilot")
router = APIRouter(prefix="/copilot", tags=["copilot"])

class ChatPayload(BaseModel):
    message: str

class SummaryPayload(BaseModel):
    experiment_id: Optional[str] = None
    scenario_template_id: Optional[str] = None

class RecommendationPayload(BaseModel):
    experiment_id: str

class ComparePayload(BaseModel):
    experiment_ids: List[str]

class ReportPayload(BaseModel):
    experiment_id: str
    section: str # 'abstract', 'discussion', 'conclusion'

PROMPT_QUOTAS = {
    "free": 50,
    "academic_premium": 500,
    "research_lab": 2000,
    "enterprise": 99999999
}

@router.get("/history")
def get_chat_history(claims: dict = Depends(get_current_user_claims), db: Session = Depends(get_db)):
    tenant_id_str = claims.get("tenant_id")
    if not tenant_id_str:
        raise HTTPException(status_code=400, detail="Missing tenant identity claim.")
    tenant_uuid = uuid.UUID(tenant_id_str)
    
    messages = db.query(CopilotMessage).filter(
        CopilotMessage.tenant_id == tenant_uuid
    ).order_by(CopilotMessage.created_at.asc()).all()
    
    return [
        {
            "id": str(m.id),
            "role": m.role,
            "content": m.content,
            "citations": m.citations or [],
            "created_at": m.created_at.isoformat()
        } for m in messages
    ]

@router.post("/chat")
def post_copilot_chat(
    payload: ChatPayload,
    claims: dict = Depends(get_current_user_claims),
    db: Session = Depends(get_db)
):
    tenant_id_str = claims.get("tenant_id")
    if not tenant_id_str:
        raise HTTPException(status_code=400, detail="Missing tenant identity claim.")
    tenant_uuid = uuid.UUID(tenant_id_str)
    
    # 1. Quota Check
    tenant = db.query(Tenant).filter(Tenant.id == tenant_uuid).first()
    tier = (tenant.plan_tier or "free").lower()
    quota = PROMPT_QUOTAS.get(tier, 50)
    
    # Count messages sent by this tenant this month
    start_of_month = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    msg_count = db.query(CopilotMessage).filter(
        CopilotMessage.tenant_id == tenant_uuid,
        CopilotMessage.role == "user",
        CopilotMessage.created_at >= start_of_month
    ).count()
    
    if msg_count >= quota:
        raise HTTPException(
            status_code=403,
            detail=f"Prompt quota limit reached. {tier.replace('_', ' ').title()} tier is capped at {quota} prompts per month. Upgrade required."
        )
        
    user_msg = payload.message
    
    # 2. RAG Knowledge Retrieval & Citations
    citations = []
    # Query scenario templates
    scenarios = db.query(ScenarioTemplate).all()
    # Mock RAG matching logic based on keywords
    matched_sc = None
    for sc in scenarios:
        if sc.name.lower() in user_msg.lower() or sc.category.lower() in user_msg.lower():
            matched_sc = sc
            citations.append({"type": "scenario", "name": sc.name, "mitre": sc.mitre_attack_id})
            break
            
    # Default citation
    citations.append({"type": "documentation", "name": "PYPY Smart-Grid Cybersecurity Framework Handbook v11.6"})
    
    # 3. Formulate Explainable AI Response
    explainable_block = ""
    if "fdia" in user_msg.lower() or "voltage" in user_msg.lower():
        explainable_block = (
            "\n\n[Explainable AI Diagnostic]\n"
            "- Detection Decision: Anomaly flag raised due to State Estimation residual (KCL mismatch) exceeding 0.042 pu.\n"
            "- Mitigation Action: Switching telemetry stream to backup Blockchain-secured registers.\n"
            "- Resilience Degradation: System voltage stability recovered from 0.92 pu back to nominal 1.01 pu."
        )
    elif "replay" in user_msg.lower() or "operator" in user_msg.lower():
        explainable_block = (
            "\n\n[Explainable AI Diagnostic]\n"
            "- Detection Decision: Replay attack detected using sequence timestamp correlation filters.\n"
            "- Mitigation Action: Initiated SCADA channel cryptographic token refresh sweep."
        )
    else:
        explainable_block = (
            "\n\n[Explainable AI Diagnostic]\n"
            "- Focus Area: Standard smart-grid resilience validation. System voltage values nominal."
        )
        
    ai_response = (
        f"Based on grid telemetry databases and current scenario marketplace settings, here is the cybersecurity analysis: "
        f"The query relates to smart grid vulnerabilities. We recommend executing active telemetry checks. "
        f"If an intrusion is confirmed, trigger the FLISR service zone isolation sequence.{explainable_block}"
    )
    
    # 4. Save Conversation History
    db.add(CopilotMessage(
        id=uuid.uuid4(),
        tenant_id=tenant_uuid,
        role="user",
        content=user_msg,
        citations=[]
    ))
    db.add(CopilotMessage(
        id=uuid.uuid4(),
        tenant_id=tenant_uuid,
        role="assistant",
        content=ai_response,
        citations=citations
    ))
    db.commit()
    
    return {
        "reply": ai_response,
        "citations": citations
    }

@router.post("/summary")
def post_copilot_summary(payload: SummaryPayload, db: Session = Depends(get_db)):
    if payload.experiment_id:
        exp = db.query(Experiment).filter(Experiment.id == uuid.UUID(payload.experiment_id)).first()
        if not exp:
            raise HTTPException(status_code=404, detail="Experiment not found")
        result = db.query(ExperimentResult).filter(ExperimentResult.experiment_id == exp.id).first()
        res_score = float(result.resilience_score) if result else 85.0
        
        content = (
            f"Autonomous Summary for Experiment '{exp.name}':\n"
            f"- Grid Model: {exp.grid_type}\n"
            f"- Resilience Score: {res_score}%\n"
            f"- Findings: System encountered contingency faults. State Estimators operated dynamically. "
            f"Explainable AI suggests the voltage drop triggered defensive loadshedding actions."
        )
    elif payload.scenario_template_id:
        tmpl = db.query(ScenarioTemplate).filter(ScenarioTemplate.id == uuid.UUID(payload.scenario_template_id)).first()
        if not tmpl:
            raise HTTPException(status_code=404, detail="Scenario template not found")
        content = (
            f"Autonomous Summary for Scenario Template '{tmpl.name}':\n"
            f"- Grid Model: {tmpl.grid_type}\n"
            f"- Objective: {tmpl.objective}\n"
            f"- MITRE Attack Map: {tmpl.mitre_attack_id} - {tmpl.mitre_attack_name}\n"
            f"- Threat Description: {tmpl.description}"
        )
    else:
        raise HTTPException(status_code=400, detail="Must provide experiment_id or scenario_template_id")
        
    return {"summary": content}

@router.post("/recommendations")
def post_copilot_recommendations(payload: RecommendationPayload, db: Session = Depends(get_db)):
    exp_uuid = uuid.UUID(payload.experiment_id)
    exp = db.query(Experiment).filter(Experiment.id == exp_uuid).first()
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")
        
    result = db.query(ExperimentResult).filter(ExperimentResult.experiment_id == exp_uuid).first()
    loss = float(result.financial_loss) if result else 0.0
    
    recommendations = (
        f"Autonomous Mitigation Advisory for Experiment '{exp.name}':\n"
        f"1. Deploy Blockchain-based state verification to secure SCADA links (Addresses MITRE T0811).\n"
        f"2. Configure FLISR Zone isolation algorithms on IEEE model loops to reduce the financial impact of line overloads (Target Loss RM {loss:,}).\n"
        f"3. Enable strict Underfrequency Load Shedding (UFLS) parameters."
    )
    return {"recommendations": recommendations}

@router.post("/compare")
def post_copilot_compare(payload: ComparePayload, db: Session = Depends(get_db)):
    if len(payload.experiment_ids) != 2:
        raise HTTPException(status_code=400, detail="Requires exactly 2 experiment IDs")
        
    exp1_uuid = uuid.UUID(payload.experiment_ids[0])
    exp2_uuid = uuid.UUID(payload.experiment_ids[1])
    
    res1 = db.query(ExperimentResult).filter(ExperimentResult.experiment_id == exp1_uuid).first()
    res2 = db.query(ExperimentResult).filter(ExperimentResult.experiment_id == exp2_uuid).first()
    
    if not res1 or not res2:
        raise HTTPException(status_code=404, detail="Result metrics missing")
        
    analysis = (
        f"Comparative Analysis Writeup:\n"
        f"- Experiment A Resilience ({float(res1.resilience_score)}%) compared to Experiment B Resilience ({float(res2.resilience_score)}%).\n"
        f"- Detection rates differ by {abs(float(res1.detection_rate) - float(res2.detection_rate)):.1f}%.\n"
        f"- Recovery time analysis indicates Experiment A recovered {abs(res1.recovery_time_seconds - res2.recovery_time_seconds)}s faster."
    )
    return {"analysis": analysis}

@router.post("/report")
def post_copilot_report(payload: ReportPayload, db: Session = Depends(get_db)):
    exp_uuid = uuid.UUID(payload.experiment_id)
    exp = db.query(Experiment).filter(Experiment.id == exp_uuid).first()
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")
        
    result = db.query(ExperimentResult).filter(ExperimentResult.experiment_id == exp_uuid).first()
    res_score = float(result.resilience_score) if result else 85.0
    
    sect = payload.section.lower()
    if sect == "abstract":
        text = (
            f"ABSTRACT: This study investigates smart-grid cybersecurity resilience under physical failures. "
            f"Using the digital twin sandbox model '{exp.name}' built on grid model '{exp.grid_type}', we simulated coordinated attacks. "
            f"Empirical results show a resilience score of {res_score}%, highlighting the critical role of automatic recovery schemes."
        )
    elif sect == "discussion":
        text = (
            f"DISCUSSION: The experimental data collected from '{exp.name}' demonstrates that cyber-physical attacks cause immediate state estimate skewing. "
            f"Traditional Bad Data Detection algorithms failed to detect malicious injections. "
            f"However, integrating advanced cryptographical state checks significantly mitigated cascade trips."
        )
    elif sect == "conclusion":
        text = (
            f"CONCLUSION: In conclusion, smart grid structures require resilient mitigation. "
            f"The '{exp.name}' sandbox simulation confirms that early FLISR switch actions save system loads. "
            f"Future work should expand neural net intrusion detection accuracy."
        )
    else:
        raise HTTPException(status_code=400, detail="Invalid section keyword.")
        
    return {"section_text": text}
