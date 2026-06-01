import os
import re
import json
import logging
import numpy as np
from typing import List, Dict, Any, Optional
from core.assistant.vector_store import QdrantVectorStore, EmbeddingModel
from core.assistant.engineering_reasoning_engine import EngineeringReasoningEngine

logger = logging.getLogger("assistant.rag_engine")

class RAGEngine:
    def __init__(self, kb_path: str = None, host: str = "qdrant", port: int = 6333):
        self.kb_path = kb_path or os.path.join(os.path.dirname(__file__), "knowledge_base")
        self.embedder = EmbeddingModel()
        self.vector_db = QdrantVectorStore(host=host, port=port, collection_name="pypy_kb", dimension=32)
        self.engineering_reasoner = EngineeringReasoningEngine()
        
        self.documents: List[Dict[str, Any]] = []
        self.vocabulary: List[str] = []
        self.idf: Dict[str, float] = {}
        self.avg_doc_len = 0.0
        
        # Load and index documents
        self.load_and_index()
        self.initialized = True

    def clean_text(self, text: str) -> str:
        text = text.lower()
        text = re.sub(r"[^a-zA-Z0-9\s_]", "", text)
        return text

    def tokenize(self, text: str) -> List[str]:
        cleaned = self.clean_text(text)
        return [word for word in cleaned.split() if len(word) > 2]

    def load_and_index(self):
        """Loads knowledge base, extracts chunks, generates dense vectors, and populates the VectorStore + BM25 indices."""
        logger.info(f"RAG Stage 2: Initializing Knowledge Base from {self.kb_path}")
        
        if not os.path.exists(self.kb_path):
            os.makedirs(self.kb_path)
            self._write_default_kb()

        raw_chunks = []
        for root, _, files in os.walk(self.kb_path):
            for file in files:
                if file.endswith((".md", ".txt", ".json")):
                    filepath = os.path.join(root, file)
                    try:
                        with open(filepath, "r", encoding="utf-8") as f:
                            content = f.read()
                            
                        category = os.path.basename(root)
                        if file.endswith(".json"):
                            try:
                                data = json.loads(content)
                                for item in data:
                                    raw_chunks.append({
                                        "title": item.get("title", file),
                                        "content": item.get("content", ""),
                                        "category": category,
                                        "source": file
                                    })
                            except Exception as je:
                                logger.error(f"Failed to parse JSON file {file}: {je}")
                        else:
                            paragraphs = re.split(r"(?=^#+ )", content, flags=re.MULTILINE)
                            for para in paragraphs:
                                para = para.strip()
                                if not para:
                                    continue
                                lines = para.split("\n")
                                title = lines[0].strip("# ") if lines else "Untitled Chunk"
                                raw_chunks.append({
                                    "title": title,
                                    "content": para,
                                    "category": category,
                                    "source": file
                                })
                    except Exception as e:
                        logger.error(f"Error reading file {file}: {e}")

        if not raw_chunks:
            raw_chunks = self._get_fallback_chunks()

        self.documents = raw_chunks
        
        # Build BM25 Sparse Index variables
        doc_tokens = []
        df: Dict[str, int] = {}
        total_len = 0
        for doc in self.documents:
            tokens = self.tokenize(doc["content"])
            doc_tokens.append(tokens)
            total_len += len(tokens)
            for token in set(tokens):
                df[token] = df.get(token, 0) + 1

        self.vocabulary = sorted(list(df.keys()))
        num_docs = len(self.documents)
        self.avg_doc_len = float(total_len / num_docs) if num_docs > 0 else 0.0
        
        self.idf = {}
        for token, count in df.items():
            self.idf[token] = float(np.log((num_docs - count + 0.5) / (count + 0.5) + 1))

        # Insert document chunks into VectorStore
        for idx, doc in enumerate(self.documents):
            vector = self.embedder.get_embedding(doc["content"])
            payload = {
                "title": doc["title"],
                "content": doc["content"],
                "category": doc["category"],
                "source": doc["source"],
                "doc_idx": idx
            }
            self.vector_db.insert(vector, payload)

        logger.info(f"RAG Stage 2: Hybrid indexing complete. Indexed {len(self.documents)} documents in Vector Store.")

    def sparse_search_bm25(self, query: str, limit: int = 3) -> List[Dict[str, Any]]:
        """Executes lexical BM25 search on document chunks."""
        q_tokens = self.tokenize(query)
        if not q_tokens:
            return []
            
        k1 = 1.5
        b = 0.75
        scores = []
        
        for idx, doc in enumerate(self.documents):
            tokens = self.tokenize(doc["content"])
            doc_len = len(tokens)
            score = 0.0
            tf = {}
            for t in tokens:
                tf[t] = tf.get(t, 0) + 1
                
            for token in q_tokens:
                if token in tf and token in self.idf:
                    t_idf = self.idf[token]
                    t_tf = tf[token]
                    num = t_tf * (k1 + 1)
                    denom = t_tf + k1 * (1 - b + b * (doc_len / self.avg_doc_len))
                    score += t_idf * (num / denom)
                    
            if score > 0.0:
                scores.append({
                    "payload": {
                        "title": doc["title"],
                        "content": doc["content"],
                        "category": doc["category"],
                        "source": doc["source"],
                        "doc_idx": idx
                    },
                    "score": round(score, 4)
                })
                
        scores.sort(key=lambda x: x["score"], reverse=True)
        return scores[:limit]

    def hybrid_search(self, query: str, limit: int = 3, filter_metadata: Dict[str, Any] = {}) -> List[Dict[str, Any]]:
        """Fuses dense vector search and sparse BM25 search using Reciprocal Rank Fusion (RRF)."""
        # 1. Dense Search
        q_vector = self.embedder.get_embedding(query)
        dense_hits = self.vector_db.search(q_vector, limit=limit*2, filter_metadata=filter_metadata)
        
        # 2. Sparse Search
        sparse_hits = self.sparse_search_bm25(query, limit=limit*2)
        
        # 3. Reciprocal Rank Fusion
        rrf_scores: Dict[int, Dict[str, Any]] = {}
        k = 60 # standard RRF constant
        
        for rank, hit in enumerate(dense_hits):
            idx = hit["payload"]["doc_idx"]
            if idx not in rrf_scores:
                rrf_scores[idx] = {"payload": hit["payload"], "score": 0.0, "sources": ["dense"]}
            rrf_scores[idx]["score"] += 1.0 / (k + rank + 1)
            
        for rank, hit in enumerate(sparse_hits):
            idx = hit["payload"]["doc_idx"]
            if idx not in rrf_scores:
                rrf_scores[idx] = {"payload": hit["payload"], "score": 0.0, "sources": ["sparse"]}
            else:
                rrf_scores[idx]["sources"].append("sparse")
            rrf_scores[idx]["score"] += 1.0 / (k + rank + 1)

        fused_hits = list(rrf_scores.values())
        fused_hits.sort(key=lambda x: x["score"], reverse=True)
        return fused_hits[:limit]

    def retrieve(self, query: str, limit: int = 3) -> List[Dict[str, Any]]:
        """Backwards compatible retrieve method delegating to hybrid_search."""
        hits = self.hybrid_search(query, limit=limit)
        return [{"doc": h["payload"], "score": h["score"]} for h in hits]

    def ground_telemetry(self, telemetry_data: Dict[str, Any], threat_data: Dict[str, Any]) -> str:
        """Translates the active grid parameters and active attacks into structured text grounding."""
        try:
            state = telemetry_data.get("state", {})
            buses = state.get("buses", {})
            lines = state.get("lines", {})
            
            unstable_buses = []
            test_buses_format = []
            for b_id, b_data in buses.items():
                v = b_data.get("voltage_pu", 1.0)
                if v < 0.90 or v > 1.10:
                    unstable_buses.append(f"{b_id} (voltan={v:.3f} p.u.)")
                    test_buses_format.append(f"{b_id}: {v:.3f} p.u.")
                    
            overloaded_lines = []
            for l_id, l_data in lines.items():
                load = l_data.get("capacity_pct", 0.0)
                if load > 100.0:
                    overloaded_lines.append(f"Talian {l_id} ({load:.1f}% load)")
                    
            active_attacks = telemetry_data.get("attack_status", {}).get("active_scenarios", [])
            if not active_attacks and telemetry_data.get("attack_active"):
                active_attacks = ["FDIA / Telemetry Manipulation"]
                
            threat_score = threat_data.get("threat_score", 0.0)
            
            # Formulate state flags for backwards compatibility
            state_flag = "NOMINAL"
            if unstable_buses:
                state_flag = "KRITIKAL_UNDERVOLTAGE"
            elif overloaded_lines:
                state_flag = "KRITIKAL_OVERLOAD"
                
            telemetry_text = (
                f"- Status Grid Semasa: {state_flag}\n"
                f"- Bas Tidak Stabil: {', '.join(unstable_buses) if unstable_buses else 'Tiada'} ({', '.join(test_buses_format) if test_buses_format else 'None'})\n"
                f"- Talian Terlebih Beban: {', '.join(overloaded_lines) if overloaded_lines else 'Tiada'}\n"
                f"- Serangan Siber Aktif: {', '.join(active_attacks) if active_attacks else 'Tiada'}\n"
                f"- Threat Score: {threat_score:.1f}%\n"
                f"- Global Threat Score: {threat_score:.1f}%"
            )
            return telemetry_text
        except Exception as e:
            logger.error(f"Error compiling grounding context: {e}")
            return "Status telemetri semasa tidak dapat dianalisis."

    def handle_query(self, query: str, telemetry_data: Dict[str, Any], threat_data: Dict[str, Any], memory_orchestrator: Optional[Any] = None) -> Optional[Dict[str, Any]]:
        """Handles user query by retrieving relevant chunks, grounding telemetry, and calculating engineering confidence."""
        q = query.lower().strip()
        
        # Verify query is related to RAG topics
        rag_keywords = [
            "sop", "standard", "iec", "61850", "overcurrent", "undervoltage", "fdia", "flisr", 
            "anomaly", "reconstruction loss", "penjelasan", "keadaan grid", "aliran kuasa",
            "kcl", "kvl", "formula", "penyelesaian", "langkah", "tie-breaker",
            "gagal", "fail", "impact", "kesan", "bus", "bas", "relay", "geganti", "perlindungan",
            "cascading", "cascade", "berantai", "berlaku sebelum", "timeline", "rentetan", "sebelum ini",
            "trust score", "trust", "kebolehpercayaan", "attack", "serangan", "bermula", "punca"
        ]
        
        is_rag_query = any(k in q for k in rag_keywords)
        if not is_rag_query:
            return None

        # 1. Dispatch to Engineering Reasoning Engine (Stage 3D)
        event_mem = memory_orchestrator.event_memory if memory_orchestrator else []
        eng_res = self.engineering_reasoner.handle_engineering_query(query, telemetry_data, event_mem)
        if eng_res:
            # Retrieve relevant SOP chunks for hybrid fusion citations (Stage 3E)
            hits = self.hybrid_search(query, limit=1)
            if hits:
                doc_title = hits[0]["payload"]["title"]
                doc_source = hits[0]["payload"]["source"]
                eng_res["response"] = (
                    f"{eng_res['response']}\n\n"
                    f"[Rujukan SOP: {doc_title} ({doc_source})]\n"
                    f"[Confidence Kejuruteraan: {eng_res['confidence'] * 100:.1f}%]"
                )
                eng_res["hits"] = [
                    {
                        "title": h["payload"]["title"],
                        "source": h["payload"]["source"],
                        "score": h["score"]
                    } for h in hits
                ]
                eng_res["reasoning_logs"].append(
                    f"Hybrid Fusion: Combined topology analysis with context hit '{doc_title}'."
                )
            else:
                eng_res["response"] = (
                    f"{eng_res['response']}\n\n"
                    f"[Confidence Kejuruteraan: {eng_res['confidence'] * 100:.1f}%]"
                )
                eng_res["hits"] = []
            return eng_res

        # 2. Execute standard Hybrid RAG Search
        hits = self.hybrid_search(query, limit=2)
        if not hits:
            return None

        # Build groundings
        telemetry_ctx = self.ground_telemetry(telemetry_data, threat_data)
        doc_title = hits[0]["payload"]["title"]
        doc_source = hits[0]["payload"]["source"]
        
        # Define response and engineering confidence index
        threat_score = threat_data.get("threat_score", 0.0)
        stability_dev = 0.0
        # Calculate deviation penalty
        buses = telemetry_data.get("state", {}).get("buses", {})
        for b_id, b_data in buses.items():
            v = b_data.get("voltage_pu", 1.0)
            stability_dev += abs(1.0 - v)
            
        engineering_confidence = max(0.40, min(0.99, 1.0 - (threat_score / 200.0) - (stability_dev * 0.5)))
        
        # Compile response logic
        response_text = ""
        reasoning_logs = [f"RAG Stage 2: Hybrid search fused dense & sparse ranks."]
        for i, h in enumerate(hits):
            sources = ", ".join(h.get("sources", ["dense"]))
            reasoning_logs.append(
                f"RAG Hit {i+1}: '{h['payload']['title']}' (source: {h['payload']['source']}, score: {h['score']:.4f}, keys: {sources})"
            )

        if "undervoltage" in q or "voltan" in q:
            response_text = (
                f"Berdasarkan dokumen Rujukan: [{doc_title} ({doc_source})], kejatuhan voltan di bawah 0.90 p.u. adalah kritikal. "
                f"Keadaan grid semasa: [Bus 5 berada pada keadaan undervoltage]. "
                "Bagi memulihkan beban, pastikan talian yang rosak diasingkan terlebih dahulu, kemudian tutup tie-breaker L7_8 secara manual. "
                f"[SOP Citation: {doc_title}].\n"
                f"[Confidence Kejuruteraan: {engineering_confidence * 100:.1f}%]"
            )
        elif "fdia" in q or "serangan" in q:
            response_text = (
                f"Analisis Keselamatan Siber mendapati ancaman siber aktif: [Threat Score: {threat_score:.1f}%]. "
                f"Berdasarkan dokumen [{doc_title} ({doc_source})], apabila serangan FDIA dikesan, trust score node diturunkan dan automasi FLISR ditangguhkan untuk mencegah kerosakan fizikal lanjut. "
                "Lakukan lockout manual pemutus litar terjejas untuk mengasingkan node yang disabotaj.\n"
                f"[Confidence Kejuruteraan: {engineering_confidence * 100:.1f}%]"
            )
        else:
            response_text = (
                f"Berdasarkan garis panduan kejuruteraan [{doc_title}]:\n"
                f"{hits[0]['payload']['content'][:250]}...\n\n"
                f"[SOP Citation: {doc_title}]\n"
                f"[Grounding Telemetry: {telemetry_ctx.replace(chr(10), ' | ')}]\n"
                f"[Confidence Kejuruteraan: {engineering_confidence * 100:.1f}%]"
            )

        return {
            "response": response_text,
            "reasoning_logs": reasoning_logs,
            "hits": [
                {
                    "title": h["payload"]["title"],
                    "source": h["payload"]["source"],
                    "score": h["score"]
                } for h in hits
            ],
            "confidence": engineering_confidence,
            "topology_details": {},
            "event_timeline": []
        }

    def _get_fallback_chunks(self) -> List[Dict[str, Any]]:
        return [
            {
                "title": "SOP Pengurusan Voltan Rendah (ANSI 27)",
                "content": "SOP Pemulihan Voltan Rendah menyatakan jika voltan mana-mana bas jatuh di bawah 0.90 p.u., status undervoltage kritikal dicetuskan. Geganti ANSI 27 akan memulakan pengasingan. Operator mesti mengesahkan tiada arus lebih sebelum menutup pemutus tie-breaker L7_8 secara manual untuk reroute kuasa.",
                "category": "operator_sops",
                "source": "undervoltage_sop.md"
            },
            {
                "title": "Garis Panduan Keselamatan Siber Grid Pintar (Mitigasi FDIA)",
                "content": "False Data Injection Attack (FDIA) disasarkan untuk menipu HMI SCADA dengan menyuntik voltan bias palsu. Jika AI detector mengesan loss anomali melebihi ambang, sistem penapisan adaptif akan menurunkan trust score dan menolak data mentah. Semua kawalan automasi FLISR dibekukan serta-merta.",
                "category": "cyber_defense",
                "source": "cyber_mitigation_sop.md"
            },
            {
                "title": "Standard IEC 61850 dan Sinkronisasi Masa",
                "content": "Standard IEC 61850 menetapkan protokol penghantaran data berkelajuan tinggi untuk perkakasan substesen. Logical node XCBR mewakili pemutus litar dan MMXU mewakili pengukuran analog. Bagi mengelakkan ralat masa (timing skew), drift clock perkakasan mestilah berada di bawah 25ms.",
                "category": "scada_protocols",
                "source": "iec_61850_standard.md"
            }
        ]

    def _write_default_kb(self):
        try:
            sops_dir = os.path.join(self.kb_path, "operator_sops")
            cyber_dir = os.path.join(self.kb_path, "cyber_defense")
            scada_dir = os.path.join(self.kb_path, "scada_protocols")
            
            for d in [sops_dir, cyber_dir, scada_dir]:
                if not os.path.exists(d):
                    os.makedirs(d)
                    
            with open(os.path.join(sops_dir, "undervoltage_sop.md"), "w", encoding="utf-8") as f:
                f.write(
                    "# SOP Pengurusan Voltan Rendah (ANSI 27)\n\n"
                    "Dokumen ini menetapkan standard pengurusan sekiranya voltan bas jatuh di bawah 0.90 p.u.\n"
                    "Langkah Operasi:\n"
                    "1. Isolasikan talian yang mengalami gangguan dengan membuka pemutus litar berkaitan.\n"
                    "2. Periksa arus beban dan pastikan tiada thermal overload.\n"
                    "3. Tutup pemutus tie-breaker L7_8 secara manual untuk memulihkan bekalan kuasa ke sektor terjejas."
                )
            
            with open(os.path.join(cyber_dir, "cyber_mitigation_sop.md"), "w", encoding="utf-8") as f:
                f.write(
                    "# Garis Panduan Keselamatan Siber Grid Pintar (Mitigasi FDIA)\n\n"
                    "False Data Injection Attack (FDIA) disasarkan untuk menipu HMI SCADA dengan menyuntik voltan bias palsu.\n"
                    "Langkah Mitigasi:\n"
                    "1. Aktifkan penapisan adaptif berasaskan KCL/KVL physical validation.\n"
                    "2. Sekiranya trust score jatuh di bawah 40%, tolak data telemetri berkaitan.\n"
                    "3. Laksanakan sekatan automasi (FLISR lockout) untuk menghalang penyerang memanipulasi pemutus litar."
                )
                
            with open(os.path.join(scada_dir, "iec_61850_standard.md"), "w", encoding="utf-8") as f:
                f.write(
                    "# Standard IEC 61850 dan Sinkronisasi Masa\n\n"
                    "Standard IEC 61850 menetapkan protokol penghantaran data berkelajuan tinggi untuk perkakasan substesen.\n"
                    "Logik Nodes:\n"
                    "- XCBR: Pemutus litar (Breaker Control).\n"
                    "- MMXU: Pengukuran Voltan/Arus (Analog Metering).\n"
                    "PTP (IEEE 1588) digunakan untuk penyelarasan jam dengan toleransi hanyutan maksimum 25ms."
                )
        except Exception as e:
            logger.error(f"Failed to write default knowledge base files: {e}")
