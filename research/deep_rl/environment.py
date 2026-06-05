import random
from typing import Dict, Any, Tuple, Union

class SmartGridRLEnv:
    def __init__(self, max_steps: int = 50, bus_count: int = 9):
        """
        Initializes the Gym-Like Research Environment representing an IEEE-like grid.
        """
        self.max_steps = max_steps
        self.bus_count = bus_count
        self.bus_ids = [f"Bus_{i}" for i in range(1, bus_count + 1)]
        self.line_ids = [
            "L1_4", "L2_7", "L3_9", "L4_5", "L4_9", "L5_6", "L6_7", "L7_8", "L8_9"
        ]
        
        self.current_step = 0
        self.state: Dict[str, Any] = {}
        self.reset()

    def reset(self) -> Dict[str, Any]:
        """
        Resets the environment state to standard nominal conditions.
        """
        self.current_step = 0
        
        # Nominal buses: voltage = 1.0 pu, frequency = 60.0 Hz
        buses = {
            bus_id: {"voltage_pu": 1.0, "frequency_hz": 60.0} 
            for bus_id in self.bus_ids
        }
        
        # Nominal lines: capacity = 50%, current = 0.5 pu
        lines = {
            line_id: {"capacity_pct": 50.0, "current_pu": 0.5} 
            for line_id in self.line_ids
        }
        
        # Maximum initial trust, zero initial threat/anomalies
        trust_scores = {bus_id: 1.0 for bus_id in self.bus_ids}
        threat_scores = {bus_id: 0.0 for bus_id in self.bus_ids}
        anomalies = {bus_id: 0 for bus_id in self.bus_ids}
        
        self.state = {
            "buses": buses,
            "lines": lines,
            "trust_scores": trust_scores,
            "threat_scores": threat_scores,
            "anomalies": anomalies,
            "restoration_status": {
                "completed": False,
                "step": 0
            },
            "defense_status": {
                "isolation_active": False,
                "rollback_lockout": 0.0
            }
        }
        return self.state

    def step(self, action: Union[Dict[str, Any], Any]) -> Tuple[Dict[str, Any], Dict[str, float], bool, Dict[str, Any]]:
        """
        Transitions the grid simulation state based on the actions taken.
        Supports:
        - Red-only actions (dict)
        - Blue-only actions (dict)
        - Multi-Agent coevolution actions: {"red": red_action, "blue": blue_action}
        """
        self.current_step += 1
        
        # Extract actions
        red_action = None
        blue_action = None
        
        if isinstance(action, dict):
            if "red" in action or "blue" in action:
                red_action = action.get("red")
                blue_action = action.get("blue")
            else:
                # Assume single unified action structure: check target or keys to determine side
                if "target" in action or "attack_type" in action:
                    red_action = action
                if "routing_strategy" in action or "anomaly_threshold" in action:
                    blue_action = action
        
        # 1. Process Red Attacker Actions
        if red_action:
            target = red_action.get("target", "Bus_5")
            severity = float(red_action.get("severity", 0.5))
            attack_type = red_action.get("attack_type", "FDIA")
            stealth = float(red_action.get("stealth", 0.5))

            # Trigger anomalies and reduce trust based on stealth
            if target in self.state["threat_scores"]:
                self.state["threat_scores"][target] += severity * 20.0
                
                # Trust drops more if the attack is less stealthy
                trust_decay = (1.0 - stealth) * severity * 0.4
                self.state["trust_scores"][target] = max(0.0, self.state["trust_scores"][target] - trust_decay)
                
                # Low stealth increases detection chance (anomalies)
                if random.random() > stealth:
                    self.state["anomalies"][target] = 1

                # Voltage and Frequency deviations
                if attack_type == "FDIA":
                    # Spoil readings: voltage departs nominal 1.0 pu
                    self.state["buses"][target]["voltage_pu"] -= (severity * 0.25)
                elif attack_type == "DoS":
                    # Cause line frequency drops due to load imbalances
                    self.state["buses"][target]["frequency_hz"] -= (severity * 5.0)

        # 2. Process Blue Defender Actions
        if blue_action:
            routing_strat = blue_action.get("routing_strategy", "DEFAULT")
            rollback = float(blue_action.get("rollback_lockout", 0.0))
            threshold = float(blue_action.get("anomaly_threshold", 0.5))
            trust_decay_speed = blue_action.get("trust_decay_speed", "NORMAL")

            # Enable isolation defenses
            if routing_strat != "DEFAULT":
                self.state["defense_status"]["isolation_active"] = True
            
            self.state["defense_status"]["rollback_lockout"] = rollback

            # Recover trust and contain threats based on threshold & strategy
            for bus_id in self.bus_ids:
                # If trust was damaged and threshold is strict, isolate and recover
                if self.state["trust_scores"][bus_id] < threshold:
                    # Isolate target to reduce threat levels
                    self.state["threat_scores"][bus_id] = max(0.0, self.state["threat_scores"][bus_id] - 15.0)
                    
                    # Recover trust over time
                    self.state["trust_scores"][bus_id] = min(1.0, self.state["trust_scores"][bus_id] + 0.1)
                    
                    # Clear anomalies
                    self.state["anomalies"][bus_id] = 0

                # Recover physical bounds (grid stabilization)
                vol = self.state["buses"][bus_id]["voltage_pu"]
                freq = self.state["buses"][bus_id]["frequency_hz"]
                
                if vol < 1.0:
                    self.state["buses"][bus_id]["voltage_pu"] = min(1.0, vol + 0.05)
                elif vol > 1.0:
                    self.state["buses"][bus_id]["voltage_pu"] = max(1.0, vol - 0.05)

                if freq < 60.0:
                    self.state["buses"][bus_id]["frequency_hz"] = min(60.0, freq + 1.0)

            # Update restoration progress
            if self.state["restoration_status"]["step"] < 5:
                self.state["restoration_status"]["step"] += 1
            else:
                self.state["restoration_status"]["completed"] = True

        # 3. Assess terminal conditions and calculate rewards
        done = self.is_terminal()
        
        # Multi-agent rewards payload
        rewards = {
            "red": self.get_reward("red", red_action or {}, self.state),
            "blue": self.get_reward("blue", blue_action or {}, self.state)
        }
        
        info = {
            "current_step": self.current_step,
            "max_steps_reached": self.current_step >= self.max_steps
        }

        return self.state, rewards, done, info

    def get_state(self) -> Dict[str, Any]:
        """
        Returns the raw state dictionary.
        """
        return self.state

    def get_reward(self, agent_type: str, action: Dict[str, Any], next_state: Dict[str, Any]) -> float:
        """
        Interface to compute reward values for Red or Blue team.
        """
        from reward_engine import RewardEngine
        engine = RewardEngine()
        if agent_type == "red":
            return engine.calculate_red_reward(self.state, action, next_state)
        else:
            return engine.calculate_blue_reward(self.state, action, next_state)

    def is_terminal(self) -> bool:
        """
        Returns true if terminal state criteria is reached.
        - Maximum steps reached.
        - Voltage collapse on any bus (< 0.70 pu or > 1.30 pu).
        - Frequency drop below 50 Hz.
        - Restoration fully completed.
        """
        if self.current_step >= self.max_steps:
            return True

        # Check voltage collapse & frequency drop boundaries
        for bus_id, bus_data in self.state.get("buses", {}).items():
            voltage = float(bus_data.get("voltage_pu", 1.0))
            freq = float(bus_data.get("frequency_hz", 60.0))
            if voltage < 0.70 or voltage > 1.30:
                return True
            if freq < 50.0:
                return True

        # Check restoration complete
        if self.state.get("restoration_status", {}).get("completed", False):
            return True

        return False
