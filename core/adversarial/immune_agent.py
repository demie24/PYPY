import os
import torch
import torch.nn as nn
import torch.optim as optim
from torch.distributions import Categorical
import numpy as np
import logging
from typing import Dict, Any, Tuple

logger = logging.getLogger("adversarial.immune_agent")

class ImmunePolicyNetwork(nn.Module):
    """
    Policy Network for the Artificial Immune System (Blue Agent).
    Outputs discrete defense action type and target component index.
    """
    def __init__(self, state_dim: int = 299, num_action_types: int = 7, num_targets: int = 46):
        super(ImmunePolicyNetwork, self).__init__()
        
        # Shared feature representation network
        self.shared = nn.Sequential(
            nn.Linear(state_dim, 128),
            nn.ReLU(),
            nn.Linear(128, 64),
            nn.ReLU()
        )
        
        # Policy output heads
        self.action_type_head = nn.Linear(64, num_action_types)
        self.target_head = nn.Linear(64, num_targets)

    def forward(self, state: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        features = self.shared(state)
        action_logits = self.action_type_head(features)
        target_logits = self.target_head(features)
        return action_logits, target_logits

class ImmuneValueNetwork(nn.Module):
    """
    Critic Network for state value estimation.
    """
    def __init__(self, state_dim: int = 299):
        super(ImmuneValueNetwork, self).__init__()
        self.net = nn.Sequential(
            nn.Linear(state_dim, 128),
            nn.ReLU(),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, 1)
        )

    def forward(self, state: torch.Tensor) -> torch.Tensor:
        return self.net(state)

