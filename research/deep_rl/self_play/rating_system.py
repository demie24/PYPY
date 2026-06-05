import os
import json
from typing import Dict, Any, Tuple, Optional, List

class RatingSystem:
    def __init__(self, ratings_file: Optional[str] = None, k_factor: float = 32.0):
        """
        Manages ELO rating calculations and persistence of histories.
        """
        self.k_factor = k_factor
        
        # Default ELO ratings path
        if ratings_file is None:
            self.ratings_file = os.path.abspath(
                os.path.join(
                    os.path.dirname(__file__),
                    "..",
                    "persistence",
                    "training_logs",
                    "self_play_ratings.json"
                )
            )
        else:
            self.ratings_file = os.path.abspath(ratings_file)
            
        self.ratings: Dict[str, float] = {}
        self.match_histories: Dict[str, Dict[str, int]] = {} # id -> {wins, losses, draws}
        self.load_ratings()

    def get_rating(self, agent_id: str) -> float:
        """
        Retrieves Elo rating for an agent. Defaults to 1000.0.
        """
        return self.ratings.get(agent_id, 1000.0)

    def set_rating(self, agent_id: str, elo: float) -> None:
        self.ratings[agent_id] = elo

    def record_match(self, agent_a: str, agent_b: str, outcome_a: float) -> Tuple[float, float]:
        """
        Updates ELO ratings based on match outcome.
        outcome_a: 1.0 (A wins), 0.0 (B wins), 0.5 (draw).
        """
        r_a = self.get_rating(agent_a)
        r_b = self.get_rating(agent_b)

        # Expected outcome
        e_a = 1.0 / (1.0 + 10.0 ** ((r_b - r_a) / 400.0))
        e_b = 1.0 / (1.0 + 10.0 ** ((r_a - r_b) / 400.0))

        outcome_b = 1.0 - outcome_a

        # New ratings
        new_r_a = r_a + self.k_factor * (outcome_a - e_a)
        new_r_b = r_b + self.k_factor * (outcome_b - e_b)

        self.ratings[agent_a] = new_r_a
        self.ratings[agent_b] = new_r_b

        # Update win/loss/draw records
        for aid in [agent_a, agent_b]:
            if aid not in self.match_histories:
                self.match_histories[aid] = {"wins": 0, "losses": 0, "draws": 0}

        if outcome_a == 1.0:
            self.match_histories[agent_a]["wins"] += 1
            self.match_histories[agent_b]["losses"] += 1
        elif outcome_a == 0.0:
            self.match_histories[agent_a]["losses"] += 1
            self.match_histories[agent_b]["wins"] += 1
        else:
            self.match_histories[agent_a]["draws"] += 1
            self.match_histories[agent_b]["draws"] += 1

        self.save_ratings()
        return new_r_a, new_r_b

    def save_ratings(self) -> None:
        """
        Saves ELO ratings and histories to a JSON file.
        """
        os.makedirs(os.path.dirname(self.ratings_file), exist_ok=True)
        payload = {
            "ratings": self.ratings,
            "histories": self.match_histories
        }
        with open(self.ratings_file, "w") as f:
            json.dump(payload, f, indent=4)

    def load_ratings(self) -> None:
        """
        Loads ELO ratings and histories.
        """
        if os.path.exists(self.ratings_file):
            try:
                with open(self.ratings_file, "r") as f:
                    payload = json.load(f)
                    self.ratings = payload.get("ratings", {})
                    self.match_histories = payload.get("histories", {})
            except Exception:
                self.ratings = {}
                self.match_histories = {}
