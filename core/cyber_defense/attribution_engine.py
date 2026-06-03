import logging
from typing import Dict, Any, List

logger = logging.getLogger("cyber_defense.attribution_engine")

class AttributionEngine:
    """
    Analyzes ongoing campaigns to suggest confidence-based threat actor attribution.
    Ties signatures and attack tactics to profiles without asserting absolute certainty.
    """
    def __init__(self):
        # Known threat actor profile definitions
        self.PROFILES = {
            "APT-GRID-TAMPERER": {
                "description": "Stealthy state-sponsored actor specializing in sensor telemetry spoofing and FDIA attacks.",
                "indicators": ["T0814", "Stealthy Voltage Bias", "High KCL Mismatch"],
                "base_confidence": 0.40
            },
            "APT-GRID-DISRUPTOR": {
                "description": "High-impact destructive actor targeting communications availability (DoS/Jamming) and line tripping.",
                "indicators": ["T0883", "T0861", "Communication Loss", "Cascading Breaker Trips"],
                "base_confidence": 0.35
            },
            "APT-REPLAY-SPOOFER": {
                "description": "Information gathering and evasion actor specializing in capturing and replaying historical telemetry.",
                "indicators": ["T0809", "Stale/Delayed Telemetry"],
                "base_confidence": 0.30
            }
        }

    def attribute_campaign(self, 
                          mitre_techniques: List[str], 
                          alerts: List[Dict[str, Any]], 
                          physics_val: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculates attribution probabilities based on indicators observed in the active campaign.
        """
        candidate_attribution = "UNKNOWN"
        max_confidence = 0.0
        indicators_matched = []

        # Determine features from current context
        has_fdia = any("T0814" in tech for tech in mitre_techniques)
        has_replay = any("T0809" in tech for tech in mitre_techniques)
        has_dos = any("T0883" in tech for tech in mitre_techniques) or any("T0861" in tech for tech in mitre_techniques)
        
        has_physics_anomaly = False
        if physics_val and physics_val.get("physics_anomaly_score", 0.0) > 30.0:
            has_physics_anomaly = True

        # Evaluate APT-GRID-TAMPERER likelihood
        if has_fdia:
            conf = self.PROFILES["APT-GRID-TAMPERER"]["base_confidence"]
            matched = ["T0814"]
            if has_physics_anomaly:
                conf += 0.35
                matched.append("High KCL Mismatch")
            if len(alerts) >= 2:
                conf += 0.15
                matched.append("Coordinated FDIA alerts")
            conf = min(0.95, conf)
            if conf > max_confidence:
                max_confidence = conf
                candidate_attribution = "APT-GRID-TAMPERER"
                indicators_matched = matched

        # Evaluate APT-GRID-DISRUPTOR likelihood
        if has_dos:
            conf = self.PROFILES["APT-GRID-DISRUPTOR"]["base_confidence"]
            matched = ["T0883"]
            has_breaker_trips = any("trip" in str(a.get("type", "")).lower() for a in alerts)
            if has_breaker_trips:
                conf += 0.35
                matched.append("Cascading Breaker Trips")
            if any("T0861" in tech for tech in mitre_techniques):
                conf += 0.15
                matched.append("Restoration Interception (T0861)")
            conf = min(0.95, conf)
            if conf > max_confidence:
                max_confidence = conf
                candidate_attribution = "APT-GRID-DISRUPTOR"
                indicators_matched = matched

        # Evaluate APT-REPLAY-SPOOFER likelihood
        if has_replay:
            conf = self.PROFILES["APT-REPLAY-SPOOFER"]["base_confidence"]
            matched = ["T0809"]
            if len(alerts) >= 2:
                conf += 0.40
                matched.append("Multiple Replay alerts")
            conf = min(0.95, conf)
            if conf > max_confidence:
                max_confidence = conf
                candidate_attribution = "APT-REPLAY-SPOOFER"
                indicators_matched = matched

        # If no techniques matched but alerts exist, default to unknown
        if max_confidence == 0.0 and (alerts or mitre_techniques):
            candidate_attribution = "UNKNOWN_APT"
            max_confidence = 0.25
            indicators_matched = ["Unclassified Intrusion Alerts"]

        return {
            "threat_actor": candidate_attribution,
            "confidence": round(max_confidence, 2),
            "indicators_matched": indicators_matched,
            "profile_description": self.PROFILES.get(candidate_attribution, {}).get("description", "No matching profile description.")
        }
