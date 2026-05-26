import time
import logging
from typing import Dict, Any, List

logger = logging.getLogger("cyber_defense.adaptive_engine")

class AdaptiveDefenseEngine:
    """
    Learns attacker behavioral traits statefully (timing, persistence) and adapts
    trust thresholds, filtering coefficients, and containment severity dynamically.
    """
    def __init__(self):
        # Persistence tracking: target -> consecutive ticks flagged as anomalous
        self.anomaly_persistence = {}
        # Repeated attacks tracker: list of (timestamp, alert_count)
        self.attack_history = []
        # Attacker timing: intervals between attacks (in seconds)
        self.observed_attack_intervals = []
        self.last_attack_time = 0.0

        # Output adaptive configuration variables
        self.adaptive_trust_threshold = 50.0  # Base trust threshold
        self.trust_penalty_multiplier = 1.0   # Scale trust degradation speed
        self.filtering_smoothing_alpha = 0.40 # Base telemetry filtering EMA
        self.containment_severity_multiplier = 1.0 # Containment escalation level

    def update_and_adapt(self,
                         telemetry: Dict[str, Any],
                         alerts: List[Dict[str, Any]],
                         current_trust_scores: Dict[str, Any]) -> Dict[str, Any]:
        """
        Updates internal attacker behavioral profiles and adapts dynamic filters/thresholds.
        """
        now = time.time()
        
        # 1. Update Anomaly Persistence Tracking
        active_suspects = set()
        for alert in alerts:
            suspect = alert.get("suspect_node") or alert.get("target")
            if suspect:
                active_suspects.add(suspect)
                self.anomaly_persistence[suspect] = self.anomaly_persistence.get(suspect, 0) + 1
        
        # Decay persistence for targets no longer flagged
        decayed_targets = []
        for target in list(self.anomaly_persistence.keys()):
            if target not in active_suspects:
                self.anomaly_persistence[target] = max(0, self.anomaly_persistence[target] - 1)
                if self.anomaly_persistence[target] == 0:
                    decayed_targets.append(target)
        for t in decayed_targets:
            self.anomaly_persistence.pop(t, None)

        # 2. Repeated Attack & Timing Recognition
        if len(alerts) > 0:
            if self.last_attack_time > 0.0:
                interval = now - self.last_attack_time
                # Register intervals only if they represent discrete attack phases (>15s)
                if interval > 15.0:
                    self.observed_attack_intervals.append(interval)
                    if len(self.observed_attack_intervals) > 5:
                        self.observed_attack_intervals.pop(0)
                    logger.info(f"[ADAPTIVE AI] Attacker timing interval recognized: {interval:.1f}s")
            
            self.last_attack_time = now
            self.attack_history.append((now, len(alerts)))
            
        # Clean history older than 180s
        self.attack_history = [h for h in self.attack_history if now - h[0] < 180.0]

        # 3. Compute Adaptive Thresholds
        max_persistence = max(self.anomaly_persistence.values()) if self.anomaly_persistence else 0
        total_recent_alerts = sum(h[1] for h in self.attack_history)
        
        # Attacker persistence shifts dynamic multipliers
        if max_persistence > 10:
            # Persistent anomaly -> escalate sensitivity and containment severity
            self.adaptive_trust_threshold = 70.0  # Degrade earlier
            self.trust_penalty_multiplier = 2.0   # Fast degradation
            self.filtering_smoothing_alpha = 0.15 # Filter spikes extremely heavily
            self.containment_severity_multiplier = 2.0
            logger.warning("[ADAPTIVE AI] Persistent anomaly detected. Escalating filters & containment sensitivity.")
        elif total_recent_alerts > 15:
            # High frequency repeated attacks -> increase sensitivity
            self.adaptive_trust_threshold = 60.0
            self.trust_penalty_multiplier = 1.5
            self.filtering_smoothing_alpha = 0.25
            self.containment_severity_multiplier = 1.5
            logger.info("[ADAPTIVE AI] Repeated high-frequency alert pattern. Adapting thresholds.")
        else:
            # Normal baseline
            self.adaptive_trust_threshold = 50.0
            self.trust_penalty_multiplier = 1.0
            self.filtering_smoothing_alpha = 0.40
            self.containment_severity_multiplier = 1.0

        # Predict next attack window if interval patterns are stable
        next_attack_in = None
        if len(self.observed_attack_intervals) >= 2:
            mean_interval = sum(self.observed_attack_intervals) / len(self.observed_attack_intervals)
            elapsed = now - self.last_attack_time
            next_attack_in = max(0.0, mean_interval - elapsed)

        return {
            "adaptive_trust_threshold": float(self.adaptive_trust_threshold),
            "trust_penalty_multiplier": float(self.trust_penalty_multiplier),
            "filtering_smoothing_alpha": float(self.filtering_smoothing_alpha),
            "containment_severity_multiplier": float(self.containment_severity_multiplier),
            "persistence_matrix": self.anomaly_persistence.copy(),
            "next_attack_window_prediction_seconds": round(next_attack_in, 1) if next_attack_in is not None else None,
            "repeated_attack_detected": bool(total_recent_alerts > 15)
        }
