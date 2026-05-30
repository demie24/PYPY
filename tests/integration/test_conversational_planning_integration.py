import pytest
import json
import time
from unittest.mock import MagicMock, patch
from core.assistant.assistant_daemon import AssistantDaemon

class MockMQTTMessage:
    def __init__(self, topic, payload):
        self.topic = topic
        self.payload = json.dumps(payload).encode("utf-8")

def test_chained_task_plan_simulation():
    with patch("paho.mqtt.client.Client") as mock_client:
        daemon = AssistantDaemon()
        daemon.client = MagicMock()
        
        # Simulate creating a plan
        plan_payload = {
            "action": "create",
            "query": "check latency lepas tu kalau tinggi trigger recovery workflow",
            "intent": {"category": "CHECK_LATENCY", "action": "measure"}
        }
        daemon._on_message(None, None, MockMQTTMessage("assistant/plan_simulation", plan_payload))
        assert len(daemon.planning_engine.active_plans) == 1
        
        # Submit the chain
        chain_payload = {"action": "submit"}
        daemon._on_message(None, None, MockMQTTMessage("assistant/chain_simulation", chain_payload))
        assert len(daemon.task_chain_mgr.active_chains) == 1
        
        # Verify chain execution state
        chain_id = list(daemon.task_chain_mgr.active_chains.keys())[0]
        chain = daemon.task_chain_mgr.active_chains[chain_id]
        assert chain["status"] == "PENDING"
        
        # Tick the daemon presence and proactive loop to run the chain
        daemon.tick_periodic_presence_and_proactive()
        assert chain["status"] == "EXECUTING"
        assert chain["current_step_idx"] == 1
        assert chain["steps"][0]["status"] == "SUCCESS"

def test_live_stream_interruption_by_new_request():
    with patch("paho.mqtt.client.Client") as mock_client:
        daemon = AssistantDaemon()
        daemon.client = MagicMock()
        
        # Start a stream simulation
        stream_payload = {
            "action": "start",
            "text": "Sistem sedang mengesan gangguan transient pada Bus 5."
        }
        daemon._on_message(None, None, MockMQTTMessage("assistant/stream_simulation", stream_payload))
        assert daemon.live_stream.is_streaming is True
        assert daemon.live_stream.status == "STREAMING"
        
        # Tick stream to output some words
        daemon.tick_periodic_presence_and_proactive()
        assert daemon.live_stream.output_buffer != ""
        
        # Send a new chat request during streaming, patching _respond to prevent starting a new stream
        chat_payload = {"text": "buka youtube"}
        with patch.object(daemon, "_respond") as mock_respond:
            daemon._on_message(None, None, MockMQTTMessage("assistant/chat_input", chat_payload))
        
        # Verify streaming is interrupted
        assert daemon.live_stream.is_streaming is False
        assert daemon.live_stream.status == "INTERRUPTED"
        assert "Maaf mencelah" in daemon.live_stream.interruption_apology

def test_dialogue_ambiguity_clarification_and_resolution():
    with patch("paho.mqtt.client.Client") as mock_client:
        daemon = AssistantDaemon()
        daemon.client = MagicMock()
        
        # Send ambiguous request missing target bus
        chat_payload = {"text": "check latency"}
        daemon._on_message(None, None, MockMQTTMessage("assistant/chat_input", chat_payload))
        
        # Dialogue engine should transition to AWAITING_CLARIFICATION
        assert daemon.dialogue_engine.state == "AWAITING_CLARIFICATION"
        assert daemon.dialogue_engine.parameter_needed == "target_bus"
        assert "Bus 5 atau Bus 7" in daemon.dialogue_engine.clarification_question
        
        # Resolve dialogue by sending "Bus 5"
        resolve_payload = {"action": "resolve", "answer": "Bus 5"}
        daemon._on_message(None, None, MockMQTTMessage("assistant/dialogue_simulation", resolve_payload))
        
        # State should clear back to IDLE/RESOLVED
        assert daemon.dialogue_engine.state == "RESOLVED"
        assert daemon.dialogue_engine.pending_intent is None

def test_confidence_safety_gate_blocking():
    with patch("paho.mqtt.client.Client") as mock_client:
        daemon = AssistantDaemon()
        daemon.client = MagicMock()
        
        # Set safety settings to high (min confidence = 0.95)
        safety_payload = {
            "action": "set_safety",
            "confidence_threshold": 0.95,
            "min_stability": 30.0
        }
        daemon._on_message(None, None, MockMQTTMessage("assistant/orchestration_simulation", safety_payload))
        assert daemon.planner_bridge.confidence_threshold == 0.95
        
        # Mock grid state with threat confidence = 0.60 (too low)
        daemon.grid_state["threat"] = {"confidence": 0.60, "threat_score": 80.0}
        
        # Evaluate confidence and safety for a critical step
        step = {
            "objective": "TRIGGER_WORKFLOW",
            "parameters": {"workflow_name": "emergency_load_shed"}
        }
        res = daemon.planner_bridge.evaluate_confidence_and_safety(step, daemon.grid_state)
        assert res["status"] == "FAILED"
        assert "Confidence score too low" in res["error"]
