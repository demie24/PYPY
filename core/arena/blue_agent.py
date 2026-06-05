import random
from typing import Dict, Any, List, Tuple

class BlueAgent:
    def __init__(self, alpha: float = 0.1, gamma: float = 0.9, epsilon: float = 0.2):
        self.alpha = alpha
        self.gamma = gamma
        self.epsilon = epsilon

        # Action space list: (AnomalyThreshold, TrustDecaySpeed, RollbackLockout, RoutingStrategy)
        self.actions = [
            (0.3, "FAST", 30.0, "REDUNDANT_PATH"),
            (0.5, "NORMAL", 30.0, "SHORTEST_PATH"),
            (0.7, "SLOW", 10.0, "ISOLATE_ONLY"),
            (0.3, "FAST", 60.0, "REDUNDANT_PATH"),
            (0.4, "FAST", 45.0, "REDUNDANT_PATH"),
            (0.5, "FAST", 30.0, "SHORTEST_PATH"),
            (0.6, "NORMAL", 20.0, "SHORTEST_PATH"),
            (0.3, "NORMAL", 60.0, "ISOLATE_ONLY"),
            (0.5, "SLOW", 15.0, "SHORTEST_PATH"),
            (0.8, "SLOW", 5.0, "ISOLATE_ONLY")
        ]

        # Q-table: State -> Dict[ActionIndex, Q-value]
        # State key is a string representing the Red Agent's attack parameters
        self.q_table: Dict[str, List[float]] = {}

    def get_state_key(self, red_attack: Dict[str, Any]) -> str:
        """
        Derive discrete state representation of the attacker's posture.
        """
        target = red_attack.get("target", "Bus_5")
        severity = red_attack.get("severity", 0.5)

        sev_lvl = "LOW" if severity <= 0.5 else "HIGH"
        return f"{target}_{sev_lvl}"

    def select_action(self, red_attack: Dict[str, Any]) -> Tuple[int, Tuple[float, str, float, str]]:
        """
        Select action index and parameters using Epsilon-Greedy.
        """
        state = self.get_state_key(red_attack)
        if state not in self.q_table:
            self.q_table[state] = [0.0] * len(self.actions)

        # Explore
        if random.random() < self.epsilon:
            idx = random.randint(0, len(self.actions) - 1)
        # Exploit
        else:
            q_values = self.q_table[state]
            max_q = max(q_values)
            max_indices = [i for i, q in enumerate(q_values) if q == max_q]
            idx = random.choice(max_indices)

        return idx, self.actions[idx]

    def update_q_value(
        self, 
        red_attack: Dict[str, Any], 
        action_idx: int, 
        reward: float, 
        next_red_attack: Dict[str, Any]
    ):
        """
        Standard Q-learning update step.
        """
        state = self.get_state_key(red_attack)
        next_state = self.get_state_key(next_red_attack)

        if state not in self.q_table:
            self.q_table[state] = [0.0] * len(self.actions)
        if next_state not in self.q_table:
            self.q_table[next_state] = [0.0] * len(self.actions)

        max_next_q = max(self.q_table[next_state])
        current_q = self.q_table[state][action_idx]

        self.q_table[state][action_idx] = current_q + self.alpha * (
            reward + self.gamma * max_next_q - current_q
        )

    def decay_exploration(self, decay_rate: float = 0.99, min_eps: float = 0.05):
        """
        Reduce exploration rate as training progresses.
        """
        self.epsilon = max(min_eps, self.epsilon * decay_rate)
