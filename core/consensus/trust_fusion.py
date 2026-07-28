import numpy as np
from typing import Dict, List, Any

class TrustFusionEngine:
    """
    Fuses confidence scores from PINN, LSTM, GNN, and ST-GNN into a single unified trust score.
    Includes a stateful sliding window history and dynamic weight adaptation to handle outliers.
    """
    def __init__(self, base_weights: Dict[str, float] = None, window_size: int = 10):
        if base_weights is None:
            self.base_weights = {
                "pinn": 0.25,
                "lstm": 0.25,
                "gnn": 0.25,
                "stgnn": 0.25
            }
        else:
            self.base_weights = base_weights
            
        self.window_size = window_size
        self.history: Dict[str, List[float]] = {k: [] for k in self.base_weights.keys()}

    def fuse(self, pinn_conf: float, lstm_conf: float, gnn_conf: float, stgnn_conf: float) -> float:
        """
        Statefully fuses the confidence/trust levels of the 4 models.
        Applies a penalty to the weights of models that deviate significantly from the group consensus.
        
        Args:
            pinn_conf: Physics-Informed Neural Network confidence score [0.0, 1.0]
            lstm_conf: Long Short-Term Memory confidence score [0.0, 1.0]
            gnn_conf: Graph Neural Network confidence score [0.0, 1.0]
            stgnn_conf: Spatio-Temporal Graph Neural Network confidence score [0.0, 1.0]
            
        Returns:
            fused_trust: A unified trust score in range [0.0, 1.0]
        """
        confs = {
            "pinn": float(np.clip(pinn_conf, 0.0, 1.0)),
            "lstm": float(np.clip(lstm_conf, 0.0, 1.0)),
            "gnn": float(np.clip(gnn_conf, 0.0, 1.0)),
            "stgnn": float(np.clip(stgnn_conf, 0.0, 1.0))
        }

        # 1. Update historical state
        for k, val in confs.items():
            self.history[k].append(val)
            if len(self.history[k]) > self.window_size:
                self.history[k].pop(0)

        # 2. Compute dynamic outlier penalties
        # Models that deviate significantly from the mean of all models are penalized
        vals = list(confs.values())
        mean_conf = np.mean(vals)
        
        dynamic_weights = {}
        for k, val in confs.items():
            dev = abs(val - mean_conf)
            # Weight multiplier drops exponentially with deviation from consensus
            # e.g., deviation of 0.2 leads to multiplier of exp(-0.4) = 0.67
            weight_mult = np.exp(-2.0 * dev)
            dynamic_weights[k] = self.base_weights[k] * weight_mult

        # Normalize weights
        total_weight = sum(dynamic_weights.values())
        if total_weight <= 0:
            dynamic_weights = self.base_weights.copy()
            total_weight = sum(dynamic_weights.values())

        # 3. Fuse scores
        fused_score = sum(dynamic_weights[k] * confs[k] for k in confs) / total_weight
        return float(np.clip(fused_score, 0.0, 1.0))

    def get_history_summary(self) -> Dict[str, Any]:
        """
        Returns average trust/confidence scores from history.
        """
        return {
            k: float(np.mean(v)) if v else 1.0 for k, v in self.history.items()
        }
