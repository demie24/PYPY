import pytest
import time
from core.assistant.action_router import ActionRouter

def test_action_router_open_youtube():
    router = ActionRouter()
    result = router.route_action("open_youtube", {})
    assert result["action"] == "open_youtube"
    assert result["status"] == "SUCCESS"
    assert result["payload"]["url"] == "https://www.youtube.com"

def test_action_router_open_browser():
    router = ActionRouter()
    result = router.route_action("open_browser", {})
    assert result["action"] == "open_browser"
    assert result["status"] == "SUCCESS"
    assert result["payload"]["url"] == "https://www.google.com"

def test_action_router_get_time():
    router = ActionRouter()
    result = router.route_action("get_time", {})
    assert result["action"] == "get_time"
    assert result["status"] == "SUCCESS"
    assert "time" in result["payload"]

def test_action_router_get_system_status_nominal():
    router = ActionRouter()
    grid_state = {
        "telemetry": {"state": {"buses": {"Bus_1": {"P_mw": 10}}}},
        "threat": {"threat_score": 10.0, "affected_nodes": []}
    }
    result = router.route_action("get_system_status", {}, grid_state=grid_state)
    assert result["action"] == "get_system_status"
    assert result["status"] == "SUCCESS"
    assert result["payload"]["stability"] == "NORMAL"
    assert result["payload"]["threat_score"] == 10.0
    assert result["payload"]["active_attack"] is False

def test_action_router_get_system_status_critical():
    router = ActionRouter()
    grid_state = {
        "telemetry": {"state": {"buses": {"Bus_1": {"P_mw": 10}}}},
        "threat": {"threat_score": 85.0, "affected_nodes": ["Bus_5"]}
    }
    result = router.route_action("get_system_status", {}, grid_state=grid_state)
    assert result["action"] == "get_system_status"
    assert result["status"] == "SUCCESS"
    assert result["payload"]["stability"] == "CRITICAL"
    assert result["payload"]["threat_score"] == 85.0
    assert result["payload"]["active_attack"] is True

def test_action_router_n8n_and_unsupported():
    router = ActionRouter()
    result1 = router.route_action("n8n_restoration", {"param1": "test"})
    assert result1["action"] == "n8n_restoration"
    assert result1["status"] == "PENDING_AUTOMATION"
    assert "webhook/restoration" in result1["payload"]["n8n_url"]
    
    result2 = router.route_action("unknown_action", {})
    assert result2["action"] == "unknown_action"
    assert result2["status"] == "UNSUPPORTED"
