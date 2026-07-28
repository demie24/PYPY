# core/workers/health/worker_monitor.py

import os
import time
import json
import logging
import socket
import threading
from datetime import datetime, timezone
import psutil
import redis

logger = logging.getLogger("workers.health.monitor")

# Global tracker for active task count
_active_tasks_count = 0
_lock = threading.Lock()

def increment_active_tasks():
    global _active_tasks_count
    with _lock:
        _active_tasks_count += 1

def decrement_active_tasks():
    global _active_tasks_count
    with _lock:
        _active_tasks_count = max(0, _active_tasks_count - 1)

def get_active_tasks_count() -> int:
    global _active_tasks_count
    with _lock:
        return _active_tasks_count

def _heartbeat_loop(redis_url: str):
    logger.info("Worker status heartbeat loop started.")
    r = redis.from_url(redis_url)
    worker_id = f"worker-{socket.gethostname()}-{os.getpid()}"
    
    while True:
        try:
            cpu = psutil.cpu_percent(interval=None)
            mem = psutil.virtual_memory().percent
            active = get_active_tasks_count()
            status = "BUSY" if active > 0 else "ONLINE"
            
            payload = {
                "worker_id": worker_id,
                "last_heartbeat": datetime.now(timezone.utc).isoformat(),
                "active_tasks": active,
                "cpu_usage": cpu,
                "memory_usage": mem,
                "status": status
            }
            # Set to Redis hash
            r.hset("pypy:worker:status", worker_id, json.dumps(payload))
            # Optional expiration (e.g. keep keys alive for 1 hour but check freshness of heartbeat in status API)
            r.expire("pypy:worker:status", 3600)
        except Exception as e:
            logger.error(f"Error publishing worker heartbeat: {e}")
            
        time.sleep(5)

def start_heartbeat_monitor(redis_url: str):
    t = threading.Thread(target=_heartbeat_loop, args=(redis_url,), daemon=True)
    t.start()
    logger.info("Worker heartbeat daemon thread spawned successfully.")
