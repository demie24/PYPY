import time
import logging
from typing import Dict, Any, List

logger = logging.getLogger("assistant.predictive_coordination")

class PredictiveCoordinationEngine:
    def __init__(self, history_limit: int = 10):
        self.history_limit = history_limit
        self.latency_history: List[float] = []
        self.workflow_execution_history: Dict[str, List[float]] = {}
        self.forecasts: List[Dict[str, Any]] = []
        self.suggestions: List[Dict[str, Any]] = []
        self.last_suggestion_time = 0.0
        self.suggestion_cooldown = 30.0  # Avoid predictive spam safety rule

    def add_latency_point(self, latency: float) -> None:
        self.latency_history.append(latency)
        if len(self.latency_history) > self.history_limit:
            self.latency_history.pop(0)

    def record_workflow_duration(self, name: str, duration_sec: float) -> None:
        if name not in self.workflow_execution_history:
            self.workflow_execution_history[name] = []
        self.workflow_execution_history[name].append(duration_sec)
        if len(self.workflow_execution_history[name]) > self.history_limit:
            self.workflow_execution_history[name].pop(0)

    def predict_workflow_duration(self, name: str) -> float:
        history = self.workflow_execution_history.get(name, [])
        if not history:
            return 5.0  # Default nominal workflow execution estimate
        return round(sum(history) / len(history), 2)

    def analyze_trends(self, grid_state: Dict[str, Any], hardware_state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Lightweight predictive reasoning & recurring condition forecasting.
        Generates suggestions if trends point to latency spikes, drift, or connection loops.
        """
        now = time.time()
        self.forecasts = []

        # 1. Latency Spike Trend check
        if len(self.latency_history) >= 3:
            # Check if strictly increasing
            if all(self.latency_history[i] < self.latency_history[i+1] for i in range(len(self.latency_history)-1)):
                last_val = self.latency_history[-1]
                if last_val > 70.0:
                    self.forecasts.append({
                        "category": "LATENCY_SPIKE",
                        "description": "Trend kenaikan latency dikesan pada edge nodes.",
                        "predicted_value": last_val * 1.5,
                        "time_horizon_sec": 10.0,
                        "confidence": 0.85
                    })

        # 2. Reconnection loop check (from hardware state)
        if hardware_state.get("latency_spike") or grid_state.get("relay_unstable"):
            self.forecasts.append({
                "category": "RECOVERY_CONGESTION",
                "description": "Ketidakstabilan relay berulang dikesan. Risiko kegagalan pemutus litar.",
                "predicted_value": 1.0,
                "time_horizon_sec": 20.0,
                "confidence": 0.75
            })

        # Generate coordination suggestions if cooldown allows
        if now - self.last_suggestion_time >= self.suggestion_cooldown:
            new_suggestions = []
            for f in self.forecasts:
                if f["category"] == "LATENCY_SPIKE":
                    new_suggestions.append({
                        "id": f"sug_lat_{int(now)}",
                        "title": "Pra-Pengasingan Pencawang (Pre-emptive Isolation)",
                        "description": "Latency dikesan meningkat. Cadangkan aktifkan workflow system_status_check.",
                        "action_type": "TRIGGER_WORKFLOW",
                        "parameters": {"workflow_name": "system_status_check"},
                        "confidence": f["confidence"],
                        "timestamp": int(now * 1000)
                    })
                elif f["category"] == "RECOVERY_CONGESTION":
                    new_suggestions.append({
                        "id": f"sug_rec_{int(now)}",
                        "title": "Relay Stabilization Routine",
                        "description": "Relay tidak stabil. Cadangkan jalankan routine kestabilan pemutus litar.",
                        "action_type": "CREATE_ROUTINE",
                        "parameters": {"routine_type": "relay_stabilization"},
                        "confidence": f["confidence"],
                        "timestamp": int(now * 1000)
                    })
            if new_suggestions:
                self.suggestions = new_suggestions
                self.last_suggestion_time = now

        return self.forecasts

    def get_status_summary(self) -> Dict[str, Any]:
        return {
            "latency_history": self.latency_history,
            "forecasts_count": len(self.forecasts),
            "forecasts": self.forecasts,
            "suggestions_count": len(self.suggestions),
            "suggestions": self.suggestions,
            "workflow_timings": {k: self.predict_workflow_duration(k) for k in self.workflow_execution_history.keys()}
        }
