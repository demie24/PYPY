import torch
import torch.nn as nn
import torch.optim as optim
import random
import os
import sys
from typing import Dict, Any, Union

# Ensure parent directory is in path to import state encoder, model manager
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from state_encoder import StateEncoder
from model_manager import ModelManager

from training_config import DQNConfig
from dqn_network import DQNNetwork
from replay_memory import DQNReplayMemory

class DQNRedAgent:
    def __init__(self, config: DQNConfig = None, input_dim: int = None, device: str = "cpu"):
        """
        DQN agent representing the Red Team (Attacker) learning policy.
        """
        self.config = config or DQNConfig()
        self.device = device
        
        # Resolve state dimension dynamically from encoder
        self.encoder = StateEncoder()
        self.input_dim = input_dim or self.encoder.state_dim
        
        # 54 actions: 9 buses * 2 attack types (FDIA, DoS) * 3 severity configurations
        self.action_space_size = 54
        
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
        self.attack_success_count = 0
        self.total_attacks = 0

    def select_action(self, state_vector: Union[torch.Tensor, Any], eval_mode: bool = False) -> Dict[str, Any]:
        """
        Selects an attack action using Epsilon-Greedy selection strategy.
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
        Decodes a discrete action index [0, 53] to attack parameter mapping.
        """
        bus_idx = action_idx // 6
        attack_type_idx = (action_idx // 3) % 2
        param_idx = action_idx % 3

        target_bus = f"Bus_{bus_idx + 1}"
        attack_type = "FDIA" if attack_type_idx == 0 else "DoS"

        if param_idx == 0:
            severity = 0.3
            stealth = 0.8
        elif param_idx == 1:
            severity = 0.6
            stealth = 0.5
        else:
            severity = 1.0
            stealth = 0.2

        return {
            "target": target_bus,
            "attack_type": attack_type,
            "severity": severity,
            "stealth": stealth
        }

    def _encode_action(self, action_dict: Dict[str, Any]) -> int:
        """
        Encodes an action dictionary back to a discrete action index.
        """
        target = action_dict.get("target", "Bus_5")
        try:
            bus_idx = int(target.split("_")[1]) - 1
        except Exception:
            bus_idx = 4  # Default Bus_5

        attack_type = action_dict.get("attack_type", "FDIA")
        attack_idx = 0 if attack_type == "FDIA" else 1

        severity = float(action_dict.get("severity", 0.5))
        if severity <= 0.4:
            param_idx = 0
        elif severity <= 0.7:
            param_idx = 1
        else:
            param_idx = 2

        return bus_idx * 6 + attack_idx * 3 + param_idx

    def remember(self, state: Any, action_dict: Dict[str, Any], reward: float, next_state: Any, done: bool):
        """
        Registers a transition state to replay memory.
        """
        discrete_action = self._encode_action(action_dict)
        self.memory.push(state, discrete_action, reward, next_state, done)
        
        # Track metric for attack successes (severity > 0 and reward is positive for attacker)
        self.total_attacks += 1
        if reward > 0.3:
            self.attack_success_count += 1

    def learn(self, state: Any, action_dict: Dict[str, Any], reward: float, next_state: Any, done: bool):
        """
        Executes a Q-Network parameter training iteration if batch conditions are met.
        """
        if len(self.memory) < self.config.batch_size:
            return

        # Sample batch
        states, actions, rewards, next_states, dones = self.memory.sample_tensors(self.config.config.batch_size if hasattr(self.config, 'config') else self.config.batch_size)

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

    def get_attack_success_rate(self) -> float:
        """
        Calculates the ratio of positive reward attacks.
        """
        if self.total_attacks == 0:
            return 0.0
        return float(self.attack_success_count) / self.total_attacks

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
            "attack_success_rate": self.get_attack_success_rate()
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
