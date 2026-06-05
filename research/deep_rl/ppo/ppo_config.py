from typing import List, Dict, Any

class PPOConfig:
    def __init__(
        self,
        learning_rate: float = 3e-4,
        gamma: float = 0.99,
        gae_lambda: float = 0.95,
        clip_epsilon: float = 0.2,
        entropy_coefficient: float = 0.01,
        value_loss_coefficient: float = 0.5,
        batch_size: int = 64,
        epochs_per_update: int = 10,
        hidden_layers: List[int] = None,
        activation: str = "relu",
        seed: int = 42
    ):
        self.learning_rate = learning_rate
        self.gamma = gamma
        self.gae_lambda = gae_lambda
        self.clip_epsilon = clip_epsilon
        self.entropy_coefficient = entropy_coefficient
        self.value_loss_coefficient = value_loss_coefficient
        self.batch_size = batch_size
        self.epochs_per_update = epochs_per_update
        self.hidden_layers = hidden_layers or [128, 64]
        self.activation = activation.lower()
        self.seed = seed

    def to_dict(self) -> Dict[str, Any]:
        return {
            "learning_rate": self.learning_rate,
            "gamma": self.gamma,
            "gae_lambda": self.gae_lambda,
            "clip_epsilon": self.clip_epsilon,
            "entropy_coefficient": self.entropy_coefficient,
            "value_loss_coefficient": self.value_loss_coefficient,
            "batch_size": self.batch_size,
            "epochs_per_update": self.epochs_per_update,
            "hidden_layers": self.hidden_layers,
            "activation": self.activation,
            "seed": self.seed
        }
