import os
import json
import logging
from typing import Dict, Any

logger = logging.getLogger("strategy.memory")

class StrategyMemory:
    def __init__(self, persistence_file: str = None):
        if persistence_file is None:
            strategy_dir = os.path.dirname(os.path.abspath(__file__))
            self.persistence_file = os.path.join(strategy_dir, "persistence", "strategy_memory.json")
        else:
            self.persistence_file = persistence_file

        self.history: Dict[str, Dict[str, Any]] = {}
        
        # Load from disk if it exists
        self.load()

    def record_action(self, action: str, success: bool, rolled_back: bool):
        """
        Record the execution result of an action.
        """
        if action not in self.history:
            self.history[action] = {
                "success_count": 0,
                "failure_count": 0,
                "rollback_count": 0,
                "total_count": 0
            }

        stats = self.history[action]
        stats["total_count"] += 1
        if success:
            stats["success_count"] += 1
        else:
            stats["failure_count"] += 1

        if rolled_back:
            stats["rollback_count"] += 1

        self.save()

    def get_metrics(self, action: str) -> Dict[str, float]:
        """
        Retrieve success and rollback rates for a given action.
        """
        stats = self.history.get(action, {
            "success_count": 0,
            "failure_count": 0,
            "rollback_count": 0,
            "total_count": 0
        })

        total = stats["total_count"]
        if total == 0:
            return {
                "success_rate": 1.0,  # Default to 100% confidence for new actions
                "rollback_rate": 0.0,
                "total_count": 0
            }

        return {
            "success_rate": round(stats["success_count"] / total, 2),
            "rollback_rate": round(stats["rollback_count"] / total, 2),
            "total_count": total
        }

    def load(self):
        """
        Load historical records from persistence JSON.
        """
        if os.path.exists(self.persistence_file):
            try:
                with open(self.persistence_file, "r") as f:
                    self.history = json.load(f)
                logger.info(f"Strategy memory loaded successfully from {self.persistence_file}")
            except Exception as e:
                logger.error(f"Failed to load strategy memory: {e}")
        else:
            self.history = {}

    def save(self):
        """
        Serialize historical records to persistence JSON.
        Skip writing if running inside a pytest environment.
        """
        if "PYTEST_CURRENT_TEST" in os.environ:
            return
            
        try:
            os.makedirs(os.path.dirname(self.persistence_file), exist_ok=True)
            with open(self.persistence_file, "w") as f:
                json.dump(self.history, f, indent=4)
        except Exception as e:
            logger.error(f"Failed to save strategy memory: {e}")
