import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("assistant.edge_awareness")

class EdgeAwarenessEngine:
    def __init__(self):
        # Default edge nodes fleet mapping virtual physical layout
        self.nodes: Dict[str, Dict[str, Any]] = {
            "esp32_zone1": {"latency_ms": 45.0, "packet_loss_pct": 0.0, "online": True, "drift_sec": 0.0, "health": 1.0},
            "esp32_zone2": {"latency_ms": 48.0, "packet_loss_pct": 0.0, "online": True, "drift_sec": 0.0, "health": 1.0},
            "esp32_zone3": {"latency_ms": 50.0, "packet_loss_pct": 0.0, "online": True, "drift_sec": 0.0, "health": 1.0},
            "plc_primary": {"latency_ms": 12.0, "packet_loss_pct": 0.0, "online": True, "drift_sec": 0.0, "health": 1.0},
            "plc_backup": {"latency_ms": 15.0, "packet_loss_pct": 0.0, "online": True, "drift_sec": 0.0, "health": 1.0},
            "esp32_backup": {"latency_ms": 46.0, "packet_loss_pct": 0.0, "online": True, "drift_sec": 0.0, "health": 1.0}
        }
        self.anomalies: Dict[str, Any] = {}
        
    def update_edge_state(self, node_id: str, latency: Optional[float], packet_loss: Optional[float], online: bool, drift_sec: float = 0.0):
        """Updates the status and telemetry profile of a given edge node."""
        if node_id not in self.nodes:
            self.nodes[node_id] = {
                "latency_ms": 40.0,
                "packet_loss_pct": 0.0,
                "online": True,
                "drift_sec": 0.0,
                "health": 1.0
            }
        
        node = self.nodes[node_id]
        node["online"] = bool(online)
        node["latency_ms"] = float(latency) if latency is not None else 0.0
        node["packet_loss_pct"] = float(packet_loss) if packet_loss is not None else 0.0
        node["drift_sec"] = float(drift_sec)
        
        # Calculate dynamic health
        node["health"] = self.calculate_health_score(node_id)
        self._analyze_node_anomaly(node_id)

    def calculate_health_score(self, node_id: str) -> float:
        """Computes dynamic health score from 0.0 to 1.0 based on latency, packet loss, and sync drift."""
        node = self.nodes.get(node_id)
        if not node or not node.get("online", False):
            return 0.0
            
        health = 1.0
        latency = node.get("latency_ms", 0.0)
        packet_loss = node.get("packet_loss_pct", 0.0)
        drift = abs(node.get("drift_sec", 0.0))
        
        # Latency Penalty (starts after 100ms)
        if latency > 100.0:
            deduction = (latency - 100.0) / 400.0
            health -= min(deduction, 0.40)
            
        # Packet Loss Penalty
        if packet_loss > 0.0:
            deduction = packet_loss / 100.0
            health -= min(deduction, 0.35)
            
        # Synchronization Drift Penalty (starts after 20ms = 0.02s)
        if drift > 0.02:
            deduction = (drift - 0.02) * 5.0
            health -= min(deduction, 0.25)
            
        return max(0.0, min(1.0, health))

    def _analyze_node_anomaly(self, node_id: str):
        """Analyzes anomalies on a specific node."""
        node = self.nodes[node_id]
        anomalies_list = []
        
        if not node["online"]:
            anomalies_list.append("OFFLINE")
        else:
            if node["latency_ms"] > 150.0:
                anomalies_list.append("HIGH_LATENCY")
            if node["packet_loss_pct"] > 5.0:
                anomalies_list.append("PACKET_LOSS_DETECTION")
            if abs(node["drift_sec"]) > 0.05:
                anomalies_list.append("SYNC_DRIFT_SKEW")
                
        if anomalies_list:
            self.anomalies[node_id] = anomalies_list
        elif node_id in self.anomalies:
            del self.anomalies[node_id]

    def get_worst_node(self) -> Optional[str]:
        """Identifies and returns the name of the most degraded edge node."""
        worst_node = None
        min_health = 1.01
        
        for k, v in self.nodes.items():
            # If equal, pick the one with higher latency or drift
            if v["health"] < min_health:
                min_health = v["health"]
                worst_node = k
            elif abs(v["health"] - min_health) < 0.001 and worst_node:
                # Tie-breaker logic (higher latency / drift wins worst score)
                curr_worst = self.nodes[worst_node]
                if v["latency_ms"] > curr_worst["latency_ms"] or abs(v["drift_sec"]) > abs(curr_worst["drift_sec"]):
                    worst_node = k
                    
        return worst_node

    def get_status_summary(self) -> Dict[str, Any]:
        """Compiles health metrics, active anomalies, and worst node pointers."""
        worst_node_id = self.get_worst_node()
        worst_node_health = self.nodes[worst_node_id]["health"] if worst_node_id else 1.0
        
        # Correlate distributed edge behavior
        average_latency = sum(n["latency_ms"] for n in self.nodes.values() if n["online"]) / max(1, sum(1 for n in self.nodes.values() if n["online"]))
        
        return {
            "nodes": self.nodes,
            "anomalies": self.anomalies,
            "worst_node": worst_node_id,
            "worst_node_health": worst_node_health,
            "average_latency_ms": average_latency,
            "distributed_anomaly_count": len(self.anomalies)
        }

    def reset_engine(self):
        """Resets nodes health stats and wipes simulated anomaly states."""
        for node in self.nodes.values():
            node["latency_ms"] = 45.0 if "esp32" in str(node) else 12.0
            node["packet_loss_pct"] = 0.0
            node["online"] = True
            node["drift_sec"] = 0.0
            node["health"] = 1.0
        self.anomalies.clear()
