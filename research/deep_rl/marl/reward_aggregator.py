from typing import Dict, Any

class RewardAggregator:
    def __init__(self, mode: str = "INDIVIDUAL", alpha: float = 0.5):
        """
        Aggregates and distributes rewards to Red and Blue agents.
        Modes:
        - INDIVIDUAL: Agents receive rewards based on their specific individual actions.
        - TEAM: Agents receive the team reward (from the coordinated effective action).
        - HYBRID: Mixed reward: alpha * individual_reward + (1 - alpha) * team_reward.
        """
        self.mode = mode.upper()
        self.alpha = alpha

    def set_mode(self, mode: str, alpha: float = 0.5) -> None:
        self.mode = mode.upper()
        self.alpha = alpha

    def aggregate(
        self,
        agent_id: str,
        team: str,
        individual_reward: float,
        team_reward: float
    ) -> float:
        """
        Calculates the aggregated reward for a single agent.
        """
        if self.mode == "INDIVIDUAL":
            return individual_reward
        elif self.mode == "TEAM":
            return team_reward
        elif self.mode == "HYBRID":
            return self.alpha * individual_reward + (1.0 - self.alpha) * team_reward
        else:
            # Fallback
            return individual_reward
