import os
import pytest
import shutil
import tempfile
from core.assistant.rag_engine import RAGEngine

@pytest.fixture
def temp_kb():
    # Setup temporary directory for knowledge base tests
    tmpdir = tempfile.mkdtemp()
    sops = os.path.join(tmpdir, "operator_sops")
    os.makedirs(sops)
    
    # Write a test file
    with open(os.path.join(sops, "test_sop.md"), "w", encoding="utf-8") as f:
        f.write(
            "# SOP Voltan Bus 5\n\n"
            "Sekiranya berlaku undervoltage pada Bus 5 di bawah 0.90 p.u., geganti ANSI 27 diaktifkan. "
            "Operator dikehendaki menutup tie-breaker L7_8 secara manual untuk reroute kuasa."
        )
    yield tmpdir
    shutil.rmtree(tmpdir)

def test_rag_engine_initialization(temp_kb):
    engine = RAGEngine(kb_path=temp_kb)
    assert engine.initialized is True
    assert len(engine.documents) == 1
    assert engine.documents[0]["title"] == "SOP Voltan Bus 5"
    assert "tiebreaker" in engine.vocabulary

def test_rag_engine_retrieval(temp_kb):
    engine = RAGEngine(kb_path=temp_kb)
    hits = engine.retrieve("bagaimana mengatasi undervoltage pada bus 5?", limit=1)
    assert len(hits) == 1
    assert hits[0]["doc"]["title"] == "SOP Voltan Bus 5"
    assert hits[0]["score"] > 0.0

def test_rag_engine_telemetry_grounding():
    engine = RAGEngine()
    telemetry = {
        "state": {
            "buses": {
                "Bus_1": {"voltage_pu": 1.01},
                "Bus_5": {"voltage_pu": 0.82}
            },
            "lines": {
                "L4_5": {"capacity_pct": 12.0, "breaker_closed": False}
            }
        }
    }
    threat = {
        "threat_score": 82.5,
        "severity": "CRITICAL"
    }
    
    ctx = engine.ground_telemetry(telemetry, threat)
    assert "Bus_5: 0.820 p.u." in ctx
    assert "KRITIKAL_UNDERVOLTAGE" in ctx
    assert "Threat Score: 82.5" in ctx

def test_rag_engine_handle_query(temp_kb):
    engine = RAGEngine(kb_path=temp_kb)
    telemetry = {
        "state": {
            "buses": {
                "Bus_5": {"voltage_pu": 0.82}
            },
            "lines": {}
        }
    }
    threat = {"threat_score": 45.0, "severity": "MEDIUM"}
    
    # Query matching RAG keywords
    res = engine.handle_query("Langkah pemulihan undervoltage Bus 5?", telemetry, threat)
    assert res is not None
    assert "response" in res
    assert "L7_8" in res["response"]
    assert "SOP Voltan Bus 5" in res["hits"][0]["title"]
    assert len(res["reasoning_logs"]) > 1

    # Query not matching RAG keywords should return None
    res_none = engine.handle_query("siapa khabar kamu hari ini?", telemetry, threat)
    assert res_none is None
