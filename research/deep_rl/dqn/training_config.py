from typing import List

class DQNConfig:
    def __init__(
        self,
        learning_rate: float = 1e-3,
        gamma: float = 0.99,
        epsilon_start: float = 1.0,
        epsilon_end: float = 0.05,
        epsilon_decay: float = 0.995,
        batch_size: int = 64,
        target_update_freq: int = 10,   # used for hard updates (number of steps)
        tau: float = 0.005,             # used for soft updates
        use_soft_update: bool = True,
        hidden_layers: List[int] = None,
        activation: str = "relu",
        seed: int = 42
    ):
        self.learning_rate = learning_rate
        self.gamma = gamma
        self.epsilon_start = epsilon_start
        self.epsilon_end = epsilon_end
        self.epsilon_decay = epsilon_decay
        self.batch_size = batch_size
        self.target_update_freq = target_update_freq
        self.tau = tau
        self.use_soft_update = use_soft_update
        self.hidden_layers = hidden_layers or [128, 64]
        self.activation = activation.lower()
        self.seed = seed

    def to_dict(self) -> dict:
        return {
            "learning_rate": self.learning_rate,
            "gamma": self.gamma,
            "epsilon_start": self.epsilon_start,
            "epsilon_end": self.epsilon_end,
            "epsilon_decay": self.epsilon_decay,
            "batch_size": self.batch_size,
            "target_update_freq": self.target_update_freq,
            "tau": self.tau,
            "use_soft_update": self.use_soft_update,
            "hidden_layers": self.hidden_layers,
            "activation": self.activation,
            "seed": self.seed
        }
