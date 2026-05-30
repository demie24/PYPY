import pytest
from core.assistant.automation_hook_manager import AutomationHookManager

def test_automation_hook_validation_clean():
    manager = AutomationHookManager()
    
    # Clean parameters
    assert manager.validate_parameters({}) is True
    assert manager.validate_parameters({"zone": "zone_5", "bus": "Bus_3"}) is True
    assert manager.validate_parameters({"text": "keadaan grid ok ke?"}) is True

def test_automation_hook_validation_injection():
    manager = AutomationHookManager()
    
    # Injection attempts
    assert manager.validate_parameters({"cmd": "ls; rm -rf /"}) is False
    assert manager.validate_parameters({"target": "Bus_1 | cat /etc/passwd"}) is False
    assert manager.validate_parameters({"payload": "$(whoami)"}) is False
    assert manager.validate_parameters({"url": "http://n8n-broker:5678/webhook`id`"}) is False
    assert manager.validate_parameters({"path": "test & shutdown -h now"}) is False

def test_automation_hook_dispatch_success():
    manager = AutomationHookManager()
    
    payload = {
        "status": "SUCCESS",
        "parameters": {"zone": "zone_1"}
    }
    
    # Valid allowlist hook
    result = manager.trigger_webhook("n8n_restoration", payload)
    assert result["status"] == "SUCCESS"
    assert result["message"] == "TRIGGERED"
    assert result["hook_name"] == "n8n_restoration"
    assert "endpoint_url" in result["payload"]
    assert result["payload"]["endpoint_url"] == "http://n8n-broker:5678/webhook/restoration"
    assert manager.trigger_count == 1
    
    summary = manager.get_automation_summary()
    assert summary["trigger_count"] == 1
    assert summary["latest_hook_status"] == result

def test_automation_hook_dispatch_unauthorized():
    manager = AutomationHookManager()
    
    payload = {"parameters": {}}
    
    # Unauthorized hook name
    result = manager.trigger_webhook("n8n_delete_database", payload)
    assert result["status"] == "FAILED"
    assert result["message"] == "UNAUTHORIZED_ENDPOINT"
    assert manager.trigger_count == 1

def test_automation_hook_dispatch_blocked():
    manager = AutomationHookManager()
    
    # Parameter guard intercept
    payload = {
        "parameters": {"zone": "zone_1; rm -rf /"}
    }
    
    result = manager.trigger_webhook("n8n_restoration", payload)
    assert result["status"] == "FAILED"
    assert result["message"] == "SECURITY_VALIDATION_BLOCKED"
    assert manager.trigger_count == 1
