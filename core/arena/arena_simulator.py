import random
from typing import Dict, Any, Tuple

class ArenaSimulator:
    def __init__(self):
        pass

    def run_match(
        self, 
        red_action: Tuple[str, str, float, float], 
        blue_action: Tuple[float, str, float, str]
    ) -> Dict[str, Any]:
        """
        Simulate a match round between the Red Attacker and Blue Defender.
        """
        target, attack_type, severity, stealth = red_action
        anomaly_threshold, trust_decay_speed, rollback_lockout, routing_strategy = blue_action

        # 1. Calculate Detection Delay
        # High stealth + high anomaly threshold = slow detection
        detection_delay = 1.0 + (stealth * 12.0) * (anomaly_threshold * 2.5)

        # 2. Calculate Containment Delay
        # Fast trust decay and redundant routing isolation speeds containment
        base_containment = 4.0
        if trust_decay_speed == "FAST":
            base_containment -= 2.0
        elif trust_decay_speed == "SLOW":
            base_containment += 4.0

        if routing_strategy == "ISOLATE_ONLY":
            base_containment -= 1.0
        elif routing_strategy == "REDUNDANT_PATH":
            base_containment -= 0.5

        containment_delay = max(1.0, base_containment)

        # 3. Calculate Restoration Delay
        # Bounded by rollback lockout timers
        restoration_delay = 5.0 + (rollback_lockout / 8.0)
        if routing_strategy == "REDUNDANT_PATH":
            restoration_delay -= 2.0

        # 4. Calculate Grid Deviations (Impact)
        # Larger severity + longer detection delay before containment = higher grid impact
        exposure_time = detection_delay + containment_delay
        voltage_deviation = min(0.35, severity * (exposure_time / 20.0))
        frequency_deviation = min(0.15, severity * (exposure_time / 40.0))

        # 5. Determine success parameters
        mitigation_success = (exposure_time < 18.0) and (voltage_deviation < 0.25)
        
        # Anomaly threshold <= 0.3 introduces false alarm risk
        false_alarm = True if (anomaly_threshold <= 0.3 and random.random() < 0.25) else False

        # Build simulated event list
        events = [
            {"event": f"Red launched {attack_type} on {target} (severity={severity}, stealth={stealth})"},
            {"event": f"Blue scanning with threshold={anomaly_threshold}, decay={trust_decay_speed}"},
            {"event": f"Threat detected after {detection_delay:.2f}s"},
            {"event": f"Threat isolated after {containment_delay:.2f}s using strategy {routing_strategy}"},
            {"event": f"Grid operations restored after {restoration_delay:.2f}s"}
        ]

        # Build simulated final telemetry
        telemetry = {
            "voltage_pu": max(0.8, 1.0 - voltage_deviation),
            "frequency_hz": max(59.0, 60.0 - frequency_deviation)
        }

        return {
            "detection_delay": round(detection_delay, 2),
            "containment_delay": round(containment_delay, 2),
            "restoration_delay": round(restoration_delay, 2),
            "voltage_deviation": round(voltage_deviation, 3),
            "frequency_deviation": round(frequency_deviation, 3),
            "mitigation_success": mitigation_success,
            "false_alarm": false_alarm,
            "events": events,
            "telemetry": telemetry
        }
