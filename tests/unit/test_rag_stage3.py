import pytest
import time
from core.assistant.engineering_reasoning_engine import EngineeringReasoningEngine
from core.assistant.rag_engine import RAGEngine
from core.assistant.orchestration_planner_bridge import OrchestrationPlannerBridge
from core.assistant.memory_orchestrator import MemoryOrchestrator

def test_topology_analysis():
    engine = EngineeringReasoningEngine()
    
    # Check Bus 5 impact
    impact_5 = engine.analyze_topology_impact("Bus_5")
    assert "Bus_4" in impact_5["neighbors"]
    assert "Bus_6" in impact_5["neighbors"]
    assert "L4_5" in impact_5["associated_lines"]
    assert "L5_6" in impact_5["associated_lines"]
    assert impact_5["load_lost"] == "Load_5 (1.25 p.u.)"
    assert "Bus_5" in impact_5["islanding_zone"]
    assert "Bus_6" in impact_5["islanding_zone"]
    assert "Tutup tie-breaker L7_8 secara manual" in impact_5["restoration_path"]
    
    # Check protecting relays for Bus 7
    relays_7 = engine.get_relay_relationships("Bus_7")
    assert "RELAY_IED_L2_7" in relays_7
    assert "RELAY_IED_L6_7" in relays_7
    assert "RELAY_IED_L7_8" in relays_7

def test_ontology_translation():
    engine = EngineeringReasoningEngine()
    telemetry = {"state": {}, "validation": {"trust_score": 100.0, "kcl_validated": True, "kvl_validated": True}}
    event_mem = []
    
    # Check translation of "voltan rendah" to undervoltage for Bus 5
    res = engine.handle_engineering_query("Langkah untuk voltan rendah Bus 5?", telemetry, event_mem)
    assert res is not None
    assert res["topic"] == "topology_analysis"
    assert "Load_5" in res["response"]
    
    # Check translation of "geganti" / "perlindungan"
    res_relay = engine.handle_engineering_query("Apakah geganti perlindungan Bus 7?", telemetry, event_mem)
    assert res_relay is not None
    assert res_relay["topic"] == "relay_coordination"
    assert "RELAY_IED_L7_8" in res_relay["response"]

def test_temporal_timeline():
    engine = EngineeringReasoningEngine()
    
    # Simulate historical log event queue
    now_ms = time.time() * 1000
    event_mem = [
        {"timestamp": now_ms - 5000, "event_type": "CYBER_ATTACK", "details": "FDIA detected at Substation 5", "severity": "HIGH"},
        {"timestamp": now_ms - 2000, "event_type": "RELAY_TRIP", "details": "Breaker L4_5 open by Relay IED", "severity": "CRITICAL"},
        {"timestamp": now_ms - 1000, "event_type": "FAULT", "details": "Bus 5 voltan rendah 0.82 p.u.", "severity": "CRITICAL"}
    ]
    
    timeline = engine.analyze_temporal_history(event_mem)
    assert len(timeline) == 3
    # Check chronological ordering (earliest event offset is largest)
    assert timeline[0]["time_offset_sec"] >= 4.5
    assert timeline[2]["time_offset_sec"] >= 0.5
    assert timeline[0]["type"] == "CYBER_ATTACK"
    assert timeline[2]["type"] == "FAULT"

def test_advanced_hybrid_rag_fusion():
    # Verify RAGEngine handle_query dispatches topology queries to EngineeringReasoningEngine
    engine = RAGEngine()
    telemetry = {
        "state": {
            "buses": {
                "Bus_5": {"voltage_pu": 0.82}
            }
        },
        "validation": {"trust_score": 100.0}
    }
    threat = {"threat_score": 25.0}
    mem = MemoryOrchestrator()
    
    # Query details topology impact
    res = engine.handle_query("Apakah kesan sekiranya Bus 5 gagal?", telemetry, threat, mem)
    assert res is not None
    assert "Analisis Topologi bagi [Bus_5]" in res["response"]
    assert res["confidence"] == 0.95
    assert len(res["hits"]) > 0  # Embedded SOP references
    assert "L4_5" in res["topology_details"]["lines"]

def test_safety_supervision_interception():
    bridge = OrchestrationPlannerBridge(confidence_threshold=0.50, min_stability=30.0)
    
    # 1. Test nominal execution works
    grid_state_nominal = {
        "threat": {"threat_score": 10.0, "confidence": 0.95, "affected_nodes": []},
        "telemetry": {
            "stability_index": 85.0,
            "validation": {"trust_score": 100.0, "kcl_validated": True, "kvl_validated": True},
            "attack_active": False
        }
    }
    step_load_shed = {"objective": "SHED_LOAD", "parameters": {"bus_id": "Bus_5", "percentage": 100.0}}
    res_nominal = bridge.evaluate_confidence_and_safety(step_load_shed, grid_state_nominal)
    assert res_nominal["status"] == "SUCCESS"

    # 2. Test Rule C: Low telemetry trust score blocks load shed
    grid_state_low_trust = {
        "threat": {"threat_score": 10.0, "confidence": 0.95, "affected_nodes": []},
        "telemetry": {
            "stability_index": 85.0,
            "validation": {"trust_score": 82.0, "kcl_validated": False, "kvl_validated": True},
            "attack_active": False
        }
    }
    res_low_trust = bridge.evaluate_confidence_and_safety(step_load_shed, grid_state_low_trust)
    assert res_low_trust["status"] == "FAILED"
    assert "trust score too low" in res_low_trust["error"]

    # 3. Test Rule D: Active cyberattack and high threat score blocks automation
    grid_state_attack = {
        "threat": {"threat_score": 85.0, "confidence": 0.95, "affected_nodes": ["Sub_5"]},
        "telemetry": {
            "stability_index": 85.0,
            "validation": {"trust_score": 100.0, "kcl_validated": True, "kvl_validated": True},
            "attack_active": True
        }
    }
    res_attack = bridge.evaluate_confidence_and_safety(step_load_shed, grid_state_attack)
    assert res_attack["status"] == "FAILED"
    assert res_attack["error"] == "cyberattack_suppression"

    # 4. Test Rule E: Operations on critical slack/generator bus (Bus 1, 2, 3, 4) are blocked
    step_critical_shed = {"objective": "SHED_LOAD", "parameters": {"bus_id": "Bus_1", "percentage": 100.0}}
    res_critical = bridge.evaluate_confidence_and_safety(step_critical_shed, grid_state_nominal)
    assert res_critical["status"] == "FAILED"
    assert "critical infrastructure bus" in res_critical["error"]
