# tests/test_v113_completion.py

import os
import sys
import uuid
import json
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

# Ensure core/ is in Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../core")))

from services.auth.models import Base, Tenant, User, Scenario, SimulatorRun, SimulationAuditLog
from services.simulation.audit import log_simulation_audit
from services.simulation.notifications import send_simulation_email
from workers.health.worker_monitor import (
    increment_active_tasks,
    decrement_active_tasks,
    get_active_tasks_count,
    _heartbeat_loop
)

@pytest.fixture
def db_session():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    # Ensure column is added for SQLite memory DB
    from sqlalchemy import text
    with engine.begin() as conn:
        try:
            conn.execute(text("ALTER TABLE simulator_runs ADD COLUMN progress_percentage INTEGER DEFAULT 0"))
        except Exception:
            pass
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

def test_progress_percentage_and_audit_logging(db_session):
    tenant_id = uuid.uuid4()
    job_id = uuid.uuid4()
    
    # 1. Verify progress percentage defaults to 0 on new SimulatorRun
    run = SimulatorRun(
        id=job_id,
        tenant_id=tenant_id,
        status="RUNNING"
    )
    db_session.add(run)
    db_session.commit()
    
    assert run.progress_percentage == 0
    
    # 2. Update progress percentage
    run.progress_percentage = 50
    db_session.commit()
    
    db_session.refresh(run)
    assert run.progress_percentage == 50
    
    # 3. Log simulation audit
    log_simulation_audit(db_session, tenant_id, job_id, "JOB_STARTED", actor="test_user", details="Test run active")
    
    audit = db_session.query(SimulationAuditLog).filter(SimulationAuditLog.job_id == job_id).first()
    assert audit is not None
    assert audit.action == "JOB_STARTED"
    assert audit.actor == "test_user"
    assert audit.details == "Test run active"

@patch("redis.from_url")
def test_worker_monitor_heartbeat(mock_from_url):
    # Mock redis instance
    r_inst = MagicMock()
    mock_from_url.return_value = r_inst
    
    # Prerun increment
    start_count = get_active_tasks_count()
    increment_active_tasks()
    assert get_active_tasks_count() == start_count + 1
    
    decrement_active_tasks()
    assert get_active_tasks_count() == start_count
    
    # Test heartbeat update
    with patch("time.sleep", side_effect=InterruptedError("Stop loop")):
        with pytest.raises(InterruptedError):
            _heartbeat_loop("redis://localhost:6379/0")
            
    # Verify Redis set was called
    assert r_inst.hset.called

@patch("services.email.email_service.SMTPProvider.send_email")
def test_email_notification_dispatch(mock_send):
    mock_send.return_value = True
    
    send_simulation_email(
        to_email="test@pypy.com",
        template_name="simulation_started.html",
        subject="Simulation Started",
        variables={"run_id": "test-run", "grid_name": "IEEE14", "tenant_id": "test-tenant"}
    )
    
    # Verify mock SMTP send was triggered
    assert mock_send.called
    args, kwargs = mock_send.call_args
    assert args[0] == "test@pypy.com"
    assert args[1] == "Simulation Started"
    assert "test-run" in args[2]

@patch("services.email.email_service.SMTPProvider.send_email")
@patch("redis.from_url")
def test_celery_task_retry_and_dlq(mock_from_url, mock_email, db_session):
    mock_email.return_value = True
    r_inst = MagicMock()
    mock_from_url.return_value = r_inst
    
    tenant = Tenant(name="Test Org", subdomain="test", plan_tier="free")
    db_session.add(tenant)
    db_session.flush()
    
    user = User(tenant_id=tenant.id, email="admin@test.com", password_hash="dummy")
    db_session.add(user)
    db_session.flush()
    
    scenario = Scenario(tenant_id=tenant.id, name="Test Scenario", grid_type="IEEE14", config={})
    db_session.add(scenario)
    db_session.commit()
    
    run = SimulatorRun(
        tenant_id=tenant.id,
        scenario_id=scenario.id,
        status="RUNNING"
    )
    db_session.add(run)
    db_session.commit()
    
    # Cause a dummy exception to test retries inside Celery tasks context
    from workers.simulation.tasks import run_grid_simulation
    
    # Mock celery task properties on the actual proxy/task instance
    mock_req = MagicMock()
    mock_req.retries = 0
    run_grid_simulation.request_stack.push(mock_req)
    run_grid_simulation.max_retries = 3
    
    # Mock retry directly on the bound task instance
    mock_retry = MagicMock()
    run_grid_simulation.__wrapped__.__self__.retry = mock_retry
    
    # We patch get_db_context to return our db_session
    @contextmanager_mock
    def mock_db_ctx():
        yield db_session
        
    with patch("workers.simulation.tasks.get_db_context", side_effect=mock_db_ctx):
        with patch("paho.mqtt.client.Client") as mock_mqtt:
            # Connect fails, causing retry
            mock_mqtt.return_value.connect.side_effect = Exception("MQTT broker down")
            
            run_grid_simulation.__wrapped__(str(tenant.id), str(run.id), "IEEE14", {"duration_seconds": 10})
            
            # Verify retry was called
            assert mock_retry.called
            
            # Now let's test MaxRetriesExceeded behavior by setting retries to max
            mock_req.retries = 3
            from celery.exceptions import MaxRetriesExceededError
            mock_retry.side_effect = MaxRetriesExceededError()
            
            with pytest.raises(MaxRetriesExceededError):
                run_grid_simulation.__wrapped__(str(tenant.id), str(run.id), "IEEE14", {"duration_seconds": 10})
                
            # Verify status in database set to FAILED
            db_session.refresh(run)
            assert run.status == "FAILED"
            
            # Verify dead letter queue list push
            assert r_inst.rpush.called
            dlq_args = r_inst.rpush.call_args[0]
            assert dlq_args[0] == "simulation.deadletter"
            assert "MQTT broker down" in dlq_args[1]

# Utility helper for python context manager mocking
def contextmanager_mock(func):
    from contextlib import contextmanager
    return contextmanager(func)
