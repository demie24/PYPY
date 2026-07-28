# tests/test_v116.py

import os
import sys
import uuid
import pytest
from datetime import datetime, timezone
from fastapi import HTTPException

# Ensure core/ is in Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../core")))

from services.auth.models import Base, Tenant, User, CopilotMessage, Experiment, ExperimentResult, ScenarioTemplate
from gateway.routes.copilot import post_copilot_chat, get_chat_history, post_copilot_summary, post_copilot_recommendations, post_copilot_compare, post_copilot_report, ChatPayload, SummaryPayload, RecommendationPayload, ComparePayload, ReportPayload

@pytest.fixture
def db_session():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    try:
        # Seed scenario template
        tmpl = ScenarioTemplate(
            id=uuid.uuid4(),
            name="FDIA Attack",
            description="Launches False Data Injection",
            grid_type="IEEE39",
            category="Attack",
            difficulty="Intermediate",
            config={}
        )
        session.add(tmpl)
        session.commit()
        yield session
    finally:
        session.close()

def test_copilot_quotas(db_session):
    tenant_id = uuid.uuid4()
    tenant = Tenant(id=tenant_id, name="Sandbox Tenant", subdomain="sandbox", plan_tier="free")
    db_session.add(tenant)
    db_session.commit()
    
    claims = {"tenant_id": str(tenant_id), "user_id": str(uuid.uuid4())}
    payload = ChatPayload(message="Is there any FDIA threat?")
    
    # 1. Free plan allows up to 50 prompts
    for i in range(50):
        db_session.add(CopilotMessage(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            role="user",
            content=f"msg {i}"
        ))
    db_session.commit()
    
    # 51st prompt should raise 403 Forbidden
    with pytest.raises(HTTPException) as exc:
        post_copilot_chat(payload, claims, db_session)
    assert exc.value.status_code == 403
    assert "quota limit reached" in exc.value.detail

def test_copilot_chat_rag_and_explainable_ai(db_session):
    tenant_id = uuid.uuid4()
    tenant = Tenant(id=tenant_id, name="Premium Tenant", subdomain="premium", plan_tier="academic_premium")
    db_session.add(tenant)
    db_session.commit()
    
    claims = {"tenant_id": str(tenant_id), "user_id": str(uuid.uuid4())}
    
    # Message triggering RAG scenario match
    payload = ChatPayload(message="Tell me about FDIA Attack")
    res = post_copilot_chat(payload, claims, db_session)
    
    assert "reply" in res
    assert "citations" in res
    assert any(c["type"] == "scenario" and c["name"] == "FDIA Attack" for c in res["citations"])
    assert "Explainable AI Diagnostic" in res["reply"]
    
    # Verify saved messages
    history = get_chat_history(claims, db_session)
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[1]["role"] == "assistant"

def test_autonomous_insight_and_recommendations(db_session):
    exp_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    
    exp = Experiment(id=exp_id, tenant_id=tenant_id, user_id=uuid.uuid4(), name="Outage Analysis", grid_type="IEEE14")
    db_session.add(exp)
    db_session.flush()
    
    res = ExperimentResult(
        id=uuid.uuid4(), tenant_id=tenant_id, experiment_id=exp_id,
        resilience_score=80.0, rto_seconds=30, rpo_seconds=5, total_load_shed_mwh=5.0, financial_loss=10000.0, verdict="DEGRADED"
    )
    db_session.add(res)
    db_session.commit()
    
    # 1. Summary
    payload_summary = SummaryPayload(experiment_id=str(exp_id))
    summary_res = post_copilot_summary(payload_summary, db_session)
    assert "Outage Analysis" in summary_res["summary"]
    
    # 2. Recommendations
    payload_rec = RecommendationPayload(experiment_id=str(exp_id))
    rec_res = post_copilot_recommendations(payload_rec, db_session)
    assert "Mitigation Advisory" in rec_res["recommendations"]

def test_thesis_writing_assistant(db_session):
    exp_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    
    exp = Experiment(id=exp_id, tenant_id=tenant_id, user_id=uuid.uuid4(), name="Mitigation sandbox", grid_type="IEEE39")
    db_session.add(exp)
    db_session.commit()
    
    # Abstract
    payload_abstract = ReportPayload(experiment_id=str(exp_id), section="abstract")
    res_abstract = post_copilot_report(payload_abstract, db_session)
    assert "ABSTRACT" in res_abstract["section_text"]
    
    # Discussion
    payload_discussion = ReportPayload(experiment_id=str(exp_id), section="discussion")
    res_discussion = post_copilot_report(payload_discussion, db_session)
    assert "DISCUSSION" in res_discussion["section_text"]
    
    # Conclusion
    payload_conclusion = ReportPayload(experiment_id=str(exp_id), section="conclusion")
    res_conclusion = post_copilot_report(payload_conclusion, db_session)
    assert "CONCLUSION" in res_conclusion["section_text"]
