import os
import json
import logging
from typing import Dict, Any, List

logger = logging.getLogger("assistant.persistent_routine")

class PersistentRoutineMemory:
    def __init__(self, file_path: str = None):
        if file_path is None:
            # Set relative to module
            curr_dir = os.path.dirname(os.path.abspath(__file__))
            self.file_path = os.path.join(curr_dir, "routine_memory.json")
        else:
            self.file_path = file_path
            
        self.interactions: List[Dict[str, Any]] = []
        self.recurrence_history: Dict[str, Dict[str, Any]] = {}
        self.load_memory()

    def load_memory(self) -> None:
        try:
            if os.path.exists(self.file_path):
                with open(self.file_path, "r") as f:
                    data = json.load(f)
                    self.interactions = data.get("interactions", [])
                    self.recurrence_history = data.get("recurrence_history", {})
                logger.info(f"Loaded {len(self.interactions)} persistent routine entries.")
            else:
                self.interactions = []
                self.recurrence_history = {}
        except Exception as e:
            logger.error(f"Failed to load persistent routine memory: {e}")
            self.interactions = []
            self.recurrence_history = {}

    def save_memory(self) -> None:
        try:
            with open(self.file_path, "w") as f:
                json.dump({
                    "interactions": self.interactions,
                    "recurrence_history": self.recurrence_history
                }, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save persistent routine memory: {e}")

    def add_interaction(self, query: str, action: str, timestamp_ms: float = None) -> None:
        if not timestamp_ms:
            import time
            timestamp_ms = int(time.time() * 1000)

        # Map current hour to temporal bin
        from datetime import datetime
        hour = datetime.fromtimestamp(timestamp_ms / 1000.0).hour
        if 0 <= hour < 6:
            bin_name = "NIGHT"
        elif 6 <= hour < 12:
            bin_name = "MORNING"
        elif 12 <= hour < 18:
            bin_name = "AFTERNOON"
        else:
            bin_name = "EVENING"

        interaction = {
            "query": query,
            "action": action,
            "timestamp": timestamp_ms,
            "temporal_bin": bin_name,
            "hour": hour
        }
        self.interactions.append(interaction)
        
        # Track statistics statefully
        if action:
            if action not in self.recurrence_history:
                self.recurrence_history[action] = {
                    "action": action,
                    "count": 0,
                    "bins": {},
                    "last_seen": 0
                }
            rec = self.recurrence_history[action]
            rec["count"] += 1
            rec["last_seen"] = timestamp_ms
            rec["bins"][bin_name] = rec["bins"].get(bin_name, 0) + 1

        self.save_memory()

    def get_recurring_actions(self, threshold: int = 3) -> List[Dict[str, Any]]:
        recurring = []
        for action, data in self.recurrence_history.items():
            if data["count"] >= threshold:
                # Find dominant temporal bin
                dom_bin = "ANYTIME"
                max_val = 0
                for b, val in data["bins"].items():
                    if val > max_val:
                        max_val = val
                        dom_bin = b
                recurring.append({
                    "action": action,
                    "count": data["count"],
                    "dominant_bin": dom_bin,
                    "confidence": min(1.0, data["count"] / 5.0)
                })
        return recurring

    def clear_memory(self) -> None:
        self.interactions = []
        self.recurrence_history = {}
        if os.path.exists(self.file_path):
            try:
                os.remove(self.file_path)
            except Exception as e:
                logger.error(f"Error removing persistent routine file: {e}")
        logger.info("Cleared persistent routine memory file.")

    def get_status_summary(self) -> Dict[str, Any]:
        return {
            "total_interactions": len(self.interactions),
            "recurring_count": len(self.get_recurring_actions()),
            "recurring_actions": self.get_recurring_actions(),
            "latest_interactions": self.interactions[-5:]
        }
