import time
import logging
from typing import Dict, Any, List

logger = logging.getLogger("cyber_defense.defense_memory")

class DefenseMemory:
    """
    Maintains stateful memory of previous attacks, containment actions, failed restores,
    and rollback events. Generates defense confidence trends and repeated attacker markers.
    """
    def __init__(self, max_history: int = 100):
        self.max_history = max_history
        self.attacks: List[Dict[str, Any]] = []
        self.containment_actions: List[Dict[str, Any]] = []
        self.failed_restorations: List[Dict[str, Any]] = []
        self.rollback_events: List[Dict[str, Any]] = []
        
        # Stateful markers
        self.defense_confidence_score = 100.0  # Base score
        self.repeated_attacker_detected = False

    def record_attack(self, target: str, attack_type: str, severity: float):
        now = time.time()
        self.attacks.append({
            "timestamp": now,
            "target": target,
            "attack_type": attack_type,
            "severity": severity
        })
        if len(self.attacks) > self.max_history:
            self.attacks.pop(0)
        self._evaluate_attacker_patterns()

    def record_containment(self, action: str, target: str, success: bool, reason: str = ""):
        now = time.time()
        self.containment_actions.append({
            "timestamp": now,
            "action": action,
            "target": target,
            "success": success,
            "reason": reason
        })
        if len(self.containment_actions) > self.max_history:
            self.containment_actions.pop(0)
        self._update_confidence()

    def record_failed_restoration(self, target: str, reason: str = ""):
        now = time.time()
        self.failed_restorations.append({
            "timestamp": now,
            "target": target,
            "reason": reason
        })
        if len(self.failed_restorations) > self.max_history:
            self.failed_restorations.pop(0)
        self._update_confidence()

    def record_rollback(self, action: Dict[str, Any], reason: str = ""):
        now = time.time()
        self.rollback_events.append({
            "timestamp": now,
            "action": action,
            "reason": reason
        })
        if len(self.rollback_events) > self.max_history:
            self.rollback_events.pop(0)
        self._update_confidence()

    def _update_confidence(self):
        """
        Dynamically adjusts defense confidence score based on historical performance.
        Failed restorations: -15% penalty.
        Rollback events: -10% penalty.
        Failed containments: -20% penalty.
        Successful containments: +5% recovery (capped at 100).
        """
        penalty = 0.0
        now = time.time()
        
        # Penalize for recent events (within last 60 seconds)
        recent_failed_restores = sum(1 for e in self.failed_restorations if now - e["timestamp"] < 60)
        recent_rollbacks = sum(1 for e in self.rollback_events if now - e["timestamp"] < 60)
        
        recent_failed_containments = sum(1 for e in self.containment_actions if not e["success"] and now - e["timestamp"] < 60)
        recent_success_containments = sum(1 for e in self.containment_actions if e["success"] and now - e["timestamp"] < 60)
        
        penalty += recent_failed_restores * 15.0
        penalty += recent_rollbacks * 10.0
        penalty += recent_failed_containments * 20.0
        
        recovery = recent_success_containments * 5.0
        
        new_score = 100.0 - penalty + recovery
        self.defense_confidence_score = max(10.0, min(100.0, new_score))

    def _evaluate_attacker_patterns(self):
        """
        Evaluates historical attacks to identify patterns such as:
        - Repeated target targeting (same node targeted multiple times)
        """
        now = time.time()
        recent_attacks = [a for a in self.attacks if now - a["timestamp"] < 120]
        
        targets = [a["target"] for a in recent_attacks]
        if len(targets) >= 3:
            for target in set(targets):
                if targets.count(target) >= 2:
                    self.repeated_attacker_detected = True
                    return
        self.repeated_attacker_detected = False

    def get_summary(self) -> Dict[str, Any]:
        return {
            "defense_confidence_score": round(self.defense_confidence_score, 1),
            "repeated_attacker_detected": self.repeated_attacker_detected,
            "total_attacks_recorded": len(self.attacks),
            "total_containments_recorded": len(self.containment_actions),
            "total_rollbacks_recorded": len(self.rollback_events),
            "total_failed_restorations": len(self.failed_restorations),
            "recent_rollbacks_count": sum(1 for e in self.rollback_events if time.time() - e["timestamp"] < 60)
        }
