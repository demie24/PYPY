import torch
import torch.optim as optim
from torch.distributions import Categorical
import numpy as np
import os
import sys
from typing import Dict, Any, Union, Optional

# Ensure parent directory is in path to import state encoder, model manager
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from state_encoder import StateEncoder
from model_manager import ModelManager

from ppo_config import PPOConfig
from actor_network import ActorNetwork
from critic_network import CriticNetwork
from ppo_memory import PPOMemory

class PPORedAgent:
    def __init__(self, config: PPOConfig = None, input_dim: int = None, device: str = "cpu"):
        """
        PPO agent representing the Red Team (Attacker) policy-based learning implementation.
        """
        self.config = config or PPOConfig()
        self.device = device

        self.encoder = StateEncoder()
        self.input_dim = input_dim or self.encoder.state_dim
        self.action_space_size = 54

        # Actor and Critic networks initialization
        self.actor = ActorNetwork(
            input_dim=self.input_dim,
            output_dim=self.action_space_size,
            hidden_layers=self.config.hidden_layers,
            activation=self.config.activation,
            seed=self.config.seed
        ).to(self.device)

        self.critic = CriticNetwork(
            input_dim=self.input_dim,
            hidden_layers=self.config.hidden_layers,
            activation=self.config.activation,
            seed=self.config.seed
        ).to(self.device)

        # Separate optimizers or unified optimizer (we use separate for flexible learning rates)
        self.actor_optimizer = optim.Adam(self.actor.parameters(), lr=self.config.learning_rate)
        self.critic_optimizer = optim.Adam(self.critic.parameters(), lr=self.config.learning_rate)

        # Rollout memory
        self.memory = PPOMemory(device=self.device)
        self.model_manager = ModelManager()

        # Research metrics tracking
        self.loss_history = []
        self.actor_loss_history = []
        self.critic_loss_history = []
        self.entropy_history = []
        self.attack_success_count = 0
        self.total_attacks = 0

        # Cached transition values for step boundary matching (since remember & learn are called sequentially)
        self._last_state = None
        self._last_action_idx = None
        self._last_log_prob = None
        self._last_value = None

    def select_action(self, state_vector: Union[torch.Tensor, np.ndarray, Any], eval_mode: bool = False) -> Dict[str, Any]:
        """
        Selects an attack action by mapping state vectors into probability distributions.
        In training mode, samples from the distribution. In evaluation mode, selects argmax.
        """
        # Convert state vector to PyTorch tensor
        if not isinstance(state_vector, torch.Tensor):
            state_tensor = torch.tensor(state_vector, dtype=torch.float32).unsqueeze(0).to(self.device)
        else:
            state_tensor = state_vector.unsqueeze(0).to(self.device)

        # Run model forward passes
        with torch.no_grad():
            probs = self.actor(state_tensor)
            value = self.critic(state_tensor).item()

        dist = Categorical(probs)

        if eval_mode:
            # Deterministic/Greedy action choice
            discrete_action = torch.argmax(probs, dim=-1).item()
            log_prob = dist.log_prob(torch.tensor([discrete_action]).to(self.device)).item()
        else:
            # Categorical action sampling
            action_tensor = dist.sample()
            discrete_action = action_tensor.item()
            log_prob = dist.log_prob(action_tensor).item()

        # Cache step selection properties for storage during training bounds (in remember())
        if not eval_mode:
            # Store raw numpy version of state
            if isinstance(state_vector, torch.Tensor):
                self._last_state = state_vector.cpu().numpy()
            else:
                self._last_state = np.array(state_vector, dtype=np.float32)

            self._last_action_idx = discrete_action
            self._last_log_prob = log_prob
            self._last_value = value

        return self._decode_action(discrete_action)

    def _decode_action(self, action_idx: int) -> Dict[str, Any]:
        """
        Decodes a discrete action index [0, 53] to attack parameter mapping.
        Identical mapping logic to DQN Red Agent for baseline comparisons.
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
        Identical mapping logic to DQN Red Agent for baseline comparisons.
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
        Saves step transition states and cached PPO metrics (log probabilities, values) into buffer memory.
        """
        # Populate rollout memory if cached values are present
        if self._last_state is not None:
            self.memory.store(
                state=self._last_state,
                action=self._last_action_idx,
                log_prob=self._last_log_prob,
                reward=reward,
                value=self._last_value,
                done=done
            )

        # Track performance metrics
        self.total_attacks += 1
        if reward > 0.3:
            self.attack_success_count += 1

    def learn(self, state: Any, action_dict: Dict[str, Any], reward: float, next_state: Any, done: bool):
        """
        Processes model updates via Proximal Policy Optimization clipped objectives and updates weights.
        """
        # Reset cached transition values
        self._last_state = None
        self._last_action_idx = None
        self._last_log_prob = None
        self._last_value = None

        # Learn conditions check: PPO requires collecting trajectories/rollouts first.
        # We trigger learning when a rollout buffer reaches batch size, or when the episode finishes.
        if len(self.memory) < self.config.batch_size and not done:
            return

        if len(self.memory) == 0:
            return

        # 1. Fetch value estimate of final next state to bootstrap value prediction
        if not isinstance(next_state, torch.Tensor):
            next_state_tensor = torch.tensor(next_state, dtype=torch.float32).unsqueeze(0).to(self.device)
        else:
            next_state_tensor = next_state.unsqueeze(0).to(self.device)

        with torch.no_grad():
            next_value = self.critic(next_state_tensor).item()

        # 2. Compute Generalized Advantage Estimations & Returns
        advantages, returns = self.memory.compute_gae(
            next_value=next_value,
            gamma=self.config.gamma,
            gae_lambda=self.config.gae_lambda
        )

        # 3. Retrieve baseline values and randomized minibatch indices
        (
            states,
            actions,
            old_log_probs,
            old_values,
            batches
        ) = self.memory.generate_batches(self.config.batch_size)

        # 4. Multi-epoch updates
        for _ in range(self.config.epochs_per_update):
            for batch_indices in batches:
                # Slice mini-batch parameters
                batch_indices = torch.tensor(batch_indices, dtype=torch.long).to(self.device)
                
                b_states = states[batch_indices]
                b_actions = actions[batch_indices]
                b_old_log_probs = old_log_probs[batch_indices]
                b_returns = returns[batch_indices]
                b_advantages = advantages[batch_indices]

                # Evaluate new action probabilities & values
                probs = self.actor(b_states)
                values = self.critic(b_states).squeeze(-1)

                dist = Categorical(probs)
                entropy = dist.entropy().mean()
                new_log_probs = dist.log_prob(b_actions)

                # Policy ratio: r_t(theta) = pi_theta(a|s) / pi_theta_old(a|s)
                ratios = torch.exp(new_log_probs - b_old_log_probs)

                # Clipped surrogate objective: L^CLIP(theta) = E[ min(r_t * A_t, clip(r_t) * A_t) ]
                surr1 = ratios * b_advantages
                surr2 = torch.clamp(ratios, 1.0 - self.config.clip_epsilon, 1.0 + self.config.clip_epsilon) * b_advantages
                actor_loss = -torch.min(surr1, surr2).mean()

                # Value network objective: Mean Squared Error loss L^VF(phi)
                critic_loss = (b_returns - values).pow(2).mean()

                # Unified objective loss: L = L^CLIP - c_1 * L^VF + c_2 * S[pi]
                total_loss = (
                    actor_loss
                    + self.config.value_loss_coefficient * critic_loss
                    - self.config.entropy_coefficient * entropy
                )

                # Actor gradient descent step
                self.actor_optimizer.zero_grad()
                self.critic_optimizer.zero_grad()
                total_loss.backward()

                # Gradient clipping for stability
                torch.nn.utils.clip_grad_norm_(self.actor.parameters(), 1.0)
                torch.nn.utils.clip_grad_norm_(self.critic.parameters(), 1.0)

                self.actor_optimizer.step()
                self.critic_optimizer.step()

                # Log metrics histories
                self.loss_history.append(total_loss.item())
                self.actor_loss_history.append(actor_loss.item())
                self.critic_loss_history.append(critic_loss.item())
                self.entropy_history.append(entropy.item())

        # Clean rollout memory buffer ready for the next rollout cycle
        self.memory.clear()

    def get_attack_success_rate(self) -> float:
        """
        Calculates the ratio of positive reward attacks.
        """
        if self.total_attacks == 0:
            return 0.0
        return float(self.attack_success_count) / self.total_attacks

    def save_model(self, checkpoint_name: str) -> str:
        """
        Saves actor weights, critic weights, optimizer states, configurations, and training metrics history.
        """
        weights = {
            "actor": self.actor.state_dict(),
            "critic": self.critic.state_dict(),
            "actor_optimizer": self.actor_optimizer.state_dict(),
            "critic_optimizer": self.critic_optimizer.state_dict()
        }
        metadata = {
            "config": self.config.to_dict()
        }
        history = {
            "loss_history": self.loss_history,
            "actor_loss_history": self.actor_loss_history,
            "critic_loss_history": self.critic_loss_history,
            "entropy_history": self.entropy_history,
            "attack_success_rate": self.get_attack_success_rate()
        }
        return self.model_manager.save_checkpoint(checkpoint_name, weights, metadata, history)

    def load_model(self, checkpoint_name: str):
        """
        Restores PPO model checkpoints (actor/critic weights and training history logs).
        """
        checkpoint = self.model_manager.load_checkpoint(checkpoint_name)
        weights = checkpoint["weights"]
        history = checkpoint["training_history"]

        self.actor.load_state_dict(weights["actor"])
        self.critic.load_state_dict(weights["critic"])
        self.actor_optimizer.load_state_dict(weights["actor_optimizer"])
        self.critic_optimizer.load_state_dict(weights["critic_optimizer"])

        self.loss_history = history.get("loss_history", [])
        self.actor_loss_history = history.get("actor_loss_history", [])
        self.critic_loss_history = history.get("critic_loss_history", [])
        self.entropy_history = history.get("entropy_history", [])
