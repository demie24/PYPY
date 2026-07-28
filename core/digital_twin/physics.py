import numpy as np
import logging
from typing import List
try:
    from core.digital_twin.grid_topology import GridTopology
    from core.digital_twin.solver import GridACSolver
except ModuleNotFoundError:
    from grid_topology import GridTopology
    from solver import GridACSolver

logger = logging.getLogger("digital_twin.physics")

class GridPhysicsEngine:
    def __init__(self, topology: GridTopology):
        self.topo = topology
        self.num_buses = topology.num_buses
        self.slack = topology.slack_bus
        self.prev_currents = {}
        
        # Instantiate the new dedicated AC solver service if loader is available
        if hasattr(topology, "loader") and topology.loader is not None:
            self.solver = GridACSolver(topology.loader)
        else:
            self.solver = None
        self.last_solver_status = {}

    def solve(self, breakers: dict, active_loads: dict, generator_P: dict, generator_Q: dict, generators_online: dict = None):
        """
        Delegates power flow execution to GridACSolver (AC) or runs local DC power flow (legacy fallback).
        """
        if generators_online is None:
            generators_online = {b: True for b in self.topo.generators.keys()}

        if self.solver is not None:
            V, theta, P, Q, line_flows, status = self.solver.solve_ac(
                breakers, active_loads, generator_P, generator_Q, generators_online
            )
            self.last_solver_status = status
        else:
            # Run the legacy native DC power flow solver
            # 1. Connectivity analysis (BFS to find de-energized islands)
            connected_buses = self._get_connected_buses(breakers, generators_online)

            # 2. Formulate the B' susceptance matrix
            reactance_factors = {}
            for line in self.topo.lines:
                lid = line["id"]
                prev_i = self.prev_currents.get(lid, 0.0)
                if prev_i > 1.8:
                    target_factor = min(1.6, 1.0 + 0.5 * (prev_i - 1.8))
                else:
                    target_factor = 1.0
                prev_factor = getattr(self, "_prev_reactance_factors", {}).get(lid, 1.0)
                if not hasattr(self, "_prev_reactance_factors"):
                    self._prev_reactance_factors = {}
                self._prev_reactance_factors[lid] = prev_factor + 0.2 * (target_factor - prev_factor)
                reactance_factors[lid] = self._prev_reactance_factors[lid]

            shunt = 0.001
            B = np.zeros((self.num_buses, self.num_buses))
            for line in self.topo.lines:
                f, t, lid = line["from"], line["to"], line["id"]
                if breakers.get(lid, "CLOSED") == "CLOSED":
                    x_val = line["X"] * reactance_factors.get(lid, 1.0)
                    b_val = 1.0 / x_val
                    B[f, f] += b_val
                    B[t, t] += b_val
                    B[f, t] -= b_val
                    B[t, f] -= b_val

            for i in range(self.num_buses):
                B[i, i] += shunt

            # 3. Formulate Net Active Power Injection Vector P
            P = np.zeros(self.num_buses)
            for bus_idx, load in active_loads.items():
                P[bus_idx] -= load["P"]
            for gen_idx, gen in self.topo.generators.items():
                if generators_online.get(gen_idx, True):
                    P[gen_idx] += generator_P.get(gen_idx, gen["P_nom"])

            # 4. Partition and Solve for Voltage Angles (theta) per island component
            theta = np.zeros(self.num_buses)
            components = self._get_components(breakers)

            for comp in components:
                comp_online_gens = [b for b in comp if b in self.topo.generators and generators_online.get(b, True)]
                if not comp_online_gens:
                    for bus in comp:
                        theta[bus] = 0.0
                    continue

                if 0 in comp_online_gens:
                    local_slack = 0
                else:
                    local_slack = min(comp_online_gens)

                comp_noslack = [b for b in comp if b != local_slack]
                if not comp_noslack:
                    theta[local_slack] = 0.0
                    continue

                B_comp = B[np.ix_(comp_noslack, comp_noslack)]
                P_comp = P[comp_noslack]

                try:
                    theta_comp = np.linalg.solve(B_comp, P_comp)
                    theta[comp_noslack] = theta_comp
                    theta[local_slack] = 0.0
                except np.linalg.LinAlgError:
                    logger.error(f"Failed to solve local voltage angles for component {comp}")

            # 5. Formulate Net Reactive Power Injection Vector Q & Solve Voltages
            Q = np.zeros(self.num_buses)
            for bus_idx, load in active_loads.items():
                Q[bus_idx] -= load["Q"]
            for gen_idx, gen in self.topo.generators.items():
                if generators_online.get(gen_idx, True):
                    Q[gen_idx] += generator_Q.get(gen_idx, gen["Q_nom"])

            V = np.zeros(self.num_buses)
            for gen_idx, gen in self.topo.generators.items():
                if generators_online.get(gen_idx, True):
                    V[gen_idx] = gen["V_set"]

            load_indices = [i for i in range(self.num_buses) if i not in self.topo.generators]
            B_LL = B[np.ix_(load_indices, load_indices)]
            Q_L = Q[load_indices]

            try:
                delta_V = np.linalg.solve(B_LL, -Q_L)
                V[load_indices] = 1.0 + delta_V
            except np.linalg.LinAlgError:
                pass

            for i in range(self.num_buses):
                if i not in connected_buses:
                    V[i] = 0.0
                    theta[i] = 0.0

            V = np.clip(V, 0.0, 1.2)

            if not hasattr(self, "_bus_voltage_history"):
                self._bus_voltage_history = {}
            for i in range(self.num_buses):
                hist = self._bus_voltage_history.get(i, [])
                hist.append(float(V[i]))
                if len(hist) > 3:
                    hist.pop(0)
                self._bus_voltage_history[i] = hist
                if i not in self.topo.generators and len(hist) >= 2:
                    weights = np.linspace(0.5, 1.0, len(hist))
                    V[i] = float(np.average(hist, weights=weights))
                    V[i] = max(0.0, min(1.2, V[i]))

            # 6. Compute Line active/reactive power flows and currents
            line_flows = {}
            for line in self.topo.lines:
                f, t, lid = line["from"], line["to"], line["id"]
                x_val = line["X"] * reactance_factors.get(lid, 1.0)
                if breakers.get(lid, "CLOSED") == "CLOSED" and f in connected_buses and t in connected_buses:
                    p_flow = (theta[f] - theta[t]) / x_val
                    q_flow = (V[f] - V[t]) / x_val
                    voltage_divisor = V[f] if V[f] > 0.1 else 1.0
                    current = np.sqrt(p_flow**2 + q_flow**2) / voltage_divisor
                else:
                    p_flow = 0.0
                    q_flow = 0.0
                    current = 0.0

                line_flows[lid] = {
                    "P_flow": float(p_flow),
                    "Q_flow": float(q_flow),
                    "current": float(current)
                }

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
