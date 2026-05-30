import pytest
import json
import time
from unittest.mock import MagicMock, patch
from core.assistant.assistant_daemon import AssistantDaemon

class MockMQTTMessage:
    def __init__(self, topic, payload):
        self.topic = topic
        self.payload = json.dumps(payload).encode("utf-8")

def test_assistant_daemon_initialization():
    with patch("paho.mqtt.client.Client") as mock_client:
        daemon = AssistantDaemon()
        assert daemon.broker == "localhost"
        assert daemon.port == 1883
        assert daemon.state_mgr.state == "IDLE"
        assert daemon.grid_state["telemetry"] == {}

def test_assistant_daemon_reset():
    with patch("paho.mqtt.client.Client") as mock_client:
        daemon = AssistantDaemon()
        daemon.client = MagicMock()
        
        daemon.context_eng.session_active = True
        daemon.context_eng.interaction_depth = 5
        daemon.memory_orch.add_interaction("user", "test")
        
        daemon.reset_assistant()
        
        # Verify reset cleared context and memory
        assert daemon.context_eng.session_active is False
        assert daemon.context_eng.interaction_depth == 0
        assert len(daemon.memory_orch.interactions) == 0
        assert daemon.state_mgr.state == "IDLE"

def test_assistant_daemon_process_request_greeting():
    with patch("paho.mqtt.client.Client") as mock_client:
        daemon = AssistantDaemon()
        daemon.client = MagicMock()
        
        # Mock telemetry publishing to verify topic names
        published_topics = []
        def mock_publish(topic, payload):
            published_topics.append(topic)
            return MagicMock()
        daemon.client.publish = mock_publish
        
        # Process a simple greeting request
        daemon.process_request("hello assistant", is_voice=False)
        
        # Check that the runtime variables were populated
        assert len(daemon.memory_orch.interactions) == 2 # 1 user, 1 assistant response
        assert daemon.memory_orch.interactions[0]["role"] == "user"
        assert daemon.memory_orch.interactions[0]["text"] == "hello assistant"
        
        # Check that assistant ended back in IDLE
        assert daemon.state_mgr.state == "IDLE"
        
        # Verify that all 7 required telemetry topics were published
        assert "assistant/state" in published_topics
        assert "assistant/intent" in published_topics
        assert "assistant/emotion" in published_topics
        assert "assistant/actions" in published_topics
        assert "assistant/context" in published_topics
        assert "assistant/memory" in published_topics
        assert "assistant/runtime" in published_topics
        assert "assistant/response" in published_topics

def test_assistant_daemon_process_command_youtube_safety_override():
    with patch("paho.mqtt.client.Client") as mock_client:
        daemon = AssistantDaemon()
        daemon.client = MagicMock()
        daemon.client.publish = MagicMock()
        
        # Scenario 1: Nominal grid threat. YouTube is allowed.
        daemon.grid_state["threat"] = {"threat_score": 10.0, "affected_nodes": []}
        daemon.process_request("buka youtube", is_voice=False)
        
        # Should execute successfully, actions history records open_youtube
        assert "open_youtube" in daemon.memory_orch.command_history
        
        # Scenario 2: High grid threat. YouTube request should be blocked.
        daemon.memory_orch.clear_memory()
        daemon.grid_state["threat"] = {"threat_score": 85.0, "affected_nodes": ["Bus_5"]}
        daemon.process_request("buka youtube", is_voice=False)
        
        # "open_youtube" should not be executed. It should redirect to get_system_status or block.
        assert "open_youtube" not in daemon.memory_orch.command_history
        assert "get_system_status" in daemon.memory_orch.command_history

def test_assistant_daemon_on_message_routing():
    with patch("paho.mqtt.client.Client") as mock_client:
        daemon = AssistantDaemon()
        daemon.client = MagicMock()
        daemon.client.publish = MagicMock()
        
        # Simulate incoming grid telemetry message
        telem_payload = {"state": {"buses": {"Bus_5": {"voltage": 1.0}}}}
        daemon._on_message(None, None, MockMQTTMessage("grid/telemetry", telem_payload))
        assert daemon.grid_state["telemetry"] == telem_payload
        
        # Simulate incoming grid threat message
        threat_payload = {"threat_score": 45.0, "affected_nodes": []}
        daemon._on_message(None, None, MockMQTTMessage("grid/threat", threat_payload))
        assert daemon.grid_state["threat"] == threat_payload
        
        # Simulate incoming user chat request
        chat_payload = {"text": "apa khabar?"}
        daemon._on_message(None, None, MockMQTTMessage("assistant/chat_input", chat_payload))
        # Verify it ran process_request and generated a response
        assert len(daemon.memory_orch.interactions) == 2
