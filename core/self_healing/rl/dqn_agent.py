import os
import random
import logging
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from typing import Tuple, Dict, Any

logger = logging.getLogger("self_healing.rl.dqn_agent")

class QNetwork(nn.Module):
    """
    Q-Network for DQN. Maps the 72-dimensional grid state vector
    to 10 action values (Q-values).
    """
    def __init__(self, state_dim: int = 72, action_dim: int = 10):
        super(QNetwork, self).__init__()
        self.fc1 = nn.Linear(state_dim, 64)
        self.fc2 = nn.Linear(64, 64)
        self.q_head = nn.Linear(64, action_dim)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if x.dim() == 1:
            x = x.unsqueeze(0)
        x = torch.relu(self.fc1(x))
        x = torch.relu(self.fc2(x))
        q_values = self.q_head(x)
        return q_values

class DQNAgent:
    """
    Double-DQN Agent with target network, epsilon-greedy exploration,
    and checkpoint saving/loading.
    """
    def __init__(self,
                 state_dim: int = 72,
                 action_dim: int = 10,
                 lr: float = 1e-3,
                 gamma: float = 0.99,
                 epsilon_start: float = 1.0,
                 epsilon_end: float = 0.05,
                 epsilon_decay: float = 0.995,
                 target_update_interval: int = 100,
                 tau: float = 0.005,  # Soft update parameter
                 device: str = "cpu"):
        self.device = torch.device(device)
        self.action_dim = action_dim
        self.gamma = gamma
        
        # Epsilon-greedy parameters
        self.epsilon = epsilon_start
        self.epsilon_end = epsilon_end
        self.epsilon_decay = epsilon_decay
        
        self.target_update_interval = target_update_interval
        self.tau = tau
        self.update_counter = 0

        # Networks
        self.q_net = QNetwork(state_dim, action_dim).to(self.device)
        self.target_net = QNetwork(state_dim, action_dim).to(self.device)
        self.target_net.load_state_dict(self.q_net.state_dict())
        self.target_net.eval()

        self.optimizer = optim.Adam(self.q_net.parameters(), lr=lr)
        self.loss_fn = nn.MSELoss()

    def select_action(self, state: np.ndarray, evaluation: bool = False) -> Tuple[int, float]:
        """
        Selects an action using epsilon-greedy exploration.
        Returns:
            action: int
            q_value: float (estimated Q-value of the selected action)
        """
        state_t = torch.FloatTensor(state).to(self.device)
        
        with torch.no_grad():
            q_values = self.q_net(state_t)
            max_q_val = torch.max(q_values).item()
            best_action = torch.argmax(q_values, dim=-1).item()

        if evaluation or random.random() > self.epsilon:
            action = best_action
            q_val = max_q_val
        else:
            action = random.randrange(self.action_dim)
            q_val = q_values[0, action].item()

        return action, q_val

    def decay_epsilon(self):
        self.epsilon = max(self.epsilon_end, self.epsilon * self.epsilon_decay)

    def update(self, batch_data: Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]) -> float:
        """
        Updates the Q-network using Double-DQN loss.
        """
        states, actions, rewards, next_states, dones = batch_data

        states_t = torch.FloatTensor(states).to(self.device)
        actions_t = torch.LongTensor(actions).unsqueeze(1).to(self.device)
        rewards_t = torch.FloatTensor(rewards).to(self.device)
        next_states_t = torch.FloatTensor(next_states).to(self.device)
        dones_t = torch.FloatTensor(dones).to(self.device)

        # Current Q-values: Q(s, a)
        curr_q = self.q_net(states_t).gather(1, actions_t).squeeze(1)

        # Double-DQN: Q_target(s', argmax_a Q(s', a))
        with torch.no_grad():
            # Action selection: a* = argmax_a Q(s', a)
            next_actions = self.q_net(next_states_t).max(1)[1].unsqueeze(1)
            # Action evaluation: Q_target(s', a*)
            next_q = self.target_net(next_states_t).gather(1, next_actions).squeeze(1)
            # Target Q-value
            target_q = rewards_t + self.gamma * next_q * (1.0 - dones_t)

        loss = self.loss_fn(curr_q, target_q)

        # Optimize
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()

        # Update target network
        self.update_counter += 1
        if self.update_counter % self.target_update_interval == 0:
            self._soft_update_target()

        return loss.item()

    def _soft_update_target(self):
        """
        Soft update model parameters: target = tau * local + (1 - tau) * target
        """
        for target_param, local_param in zip(self.target_net.parameters(), self.q_net.parameters()):
            target_param.data.copy_(self.tau * local_param.data + (1.0 - self.tau) * target_param.data)

    def save_checkpoint(self, directory: str, filename: str = "dqn_self_healing.pt"):
        os.makedirs(directory, exist_ok=True)
        path = os.path.join(directory, filename)
        torch.save({
            "q_net_state_dict": self.q_net.state_dict(),
            "target_net_state_dict": self.target_net.state_dict(),
            "optimizer_state": self.optimizer.state_dict(),
            "epsilon": self.epsilon
        }, path)
        logger.info(f"[DQN AGENT] Checkpoint saved successfully to {path}")

    def load_checkpoint(self, path: str) -> bool:
        if not os.path.exists(path):
            logger.warning(f"[DQN AGENT] Checkpoint path does not exist: {path}")
            return False
        try:
            checkpoint = torch.load(path, map_location=self.device)
            self.q_net.load_state_dict(checkpoint["q_net_state_dict"])
            self.target_net.load_state_dict(checkpoint["target_net_state_dict"])
            self.optimizer.load_state_dict(checkpoint["optimizer_state"])
            self.epsilon = checkpoint.get("epsilon", self.epsilon)
            logger.info(f"[DQN AGENT] Checkpoint loaded successfully from {path}")
            return True
        except Exception as e:
            logger.error(f"[DQN AGENT] Failed to load checkpoint: {e}", exc_info=True)
            return False
