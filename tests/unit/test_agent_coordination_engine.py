import pytest
from core.assistant.telemetry_agent import TelemetryAgent
from core.assistant.relay_agent import RelayAgent
from core.assistant.workflow_agent import WorkflowAgent
from core.assistant.security_agent import SecurityAgent
from core.assistant.agent_coordination_engine import AgentCoordinationEngine

def create_engine():
    t = TelemetryAgent()
    r = RelayAgent()
    w = WorkflowAgent()
    s = SecurityAgent()
    engine = AgentCoordinationEngine(t, r, w, s)
    return engine, t, r, w, s

def test_coordination_engine_initial_state():
    engine, t, r, w, s = create_engine()
    summary = engine.get_status_summary()
    assert summary["agent_name"] == "AgentCoordinationEngine"
    assert summary["status"] == "NOMINAL"
    assert summary["consensus_state"] == "IDLE"
    assert summary["consensus_score"] == 1.0
    assert not summary["delegation_chain"]
    assert not summary["inter_agent_logs"]

def test_coordination_engine_delegation_flow():
    engine, t, r, w, s = create_engine()
    
    # 1. Nominal data
    res = engine.coordinate_agents(
        telemetry={"bus_1_v": 1.0, "line_L1_2_load": 40.0},
        sync_states={},
        relay_summary={"breakers": {}},
        workflows_summary={},
        task_chains_summary={},
        threat_summary={"threat_score": 10.0, "confidence": 1.0, "severity": "LOW"},
        active_attacks=[]
    )
    assert res["status"] == "NOMINAL"
    assert res["delegation_chain"] == ["TelemetryAgent"]
    
    # 2. Critical anomaly causing cascading delegation
    # Telemetry finds anomaly -> asks Relay -> Relay finds anomaly -> asks Security -> Security finds attack -> Workflow
    res = engine.coordinate_agents(
        telemetry={"bus_1_v": 0.80, "line_L1_2_load": 115.0},
        sync_states={},
        relay_summary={"breakers": {"L1_4": {"unstable": True, "wear_pct": 20.0, "timing_ms": 50.0}}},
        workflows_summary={},
        task_chains_summary={},
        threat_summary={"threat_score": 85.0, "confidence": 0.90, "severity": "CRITICAL"},
        active_attacks=["mitm_replay"]
    )
    assert res["status"] == "CRITICAL"
    assert res["delegation_chain"] == ["TelemetryAgent", "RelayAgent", "SecurityAgent", "WorkflowAgent"]
    assert len(res["inter_agent_logs"]) > 0

def test_coordination_engine_loop_prevention():
    engine, t, r, w, s = create_engine()
    
    # Force cascading delegation loop override
    engine.simulation_mode = "cascading_failures"
    res = engine.coordinate_agents(
        telemetry={"bus_1_v": 0.80},
        sync_states={},
        relay_summary={},
        workflows_summary={},
        task_chains_summary={},
        threat_summary={},
        active_attacks=[]
    )
    assert res["status"] == "LOOP_PREVENTED"
    assert res["consensus_state"] == "BLOCKED (LOOP_PREVENTED)"
    assert res["consensus_score"] == 0.0
    assert any("kedalaman > 3" in log for log in res["inter_agent_logs"])

def test_coordination_engine_consensus_arbitration():
    engine, t, r, w, s = create_engine()
    
    # 1. Test consensus approved with high confidence (>= 0.75)
    res = engine.coordinate_agents(
        telemetry={"bus_1_v": 0.80},
        sync_states={},
        relay_summary={"breakers": {"L1_4": {"unstable": True}}},
        workflows_summary={},
        task_chains_summary={},
        threat_summary={"threat_score": 85.0, "confidence": 0.80, "severity": "CRITICAL"},
        active_attacks=[]
    )
    assert res["consensus_state"] == "APPROVED"
    assert res["consensus_score"] >= 0.75
    
    # 2. Test consensus blocked with low confidence (< 0.75)
    res = engine.coordinate_agents(
        telemetry={"bus_1_v": 0.80},
        sync_states={},
        relay_summary={"breakers": {"L1_4": {"unstable": True}}},
        workflows_summary={},
        task_chains_summary={},
        threat_summary={"threat_score": 85.0, "confidence": 0.60, "severity": "CRITICAL"},
        active_attacks=[]
    )
    assert res["consensus_state"] == "BLOCKED (LOW_CONFIDENCE)"
    assert res["consensus_score"] < 0.75

def test_coordination_engine_malay_queries():
    engine, t, r, w, s = create_engine()
    
    # Analyze state to populate data
    engine.coordinate_agents(
        telemetry={"bus_1_v": 0.80},
        sync_states={"node_sync_states": {"esp32_zone1": {"drift_sec": 0.045}}},
        relay_summary={"breakers": {"L1_4": {"unstable": True}}},
        workflows_summary={"completed_workflows": [{"workflow_name": "system_status_check", "status": "FAILED"}]},
        task_chains_summary={},
        threat_summary={"threat_score": 85.0, "confidence": 0.80, "severity": "CRITICAL"},
        active_attacks=["replay"]
    )
    
    # Query 1: worst agent
    resp = engine.handle_query("agent mana detect masalah paling kritikal")
    assert "TelemetryAgent" in resp or "RelayAgent" in resp or "SecurityAgent" in resp or "WorkflowAgent" in resp
    
    # Query 2: coordinated recovery plan
    resp = engine.handle_query("buat coordinated recovery plan")
    assert "Coordinated Recovery Plan" in resp
    assert "KONSENSUS" in resp or "Konsensus" in resp
    
    # Query 3: relay agent report
    resp = engine.handle_query("status relay agent")
    assert "RelayAgent" in resp
    
    # Query 4: telemetry drift
    resp = engine.handle_query("telemetry agent summarize drift")
    assert "TelemetryAgent" in resp
    assert "esp32_zone1" in resp
    
    # Query 5: security report
    resp = engine.handle_query("security agent lapor")
    assert "SecurityAgent" in resp
    assert "ACTIVE_ATTACK" in resp

def test_coordination_engine_reset():
    engine, t, r, w, s = create_engine()
    engine.coordinate_agents(
        telemetry={"bus_1_v": 0.80},
        sync_states={},
        relay_summary={},
        workflows_summary={},
        task_chains_summary={},
        threat_summary={},
        active_attacks=[]
    )
    assert engine.status != "NOMINAL"
    
    engine.reset_engine()
    assert engine.status == "NOMINAL"
    assert engine.consensus_state == "IDLE"
    assert engine.consensus_score == 1.0
    assert not engine.delegation_chain
    assert not engine.inter_agent_logs
