import logging
from typing import Dict, Any, List

logger = logging.getLogger("assistant.cross_system_coordination")

class CrossSystemCoordinationManager:
    def __init__(self):
        self.sync_state = "SYNCED"  # SYNCED, DRIFTING, CONFLICT_RESOLVING
        self.drift_sec = 0.0
        self.conflict_logs: List[str] = []
        self.last_sync_timestamp = 0.0

    def tick_synchronization(
        self,
        grid_state: Dict[str, Any],
        hardware_sim_state: Dict[str, Any],
        recommendations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Monitors cross-module synchronization offsets and checks for execution conflicts.
        """
        import time
        now = time.time()
        self.last_sync_timestamp = now * 1000

        # Simulate drift based on hardware twin latency variations
        device_latency = grid_state.get("telemetry", {}).get("latency_ms", 45.0)
        # Alternate mappings
        if "latency_ms" in hardware_sim_state:
            device_latency = hardware_sim_state["latency_ms"]

        if device_latency > 150.0:
            self.sync_state = "DRIFTING"
            self.drift_sec = round((device_latency - 100.0) / 1000.0, 3)
        else:
            self.sync_state = "SYNCED"
            self.drift_sec = 0.0

        # Conflict Prevention Logic (Enforce Safety rules)
        threat_score = grid_state.get("threat", {}).get("threat_score", 0.0)
        
        # Check conflicts
        conflict_found = False
        for rec in recommendations:
            if rec["workflow_name"] == "system_status_check" and rec["optimization_type"] == "TRIM_DELAY":
                # If threat score rises while a delay reduction recommendation is active, this is a conflict!
                if threat_score > 75.0:
                    self.sync_state = "CONFLICT_RESOLVING"
                    conflict_found = True
                    log_msg = f"OVERRIDE: Rejected TRIM_DELAY on system_status_check. Threat is critical ({threat_score:.1f}%). Safety overrides optimization."
                    if not self.conflict_logs or self.conflict_logs[-1] != log_msg:
                        self.conflict_logs.append(log_msg)
                        logger.warning(log_msg)
                    # Forcibly change recommendation state to BLOCKED
                    rec["status"] = "BLOCKED"
                    rec["description"] = "Disekat: Ancaman grid kritikal menghentikan pengoptimuman masa sela."

        if not conflict_found and self.sync_state == "CONFLICT_RESOLVING":
            self.sync_state = "SYNCED"

        return self.get_status_summary()

    def get_status_summary(self) -> Dict[str, Any]:
        return {
            "sync_state": self.sync_state,
            "drift_sec": self.drift_sec,
            "conflict_logs_count": len(self.conflict_logs),
            "conflict_logs": self.conflict_logs[-5:],
            "last_sync_timestamp": self.last_sync_timestamp
        }
