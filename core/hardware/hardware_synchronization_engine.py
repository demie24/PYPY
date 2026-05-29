import time
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("hardware.sync_engine")

class HardwareSynchronizationEngine:
    def __init__(self):
        self.tick_counter = 0
        # Simulated clock drift per virtual device (in milliseconds)
        self.device_drifts: Dict[str, float] = {}
        # Buffer of historical device states indexed by tick count
        self.telemetry_buffer: Dict[int, Dict[str, Any]] = {}
        # Max history for buffer alignment
        self.max_buffer_history = 100
        # Active/Standby mappings for failover sync
        self.failover_pairs: Dict[str, str] = {
            "esp32_zone1": "esp32_backup",
            "plc_primary": "plc_backup"
        }
        # Alignment check results: True if standby matches primary
        self.failover_aligned: Dict[str, bool] = {
            "esp32_zone1": True,
            "plc_primary": True
        }
        
    def tick(self):
        """
        Increments the virtual clock tick and simulates incremental drift.
        """
        self.tick_counter += 1
        
        # Simulate slight drift on virtual devices
        for dev in ["esp32_zone1", "esp32_zone2", "esp32_zone3", "plc_primary", "esp32_backup", "plc_backup"]:
            if dev not in self.device_drifts:
                self.device_drifts[dev] = 0.0
            
            # Minor random walk for clock drift (drift increases over time)
            # ESP32s drift faster than PLCs
            if "esp32" in dev:
                self.device_drifts[dev] += 0.05  # ms drift per tick
            else:
                self.device_drifts[dev] += 0.02  # ms drift per tick
                
        # Run periodic failover synchronization checks
        if self.tick_counter % 10 == 0:
            self._verify_failover_alignment()

    def sync_device_clock(self, device_id: str) -> float:
        """
        Resets the clock drift for a device, simulating a PTP/NTP adjustment.
        Returns the drift before synchronization.
        """
        old_drift = self.device_drifts.get(device_id, 0.0)
        self.device_drifts[device_id] = 0.0
        logger.info(f"Clock synchronization triggered for {device_id}. Corrected {old_drift:.2f}ms drift.")
        return old_drift

    def record_telemetry_state(self, tick: int, device_id: str, state: Dict[str, Any]):
        """
        Buffers device telemetry state to align telemetry times for audits.
        """
        if tick not in self.telemetry_buffer:
            self.telemetry_buffer[tick] = {}
        
        self.telemetry_buffer[tick][device_id] = {
            "timestamp": time.time(),
            "state": state.copy()
        }
        
        # Enforce rolling history limit
        if len(self.telemetry_buffer) > self.max_buffer_history:
            oldest_tick = min(self.telemetry_buffer.keys())
            self.telemetry_buffer.pop(oldest_tick, None)

    def get_aligned_telemetry(self, tick: int) -> Optional[Dict[str, Any]]:
        """
        Returns synchronized telemetry across all active devices for a specific tick.
        """
        return self.telemetry_buffer.get(tick)

    def replicate_state(self, primary_id: str, standby_id: str, state: Dict[str, Any]):
        """
        Simulates state replication from a primary device to a standby unit.
        """
        if primary_id in self.failover_pairs and self.failover_pairs[primary_id] == standby_id:
            # Replicate state to telemetry buffer at current tick
            self.record_telemetry_state(self.tick_counter, standby_id, state)
            self.failover_aligned[primary_id] = True
            logger.debug(f"Replicated primary state from {primary_id} to standby {standby_id}.")

    def _verify_failover_alignment(self):
        """
        Compares states between primary and backup units in the buffer.
        """
        for primary, standby in self.failover_pairs.items():
            primary_states = [self.telemetry_buffer[t].get(primary) for t in self.telemetry_buffer if primary in self.telemetry_buffer[t]]
            standby_states = [self.telemetry_buffer[t].get(standby) for t in self.telemetry_buffer if standby in self.telemetry_buffer[t]]
            
            if not primary_states or not standby_states:
                self.failover_aligned[primary] = False
                continue
                
            # Compare latest buffered states
            latest_pri = primary_states[-1]
            latest_std = standby_states[-1]
            
            if latest_pri and latest_std:
                # Compare the state sub-dictionary
                if latest_pri["state"] == latest_std["state"]:
                    self.failover_aligned[primary] = True
                else:
                    self.failover_aligned[primary] = False
                    logger.warning(f"Failover desynchronization detected between {primary} and {standby}.")

    def get_telemetry_payload(self) -> Dict[str, Any]:
        """
        Generates telemetry representation for the synchronization engine.
        """
        return {
            "timestamp": int(time.time() * 1000),
            "tick_counter": self.tick_counter,
            "device_drifts": self.device_drifts,
            "failover_alignment": self.failover_aligned,
            "synchronization_status": "SYNCHRONIZED" if all(drift < 5.0 for drift in self.device_drifts.values()) else "DRIFT_ALERT"
        }
