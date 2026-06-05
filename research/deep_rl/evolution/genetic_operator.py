import torch
import random
from typing import Any, Optional

class GeneticOperator:
    def __init__(self, seed: Optional[int] = None):
        """
        Applies genetic mutations, crossovers, and perturbations to agent weights and configurations.
        """
        if seed is not None:
            random.seed(seed)

    def crossover(self, parent_a: Any, parent_b: Any, child: Any, crossover_rate: float = 0.5) -> None:
        """
        Combines PyTorch parameters and configurations from Parent A and Parent B into Child.
        """
        # Crossover actor/policy weights
        a_net = parent_a.actor if hasattr(parent_a, "actor") else parent_a.policy_net
        b_net = parent_b.actor if hasattr(parent_b, "actor") else parent_b.policy_net
        c_net = child.actor if hasattr(child, "actor") else child.policy_net

        with torch.no_grad():
            a_dict = a_net.state_dict()
            b_dict = b_net.state_dict()
            child_dict = {}
            
            for key in a_dict.keys():
                if random.random() < crossover_rate:
                    child_dict[key] = a_dict[key].clone()
                else:
                    child_dict[key] = b_dict[key].clone()
                    
            c_net.load_state_dict(child_dict)

        # Crossover critic weights (PPO specific)
        if hasattr(parent_a, "critic") and hasattr(parent_b, "critic") and hasattr(child, "critic"):
            with torch.no_grad():
                a_crit_dict = parent_a.critic.state_dict()
                b_crit_dict = parent_b.critic.state_dict()
                child_crit_dict = {}
                
                for key in a_crit_dict.keys():
                    if random.random() < crossover_rate:
                        child_crit_dict[key] = a_crit_dict[key].clone()
                    else:
                        child_crit_dict[key] = b_crit_dict[key].clone()
                        
                child.critic.load_state_dict(child_crit_dict)

        # Mirror weights to DQN target net
        if hasattr(child, "target_net"):
            child.target_net.load_state_dict(child.policy_net.state_dict())

        # Crossover hyperparameters
        p_attrs = ["learning_rate", "gamma", "entropy_coefficient", "value_loss_coefficient", "clip_epsilon"]
        for attr in p_attrs:
            if hasattr(parent_a.config, attr) and hasattr(parent_b.config, attr) and hasattr(child.config, attr):
                val = getattr(parent_a.config, attr) if random.random() < crossover_rate else getattr(parent_b.config, attr)
                setattr(child.config, attr, val)

    def mutate(self, agent: Any, mutation_rate: float = 0.1, mutation_strength: float = 0.02) -> None:
        """
        Mutates agent network parameters and perturbs hyperparameters.
        """
        # Mutate policy/actor weights
        net = agent.actor if hasattr(agent, "actor") else agent.policy_net
        with torch.no_grad():
            for param in net.parameters():
                if random.random() < mutation_rate:
                    noise = torch.randn_like(param) * mutation_strength
                    param.add_(noise)

        # Mutate critic weights
        if hasattr(agent, "critic"):
            with torch.no_grad():
                for param in agent.critic.parameters():
                    if random.random() < mutation_rate:
                        noise = torch.randn_like(param) * mutation_strength
                        param.add_(noise)

        # Mirror weights to DQN target net
        if hasattr(agent, "target_net"):
            agent.target_net.load_state_dict(agent.policy_net.state_dict())

        # Perturb hyperparameters
        p_attrs = ["learning_rate", "gamma", "entropy_coefficient", "value_loss_coefficient", "clip_epsilon"]
        for attr in p_attrs:
            if hasattr(agent.config, attr):
                val = getattr(agent.config, attr)
                # Perturb by ±15%
                multiplier = random.choice([0.85, 1.15])
                new_val = val * multiplier
                
                # Boundaries checks
                if attr == "gamma":
                    new_val = min(0.999, max(0.9, new_val))
                elif attr == "clip_epsilon":
                    new_val = min(0.3, max(0.05, new_val))
                elif attr == "entropy_coefficient":
                    new_val = min(0.1, max(0.001, new_val))
                    
                setattr(agent.config, attr, new_val)
