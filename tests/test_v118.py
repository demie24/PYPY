# tests/test_v118.py
"""
PYPY V11.8 — Operations, Observability & Security Hardening
Pytest test suite validating:
  - Security service: brute-force, JWT blacklist, IP blocking, audit trail
  - Alert service: rule evaluation engine, threshold logic
  - Backup service: on-demand backup creation
  - Metrics service: system metric collection structure
  - Operations models: schema creation
  - API route imports: operations + security_hardening
"""

import os
import sys
import uuid
import time
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../core")))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# ─── Test Database Setup ──────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def db():
    """In-memory SQLite DB with all V11.8 models created."""
    from services.auth.models import Base
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture(scope="module")
def tenant_and_user(db):
    """Create a minimal tenant and user for security tests."""
    from services.auth.models import Tenant, User
    import bcrypt
    tenant = Tenant(
        id=uuid.uuid4(),
        name="Test Ops Tenant",
        subdomain=f"ops-{uuid.uuid4().hex[:6]}",
        plan_tier="academic_premium",
    )
    db.add(tenant)
    db.flush()

    user = User(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        email=f"ops-{uuid.uuid4().hex[:6]}@test.com",
        password_hash=bcrypt.hashpw(b"testpass123", bcrypt.gensalt()).decode(),
        role="admin",
        failed_login_attempts=0,
        email_verified=True,
    )
    db.add(user)
    db.commit()
    return tenant, user


# ─── 1. Security Service: Brute-Force ────────────────────────────────────────

class TestBruteForceProtection:
    def test_failed_login_increments_counter(self, db, tenant_and_user):
        """Recording a failed login must increment failed_login_attempts."""
        from services.operations.security_service import record_failed_login
        tenant, user = tenant_and_user
        user.failed_login_attempts = 0
        db.commit()
        result = record_failed_login(db, user.id, "10.0.0.1")
        assert result["attempts"] == 1
        assert result["locked"] is False

    def test_account_locked_after_5_failures(self, db, tenant_and_user):
        """Account must be locked after MAX_FAILED_ATTEMPTS (5) consecutive failures."""
        from services.operations.security_service import record_failed_login
        tenant, user = tenant_and_user
        user.failed_login_attempts = 0
        db.commit()
        result = None
        for _ in range(5):
            result = record_failed_login(db, user.id, "10.0.0.2")
        assert result["locked"] is True
        assert result["lockout_until"] is not None

    def test_is_account_locked_returns_true(self, db, tenant_and_user):
        """is_account_locked should return True when lockout_until is in the future."""
        from services.operations.security_service import is_account_locked
        from services.auth.models import User
        tenant, user = tenant_and_user
        user.lockout_until = datetime.now(timezone.utc) + timedelta(minutes=15)
        db.commit()
        assert is_account_locked(db, user.id) is True

    def test_reset_failed_login_clears_lockout(self, db, tenant_and_user):
        """reset_failed_login should clear the lockout."""
        from services.operations.security_service import reset_failed_login, is_account_locked
        tenant, user = tenant_and_user
        reset_failed_login(db, user.id)
        assert is_account_locked(db, user.id) is False


# ─── 2. Security Service: JWT Blacklist ──────────────────────────────────────

class TestJWTBlacklist:
    def test_blacklist_token_and_check(self, db, tenant_and_user):
        """Blacklisting a JTI should make is_token_blacklisted return True."""
        from services.operations.security_service import blacklist_token, is_token_blacklisted
        tenant, user = tenant_and_user
        jti = f"jti-{uuid.uuid4().hex}"
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)
        blacklist_token(db, jti, expires_at, user_id=user.id, reason="logout")
        assert is_token_blacklisted(db, jti) is True

    def test_non_blacklisted_token_passes(self, db):
        """A JTI not in the blacklist should return False."""
        from services.operations.security_service import is_token_blacklisted
        assert is_token_blacklisted(db, f"fresh-jti-{uuid.uuid4().hex}") is False

    def test_purge_expired_entries(self, db, tenant_and_user):
        """Purging expired entries must remove past-expiry JTIs."""
        from services.operations.security_service import blacklist_token, purge_expired_blacklist_entries
        tenant, user = tenant_and_user
        jti = f"expired-{uuid.uuid4().hex}"
        expires_at = datetime.now(timezone.utc) - timedelta(hours=1)  # Already expired
        blacklist_token(db, jti, expires_at, user_id=user.id)
        deleted = purge_expired_blacklist_entries(db)
        assert deleted >= 1


