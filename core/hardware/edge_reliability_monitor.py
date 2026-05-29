import time
import logging
from typing import Dict, Any, List, Tuple

logger = logging.getLogger("hardware.reliability")

class EdgeReliabilityMonitor:
    def __init__(self):
        # Device Reliability Scores (0.0 to 1.0)
        self.devices = [
            "esp32_zone1", "esp32_zone2", "esp32_zone3",
            "plc_primary", "esp32_backup", "plc_backup"
        ]
        self.reliability_scores: Dict[str, float] = {dev: 1.0 for dev in self.devices}
        
        # Interface Flapping Tracking
        self.device_statuses: Dict[str, str] = {dev: "ONLINE" for dev in self.devices}
        self.device_transitions: Dict[str, List[float]] = {dev: [] for dev in self.devices}
        self.lockout_states: Dict[str, bool] = {dev: False for dev in self.devices}
        self.lockout_times: Dict[str, float] = {dev: 0.0 for dev in self.devices}
        self.lockout_cooldown = 30.0  # 30 seconds lockout cooldown
        
        # Relay Timeout Tracking
        # {relay_id: {"target": target_state, "device_id": device_id, "timestamp": timestamp, "alerted": bool}}
        self.pending_relay_commands: Dict[str, Dict[str, Any]] = {}
        self.timeout_threshold_ms = 200.0  # 200ms
        
        # Alerts list
        self.alerts: List[str] = []
        
    def register_relay_command(self, relay_id: str, target_state: str, device_id: str):
        """
        Registers a relay command to track feedback execution timeouts.
        """
        self.pending_relay_commands[relay_id] = {
            "target": target_state,
            "device_id": device_id,
            "timestamp": time.time(),
            "alerted": False
        }
        logger.info(f"Reliability monitor registered command for relay {relay_id} target={target_state} on device={device_id}")

    def update_device_status(self, device_id: str, current_status: str):
        """
        Processes status updates to detect interface flapping.
        If status transitions > 3 times in 15 seconds, locks out the port.
        """
        if device_id not in self.device_statuses:
            return
            
        prev_status = self.device_statuses[device_id]
        if prev_status != current_status:
            now = time.time()
            self.device_transitions[device_id].append(now)
            
            # Prune transitions older than 15 seconds
            self.device_transitions[device_id] = [t for t in self.device_transitions[device_id] if now - t <= 15.0]
            
            logger.info(f"Device status transition: {device_id} changed from {prev_status} to {current_status}. (transitions in 15s: {len(self.device_transitions[device_id])})")
            
            # Check for interface flapping: > 3 transitions in 15 seconds
            if len(self.device_transitions[device_id]) > 3:
                if not self.lockout_states[device_id]:
                    self.lockout_states[device_id] = True
                    self.lockout_times[device_id] = now
                    alert_msg = f"INTERFACE_FLAPPING_LOCKOUT: {device_id} locked out due to excessive state transitions (>3 in 15s)"
                    self.alerts.append(alert_msg)
                    logger.error(alert_msg)
                    self.decay_reliability(device_id, 0.4)
                    
            self.device_statuses[device_id] = current_status

    def decay_reliability(self, device_id: str, penalty: float):
        """
        Decays the reliability score of a device.
        """
        if device_id in self.reliability_scores:
            self.reliability_scores[device_id] = max(0.0, round(self.reliability_scores[device_id] - penalty, 3))
            logger.warning(f"Device {device_id} reliability score decayed to {self.reliability_scores[device_id]}")

    def recover_reliability(self, device_id: str, recovery: float):
        """
        Recovers the reliability score of a device.
        """
        if device_id in self.reliability_scores:
            # Locked out devices cannot recover reliability until lockout is cleared
            if self.lockout_states.get(device_id, False):
                return
            self.reliability_scores[device_id] = min(1.0, round(self.reliability_scores[device_id] + recovery, 3))

    def tick(self, fleet_data: Dict[str, Any], relay_telemetry: Dict[str, Any]):
        """
        Periodic execution step. Processes missed heartbeats, latency spikes, relay timeouts, and lockout cooldowns.
        """
        now = time.time()
        
        # 1. Process Lockout Cooldowns
        for dev in self.devices:
            if self.lockout_states[dev]:
                lock_time = self.lockout_times.get(dev, 0.0)
                if now - lock_time > self.lockout_cooldown:
                    self.lockout_states[dev] = False
                    self.device_transitions[dev] = []
                    alert_msg = f"INTERFACE_LOCKOUT_RELEASED: {dev} lockout cooldown expired."
                    self.alerts.append(alert_msg)
                    logger.info(alert_msg)
                    # Starts with moderate reliability recovery on release
                    self.reliability_scores[dev] = min(1.0, self.reliability_scores[dev] + 0.2)

        # 2. Process Heartbeats and Latency Spikes
        fleet = fleet_data.get("fleet", {})
        for dev_id, dev_info in fleet.items():
            if dev_id not in self.reliability_scores:
                continue
                
            status = dev_info.get("status")
            latency = dev_info.get("latency_ms", 0.0)
            
            # Feed current status to flapping monitor
            self.update_device_status(dev_id, status)
            
            if status == "OFFLINE":
                # Missed heartbeat: gradual decay
                self.decay_reliability(dev_id, 0.05)
            elif status == "ONLINE":
                if latency > 150.0:
                    # Latency spike decay
                    self.decay_reliability(dev_id, 0.02)
                else:
                    # Normal operation: slow recovery
                    self.recover_reliability(dev_id, 0.01)

        # 3. Process Relay Timeout Tracking
        relays = relay_telemetry.get("relays", {})
        for relay_id, cmd_info in list(self.pending_relay_commands.items()):
            target = cmd_info["target"]
            device_id = cmd_info["device_id"]
            start_time = cmd_info["timestamp"]
            alerted = cmd_info["alerted"]
            
            current_relay = relays.get(relay_id, {})
            current_feedback = current_relay.get("feedback")
            
            if current_feedback == target:
                # Successfully transitioned!
                self.pending_relay_commands.pop(relay_id, None)
            else:
                elapsed_ms = (now - start_time) * 1000.0
                if elapsed_ms > self.timeout_threshold_ms:
                    if not alerted:
                        cmd_info["alerted"] = True
                        alert_msg = f"RELAY_TIMEOUT_ALERT: {relay_id} failed to transition to {target} within {self.timeout_threshold_ms}ms on {device_id}"
                        self.alerts.append(alert_msg)
                        logger.error(alert_msg)
                        # Penalize target device reliability
                        self.decay_reliability(device_id, 0.25)
                        
                    # Keep command in queue until it reaches state or gets overridden, but capped at 5s to avoid leaks
                    if now - start_time > 5.0:
                        self.pending_relay_commands.pop(relay_id, None)

        # Keep alerts list length in check (max 50)
        if len(self.alerts) > 50:
            self.alerts = self.alerts[-50:]

    def get_telemetry_payload(self) -> Dict[str, Any]:
        """
        Serializes current reliability telemetry.
        """
        return {
            "timestamp": int(time.time() * 1000),
            "reliability_scores": self.reliability_scores,
            "lockout_states": self.lockout_states,
            "alerts": self.alerts,
            "pending_commands_count": len(self.pending_relay_commands)
        }
