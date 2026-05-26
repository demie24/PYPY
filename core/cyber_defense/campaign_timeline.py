import time
import logging
from typing import Dict, Any, List

logger = logging.getLogger("cyber_defense.campaign_timeline")

class CampaignTimeline:
    """
    Stateful ledger capturing forensic timelines of cyber campaigns.
    Links attacks, physical anomalies, escalation steps, containment dispatches,
    and operator overrides/restoration blocks chronologically.
    """
    def __init__(self, max_records: int = 150):
        self.max_records = max_records
        self.events: List[Dict[str, Any]] = []

    def record(self, event_type: str, message: str, details: Dict[str, Any] = None):
        """
        Appends an event to the timeline ledger.
        """
        now = time.time()
        event = {
            "timestamp": int(now * 1000),
            "event_type": event_type,
            "message": message,
            "details": details or {}
        }
        self.events.append(event)
        if len(self.events) > self.max_records:
            self.events.pop(0)
            
        logger.info(f"[TIMELINE] {event_type} | {message}")

    def get_events(self) -> List[Dict[str, Any]]:
        return self.events.copy()

    def clear(self):
        self.events.clear()
        logger.info("Timeline ledger cleared.")
