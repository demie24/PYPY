import pytest
import time
from core.assistant.n8n_orchestration_bridge import N8nOrchestrationBridge

def test_payload_validation_and_injection():
    bridge = N8nOrchestrationBridge()
    
    # Safe payload
    assert bridge.validate_payload({"command": "status", "bus": "Bus_5"}) is True
    
    # Malicious injection payloads
    assert bridge.validate_payload({"command": "status; rm -rf /"}) is False
    assert bridge.validate_payload({"command": "status & cat /etc/passwd"}) is False
    assert bridge.validate_payload({"command": "status | wget malicious_site"}) is False
    assert bridge.validate_payload({"command": "`whoami`"}) is False
    assert bridge.validate_payload({"command": "$((1+1))"}) is False
    assert bridge.validate_payload({"command": "backslash\\test"}) is False

def test_dispatch_webhook_success_and_rejection():
    bridge = N8nOrchestrationBridge()
    
    # Success dispatch
    res = bridge.dispatch_webhook("test_hook", {"param": "value"})
    assert res["status"] == "SUCCESS"
    assert res["retry_count"] == 0
    
    # Rejected injection dispatch
    res_reject = bridge.dispatch_webhook("test_hook", {"param": "value; injection"})
    assert res_reject["status"] == "REJECTED"
    assert res_reject["error"] == "command_injection_detected"

def test_webhook_retry_backoff_and_failure():
    # Base delay of 0.05s for quick tests
    bridge = N8nOrchestrationBridge(base_backoff_sec=0.05, max_retries=2)
    
    # Dispatch forcing network failure simulation
    res = bridge.dispatch_webhook("failed_hook", {"param": "retry_me"}, force_failure=True)
    assert res["status"] == "RETRACTED_FOR_RETRY"
    
    summary = bridge.get_status_summary()
    assert summary["active_retries_count"] == 1
    assert summary["active_retries"][0]["retry_count"] == 0
    
    # Tick immediately - should not run because backoff (0.05s) is active
    completed = bridge.tick()
    assert len(completed) == 0
    
    # Wait for first backoff window and tick
    time.sleep(0.06)
    completed = bridge.tick()
    # Should attempt and fail, scheduling next retry with double delay (0.10s)
    assert len(completed) == 0
    assert bridge.active_retries[0]["retry_count"] == 1
    
    # Wait for second backoff (0.10s) and tick, should reach max retries (2) and mark FAILED
    time.sleep(0.12)
    completed = bridge.tick()
    assert len(completed) == 1
    assert completed[0]["status"] == "FAILED"
    assert completed[0]["error"] == "max_retries_exceeded"
    assert bridge.get_status_summary()["active_retries_count"] == 0
