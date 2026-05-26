import logging
from typing import Dict, Any

logger = logging.getLogger("cyber_defense.escalation")

class DefenseEscalator:
    """
    Manages transitions across 5 defense levels using hysteresis locks
    and defines operational constraints and permissions per level.
    """
    def __init__(self):
        self.current_level = "ADVISORY"
        
        # Hysteresis de-escalation counter (requires N stable ticks before down-grading)
        self.de_escalation_counter = 0
        self.hysteresis_ticks = 10  # ~10 seconds at 1Hz

        # Specifications for each defense escalation mode
        self.MODE_SPECS = {
            "ADVISORY": {
                "operator_authority": "FULL",
                "rl_permissions": "ALLOWED",
                "restoration_permissions": "ALLOWED",
                "containment_aggressiveness": "LOW",
                "telemetry_trust_threshold": 50.0,
                "rollback_restrictions": "NONE"
            },
            "ASSISTED_DEFENSE": {
                "operator_authority": "CONFIRM_REQUIRED",
                "rl_permissions": "ALLOWED",
                "restoration_permissions": "CONFIRM_REQUIRED",
                "containment_aggressiveness": "LOW",
                "telemetry_trust_threshold": 60.0,
                "rollback_restrictions": "NONE"
            },
            "AUTONOMOUS_DEFENSE": {
                "operator_authority": "OVERRIDE_ONLY",
                "rl_permissions": "RESTRICTED",  # Only allowed in clean zones
                "restoration_permissions": "RESTRICTED",
                "containment_aggressiveness": "MEDIUM",
                "telemetry_trust_threshold": 70.0,
                "rollback_restrictions": "RECOMMENDED"
            },
            "EMERGENCY_CONTAINMENT": {
                "operator_authority": "OVERRIDE_ONLY",
                "rl_permissions": "BLOCKED",
                "restoration_permissions": "BLOCKED",
                "containment_aggressiveness": "HIGH",
                "telemetry_trust_threshold": 80.0,
                "rollback_restrictions": "FORCE"
            },
            "GRID_PRESERVATION": {
                "operator_authority": "MONITOR_ONLY",
                "rl_permissions": "BLOCKED",
                "restoration_permissions": "BLOCKED",
                "containment_aggressiveness": "CRITICAL",
                "telemetry_trust_threshold": 90.0,
                "rollback_restrictions": "FORCE"
            }
        }

    def evaluate_escalation(self,
                            threat_score: int,
                            campaign_severity: int,
                            physics_anomaly: float,
                            pinn_confidence: float,
                            islanding_active: bool,
                            stability_score: float) -> Dict[str, Any]:
        """
        Determines the appropriate defense escalation level with hysteresis protection.
        """
        # Determine target escalation level based on metrics
        target_level = "ADVISORY"
        
        if stability_score < 40.0 or islanding_active or threat_score >= 80:
            target_level = "GRID_PRESERVATION"
        elif campaign_severity >= 70 or threat_score >= 65 or physics_anomaly >= 60.0:
            target_level = "EMERGENCY_CONTAINMENT"
        elif campaign_severity >= 40 or threat_score >= 40 or physics_anomaly >= 30.0:
            target_level = "AUTONOMOUS_DEFENSE"
        elif campaign_severity > 10 or threat_score >= 25 or physics_anomaly >= 15.0:
            target_level = "ASSISTED_DEFENSE"

        # Apply Hysteresis transitions
        levels_order = ["ADVISORY", "ASSISTED_DEFENSE", "AUTONOMOUS_DEFENSE", "EMERGENCY_CONTAINMENT", "GRID_PRESERVATION"]
        current_idx = levels_order.index(self.current_level)
        target_idx = levels_order.index(target_level)

        if target_idx > current_idx:
            # Escalate instantly
            logger.warning(f"[ESCALATION] Cyber-physical anomalies detected! Escalating: {self.current_level} -> {target_level}")
            self.current_level = target_level
            self.de_escalation_counter = 0
        elif target_idx < current_idx:
            # De-escalate only if target is lower and hysteresis ticks elapsed
            self.de_escalation_counter += 1
            if self.de_escalation_counter >= self.hysteresis_ticks:
                logger.info(f"[ESCALATION] Grid stabilized. De-escalating: {self.current_level} -> {target_level}")
                self.current_level = target_level
                self.de_escalation_counter = 0
            else:
                # Keep current level but log remaining ticks
                logger.debug(f"[ESCALATION] Hysteresis active. Remaining de-escalate ticks: {self.hysteresis_ticks - self.de_escalation_counter}")
        else:
            # Stable level
            self.de_escalation_counter = 0

        # Retrieve permissions for current level
        specs = self.MODE_SPECS[self.current_level]
        
        return {
            "escalation_level": self.current_level,
            "operator_authority": specs["operator_authority"],
            "rl_permissions": specs["rl_permissions"],
            "restoration_permissions": specs["restoration_permissions"],
            "containment_aggressiveness": specs["containment_aggressiveness"],
            "telemetry_trust_threshold": specs["telemetry_trust_threshold"],
            "rollback_restrictions": specs["rollback_restrictions"],
            "de_escalation_progress_pct": int((self.de_escalation_counter / self.hysteresis_ticks) * 100) if target_idx < current_idx else 0
        }
