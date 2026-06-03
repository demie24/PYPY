import os
import json
import logging
import urllib.request
import urllib.error
import re
import numpy as np
from typing import List, Dict, Any, Optional

logger = logging.getLogger("assistant.vector_store")

def deterministic_hash(s: str) -> int:
    """Computes a deterministic FNV-1a rolling hash to replace volatile python hash()."""
    h = 2166136261
    for char in s:
        h = (h ^ ord(char)) * 16777619
        h &= 0xffffffff
    return h

class EmbeddingModel:
    def __init__(self, dimension: int = 32):
        self.dimension = dimension
        self.concept_map = {
            # Voltage / Voltan / Undervoltage / Overvoltage / Voltan Rendah
            "voltan": 0, "voltage": 0, "undervoltage": 0, "overvoltage": 0, "rendah": 0, "tinggi": 0, "pu": 0,
            # Breaker / Pemutus / Switch / Tie-breaker
            "breaker": 1, "pemutus": 1, "switch": 1, "tiebreaker": 1, "tie-breaker": 1,
            # Relay / Geganti
            "relay": 2, "geganti": 2,
            # Trip / Open / Closed / Trigger / Tutup
            "trip": 3, "open": 3, "closed": 3, "tutup": 3, "buka": 3, "diaktifkan": 3,
            # Cyberattack / Attack / FDIA / Serangan / Cyber
            "attack": 4, "serangan": 4, "fdia": 4, "cyber": 4, "pencerobohan": 4,
            # Anomaly / Anomali / Fault / Abnormal / Rosak / Gangguan
            "anomaly": 5, "anomali": 5, "fault": 5, "abnormal": 5, "masalah": 5, "failure": 5, "rosak": 5, "gangguan": 5,
            # IEC 61850 / SCADA / Telemetry / Telemetri / HMI
            "iec": 6, "61850": 6, "scada": 6, "telemetry": 6, "telemetri": 6, "hmi": 6,
            # FLISR / Recovery / Pemulihan / Restore
            "flisr": 7, "recovery": 7, "pemulihan": 7, "restore": 7, "selamat": 7,
            # Overload / Cascade / Beban / Melampau
            "overload": 8, "beban": 8, "cascade": 8, "limpahan": 8,
            # Sync / PTP / Drift / Skew / Time
            "sync": 9, "ptp": 9, "drift": 9, "skew": 9, "time": 9, "masa": 9,
            # Stability / Unstable / Oscillation / Ayunan
            "unstable": 10, "oscillation": 10, "stabil": 10, "ayunan": 10,
            # Bus / Bas / Nodes
            "bus": 11, "bas": 11, "node": 11, "nodes": 11,
            # Actions / Bagaimana / Atasi / Tindakan / Cara / Langkah / Reroute
            "bagaimana": 12, "atasi": 12, "tindakan": 12, "cara": 12, "langkah": 12, "resolusi": 12, "reroute": 12,
            # Numbers
            "5": 13, "four": 14, "4": 14, "seven": 15, "7": 15, "eight": 16, "8": 16
        }
        self.vocabulary = list(self.concept_map.keys())

    def clean_text(self, text: str) -> str:
        text = text.lower()
        return re.sub(r"[^a-zA-Z0-9\s_]", "", text)

    def get_embedding(self, text: str) -> List[float]:
        """Generates a deterministic vector representation of text based on concept mapping and FNV-1a hashing."""
        words = self.clean_text(text).split()
        vector = np.zeros(self.dimension)
        
        for word in words:
            if word in self.concept_map:
                idx = self.concept_map[word] % self.dimension
                vector[idx] += 1.0
            # Handle character n-grams with deterministic hash for out-of-vocab robustness
            for i in range(len(word) - 2):
                tri = word[i:i+3]
                h_idx = deterministic_hash(tri) % self.dimension
                vector[h_idx] += 0.05
                
        # Normalize vector
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
        return vector.tolist()

class VectorStore:
    def search(self, query_vector: List[float], limit: int = 3, filter_metadata: Dict[str, Any] = {}) -> List[Dict[str, Any]]:
        raise NotImplementedError

    def insert(self, vector: List[float], payload: Dict[str, Any]) -> bool:
        raise NotImplementedError

