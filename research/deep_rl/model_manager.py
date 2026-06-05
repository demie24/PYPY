import os
import json
import pickle
from typing import Dict, Any, Optional

class ModelManager:
    def __init__(self, base_dir: str = None):
        """
        Initializes the model manager pointing to the persistence checkpoints directory.
        """
        # Resolve absolute path to deep_rl/persistence/checkpoints/
        if base_dir is None:
            self.base_dir = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "persistence", "checkpoints")
            )
        else:
            self.base_dir = os.path.abspath(base_dir)
            
        os.makedirs(self.base_dir, exist_ok=True)

    def save_checkpoint(
        self, 
        checkpoint_name: str, 
        model_weights: Any, 
        metadata: Dict[str, Any], 
        training_history: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Saves a framework-agnostic checkpoint (weights, metadata, training history).
        Weights can be standard state-dicts, numpy arrays, or tabular structures.
        """
        checkpoint_dir = os.path.join(self.base_dir, checkpoint_name)
        os.makedirs(checkpoint_dir, exist_ok=True)

        # 1. Save weights/parameters via pickle (supports tab Q-tables, pytorch weights, etc.)
        weights_path = os.path.join(checkpoint_dir, "weights.pkl")
        with open(weights_path, "wb") as f:
            pickle.dump(model_weights, f)

        # 2. Save metadata and training history via JSON
        info = {
            "checkpoint_name": checkpoint_name,
            "metadata": metadata,
            "training_history": training_history or {}
        }
        info_path = os.path.join(checkpoint_dir, "info.json")
        with open(info_path, "w") as f:
            json.dump(info, f, indent=4)

        return checkpoint_dir

    def load_checkpoint(self, checkpoint_name: str) -> Dict[str, Any]:
        """
        Loads a framework-agnostic checkpoint, returning the weights, metadata, and history.
        """
        checkpoint_dir = os.path.join(self.base_dir, checkpoint_name)
        if not os.path.exists(checkpoint_dir):
            raise FileNotFoundError(f"Checkpoint '{checkpoint_name}' not found under {self.base_dir}")

        weights_path = os.path.join(checkpoint_dir, "weights.pkl")
        if not os.path.exists(weights_path):
            raise FileNotFoundError(f"Weights file not found for checkpoint '{checkpoint_name}'")

        with open(weights_path, "rb") as f:
            weights = pickle.load(f)

        info_path = os.path.join(checkpoint_dir, "info.json")
        info = {}
        if os.path.exists(info_path):
            with open(info_path, "r") as f:
                info = json.load(f)

        return {
            "weights": weights,
            "metadata": info.get("metadata", {}),
            "training_history": info.get("training_history", {})
        }

    def list_checkpoints(self) -> list:
        """
        Lists names of all available checkpoints.
        """
        if not os.path.exists(self.base_dir):
            return []
        return [
            d for d in os.listdir(self.base_dir) 
            if os.path.isdir(os.path.join(self.base_dir, d))
        ]
