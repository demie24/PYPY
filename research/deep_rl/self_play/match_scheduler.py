import numpy as np
from typing import Dict, Any, List, Optional
from opponent_pool import OpponentPool
from rating_system import RatingSystem

class MatchScheduler:
    def __init__(self, opponent_pool: OpponentPool, rating_system: RatingSystem):
        """
        Coordinates opponent pairings based on ELO metrics, progression, and league setups.
        """
        self.opponent_pool = opponent_pool
        self.rating_system = rating_system

    def schedule_opponent(
        self,
        agent_id: str,
        opponent_team: str,
        method: str = "random",
        win_rate: float = 0.5
    ) -> Optional[Dict[str, Any]]:
        """
        Schedules a historical match opponent.
        Methods:
        - random: Uniform random choice.
        - league: Closest ELO rating matchup.
        - historical: Opponents matching own ID namespace (e.g. self-snapshots).
        - progression: Opponent chosen dynamically based on win rate (e.g. harder as win_rate increases).
        """
        opponents = self.opponent_pool.list_opponents(team=opponent_team)
        if not opponents:
            return None

        agent_elo = self.rating_system.get_rating(agent_id)

        if method == "random":
            return np.random.choice(opponents)
            
        elif method == "league":
            # Select the opponent with ELO closest to training agent's ELO
            return min(opponents, key=lambda o: abs(o["elo"] - agent_elo))
            
        elif method == "historical":
            # Match own base prefix/id (filter historical versions of self)
            base_prefix = agent_id.split("_")[0]
            self_opps = [o for o in opponents if o["opponent_id"].startswith(base_prefix)]
            if self_opps:
                return np.random.choice(self_opps)
            return np.random.choice(opponents)
            
        elif method == "progression":
            # Sort opponents by Elo (ascending)
            sorted_opps = sorted(opponents, key=lambda o: o["elo"])
            # Index proportional to agent's win rate performance
            idx = int(win_rate * (len(sorted_opps) - 1))
            idx = max(0, min(len(sorted_opps) - 1, idx))
            return sorted_opps[idx]

        return np.random.choice(opponents)
