# core/gateway/routes/operations.py
"""
V11.8 — Operations Center API Routes
Exposes endpoints for:
- System metrics and snapshots
- Service health
- Alert management (list, acknowledge)
- Log viewer (aggregated logs)
- Backup management (list, run, delete, restore)
- Grafana metrics scrape endpoint
"""

import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from services.auth.session import get_db
from services.auth.auth_service import get_current_user_claims
from services.operations.metrics_service import (
    collect_system_metrics,
    collect_service_health,
    collect_simulation_metrics,
    collect_ai_usage_metrics,
    get_full_metrics_snapshot,
)
from services.operations.alert_service import evaluate_all_rules, dispatch_alerts
from services.operations.backup_service import (
    run_postgres_backup,
    run_full_backup,
    list_backups,
    delete_backup,
    restore_postgres_backup,
)

router = APIRouter(prefix="/operations", tags=["operations"])
logger = logging.getLogger("gateway.operations")

# Shared in-memory API metrics accumulator (updated by middleware)
_api_metrics: dict = {
    "total_requests": 0,
    "avg_latency_ms": 0.0,
    "p95_latency_ms": 0.0,
    "error_rate_percent": 0.0,
    "requests_per_min": 0,
    "active_websockets": 0,
    "_latency_samples": [],
}


def get_api_metrics_store() -> dict:
    return _api_metrics


def update_api_request_metric(latency_ms: float, is_error: bool = False):
    """Called from middleware to track per-request metrics."""
    _api_metrics["total_requests"] += 1
    samples = _api_metrics["_latency_samples"]
    samples.append(latency_ms)
    if len(samples) > 1000:
        _api_metrics["_latency_samples"] = samples[-500:]
        samples = _api_metrics["_latency_samples"]

    _api_metrics["avg_latency_ms"] = sum(samples) / len(samples)
    if len(samples) >= 20:
        sorted_samples = sorted(samples)
        p95_idx = int(len(sorted_samples) * 0.95)
        _api_metrics["p95_latency_ms"] = sorted_samples[p95_idx]

    if is_error:
        total = _api_metrics["total_requests"]
        current_errors = _api_metrics["error_rate_percent"] * total / 100
        _api_metrics["error_rate_percent"] = ((current_errors + 1) / total) * 100


# ─── System Metrics ──────────────────────────────────────────────────────────

@router.get("/metrics/system")
def get_system_metrics(claims: dict = Depends(get_current_user_claims)):
    """Get current CPU, RAM, Disk metrics."""
    return collect_system_metrics()


@router.get("/metrics/services")
def get_service_health(claims: dict = Depends(get_current_user_claims)):
    """Get health status of all PYPY Grid services."""
    return collect_service_health()


@router.get("/metrics/snapshot")
def get_metrics_snapshot(
    claims: dict = Depends(get_current_user_claims),
    db: Session = Depends(get_db),
):
    """Get a full aggregated metrics snapshot."""
    snapshot = get_full_metrics_snapshot(db, _api_metrics)
    return snapshot


@router.get("/metrics/history")
def get_metrics_history(
    limit: int = Query(default=60, le=500),
    claims: dict = Depends(get_current_user_claims),
    db: Session = Depends(get_db),
):
    """Retrieve historical metric snapshots from the DB."""
    try:
        from services.auth.models import SystemMetricSnapshot
        rows = (
            db.query(SystemMetricSnapshot)
            .order_by(SystemMetricSnapshot.captured_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "cpu_percent": float(r.cpu_percent or 0),
                "ram_percent": float(r.ram_percent or 0),
                "disk_percent": float(r.disk_percent or 0),
                "active_simulations": r.active_simulations or 0,
                "queue_length": r.queue_length or 0,
                "avg_latency_ms": float(r.avg_latency_ms or 0),
                "error_rate_percent": float(r.error_rate_percent or 0),
                "captured_at": r.captured_at.isoformat() if r.captured_at else None,
            }
            for r in reversed(rows)
        ]
    except Exception as e:
        logger.error(f"Failed to fetch metric history: {e}")
        return []


