import time
import logging
from typing import Dict, Any, List

logger = logging.getLogger("assistant.federated_memory_manager")

class FederatedMemoryManager:
    def __init__(self):
        self.agent_name = "FederatedMemoryManager"
        self.status = "NOMINAL"
        self.local_memory: Dict[str, Any] = {}
        self.shared_memory: Dict[str, Any] = {}
        self.lamport_clock = 0
        self.sync_count = 0
        self.last_sync_time = time.time()
        self.sync_cooldown = 1.0  # seconds
        self.conflict_logs: List[str] = []
        self.sync_status = "SYNCED"

    def update_local_memory(self, key: str, value: Any):
        """Updates a local memory key and increments the Lamport clock."""
        self.lamport_clock += 1
        self.local_memory[key] = {
            "value": value,
            "timestamp": time.time(),
            "clock": self.lamport_clock
        }
        # Auto propagate to shared memory for current node
        self.shared_memory[key] = self.local_memory[key]

    def synchronize_memory(self, remote_node_id: str, remote_memory: Dict[str, Any], simulation_mode: str = None) -> Dict[str, Any]:
        """Merges remote node memory into the local shared memory workspace with conflict resolution."""
        current_time = time.time()
        
        # Enforce synchronization storm prevention
        # If in conflict state, or if synchronization calls happen too rapidly, rate-limit.
        is_storm_sim = (simulation_mode == "synchronization_storms")
        time_since_last_sync = current_time - self.last_sync_time
        
        if is_storm_sim or (time_since_last_sync < self.sync_cooldown and self.sync_status == "OUT_OF_SYNC"):
            self.sync_status = "STORM_PREVENTED"
            self.conflict_logs.append(f"[SAFETY]: Sync storm dikesan dari {remote_node_id}. Sync di-rate-limit!")
            self.status = "STORM_MITIGATED"
            return self.get_status_summary()

        self.last_sync_time = current_time
        self.sync_count += 1
        has_conflicts = False

        for key, remote_entry in remote_memory.items():
            if not isinstance(remote_entry, dict) or "value" not in remote_entry or "clock" not in remote_entry:
                continue

            local_entry = self.shared_memory.get(key)
            if not local_entry:
                # New key, propagate directly
                self.shared_memory[key] = remote_entry
                self.lamport_clock = max(self.lamport_clock, remote_entry["clock"]) + 1
            else:
                # Conflict Resolution: Compare Lamport clocks
                if remote_entry["clock"] > local_entry["clock"]:
                    # Remote wins
                    self.shared_memory[key] = remote_entry
                    self.lamport_clock = max(self.lamport_clock, remote_entry["clock"]) + 1
                elif remote_entry["clock"] == local_entry["clock"]:
                    # Clock tie, resolve by timestamp (or value comparison if timestamp ties)
                    if remote_entry["timestamp"] > local_entry["timestamp"]:
                        self.shared_memory[key] = remote_entry
                    elif remote_entry["timestamp"] == local_entry["timestamp"]:
                        # Absolute tie-breaker: larger value or string representation wins
                        if str(remote_entry["value"]) > str(local_entry["value"]):
                            self.shared_memory[key] = remote_entry
                    has_conflicts = True
                    self.conflict_logs.append(
                        f"Konflik diselesaikan bagi key '{key}' pada clock {remote_entry['clock']}. Nilai terkini: {self.shared_memory[key]['value']}."
                    )
                else:
                    # Local wins, ignore remote update
                    has_conflicts = True

        if simulation_mode == "federated_memory_conflicts":
            self.sync_status = "CONFLICT_DETECTED"
            self.status = "DEGRADED"
            self.conflict_logs.append("SIMULASI KONFLIK MEMORI: Konflik replikasi antara nod dikesan.")
        elif has_conflicts:
            self.sync_status = "OUT_OF_SYNC"
            self.status = "DEGRADED"
        else:
            self.sync_status = "SYNCED"
            self.status = "NOMINAL"

        return self.get_status_summary()

    def get_status_summary(self) -> Dict[str, Any]:
        serialized_shared = {}
        for k, v in self.shared_memory.items():
            serialized_shared[k] = v.get("value") if isinstance(v, dict) else v

        return {
            "agent_name": self.agent_name,
            "status": self.status,
            "sync_status": self.sync_status,
            "lamport_clock": self.lamport_clock,
            "sync_count": self.sync_count,
            "conflict_logs": self.conflict_logs[-10:],  # last 10 logs
            "shared_memory": serialized_shared
        }

    def reset_agent(self):
        self.status = "NOMINAL"
        self.local_memory.clear()
        self.shared_memory.clear()
        self.lamport_clock = 0
        self.sync_count = 0
        self.last_sync_time = time.time()
        self.conflict_logs.clear()
        self.sync_status = "SYNCED"
