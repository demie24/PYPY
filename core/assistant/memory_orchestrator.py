import time
import os
import json
import numpy as np
from typing import Dict, Any, List, Optional
from core.assistant.vector_store import EmbeddingModel

class MemoryOrchestrator:
    def __init__(self, limit: int = 10, persistence_path: Optional[str] = None, enable_persistence: Optional[bool] = None):
        self.limit = limit
        self.interactions: List[Dict[str, Any]] = []
        self.user_preferences: Dict[str, Any] = {
            "name": "Operator",
            "language": "ms",  # Malay
            "tone": "casual"
        }
        self.command_history: List[str] = []
        
        # Phase 9.10 Stage 2 memory categories
        self.semantic_memory: Dict[str, str] = {} # query -> key insights
        self.event_memory: List[Dict[str, Any]] = [] # system event logs
        self.retrieval_cache: Dict[str, Any] = {} # query -> RAG results
        self.embedder = EmbeddingModel()
        self.max_events = 30
        
        self.persistence_path = persistence_path or os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "persistence", "memory_orchestrator.json"
        )
        
        if enable_persistence is None:
            enable_persistence = "PYTEST_CURRENT_TEST" not in os.environ
        self.enable_persistence = enable_persistence
        
        if self.enable_persistence:
            self.load_from_disk()
            
    def load_from_disk(self):
        if os.path.exists(self.persistence_path):
            try:
                with open(self.persistence_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.interactions = data.get("interactions", [])
                self.user_preferences = data.get("user_preferences", self.user_preferences)
                self.command_history = data.get("command_history", [])
                self.semantic_memory = data.get("semantic_memory", {})
                self.event_memory = data.get("event_memory", [])
                self.retrieval_cache = data.get("retrieval_cache", {})
            except Exception:
                pass

    def save_to_disk(self):
        if self.enable_persistence:
            try:
                os.makedirs(os.path.dirname(self.persistence_path), exist_ok=True)
                data = {
                    "interactions": self.interactions,
                    "user_preferences": self.user_preferences,
                    "command_history": self.command_history,
                    "semantic_memory": self.semantic_memory,
                    "event_memory": self.event_memory,
                    "retrieval_cache": self.retrieval_cache
                }
                with open(self.persistence_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
            except Exception:
                pass
        
    def add_interaction(self, role: str, text: str):
        """Appends interaction to short-term memory buffer. Summarizes if limits exceeded."""
        self.interactions.append({
            "role": role,
            "text": text
        })
        if len(self.interactions) > self.limit:
            self.summarize_memory()
        self.save_to_disk()
            
    def record_command(self, command_name: str):
        """Logs executed actions to history queue."""
        self.command_history.append(command_name)
        if len(self.command_history) > 10:
            self.command_history.pop(0)
        self.save_to_disk()
            
    def summarize_memory(self):
        """Consolidates old messages in interactions to a summary string to keep buffer short."""
        if len(self.interactions) < 4:
            return
        old_items = self.interactions[:4]
        summary_lines = []
        for item in old_items:
            summary_lines.append(f"{item['role']}: {item['text']}")
        
        summary_text = "Previously: " + " | ".join(summary_lines)
        self.interactions = [{"role": "system_summary", "text": summary_text}] + self.interactions[4:]
        self.save_to_disk()
        
    def set_user_preference(self, key: str, value: Any):
        """Updates user preferences cache."""
        self.user_preferences[key] = value
        self.save_to_disk()

    def clear_memory(self):
        """Clears all interaction, command, and retrieval memory databases."""
        self.interactions = []
        self.command_history = []
        self.semantic_memory = {}
        self.event_memory = []
        self.retrieval_cache = {}
        self.save_to_disk()

    def get_memory_summary(self) -> Dict[str, Any]:
        """Returns serialized representation of memory including evolved categories."""
        return {
            "interactions": self.interactions,
            "user_preferences": self.user_preferences,
            "command_history": self.command_history,
            "event_memory_count": len(self.event_memory),
            "semantic_memory_keys": list(self.semantic_memory.keys()),
            "retrieval_cache_count": len(self.retrieval_cache)
        }

    # Evolved Memory Methods (Stage 2F)
    def add_event(self, event_type: str, details: str, severity: str = "INFO"):
        """Logs real-time grid faults, relay trips, or cyber threats statefully."""
        self.event_memory.append({
            "timestamp": int(time.time() * 1000),
            "event_type": event_type,
            "details": details,
            "severity": severity
        })
        if len(self.event_memory) > self.max_events:
            self.event_memory.pop(0)
        self.save_to_disk()

    def cache_retrieval(self, query: str, hits: List[Dict[str, Any]]):
        """Stores query search results to cache."""
        self.retrieval_cache[query.strip().lower()] = {
            "timestamp": time.time(),
            "hits": hits
        }
        self.save_to_disk()

    def get_cached_retrieval(self, query: str) -> Optional[List[Dict[str, Any]]]:
        """Fetches query RAG result from cache if fresh (TTL: 60 seconds)."""
        key = query.strip().lower()
        if key in self.retrieval_cache:
            cache_entry = self.retrieval_cache[key]
            if time.time() - cache_entry["timestamp"] < 60.0:
                return cache_entry["hits"]
        return None

    def add_semantic_memory(self, query: str, insight: str):
        """Records long-term key insights from operator questions."""
        self.semantic_memory[query.strip().lower()] = insight
        self.save_to_disk()

    def recall_semantic_memory(self, query: str) -> Optional[str]:
        """Recalls insights from memory using cosine similarity overlap on embeddings."""
        if not self.semantic_memory:
            return None
            
        q_vec = np.array(self.embedder.get_embedding(query))
        best_match = None
        best_score = 0.0
        
        for remembered_query, insight in self.semantic_memory.items():
            r_vec = np.array(self.embedder.get_embedding(remembered_query))
            q_norm = np.linalg.norm(q_vec)
            r_norm = np.linalg.norm(r_vec)
            if q_norm > 0 and r_norm > 0:
                score = float(np.dot(q_vec, r_vec) / (q_norm * r_norm))
            else:
                score = 0.0
                
            if score > best_score:
                best_score = score
                best_match = insight
                
        if best_score > 0.70: # semantic relevance recall threshold
            return best_match
        return None
