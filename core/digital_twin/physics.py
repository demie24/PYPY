import numpy as np
import logging
from typing import List
from grid_topology import GridTopology
from solver import GridACSolver

logger = logging.getLogger("digital_twin.physics")

class GridPhysicsEngine:
    def __init__(self, topology: GridTopology):
        self.topo = topology
        self.num_buses = topology.num_buses
        self.slack = topology.slack_bus
        self.prev_currents = {}
        
        # Instantiate the new dedicated AC solver service
        self.solver = GridACSolver(topology.loader)
        self.last_solver_status = {}

    def solve(self, breakers: dict, active_loads: dict, generator_P: dict, generator_Q: dict, generators_online: dict = None):
        """
        Delegates the power flow execution to the GridACSolver for AC calculations.
        Supports continuous telemetry tracking logic.
        """
        if generators_online is None:
            generators_online = {b: True for b in self.topo.generators.keys()}

        # Run AC Newton-Raphson simulation sweep
        V, theta, P, Q, line_flows, status = self.solver.solve_ac(
            breakers, active_loads, generator_P, generator_Q, generators_online
        )

        # Cache solver execution logs statefully
        self.last_solver_status = status

        # Keep prev_currents updated for thermal rating overrides
        for lid, flow in line_flows.items():
            self.prev_currents[lid] = flow["current"]

        return V, theta, P, Q, line_flows

    def _get_connected_buses(self, breakers: dict, generators_online: dict = None) -> set:
        """
        Executes a BFS search to find which buses are connected to active generators.
        """
        if generators_online is None:
            generators_online = {b: True for b in self.topo.generators.keys()}
        generators = set(i for i in self.topo.generators.keys() if generators_online.get(i, True))
        visited = set(generators)
        queue = list(generators)
        
        adj = {i: [] for i in range(self.num_buses)}
        for line in self.topo.lines:
            f, t, lid = line["from"], line["to"], line["id"]
            if breakers.get(lid, "CLOSED") == "CLOSED":
                adj[f].append(t)
                adj[t].append(f)
                
        while queue:
            node = queue.pop(0)
            for neighbor in adj[node]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
                    
        return visited

    def _get_components(self, breakers: dict) -> List[List[int]]:
        """
        Calculates connected components (islands) of buses in the current grid state using BFS.
        """
        visited = set()
        components = []
        
        adj = {i: [] for i in range(self.num_buses)}
        for line in self.topo.lines:
            f, t, lid = line["from"], line["to"], line["id"]
            if breakers.get(lid, "CLOSED") == "CLOSED":
                adj[f].append(t)
                adj[t].append(f)
                
        for i in range(self.num_buses):
            if i not in visited:
                comp = []
                queue = [i]
                visited.add(i)
                while queue:
                    curr = queue.pop(0)
                    comp.append(curr)
                    for neighbor in adj[curr]:
                        if neighbor not in visited:
                            visited.add(neighbor)
                            queue.append(neighbor)
                components.append(comp)
        return components
