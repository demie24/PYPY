import time
import logging
from typing import Dict, Any, List

logger = logging.getLogger("self_healing.relay")

class ProtectiveRelay:
    def __init__(self):
        # ANSI 50/51: Overcurrent protection thresholds (p.u.)
        self.instantaneous_overcurrent_threshold = 3.5
        self.timed_overcurrent_threshold = 3.0
        self.timed_overcurrent_delay_frames = 2
        
        # ANSI 27: Undervoltage protection thresholds (p.u.)
        self.undervoltage_threshold = 0.90
        self.undervoltage_delay_frames = 3
        
        # Track state history for delay calculations
        # line_id -> count of consecutive frames exceeding threshold
        self.overcurrent_counters: Dict[str, int] = {}
        # bus_id -> count of consecutive frames below threshold
        self.undervoltage_counters: Dict[str, int] = {}
        
        # Track tripped breakers to prevent repeated actions
        self.tripped_devices: List[str] = []

    def reset_trips(self):
        self.tripped_devices.clear()
        self.overcurrent_counters.clear()
        self.undervoltage_counters.clear()
        logger.info("Relay protection tripped devices state reset.")

    def evaluate_telemetry(self, telemetry: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Evaluates current grid telemetry.
        Returns a list of control commands to issue (tripping breakers).
        """
        commands = []
        state = telemetry.get("state", {})
        lines = state.get("lines", {})
        buses = state.get("buses", {})
        breakers = state.get("breakers", {})
        
        timestamp = telemetry.get("timestamp", int(time.time() * 1000))

        # Evaluate ANSI 50/51 (Overcurrent Protection) for lines
        for lid, line_data in lines.items():
            # Only evaluate lines that are closed
            if breakers.get(lid) != "CLOSED":
                self.overcurrent_counters[lid] = 0
                continue
                
            current = line_data.get("current_pu", 0.0)
            
            # ANSI 50: Instantaneous Overcurrent Trip
            if current >= self.instantaneous_overcurrent_threshold:
                if lid not in self.tripped_devices:
                    self.tripped_devices.append(lid)
                    commands.append(self._create_trip_command(lid, "ANSI 50 (Instantaneous Overcurrent)", current, timestamp))
                    logger.warning(f"ANSI 50 Instantaneous Overcurrent trip triggered on line {lid}. Current: {current} p.u.")
                continue

            # ANSI 51: Timed Overcurrent Trip
            if current >= self.timed_overcurrent_threshold:
                self.overcurrent_counters[lid] = self.overcurrent_counters.get(lid, 0) + 1
                if self.overcurrent_counters[lid] >= self.timed_overcurrent_delay_frames:
                    if lid not in self.tripped_devices:
                        self.tripped_devices.append(lid)
                        commands.append(self._create_trip_command(lid, "ANSI 51 (Timed Overcurrent)", current, timestamp))
                        logger.warning(f"ANSI 51 Timed Overcurrent trip triggered on line {lid}. Current: {current} p.u. for {self.timed_overcurrent_delay_frames} frames")
            else:
                self.overcurrent_counters[lid] = 0

        # Evaluate ANSI 27 (Undervoltage Protection) for load buses
        for bid, bus_data in buses.items():
            if not bus_data.get("is_load", False):
                continue
                
            voltage = bus_data.get("voltage_pu", 0.0)
            
            # An undervoltage trip should only trigger if the bus is supposed to be energized
            # If the voltage is already collapsed to 0, it means it's de-energized, not that it's experiencing undervoltage stress
            if 0.1 < voltage < self.undervoltage_threshold:
                self.undervoltage_counters[bid] = self.undervoltage_counters.get(bid, 0) + 1
                if self.undervoltage_counters[bid] >= self.undervoltage_delay_frames:
                    # Find associated breaker feeding this bus to trip
                    feeding_breaker = self._find_feeding_breaker(bid, breakers)
                    if feeding_breaker and feeding_breaker not in self.tripped_devices:
                        self.tripped_devices.append(feeding_breaker)
                        commands.append(self._create_trip_command(feeding_breaker, f"ANSI 27 (Undervoltage on {bid})", voltage, timestamp))
                        logger.warning(f"ANSI 27 Undervoltage trip triggered on {bid}. Voltage: {voltage} p.u.")
            else:
                self.undervoltage_counters[bid] = 0

        return commands

    def _create_trip_command(self, line_id: str, code: str, value: float, timestamp: int) -> Dict[str, Any]:
        return {
            "type": "TRIP_ACTION",
            "command": "OPEN",
            "target": line_id,
            "event_log": {
                "timestamp": timestamp,
                "source": f"RELAY_IED_{line_id}",
                "event": f"Relay Trip [{code}] triggered breaker OPEN for '{line_id}'. Parameter: {value:.2f} p.u.",
                "severity": "CRITICAL"
            }
        }

    def _find_feeding_breaker(self, bus_id: str, breakers: Dict[str, str]) -> str:
        """
        Finds a line breaker connected to this bus. Simplified mapping for IEEE 9-bus.
        - Bus 5 index 4 is fed by line L4_5 and line L5_6
        - Bus 6 index 5 is fed by line L5_6 and L6_7
        - Bus 8 index 7 is fed by line L7_8 and L8_9
        """
        bus_num = int(bus_id.split("_")[1])
        if bus_num == 5:
            # Trip L4_5 if CLOSED
            if breakers.get("L4_5") == "CLOSED": return "L4_5"
            if breakers.get("L5_6") == "CLOSED": return "L5_6"
        elif bus_num == 6:
            if breakers.get("L5_6") == "CLOSED": return "L5_6"
            if breakers.get("L6_7") == "CLOSED": return "L6_7"
        elif bus_num == 8:
            if breakers.get("L8_9") == "CLOSED": return "L8_9"
            if breakers.get("L7_8") == "CLOSED": return "L7_8"
        return ""
