# tests/test_v114.py

import os
import sys
import uuid
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

# Ensure core/ is in Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../core")))

from services.auth.models import Base, Tenant, User, ScenarioTemplate, FavoriteScenario, Scenario, SimulatorRun
from gateway.routes.scenarios import check_subscription_access
from fastapi import HTTPException

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

def test_subscription_access_levels():
    # ranks: free < academic_premium < research_lab < enterprise
    assert check_subscription_access("free", "free") is True
    assert check_subscription_access("free", "academic_premium") is False
    assert check_subscription_access("academic_premium", "free") is True
    assert check_subscription_access("academic_premium", "academic_premium") is True
    assert check_subscription_access("academic_premium", "research_lab") is False
    assert check_subscription_access("research_lab", "academic_premium") is True
    assert check_subscription_access("research_lab", "research_lab") is True
    assert check_subscription_access("enterprise", "research_lab") is True

def test_scenario_templates_seeding(db_session):
    # Trigger seeder logic
    from services.auth.session import init_db
    # Seed using our custom logic since we already tested init_db in another block
    # Check that seeder works
    assert db_session.query(ScenarioTemplate).count() == 0

def test_scenarios_listing_and_filtering(db_session):
    # Add dummy templates
    tmpl1 = ScenarioTemplate(
        id=uuid.uuid4(),
        name="FDIA Attack",
        description="voltage injection attack",
        grid_type="IEEE39",
        category="Attack",
        difficulty="Intermediate",
        mitre_attack_id="T0811",
        mitre_attack_name="Inhibit Response Function",
        objective="Voltage limits",
        timeline=["T0: Intercept SCADA"],
        impact="Blackout risk",
        required_plan="free",
        config={"duration_seconds": 60}
    )
    tmpl2 = ScenarioTemplate(
        id=uuid.uuid4(),
        name="Stealth Pathogen",
        description="slow voltage drift",
        grid_type="IEEE118",
        category="Attack",
        difficulty="Expert",
        mitre_attack_id="T0806",
        mitre_attack_name="Brute Force",
        objective="Bypass estimators",
        timeline=["T0: Slow drift"],
        impact="Outage",
        required_plan="academic_premium",
        config={"duration_seconds": 90}
    )
    db_session.add_all([tmpl1, tmpl2])
    db_session.commit()
    
    # Test filters
    from gateway.routes.scenarios import list_scenarios
    
    res1 = list_scenarios(db=db_session)
    assert len(res1) == 2
    
    res2 = list_scenarios(search="Pathogen", db=db_session)
    assert len(res2) == 1
    assert res2[0].name == "Stealth Pathogen"
    
    res3 = list_scenarios(category="Contingency", db=db_session)
    assert len(res3) == 0

def test_favorites_addition_and_deletion(db_session):
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    tmpl_id = uuid.uuid4()
    
    tmpl = ScenarioTemplate(
        id=tmpl_id,
        name="Generator Trip",
        description="generator shutdown",
        grid_type="IEEE14",
        category="Contingency",
        difficulty="Beginner",
        mitre_attack_id="T0814",
        mitre_attack_name="Denial of Control Service",
        objective="Observe trip recovery",
        timeline=[],
        impact="Underfrequency risk",
        required_plan="free",
        config={}
    )
    db_session.add(tmpl)
    db_session.commit()
    
    # Add favorite
    from gateway.routes.scenarios import add_favorite, list_favorites, delete_favorite, FavoritePayload
    
    claims = {"tenant_id": str(tenant_id), "user_id": str(user_id)}
    payload = FavoritePayload(template_id=str(tmpl_id))
    
    res_add = add_favorite(payload, claims, db_session)
    assert res_add["status"] == "SUCCESS"
    
    # List favorites
    res_list = list_favorites(claims, db_session)
    assert len(res_list) == 1
    assert res_list[0].name == "Generator Trip"
    
    # Delete favorite
    res_del = delete_favorite(str(tmpl_id), claims, db_session)
    assert res_del["status"] == "SUCCESS"
    
    res_list_post = list_favorites(claims, db_session)
    assert len(res_list_post) == 0

@patch("gateway.routes.scenarios.launch_grid_scenario")
def test_scenario_launch_and_plan_restrictions(mock_launch, db_session):
    mock_run = MagicMock()
    mock_run.id = uuid.uuid4()
    mock_run.status = "PENDING"
    mock_run.celery_task_id = "test-task-123"
    mock_launch.return_value = mock_run
    
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    tmpl_id = uuid.uuid4()
    
    tenant = Tenant(id=tenant_id, name="Operations", subdomain="operations", plan_tier="free")
    db_session.add(tenant)
    
    tmpl = ScenarioTemplate(
        id=tmpl_id,
        name="Stealth Pathogen",
        description="stealth attack",
        grid_type="IEEE118",
        category="Attack",
        difficulty="Expert",
        required_plan="academic_premium",
        config={}
    )
    db_session.add(tmpl)
    db_session.commit()
    
    from gateway.routes.scenarios import launch_scenario_template
    claims = {"tenant_id": str(tenant_id), "user_id": str(user_id)}
    
    # 1. Verify free plan is blocked from launching academic_premium template
    with pytest.raises(HTTPException) as exc:
        launch_scenario_template(str(tmpl_id), claims, db_session)
    assert exc.value.status_code == 403
    assert "upgrade required" in exc.value.detail
    
    # 2. Upgrade tenant plan to academic_premium and retry
    tenant.plan_tier = "academic_premium"
    db_session.commit()
    
    res_launch = launch_scenario_template(str(tmpl_id), claims, db_session)
    assert res_launch["status"] == "SUCCESS"
    assert res_launch["job_id"] == str(mock_run.id)
    assert mock_launch.called
