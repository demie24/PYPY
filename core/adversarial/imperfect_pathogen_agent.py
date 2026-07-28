import os
import torch
import torch.nn as nn
import torch.optim as optim
from torch.distributions import Categorical, Normal
import numpy as np
from typing import Dict, Any, Tuple
from core.adversarial.belief_encoder import GRUBeliefEncoder

class PathogenRecurrentPolicyNetwork(nn.Module):
    """
    Recurrent Policy Network mapping the belief state (64 dims)
    to action type (8 choices), target (46 choices), and continuous magnitude.
    """
    def __init__(self, belief_dim: int = 64, num_action_types: int = 8, num_targets: int = 46):
        super(PathogenRecurrentPolicyNetwork, self).__init__()
        
        self.shared = nn.Sequential(
            nn.Linear(belief_dim, 64),
            nn.ReLU()
        )
        
        self.action_type_head = nn.Linear(64, num_action_types)
        self.target_head = nn.Linear(64, num_targets)
        
        self.magnitude_mean = nn.Linear(64, 1)
        self.magnitude_log_std = nn.Parameter(torch.zeros(1))

    def forward(self, belief: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        features = self.shared(belief)
        
        action_logits = self.action_type_head(features)
        target_logits = self.target_head(features)
        
        mag_mean = torch.tanh(self.magnitude_mean(features)) * 0.20
        mag_std = torch.clamp(torch.exp(self.magnitude_log_std), min=1e-3, max=1.0)
        
        return action_logits, target_logits, mag_mean, mag_std

class PathogenRecurrentValueNetwork(nn.Module):
    """
    Recurrent Critic Network mapping the belief state to a scalar value.
    """
    def __init__(self, belief_dim: int = 64):
        super(PathogenRecurrentValueNetwork, self).__init__()
        self.net = nn.Sequential(
            nn.Linear(belief_dim, 64),
            nn.ReLU(),
            nn.Linear(64, 1)
        )

    def forward(self, belief: torch.Tensor) -> torch.Tensor:
        return self.net(belief)

class ImperfectPathogenAgent:
    """
    Imperfect Pathogen Agent implementing recurrent PPO clipping updates
    driven by the GRU Belief Encoder.
    """
    def __init__(
        self,
        obs_dim: int = 293,
        belief_dim: int = 64,
        lr_actor: float = 3e-4,
        lr_critic: float = 1e-3,
        device: str = "cpu"
    ):
        self.device = torch.device(device)
        self.belief_dim = belief_dim
        
        # Core recurrent components
        self.belief_encoder = GRUBeliefEncoder(obs_dim=obs_dim, action_dim=8, hidden_dim=belief_dim).to(self.device)
        self.actor = PathogenRecurrentPolicyNetwork(belief_dim=belief_dim).to(self.device)
        self.critic = PathogenRecurrentValueNetwork(belief_dim=belief_dim).to(self.device)
        
        # Optimizers
        self.optimizer_belief = optim.Adam(self.belief_encoder.parameters(), lr=lr_actor)
        self.optimizer_actor = optim.Adam(self.actor.parameters(), lr=lr_actor)
        self.optimizer_critic = optim.Adam(self.critic.parameters(), lr=lr_critic)
        
        self.mse_loss = nn.MSELoss()

    def select_action(
        self,
        obs: np.ndarray,
        prev_action: int,
        prev_belief: np.ndarray,
        evaluation: bool = False
    ) -> Tuple[Dict[str, Any], float, float, np.ndarray]:
        """
        Processes observation through the GRU belief encoder, and samples action choices.
        """
        obs_t = torch.FloatTensor(obs).to(self.device).unsqueeze(0)
        prev_act_t = torch.LongTensor([prev_action]).to(self.device)
        prev_bel_t = torch.FloatTensor(prev_belief).to(self.device).unsqueeze(0)
        
        with torch.no_grad():
            belief_t = self.belief_encoder(obs_t, prev_act_t, prev_bel_t)
            act_logits, trg_logits, mag_mean, mag_std = self.actor(belief_t)
            value = self.critic(belief_t).item()
            
            act_probs = torch.softmax(act_logits, dim=-1)
            trg_probs = torch.softmax(trg_logits, dim=-1)
            
        belief_np = belief_t.squeeze(0).cpu().numpy()

        if evaluation:
            act_type = torch.argmax(act_probs, dim=-1).item()
            act_target = torch.argmax(trg_probs, dim=-1).item()
            act_mag = mag_mean.item()
            log_prob = 0.0
        else:
            # Sample categorical types and targets
            dist_act = Categorical(act_probs)
            dist_trg = Categorical(trg_probs)
            
            act_type_t = dist_act.sample()
            act_trg_t = dist_trg.sample()
            
            # Sample continuous magnitude
            dist_mag = Normal(mag_mean, mag_std)
            act_mag_t = dist_mag.sample()
            
            act_type = act_type_t.item()
            act_target = act_trg_t.item()
            act_mag = act_mag_t.item()
            
            # Sum component log probs
            log_prob = (
                dist_act.log_prob(act_type_t) +
                dist_trg.log_prob(act_trg_t) +
                dist_mag.log_prob(act_mag_t).sum()
            ).item()

        action = {
            "type": act_type,
            "target": act_target,
            "magnitude": np.array([act_mag], dtype=np.float32)
        }
        
        return action, log_prob, value, belief_np

    def save_checkpoint(self, path: str, filename: str) -> None:
        os.makedirs(path, exist_ok=True)
        checkpoint = {
            "belief_encoder": self.belief_encoder.state_dict(),
            "actor": self.actor.state_dict(),
            "critic": self.critic.state_dict()
        }
        torch.save(checkpoint, os.path.join(path, filename))

    def load_checkpoint(self, filepath: str) -> None:
        if os.path.exists(filepath):
            checkpoint = torch.load(filepath, map_location=self.device)
            self.belief_encoder.load_state_dict(checkpoint["belief_encoder"])
            self.actor.load_state_dict(checkpoint["actor"])
            self.critic.load_state_dict(checkpoint["critic"])

    def update(
        self,
        memory: Tuple,
        gamma: float = 0.99,
        gae_lambda: float = 0.95,
        ppo_epochs: int = 4,
        clip_eps: float = 0.2,
        c1: float = 0.5,
        c2: float = 0.01
    ) -> Tuple[float, float]:
        """
        Performs recurrent PPO clipping updates over the collected trajectory.
        """
        obs, prev_actions, act_types, act_targets, act_mags, old_log_probs, values, rewards, dones = memory
        
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
        obs_t = torch.FloatTensor(np.array(obs)).to(self.device)
        prev_acts_t = torch.LongTensor(np.array(prev_actions)).to(self.device)
        act_types_t = torch.LongTensor(np.array(act_types)).to(self.device)
        act_targets_t = torch.LongTensor(np.array(act_targets)).to(self.device)
        act_mags_t = torch.FloatTensor(np.array(act_mags)).to(self.device)
        old_log_probs_t = torch.FloatTensor(np.array(old_log_probs)).to(self.device)
        advantages_t = torch.FloatTensor(np.array(advantages)).to(self.device)
        returns_t = torch.FloatTensor(np.array(returns)).to(self.device)
        
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
        
        for _ in range(ppo_epochs):
            # Compute belief states sequentially starting from zero belief
            belief = torch.zeros(1, self.belief_dim).to(self.device)
            beliefs = []
            
            for t in range(n_steps):
                belief = self.belief_encoder(obs_t[t].unsqueeze(0), prev_acts_t[t].unsqueeze(0), belief)
                beliefs.append(belief)
                
            beliefs_t = torch.cat(beliefs, dim=0)
            
            # Forward policy and critic
            act_logits, trg_logits, mag_mean, mag_std = self.actor(beliefs_t)
            new_values = self.critic(beliefs_t).squeeze(-1)
            
            dist_act = Categorical(torch.softmax(act_logits, dim=-1))
            dist_trg = Categorical(torch.softmax(trg_logits, dim=-1))
            dist_mag = Normal(mag_mean, mag_std)
            
            new_log_probs = (
                dist_act.log_prob(act_types_t) +
                dist_trg.log_prob(act_targets_t) +
                dist_mag.log_prob(act_mags_t).squeeze(-1)
            )
            
            entropy = dist_act.entropy().mean() + dist_trg.entropy().mean() + dist_mag.entropy().mean()
            
            ratios = torch.exp(new_log_probs - old_log_probs_t)
            
            surr1 = ratios * advantages_t
            surr2 = torch.clamp(ratios, 1.0 - clip_eps, 1.0 + clip_eps) * advantages_t
            actor_loss = -torch.min(surr1, surr2).mean()
            
            critic_loss = self.mse_loss(new_values, returns_t)
            
            total_loss = actor_loss + c1 * critic_loss - c2 * entropy
            
            self.optimizer_belief.zero_grad()
            self.optimizer_actor.zero_grad()
            self.optimizer_critic.zero_grad()
            total_loss.backward()
            
            nn.utils.clip_grad_norm_(self.belief_encoder.parameters(), max_norm=0.5)
            nn.utils.clip_grad_norm_(self.actor.parameters(), max_norm=0.5)
            nn.utils.clip_grad_norm_(self.critic.parameters(), max_norm=0.5)
            
            self.optimizer_belief.step()
            self.optimizer_actor.step()
            self.optimizer_critic.step()
            
            actor_loss_epoch += actor_loss.item()
            critic_loss_epoch += critic_loss.item()
            
        return actor_loss_epoch / ppo_epochs, critic_loss_epoch / ppo_epochs
