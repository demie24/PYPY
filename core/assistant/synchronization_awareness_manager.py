import time
import logging
from typing import Dict, Any, List

logger = logging.getLogger("assistant.synchronization_awareness")

class SynchronizationAwarenessManager:
    def __init__(self):
        # Default node drifts in seconds (e.g. 0.002s = 2ms)
        self.node_drifts: Dict[str, Dict[str, Any]] = {
            "esp32_zone1": {"drift_sec": 0.0, "status": "IN_SYNC", "consecutive_skew_ticks": 0, "last_sync": time.time()},
            "esp32_zone2": {"drift_sec": 0.0, "status": "IN_SYNC", "consecutive_skew_ticks": 0, "last_sync": time.time()},
            "esp32_zone3": {"drift_sec": 0.0, "status": "IN_SYNC", "consecutive_skew_ticks": 0, "last_sync": time.time()},
            "plc_primary": {"drift_sec": 0.0, "status": "IN_SYNC", "consecutive_skew_ticks": 0, "last_sync": time.time()},
            "plc_backup": {"drift_sec": 0.0, "status": "IN_SYNC", "consecutive_skew_ticks": 0, "last_sync": time.time()},
            "esp32_backup": {"drift_sec": 0.0, "status": "IN_SYNC", "consecutive_skew_ticks": 0, "last_sync": time.time()}
        }
        self.drift_threshold_sec = 0.025 # 25ms threshold
        self.critical_threshold_ticks = 5 # Escalate to critical skew after 5 ticks

    def update_node_drift(self, node_id: str, drift_sec: float):
        """Updates clock drift offset for a node and executes validation analysis."""
        if node_id not in self.node_drifts:
            self.node_drifts[node_id] = {
                "drift_sec": 0.0,
                "status": "IN_SYNC",
                "consecutive_skew_ticks": 0,
                "last_sync": time.time()
            }
            
        n = self.node_drifts[node_id]
        n["drift_sec"] = float(drift_sec)
        n["last_sync"] = time.time()
        
        # Validation checks
        self._validate_node_synchronization(node_id)

    def _validate_node_synchronization(self, node_id: str):
        """Analyzes timing skew and determines FSM transitions for sync states."""
        n = self.node_drifts[node_id]
        abs_drift = abs(n["drift_sec"])
        
        # Check drift exceeding threshold
        if abs_drift > self.drift_threshold_sec:
            n["consecutive_skew_ticks"] += 1
            if n["consecutive_skew_ticks"] > self.critical_threshold_ticks:
                n["status"] = "CRITICAL_SKEW"
            else:
                n["status"] = "SKEWED"
        else:
            # Recovery hysteresis (must be below 15ms to recover completely)
            if abs_drift < 0.015:
                n["consecutive_skew_ticks"] = 0
                n["status"] = "IN_SYNC"
            # Otherwise remain in "SKEWED" if not in critical state

    def get_skewed_nodes(self) -> List[str]:
        """Returns list of nodes currently skewed (SKEWED or CRITICAL_SKEW)."""
        return [k for k, v in self.node_drifts.items() if v["status"] in ("SKEWED", "CRITICAL_SKEW")]

    def get_critical_skewed_nodes(self) -> List[str]:
        """Returns list of nodes currently under critical skew."""
        return [k for k, v in self.node_drifts.items() if v["status"] == "CRITICAL_SKEW"]

    def get_status_summary(self) -> Dict[str, Any]:
        """Exposes timing skew list, max timing deviations, and timing alert logs."""
        skewed = self.get_skewed_nodes()
        critical_skewed = self.get_critical_skewed_nodes()
        
        max_drift_node = None
        max_drift_val = 0.0
        
        for k, v in self.node_drifts.items():
            abs_d = abs(v["drift_sec"])
            if abs_d > max_drift_val:
                max_drift_val = abs_d
                max_drift_node = k
                
        # Format warnings list
        warnings = []
        for node, profile in self.node_drifts.items():
            if profile["status"] == "CRITICAL_SKEW":
                warnings.append(f"CLOCK_SKEW_CRITICAL: Node {node} drift ({profile['drift_sec']*1000:.1f}ms) persists > 25ms threshold.")
            elif profile["status"] == "SKEWED":
                warnings.append(f"CLOCK_SKEW_WARNING: Node {node} drift ({profile['drift_sec']*1000:.1f}ms) exceeds threshold.")

        return {
            "node_sync_states": self.node_drifts,
            "skewed_nodes": skewed,
            "critical_skewed_nodes": critical_skewed,
            "max_drift_node": max_drift_node,
            "max_drift_ms": max_drift_val * 1000.0,
            "warnings": warnings,
            "skewed_count": len(skewed)
        }

    def reset_engine(self):
        """Resets all timing deviations to 0 and clears timing alarms."""
        for n in self.node_drifts.values():
            n["drift_sec"] = 0.0
            n["status"] = "IN_SYNC"
            n["consecutive_skew_ticks"] = 0
            n["last_sync"] = time.time()
