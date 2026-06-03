import os
import pytest
import time
import shutil
import tempfile
import json
from unittest.mock import Mock, MagicMock
from core.assistant.vector_store import EmbeddingModel, NumpyVectorStore, deterministic_hash
from core.assistant.memory_orchestrator import MemoryOrchestrator
from core.assistant.explainability_engine import ExplainabilityEngine
from core.assistant.reporting_engine import ReportingEngine
from core.assistant.assistant_daemon import AssistantDaemon

@pytest.fixture
def temp_dir():
    tmp = tempfile.mkdtemp()
    yield tmp
    shutil.rmtree(tmp)

def test_deterministic_embedding_hashing():
    # 1. Verify deterministic rolling hash
    h1 = deterministic_hash("voltage_tamper")
    h2 = deterministic_hash("voltage_tamper")
    assert h1 == h2
    assert isinstance(h1, int)
    
    # 2. Verify EmbeddingModel get_embedding is identical across runs
    embedder = EmbeddingModel()
    v1 = embedder.get_embedding("voltan rendah pada bus 5")
    v2 = embedder.get_embedding("voltan rendah pada bus 5")
    assert v1 == v2
    assert len(v1) == 32

def test_persistent_memory_and_vector_store(temp_dir):
    mem_path = os.path.join(temp_dir, "mem.json")
    vec_path = os.path.join(temp_dir, "vec.json")
    
    # 1. Initialize MemoryOrchestrator and save states
    mem_1 = MemoryOrchestrator(persistence_path=mem_path, enable_persistence=True)
    mem_1.add_interaction("user", "Jalankan load shed Hospital")
    mem_1.add_interaction("assistant", "Menjalankan tindakan load shed")
    mem_1.record_command("SHED_LOAD")
    mem_1.add_event("CYBER_ATTACK", "FDIA detected on Bus 5", "HIGH")
    mem_1.add_semantic_memory("undervoltage", "Operator requested restoration manual bypass")
    
    # Verify files created
    assert os.path.exists(mem_path)
    
    # 2. Re-initialize memory from disk and assert restoration
    mem_2 = MemoryOrchestrator(persistence_path=mem_path, enable_persistence=True)
    assert len(mem_2.interactions) == 2
    assert mem_2.interactions[0]["role"] == "user"
    assert mem_2.command_history == ["SHED_LOAD"]
    assert len(mem_2.event_memory) == 1
    assert mem_2.event_memory[0]["event_type"] == "CYBER_ATTACK"
    assert mem_2.semantic_memory["undervoltage"] == "Operator requested restoration manual bypass"

    # 3. Repeat for NumpyVectorStore
    vec_1 = NumpyVectorStore(persistence_path=vec_path, enable_persistence=True)
    embedder = EmbeddingModel()
    vec_1.insert(embedder.get_embedding("voltage drop"), {"title": "ANSI 27 SOP", "category": "operator_sops"})
    
    assert os.path.exists(vec_path)
    
    vec_2 = NumpyVectorStore(persistence_path=vec_path, enable_persistence=True)
    assert len(vec_2.entries) == 1
    assert vec_2.entries[0]["payload"]["title"] == "ANSI 27 SOP"

def test_explainability_engine():
    engine = ExplainabilityEngine()
    
    # Setup mock grid state
    grid_state = {
        "threat": {"threat_score": 85.0, "confidence": 0.90},
        "telemetry": {
            "attack_status": {
                "compromised_nodes": ["Bus_5"]
            }
        },
        "trust_scores": {
            "bus_trust": {"Bus_5": 35.5, "Bus_8": 80.0},
            "line_trust": {"L4_5": 40.0}
        },
        "physics_val": {
            "kcl_mismatches": {"Bus_5": 12.45},
            "violations": ["Bus_5 voltan melebihi had"]
        },
        "defense": {
            "breaker_lockdown_targets": ["Bus_5"],
            "escalation_level": "EMERGENCY_CONTAINMENT",
            "restoration_lockdown_active": True,
            "recommended_defense_actions": [
                {"target": "Bus_5", "action": "QUARANTINE_BREAKER"}
            ]
        },
        "l6_recovery": {
            "cooldown_active_breakers": ["L4_5"]
        },
        "operator_mode": "AUTO",
        "alerts": [
            {"suspect_node": "Bus_5", "type": "TARGETED_FDIA"}
        ]
    }
    
    # 1. Test explain isolation
    exp_iso = engine.explain_isolation("Bus 5", grid_state)
    assert "Bus_5" in exp_iso
    assert "kebolehpercayaan" in exp_iso
    assert "35.5%" in exp_iso
    assert "Kirchhoff" in exp_iso or "KCL" in exp_iso
    
    # 2. Test explain blocked restoration
    exp_block = engine.explain_blocked_restoration(grid_state)
    assert "disekat" in exp_block
    assert "Restoration Lockdown" in exp_block
    
    # 3. Test explain trust reduction
    exp_trust = engine.explain_trust_reduction("Bus 5", grid_state)
    assert "Bus_5" in exp_trust
    assert "35.5%" in exp_trust
    assert "Kirchhoff" in exp_trust or "KCL" in exp_trust
    
    # 4. Test explain rejected recovery
    grid_state["consensus_state"] = "BLOCKED (CONFLICT)"
    grid_state["consensus_score"] = 0.45
    exp_reject = engine.explain_rejected_recovery(grid_state)
    assert "ditolak" in exp_reject
    assert "konsensus" in exp_reject