class NumpyVectorStore(VectorStore):
    def __init__(self, persistence_path: Optional[str] = None, enable_persistence: Optional[bool] = None):
        self.entries: List[Dict[str, Any]] = []
        self.persistence_path = persistence_path or os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "persistence", "numpy_vector_store.json"
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
                    self.entries = json.load(f)
                logger.info(f"Loaded {len(self.entries)} vector entries from disk: {self.persistence_path}")
            except Exception as e:
                logger.error(f"Failed to load vector store from disk: {e}")

    def save_to_disk(self):
        if self.enable_persistence:
            try:
                os.makedirs(os.path.dirname(self.persistence_path), exist_ok=True)
                with open(self.persistence_path, "w", encoding="utf-8") as f:
                    json.dump(self.entries, f, indent=2)
            except Exception as e:
                logger.error(f"Failed to save vector store to disk: {e}")

    def search(self, query_vector: List[float], limit: int = 3, filter_metadata: Dict[str, Any] = {}) -> List[Dict[str, Any]]:
        if not self.entries:
            return []
            
        q_vec = np.array(query_vector)
        results = []
        
        for entry in self.entries:
            payload = entry.get("payload", {})
            match = True
            for k, v in filter_metadata.items():
                if payload.get(k) != v:
                    match = False
                    break
            if not match:
                continue
                
            e_vec = np.array(entry["vector"])
            q_norm = np.linalg.norm(q_vec)
            e_norm = np.linalg.norm(e_vec)
            if q_norm > 0 and e_norm > 0:
                score = float(np.dot(q_vec, e_vec) / (q_norm * e_norm))
            else:
                score = 0.0
                
            results.append({
                "payload": payload,
                "score": round(score, 4)
            })
            
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]

    def insert(self, vector: List[float], payload: Dict[str, Any]) -> bool:
        self.entries.append({
            "vector": vector,
            "payload": payload
        })
        self.save_to_disk()
        return True

class QdrantVectorStore(VectorStore):
    def __init__(self, host: str = "qdrant", port: int = 6333, collection_name: str = "pypy_kb", dimension: int = 32, persistence_path: Optional[str] = None, enable_persistence: Optional[bool] = None):
        self.url = f"http://{host}:{port}/collections/{collection_name}"
        self.collection_name = collection_name
        self.dimension = dimension
        self.fallback_store: Optional[NumpyVectorStore] = None
        self.qdrant_available = False
        self.persistence_path = persistence_path
        
        if enable_persistence is None:
            enable_persistence = "PYTEST_CURRENT_TEST" not in os.environ
        self.enable_persistence = enable_persistence
        
        self.init_collection()

    def init_collection(self):
        try:
            req = urllib.request.Request(self.url, method="GET")
            with urllib.request.urlopen(req, timeout=1.0) as res:
                if res.status == 200:
                    self.qdrant_available = True
                    logger.info("Connected to Qdrant service successfully.")
        except Exception as e:
            logger.warning(f"Qdrant service not available at {self.url}: {e}. Falling back to NumpyVectorStore.")
            self.fallback_store = NumpyVectorStore(persistence_path=self.persistence_path, enable_persistence=self.enable_persistence)
            self.qdrant_available = False

    def search(self, query_vector: List[float], limit: int = 3, filter_metadata: Dict[str, Any] = {}) -> List[Dict[str, Any]]:
        if not self.qdrant_available or self.fallback_store is not None:
            return self.fallback_store.search(query_vector, limit, filter_metadata)
            
        try:
            search_url = f"{self.url}/points/search"
            filter_must = []
            for k, v in filter_metadata.items():
                filter_must.append({"key": k, "match": {"value": v}})
                
            payload = {
                "vector": query_vector,
                "limit": limit,
                "with_payload": True
            }
            if filter_must:
                payload["filter"] = {"must": filter_must}
                
            req = urllib.request.Request(
                search_url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=1.5) as res:
                response = json.loads(res.read().decode("utf-8"))
                hits = response.get("result", [])
                return [
                    {
                        "payload": h.get("payload", {}),
                        "score": round(h.get("score", 0.0), 4)
                    } for h in hits
                ]
        except Exception as e:
            logger.error(f"Qdrant search failed: {e}. Executing Numpy fallback search.")
            if self.fallback_store is None:
                self.fallback_store = NumpyVectorStore(persistence_path=self.persistence_path, enable_persistence=self.enable_persistence)
            return self.fallback_store.search(query_vector, limit, filter_metadata)

    def insert(self, vector: List[float], payload: Dict[str, Any]) -> bool:
        if not self.qdrant_available or self.fallback_store is not None:
            return self.fallback_store.insert(vector, payload)
            
        try:
            point_id = hash(json.dumps(payload)) & 0xffffffffffffffff
            points_url = f"{self.url}/points?wait=true"
            body = {
                "points": [
                    {
                        "id": point_id,
                        "vector": vector,
                        "payload": payload
                    }
                ]
            }
            req = urllib.request.Request(
                points_url,
                data=json.dumps(body).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="PUT"
            )
            with urllib.request.urlopen(req, timeout=1.5) as res:
                return res.status == 200
        except Exception as e:
            logger.error(f"Qdrant insert failed: {e}. Executing Numpy fallback insert.")
            if self.fallback_store is None:
                self.fallback_store = NumpyVectorStore(persistence_path=self.persistence_path, enable_persistence=self.enable_persistence)
            return self.fallback_store.insert(vector, payload)
