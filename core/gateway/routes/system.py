from fastapi import APIRouter
from gateway.store import store
from gateway.mqtt_manager import mqtt_manager

router = APIRouter()

@router.get("/health")
def health_check():
    return {
        "status": "healthy",
        "mqtt_connected": mqtt_manager.client.is_connected()
    }

@router.get("/history/events")
def get_event_history():
    return {
        "events": store.events
    }

@router.get("/history/alerts")
def get_alert_history():
    return {
        "alerts": store.alerts
    }

@router.post("/alerts/clear")
def clear_alert_history():
    store.clear_alerts()
    # Also notify the grid that alarms are reset
    reset_payload = {
        "command": "RESET_ALARMS",
        "timestamp": int(time.time() * 1000) if 'time' in globals() else 0
    }
    # Dynamic import to avoid dependency cycle if any
    import time
    reset_payload["timestamp"] = int(time.time() * 1000)
    mqtt_manager.publish("grid/control", reset_payload)
    return {"status": "success", "message": "Alerts cleared and reset command broadcasted"}
