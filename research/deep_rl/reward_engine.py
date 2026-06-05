from typing import Dict, Any

class RewardEngine:
    def __init__(self, red_config: Dict[str, float] = None, blue_config: Dict[str, float] = None):
        """
        Initializes the Reward Engine with configurable weights for Red and Blue teams.
        """
        # Red config weights
        self.red_weights = red_config or {
            "disruption": 1.0,      # weight on voltage/frequency deviations
            "stealth": 0.5,         # weight on remaining undetected/trusted
            "action_penalty": -0.1  # penalty for high severity attacks to encourage efficiency
        }

        # Blue config weights
        self.blue_weights = blue_config or {
            "stability": 1.5,       # weight on keeping voltage at 1.0 and freq at 60Hz
            "trust": 0.8,           # weight on preserving telemetry trust scores
            "containment": 1.0,     # reward for containment latency reduction
            "false_alarms": -0.2    # penalty for incorrect anomaly classifications
        }

    def calculate_red_reward(self, state: Dict[str, Any], action: Dict[str, Any], next_state: Dict[str, Any]) -> float:
        """
        Calculates reinforcement learning reward for the Red Team (Attacker).
        Red objective: Maximize grid deviation, maximize stealth (minimize trust score drop), minimize action footprint.
        """
        reward = 0.0

        # 1. Disruption component (Deviations from nominal voltage 1.0 pu and nominal freq 60.0 Hz)
        voltage_dev = 0.0
        freq_dev = 0.0
        
        buses = next_state.get("buses", {})
        for bus_id, bus_data in buses.items():
            voltage = float(bus_data.get("voltage_pu", 1.0))
            frequency = float(bus_data.get("frequency_hz", 60.0))
            voltage_dev += abs(voltage - 1.0)
            freq_dev += abs(frequency - 60.0) / 60.0

        disruption_score = (voltage_dev + freq_dev) / max(1, len(buses))
        reward += self.red_weights.get("disruption", 1.0) * disruption_score

        # 2. Stealth component (Average trust scores: higher average trust score is better for Red)
        trust_scores = next_state.get("trust_scores", {})
        avg_trust = sum(trust_scores.values()) / max(1, len(trust_scores)) if trust_scores else 1.0
        reward += self.red_weights.get("stealth", 0.5) * avg_trust

        # 3. Action efficiency penalty (severity and stealth coefficients)
        severity = float(action.get("severity", 0.0))
        reward += self.red_weights.get("action_penalty", -0.1) * severity

        return float(reward)

    def calculate_blue_reward(self, state: Dict[str, Any], action: Dict[str, Any], next_state: Dict[str, Any]) -> float:
        """
        Calculates reinforcement learning reward for the Blue Team (Defender).
        Blue objective: Maintain voltage/frequency stability, preserve trust, contain attacks.
        """
        reward = 0.0

        # 1. Stability component (Penalizes deviations from nominal voltage 1.0 pu and frequency 60.0 Hz)
        voltage_penalty = 0.0
        freq_penalty = 0.0
        
        buses = next_state.get("buses", {})
        for bus_id, bus_data in buses.items():
            voltage = float(bus_data.get("voltage_pu", 1.0))
            frequency = float(bus_data.get("frequency_hz", 60.0))
            voltage_penalty += abs(voltage - 1.0)
            freq_penalty += abs(frequency - 60.0) / 60.0

        avg_deviation = (voltage_penalty + freq_penalty) / max(1, len(buses))
        reward -= self.blue_weights.get("stability", 1.5) * avg_deviation

        # 2. Trust Preservation component
        trust_scores = next_state.get("trust_scores", {})
        avg_trust = sum(trust_scores.values()) / max(1, len(trust_scores)) if trust_scores else 1.0
        reward += self.blue_weights.get("trust", 0.8) * avg_trust

        # 3. Containment Component (Success in reducing threat levels / restoring isolated breakers)
        prev_threat = sum(state.get("threat_scores", {}).values())
        curr_threat = sum(next_state.get("threat_scores", {}).values())
        threat_reduction = max(0.0, prev_threat - curr_threat)
        reward += self.blue_weights.get("containment", 1.0) * threat_reduction

        # 4. Action Cost / Anomaly False Alarms (Penalty if isolation is active but threat is zero)
        defense = next_state.get("defense_status", {})
        isolation_active = defense.get("isolation_active", False)
        if isolation_active and curr_threat == 0.0:
            reward += self.blue_weights.get("false_alarms", -0.2)

        return float(reward)
