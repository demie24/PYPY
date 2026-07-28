# tests/test_v115.py

import os
import sys
import uuid
import json
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone
from fastapi import HTTPException

# Ensure core/ is in Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../core")))

from services.auth.models import Base, Tenant, User, Experiment, ExperimentResult, ExperimentTag, ExperimentShare
from gateway.routes.experiments import list_experiments, create_experiment, get_experiment_details, update_experiment, delete_experiment, share_experiment, get_replay_logs, compare_experiments, export_json, export_csv, export_pdf, ExperimentCreateSchema, ExperimentUpdateSchema, SharePayload, ComparePayload

@pytest.fixture
def db_session():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

def test_experiment_creation_and_quota(db_session):
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    
    tenant = Tenant(id=tenant_id, name="Grid Corp", subdomain="gridcorp", plan_tier="free")
    db_session.add(tenant)
    db_session.commit()
    
    claims = {"tenant_id": str(tenant_id), "user_id": str(user_id)}
    
    # 1. Create up to 10 experiments
    for i in range(10):
        payload = ExperimentCreateSchema(
            name=f"Exp {i}",
            grid_type="IEEE14",
            description="test experiment",
            tags=["attack"]
        )
        res = create_experiment(payload, claims, db_session)
        assert res["status"] == "SUCCESS"
        
    assert db_session.query(Experiment).filter(Experiment.tenant_id == tenant_id).count() == 10
    
    # 2. 11th experiment should trigger quota limits restriction
    payload_overflow = ExperimentCreateSchema(
        name="Exp 11",
        grid_type="IEEE14",
        description="test experiment",
        tags=["attack"]
    )
    with pytest.raises(HTTPException) as exc:
        create_experiment(payload_overflow, claims, db_session)
    assert exc.value.status_code == 403
    assert "limit exceeded" in exc.value.detail

def test_experiment_list_and_filters(db_session):
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    
    claims = {"tenant_id": str(tenant_id), "user_id": str(user_id)}
    
    # Create experiments with different tags
    exp1 = Experiment(id=uuid.uuid4(), tenant_id=tenant_id, user_id=user_id, name="Contingency Case A", grid_type="IEEE39")
    exp2 = Experiment(id=uuid.uuid4(), tenant_id=tenant_id, user_id=user_id, name="Cyber Intrusion FDIA", grid_type="IEEE14")
    db_session.add_all([exp1, exp2])
    db_session.flush()
    
    db_session.add(ExperimentTag(id=uuid.uuid4(), experiment_id=exp1.id, tag="fault"))
    db_session.add(ExperimentTag(id=uuid.uuid4(), experiment_id=exp2.id, tag="attack"))
    db_session.commit()
    
    # Check all
    res_all = list_experiments(claims=claims, db=db_session)
    assert len(res_all) == 2
    
    # Check search
    res_search = list_experiments(search="Intrusion", claims=claims, db=db_session)
    assert len(res_search) == 1
    assert res_search[0]["name"] == "Cyber Intrusion FDIA"
    
    # Check tag
    res_tag = list_experiments(tag="fault", claims=claims, db=db_session)
    assert len(res_tag) == 1
    assert res_tag[0]["name"] == "Contingency Case A"

