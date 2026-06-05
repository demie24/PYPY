from typing import Dict, Any, Optional

class FitnessEvaluator:
    def __init__(self, weights: Optional[Dict[str, float]] = None):
        """
        Computes fitness metrics for agents based on configurable weights.
        """
        self.weights = weights or {
            "win_rate": 0.3,
            "elo": 0.3,
            "avg_reward": 0.1,
            "success_rate": 0.2,
            "stability": 0.1
        }

    def set_weights(self, weights: Dict[str, float]) -> None:
        self.weights.update(weights)

    def evaluate(self, metrics: Dict[str, Any]) -> float:
        """
        Calculates agent fitness score.
        metrics keys:
        - win_rate (0.0 to 1.0)
        - elo (float)
        - avg_reward (float)
        - success_rate (0.0 to 1.0, representing attack or defense success rate)
        - stability (0.0 to 1.0, representing stability preservation)
        """
        win_rate = float(metrics.get("win_rate", 0.0))
        elo = float(metrics.get("elo", 1000.0))
        avg_reward = float(metrics.get("avg_reward", 0.0))
        success_rate = float(metrics.get("success_rate", 0.0))
        stability = float(metrics.get("stability", 0.0))

        # Normalize ELO relative to standard baseline expectations (e.g. normalized around 1000)
        normalized_elo = elo / 2000.0

        fitness = (
            self.weights.get("win_rate", 0.3) * win_rate
            + self.weights.get("elo", 0.3) * normalized_elo
            + self.weights.get("avg_reward", 0.1) * avg_reward
            + self.weights.get("success_rate", 0.2) * success_rate
            + self.weights.get("stability", 0.1) * stability
        )
        return float(fitness)
