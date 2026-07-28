# verify_v118.py
"""
PYPY V11.8 — Operations, Observability & Security Hardening
Standalone verification script: runs integrity checks without pytest.
"""

import os
import sys
import uuid
import json
import gzip
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "core")))
# Ensure core/services/auth resolves before root services/auth
_root = os.path.dirname(os.path.abspath(__file__))
_core = os.path.join(_root, "core")
if _core not in sys.path:
    sys.path.insert(0, _core)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import MagicMock, patch

PASS = "\033[92m✅ PASS\033[0m"
FAIL = "\033[91m❌ FAIL\033[0m"
WARN = "\033[93m⚠️  WARN\033[0m"

checks_total = 0
checks_passed = 0
checks_failed = 0


def check(label: str, condition: bool, detail: str = ""):
    global checks_total, checks_passed, checks_failed
    checks_total += 1
    if condition:
        checks_passed += 1
        print(f"  {PASS} {label}")
    else:
        checks_failed += 1
        print(f"  {FAIL} {label}" + (f" — {detail}" if detail else ""))


def section(title: str):
    print(f"\n{'═' * 60}")
    print(f"  {title}")
    print('═' * 60)


def main():
    print("=" * 60)
    print("  PYPY V11.8 PRODUCTION VERIFICATION")
    print("  Operations, Observability & Security Hardening")
    print("=" * 60)

    # ── 1. Models ──────────────────────────────────────────────────────────────
    section("[1/10] V11.8 Database Models")

    try:
        from services.auth.models import (
            JWTBlacklist, IPBlock, SecurityAuditEvent,
            AlertEvent, BackupRecord, OperationLog, SystemMetricSnapshot, Base
        )
        check("JWTBlacklist model importable", True)
        check("IPBlock model importable", True)
        check("SecurityAuditEvent model importable", True)
        check("AlertEvent model importable", True)
        check("BackupRecord model importable", True)
        check("OperationLog model importable", True)
        check("SystemMetricSnapshot model importable", True)
    except ImportError as e:
        check("V11.8 models importable", False, str(e))
        print("  Cannot continue verification without models.")
        _print_summary()
        return

    # ── 2. DB Schema ───────────────────────────────────────────────────────────
    section("[2/10] Database Schema Creation")

    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    tables = [t for t in Base.metadata.tables.keys()]
    for expected in ["jwt_blacklist", "ip_blocks", "security_audit_events", "alert_events",
                     "backup_records", "operation_logs", "system_metric_snapshots"]:
        check(f"Table '{expected}' created", expected in tables)

    # ── 3. Security Service: Brute-Force ───────────────────────────────────────
    section("[3/10] Security Service — Brute Force Protection")

    from services.auth.models import Tenant, User
    import bcrypt
    tenant = Tenant(id=uuid.uuid4(), name="Verify Tenant", subdomain=f"vt-{uuid.uuid4().hex[:5]}", plan_tier="free")
    db.add(tenant)
    db.flush()
    user = User(
        id=uuid.uuid4(), tenant_id=tenant.id,
        email=f"verify-{uuid.uuid4().hex[:6]}@test.com",
        password_hash=bcrypt.hashpw(b"pass", bcrypt.gensalt()).decode(),
        role="admin", email_verified=True, failed_login_attempts=0,
    )
    db.add(user)
    db.commit()

    from services.operations.security_service import (
        record_failed_login, reset_failed_login, is_account_locked
    )
    # Simulate 5 failed logins
    result = None
    for _ in range(5):
        result = record_failed_login(db, user.id, "1.2.3.4")
    check("Account locked after 5 failed logins", result and result["locked"] is True)
    check("Lockout timestamp set", result and result.get("lockout_until") is not None)
    check("is_account_locked returns True", is_account_locked(db, user.id) is True)
    reset_failed_login(db, user.id)
    check("reset_failed_login clears lockout", is_account_locked(db, user.id) is False)

    # ── 4. Security Service: JWT Blacklist ─────────────────────────────────────
    section("[4/10] Security Service — JWT Blacklist")

    from services.operations.security_service import (
        blacklist_token, is_token_blacklisted, purge_expired_blacklist_entries
    )
    jti_active = f"jti-active-{uuid.uuid4().hex}"
    jti_expired = f"jti-expired-{uuid.uuid4().hex}"
    blacklist_token(db, jti_active, datetime.now(timezone.utc) + timedelta(minutes=15), user.id)
    blacklist_token(db, jti_expired, datetime.now(timezone.utc) - timedelta(hours=1), user.id)

    check("Active JTI is blacklisted", is_token_blacklisted(db, jti_active) is True)
    check("Fresh JTI is not blacklisted", is_token_blacklisted(db, f"fresh-{uuid.uuid4().hex}") is False)
    deleted = purge_expired_blacklist_entries(db)
    check(f"Purged {deleted} expired JWT entries", deleted >= 1)

    # ── 5. Security Service: IP Blocking ──────────────────────────────────────
    section("[5/10] Security Service — IP Blocking")

    from services.operations.security_service import (
        block_ip, unblock_ip, is_ip_blocked, list_ip_blocks
    )
    ip_to_block = f"192.168.{uuid.uuid4().int % 255}.{uuid.uuid4().int % 255}"
    block_ip(db, ip_to_block, reason="verify_script", blocked_hours=1)
    check("IP block created successfully", is_ip_blocked(db, ip_to_block) is True)
    ip_blocks = list_ip_blocks(db)
    check("list_ip_blocks returns list", isinstance(ip_blocks, list))
    check("Blocked IP appears in list", any(b["ip_address"] == ip_to_block for b in ip_blocks))
    unblock_ip(db, ip_to_block)
    check("IP unblocked successfully", is_ip_blocked(db, ip_to_block) is False)

    # ── 6. Security Audit Trail ────────────────────────────────────────────────
    section("[6/10] Security Service — Audit Trail")

    from services.operations.security_service import (
        log_login_success, log_login_failure, get_recent_security_events
    )
    log_login_success(db, user.id, "10.0.0.1", tenant_id=tenant.id)
    log_login_failure(db, "attacker@bad.com", "9.9.9.9")
    events = get_recent_security_events(db, limit=20)
    event_types = [e["event_type"] for e in events]
    check("LOGIN_SUCCESS event recorded", "LOGIN_SUCCESS" in event_types)
    check("LOGIN_FAILURE event recorded", "LOGIN_FAILURE" in event_types)
    check("Events have ip_address field", all("ip_address" in e for e in events))

    # ── 7. Alert Evaluation Engine ─────────────────────────────────────────────
    section("[7/10] Alert Evaluation Engine")

    from services.operations.alert_service import evaluate_all_rules

    healthy_snap = {
        "system": {"cpu_percent": 10.0, "ram_percent": 20.0, "disk_percent": 30.0},
        "services": {"gateway": {"status": "online"}, "redis": {"status": "online"},
                     "mqtt": {"status": "online"}, "celery_worker": {"status": "online"}},
        "simulations": {"failed_simulations": 0, "queue_length": 0},
        "api": {"error_rate_percent": 0.0},
    }
    check("No alerts when all healthy", len(evaluate_all_rules(healthy_snap)) == 0)

    cpu_snap = {**healthy_snap, "system": {"cpu_percent": 95.0, "ram_percent": 20.0, "disk_percent": 30.0}}
    fired = evaluate_all_rules(cpu_snap)
    check("cpu_high alert fires at 95%", any(f["rule_id"] == "cpu_high" for f in fired))

    offline_snap = {**healthy_snap, "services": {"gateway": {"status": "offline"}, "redis": {"status": "online"},
                                                   "mqtt": {"status": "online"}, "celery_worker": {"status": "online"}}}
    fired_gw = evaluate_all_rules(offline_snap)
    check("gw_offline alert fires", any(f["rule_id"] == "gw_offline" for f in fired_gw))

    sim_fail_snap = {**healthy_snap, "simulations": {"failed_simulations": 3, "queue_length": 0}}
    fired_sim = evaluate_all_rules(sim_fail_snap)
    check("sim_failure alert fires", any(f["rule_id"] == "sim_failure" for f in fired_sim))

    # ── 8. Backup Engine ───────────────────────────────────────────────────────
    section("[8/10] Backup Engine")

    import tempfile
    from services.operations import backup_service

    with tempfile.TemporaryDirectory() as tmpdir:
        backup_service.BACKUP_DIR = tmpdir
        result = backup_service.run_postgres_backup()
        check("Postgres backup succeeds", result["success"] is True)
        check("Backup file created on disk", os.path.exists(result["record"]["filepath"]))
        check("Backup has valid filename", result["record"]["filename"].endswith(".sql.gz"))

        files_result = backup_service.run_files_backup(["/nonexistent_xyz"], label="test")
        check("Files backup handles missing dirs", files_result["success"] is True)

        listed = backup_service.list_backups()
        check("list_backups returns items", isinstance(listed, list))

        fname = result["record"]["filename"]
        deleted = backup_service.delete_backup(fname)
        check("Backup file deleted", deleted is True)

    # ── 9. Metrics Service ─────────────────────────────────────────────────────
    section("[9/10] Metrics Service")

    from services.operations.metrics_service import (
        collect_system_metrics, collect_service_health, collect_api_metrics
    )
    sys_m = collect_system_metrics()
    check("System metrics returns cpu_percent", "cpu_percent" in sys_m)
    check("System metrics returns ram_percent", "ram_percent" in sys_m)
    check("System metrics returns disk_percent", "disk_percent" in sys_m)
    check("CPU percent in valid range", 0 <= sys_m["cpu_percent"] <= 100)
    check("RAM percent in valid range", 0 <= sys_m["ram_percent"] <= 100)

    svc = collect_service_health()
    for service in ["gateway", "redis", "mqtt", "postgres", "celery_worker"]:
        check(f"Service '{service}' in health check", service in svc)

    api_m = collect_api_metrics({"total_requests": 100, "avg_latency_ms": 25.0,
                                  "error_rate_percent": 2.0, "p95_latency_ms": 80.0,
                                  "requests_per_min": 15, "active_websockets": 4})
    check("API metrics returns total_requests", api_m["total_requests"] == 100)

    # ── 10. File & Structure Checks ────────────────────────────────────────────
    section("[10/10] File Integrity & Structure")

    project_root = os.path.dirname(os.path.abspath(__file__))
    expected_files = [
        "core/services/operations/__init__.py",
        "core/services/operations/metrics_service.py",
        "core/services/operations/alert_service.py",
        "core/services/operations/backup_service.py",
        "core/services/operations/security_service.py",
        "core/gateway/routes/operations.py",
        "core/gateway/routes/security_hardening.py",
        "monitoring/grafana/dashboards/pypy_operations.json",
        "dashboard/src/components/OperationsCenter.tsx",
        "tests/test_v118.py",
    ]
    for f in expected_files:
        path = os.path.join(project_root, f)
        check(f"File exists: {f}", os.path.exists(path))

    # Grafana JSON valid
    grafana_path = os.path.join(project_root, "monitoring/grafana/dashboards/pypy_operations.json")
    try:
        with open(grafana_path) as fp:
            gdata = json.load(fp)
        check("Grafana JSON valid and has 8+ panels", len(gdata.get("panels", [])) >= 8)
        check("Grafana JSON has correct title", gdata.get("title") == "PYPY Grid Operations Dashboard")
    except Exception as e:
        check("Grafana JSON valid", False, str(e))

    # OperationsCenter.tsx has key sections
    tsx_path = os.path.join(project_root, "dashboard/src/components/OperationsCenter.tsx")
    try:
        tsx_content = open(tsx_path).read()
        check("OperationsCenter has Overview tab", "overview" in tsx_content)
        check("OperationsCenter has Alerts tab", "alerts" in tsx_content)
        check("OperationsCenter has Backups tab", "backups" in tsx_content)
        check("OperationsCenter has Security tab", "security" in tsx_content)
        check("OperationsCenter has DR tab", "disaster" in tsx_content.lower())
        check("OperationsCenter has GaugeMeter component", "GaugeMeter" in tsx_content)
        check("OperationsCenter has auto-refresh", "REFRESH_INTERVAL_MS" in tsx_content)
    except Exception as e:
        check("OperationsCenter.tsx readable", False, str(e))

    # ── Summary ────────────────────────────────────────────────────────────────
    db.close()
    _print_summary()


def _print_summary():
    global checks_total, checks_passed, checks_failed
    print("\n" + "=" * 60)
    print("  PYPY V11.8 VERIFICATION SUMMARY")
    print("=" * 60)
    print(f"  Total Checks : {checks_total}")
    print(f"  Passed       : \033[92m{checks_passed}\033[0m")
    print(f"  Failed       : \033[91m{checks_failed}\033[0m")
    print("=" * 60)
    if checks_failed == 0:
        print("\n  🎉 \033[92mV11.8 FULLY CERTIFIED — ALL CHECKS PASSED\033[0m")
    else:
        print(f"\n  ⚠️  \033[91m{checks_failed} check(s) require attention before certification.\033[0m")
    print()


if __name__ == "__main__":
    main()
