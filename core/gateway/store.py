import time
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger("gateway.store")

class MemoryStore:
    def __init__(self, max_history: int = 100):
        self.max_history = max_history
        self.latest_telemetry: Optional[Dict[str, Any]] = None
        self.events: List[Dict[str, Any]] = []
        self.alerts: List[Dict[str, Any]] = []
        self.latest_config: Dict[str, Any] = {}
        
        # Add initial system startup event
        self.add_event({
            "timestamp": int(time.time() * 1000),
            "source": "GATEWAY",
            "event": "Gateway communication service initialized. Standing by for telemetry...",
            "severity": "INFO"
        })

    def update_telemetry(self, telemetry: Dict[str, Any]):
        self.latest_telemetry = telemetry

    def update_config(self, config: Dict[str, Any]):
        self.latest_config.update(config)

    def add_event(self, event: Dict[str, Any]):
        self.events.append(event)
        if len(self.events) > self.max_history:
            self.events.pop(0)

    def add_alert(self, alert: Dict[str, Any]):
        self.alerts.append(alert)
        if len(self.alerts) > self.max_history:
            self.alerts.pop(0)
            
    def get_bootstrap_payload(self) -> Dict[str, Any]:
        """
        Returns the initialization payload for newly connected clients.
        """
        return {
            "type": "BOOTSTRAP",
            "telemetry": self.latest_telemetry,
            "events": self.events,
            "alerts": self.alerts,
            "config": self.latest_config
        }

    def clear_alerts(self):
        self.alerts = []
        self.add_event({
            "timestamp": int(time.time() * 1000),
            "source": "GATEWAY",
            "event": "Alert history cleared by operator command.",
            "severity": "INFO"
        })

store = MemoryStore()
