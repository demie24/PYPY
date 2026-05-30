import os
import torch
import torch.nn as nn
import torch.optim as optim
from torch.distributions import Categorical
import numpy as np
import logging
from typing import Dict, Any, Tuple

from core.self_healing.rl.policy_network import PolicyNetwork
from core.self_healing.rl.value_network import ValueNetwork

logger = logging.getLogger("self_healing.rl.ppo_agent")

class PPOAgent:
    """
    PPO Agent implementing clipping actor-critic policy updates
    and GAE advantage estimation for safe self-healing.
    """
    def __init__(self, 
                 state_dim: int = 72, 
                 action_dim: int = 10, 
                 lr_actor: float = 3e-4, 
                 lr_critic: float = 1e-3,
                 device: str = "cpu"):
        self.device = torch.device(device)
        
        self.actor = PolicyNetwork(state_dim, action_dim).to(self.device)
        self.critic = ValueNetwork(state_dim).to(self.device)
        
        self.optimizer_actor = optim.Adam(self.actor.parameters(), lr=lr_actor)
        self.optimizer_critic = optim.Adam(self.critic.parameters(), lr=lr_critic)
        
        self.mse_loss = nn.MSELoss()

    def select_action(self, state: np.ndarray, evaluation: bool = False) -> Tuple[int, float, float]:
        """
        Selects a discrete action based on the policy distribution.
        Returns:
            action: int
            log_prob: float
            value: float
        """
        state_t = torch.FloatTensor(state).to(self.device)
        
        with torch.no_grad():
            logits = self.actor(state_t)
            value = self.critic(state_t).item()
            
            probs = torch.softmax(logits, dim=-1)
            
        if evaluation:
            action = torch.argmax(probs, dim=-1).item()
            log_prob = 0.0
        else:
            dist = Categorical(probs)
            action_t = dist.sample()
            action = action_t.item()
            log_prob = dist.log_prob(action_t).item()
            
        return action, log_prob, value

    def update(self, 
               memory_data: Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray],
               gae_lambda: float = 0.95, 
               gamma: float = 0.99, 
               ppo_epochs: int = 4, 
               batch_size: int = 16, 
               clip_eps: float = 0.2, 
               c1: float = 0.5, 
               c2: float = 0.01) -> Tuple[float, float, float]:
        """
        Optimizes policy and value parameters using GAE advantages.
        """
        states, actions, old_log_probs, values, rewards, dones = memory_data
        
        # 1. Compute GAE Advantages and discounted returns
        n_steps = len(rewards)
        advantages = np.zeros(n_steps, dtype=np.float32)
        returns = np.zeros(n_steps, dtype=np.float32)
        
        last_advantage = 0
        for t in reversed(range(n_steps)):
            if t == n_steps - 1:
                next_val = 0.0
                next_non_terminal = 1.0 - dones[t]
            else:
                next_val = values[t + 1]
                next_non_terminal = 1.0 - dones[t]
                
            delta = rewards[t] + gamma * next_val * next_non_terminal - values[t]
            advantages[t] = last_advantage = delta + gamma * gae_lambda * next_non_terminal * last_advantage
            returns[t] = advantages[t] + values[t]
            
        # Convert to tensors
        states_t = torch.FloatTensor(states).to(self.device)
        actions_t = torch.LongTensor(actions).to(self.device)
        old_log_probs_t = torch.FloatTensor(old_log_probs).to(self.device)
        advantages_t = torch.FloatTensor(advantages).to(self.device)
        returns_t = torch.FloatTensor(returns).to(self.device)
        
        # Normalize advantages
        advantages_t = (advantages_t - advantages_t.mean()) / (advantages_t.std() + 1e-8)
        
        actor_loss_epoch = 0.0
        critic_loss_epoch = 0.0
        entropy_epoch = 0.0
        
        dataset_size = len(states)
        
        # 2. PPO Clipping updates
        for _ in range(ppo_epochs):
            indices = np.arange(dataset_size)
            np.random.shuffle(indices)
            
            for start_idx in range(0, dataset_size, batch_size):
                batch_idx = indices[start_idx : start_idx + batch_size]
                
                b_states = states_t[batch_idx]
                b_actions = actions_t[batch_idx]
                b_old_log_probs = old_log_probs_t[batch_idx]
                b_advantages = advantages_t[batch_idx]
                b_returns = returns_t[batch_idx]
                
                # Forward passes
                logits = self.actor(b_states)
                probs = torch.softmax(logits, dim=-1)
                dist = Categorical(probs)
                
                new_log_probs = dist.log_prob(b_actions)
                entropy = dist.entropy().mean()
                
                new_values = self.critic(b_states).squeeze(-1)
                
                # Policy ratio
                ratios = torch.exp(new_log_probs - b_old_log_probs)
                
                # Actor loss (clipped surrogate object)
                surr1 = ratios * b_advantages
                surr2 = torch.clamp(ratios, 1.0 - clip_eps, 1.0 + clip_eps) * b_advantages
                actor_loss = -torch.min(surr1, surr2).mean()
                
                # Critic loss (MSE value matching)
                critic_loss = self.mse_loss(new_values, b_returns)
                
                # Total loss with entropy bonus
                total_loss = actor_loss + c1 * critic_loss - c2 * entropy
                
                # Optimize
                self.optimizer_actor.zero_grad()
                self.optimizer_critic.zero_grad()
                total_loss.backward()
                self.optimizer_actor.step()
                self.optimizer_critic.step()
                
                actor_loss_epoch += actor_loss.item()
                critic_loss_epoch += critic_loss.item()
                entropy_epoch += entropy.item()
                
        num_updates = ppo_epochs * (dataset_size // batch_size + 1)
        return (
            actor_loss_epoch / num_updates,
            critic_loss_epoch / num_updates,
            entropy_epoch / num_updates
        )

    def save_checkpoint(self, directory: str, filename: str = "ppo_self_healing.pt"):
        os.makedirs(directory, exist_ok=True)
        path = os.path.join(directory, filename)
        torch.save({
            "actor_state_dict": self.actor.state_dict(),
            "critic_state_dict": self.critic.state_dict(),
            "optimizer_actor_state": self.optimizer_actor.state_dict(),
            "optimizer_critic_state": self.optimizer_critic.state_dict(),
        }, path)
        logger.info(f"[PPO AGENT] Checkpoint saved successfully to {path}")

    def load_checkpoint(self, path: str) -> bool:
        if not os.path.exists(path):
            logger.warning(f"[PPO AGENT] Checkpoint path does not exist: {path}")
            return False
        try:
            checkpoint = torch.load(path, map_location=self.device)
            self.actor.load_state_dict(checkpoint["actor_state_dict"])
            self.critic.load_state_dict(checkpoint["critic_state_dict"])
            self.optimizer_actor.load_state_dict(checkpoint["optimizer_actor_state"])
            self.optimizer_critic.load_state_dict(checkpoint["optimizer_critic_state"])
            logger.info(f"[PPO AGENT] Checkpoint loaded successfully from {path}")
            return True
        except Exception as e:
            logger.error(f"[PPO AGENT] Failed to load checkpoint: {e}", exc_info=True)
            return False
