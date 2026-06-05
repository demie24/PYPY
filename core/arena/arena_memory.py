import os
import json
import logging
from typing import Dict, Any, List

logger = logging.getLogger("arena.arena_memory")

class ArenaMemory:
    def __init__(self, persistence_file: str = "arena_memory.json"):
        # Put persistence under a subfolder if running inside package
        base_dir = os.path.dirname(os.path.abspath(__file__))
        persist_dir = os.path.join(base_dir, "persistence")
        os.makedirs(persist_dir, exist_ok=True)
        
        self.persistence_path = os.path.join(persist_dir, persistence_file)
        self.history: List[Dict[str, Any]] = []

    def record_match(
        self, 
        round_id: int, 
        red_action: Dict[str, Any], 
        blue_action: Dict[str, Any], 
        results: Dict[str, Any],
        red_reward: float,
        blue_reward: float
    ):
        """
        Record a match round outcome to history cache.
        """
        self.history.append({
            "round_id": round_id,
            "red_action": red_action,
            "blue_action": blue_action,
            "results": results,
            "red_reward": round(red_reward, 3),
            "blue_reward": round(blue_reward, 3)
        })

    def save_state(self, red_q_table: Dict[str, List[float]], blue_q_table: Dict[str, List[float]]):
        """
        Write agents Q-tables and training history to disk.
        """
        payload = {
            "red_q_table": red_q_table,
            "blue_q_table": blue_q_table,
            "history": self.history[-500:] # Cap history length to avoid huge files
        }
        try:
            with open(self.persistence_path, "w") as f:
                json.dump(payload, f, indent=2)
            logger.debug(f"Saved Arena Memory state to {self.persistence_path}")
        except Exception as e:
            logger.error(f"Failed to write Arena Memory state: {e}")

    def load_state(self) -> Dict[str, Any]:
        """
        Load historical Q-tables and history from disk.
        """
        if not os.path.exists(self.persistence_path):
            logger.info("No existing Arena Memory file found. Initializing cold start.")
            return {"red_q_table": {}, "blue_q_table": {}, "history": []}
        
        try:
            with open(self.persistence_path, "r") as f:
                data = json.load(f)
            self.history = data.get("history", [])
            logger.info(f"Loaded Arena Memory state from {self.persistence_path}")
            return data
        except Exception as e:
            logger.error(f"Failed to read Arena Memory state: {e}")
            return {"red_q_table": {}, "blue_q_table": {}, "history": []}
