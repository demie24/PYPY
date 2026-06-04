import time
import random
import uuid
from typing import Dict, Any, List

class AttackPatternGenerator:
    CAMPAIGN_TYPES = [
        "FDIA_ESCALATION",
        "TRUST_POISONING",
        "TELEMETRY_MANIPULATION",
        "COORDINATED_MULTI_NODE",
        "STEALTHY_LOW_RATE"
    ]

    def __init__(self):
        pass

    def generate_campaign(self, campaign_type: str, target_node: str = None) -> Dict[str, Any]:
        """
        Generates realistic simulated attack campaign sequences.
        """
        if campaign_type not in self.CAMPAIGN_TYPES:
            campaign_type = "TELEMETRY_MANIPULATION"

        campaign_id = f"CAMP_{uuid.uuid4().hex[:8].upper()}"
        target = target_node if target_node else "Bus_5"

        sequence: List[Dict[str, Any]] = []
        severity = 0.50
        stealth_score = 0.50

        if campaign_type == "FDIA_ESCALATION":
            # Multi-step False Data Injection Attack targeting voltage and frequency
            severity = 0.80
            stealth_score = 0.35
            sequence = [
                {"step": 1, "type": "INJECT_VOLTAGE_DRIFT", "target": target, "value": -0.05, "duration": 5},
                {"step": 2, "type": "INJECT_VOLTAGE_DRIFT", "target": target, "value": -0.12, "duration": 10},
                {"step": 3, "type": "INJECT_FREQUENCY_SPOOF", "target": target, "value": 57.5, "duration": 15}
            ]

        elif campaign_type == "TRUST_POISONING":
            # Slowly poison trust score by producing repeated mini-anomalies
            severity = 0.45
            stealth_score = 0.80
            sequence = [
                {"step": 1, "type": "MINOR_VOLTAGE_JITTER", "target": target, "value": 0.02, "duration": 15},
                {"step": 2, "type": "MINOR_VOLTAGE_JITTER", "target": target, "value": -0.03, "duration": 15},
                {"step": 3, "type": "TRUST_POISON_SWEEP", "target": target, "value": 0.05, "duration": 20}
            ]

        elif campaign_type == "TELEMETRY_MANIPULATION":
            # Manipulate capacity and breaker state reporting
            severity = 0.60
            stealth_score = 0.65
            sequence = [
                {"step": 1, "type": "SPOOF_BREAKER_STATE", "target": "L4_5", "value": "OPEN", "duration": 10},
                {"step": 2, "type": "SPOOF_LINE_CAPACITY", "target": "L4_5", "value": 120.0, "duration": 15}
            ]

        elif campaign_type == "COORDINATED_MULTI_NODE":
            # Synchronized attack targeting primary and adjacent buses
            severity = 0.90
            stealth_score = 0.20
            adjacent = "Bus_6" if target == "Bus_5" else "Bus_5"
            sequence = [
                {"step": 1, "type": "VOLTAGE_SPOOF", "target": target, "value": 0.82, "duration": 10},
                {"step": 2, "type": "VOLTAGE_SPOOF", "target": adjacent, "value": 0.84, "duration": 10},
                {"step": 3, "type": "TRIP_BREAKER", "target": "L5_6", "value": "TRIPPED", "duration": 15}
            ]

        elif campaign_type == "STEALTHY_LOW_RATE":
            # Stealth attack designed to fly below anomaly detector thresholds
            severity = 0.35
            stealth_score = 0.95
            sequence = [
                {"step": 1, "type": "STEALTH_DRIFT", "target": target, "value": -0.015, "duration": 30},
                {"step": 2, "type": "STEALTH_DRIFT", "target": target, "value": -0.030, "duration": 30}
            ]

        return {
            "campaign_id": campaign_id,
            "campaign_type": campaign_type,
            "target": target,
            "severity": severity,
            "stealth_score": stealth_score,
            "attack_sequence": sequence,
            "timestamp": int(time.time() * 1000)
        }
