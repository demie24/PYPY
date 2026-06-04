import logging
from typing import Dict, Any, List

logger = logging.getLogger("adversarial.defense_evaluator")

class DefenseEvaluator:
    def __init__(self):
        pass

    def evaluate_defense(self, campaign: Dict[str, Any], events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Evaluate defensive reaction timing (detection, containment, restoration, trust recovery).
        """
        campaign_id = campaign.get("campaign_id", "CAMP_UNKNOWN")
        campaign_start = campaign.get("timestamp", 0) / 1000.0  # Convert to seconds

        detection_time = None
        containment_time = None
        restoration_time = None
        trust_recovery_time = 0.0

        for e in events:
            evt_text = e.get("event", "").upper()
            evt_ts = e.get("timestamp", 0) / 1000.0

            # 1. Detection timestamp (when anomaly or attack was detected)
            if not detection_time:
                if any(kw in evt_text for kw in ["ANOMALY DETECTED", "ATTACK DETECTED", "CYBER_ATTACK", "INTRUSION"]):
                    detection_time = evt_ts

            # 2. Containment timestamp (when isolation was completed)
            if detection_time and not containment_time:
                if any(kw in evt_text for kw in ["ISOLATED", "QUARANTINED", "BREAKER TRIP", "CONTAINED"]):
                    containment_time = evt_ts

            # 3. Restoration timestamp (when normal recovery completes)
            if containment_time and not restoration_time:
                if any(kw in evt_text for kw in ["RESTORED", "RECONNECTED", "NORMAL OPERATIONS", "RECOVERED"]):
                    restoration_time = evt_ts

        # Compute delays in seconds (with reasonable defaults if steps are missing)
        detection_delay = float(round(detection_time - campaign_start, 2)) if detection_time else 15.0
        containment_delay = float(round(containment_time - detection_time, 2)) if (containment_time and detection_time) else 20.0
        restoration_delay = float(round(restoration_time - containment_time, 2)) if (restoration_time and containment_time) else 30.0
        
        # Simulating trust recovery time based on events
        trust_recovery_time = 45.0 if restoration_time else 60.0

        # Calculate effectiveness metrics
        detected = (detection_time is not None)
        contained = (containment_time is not None)
        restored = (restoration_time is not None)

        detection_accuracy = 1.0 if detected else 0.0
        mitigation_success = contained and restored

        # Calculate overall score in [0.0, 1.0] (lower delay + success = higher rating)
        raw_rating = 0.0
        if detected:
            raw_rating += 0.30 * (1.0 - min(1.0, detection_delay / 30.0))
        if contained:
            raw_rating += 0.30 * (1.0 - min(1.0, containment_delay / 40.0))
        if restored:
            raw_rating += 0.40 * (1.0 - min(1.0, restoration_delay / 60.0))

        overall_defense_rating = float(round(max(0.10, min(1.0, raw_rating)), 2))

        return {
            "campaign_id": campaign_id,
            "detection_delay": detection_delay,
            "containment_delay": containment_delay,
            "restoration_delay": restoration_delay,
            "trust_recovery_time": trust_recovery_time,
            "detection_accuracy": detection_accuracy,
            "mitigation_success": mitigation_success,
            "overall_defense_rating": overall_defense_rating
        }