# ─── 3. Security Service: IP Blocking ────────────────────────────────────────

class TestIPBlocking:
    def test_block_and_check_ip(self, db):
        """Blocking an IP must make is_ip_blocked return True."""
        from services.operations.security_service import block_ip, is_ip_blocked
        ip = f"192.168.{uuid.uuid4().int % 255}.{uuid.uuid4().int % 255}"
        block_ip(db, ip, reason="test_block", blocked_hours=24)
        assert is_ip_blocked(db, ip) is True

    def test_unblock_ip(self, db):
        """Unblocking an IP must make is_ip_blocked return False."""
        from services.operations.security_service import block_ip, unblock_ip, is_ip_blocked
        ip = f"10.9.{uuid.uuid4().int % 255}.{uuid.uuid4().int % 255}"
        block_ip(db, ip, reason="test_unblock", blocked_hours=24)
        unblock_ip(db, ip)
        assert is_ip_blocked(db, ip) is False

    def test_list_ip_blocks_returns_list(self, db):
        """list_ip_blocks should return a list of active blocks."""
        from services.operations.security_service import list_ip_blocks
        blocks = list_ip_blocks(db)
        assert isinstance(blocks, list)


# ─── 4. Security Service: Audit Trail ────────────────────────────────────────

class TestSecurityAuditTrail:
    def test_login_success_logged(self, db, tenant_and_user):
        """log_login_success must persist a SecurityAuditEvent of LOGIN_SUCCESS."""
        from services.operations.security_service import log_login_success, get_recent_security_events
        tenant, user = tenant_and_user
        log_login_success(db, user.id, "192.168.1.1", tenant_id=tenant.id)
        events = get_recent_security_events(db, limit=10)
        types = [e["event_type"] for e in events]
        assert "LOGIN_SUCCESS" in types

    def test_login_failure_logged(self, db):
        """log_login_failure must persist a LOGIN_FAILURE event."""
        from services.operations.security_service import log_login_failure, get_recent_security_events
        log_login_failure(db, "attacker@evil.com", "1.2.3.4")
        events = get_recent_security_events(db, limit=10)
        types = [e["event_type"] for e in events]
        assert "LOGIN_FAILURE" in types


# ─── 5. Alert Service: Rule Evaluation ───────────────────────────────────────

class TestAlertEvaluation:
    def _make_snapshot(self, cpu=10.0, ram=10.0, disk=10.0, gateway="online", redis="online",
                       mqtt="online", worker="online", failed_sims=0, queue=0, error_rate=0.0):
        return {
            "system": {"cpu_percent": cpu, "ram_percent": ram, "disk_percent": disk},
            "services": {
                "gateway": {"status": gateway},
                "redis": {"status": redis},
                "mqtt": {"status": mqtt},
                "celery_worker": {"status": worker},
            },
            "simulations": {"failed_simulations": failed_sims, "queue_length": queue},
            "api": {"error_rate_percent": error_rate},
        }

    def test_no_alerts_when_all_healthy(self):
        """No rules should fire when all metrics are below thresholds."""
        from services.operations.alert_service import evaluate_all_rules
        snapshot = self._make_snapshot()
        fired = evaluate_all_rules(snapshot)
        assert len(fired) == 0

    def test_cpu_high_alert_fires(self):
        """CPU High rule must fire when cpu_percent > 90."""
        from services.operations.alert_service import evaluate_all_rules
        snapshot = self._make_snapshot(cpu=95.0)
        fired = evaluate_all_rules(snapshot)
        rule_ids = [f["rule_id"] for f in fired]
        assert "cpu_high" in rule_ids

    def test_ram_high_alert_fires(self):
        """RAM High rule must fire when ram_percent > 90."""
        from services.operations.alert_service import evaluate_all_rules
        snapshot = self._make_snapshot(ram=92.0)
        fired = evaluate_all_rules(snapshot)
        rule_ids = [f["rule_id"] for f in fired]
        assert "ram_high" in rule_ids

    def test_gateway_offline_alert_fires(self):
        """Gateway Offline rule must fire when gateway status is not 'online'."""
        from services.operations.alert_service import evaluate_all_rules
        snapshot = self._make_snapshot(gateway="offline")
        fired = evaluate_all_rules(snapshot)
        rule_ids = [f["rule_id"] for f in fired]
        assert "gw_offline" in rule_ids

    def test_redis_offline_alert_fires(self):
        """Redis Offline rule must fire when redis status is not 'online'."""
        from services.operations.alert_service import evaluate_all_rules
        snapshot = self._make_snapshot(redis="offline")
        fired = evaluate_all_rules(snapshot)
        rule_ids = [f["rule_id"] for f in fired]
        assert "redis_offline" in rule_ids

    def test_sim_failure_alert_fires(self):
        """Simulation Failure rule must fire when failed_simulations >= 1."""
        from services.operations.alert_service import evaluate_all_rules
        snapshot = self._make_snapshot(failed_sims=2)
        fired = evaluate_all_rules(snapshot)
        rule_ids = [f["rule_id"] for f in fired]
        assert "sim_failure" in rule_ids

    def test_all_critical_alerts_fire_simultaneously(self):
        """Multiple thresholds breached at once must produce multiple alerts."""
        from services.operations.alert_service import evaluate_all_rules
        snapshot = self._make_snapshot(cpu=95.0, ram=95.0, gateway="offline")
        fired = evaluate_all_rules(snapshot)
        assert len(fired) >= 3

    def test_alert_has_required_fields(self):
        """Every fired alert must contain id, rule_id, severity, message, fired_at."""
        from services.operations.alert_service import evaluate_all_rules
        snapshot = self._make_snapshot(cpu=95.0)
        fired = evaluate_all_rules(snapshot)
        assert len(fired) > 0
        for alert in fired:
            assert "id" in alert
            assert "rule_id" in alert
            assert "severity" in alert
            assert "message" in alert
            assert "fired_at" in alert


