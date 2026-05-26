import time
import logging
from typing import Dict, Any, List

logger = logging.getLogger("self_healing.restoration_timeline")

class RestorationTimeline:
    """
    Chronologically tracks grid attack detection, telemetry degradation, topology shifts,
    AI action selection, rollbacks, and restoration success outcomes.
    """
    def __init__(self):
        self.events: List[Dict[str, Any]] = []
        self.max_events = 50

        # Record baseline initialization event
        self.record_event(
            category="STATUS_UPDATE",
            description="Autonomous pre-RL restoration timeline tracker initialized."
        )

    def record_event(self, category: str, description: str, state_change: Dict[str, Any] = None):
        """
        Appends a cyber-physical event to the restoration timeline stack.
        
        Categories:
            - ATTACK_DETECTED
            - TELEMETRY_DEGRADED
            - TOPOLOGY_INSTABILITY
            - ACTION_SELECTED
            - RESTORATION_INITIATED
            - ROLLBACK_TRIGGERED
            - STATUS_UPDATE
            - RESTORATION_SUCCESS
            - RESTORATION_FAILURE
        """
        valid_categories = [
            "ATTACK_DETECTED", "TELEMETRY_DEGRADED", "TOPOLOGY_INSTABILITY",
            "ACTION_SELECTED", "RESTORATION_INITIATED", "ROLLBACK_TRIGGERED",
            "STATUS_UPDATE", "RESTORATION_SUCCESS", "RESTORATION_FAILURE"
        ]
        if category not in valid_categories:
            logger.warning(f"Timeline received unrecognized event category: {category}")

        event = {
            "timestamp": int(time.time() * 1000),
            "category": category,
            "description": description,
            "state_change": state_change if state_change else {}
        }
        
        self.events.append(event)
        
        # Enforce history limit
        if len(self.events) > self.max_events:
            self.events.pop(0)

        logger.info(f"[TIMELINE EVENT] {category}: {description}")

    def clear(self):
        """
        Clears the timeline history.
        """
        self.events = []
        self.record_event("STATUS_UPDATE", "Timeline cleared by operator.")

    def get_timeline_payload(self) -> List[Dict[str, Any]]:
        """
        Returns the timeline history for dashboard streaming.
        """
        # Return reversed history to show newest events first on the dashboard
        return list(reversed(self.events))
