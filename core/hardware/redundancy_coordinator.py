import time
import logging
from typing import Dict, Any, List, Tuple

logger = logging.getLogger("hardware.redundancy")

class RedundancyCoordinator:
    def __init__(self):
        # Primary-backup pairings mapping
        self.device_pairs = {
            "esp32_zone1": "esp32_backup",
            "esp32_zone2": "esp32_backup",
            "esp32_zone3": "esp32_backup",
            "plc_primary": "plc_backup"
        }
        
        # Track synchronization status (bool)
        self.active_backups_synchronized = {
            "esp32_backup": True,
            "plc_backup": True
        }
        
        # Redundancy health index per primary device (0 to 100)
        self.redundancy_health = {
            "esp32_zone1": 100.0,
            "esp32_zone2": 100.0,
            "esp32_zone3": 100.0,
            "plc_primary": 100.0
        }
        
        # Track redundant routing mode status
        self.redundant_execution_active = False
        self.failover_history: List[Dict[str, Any]] = []
        
    def evaluate_redundancy_health(self, fleet_status: Dict[str, Any], timing_deviations: Dict[str, float]):
        """
        Monitors heartbeat and timing parameters to compute redundancy health.
        Health decays if synchronization is lost, or backup latencies spike.
        """
        fleet = fleet_status.get("fleet", {})
        
        for primary, backup in self.device_pairs.items():
            if primary not in fleet or backup not in fleet:
                continue
                
            p_status = fleet[primary].get("status", "OFFLINE")
            b_status = fleet[backup].get("status", "OFFLINE")
            
            p_latency = fleet[primary].get("latency_ms", 0.0)
            b_latency = fleet[backup].get("latency_ms", 0.0)
            
            p_trust = fleet[primary].get("trust", 1.0)
            b_trust = fleet[backup].get("trust", 1.0)
            
            health = 100.0
            
            # Penalize if primary is quarantined
            if p_status == "QUARANTINED":
                health -= 50.0
                
            # Penalize if backup is offline or quarantined
            if b_status == "OFFLINE":
                health -= 40.0
                self.active_backups_synchronized[backup] = False
            elif b_status == "QUARANTINED":
                health -= 60.0
                self.active_backups_synchronized[backup] = False
                
            # Penalize if backup synchronization is lost
            if not self.active_backups_synchronized.get(backup, True):
                health -= 20.0
                
            # Penalize based on timing deviations
            p_drift = abs(timing_deviations.get(primary, 0.0))
            b_drift = abs(timing_deviations.get(backup, 0.0))
            if abs(p_drift - b_drift) > 10.0:
                health -= 15.0
                
            # Penalize if backup latency spikes
            if b_latency > 100.0:
                health -= 10.0
                
            self.redundancy_health[primary] = max(0.0, min(100.0, health))
            
    def route_redundant_command(self, payload: Dict[str, Any], primary_dev: str) -> List[Dict[str, Any]]:
        """
        If redundant_execution_active is enabled, duplicates the execution route
        to both the primary and backup devices simultaneously.
        """
        commands = [payload.copy()]
        
        if self.redundant_execution_active:
            backup_dev = self.device_pairs.get(primary_dev)
            if backup_dev and self.active_backups_synchronized.get(backup_dev, True):
                # Duplicate command for redundant backup execution
                backup_payload = payload.copy()
                backup_payload["redundant_route"] = backup_dev
                backup_payload["source"] = "SAFETY_GUARD"  # Elevated privileges to execute backup override
                commands.append(backup_payload)
                logger.info(f"Redundant Coordinator duplicated command {payload.get('command')} on {payload.get('target')} to backup {backup_dev}")
                
        return commands
        
    def arbitrate_responses(self, primary_success: bool, backup_success: bool, primary_dev: str) -> Tuple[bool, str]:
        """
        Arbitrates execution feedback between dual-routed channels.
        Triggers failover validation if primary fails but backup succeeds.
        """
        backup_dev = self.device_pairs.get(primary_dev)
        
        if not self.redundant_execution_active:
            return primary_success, "Single routing active."
            
        if primary_success and backup_success:
            return True, "Dual-routing execution verified successful on both nodes."
        elif not primary_success and backup_success:
            # Primary failed, backup took over successfully!
            failover_event = {
                "timestamp": int(time.time() * 1000),
                "primary": primary_dev,
                "backup": backup_dev,
                "status": "FAILOVER_VALIDATED",
                "details": "Primary failed execution but synchronized backup completed command successfully."
            }
            self.failover_history.append(failover_event)
            logger.warning(f"Redundancy Failover Validated: {primary_dev} failed, control transitioned to {backup_dev}")
            return True, f"Failover verified: routed execution to standby backup {backup_dev}."
        elif primary_success and not backup_success:
            # Primary succeeded, backup failed to sync command
            if backup_dev:
                self.active_backups_synchronized[backup_dev] = False
            return True, f"Primary executed successfully, but backup {backup_dev} command failed. Backup marked out-of-sync."
        else:
            return False, "Dual-routing critical execution failure: both primary and backup failed command dispatch."

    def get_telemetry_payload(self) -> Dict[str, Any]:
        """
        Serializes current redundancy coordinator status.
        """
        return {
            "timestamp": int(time.time() * 1000),
            "device_pairs": self.device_pairs,
            "redundancy_health": self.redundancy_health,
            "failover_history": self.failover_history,
            "active_backups_synchronized": self.active_backups_synchronized,
            "redundant_execution_active": self.redundant_execution_active
        }
