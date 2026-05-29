import time
import logging
import random
from typing import Dict, Any, List, Tuple

logger = logging.getLogger("hardware.command_bus")

class DistributedCommandBus:
    def __init__(self):
        # Pending transmissions: tx_id -> tx_details
        self.pending_transmissions: Dict[str, Dict[str, Any]] = {}
        # Completed history for telemetry (recent 50)
        self.history: List[Dict[str, Any]] = []
        
        # Performance metrics
        self.transmitted_count = 0
        self.dropped_count = 0
        self.retry_count = 0
        self.bus_load_pct = 1.0  # Simulated bus load
        
    def send_command(self, tx_id: str, command: Dict[str, Any], target_device: str, base_latency_ms: float) -> str:
        """
        Queues a command for distributed transmission on the bus.
        """
        now = time.time()
        # Initial retry parameters
        self.pending_transmissions[tx_id] = {
            "tx_id": tx_id,
            "command": command,
            "target": target_device,
            "latency_ms": base_latency_ms,
            "start_time": now,
            "next_delivery_time": now + (base_latency_ms / 1000.0),
            "status": "PENDING",
            "retries_attempted": 0,
            "max_retries": 3,
            "backoff_factor": 1.5,
            "retry_delay": 0.5  # base retry delay in seconds
        }
        self.transmitted_count += 1
        # Dynamic bus load adjustment
        self.bus_load_pct = min(100.0, 1.0 + len(self.pending_transmissions) * 4.5)
        logger.debug(f"Command queued on bus: tx_id={tx_id}, target={target_device}")
        return tx_id

    def process_bus_tick(self, device_manager_callback) -> List[Tuple[str, Dict[str, Any], str]]:
        """
        Ticks the bus. Processes pending commands, handles simulated packet drops,
        retries with backoff, and returns a list of commands ready to be executed.
        """
        now = time.time()
        commands_to_execute = []
        finished_tx_ids = []
        
        # Track if we have high command density to simulate retry storms
        retry_storm_active = self.retry_count > 5
        
        for tx_id, tx in list(self.pending_transmissions.items()):
            if tx["status"] == "PENDING" and now >= tx["next_delivery_time"]:
                target_device = tx["target"]
                
                # Retrieve device information from the manager
                device_info = device_manager_callback(target_device)
                device_trust = device_info.get("trust", 1.0) if device_info else 1.0
                device_status = device_info.get("status", "ONLINE") if device_info else "ONLINE"
                
                if device_status == "OFFLINE":
                    # Device offline: command immediately gets NACKed or timed out
                    tx["status"] = "NACKED"
                    tx["error"] = "Target device offline"
                    finished_tx_ids.append(tx_id)
                    logger.warning(f"Bus transmission failed: {target_device} is OFFLINE (tx_id={tx_id})")
                    continue
                
                # Drop rate is influenced by trust score and retry storm overload
                drop_chance = (1.0 - device_trust) * 0.5
                if retry_storm_active:
                    drop_chance += 0.20  # retry storm increases collision drop rate
                
                # Check for simulated packet loss
                if random.random() < drop_chance:
                    self.dropped_count += 1
                    tx["retries_attempted"] += 1
                    self.retry_count += 1
                    
                    if tx["retries_attempted"] > tx["max_retries"]:
                        tx["status"] = "TIMEOUT"
                        tx["error"] = "Max retries exceeded"
                        finished_tx_ids.append(tx_id)
                        logger.error(f"Command bus transmission timeout: tx_id={tx_id} target={target_device}")
                    else:
                        # Schedule next attempt with exponential backoff
                        delay = tx["retry_delay"] * (tx["backoff_factor"] ** (tx["retries_attempted"] - 1))
                        tx["next_delivery_time"] = now + delay
                        logger.warning(f"Packet drop detected on bus. Scheduling retry {tx['retries_attempted']} in {delay:.2f}s for tx_id={tx_id}")
                else:
                    # Packet successfully delivered
                    commands_to_execute.append((tx_id, tx["command"], target_device))
                    tx["status"] = "DELIVERED"
                    
        # Archive completed transmissions
        for tx_id in finished_tx_ids:
            tx = self.pending_transmissions.pop(tx_id)
            self._archive_tx(tx)
            
        # Decay retry count metric slowly
        if self.retry_count > 0:
            self.retry_count = max(0, self.retry_count - 1)
            
        self.bus_load_pct = min(100.0, 1.0 + len(self.pending_transmissions) * 4.5)
        return commands_to_execute

    def acknowledge_command(self, tx_id: str, success: bool, reason: str = ""):
        """
        Closes the feedback loop by receiving an ACK or NACK from the executing device.
        """
        if tx_id in self.pending_transmissions:
            tx = self.pending_transmissions.pop(tx_id)
            tx["status"] = "ACKED" if success else "NACKED"
            tx["details"] = reason
            tx["end_time"] = time.time()
            tx["duration_ms"] = (tx["end_time"] - tx["start_time"]) * 1000.0
            self._archive_tx(tx)
            logger.debug(f"Bus ACK/NACK received for tx_id={tx_id}: status={tx['status']} reason={reason}")

    def _archive_tx(self, tx: Dict[str, Any]):
        self.history.append(tx)
        if len(self.history) > 50:
            self.history.pop(0)

    def get_telemetry_payload(self) -> Dict[str, Any]:
        """
        Returns telemetry parameters for the command bus.
        """
        pending_list = []
        for tx_id, tx in self.pending_transmissions.items():
            pending_list.append({
                "tx_id": tx_id,
                "target": tx["target"],
                "status": tx["status"],
                "retries": tx["retries_attempted"]
            })
            
        recent_logs = []
        for tx in reversed(self.history):
            recent_logs.append({
                "timestamp": int(tx.get("end_time", time.time()) * 1000),
                "tx_id": tx["tx_id"],
                "target": tx["target"],
                "command": tx["command"].get("command"),
                "breaker": tx["command"].get("target"),
                "status": tx["status"],
                "retries": tx["retries_attempted"],
                "duration_ms": round(tx.get("duration_ms", 0.0), 2),
                "error": tx.get("error", tx.get("details", ""))
            })
            
        return {
            "timestamp": int(time.time() * 1000),
            "bus_load_pct": round(self.bus_load_pct, 1),
            "transmitted_count": self.transmitted_count,
            "dropped_count": self.dropped_count,
            "retry_count": self.retry_count,
            "pending_queue_size": len(self.pending_transmissions),
            "pending": pending_list,
            "history": recent_logs
        }
