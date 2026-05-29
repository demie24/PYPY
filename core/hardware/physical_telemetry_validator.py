import time
import math
import logging
from typing import Dict, Any, List, Tuple

logger = logging.getLogger("hardware.telemetry_validator")

class PhysicalTelemetryValidator:
    def __init__(self):
        self.telemetry_history: List[Dict[str, float]] = []
        self.max_history = 10
        self.alerts: List[str] = []
        self.integrity_score = 100.0

    def validate_telemetry_integrity(self, telemetry_payload: Dict[str, Any], relays: Dict[str, Any]) -> Tuple[bool, float, List[str]]:
        """
        Validates incoming sensor readings against physical constraints and history.
        Returns (is_valid, integrity_score, alerts).
        """
        self.alerts = []
        deductions = 0.0
        
        sensors = telemetry_payload.get("sensors", {})
        if not sensors:
            self.integrity_score = 0.0
            self.alerts.append("EMPTY_TELEMETRY_PAYLOAD")
            return False, 0.0, self.alerts

        # 1. Bounds and NaN Checks
        for key, val in sensors.items():
            if val is None or (isinstance(val, float) and (math.isnan(val) or math.isinf(val))):
                deductions += 20.0
                self.alerts.append(f"CORRUPT_SENSOR_VALUE: {key} is NaN or Inf")
                continue

            # Bounds validation
            if "_v" in key:  # Bus Voltage (pu)
                if val < 0.0 or val > 1.3:
                    deductions += 20.0
                    self.alerts.append(f"VOLTAGE_OUT_OF_BOUNDS: {key}={val:.3f} pu (expected 0.0-1.3)")
            elif "_i" in key:  # Line Current (pu)
                if val < 0.0 or val > 3.0:
                    deductions += 20.0
                    self.alerts.append(f"CURRENT_OUT_OF_BOUNDS: {key}={val:.3f} pu (expected 0.0-3.0)")
            elif "_temp" in key:  # Line Temperature (C)
                if val < -10.0 or val > 120.0:
                    deductions += 20.0
                    self.alerts.append(f"TEMPERATURE_OUT_OF_BOUNDS: {key}={val:.1f} C (expected -10-120)")

        # 2. Breaker State vs Current Flow Consistency Checks
        for breaker_id, relay_data in relays.items():
            feedback = relay_data.get("feedback")
            # Construct line current sensor key
            current_key = f"line_{breaker_id}_i"
            
            if current_key in sensors:
                current_val = sensors[current_key]
                if current_val is not None and not math.isnan(current_val):
                    # Consistency check: If open, current must be 0
                    if feedback == "OPEN" and current_val > 0.05:
                        deductions += 25.0
                        self.alerts.append(f"BREAKER_CURRENT_DESYNC: {breaker_id} feedback is OPEN but {current_key}={current_val:.3f} pu")

        # 3. Rate of Change Checks
        if self.telemetry_history:
            prev_sensors = self.telemetry_history[-1]
            for key, val in sensors.items():
                if key in prev_sensors and val is not None and prev_sensors[key] is not None:
                    delta = abs(val - prev_sensors[key])
                    # Alert on physical impossibilities (sudden huge voltage jumps in 1s)
                    if "_v" in key and delta > 0.5:
                        deductions += 15.0
                        self.alerts.append(f"IMPOSSIBLE_RATE_OF_CHANGE: {key} jumped by {delta:.3f} pu in 1s")

        # Record to history for stale checks
        self.telemetry_history.append(sensors.copy())
        if len(self.telemetry_history) > self.max_history:
            self.telemetry_history.pop(0)

        # 4. Stale Sensor Checks (0 variance over 10 consecutive ticks)
        if len(self.telemetry_history) == self.max_history:
            for key in sensors.keys():
                vals = [h[key] for h in self.telemetry_history if key in h and h[key] is not None and not math.isnan(h[key])]
                if len(vals) == self.max_history:
                    # Check if standard deviation is exactly 0.0 (no change at all)
                    mean = sum(vals) / len(vals)
                    variance = sum((x - mean) ** 2 for x in vals) / len(vals)
                    # Ignore temperature if exactly 25.0 ambient defaults, but check current / voltages
                    if variance == 0.0 and ("_v" in key or "_i" in key) and mean > 0.0:
                        deductions += 15.0
                        self.alerts.append(f"STALE_SENSOR_ALERT: {key} value is static at {mean:.4f}")

        # Compute final integrity score
        self.integrity_score = max(0.0, 100.0 - deductions)
        is_valid = self.integrity_score >= 70.0
        
        if len(self.alerts) > 0:
            logger.warning(f"Telemetry integrity score degraded to {self.integrity_score:.1f}. Active alerts: {self.alerts}")
            
        return is_valid, self.integrity_score, self.alerts

    def get_telemetry_payload(self) -> Dict[str, Any]:
        """
        Returns telemetry overview for validation reporting.
        """
        return {
            "timestamp": int(time.time() * 1000),
            "telemetry_integrity_score": round(self.integrity_score, 1),
            "alerts": self.alerts,
            "status": "NOMINAL" if self.integrity_score >= 90.0 else ("WARNING" if self.integrity_score >= 70.0 else "COMPROMISED")
        }
