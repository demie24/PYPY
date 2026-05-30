import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("assistant.cyber_physical_reasoning")

class CyberPhysicalReasoningEngine:
    def __init__(self):
        self.severity_score = 0.0
        self.severity_level = "LOW"
        self.suggestions: List[Dict[str, Any]] = []
        self.reasoning_logs: List[str] = []

    def evaluate_state(
        self,
        edge_sum: Dict[str, Any],
        relay_sum: Dict[str, Any],
        correlation_sum: Dict[str, Any],
        sync_sum: Dict[str, Any],
        threat_score: float = 0.0,
        threat_confidence: float = 1.0
    ) -> Dict[str, Any]:
        """Fuses edge, relay, sync, and correlation telemetry summaries to evaluate global grid status."""
        self.reasoning_logs.clear()
        self.reasoning_logs.append("Memulakan penilaian keadaan cyber-physical...")
        
        # 1. Calculate dynamic severity score
        base_threat_comp = float(threat_score) * 0.30
        
        worst_health = float(edge_sum.get("worst_node_health", 1.0))
        edge_health_comp = (1.0 - worst_health) * 30.0
        
        unstable_count = int(relay_sum.get("unstable_count", 0))
        relay_comp = unstable_count * 20.0
        
        cascades_count = len(correlation_sum.get("cascades", []))
        corr_comp = cascades_count * 15.0
        
        skewed_count = int(sync_sum.get("skewed_count", 0))
        sync_comp = skewed_count * 10.0
        
        total_score = base_threat_comp + edge_health_comp + relay_comp + corr_comp + sync_comp
        self.severity_score = max(0.0, min(100.0, total_score))
        
        # Determine level
        if self.severity_score >= 75.0:
            self.severity_level = "CRITICAL"
        elif self.severity_score >= 50.0:
            self.severity_level = "HIGH"
        elif self.severity_score >= 25.0:
            self.severity_level = "MEDIUM"
        else:
            self.severity_level = "LOW"
            
        self.reasoning_logs.append(f"Severity score dinilai: {self.severity_score:.1f} ({self.severity_level})")
        
        # 2. Build recommendations & safety guards
        self.suggestions = []
        
        # Relay recommendations
        for b_id, b_val in relay_sum.get("breakers", {}).items():
            if b_val.get("unstable"):
                if threat_confidence >= 0.75:
                    self.suggestions.append({
                        "action": "LOCKOUT_BREAKER",
                        "target": b_id,
                        "description": f"Lockout breaker {b_id} untuk hentikan oscillation.",
                        "severity": "CRITICAL"
                    })
                    self.reasoning_logs.append(f"Cadangan: Lockout breaker {b_id} akibat oscillation (confidence OK).")
                else:
                    self.suggestions.append({
                        "action": "OPERATOR_VERIFICATION",
                        "target": b_id,
                        "description": f"Sahkan status breaker {b_id} secara manual (confidence {threat_confidence:.2f} rendah).",
                        "severity": "BLOCKED"
                    })
                    self.reasoning_logs.append(f"Safety Gate: Lockout breaker {b_id} disekat kerana confidence rendah ({threat_confidence:.2f}).")
                    
        # Timing sync recommendations
        skewed_nodes = sync_sum.get("skewed_nodes", [])
        for node in skewed_nodes:
            if threat_confidence >= 0.75:
                self.suggestions.append({
                    "action": "SYNC_RECOVERY",
                    "target": node,
                    "description": f"Jalankan timing calibration PTP pada {node} untuk baiki skew.",
                    "severity": "HIGH"
                })
                self.reasoning_logs.append(f"Cadangan: Sync calibration pada {node} (drift dikesan).")
            else:
                self.suggestions.append({
                    "action": "MONITOR_TIMING",
                    "target": node,
                    "description": f"Perhatikan timing drift {node} secara manual.",
                    "severity": "MEDIUM"
                })
                
        # Cascading patterns suggestions
        cascades = correlation_sum.get("cascades", [])
        if cascades:
            self.suggestions.append({
                "action": "ISOLATE_PROPAGATION_PATH",
                "target": cascades[0].get("effect"),
                "description": f"Isolate line propagation path untuk containment cascade: {cascades[0].get('cause')} -> {cascades[0].get('effect')}",
                "severity": "HIGH"
            })
            self.reasoning_logs.append("Cascading pattern dikesan; cadangan isolation path dijana.")
            
        # Global emergency safety advice
        if self.severity_level == "CRITICAL":
            self.suggestions.append({
                "action": "OPERATOR_ESCALATION",
                "target": "SCADA",
                "description": "Tahap kecemasan kritikal. Operator dinasihatkan masuk mod manual control sepenuhnya.",
                "severity": "CRITICAL"
            })
            
        return {
            "severity_score": self.severity_score,
            "severity_level": self.severity_level,
            "suggestions": self.suggestions,
            "reasoning_logs": self.reasoning_logs
        }

    def handle_query(
        self,
        query: str,
        edge_sum: Dict[str, Any],
        relay_sum: Dict[str, Any],
        correlation_sum: Dict[str, Any],
        sync_sum: Dict[str, Any],
        threat_score: float = 0.0,
        threat_confidence: float = 1.0
    ) -> Optional[str]:
        """Resolves natural language queries related to node health, timing drift, and stabilization workflows in Malay."""
        q = query.lower().strip()
        
        # 1. "node mana paling bermasalah sekarang"
        if "node mana paling bermasalah" in q or "node paling problem" in q or "node problem" in q:
            worst_node = edge_sum.get("worst_node")
            worst_health = edge_sum.get("worst_node_health", 1.0)
            if worst_node and worst_health < 0.90:
                node_profile = edge_sum.get("nodes", {}).get(worst_node, {})
                latency = node_profile.get("latency_ms", 0.0)
                drift_ms = node_profile.get("drift_sec", 0.0) * 1000.0
                return (
                    f"Node paling bermasalah sekarang ialah {worst_node} dengan health index {worst_health:.2f}. "
                    f"Latency dia ialah {latency:.1f}ms dan drift delay sebanyak {drift_ms:.1f}ms. "
                    "Saya syorkan untuk periksa sambungan controller ini."
                )
            else:
                return "Semua edge node dikesan dalam keadaan stabil buat masa sekarang."
                
        # 2. "relay node 3 nampak unstable" / "breaker unstable" / "oscillation"
        if "unstable" in q or "oscillation" in q or "relay" in q or "breaker" in q:
            # Check if user mentioned specific nodes or if there are any unstable breakers
            unstable_list = relay_sum.get("unstable_breakers", [])
            if unstable_list:
                breakers_str = ", ".join(unstable_list)
                return (
                    f"Ya, saya detect breaker {breakers_str} mengalami oscillation (unstable). "
                    "Operator dinasihatkan membuat safety lockout secepat mungkin."
                )
            
            # Specific node inquiry fallback
            if "node 3" in q or "l3_6" in q:
                b_info = relay_sum.get("breakers", {}).get("L3_6", {})
                if b_info.get("unstable"):
                    return "Breaker L3_6 di Zone 3 dikesan unstable: tengah mengalami oscillation sekarang."
                else:
                    return "Breaker L3_6 di Zone 3 dalam keadaan stabil."
                    
            # Breaker wear degradation inquiry
            wear_report = relay_sum.get("wear_report", {})
            if wear_report:
                wear_str = ", ".join([f"{k} ({v:.1f}%)" for k, v in wear_report.items()])
                return f"Wear degradation agak tinggi pada breaker berikut: {wear_str}. Sila rancang maintenance."
                
            return "Kesihatan semua relay breaker didapati nominal."

        # 3. "edge synchronization delay meningkat" / "telemetry drift"
        if "synchronization" in q or "drift" in q or "timing skew" in q or "sync delay" in q:
            worst_drift_node = sync_sum.get("max_drift_node")
            worst_drift_ms = sync_sum.get("max_drift_ms", 0.0)
            if worst_drift_node and worst_drift_ms > 25.0:
                return (
                    f"Ya, saya detect timing drift delay pada node {worst_drift_node} meningkat sebanyak {worst_drift_ms:.1f}ms. "
                    "Sila jalankan PTP sync recovery untuk recalibrate jam node."
                )
            else:
                return f"Timing synchronization stabil. Drift tertinggi dikesan hanya {worst_drift_ms:.1f}ms."

        # 4. "cadangkan stabilization workflow"
        if "cadangkan stabilization workflow" in q or "stabilization workflow" in q or "cadang workflow" in q:
            if threat_confidence < 0.75:
                return (
                    f"Cadangan stabilization workflow disekat kerana threat confidence score ({threat_confidence:.2f}) "
                    "di bawah threshold 0.75. Sila sahkan secara manual untuk keselamatan grid."
                )
                
            # Compile actions
            workflows_list = []
            
            # Breaker recovery action
            unstable_list = relay_sum.get("unstable_breakers", [])
            for b in unstable_list:
                workflows_list.append(f"1. Lockout breaker {b} (Oscillation Containment)")
                
            # Sync timing action
            skewed_nodes = sync_sum.get("skewed_nodes", [])
            for n in skewed_nodes:
                workflows_list.append(f"2. PTP Timing Recalibration pada {n} (Timing Drift Calibration)")
                
            # Cascading action
            cascades = correlation_sum.get("cascades", [])
            if cascades:
                workflows_list.append(f"3. Isolate line {cascades[0].get('effect')} (Cascade Propagation Block)")
                
            if not workflows_list:
                return "Grid berada dalam keadaan stabil. Tiada stabilization workflow perlu dicadangkan buat masa sekarang."
                
            return "Stabilization workflow yang dicadangkan:\n" + "\n".join(workflows_list)

        return None
