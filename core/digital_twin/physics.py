import numpy as np
import logging
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

    def solve(self, breakers: dict, active_loads: dict, generator_P: dict, generator_Q: dict):
        """
        Solves the DC Power Flow and computes voltage magnitudes, line currents, and power flows.
        
        Parameters:
        - breakers: dict of line_id -> "CLOSED" or "OPEN"
        - active_loads: dict of bus_index -> {"P": float, "Q": float}
        - generator_P: dict of generator_index -> float (P output setpoint)
        - generator_Q: dict of generator_index -> float (Q output setpoint)
        """
        # 1. Connectivity analysis (BFS to find de-energized islands)
        connected_buses = self._get_connected_buses(breakers)
        
        # 2. Formulate the B' susceptance matrix
        # B_ij = -1/X_ij (for line i-j)
        # B_ii = sum(1/X_ik) + shunt
        #
        # Apply thermal overcurrent stress: overloaded lines heat up, increasing reactance
        # Reactance increases linearly for currents above 1.8 p.u. (max 1.6x at 3.0 p.u.)
        reactance_factors = {}
        for line in self.topo.lines:
            lid = line["id"]
            prev_i = self.prev_currents.get(lid, 0.0)
            if prev_i > 1.8:
                factor = 1.0 + 0.5 * (prev_i - 1.8)
                reactance_factors[lid] = min(1.6, factor)
            else:
                reactance_factors[lid] = 1.0

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
                
        # Add shunt to diagonal for numerical stability (handles singular cases of islanding)
        for i in range(self.num_buses):
            B[i, i] += self.shunt
            
        # 3. Formulate Net Active Power Injection Vector P
        P = np.zeros(self.num_buses)
        
        # Load injections (Load is negative injection)
        for bus_idx, load in active_loads.items():
            P[bus_idx] -= load["P"]
            
        # Generator injections (Gen is positive injection)
        for gen_idx, gen in self.topo.generators.items():
            if gen_idx != self.slack: # Slack bus injection is solved as residual
                P[gen_idx] += generator_P.get(gen_idx, gen["P_nom"])
                
        # 4. Partition and Solve for Voltage Angles (theta)
        # Set slack bus angle theta_slack = 0
        # P_noslack = B_noslack * theta_noslack -> theta_noslack = B_noslack^-1 * P_noslack
        noslack_indices = [i for i in range(self.num_buses) if i != self.slack]
        B_noslack = B[np.ix_(noslack_indices, noslack_indices)]
        P_noslack = P[noslack_indices]
        
        theta = np.zeros(self.num_buses)
        try:
            theta_noslack = np.linalg.solve(B_noslack, P_noslack)
            theta[noslack_indices] = theta_noslack
        except np.linalg.LinAlgError:
            logger.error("Failed to solve voltage angles (singular matrix).")
            
        # Slack bus active power is solved as residual
        P[self.slack] = B[self.slack, :].dot(theta)
        
        # 5. Formulate Net Reactive Power Injection Vector Q & Solve Voltages
        # We estimate voltage magnitudes V using Decoupled Q-V equations: V = V_set - B^-1 * Q
        Q = np.zeros(self.num_buses)
        for bus_idx, load in active_loads.items():
            Q[bus_idx] -= load["Q"]
        for gen_idx, gen in self.topo.generators.items():
            if gen_idx != self.slack:
                Q[gen_idx] += generator_Q.get(gen_idx, gen["Q_nom"])
                
        # Active generator buses maintain their voltage setpoints
        V = np.ones(self.num_buses)
        for gen_idx, gen in self.topo.generators.items():
            V[gen_idx] = gen["V_set"]
            
        # For load / junction buses, calculate voltage drop
        load_indices = [i for i in range(self.num_buses) if i not in self.topo.generators]
        B_LL = B[np.ix_(load_indices, load_indices)]
        Q_L = Q[load_indices]
        
        try:
            # V_L = 1.0 - B_LL^-1 * Q_L
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

        # 6. Compute Line active/reactive power flows and currents
        line_flows = {}
        for line in self.topo.lines:
            f, t, lid = line["from"], line["to"], line["id"]
            x_val = line["X"] * reactance_factors.get(lid, 1.0)
            if breakers.get(lid, "CLOSED") == "CLOSED" and f in connected_buses and t in connected_buses:
                # Active Power Flow: P_ij = (theta_i - theta_j) / X_ij
                p_flow = (theta[f] - theta[t]) / x_val
                
                # Reactive Power Flow: Q_ij = (V_i - V_j) / X_ij
                q_flow = (V[f] - V[t]) / x_val
                
                # Current Magnitude: I_ij = sqrt(P_ij^2 + Q_ij^2) / V_i
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
            
        # Save line currents for the next sweep's thermal calculation
        for lid, flow in line_flows.items():
            self.prev_currents[lid] = flow["current"]
            
        return V, theta, P, Q, line_flows

    def _get_connected_buses(self, breakers: dict) -> set:
        """
        Executes a BFS search to find which buses are connected to active generators.
        Buses disconnected from all generators are considered de-energized (islanded).
        """
        # Starting nodes are generator buses (Bus 1, 2, 3 -> index 0, 1, 2)
        generators = set(self.topo.generators.keys())
        visited = set(generators)
        queue = list(generators)
        
        # Build adjacency list based on closed breakers
        adj = {i: [] for i in range(self.num_buses)}
        for line in self.topo.lines:
            f, t, lid = line["from"], line["to"], line["id"]
            if breakers.get(lid, "CLOSED") == "CLOSED":
                adj[f].append(t)
                adj[t].append(f)
                
        # BFS Traversal
        while queue:
            node = queue.pop(0)
            for neighbor in adj[node]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
                    
        return visited
