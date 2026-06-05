import random
from typing import Dict, List, Optional

class EliteSelection:
    def __init__(self, seed: Optional[int] = None):
        """
        Applies selection strategies (Top-K, Tournament, Percentile) to preserve fit agents.
        """
        if seed is not None:
            random.seed(seed)

    def select(
        self,
        agent_fitness: Dict[str, float],
        method: str = "top_k",
        k: int = 3,
        tournament_size: int = 3,
        percentile: float = 0.25
    ) -> List[str]:
        """
        Selects elite agent IDs from the fitness mapping.
        """
        if not agent_fitness:
            return []

        agent_ids = list(agent_fitness.keys())

        if method == "top_k":
            # Sort descending by fitness
            sorted_agents = sorted(agent_ids, key=lambda aid: agent_fitness[aid], reverse=True)
            return sorted_agents[:min(k, len(sorted_agents))]
            
        elif method == "tournament":
            # Run multiple tournaments to pick k elites
            elites = []
            for _ in range(min(k, len(agent_ids))):
                candidates = random.sample(agent_ids, min(tournament_size, len(agent_ids)))
                winner = max(candidates, key=lambda c: agent_fitness[c])
                elites.append(winner)
            return list(set(elites)) # return unique winners
            
        elif method == "percentile":
            sorted_agents = sorted(agent_ids, key=lambda aid: agent_fitness[aid], reverse=True)
            cutoff = max(1, int(len(sorted_agents) * percentile))
            return sorted_agents[:cutoff]

        # Fallback to top_k
        sorted_agents = sorted(agent_ids, key=lambda aid: agent_fitness[aid], reverse=True)
        return sorted_agents[:min(k, len(sorted_agents))]
