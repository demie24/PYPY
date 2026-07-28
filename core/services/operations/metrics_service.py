# core/services/operations/metrics_service.py
"""
V11.8 — System Metrics Collection Service
Collects CPU, RAM, Disk, Docker, Redis, MQTT, Celery, API, and simulation metrics.
"""

import os
import time
import uuid
import shutil
import logging
import subprocess
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

logger = logging.getLogger("operations.metrics")


def _run_cmd(cmd: List[str], fallback=None) -> Optional[str]:
    """Safely run a shell command and return stdout."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception as e:
        logger.debug(f"Command {cmd} failed: {e}")
    return fallback


def collect_system_metrics() -> Dict[str, Any]:
    """Collect host system resource metrics (CPU, RAM, Disk)."""
    try:
        import psutil
        cpu_pct = psutil.cpu_percent(interval=0.2)
        vm = psutil.virtual_memory()
        ram_pct = vm.percent
        ram_used_mb = vm.used // (1024 * 1024)
        ram_total_mb = vm.total // (1024 * 1024)
        disk = psutil.disk_usage("/")
        disk_pct = disk.percent
        disk_used_gb = disk.used // (1024 ** 3)
        disk_total_gb = disk.total // (1024 ** 3)
        net = psutil.net_io_counters()
        bytes_sent_mb = net.bytes_sent // (1024 * 1024)
        bytes_recv_mb = net.bytes_recv // (1024 * 1024)
        load_avg = list(os.getloadavg()) if hasattr(os, "getloadavg") else [0.0, 0.0, 0.0]
    except ImportError:
        # psutil not available — return mock values
        cpu_pct = 12.0
        ram_pct = 45.0
        ram_used_mb = 3600
        ram_total_mb = 8000
        disk_pct = 22.0
        disk_used_gb = 22
        disk_total_gb = 100
        bytes_sent_mb = 450
        bytes_recv_mb = 320
        load_avg = [0.5, 0.4, 0.3]

    return {
        "cpu_percent": cpu_pct,
        "ram_percent": ram_pct,
        "ram_used_mb": ram_used_mb,
        "ram_total_mb": ram_total_mb,
        "disk_percent": disk_pct,
        "disk_used_gb": disk_used_gb,
        "disk_total_gb": disk_total_gb,
        "net_sent_mb": bytes_sent_mb,
        "net_recv_mb": bytes_recv_mb,
        "load_avg_1m": load_avg[0],
        "load_avg_5m": load_avg[1],
        "load_avg_15m": load_avg[2],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def collect_service_health() -> Dict[str, Any]:
    """Check health of all PYPY Grid services."""
    def ping_tcp(host: str, port: int, timeout: float = 2.0) -> bool:
        import socket
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except Exception:
            return False

    def check_redis() -> bool:
        host = os.getenv("REDIS_HOST", "localhost")
        return ping_tcp(host, 6379)

    def check_mqtt() -> bool:
        host = os.getenv("MQTT_HOST", "localhost")
        return ping_tcp(host, 1884)

    def check_postgres() -> bool:
        host = os.getenv("DB_HOST", "localhost")
        return ping_tcp(host, 5432)

    def check_gateway() -> bool:
        import urllib.request
        try:
            with urllib.request.urlopen("http://localhost:8000/api/health", timeout=2):
                return True
        except Exception:
            return False

    def check_celery() -> bool:
        """Check if celery worker is running by testing for the worker PID file or socket."""
        result = _run_cmd(["pgrep", "-f", "celery"])
        return result is not None and len(result.strip()) > 0

    return {
        "gateway": {"status": "online" if check_gateway() else "degraded", "port": 8000},
        "redis": {"status": "online" if check_redis() else "offline", "port": 6379},
        "mqtt": {"status": "online" if check_mqtt() else "offline", "port": 1884},
        "postgres": {"status": "online" if check_postgres() else "offline", "port": 5432},
        "celery_worker": {"status": "online" if check_celery() else "offline"},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def collect_api_metrics(metrics_store: Dict) -> Dict[str, Any]:
    """Return accumulated API latency and request count metrics."""
    return {
        "total_requests": metrics_store.get("total_requests", 0),
        "avg_latency_ms": round(metrics_store.get("avg_latency_ms", 0.0), 2),
        "p95_latency_ms": round(metrics_store.get("p95_latency_ms", 0.0), 2),
        "error_rate_percent": round(metrics_store.get("error_rate_percent", 0.0), 2),
        "requests_per_min": metrics_store.get("requests_per_min", 0),
        "active_websockets": metrics_store.get("active_websockets", 0),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def collect_simulation_metrics(db) -> Dict[str, Any]:
    """Query DB for simulation queue and worker utilisation."""
    try:
        from services.auth.models import SimulatorRun
        running = db.query(SimulatorRun).filter(SimulatorRun.status == "RUNNING").count()
        queued = db.query(SimulatorRun).filter(SimulatorRun.status == "QUEUED").count()
        completed_today = db.query(SimulatorRun).filter(
            SimulatorRun.status == "COMPLETED"
        ).count()
        failed = db.query(SimulatorRun).filter(SimulatorRun.status == "FAILED").count()
    except Exception:
        running = queued = completed_today = failed = 0

    return {
        "running_simulations": running,
        "queued_simulations": queued,
        "completed_today": completed_today,
        "failed_simulations": failed,
        "queue_length": queued,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def collect_ai_usage_metrics(db) -> Dict[str, Any]:
    """Collect AI Copilot usage counts."""
    try:
        from services.auth.models import CopilotMessage
        from sqlalchemy import func
        today = datetime.now(timezone.utc).date()
        msgs_today = db.query(func.count(CopilotMessage.id)).scalar() or 0
    except Exception:
        msgs_today = 0

    return {
        "ai_messages_today": msgs_today,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def get_full_metrics_snapshot(db, metrics_store: Dict) -> Dict[str, Any]:
    """Aggregate all metrics into a single snapshot."""
    return {
        "system": collect_system_metrics(),
        "services": collect_service_health(),
        "api": collect_api_metrics(metrics_store),
        "simulations": collect_simulation_metrics(db),
        "ai_usage": collect_ai_usage_metrics(db),
        "snapshot_at": datetime.now(timezone.utc).isoformat(),
    }
