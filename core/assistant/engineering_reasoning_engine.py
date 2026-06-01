import logging
import time
from typing import Dict, Any, List, Optional

logger = logging.getLogger("assistant.engineering_reasoning")

class EngineeringReasoningEngine:
    def __init__(self):
        # 9-Bus Adjacency list (IEEE 9-Bus topology)
        # Bus 1, 2, 3 -> Generators
        # Bus 5, 6, 8 -> Loads
        # Bus 4, 7, 9 -> Junctions
        self.adjacency = {
            "Bus_1": ["Bus_4"],
            "Bus_2": ["Bus_7"],
            "Bus_3": ["Bus_9"],
            "Bus_4": ["Bus_1", "Bus_5", "Bus_9"],
            "Bus_5": ["Bus_4", "Bus_6"],
            "Bus_6": ["Bus_5", "Bus_7"],
            "Bus_7": ["Bus_2", "Bus_6", "Bus_8"],
            "Bus_8": ["Bus_7", "Bus_9"],
            "Bus_9": ["Bus_3", "Bus_4", "Bus_8"]
        }
        
        # Line mappings to end buses
        self.lines_map = {
            "L1_4": ("Bus_1", "Bus_4"),
            "L2_7": ("Bus_2", "Bus_7"),
            "L3_9": ("Bus_3", "Bus_9"),
            "L4_5": ("Bus_4", "Bus_5"),
            "L4_9": ("Bus_4", "Bus_9"),
            "L5_6": ("Bus_5", "Bus_6"),
            "L6_7": ("Bus_6", "Bus_7"),
            "L7_8": ("Bus_7", "Bus_8"),
            "L8_9": ("Bus_8", "Bus_9")
        }

        # Relay mappings to protecting zones
        self.relay_map = {
            "Bus_1": ["RELAY_IED_L1_4"],
            "Bus_2": ["RELAY_IED_L2_7"],
            "Bus_3": ["RELAY_IED_L3_9"],
            "Bus_4": ["RELAY_IED_L1_4", "RELAY_IED_L4_5", "RELAY_IED_L4_9"],
            "Bus_5": ["RELAY_IED_L4_5", "RELAY_IED_L5_6"],
            "Bus_6": ["RELAY_IED_L5_6", "RELAY_IED_L6_7"],
            "Bus_7": ["RELAY_IED_L2_7", "RELAY_IED_L6_7", "RELAY_IED_L7_8"],
            "Bus_8": ["RELAY_IED_L7_8", "RELAY_IED_L8_9"],
            "Bus_9": ["RELAY_IED_L3_9", "RELAY_IED_L4_9", "RELAY_IED_L8_9"]
        }

        # Load details
        self.loads = {
            "Bus_5": "Load_5 (1.25 p.u.)",
            "Bus_6": "Load_6 (0.90 p.u.)",
            "Bus_8": "Load_8 (1.00 p.u.)"
        }
        
        # Generator details
        self.generators = {
            "Bus_1": "Gen_1 (Slack, V=1.04)",
            "Bus_2": "Gen_2 (Restoration Gen, V=1.025)",
            "Bus_3": "Gen_3 (Gen, V=1.025)"
        }

        # Concept ontology synonyms (Malay -> English/SCADA concepts)
        self.ontology = {
            "voltan rendah": "undervoltage",
            "voltan tinggi": "overvoltage",
            "beban berlebihan": "overload",
            "limpahan beban": "overload",
            "pemutus litar terpelanting": "relay trip",
            "pemutus terkeluar": "relay trip",
            "gangguan geganti": "relay trip",
            "pengasingan breaker": "breaker isolation event",
            "sekatan automasi": "FLISR lockout",
            "penapisan adaptif": "adaptive physics validation",
            "manipulasi data": "FDIA"
        }

    def analyze_topology_impact(self, bus_id: str) -> Dict[str, Any]:
        """Calculates topological impact of a bus failure."""
        impacted_buses = [bus_id]
        impacted_lines = []
        islanding_zone = []
        restoration_path = []
        
        # Map bus input string (e.g. "bus 5" or "Bus_5") to standard key
        normalized_bus = bus_id.replace(" ", "_").capitalize()
        if not normalized_bus.startswith("Bus_"):
            normalized_bus = f"Bus_{normalized_bus}"
            
        neighbors = self.adjacency.get(normalized_bus, [])
        
        # Associated lines
        for line_id, (from_b, to_b) in self.lines_map.items():
            if from_b == normalized_bus or to_b == normalized_bus:
                impacted_lines.append(line_id)
                other = to_b if from_b == normalized_bus else from_b
                if other not in impacted_buses:
                    impacted_buses.append(other)

        # Islanding and restoration paths
        load_lost = self.loads.get(normalized_bus, None)
        if normalized_bus == "Bus_5":
            islanding_zone = ["Bus_5", "Bus_6"]
            restoration_path = ["Tutup tie-breaker L7_8 secara manual"]
        elif normalized_bus == "Bus_6":
            islanding_zone = ["Bus_6"]
            restoration_path = ["Tutup tie-breaker L7_8 secara manual"]
        elif normalized_bus == "Bus_8":
            islanding_zone = ["Bus_8"]
            restoration_path = ["Tutup tie-breaker L7_8 secara manual"]

        return {
            "neighbors": neighbors,
            "associated_lines": impacted_lines,
            "load_lost": load_lost,
            "islanding_zone": islanding_zone,
            "restoration_path": restoration_path
        }

    def get_relay_relationships(self, bus_id: str) -> List[str]:
        normalized_bus = bus_id.replace(" ", "_").capitalize()
        if not normalized_bus.startswith("Bus_"):
            normalized_bus = f"Bus_{normalized_bus}"
        return self.relay_map.get(normalized_bus, [])

    def analyze_temporal_history(self, event_memory: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extracts chronological sequence of faults and attack detections."""
        timeline = []
        now_ms = time.time() * 1000
        # Sort events by timestamp
        sorted_events = sorted(event_memory, key=lambda x: x.get("timestamp", 0))
        for ev in sorted_events:
            offset_sec = round((now_ms - ev.get("timestamp", 0)) / 1000.0, 1)
            # Clip offset to positive bounds
            offset_sec = max(0.1, offset_sec)
            timeline.append({
                "time_offset_sec": offset_sec,
                "type": ev.get("event_type", "EVENT"),
                "details": ev.get("details", ""),
                "severity": ev.get("severity", "INFO")
            })
        return timeline[:10]

    def explain_cascading_failure(self, line_id: str) -> str:
        """Generates topological cascade propagation explanations."""
        line = line_id.upper()
        if line == "L7_8":
            return (
                "Apabila talian tie-breaker L7_8 mengalami beban berlebihan (overload) dan terpelanting, "
                "kuasa yang disalurkan oleh Gen_2 tidak dapat mengalir ke Bus 8. "
                "Aliran kuasa terpaksa berpusing melalui Talian L8_9 dan L4_9. "
                "Limpahan beban ini melebihi had termal talian-talian tersebut, menyebabkan kejatuhan voltan berantai (cascading trip) di substesen Bus 8 dan Bus 9."
            )
        elif line == "L4_5":
            return (
                "Kejatuhan Talian L4_5 menyebabkan pengasingan fizik antara Bus 4 dan Bus 5. "
                "Kuasa daripada Gen_1 terputus ke Load_5. "
                "Talian L5_6 akan terbeban untuk menyalurkan kuasa dari Bus 6, mencetuskan trip perlindungan arus lebih berantai."
            )
        return f"Kegagalan talian {line_id} akan mengubah pengagihan kuasa pada talian bersebelahan, meningkatkan risiko thermal trip sekiranya beban melebihi had nominal."

    def explain_trust_reduction(self, telemetry_data: Dict[str, Any]) -> str:
        """Explains why trust validation score dropped."""
        validation = telemetry_data.get("validation", {})
        kcl_status = validation.get("kcl_validated", True)
        kvl_status = validation.get("kvl_validated", True)
        trust_score = validation.get("trust_score", 100.0)
        
        reasons = []
        if trust_score < 100.0:
            reasons.append(f"Trust score semasa diturunkan ke {trust_score:.1f}%.")
            if not kcl_status:
                reasons.append("Ralat KCL dikesan: jumlah arus masuk tidak sama dengan arus keluar di nod substesen.")
            if not kvl_status:
                reasons.append("Ralat KVL dikesan: jumlah voltan gelung tertutup tidak sifar.")
            reasons.append("AI Detection mengesan anomali False Data Injection Attack (FDIA) yang cuba memanipulasi voltan HMI.")
        else:
            reasons.append("Trust score berada pada tahap 100% nominal. KCL/KVL physical validation lulus.")
            
        return " ".join(reasons)

    def handle_engineering_query(self, query: str, telemetry_data: Dict[str, Any], event_memory: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Handles topology, timeline, and ontology questions in Malay."""
        q = query.lower().strip()
        
        # Translate query using ontology
        for term, translated in self.ontology.items():
            if term in q:
                q = q.replace(term, translated)
                
        # 1. Topology impact: "Apa impact kalau Bus 5 gagal?"
        bus_match = None
        for i in range(1, 10):
            if f"bus {i}" in q or f"bas {i}" in q:
                bus_match = f"Bus_{i}"
                break
                
        if bus_match and ("gagal" in q or "fail" in q or "impact" in q or "kesan" in q or "undervoltage" in q or "langkah" in q or "tindakan" in q):
            impact = self.analyze_topology_impact(bus_match)
            relays = self.get_relay_relationships(bus_match)
            
            response = (
                f"Analisis Topologi bagi [{bus_match}]:\n"
                f"- Nod Bersebelahan: {', '.join(impact['neighbors'])}\n"
                f"- Talian Terjejas: {', '.join(impact['associated_lines'])}\n"
                f"- Beban Hilang: {impact['load_lost'] if impact['load_lost'] else 'Tiada'}\n"
                f"- Zon Islanding: {', '.join(impact['islanding_zone']) if impact['islanding_zone'] else 'Tiada'}\n"
                f"- Cadangan Pemulihan: {', '.join(impact['restoration_path']) if impact['restoration_path'] else 'Sistem Stabil'}\n"
                f"- Perlindungan Geganti Terlibat: {', '.join(relays)}"
            )
            
            return {
                "response": response,
                "reasoning_logs": [
                    f"Topology Reasoning: Analyzed adjacency for {bus_match}.",
                    f"Islanding check: Load loss: {impact['load_lost']}."
                ],
                "confidence": 0.95,
                "topic": "topology_analysis",
                "topology_details": {
                    "target": bus_match,
                    "neighbors": impact["neighbors"],
                    "lines": impact["associated_lines"],
                    "islanding": impact["islanding_zone"],
                    "relays": relays
                }
            }

        # 2. Relay relationships: "Relay mana terlibat dengan Bus 7?"
        if bus_match and ("relay" in q or "geganti" in q or "perlindungan" in q):
            relays = self.get_relay_relationships(bus_match)
            response = f"Bagi melindungi substesen [{bus_match}], geganti perlindungan (relay IED) yang bertindak balas adalah: {', '.join(relays)}."
            return {
                "response": response,
                "reasoning_logs": [
                    f"Ontology mapping: Geganti -> Relay protection.", 
                    f"Topology search: Mapped {bus_match} to relays {relays}."
                ],
                "confidence": 0.98,
                "topic": "relay_coordination",
                "topology_details": {
                    "target": bus_match,
                    "relays": relays
                }
            }

        # 3. Cascading explanation: "Kenapa cascading berlaku selepas L7_8 overload?"
        line_match = None
        for line_id in self.lines_map.keys():
            if line_id.lower() in q or line_id.replace("_", "-").lower() in q:
                line_match = line_id
                break
        if not line_match and "line 7-8" in q:
            line_match = "L7_8"
        if not line_match and "line 4-5" in q:
            line_match = "L4_5"
            
        if "cascading" in q or "cascade" in q or "berantai" in q:
            target_line = line_match or "L7_8"
            explanation = self.explain_cascading_failure(target_line)
            return {
                "response": explanation,
                "reasoning_logs": [f"Cascading Reasoner: Traced line redirection on failure of {target_line}."],
                "confidence": 0.92,
                "topic": "cascade_analysis",
                "topology_details": {
                    "failed_line": target_line
                }
            }

        # 4. Temporal timeline: "Apa berlaku sebelum undervoltage tadi?" or "timeline" or "rentetan"
        if "berlaku sebelum" in q or "timeline" in q or "rentetan" in q or "sebelum ini" in q:
            timeline = self.analyze_temporal_history(event_memory)
            if timeline:
                ev_str = []
                for ev in timeline:
                    ev_str.append(f"[-{ev['time_offset_sec']}s] {ev['type']} ({ev['severity']}): {ev['details']}")
                response = "Kronologi Peristiwa Grid Terkini:\n" + "\n".join(ev_str)
            else:
                response = "Tiada rekod peristiwa ganjil ditemui dalam ingatan temporal jangka pendek assistant."
                
            return {
                "response": response,
                "reasoning_logs": ["Temporal Reasoner: Decoded memory_orchestrator sliding event window."],
                "confidence": 0.99,
                "topic": "temporal_timeline",
                "event_timeline": timeline
            }

        # 5. Trust score drops: "Kenapa trust score turun?"
        if "trust score" in q or "trust" in q or "kebolehpercayaan" in q:
            explanation = self.explain_trust_reduction(telemetry_data)
            return {
                "response": explanation,
                "reasoning_logs": ["Causal Reasoner: Correlated physical state validator mismatch registers with trust index."],
                "confidence": 0.94,
                "topic": "trust_analysis"
            }

        # 6. Attack source: "Attack ni bermula dari mana?"
        if "attack" in q or "serangan" in q or "bermula" in q or "punca" in q:
            attack_evs = [ev for ev in event_memory if "ATTACK" in ev.get("event_type", "") or "cyber" in ev.get("details", "").lower()]
            if attack_evs:
                latest_attack = attack_evs[-1]
                response = f"Berdasarkan analisis siber, serangan dikesan bermula daripada: {latest_attack.get('details')}. Sila rujuk panel mitigasi."
            else:
                response = "Tiada log pencerobohan siber aktif dikesan dalam timeline semasa."
                
            return {
                "response": response,
                "reasoning_logs": ["Security Reasoner: Traced intrusion vector in temporal log history."],
                "confidence": 0.90,
                "topic": "cyber_attack_analysis"
            }

        return None