def test_reporting_engine():
    engine = ReportingEngine()
    
    now_ms = time.time() * 1000
    event_mem = [
        {"timestamp": now_ms - 3000, "event_type": "CYBER_ATTACK", "details": "Intrusion at Bus 5", "severity": "HIGH"},
        {"timestamp": now_ms - 1000, "event_type": "RELAY_TRIP", "details": "L4_5 tripped", "severity": "CRITICAL"}
    ]
    
    # 1. Timeline reconstruction
    timeline = engine.reconstruct_timeline(event_mem)
    assert "KRONOLOGI" in timeline
    assert "Intrusion at Bus 5" in timeline
    
    # 2. Incident report
    grid_state = {
        "threat": {"threat_score": 45.0},
        "telemetry": {
            "state": {
                "buses": {
                    "Bus_5": {"voltage_pu": 0.85}
                }
            }
        },
        "defense": {
            "active_incidents": [
                {
                    "incident_id": "inc_100",
                    "affected_assets": ["Bus_5", "L4_5"],
                    "state": "CONTAINED",
                    "mitigation_action": "QUARANTINE_BREAKER",
                    "mitre_techniques": ["T0814"],
                    "attribution": {
                        "threat_actor": "APT-GRID-TAMPERER",
                        "confidence": 0.95
                    }
                }
            ]
        }
    }
    report = engine.generate_incident_report("inc_100", grid_state, event_mem)
    assert "inc_100" in report
    assert "APT-GRID-TAMPERER" in report
    assert "T0814" in report
    assert "Keberkesanan Respon" in report
    
    # 3. Daily summary
    daily = engine.generate_daily_summary(grid_state, event_mem)
    assert "OPERASI HARIAN" in daily
    assert "45.0%" in daily

def test_copilot_daemon_queries(temp_dir):
    # Setup test paths to avoid leaking files
    mem_path = os.path.join(temp_dir, "test_daemon_mem.json")
    vec_path = os.path.join(temp_dir, "test_daemon_vec.json")
    
    # Initialize Daemon with mocked client callbacks
    daemon = AssistantDaemon()
    daemon.client = MagicMock()
    daemon.memory_orch = MemoryOrchestrator(persistence_path=mem_path, enable_persistence=True)
    daemon.rag_engine.vector_db = NumpyVectorStore(persistence_path=vec_path, enable_persistence=True)
    
    daemon.grid_state["threat"] = {"threat_score": 10.0}
    daemon.memory_orch.add_event("FAULT", "Deviasi voltan pada Bus_5", "HIGH")
    
    # Mock respond method to capture answers
    daemon._respond = MagicMock()
    
    # 1. Test timeline query routing
    daemon.process_request("bina timeline peristiwa terkini", is_voice=False)
    daemon._respond.assert_called_once()
    args, kwargs = daemon._respond.call_args
    assert "KRONOLOGI PERISTIWA" in args[0]
    
    # 2. Test incident report query routing
    daemon._respond.reset_mock()
    daemon.process_request("sediakan laporan insiden 102", is_voice=False)
    args, kwargs = daemon._respond.call_args
    assert "LAPORAN INSIDEN KESELAMATAN" in args[0]
    assert "102" in args[0]
    
    # 3. Test daily summary query routing
    daemon._respond.reset_mock()
    daemon.process_request("buat daily summary operasi", is_voice=False)
    args, kwargs = daemon._respond.call_args
    assert "NARRATIVE RINGKASAN OPERASI" in args[0]
    
    # 4. Test explain isolation query routing
    daemon._respond.reset_mock()
    daemon.process_request("kenapa Bus 5 diasingkan?", is_voice=False)
    args, kwargs = daemon._respond.call_args
    assert "Sistem mengasingkan" in args[0] or "kuarantin" in args[0] or "nominal" in args[0]
