# core/services/operations/alert_service.py
"""
V11.8 — Alert Manager & Notification Engine
Evaluates metrics against thresholds, generates alert events,
and dispatches email/Telegram notifications.
"""

import os
import logging
import smtplib
import uuid
from email.mime.text import MIMEText
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

logger = logging.getLogger("operations.alerts")

# ─── Alert Thresholds ──────────────────────────────────────────────────────────

DEFAULT_RULES = [
    {"id": "cpu_high",     "name": "CPU High",          "metric": "cpu_percent",          "threshold": 90.0, "operator": "gt", "severity": "critical"},
    {"id": "ram_high",     "name": "RAM High",           "metric": "ram_percent",          "threshold": 90.0, "operator": "gt", "severity": "critical"},
    {"id": "disk_high",    "name": "Disk High",          "metric": "disk_percent",         "threshold": 90.0, "operator": "gt", "severity": "warning"},
    {"id": "gw_offline",   "name": "Gateway Offline",    "metric": "gateway_status",       "threshold": None, "operator": "offline", "severity": "critical"},
    {"id": "mqtt_offline", "name": "MQTT Offline",       "metric": "mqtt_status",          "threshold": None, "operator": "offline", "severity": "critical"},
    {"id": "redis_offline","name": "Redis Offline",      "metric": "redis_status",         "threshold": None, "operator": "offline", "severity": "critical"},
    {"id": "worker_down",  "name": "Worker Offline",     "metric": "celery_worker_status", "threshold": None, "operator": "offline", "severity": "critical"},
    {"id": "sim_failure",  "name": "Simulation Failure", "metric": "failed_simulations",   "threshold": 1,    "operator": "gte",    "severity": "warning"},
    {"id": "queue_depth",  "name": "Queue Overloaded",   "metric": "queue_length",         "threshold": 20,   "operator": "gt",    "severity": "warning"},
    {"id": "error_rate",   "name": "Error Rate High",    "metric": "error_rate_percent",   "threshold": 5.0,  "operator": "gt",    "severity": "warning"},
]


def _evaluate_rule(rule: Dict, snapshot: Dict) -> bool:
    """Returns True if a rule threshold is breached."""
    metric_key = rule["metric"]
    operator = rule["operator"]
    threshold = rule.get("threshold")

    # Flatten nested snapshot
    value = (
        snapshot.get("system", {}).get(metric_key) or
        snapshot.get("simulations", {}).get(metric_key) or
        snapshot.get("api", {}).get(metric_key)
    )

    # Service status checks
    if operator == "offline":
        service_name = metric_key.replace("_status", "")
        service_data = snapshot.get("services", {}).get(service_name, {})
        status = service_data.get("status", "offline") if isinstance(service_data, dict) else "offline"
        return status != "online"

    if value is None:
        return False

    if operator == "gt":
        return float(value) > float(threshold)
    elif operator == "gte":
        return float(value) >= float(threshold)
    elif operator == "lt":
        return float(value) < float(threshold)
    elif operator == "eq":
        return value == threshold
    return False


def evaluate_all_rules(snapshot: Dict, db: Optional[Session] = None) -> List[Dict]:
    """Evaluate all default rules against a metrics snapshot. Returns fired alerts."""
    fired = []
    for rule in DEFAULT_RULES:
        try:
            breached = _evaluate_rule(rule, snapshot)
        except Exception as e:
            logger.warning(f"Error evaluating rule {rule['id']}: {e}")
            breached = False

        if breached:
            alert = {
                "id": str(uuid.uuid4()),
                "rule_id": rule["id"],
                "rule_name": rule["name"],
                "severity": rule["severity"],
                "message": f"Alert: {rule['name']} threshold breached.",
                "fired_at": datetime.now(timezone.utc).isoformat(),
                "acknowledged": False,
            }
            fired.append(alert)

            # Persist to DB if session provided
            if db:
                _persist_alert(db, alert)

    return fired


def _persist_alert(db: Session, alert: Dict):
    """Save alert event to the DB."""
    try:
        from services.auth.models import AlertEvent
        event = AlertEvent(
            id=uuid.UUID(alert["id"]),
            rule_id=alert["rule_id"],
            rule_name=alert["rule_name"],
            severity=alert["severity"],
            message=alert["message"],
            fired_at=datetime.now(timezone.utc),
            acknowledged=False,
        )
        db.add(event)
        db.commit()
    except Exception as e:
        logger.error(f"Failed to persist alert: {e}")


# ─── Notification Dispatchers ─────────────────────────────────────────────────

def send_email_alert(to_email: str, alert: Dict) -> bool:
    """Send an email notification for a fired alert."""
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")
    from_email = os.getenv("ALERT_FROM_EMAIL", smtp_user)

    if not smtp_host or not smtp_user:
        logger.warning("SMTP not configured — skipping email alert.")
        return False

    try:
        subject = f"[PYPY Grid Alert] {alert['severity'].upper()}: {alert['rule_name']}"
        body = (
            f"PYPY Grid Operations Alert\n\n"
            f"Rule: {alert['rule_name']}\n"
            f"Severity: {alert['severity']}\n"
            f"Message: {alert['message']}\n"
            f"Time: {alert['fired_at']}\n\n"
            f"Please check the Operations Center immediately.\n"
        )
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = from_email
        msg["To"] = to_email

        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
            server.ehlo()
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(from_email, [to_email], msg.as_string())
        logger.info(f"Email alert sent to {to_email}: {alert['rule_name']}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email alert: {e}")
        return False


def send_telegram_alert(alert: Dict) -> bool:
    """Send a Telegram notification for a fired alert."""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not bot_token or not chat_id:
        logger.warning("Telegram not configured — skipping notification.")
        return False

    import urllib.request
    import json

    severity_emoji = {"critical": "🔴", "warning": "⚠️", "info": "ℹ️"}.get(alert["severity"], "🔔")
    text = (
        f"{severity_emoji} *PYPY Grid Alert*\n"
        f"*Rule:* {alert['rule_name']}\n"
        f"*Severity:* {alert['severity'].upper()}\n"
        f"*Message:* {alert['message']}\n"
        f"*Time:* {alert['fired_at']}"
    )

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = json.dumps({"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}).encode()
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            if result.get("ok"):
                logger.info(f"Telegram alert sent: {alert['rule_name']}")
                return True
    except Exception as e:
        logger.error(f"Failed to send Telegram alert: {e}")
    return False


def dispatch_alerts(fired_alerts: List[Dict]):
    """Dispatch all fired alerts to configured channels."""
    alert_email = os.getenv("ALERT_EMAIL")
    telegram_enabled = bool(os.getenv("TELEGRAM_BOT_TOKEN"))

    for alert in fired_alerts:
        if alert_email:
            send_email_alert(alert_email, alert)
        if telegram_enabled:
            send_telegram_alert(alert)