def test_experiment_shares_access_rules(db_session):
    tenant_a_id = uuid.uuid4()
    tenant_b_id = uuid.uuid4()
    user_a_id = uuid.uuid4()
    user_b_id = uuid.uuid4()
    
    # Tenant A is Free, Tenant B is Research Lab
    tenant_a = Tenant(id=tenant_a_id, name="SaaS Free", subdomain="saasfree", plan_tier="free")
    tenant_b = Tenant(id=tenant_b_id, name="Academic Lab", subdomain="academicrob", plan_tier="research_lab")
    db_session.add_all([tenant_a, tenant_b])
    db_session.commit()
    
    exp = Experiment(id=uuid.uuid4(), tenant_id=tenant_a_id, user_id=user_a_id, name="Intrusion Test", grid_type="IEEE14")
    db_session.add(exp)
    db_session.commit()
    
    # 1. Free tier trying to share should fail
    claims_a = {"tenant_id": str(tenant_a_id), "user_id": str(user_a_id)}
    payload = SharePayload(shared_with_tenant_id=str(tenant_b_id))
    
    with pytest.raises(HTTPException) as exc:
        share_experiment(str(exp.id), payload, claims_a, db_session)
    assert exc.value.status_code == 403
    assert "restricted to Research Lab" in exc.value.detail
    
    # 2. Research Lab sharing inside team (same tenant ID) should pass
    exp_b = Experiment(id=uuid.uuid4(), tenant_id=tenant_b_id, user_id=user_b_id, name="Grid Replay Test", grid_type="IEEE39")
    db_session.add(exp_b)
    db_session.commit()
    
    claims_b = {"tenant_id": str(tenant_b_id), "user_id": str(user_b_id)}
    payload_internal = SharePayload(shared_with_tenant_id=str(tenant_b_id))
    
    share_res = share_experiment(str(exp_b.id), payload_internal, claims_b, db_session)
    assert share_res["status"] == "SUCCESS"

def test_comparison_engine(db_session):
    exp1_id = uuid.uuid4()
    exp2_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    
    exp1 = Experiment(id=exp1_id, tenant_id=tenant_id, user_id=uuid.uuid4(), name="Scenario 1", grid_type="IEEE14")
    exp2 = Experiment(id=exp2_id, tenant_id=tenant_id, user_id=uuid.uuid4(), name="Scenario 2", grid_type="IEEE14")
    db_session.add_all([exp1, exp2])
    db_session.flush()
    
    res1 = ExperimentResult(
        id=uuid.uuid4(), tenant_id=tenant_id, experiment_id=exp1_id,
        resilience_score=94.5, rto_seconds=10, rpo_seconds=1, total_load_shed_mwh=0.5, financial_loss=1200.0, verdict="NOMINAL",
        detection_rate=98.2, recovery_time_seconds=10, attack_success_rate=5.0
    )
    res2 = ExperimentResult(
        id=uuid.uuid4(), tenant_id=tenant_id, experiment_id=exp2_id,
        resilience_score=62.4, rto_seconds=120, rpo_seconds=20, total_load_shed_mwh=50.2, financial_loss=150000.0, verdict="BLACKOUT",
        detection_rate=45.0, recovery_time_seconds=120, attack_success_rate=95.0
    )
    db_session.add_all([res1, res2])
    db_session.commit()
    
    payload = ComparePayload(experiment_ids=[str(exp1_id), str(exp2_id)])
    comparison = compare_experiments(payload, db_session)
    
    assert comparison["experiment_a"]["resilience_score"] == 94.5
    assert comparison["experiment_b"]["resilience_score"] == 62.4

def test_exports_formats(db_session):
    exp_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    
    exp = Experiment(id=exp_id, tenant_id=tenant_id, user_id=uuid.uuid4(), name="Export Doc", grid_type="IEEE39")
    db_session.add(exp)
    db_session.flush()
    
    res = ExperimentResult(
        id=uuid.uuid4(), tenant_id=tenant_id, experiment_id=exp_id,
        resilience_score=80.0, rto_seconds=30, rpo_seconds=5, total_load_shed_mwh=5.0, financial_loss=10000.0, verdict="DEGRADED",
        telemetry_history=[{"step": 0, "voltage": 1.0, "frequency": 60.0}]
    )
    db_session.add(res)
    db_session.commit()
    
    # 1. PDF Export
    pdf_resp = export_pdf(str(exp_id), db_session)
    assert pdf_resp.headers["Content-Disposition"] == f"attachment; filename=experiment_{exp_id}.pdf"
    
    # 2. CSV Export
    csv_resp = export_csv(str(exp_id), db_session)
    assert b"Voltage,Frequency" in csv_resp.body
    
    # 3. JSON Export
    json_resp = export_json(str(exp_id), db_session)
    body_data = json.loads(json_resp.body)
    assert body_data["name"] == "Export Doc"
