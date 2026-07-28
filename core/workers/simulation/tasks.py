# core/workers/simulation/tasks.py

import os
import time
import json
import logging
import uuid
import redis
from datetime import datetime, timezone
from celery import Celery
from celery.exceptions import MaxRetriesExceededError
from celery.signals import task_prerun, task_postrun, worker_ready
import paho.mqtt.client as mqtt

from services.auth.session import get_db_context
from services.auth.models import SimulatorRun, User
from workers.health.worker_monitor import (
    start_heartbeat_monitor,
    increment_active_tasks,
    decrement_active_tasks
)
from services.simulation.audit import log_simulation_audit
from services.simulation.notifications import send_simulation_email

logger = logging.getLogger("workers.simulation")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
app = Celery("pypy_simulation_worker", broker=REDIS_URL)

# 1. Connect worker ready signal to launch status heartbeat
@worker_ready.connect
def start_monitor_on_ready(sender, **kwargs):
    start_heartbeat_monitor(REDIS_URL)
    logger.info("Worker initialization signal: Started heartbeat thread.")

# 2. Track active tasks inside this process using prerun/postrun signals
@task_prerun.connect
def task_prerun_handler(task_id, task, *args, **kwargs):
    increment_active_tasks()

@task_postrun.connect
def task_postrun_handler(task_id, task, *args, **kwargs):
    decrement_active_tasks()

@app.task(bind=True, max_retries=3, default_retry_delay=30)
def run_grid_simulation(self, tenant_id: str, run_id: str, grid_name: str, config: dict):
    logger.info(f"Celery simulator run {run_id} started (retry={self.request.retries}) for Tenant {tenant_id} on Grid {grid_name}")
    
    tenant_uuid = uuid.UUID(tenant_id)
    job_uuid = uuid.UUID(run_id)
    
    # Audit log: JOB_STARTED
    with get_db_context() as db:
        log_simulation_audit(db, tenant_uuid, job_uuid, "JOB_STARTED", details=f"Simulation task running. Attempt {self.request.retries + 1}")
        user = db.query(User).filter(User.tenant_id == tenant_uuid).first()
        admin_email = user.email if user else "admin@pypygrid.com"
        
    # Send started notification email
    send_simulation_email(
        to_email=admin_email,
        template_name="simulation_started.html",
        subject="[PYPY Grid] Simulation Job Started",
        variables={"run_id": run_id, "grid_name": grid_name, "tenant_id": tenant_id}
    )
    
    MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
    mqtt_client = mqtt.Client(client_id=f"saas_twin_{run_id}")
    
    # Use a single master try-except for retry and DLQ routing
    try:
        try:
            mqtt_client.connect(MQTT_BROKER, 1883)
            mqtt_client.loop_start()
        except Exception as mqtt_err:
            logger.error(f"MQTT connection failed for Celery twin: {mqtt_err}")
            raise mqtt_err
            
        try:
            from core.digital_twin.main import SmartGridDigitalTwin
            twin = SmartGridDigitalTwin(grid_name=grid_name.lower())
        except Exception as twin_err:
            logger.warning(f"Could not load Pandapower twin. Running in mock telemetry mode. Detail: {twin_err}")
            twin = None
            
        topic_prefix = f"pypy/{tenant_id}/{run_id}"
        step = 0
        max_steps = config.get("duration_seconds", 60)
        reported_percentages = set()
        
        while step < max_steps:
            with get_db_context() as db:
                run = db.query(SimulatorRun).filter(SimulatorRun.id == job_uuid).first()
                if not run or run.status != "RUNNING":
                    logger.info(f"Task run {run_id} marked as stopped or deleted. Exiting loop.")
                    break
                    
                # Update progress percentage in database at intervals
                progress = int((step / max_steps) * 100)
                for threshold in [0, 10, 25, 50, 75, 90]:
                    if progress >= threshold and threshold not in reported_percentages:
                        reported_percentages.add(threshold)
                        run.progress_percentage = threshold
                        db.commit()
                        break
                        
            if twin:
                telemetry = twin.run_simulation_sweep()
            else:
                telemetry = {
                    "grid_name": grid_name,
                    "status": "NOMINAL",
                    "timestamp": int(time.time() * 1000),
                    "metrics": {
                        "active_gen": 100.0 + step * 0.5,
                        "net_load": 150.0 + step * 0.2,
                        "frequency": 60.01 - (step * 0.001),
                        "stability": 1.012
                    },
                    "state": {"buses": {}, "lines": {}}
                }
                
            mqtt_client.publish(f"{topic_prefix}/telemetry", json.dumps(telemetry))
            time.sleep(1.0)
            step += 1
            
        with get_db_context() as db:
            run = db.query(SimulatorRun).filter(SimulatorRun.id == job_uuid).first()
            if run and run.status == "RUNNING":
                run.status = "COMPLETED"
                run.progress_percentage = 100
                run.stopped_at = datetime.now(timezone.utc)
                db.commit()
                
                log_simulation_audit(db, tenant_uuid, job_uuid, "JOB_COMPLETED", details="Simulation completed successfully.")
                
                send_simulation_email(
                    to_email=admin_email,
                    template_name="simulation_completed.html",
                    subject="[PYPY Grid] Simulation Completed",
                    variables={"run_id": run_id, "grid_name": grid_name, "tenant_id": tenant_id}
                )
                
    except Exception as e:
        logger.error(f"Error during Celery simulation loop: {e}", exc_info=True)
        try:
            with get_db_context() as db:
                log_simulation_audit(db, tenant_uuid, job_uuid, "JOB_RETRIED", details=f"Simulation crashed: {str(e)}. Triggering retry.")
            self.retry(exc=e)
        except MaxRetriesExceededError as re:
            logger.error(f"Max retries exceeded for simulation job {run_id}. Pushing to dead-letter queue.")
            with get_db_context() as db:
                run = db.query(SimulatorRun).filter(SimulatorRun.id == job_uuid).first()
                if run:
                    run.status = "FAILED"
                    db.commit()
                log_simulation_audit(db, tenant_uuid, job_uuid, "JOB_FAILED", details=f"Max retries exceeded. Error: {str(e)}")
                
            # Push payload to Redis dead-letter queue: simulation.deadletter
            try:
                r = redis.from_url(REDIS_URL)
                dlq_payload = {
                    "run_id": run_id,
                    "tenant_id": tenant_id,
                    "grid_name": grid_name,
                    "config": config,
                    "failed_at": datetime.now(timezone.utc).isoformat(),
                    "error": str(e)
                }
                r.rpush("simulation.deadletter", json.dumps(dlq_payload))
            except Exception as dlq_err:
                logger.error(f"Failed to write to dead-letter queue: {dlq_err}")
                
            # Send failure notification email
            send_simulation_email(
                to_email=admin_email,
                template_name="simulation_failed.html",
                subject="[PYPY Grid] Simulation Job Failed",
                variables={"run_id": run_id, "grid_name": grid_name, "tenant_id": tenant_id, "error_reason": str(e)}
            )
            raise re
    finally:
        try:
            mqtt_client.loop_stop()
            mqtt_client.disconnect()
        except Exception:
            pass
        logger.info(f"Simulator task run {run_id} terminated.")

# Import billing tasks to register them with this Celery app instance
import workers.billing.tasks
