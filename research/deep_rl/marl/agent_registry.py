from typing import Dict, Any, List, Optional

class AgentRegistry:
    def __init__(self):
        """
        Registry that manages active RL agents, their identifiers, and target team groupings.
        """
        self.agents: Dict[str, Dict[str, Any]] = {}

    def register_agent(self, agent_id: str, agent_instance: Any, team: str) -> None:
        """
        Registers an agent instance under a specific team (red or blue).
        """
        team_lower = team.lower()
        if team_lower not in ["red", "blue"]:
            raise ValueError(f"Team must be 'red' or 'blue', got: {team}")
            
        self.agents[agent_id] = {
            "instance": agent_instance,
            "team": team_lower
        }

    def remove_agent(self, agent_id: str) -> None:
        """
        Removes an agent from the registry.
        """
        if agent_id in self.agents:
            del self.agents[agent_id]

    def get_agent(self, agent_id: str) -> Optional[Any]:
        """
        Retrieves the agent instance associated with an ID.
        """
        if agent_id in self.agents:
            return self.agents[agent_id]["instance"]
        return None

    def list_agents(self, team: Optional[str] = None) -> List[str]:
        """
        Lists registered agent IDs. Can be filtered by team.
        """
        if team is not None:
            team_lower = team.lower()
            return [
                aid for aid, info in self.agents.items()
                if info["team"] == team_lower
            ]
        return list(self.agents.keys())
