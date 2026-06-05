import random
from typing import Dict, Any, List, Optional

class OpponentPool:
    def __init__(self):
        """
        Manages the collection of historical agent snapshots used in self-play matches.
        """
        self.pool: Dict[str, Dict[str, Any]] = {}

    def add_opponent(
        self,
        opponent_id: str,
        model_type: str,
        team: str,
        checkpoint_name: str,
        elo: float = 1000.0
    ) -> None:
        """
        Adds a historical model snapshot to the opponent pool.
        """
        self.pool[opponent_id] = {
            "opponent_id": opponent_id,
            "model_type": model_type,       # "DQN" or "PPO"
            "team": team.lower(),            # "red" or "blue"
            "checkpoint_name": checkpoint_name,
            "elo": elo
        }

    def remove_opponent(self, opponent_id: str) -> None:
        """
        Removes a model snapshot from the opponent pool.
        """
        if opponent_id in self.pool:
            del self.pool[opponent_id]

    def get_opponent(self, opponent_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves metadata associated with an opponent snapshot.
        """
        return self.pool.get(opponent_id)

    def list_opponents(self, team: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Lists opponents in the pool, optionally filtered by team.
        """
        if team is not None:
            team_lower = team.lower()
            return [info for info in self.pool.values() if info["team"] == team_lower]
        return list(self.pool.values())

    def update_elo(self, opponent_id: str, new_elo: float) -> None:
        """
        Updates the ELO rating of a snapshot in the pool.
        """
        if opponent_id in self.pool:
            self.pool[opponent_id]["elo"] = new_elo
