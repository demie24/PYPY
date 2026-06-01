import os
import pytest
import shutil
import tempfile
import numpy as np
from core.assistant.vector_store import EmbeddingModel, NumpyVectorStore, QdrantVectorStore
from core.assistant.rag_engine import RAGEngine
from core.assistant.memory_orchestrator import MemoryOrchestrator

@pytest.fixture
def temp_kb():
    tmpdir = tempfile.mkdtemp()
    sops = os.path.join(tmpdir, "operator_sops")
    os.makedirs(sops)
    with open(os.path.join(sops, "test_sop.md"), "w", encoding="utf-8") as f:
        f.write(
            "# SOP Voltan Bus 5\n\n"
            "Sekiranya berlaku undervoltage pada Bus 5 di bawah 0.90 p.u., geganti ANSI 27 diaktifkan. "
            "Operator dikehendaki menutup tie-breaker L7_8 secara manual untuk reroute kuasa."
        )
    yield tmpdir
    shutil.rmtree(tmpdir)

def test_embedding_model_vectors():
    embedder = EmbeddingModel()
    vec = embedder.get_embedding("voltan drop pada bus 5 undervoltage")
    assert len(vec) == 32
    # Check that vector is normalized
    norm = np.linalg.norm(vec)
    assert np.isclose(norm, 1.0) or np.isclose(norm, 0.0)

def test_vector_store_operations():
    store = NumpyVectorStore()
    v1 = [1.0] + [0.0]*31
    v2 = [0.0, 1.0] + [0.0]*30
    
    store.insert(v1, {"id": 1, "category": "A"})
    store.insert(v2, {"id": 2, "category": "B"})
    
    hits_a = store.search(v1, limit=1, filter_metadata={"category": "A"})
    assert len(hits_a) == 1
    assert hits_a[0]["payload"]["id"] == 1
    
    hits_all = store.search(v1, limit=2)
    assert len(hits_all) == 2
    assert hits_all[0]["score"] == 1.0
    assert hits_all[1]["score"] == 0.0

def test_qdrant_vector_store_fallback():
    # If qdrant container is not running, it must automatically fall back to NumpyVectorStore
    store = QdrantVectorStore(host="non_existent_host", port=1234)
    assert store.qdrant_available is False
    assert store.fallback_store is not None
    
    # Test fallback operations
    vec = [0.1] * 32
    assert store.insert(vec, {"test": "data"}) is True
    hits = store.search(vec, limit=1)
    assert len(hits) == 1
    assert hits[0]["payload"]["test"] == "data"

def test_rag_engine_hybrid_search(temp_kb):
    engine = RAGEngine(kb_path=temp_kb)
    # Check BM25 search
    sparse_hits = engine.sparse_search_bm25("voltan bus 5", limit=1)
    assert len(sparse_hits) == 1
    assert sparse_hits[0]["payload"]["title"] == "SOP Voltan Bus 5"
    
    # Check Hybrid Search
    hybrid_hits = engine.hybrid_search("undervoltage tie-breaker", limit=1)
    assert len(hybrid_hits) == 1
    assert hybrid_hits[0]["payload"]["title"] == "SOP Voltan Bus 5"

def test_memory_orchestrator_stage2():
    mem = MemoryOrchestrator(limit=5)
    
    # Test event memory
    mem.add_event("RELAY_TRIP", "Breaker L4_5 open due to overcurrent", "CRITICAL")
    assert len(mem.event_memory) == 1
    assert mem.event_memory[0]["event_type"] == "RELAY_TRIP"
    
    # Test caching
    dummy_hits = [{"title": "Cached Chunk", "score": 0.95}]
    mem.cache_retrieval("L4_5 fault", dummy_hits)
    cached = mem.get_cached_retrieval("L4_5 fault")
    assert cached == dummy_hits
    
    # Test semantic memory recall
    mem.add_semantic_memory("bagaimana atasi undervoltage bus 5?", "tutup tie-breaker L7_8 secara manual")
    insight = mem.recall_semantic_memory("apa tindakan voltan rendah bas 5?")
    assert insight == "tutup tie-breaker L7_8 secara manual"
    
    # Query with no relevance should recall nothing
    insight_none = mem.recall_semantic_memory("siapa buat sistem ini?")
    assert insight_none is None
