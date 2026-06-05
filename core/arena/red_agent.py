import random
from typing import Dict, Any, List, Tuple

class RedAgent:
    def __init__(self, alpha: float = 0.1, gamma: float = 0.9, epsilon: float = 0.2):
        self.alpha = alpha      # Learning rate
        self.gamma = gamma      # Discount factor
        self.epsilon = epsilon  # Exploration rate

        # Action space list: (Target, AttackType, Severity, Stealth)
        self.actions = [
            ("Bus_5", "FDIA_ESCALATION", 0.8, 0.3),
            ("Bus_5", "TRUST_POISONING", 0.4, 0.8),
            ("Bus_5", "STEALTHY_LOW_RATE", 0.3, 0.9),
            ("Bus_6", "COORDINATED_MULTI_NODE", 0.9, 0.2),
            ("Bus_6", "TELEMETRY_MANIPULATION", 0.6, 0.6),
            ("Bus_5", "TELEMETRY_MANIPULATION", 0.7, 0.5),
            ("Bus_8", "FDIA_ESCALATION", 0.85, 0.35),
            ("Bus_8", "STEALTHY_LOW_RATE", 0.25, 0.95),
            ("Bus_6", "TRUST_POISONING", 0.45, 0.75),
            ("Bus_8", "COORDINATED_MULTI_NODE", 0.95, 0.15)
        ]

        # Q-table: State -> Dict[ActionIndex, Q-value]
        # State key is a string representing the Blue Agent's defense posture
        self.q_table: Dict[str, List[float]] = {}

    def get_state_key(self, blue_posture: Dict[str, Any]) -> str:
        """
        Derive discrete state representation of the defender's posture.
        """
        threshold = blue_posture.get("anomaly_threshold", 0.5)
        decay = blue_posture.get("trust_decay_speed", "NORMAL")

        # Simplify to: threshold_level (LOW/HIGH) + decay_speed
        t_lvl = "LOW" if threshold < 0.5 else "HIGH"
        return f"{t_lvl}_{decay}"

    def select_action(self, blue_posture: Dict[str, Any]) -> Tuple[int, Tuple[str, str, float, float]]:
        """
        Select action index and parameters using Epsilon-Greedy.
        """
        state = self.get_state_key(blue_posture)
        if state not in self.q_table:
            self.q_table[state] = [0.0] * len(self.actions)

        # Explore
        if random.random() < self.epsilon:
            idx = random.randint(0, len(self.actions) - 1)
        # Exploit
        else:
            q_values = self.q_table[state]
            max_q = max(q_values)
            # Handle multiple actions with max value
            max_indices = [i for i, q in enumerate(q_values) if q == max_q]
            idx = random.choice(max_indices)

        return idx, self.actions[idx]

    def update_q_value(
        self, 
        blue_posture: Dict[str, Any], 
        action_idx: int, 
        reward: float, 
        next_blue_posture: Dict[str, Any]
    ):
        """
        Standard Q-learning update step.
        """
        state = self.get_state_key(blue_posture)
        next_state = self.get_state_key(next_blue_posture)

        if state not in self.q_table:
            self.q_table[state] = [0.0] * len(self.actions)
        if next_state not in self.q_table:
            self.q_table[next_state] = [0.0] * len(self.actions)

        max_next_q = max(self.q_table[next_state])
        current_q = self.q_table[state][action_idx]
        
        # Bellman equation update
        self.q_table[state][action_idx] = current_q + self.alpha * (
            reward + self.gamma * max_next_q - current_q
        )

    def decay_exploration(self, decay_rate: float = 0.99, min_eps: float = 0.05):
        """
        Reduce exploration rate as training progresses.
        """
        self.epsilon = max(min_eps, self.epsilon * decay_rate)