@router.post("/metrics/snapshot/save")
def save_metric_snapshot(
    claims: dict = Depends(get_current_user_claims),
    db: Session = Depends(get_db),
):
    """Capture and persist a system metric snapshot to the DB."""
    try:
        from services.auth.models import SystemMetricSnapshot
        sys_metrics = collect_system_metrics()
        sim_metrics = collect_simulation_metrics(db)
        snap = SystemMetricSnapshot(
            cpu_percent=sys_metrics["cpu_percent"],
            ram_percent=sys_metrics["ram_percent"],
            disk_percent=sys_metrics["disk_percent"],
            ram_used_mb=sys_metrics["ram_used_mb"],
            active_simulations=sim_metrics["running_simulations"],
            queue_length=sim_metrics["queue_length"],
            active_websockets=_api_metrics.get("active_websockets", 0),
            api_requests_per_min=_api_metrics.get("requests_per_min", 0),
            avg_latency_ms=_api_metrics.get("avg_latency_ms", 0.0),
            error_rate_percent=_api_metrics.get("error_rate_percent", 0.0),
            captured_at=datetime.now(timezone.utc),
        )
        db.add(snap)
        db.commit()
        return {"saved": True, "captured_at": snap.captured_at.isoformat()}
    except Exception as e:
        logger.error(f"Snapshot save failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─── Prometheus-compatible scrape endpoint ────────────────────────────────────

@router.get("/metrics/prometheus", response_class=PlainTextResponse)
def prometheus_metrics(db: Session = Depends(get_db)):
    """
    Expose metrics in Prometheus text format for Grafana scraping.
    No authentication required (scraped internally by Prometheus/Grafana).
    """
    sys_m = collect_system_metrics()
    sim_m = collect_simulation_metrics(db)
    ai_m = collect_ai_usage_metrics(db)

    lines = [
        "# HELP pypy_cpu_percent CPU usage percentage",
        "# TYPE pypy_cpu_percent gauge",
        f"pypy_cpu_percent {sys_m['cpu_percent']}",
        "# HELP pypy_ram_percent RAM usage percentage",
        "# TYPE pypy_ram_percent gauge",
        f"pypy_ram_percent {sys_m['ram_percent']}",
        "# HELP pypy_disk_percent Disk usage percentage",
        "# TYPE pypy_disk_percent gauge",
        f"pypy_disk_percent {sys_m['disk_percent']}",
        "# HELP pypy_running_simulations Active running simulations",
        "# TYPE pypy_running_simulations gauge",
        f"pypy_running_simulations {sim_m['running_simulations']}",
        "# HELP pypy_queued_simulations Queued simulations",
        "# TYPE pypy_queued_simulations gauge",
        f"pypy_queued_simulations {sim_m['queued_simulations']}",
        "# HELP pypy_failed_simulations Failed simulations",
        "# TYPE pypy_failed_simulations gauge",
        f"pypy_failed_simulations {sim_m['failed_simulations']}",
        "# HELP pypy_api_total_requests Total API requests",
        "# TYPE pypy_api_total_requests counter",
        f"pypy_api_total_requests {_api_metrics['total_requests']}",
        "# HELP pypy_api_avg_latency_ms Average API latency in ms",
        "# TYPE pypy_api_avg_latency_ms gauge",
        f"pypy_api_avg_latency_ms {_api_metrics['avg_latency_ms']:.2f}",
        "# HELP pypy_api_error_rate_percent API error rate percent",
        "# TYPE pypy_api_error_rate_percent gauge",
        f"pypy_api_error_rate_percent {_api_metrics['error_rate_percent']:.2f}",
        "# HELP pypy_ai_messages_today Total AI Copilot messages today",
        "# TYPE pypy_ai_messages_today counter",
        f"pypy_ai_messages_today {ai_m['ai_messages_today']}",
    ]
    return "\n".join(lines) + "\n"


# ─── Alert Management ────────────────────────────────────────────────────────

@router.get("/alerts")
def list_alerts(
    limit: int = Query(default=50, le=200),
    severity: Optional[str] = None,
    acknowledged: Optional[bool] = None,
    claims: dict = Depends(get_current_user_claims),
    db: Session = Depends(get_db),
):
    """List recent alert events with optional filters."""
    try:
        from services.auth.models import AlertEvent
        q = db.query(AlertEvent).order_by(AlertEvent.fired_at.desc())
        if severity:
            q = q.filter(AlertEvent.severity == severity)
        if acknowledged is not None:
            q = q.filter(AlertEvent.acknowledged == acknowledged)
        events = q.limit(limit).all()
        return [
            {
                "id": str(e.id),
                "rule_id": e.rule_id,
                "rule_name": e.rule_name,
                "severity": e.severity,
                "message": e.message,
                "fired_at": e.fired_at.isoformat() if e.fired_at else None,
                "acknowledged": e.acknowledged,
            }
            for e in events
        ]
    except Exception as e:
        logger.error(f"Failed to list alerts: {e}")
        return []


@router.post("/alerts/{alert_id}/acknowledge")
def acknowledge_alert(
    alert_id: str,
    claims: dict = Depends(get_current_user_claims),
    db: Session = Depends(get_db),
):
    """Acknowledge a specific alert event."""
    try:
        from services.auth.models import AlertEvent
        event = db.query(AlertEvent).filter(AlertEvent.id == uuid.UUID(alert_id)).first()
        if not event:
            raise HTTPException(status_code=404, detail="Alert not found.")
        event.acknowledged = True
        event.acknowledged_at = datetime.now(timezone.utc)
        db.commit()
        return {"acknowledged": True, "alert_id": alert_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/alerts/evaluate")
def run_alert_evaluation(
    claims: dict = Depends(get_current_user_claims),
    db: Session = Depends(get_db),
):
    """Manually trigger alert evaluation against the current metrics snapshot."""
    snapshot = get_full_metrics_snapshot(db, _api_metrics)
    fired = evaluate_all_rules(snapshot, db=db)
    if fired:
        dispatch_alerts(fired)
    return {"fired_count": len(fired), "alerts": fired}


# ─── Log Viewer ──────────────────────────────────────────────────────────────

class LogEntrySchema(BaseModel):
    service: str
    level: str
    message: str
    extra: Optional[dict] = None


@router.get("/logs")
def get_operation_logs(
    service: Optional[str] = None,
    level: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(default=100, le=500),
    claims: dict = Depends(get_current_user_claims),
    db: Session = Depends(get_db),
):
    """Fetch aggregated operation logs with filtering."""
    try:
        from services.auth.models import OperationLog
        q = db.query(OperationLog).order_by(OperationLog.logged_at.desc())
        if service:
            q = q.filter(OperationLog.service == service)
        if level:
            q = q.filter(OperationLog.level == level.upper())
        if search:
            q = q.filter(OperationLog.message.ilike(f"%{search}%"))
        logs = q.limit(limit).all()
        return [
            {
                "id": str(l.id),
                "service": l.service,
                "level": l.level,
                "message": l.message,
                "extra": l.extra,
                "logged_at": l.logged_at.isoformat() if l.logged_at else None,
            }
            for l in logs
        ]
    except Exception as e:
        logger.error(f"Failed to fetch logs: {e}")
        return []


@router.post("/logs")
def write_operation_log(
    payload: LogEntrySchema,
    claims: dict = Depends(get_current_user_claims),
    db: Session = Depends(get_db),
):
    """Write a log entry to the centralized operation log store."""
    try:
        from services.auth.models import OperationLog
        entry = OperationLog(
            service=payload.service,
            level=payload.level.upper(),
            message=payload.message,
            extra=payload.extra,
            logged_at=datetime.now(timezone.utc),
        )
        db.add(entry)
        db.commit()
        return {"logged": True, "id": str(entry.id)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Backup Management ───────────────────────────────────────────────────────

@router.get("/backups")
def get_backups(claims: dict = Depends(get_current_user_claims)):
    """List all backup files."""
    return list_backups()


@router.post("/backups/run/postgres")
def trigger_postgres_backup(
    claims: dict = Depends(get_current_user_claims),
    db: Session = Depends(get_db),
):
    """Trigger an on-demand PostgreSQL backup."""
    result = run_postgres_backup(db=db)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Backup failed"))
    return result


@router.post("/backups/run/full")
def trigger_full_backup(
    claims: dict = Depends(get_current_user_claims),
    db: Session = Depends(get_db),
):
    """Trigger a full backup (Postgres + reports + configs)."""
    result = run_full_backup(db=db)
    return result


@router.delete("/backups/{filename}")
def remove_backup(
    filename: str,
    claims: dict = Depends(get_current_user_claims),
):
    """Delete a specific backup file."""
    if ".." in filename or "/" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename.")
    success = delete_backup(filename)
    if not success:
        raise HTTPException(status_code=404, detail="Backup file not found.")
    return {"deleted": True, "filename": filename}


@router.post("/backups/{filename}/restore")
def restore_backup(
    filename: str,
    claims: dict = Depends(get_current_user_claims),
):
    """Restore a specific backup file (PostgreSQL only for now)."""
    if ".." in filename or "/" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename.")
    result = restore_postgres_backup(filename)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Restore failed"))
    return result


# ─── Disaster Recovery ───────────────────────────────────────────────────────

@router.get("/disaster-recovery/status")
def get_disaster_recovery_status(
    claims: dict = Depends(get_current_user_claims),
    db: Session = Depends(get_db),
):
    """
    Report service health and provide restart recommendations for failed services.
    """
    service_health = collect_service_health()
    recommendations = []

    for service_name, info in service_health.items():
        if service_name == "timestamp":
            continue
        s_status = info.get("status", "unknown") if isinstance(info, dict) else "unknown"
        if s_status in ("offline", "degraded"):
            cmd_map = {
                "gateway": "docker compose restart gateway",
                "redis": "docker compose restart redis",
                "mqtt": "docker compose restart mqtt",
                "postgres": "docker compose restart postgres",
                "celery_worker": "docker compose restart celery_worker",
            }
            recommendations.append({
                "service": service_name,
                "status": s_status,
                "recommendation": f"Restart {service_name} service",
                "command": cmd_map.get(service_name, f"docker compose restart {service_name}"),
            })

    return {
        "services": service_health,
        "recommendations": recommendations,
        "all_healthy": len(recommendations) == 0,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }
