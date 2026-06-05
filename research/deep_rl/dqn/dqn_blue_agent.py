import torch
import torch.nn as nn
import torch.optim as optim
import random
import os
import sys
from typing import Dict, Any, Union, List

# Ensure parent directory is in path to import state encoder, model manager
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from state_encoder import StateEncoder
from model_manager import ModelManager

from training_config import DQNConfig
from dqn_network import DQNNetwork
from replay_memory import DQNReplayMemory

class DQNBlueAgent:
    def __init__(self, config: DQNConfig = None, input_dim: int = None, device: str = "cpu"):
        """
        DQN agent representing the Blue Team (Defender) learning policy.
        """
        self.config = config or DQNConfig()
        self.device = device
        
        # Resolve state dimension dynamically from encoder
        self.encoder = StateEncoder()
        self.input_dim = input_dim or self.encoder.state_dim
        
        # 32 actions: Isolate (9), Quarantine (9), Default (1), Special Strategies (5), Threshold Tuning (8)
        self.action_space_size = 32
        
        # Networks initialization
        self.policy_net = DQNNetwork(
            self.input_dim, 
            self.action_space_size, 
            self.config.hidden_layers, 
            self.config.activation,
            seed=self.config.seed
        ).to(self.device)
        
        self.target_net = DQNNetwork(
            self.input_dim, 
            self.action_space_size, 
            self.config.hidden_layers, 
            self.config.activation,
            seed=self.config.seed
        ).to(self.device)
        
        # Load starting weights to target network
        self.target_net.load_state_dict(self.policy_net.state_dict())
        self.target_net.eval()
        
        self.optimizer = optim.Adam(self.policy_net.parameters(), lr=self.config.learning_rate)
        self.criterion = nn.SmoothL1Loss()
        
        # Replay memory initialization
        self.memory = DQNReplayMemory(capacity=10000, device=self.device)
        self.model_manager = ModelManager()
        
        # Current status state
        self.epsilon = self.config.epsilon_start
        self.step_count = 0
        self.loss_history = []
        self.epsilon_history = []
        
        # Grid performance metrics
        self.total_steps = 0
        self.detection_success_count = 0
        self.total_attacks_observed = 0
        self.containment_success_count = 0
        self.total_containments_triggered = 0
        self.stability_preserved_steps = 0
        self.trust_preservation_accumulator = 0.0

    def select_action(self, state_vector: Union[torch.Tensor, Any], eval_mode: bool = False) -> Dict[str, Any]:
        """
        Selects a defensive action using Epsilon-Greedy selection strategy.
        """
        if not isinstance(state_vector, torch.Tensor):
            state_tensor = torch.tensor(state_vector, dtype=torch.float32).unsqueeze(0).to(self.device)
        else:
            state_tensor = state_vector.unsqueeze(0).to(self.device)

        # Explore vs Exploit
        if not eval_mode and random.random() < self.epsilon:
            discrete_action = random.randint(0, self.action_space_size - 1)
        else:
            with torch.no_grad():
                q_values = self.policy_net(state_tensor)
                discrete_action = torch.argmax(q_values, dim=1).item()

        # Decaying epsilon after action selection
        if not eval_mode:
            self.epsilon = max(self.config.epsilon_end, self.epsilon * self.config.epsilon_decay)
            self.epsilon_history.append(self.epsilon)

        return self._decode_action(discrete_action)

    def _decode_action(self, action_idx: int) -> Dict[str, Any]:
        """
        Decodes a discrete action index [0, 31] to defender parameter mapping.
        """
        routing_strategy = "DEFAULT"
        anomaly_threshold = 0.5
        rollback_lockout = 0.0
        trust_decay_speed = "NORMAL"

        if action_idx < 9:
            # Isolate Bus 1-9
            routing_strategy = f"ISOLATE_BUS_{action_idx + 1}"
            anomaly_threshold = 0.8
        elif action_idx < 18:
            # Quarantine Bus 1-9
            bus_num = action_idx - 9 + 1
            routing_strategy = f"QUARANTINE_BUS_{bus_num}"
            anomaly_threshold = 0.9
            rollback_lockout = 5.0
        elif action_idx == 18:
            # Default
            routing_strategy = "DEFAULT"
            anomaly_threshold = 0.5
        elif action_idx == 19:
            # Predictive Defense Mode
            routing_strategy = "PREDICTIVE"
            anomaly_threshold = 0.3
            rollback_lockout = 2.0
        elif action_idx == 20:
            # Enhanced Monitoring
            routing_strategy = "ENHANCED"
            anomaly_threshold = 0.4
            rollback_lockout = 1.0
        elif action_idx == 21:
            # Strict Mode
            routing_strategy = "STRICT"
            anomaly_threshold = 0.7
            rollback_lockout = 3.0
        elif action_idx == 22:
            # Prioritize Restoration
            routing_strategy = "RESTORATION_PRIORITY"
            anomaly_threshold = 0.2
            rollback_lockout = 0.0
        elif action_idx == 23:
            # Delay Restoration
            routing_strategy = "RESTORATION_DELAY"
            anomaly_threshold = 0.8
            rollback_lockout = 10.0
        elif action_idx < 32:
            # Threshold configuration adjustments
            thresholds = [0.1, 0.2, 0.3, 0.4, 0.6, 0.7, 0.8, 0.9]
            anomaly_threshold = thresholds[action_idx - 24]
            routing_strategy = "DEFAULT"

        return {
            "routing_strategy": routing_strategy,
            "anomaly_threshold": anomaly_threshold,
            "rollback_lockout": rollback_lockout,
            "trust_decay_speed": trust_decay_speed
        }

    def _encode_action(self, action_dict: Dict[str, Any]) -> int:
        """
        Encodes a defender action dictionary back to a discrete action index.
        """
        routing_strat = action_dict.get("routing_strategy", "DEFAULT")
        anomaly_threshold = float(action_dict.get("anomaly_threshold", 0.5))

        if routing_strat.startswith("ISOLATE_BUS_"):
            try:
                bus_num = int(routing_strat.split("_")[-1])
                return bus_num - 1
            except Exception:
                return 18
        elif routing_strat.startswith("QUARANTINE_BUS_"):
            try:
                bus_num = int(routing_strat.split("_")[-1])
                return 9 + bus_num - 1
            except Exception:
                return 18
        elif routing_strat == "PREDICTIVE":
            return 19
        elif routing_strat == "ENHANCED":
            return 20
        elif routing_strat == "STRICT":
            return 21
        elif routing_strat == "RESTORATION_PRIORITY":
            return 22
        elif routing_strat == "RESTORATION_DELAY":
            return 23
        elif routing_strat == "DEFAULT":
            # Match closest threshold
            thresholds = [0.1, 0.2, 0.3, 0.4, 0.6, 0.7, 0.8, 0.9]
            closest_idx = 0
            min_diff = float("inf")
            for idx, val in enumerate(thresholds):
                diff = abs(anomaly_threshold - val)
                if diff < min_diff:
                    min_diff = diff
                    closest_idx = idx
            if min_diff < 0.05:
                return 24 + closest_idx
            return 18
        return 18

    def remember(self, state: Any, action_dict: Dict[str, Any], reward: float, next_state: Any, done: bool):
        """
        Registers transition states and updates performance tracking metric histories.
        """
        discrete_action = self._encode_action(action_dict)
        self.memory.push(state, discrete_action, reward, next_state, done)
        
        # Track statistics based on state values
        self.total_steps += 1
        
        # State mapping decoding checks
        # state is an encoded state list/array of 67 elements:
        # Buses: 9 * 5 elements = 45 elements
        # 0: voltage, 1: freq, 2: trust, 3: threat, 4: anomaly
        # Lines: 9 * 2 elements = 18 elements
        # Globals: 4 elements (res_completed, res_step, def_isolation, def_lockout)
        
        # Parse next_state values for metrics mapping
        try:
            # 1. Voltage & Frequency stability preservation
            v_deviations = 0.0
            f_deviations = 0.0
            avg_trust = 0.0
            threat_active = False
            anomalies_active = False
            
            for b in range(9):
                v_idx = b * 5
                f_idx = v_idx + 1
                t_idx = v_idx + 2
                th_idx = v_idx + 3
                a_idx = v_idx + 4
                
                vol = float(next_state[v_idx])
                freq = float(next_state[f_idx])
                trust = max(0.0, min(1.0, float(next_state[t_idx])))
                threat = float(next_state[th_idx])
                anomaly = float(next_state[a_idx])
                
                v_deviations += abs(vol - 1.0)
                f_deviations += abs(freq - 1.0)  # normalized frequency deviation in state encoder
                avg_trust += trust
                
                if threat > 0.0:
                    threat_active = True
                if anomaly > 0.0:
                    anomalies_active = True

            avg_trust /= 9.0
            self.trust_preservation_accumulator += max(0.0, min(1.0, avg_trust))

            # Check if grid meets stability bounds
            if (v_deviations / 9.0 < 0.05) and (f_deviations / 9.0 < 0.05):
                self.stability_preserved_steps += 1
                
            # Threat detection: Correct anomalies active when actual threats are active
            if threat_active:
                self.total_attacks_observed += 1
                if anomalies_active:
                    self.detection_success_count += 1
                    
            # Threat containment check: If we reduced threat levels compared to previous state
            if state is not None:
                prev_threat = sum(float(state[b*5+3]) for b in range(9))
                curr_threat = sum(float(next_state[b*5+3]) for b in range(9))
                if prev_threat > 0.0:
                    self.total_containments_triggered += 1
                    if curr_threat < prev_threat:
                        self.containment_success_count += 1
        except Exception:
            pass

    def learn(self, state: Any, action_dict: Dict[str, Any], reward: float, next_state: Any, done: bool):
        """
        Executes a Q-Network parameter training iteration if batch conditions are met.
        """
        if len(self.memory) < self.config.batch_size:
            return

        # Sample batch
        states, actions, rewards, next_states, dones = self.memory.sample_tensors(self.config.batch_size)

        # Compute current state action values Q(s, a)
        q_values = self.policy_net(states)
        state_action_values = q_values.gather(1, actions)

        # Compute max Q(s', a) using target network
        with torch.no_grad():
            next_state_values = self.target_net(next_states).max(1)[0].unsqueeze(1)
            # Expected Q-values
            expected_state_action_values = rewards + (self.config.gamma * next_state_values * (1.0 - dones))

        # Compute loss
        loss = self.criterion(state_action_values, expected_state_action_values)
        self.loss_history.append(loss.item())

        # Backward propagation
        self.optimizer.zero_grad()
        loss.backward()
        # Gradient clipping
        torch.nn.utils.clip_grad_norm_(self.policy_net.parameters(), 1.0)
        self.optimizer.step()

        # Update target network
        if self.config.use_soft_update:
            for target_param, policy_param in zip(self.target_net.parameters(), self.policy_net.parameters()):
                target_param.data.copy_(
                    self.config.tau * policy_param.data + (1.0 - self.config.tau) * target_param.data
                )
        else:
            self.step_count += 1
            if self.step_count % self.config.target_update_freq == 0:
                self.target_net.load_state_dict(self.policy_net.state_dict())

    def get_detection_success_rate(self) -> float:
        if self.total_attacks_observed == 0:
            return 1.0  # default perfect if no attacks occurred
        return float(self.detection_success_count) / self.total_attacks_observed

    def get_containment_success_rate(self) -> float:
        if self.total_containments_triggered == 0:
            return 1.0
        return float(self.containment_success_count) / self.total_containments_triggered

    def get_stability_preservation(self) -> float:
        if self.total_steps == 0:
            return 1.0
        return float(self.stability_preserved_steps) / self.total_steps

    def get_trust_preservation(self) -> float:
        if self.total_steps == 0:
            return 1.0
        return float(self.trust_preservation_accumulator) / self.total_steps

    def save_model(self, checkpoint_name: str) -> str:
        """
        Saves Q-network weights, target weights, optimizer state, and training configurations.
        """
        weights = {
            "policy_net": self.policy_net.state_dict(),
            "target_net": self.target_net.state_dict(),
            "optimizer": self.optimizer.state_dict()
        }
        metadata = {
            "epsilon": self.epsilon,
            "step_count": self.step_count,
            "config": self.config.to_dict()
        }
        history = {
            "loss_history": self.loss_history,
            "epsilon_history": self.epsilon_history,
            "total_steps": self.total_steps,
            "detection_success_rate": self.get_detection_success_rate(),
            "containment_success_rate": self.get_containment_success_rate(),
            "stability_preservation": self.get_stability_preservation(),
            "trust_preservation": self.get_trust_preservation()
        }
        return self.model_manager.save_checkpoint(checkpoint_name, weights, metadata, history)

    def load_model(self, checkpoint_name: str):
        """
        Restores model checkpoints.
        """
        checkpoint = self.model_manager.load_checkpoint(checkpoint_name)
        weights = checkpoint["weights"]
        metadata = checkpoint["metadata"]
        history = checkpoint["training_history"]

        self.policy_net.load_state_dict(weights["policy_net"])
        self.target_net.load_state_dict(weights["target_net"])
        self.optimizer.load_state_dict(weights["optimizer"])
        
        self.epsilon = metadata.get("epsilon", self.config.epsilon_start)
        self.step_count = metadata.get("step_count", 0)
        
        self.loss_history = history.get("loss_history", [])
        self.epsilon_history = history.get("epsilon_history", [])
        self.total_steps = history.get("total_steps", 0)
