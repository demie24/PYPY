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

class PPOBlueAgent:
    def __init__(self, config: PPOConfig = None, input_dim: int = None, device: str = "cpu"):
        """
        PPO agent representing the Blue Team (Defender) policy-based learning implementation.
        """
        self.config = config or PPOConfig()
        self.device = device

        self.encoder = StateEncoder()
        self.input_dim = input_dim or self.encoder.state_dim
        self.action_space_size = 32

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

        # Separate optimizers or unified optimizer (we use separate for consistency with PPORedAgent)
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

        # Grid performance metrics
        self.total_steps = 0
        self.detection_success_count = 0
        self.total_attacks_observed = 0
        self.containment_success_count = 0
        self.total_containments_triggered = 0
        self.stability_preserved_steps = 0
        self.trust_preservation_accumulator = 0.0
        self.false_positive_count = 0
        self.total_clean_steps = 0

        # Cached transition values for step boundary matching (since remember & learn are called sequentially)
        self._last_state = None
        self._last_action_idx = None
        self._last_log_prob = None
        self._last_value = None

    def select_action(self, state_vector: Union[torch.Tensor, np.ndarray, Any], eval_mode: bool = False) -> Dict[str, Any]:
        """
        Selects a defensive action by mapping state vectors into probability distributions.
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
        Decodes a discrete action index [0, 31] to defender parameter mapping.
        Identical mapping logic to DQN Blue Agent for baseline comparisons.
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
        Identical mapping logic to DQN Blue Agent for baseline comparisons.
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
        Saves step transition states and cached PPO metrics into buffer memory, and updates defender statistics.
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

        # Track statistics based on state values
        self.total_steps += 1
        
        try:
            # Parse next_state values for metrics mapping
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
                f_deviations += abs(freq - 1.0)
                avg_trust += trust
                
                if threat > 0.0:
                    threat_active = True
                if anomaly > 0.0:
                    anomalies_active = True

            avg_trust /= 9.0
            self.trust_preservation_accumulator += avg_trust

            # Check if grid meets stability bounds
            if (v_deviations / 9.0 < 0.05) and (f_deviations / 9.0 < 0.05):
                self.stability_preserved_steps += 1
                
            # Threat detection: Correct anomalies active when actual threats are active
            if threat_active:
                self.total_attacks_observed += 1
                if anomalies_active:
                    self.detection_success_count += 1
            else:
                self.total_clean_steps += 1
                # Check for false positive: took isolating/quarantining actions when there is no threat
                if self._last_action_idx is not None and self._last_action_idx < 18:
                    self.false_positive_count += 1
                    
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
        Processes model updates via Proximal Policy Optimization clipped objectives and updates weights.
        """
        # Reset cached transition values
        self._last_state = None
        self._last_action_idx = None
        self._last_log_prob = None
        self._last_value = None

        # Learn conditions check: PPO requires collecting trajectories/rollouts first.
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

    def get_detection_success_rate(self) -> float:
        if self.total_attacks_observed == 0:
            return 1.0
        return float(self.detection_success_count) / self.total_attacks_observed

    def get_containment_success_rate(self) -> float:
        if self.total_containments_triggered == 0:
            return 1.0
        return float(self.containment_success_count) / self.total_containments_triggered

    def get_false_positive_rate(self) -> float:
        if self.total_clean_steps == 0:
            return 0.0
        return float(self.false_positive_count) / self.total_clean_steps

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
            "total_steps": self.total_steps,
            "detection_success_count": self.detection_success_count,
            "total_attacks_observed": self.total_attacks_observed,
            "containment_success_count": self.containment_success_count,
            "total_containments_triggered": self.total_containments_triggered,
            "stability_preserved_steps": self.stability_preserved_steps,
            "trust_preservation_accumulator": self.trust_preservation_accumulator,
            "false_positive_count": self.false_positive_count,
            "total_clean_steps": self.total_clean_steps,
            "detection_success_rate": self.get_detection_success_rate(),
            "containment_success_rate": self.get_containment_success_rate(),
            "false_positive_rate": self.get_false_positive_rate(),
            "stability_preservation": self.get_stability_preservation(),
            "trust_preservation": self.get_trust_preservation()
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
        self.total_steps = history.get("total_steps", 0)
        self.detection_success_count = history.get("detection_success_count", 0)
        self.total_attacks_observed = history.get("total_attacks_observed", 0)
        self.containment_success_count = history.get("containment_success_count", 0)
        self.total_containments_triggered = history.get("total_containments_triggered", 0)
        self.stability_preserved_steps = history.get("stability_preserved_steps", 0)
        self.trust_preservation_accumulator = history.get("trust_preservation_accumulator", 0.0)
        self.false_positive_count = history.get("false_positive_count", 0)
        self.total_clean_steps = history.get("total_clean_steps", 0)
