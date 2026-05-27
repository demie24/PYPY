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
        self.latest_threat: Optional[Dict[str, Any]] = None
        self.latest_ai_prediction: Optional[Dict[str, Any]] = None
        self.latest_ai_forecast_multi_bus: Optional[Dict[str, Any]] = None
        self.latest_ai_threat_forecast: Optional[Dict[str, Any]] = None
        self.latest_pinn_forecast: Optional[Dict[str, Any]] = None
        self.latest_physics_validation: Optional[Dict[str, Any]] = None
        self.latest_trust_scores: Optional[Dict[str, Any]] = None
        self.latest_adaptive_filter: Optional[Dict[str, Any]] = None
        self.latest_ai_orchestrator: Optional[Dict[str, Any]] = None
        self.latest_recommended_actions: Optional[Dict[str, Any]] = None
        self.latest_pre_rl: Optional[Dict[str, Any]] = None
        self.latest_defense: Optional[Dict[str, Any]] = None
        self.latest_l6_recovery: Optional[Dict[str, Any]] = None
        
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

    def update_threat(self, threat: Dict[str, Any]):
        self.latest_threat = threat

    def update_ai_prediction(self, ai_pred: Dict[str, Any]):
        self.latest_ai_prediction = ai_pred

    def update_ai_forecast_multi_bus(self, ai_forecast: Dict[str, Any]):
        self.latest_ai_forecast_multi_bus = ai_forecast

    def update_ai_threat_forecast(self, ai_threat: Dict[str, Any]):
        self.latest_ai_threat_forecast = ai_threat

    def update_pinn_forecast(self, pinn_forecast: Dict[str, Any]):
        self.latest_pinn_forecast = pinn_forecast

    def update_physics_validation(self, physics_val: Dict[str, Any]):
        self.latest_physics_validation = physics_val

    def update_trust_scores(self, trust_scores: Dict[str, Any]):
        self.latest_trust_scores = trust_scores

    def update_adaptive_filter(self, adaptive_filter: Dict[str, Any]):
        self.latest_adaptive_filter = adaptive_filter

    def update_ai_orchestrator(self, ai_orchestrator: Dict[str, Any]):
        self.latest_ai_orchestrator = ai_orchestrator

    def update_recommended_actions(self, recommended_actions: Dict[str, Any]):
        self.latest_recommended_actions = recommended_actions

    def update_pre_rl(self, pre_rl: Dict[str, Any]):
        self.latest_pre_rl = pre_rl

    def update_defense(self, defense: Dict[str, Any]):
        self.latest_defense = defense

    def update_l6_recovery(self, l6_recovery: Dict[str, Any]):
        self.latest_l6_recovery = l6_recovery

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
            "config": self.latest_config,
            "threat": self.latest_threat,
            "ai_prediction": self.latest_ai_prediction,
            "ai_forecast_multi_bus": self.latest_ai_forecast_multi_bus,
            "ai_threat_forecast": self.latest_ai_threat_forecast,
            "pinn_forecast": self.latest_pinn_forecast,
            "physics_validation": self.latest_physics_validation,
            "trust_scores": self.latest_trust_scores,
            "adaptive_filter": self.latest_adaptive_filter,
            "ai_orchestrator": self.latest_ai_orchestrator,
            "recommended_actions": self.latest_recommended_actions,
            "pre_rl": self.latest_pre_rl,
            "defense": self.latest_defense,
            "l6_recovery": self.latest_l6_recovery
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
