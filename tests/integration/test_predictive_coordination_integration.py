import pytest
import json
from unittest.mock import MagicMock, patch
from core.assistant.assistant_daemon import AssistantDaemon

class MockMQTTMessage:
    def __init__(self, topic, payload):
        self.topic = topic
        self.payload = json.dumps(payload).encode("utf-8")

def test_daemon_predictive_integration():
    with patch("paho.mqtt.client.Client") as mock_client:
        daemon = AssistantDaemon()
        daemon.client = MagicMock()
        
        # 1. Simulate recurring telemetry latencies
        daemon._on_message(None, None, MockMQTTMessage("assistant/predictive_coordination_simulation", {"action": "add_latency", "latency": 50.0}))
        daemon._on_message(None, None, MockMQTTMessage("assistant/predictive_coordination_simulation", {"action": "add_latency", "latency": 70.0}))
        daemon._on_message(None, None, MockMQTTMessage("assistant/predictive_coordination_simulation", {"action": "add_latency", "latency": 90.0}))
        
        assert len(daemon.predictive_coordination.latency_history) == 3
        
        # 2. Tick presence & proactive loops to generate trends and optimizations
        daemon.tick_periodic_presence_and_proactive()
        
        # Trigger conflict: set threat high (85.0) clashing with TRIM_DELAY optimization recommendation
        daemon.grid_state["threat"] = {"threat_score": 85.0}
        
        # Eval sync and check for override
        daemon._on_message(None, None, MockMQTTMessage("assistant/cross_system_coordination_simulation", {}))
        
        assert daemon.cross_coordination.sync_state == "CONFLICT_RESOLVING"
        assert len(daemon.cross_coordination.conflict_logs) > 0
        assert daemon.workflow_optimizer.recommendations[0]["status"] == "BLOCKED"

def test_daemon_persistent_routine_integration():
    with patch("paho.mqtt.client.Client") as mock_client:
        daemon = AssistantDaemon()
        daemon.client = MagicMock()
        
        # Clear persistent memory files
        daemon.persistent_memory.clear_memory()
        
        # Simulate chat input to store action in persistent routine memory
        chat_payload = {"text": "buka youtube"}
        daemon._on_message(None, None, MockMQTTMessage("assistant/chat_input", chat_payload))
        
        # Verify interaction is recorded
        summary = daemon.persistent_memory.get_status_summary()
        assert summary["total_interactions"] == 1
