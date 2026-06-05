import numpy as np
import random
from typing import Dict, Any, Tuple, List, Optional

class CoordinationManager:
    def __init__(self, seed: Optional[int] = None):
        """
        Coordinates and resolves concurrent actions from multiple agents.
        """
        if seed is not None:
            random.seed(seed)

    def resolve_red_actions(self, actions: Dict[str, Dict[str, Any]]) -> Tuple[Dict[str, Any], int]:
        """
        Resolves conflicts between multiple Red Agent actions.
        Rules:
        - If targeting the same bus: combine/sum severity (capped at 1.0) and average stealth.
        - If targeting different buses: conflict is triggered. Resolve by choosing the action
          with the highest severity. If severities are equal, select the action with higher stealth,
          falling back to agent ID sorting.
        """
        if not actions:
            # Default nominal non-attack action
            return {
                "target": "Bus_5",
                "attack_type": "FDIA",
                "severity": 0.0,
                "stealth": 1.0
            }, 0

        if len(actions) == 1:
            return list(actions.values())[0], 0

        # Extract all targets and check for conflicts
        targets = [act.get("target", "Bus_5") for act in actions.values()]
        unique_targets = list(set(targets))
        
        conflicts = 0
        if len(unique_targets) > 1:
            conflicts = len(unique_targets) - 1

        # Check if all agents targeted the same bus (cooperation)
        if len(unique_targets) == 1:
            target_bus = unique_targets[0]
            # Get all actions targeting this bus
            acts = list(actions.values())
            
            # Combine severity (cap at 1.0)
            combined_severity = min(1.0, sum(float(a.get("severity", 0.0)) for a in acts))
            # Average stealth
            avg_stealth = sum(float(a.get("stealth", 0.5)) for a in acts) / len(acts)
            # Default attack type to FDIA or DoS depending on counts
            attack_types = [a.get("attack_type", "FDIA") for a in acts]
            chosen_type = max(set(attack_types), key=attack_types.count)

            return {
                "target": target_bus,
                "attack_type": chosen_type,
                "severity": combined_severity,
                "stealth": avg_stealth
            }, 0

        # Resolve conflict (different buses): choose the most dominant attack
        sorted_agents = sorted(actions.keys(), key=lambda k: (
            float(actions[k].get("severity", 0.0)),
            float(actions[k].get("stealth", 0.0)),
            k
        ), reverse=True)

        winning_agent = sorted_agents[0]
        return actions[winning_agent], conflicts

    def resolve_blue_actions(self, actions: Dict[str, Dict[str, Any]], state_vector: np.ndarray) -> Tuple[Dict[str, Any], int]:
        """
        Resolves conflicts between multiple Blue Agent actions.
        Rules:
        - If multiple defensive routing strategies are chosen (e.g. isolating different buses),
          resolve by checking the state vector: prioritize isolating/quarantining the bus
          with the highest threat score or lowest trust score.
        - If general strategies conflict (e.g., STRICT vs PREDICTIVE), prioritize the stricter defense.
        """
        if not actions:
            return {
                "routing_strategy": "DEFAULT",
                "anomaly_threshold": 0.5,
                "rollback_lockout": 0.0,
                "trust_decay_speed": "NORMAL"
            }, 0

        if len(actions) == 1:
            return list(actions.values())[0], 0

        # Check for conflicts in routing strategies
        strategies = [act.get("routing_strategy", "DEFAULT") for act in actions.values()]
        unique_strategies = list(set(strategies))
        
        conflicts = 0
        if len(unique_strategies) > 1:
            conflicts = len(unique_strategies) - 1

        # Helper function to extract bus number from strategy
        def get_bus_from_strategy(strategy: str) -> Optional[int]:
            if "BUS_" in strategy:
                try:
                    return int(strategy.split("_")[-1])
                except ValueError:
                    pass
            return None

        # Resolve based on state vector metrics
        # State vector contains: 9 buses * 5 attributes each = 45 attributes
        # Attribute index per bus: 0: voltage, 1: freq, 2: trust, 3: threat, 4: anomaly
        def score_strategy(agent_id: str) -> float:
            act = actions[agent_id]
            strat = act.get("routing_strategy", "DEFAULT")
            bus_num = get_bus_from_strategy(strat)
            
            if bus_num is not None:
                # Retrieve bus threat and trust from state vector
                bus_idx = bus_num - 1
                if len(state_vector) >= (bus_idx * 5 + 4):
                    trust = float(state_vector[bus_idx * 5 + 2])
                    threat = float(state_vector[bus_idx * 5 + 3])
                    # Higher threat & lower trust = higher priority for defense
                    return threat + (1.0 - trust) * 10.0
            
            # Non-bus specific strategy scores
            priorities = {
                "STRICT": 5.0,
                "QUARANTINE": 4.5,
                "PREDICTIVE": 4.0,
                "ENHANCED": 3.0,
                "RESTORATION_PRIORITY": 2.0,
                "DEFAULT": 1.0
            }
            for p_name, val in priorities.items():
                if p_name in strat:
                    return val
            return 0.0

        # Sort agents by strategy score (highest score first)
        sorted_agents = sorted(actions.keys(), key=lambda k: (
            score_strategy(k),
            -float(actions[k].get("anomaly_threshold", 0.5)),
            k
        ), reverse=True)

        winning_agent = sorted_agents[0]
        return actions[winning_agent], conflicts