class ImmuneAgent:
    """
    Immune System PPO Agent implementing PPO-Clip for multi-discrete actions.
    """
    def __init__(self, state_dim: int = 299, lr_actor: float = 3e-4, lr_critic: float = 1e-3, device: str = "cpu"):
        self.device = torch.device(device)
        
        self.actor = ImmunePolicyNetwork(state_dim).to(self.device)
        self.critic = ImmuneValueNetwork(state_dim).to(self.device)
        
        self.optimizer_actor = optim.Adam(self.actor.parameters(), lr=lr_actor)
        self.optimizer_critic = optim.Adam(self.critic.parameters(), lr=lr_critic)
        
        self.mse_loss = nn.MSELoss()

    def select_action(self, state: np.ndarray, evaluation: bool = False) -> Tuple[Dict[str, Any], float, float]:
        """
        Samples a multi-discrete defense action.
        Returns:
            action: Dict containing type and target
            log_prob: float (joint log probability)
            value: float
        """
        state_t = torch.FloatTensor(state).to(self.device).unsqueeze(0)
        
        with torch.no_grad():
            act_logits, trg_logits = self.actor(state_t)
            value = self.critic(state_t).item()
            
            act_probs = torch.softmax(act_logits, dim=-1)
            trg_probs = torch.softmax(trg_logits, dim=-1)
            
        if evaluation:
            act_type = torch.argmax(act_probs, dim=-1).item()
            act_target = torch.argmax(trg_probs, dim=-1).item()
            log_prob = 0.0
        else:
            # Sample discrete type
            dist_act = Categorical(act_probs)
            act_type_t = dist_act.sample()
            act_type = act_type_t.item()
            
            # Sample discrete target
            dist_trg = Categorical(trg_probs)
            act_target_t = dist_trg.sample()
            act_target = act_target_t.item()
            
            # Combined joint log probability of the multi-discrete action
            log_prob = (
                dist_act.log_prob(act_type_t).item() +
                dist_trg.log_prob(act_target_t).item()
            )
            
        action = {
            "type": act_type,
            "target": act_target
        }
        
        return action, log_prob, value

    def update(self, 
               memory_data: Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray],
               gae_lambda: float = 0.95, 
               gamma: float = 0.99, 
               ppo_epochs: int = 4, 
               batch_size: int = 16, 
               clip_eps: float = 0.2, 
               c1: float = 0.5, 
               c2: float = 0.01) -> Tuple[float, float]:
        """
        Runs batch optimization over stored trajectory parameters.
        """
        states, act_types, act_targets, old_log_probs, values, rewards, dones = memory_data
        
        # Calculate advantages and returns (GAE)
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
        act_types_t = torch.LongTensor(act_types).to(self.device)
        act_targets_t = torch.LongTensor(act_targets).to(self.device)
        old_log_probs_t = torch.FloatTensor(old_log_probs).to(self.device)
        advantages_t = torch.FloatTensor(advantages).to(self.device)
        returns_t = torch.FloatTensor(returns).to(self.device)
        
        if len(advantages_t) > 1:
            adv_std = advantages_t.std()
            if adv_std > 1e-8:
                advantages_t = (advantages_t - advantages_t.mean()) / adv_std
            else:
                advantages_t = advantages_t - advantages_t.mean()
        else:
            advantages_t = torch.zeros_like(advantages_t)
        
        actor_loss_epoch = 0.0
        critic_loss_epoch = 0.0
        dataset_size = len(states)
        
        for _ in range(ppo_epochs):
            indices = np.arange(dataset_size)
            np.random.shuffle(indices)
            
            for start_idx in range(0, dataset_size, batch_size):
                batch_idx = indices[start_idx : start_idx + batch_size]
                
                b_states = states_t[batch_idx]
                b_types = act_types_t[batch_idx]
                b_targets = act_targets_t[batch_idx]
                b_old_log_probs = old_log_probs_t[batch_idx]
                b_advantages = advantages_t[batch_idx]
                b_returns = returns_t[batch_idx]
                
                # Forward actor outputs
                act_logits, trg_logits = self.actor(b_states)
                
                dist_act = Categorical(torch.softmax(act_logits, dim=-1))
                dist_trg = Categorical(torch.softmax(trg_logits, dim=-1))
                
                new_log_probs = (
                    dist_act.log_prob(b_types) +
                    dist_trg.log_prob(b_targets)
                )
                
                entropy = dist_act.entropy().mean() + dist_trg.entropy().mean()
                new_values = self.critic(b_states).squeeze(-1)
                
                ratios = torch.exp(new_log_probs - b_old_log_probs)
                
                # Surrogate loss
                surr1 = ratios * b_advantages
                surr2 = torch.clamp(ratios, 1.0 - clip_eps, 1.0 + clip_eps) * b_advantages
                actor_loss = -torch.min(surr1, surr2).mean()
                
                # Critic loss
                critic_loss = self.mse_loss(new_values, b_returns)
                
                total_loss = actor_loss + c1 * critic_loss - c2 * entropy
                
                self.optimizer_actor.zero_grad()
                self.optimizer_critic.zero_grad()
                total_loss.backward()
                nn.utils.clip_grad_norm_(self.actor.parameters(), max_norm=0.5)
                nn.utils.clip_grad_norm_(self.critic.parameters(), max_norm=0.5)
                self.optimizer_actor.step()
                self.optimizer_critic.step()
                
                actor_loss_epoch += actor_loss.item()
                critic_loss_epoch += critic_loss.item()
                
        num_updates = ppo_epochs * (dataset_size // batch_size + 1)
        return actor_loss_epoch / num_updates, critic_loss_epoch / num_updates

    def save_checkpoint(self, directory: str, filename: str = "ppo_immune.pt"):
        os.makedirs(directory, exist_ok=True)
        path = os.path.join(directory, filename)
        torch.save({
            "actor_state_dict": self.actor.state_dict(),
            "critic_state_dict": self.critic.state_dict(),
            "optimizer_actor_state": self.optimizer_actor.state_dict(),
            "optimizer_critic_state": self.optimizer_critic.state_dict(),
        }, path)

    def load_checkpoint(self, path: str) -> bool:
        if not os.path.exists(path):
            return False
        checkpoint = torch.load(path, map_location=self.device)
        self.actor.load_state_dict(checkpoint["actor_state_dict"])
        self.critic.load_state_dict(checkpoint["critic_state_dict"])
        return True