# ─── 6. Backup Service ───────────────────────────────────────────────────────

class TestBackupService:
    def test_postgres_backup_creates_file(self, tmp_path, monkeypatch):
        """run_postgres_backup must create a .sql.gz file even without pg_dump."""
        monkeypatch.setenv("BACKUP_DIR", str(tmp_path))
        from services.operations import backup_service
        backup_service.BACKUP_DIR = str(tmp_path)

        result = backup_service.run_postgres_backup()
        assert result["success"] is True
        assert os.path.exists(result["record"]["filepath"])

    def test_files_backup_creates_archive(self, tmp_path, monkeypatch):
        """run_files_backup must create an archive even for empty/missing dirs."""
        monkeypatch.setenv("BACKUP_DIR", str(tmp_path))
        from services.operations import backup_service
        backup_service.BACKUP_DIR = str(tmp_path)

        result = backup_service.run_files_backup(["/nonexistent_dir_xyz"], label="test")
        assert result["success"] is True

    def test_list_backups_returns_list(self, tmp_path, monkeypatch):
        """list_backups must return a list."""
        monkeypatch.setenv("BACKUP_DIR", str(tmp_path))
        from services.operations import backup_service
        backup_service.BACKUP_DIR = str(tmp_path)
        result = backup_service.list_backups()
        assert isinstance(result, list)

    def test_delete_backup_removes_file(self, tmp_path, monkeypatch):
        """delete_backup must remove the specified file."""
        monkeypatch.setenv("BACKUP_DIR", str(tmp_path))
        from services.operations import backup_service
        backup_service.BACKUP_DIR = str(tmp_path)

        # Create a file backup first
        res = backup_service.run_postgres_backup()
        fname = res["record"]["filename"]
        assert backup_service.delete_backup(fname) is True
        assert not os.path.exists(res["record"]["filepath"])


# ─── 7. Metrics Service ──────────────────────────────────────────────────────

