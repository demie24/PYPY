# tests/test_v113.py

import os
import sys
import uuid
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

# Ensure core/ is in Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../core")))

from services.auth.models import Base, Tenant, User, Scenario, SimulatorRun, AuditTrail
from services.simulation.launcher import launch_grid_scenario, stop_grid_scenario

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

@patch("services.simulation.launcher.run_grid_simulation")
def test_free_concurrency_and_grid_limits(mock_task, db_session):
    # Setup mock Celery task delay response
    mock_task.delay.side_effect = lambda *args, **kwargs: MagicMock(id=f"mock-celery-id-{uuid.uuid4().hex[:8]}")

    # 1. Setup Free tenant
    tenant = Tenant(name="Free Org", subdomain="free", plan_tier="free")
    db_session.add(tenant)
    db_session.flush()
    
    user = User(tenant_id=tenant.id, email="admin@free.com", password_hash="dummy")
    db_session.add(user)
    db_session.flush()
    
    # Allowed scenario
    scenario_allowed = Scenario(tenant_id=tenant.id, name="Nominal 14", grid_type="IEEE14", config={})
    # Blocked scenario
    scenario_blocked = Scenario(tenant_id=tenant.id, name="Large 118", grid_type="IEEE118", config={})
    db_session.add_all([scenario_allowed, scenario_blocked])
    db_session.commit()
    
    # Verify free tier cannot launch IEEE118
    with pytest.raises(PermissionError) as exc_grid:
        launch_grid_scenario(db_session, tenant.id, user.id, scenario_blocked.id)
    assert "locked in Free Plan" in str(exc_grid.value)
    
    # Launch allowed scenario
    run1 = launch_grid_scenario(db_session, tenant.id, user.id, scenario_allowed.id)
    assert run1.status == "RUNNING"
    assert run1.celery_task_id.startswith("mock-celery-id-")
    
    # Verify launching second scenario fails under Free concurrency quota limit of 1
    with pytest.raises(PermissionError) as exc_concurrency:
        launch_grid_scenario(db_session, tenant.id, user.id, scenario_allowed.id)
    assert "Free Plan concurrency limit reached" in str(exc_concurrency.value)

@patch("services.simulation.launcher.run_grid_simulation")
def test_premium_concurrency_limits(mock_task, db_session):
    mock_task.delay.side_effect = lambda *args, **kwargs: MagicMock(id=f"mock-celery-id-premium-{uuid.uuid4().hex[:8]}")

    # 1. Setup Premium tenant (limit 3)
    tenant = Tenant(name="Premium Org", subdomain="prem", plan_tier="academic_premium")
    db_session.add(tenant)
    db_session.flush()
    
    user = User(tenant_id=tenant.id, email="admin@prem.com", password_hash="dummy")
    db_session.add(user)
    db_session.flush()
    
    scenario = Scenario(tenant_id=tenant.id, name="Big 118", grid_type="IEEE118", config={})
    db_session.add(scenario)
    db_session.commit()
    
    # Launch up to 3 runs
    runs = []
    for i in range(3):
        run = launch_grid_scenario(db_session, tenant.id, user.id, scenario.id)
        assert run.status == "RUNNING"
        runs.append(run)
        
    # Launching 4th run fails under concurrency quota limit of 3
    with pytest.raises(PermissionError) as exc_concurrency:
        launch_grid_scenario(db_session, tenant.id, user.id, scenario.id)
    assert "Academic Premium Plan concurrency limit reached" in str(exc_concurrency.value)

    # 2. Setup Research Lab tenant (limit 5)
    tenant_lab = Tenant(name="Lab Org", subdomain="lab", plan_tier="research_lab")
    db_session.add(tenant_lab)
    db_session.flush()
    
    user_lab = User(tenant_id=tenant_lab.id, email="admin@lab.com", password_hash="dummy")
    db_session.add(user_lab)
    db_session.flush()
    
    scenario_lab = Scenario(tenant_id=tenant_lab.id, name="Big 118", grid_type="IEEE118", config={})
    db_session.add(scenario_lab)
    db_session.commit()
    
    runs_lab = []
    for i in range(5):
        run = launch_grid_scenario(db_session, tenant_lab.id, user_lab.id, scenario_lab.id)
        assert run.status == "RUNNING"
        runs_lab.append(run)
        
    # Launching 6th run fails under concurrency quota limit of 5
    with pytest.raises(PermissionError) as exc_concurrency_lab:
        launch_grid_scenario(db_session, tenant_lab.id, user_lab.id, scenario_lab.id)
    assert "Research Lab Plan concurrency limit reached" in str(exc_concurrency_lab.value)

@patch("workers.simulation.tasks.app.control.revoke")
def test_stop_grid_scenario(mock_revoke, db_session):
    tenant = Tenant(name="Stop Org", subdomain="stop", plan_tier="academic_premium")
    db_session.add(tenant)
    db_session.flush()
    
    run = SimulatorRun(
        tenant_id=tenant.id,
        celery_task_id="celery-task-to-stop",
        status="RUNNING",
        started_at=datetime.now(timezone.utc)
    )
    db_session.add(run)
    db_session.commit()
    
    # Stop scenario
    stopped_run = stop_grid_scenario(db_session, tenant.id, run.id)
    assert stopped_run.status == "STOPPED"
    assert stopped_run.stopped_at is not None
    mock_revoke.assert_called_once_with("celery-task-to-stop", terminate=True)
