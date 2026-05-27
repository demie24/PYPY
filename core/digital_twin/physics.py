import numpy as np
import logging
from typing import List
from grid_topology import GridTopology

logger = logging.getLogger("digital_twin.physics")

class GridPhysicsEngine:
    def __init__(self, topology: GridTopology):
        self.topo = topology
        self.num_buses = topology.num_buses
        self.slack = topology.slack_bus
        
        # Grounding shunt to ensure matrix invertibility
        self.shunt = 1e-6

        # Track line currents from previous step to compute dynamic thermal reactance overloads
        self.prev_currents = {}

        # Phase 5B: Cascade propagation smoothing
        # Thermal reactance factors are blended with history to avoid instant jumps
        # This simulates the thermal time constant of real conductors (~2-5 seconds).
        self._prev_reactance_factors = {}
        self._cascade_alpha = 0.40  # blend rate: 0.40 = 40% new value per step

        # Phase 5B: Per-bus voltage stress history for neighbour load redistribution
        # Neighbours see a lagged voltage effect rather than an instant step change.
        self._bus_voltage_history = {}   # bus_idx -> list of recent V values
        self._voltage_hist_len = 3        # number of history steps to average

    def solve(self, breakers: dict, active_loads: dict, generator_P: dict, generator_Q: dict, generators_online: dict = None):
        """
        Solves the DC Power Flow and computes voltage magnitudes, line currents, and power flows.
        Supports multi-island simulation.
        """
        if generators_online is None:
            generators_online = {0: True, 1: True, 2: True}

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
            prev_factor = self._prev_reactance_factors.get(lid, 1.0)
            blended = prev_factor + self._cascade_alpha * (target_factor - prev_factor)
            reactance_factors[lid] = blended
            self._prev_reactance_factors[lid] = blended

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
            B[i, i] += self.shunt
            
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
                # Island is de-energized
                for bus in comp:
                    theta[bus] = 0.0
                continue
            
            # Select local slack bus: prefer index 0 (Bus_1) if online, otherwise lowest generator index in component
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
                # Residual for local slack
                P[local_slack] = B[local_slack, comp].dot(theta[comp])
            except np.linalg.LinAlgError:
                logger.error(f"Failed to solve local voltage angles for component {comp}")
        
        # 5. Formulate Net Reactive Power Injection Vector Q & Solve Voltages
        Q = np.zeros(self.num_buses)
        for bus_idx, load in active_loads.items():
            Q[bus_idx] -= load["Q"]
        for gen_idx, gen in self.topo.generators.items():
            if generators_online.get(gen_idx, True):
                Q[gen_idx] += generator_Q.get(gen_idx, gen["Q_nom"])
                
        # Active generator buses maintain their voltage setpoints
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

        # Zero out de-energized buses (not connected to any generator)
        for i in range(self.num_buses):
            if i not in connected_buses:
                V[i] = 0.0
                theta[i] = 0.0

        # Clip voltages to reasonable physical boundaries (0.0 to 1.2)
        V = np.clip(V, 0.0, 1.2)

        # Phase 5B: Voltage history smoothing for neighbour stress propagation
        for i in range(self.num_buses):
            hist = self._bus_voltage_history.get(i, [])
            hist.append(float(V[i]))
            if len(hist) > self._voltage_hist_len:
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
            
        for lid, flow in line_flows.items():
            self.prev_currents[lid] = flow["current"]
            
        return V, theta, P, Q, line_flows

    def _get_connected_buses(self, breakers: dict, generators_online: dict = None) -> set:
        """
        Executes a BFS search to find which buses are connected to active generators.
        """
        if generators_online is None:
            generators_online = {0: True, 1: True, 2: True}
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