class TestMetricsService:
    def test_system_metrics_has_required_keys(self):
        """collect_system_metrics must return a dict with cpu, ram, disk keys."""
        from services.operations.metrics_service import collect_system_metrics
        m = collect_system_metrics()
        assert "cpu_percent" in m
        assert "ram_percent" in m
        assert "disk_percent" in m
        assert "timestamp" in m
        assert 0 <= m["cpu_percent"] <= 100
        assert 0 <= m["ram_percent"] <= 100
        assert 0 <= m["disk_percent"] <= 100

    def test_service_health_has_required_services(self):
        """collect_service_health must return entries for all core services."""
        from services.operations.metrics_service import collect_service_health
        h = collect_service_health()
        for svc in ("gateway", "redis", "mqtt", "postgres", "celery_worker"):
            assert svc in h

    def test_api_metrics_structure(self):
        """collect_api_metrics must return total_requests, avg_latency_ms, error_rate."""
        from services.operations.metrics_service import collect_api_metrics
        m = collect_api_metrics({"total_requests": 42, "avg_latency_ms": 12.5, "error_rate_percent": 1.0, "requests_per_min": 10, "active_websockets": 2, "p95_latency_ms": 30.0})
        assert m["total_requests"] == 42
        assert m["avg_latency_ms"] == 12.5
        assert m["error_rate_percent"] == 1.0


# ─── 8. DB Models Exist ──────────────────────────────────────────────────────

class TestV118Models:
    def test_all_v118_models_importable(self):
        """All V11.8 models must be importable from services.auth.models."""
        from services.auth.models import (
            JWTBlacklist,
            IPBlock,
            SecurityAuditEvent,
            AlertEvent,
            BackupRecord,
            OperationLog,
            SystemMetricSnapshot,
        )
        for cls in [JWTBlacklist, IPBlock, SecurityAuditEvent, AlertEvent, BackupRecord, OperationLog, SystemMetricSnapshot]:
            assert hasattr(cls, "__tablename__")

    def test_operation_log_insert(self, db):
        """OperationLog must persist and retrieve correctly."""
        from services.auth.models import OperationLog
        entry = OperationLog(
            service="gateway",
            level="INFO",
            message="V11.8 test log entry",
            extra={"context": "pytest"},
        )
        db.add(entry)
        db.commit()
        fetched = db.query(OperationLog).filter(OperationLog.message == "V11.8 test log entry").first()
        assert fetched is not None
        assert fetched.service == "gateway"

    def test_alert_event_insert(self, db):
        """AlertEvent must persist rule_id, severity, and fired_at."""
        from services.auth.models import AlertEvent
        event = AlertEvent(
            rule_id="cpu_high",
            rule_name="CPU High",
            severity="critical",
            message="CPU exceeded 90%",
        )
        db.add(event)
        db.commit()
        fetched = db.query(AlertEvent).filter(AlertEvent.rule_id == "cpu_high").first()
        assert fetched is not None
        assert fetched.severity == "critical"

    def test_system_metric_snapshot_insert(self, db):
        """SystemMetricSnapshot must persist and retrieve numeric fields."""
        from services.auth.models import SystemMetricSnapshot
        snap = SystemMetricSnapshot(
            cpu_percent=55.5,
            ram_percent=70.2,
            disk_percent=30.0,
            active_simulations=3,
            queue_length=2,
        )
        db.add(snap)
        db.commit()
        fetched = db.query(SystemMetricSnapshot).first()
        assert fetched is not None
        assert float(fetched.cpu_percent) == pytest.approx(55.5, abs=0.01)


# ─── 9. Route Imports ────────────────────────────────────────────────────────

class TestRouteImports:
    def test_operations_router_importable(self):
        """operations.py router must import without errors."""
        # Uses a minimal mock to avoid DB dependency at import time
        with patch("gateway.routes.operations.get_db"), \
             patch("gateway.routes.operations.get_current_user_claims"):
            from gateway.routes.operations import router
            assert router.prefix == "/operations"

    def test_security_router_importable(self):
        """security_hardening.py router must import without errors."""
        with patch("gateway.routes.security_hardening.get_db"), \
             patch("gateway.routes.security_hardening.get_current_user_claims"):
            from gateway.routes.security_hardening import router
            assert router.prefix == "/security"


# ─── 10. Grafana Dashboard JSON ──────────────────────────────────────────────

class TestGrafanaDashboard:
    def test_grafana_json_exists_and_valid(self):
        """Grafana dashboard JSON file must exist and parse correctly."""
        import json
        path = os.path.join(
            os.path.dirname(__file__), "../monitoring/grafana/dashboards/pypy_operations.json"
        )
        assert os.path.exists(path), "Grafana dashboard JSON not found"
        with open(path) as f:
            data = json.load(f)
        assert data["title"] == "PYPY Grid Operations Dashboard"
        assert len(data["panels"]) >= 8
