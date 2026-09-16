import numpy as np
from core.digital_twin.grid_topology import GridTopology
from core.analytics.ptdf_engine import build_b_matrix, get_connected_components

class CascadingFailureSimulator:
    def __init__(self, topo: GridTopology, overload_threshold: float = 1.5, min_capacity: float = 0.5):
        self.topo = topo
        self.overload_threshold = overload_threshold
        self.min_capacity = min_capacity
        self.line_capacities = {}
        self._calculate_nominal_flows()

    def _calculate_nominal_flows(self):
        """
        Solves a nominal DC load flow (all breakers closed) to establish base flows
        and define line thermal capacities.
        """
        breakers_closed = {line["id"]: "CLOSED" for line in self.topo.lines}
        nominal_flows = self._solve_dc_power_flow(breakers_closed)

        for lid, flow in nominal_flows.items():
            # Capacity is threshold * nominal flow, capped at a minimum to avoid zero-flow traps
            self.line_capacities[lid] = max(self.overload_threshold * abs(flow), self.min_capacity)

    def _solve_dc_power_flow(self, breakers: dict) -> dict:
        """
        Solves a linear DC power flow on the grid (supporting islanding).
        Returns a dict of active power flows for each line: {line_id: P_flow}
        """
        num_buses = self.topo.num_buses
        flows = {line["id"]: 0.0 for line in self.topo.lines}

        # 1. Identify connected components (islands)
        components = get_connected_components(self.topo, breakers)

        for comp in components:
            if len(comp) <= 1:
                continue

            # Filter active generators and loads in this island
            comp_gens = [b for b in comp if b in self.topo.generators]
            comp_loads = [b for b in comp if b in self.topo.loads]

            if len(comp_gens) == 0 or len(comp_loads) == 0:
                # No generation or no load in this island, power flow is zero
                continue

            # Calculate total generation capacity and load demand in the island
            p_g_total = sum(self.topo.generators[g]["P_nom"] for g in comp_gens)
            p_d_total = sum(self.topo.loads[d]["P_nom"] for d in comp_loads)

            # Map global indices to local island indices
            comp_indices = sorted(list(comp))
            n_comp = len(comp_indices)
            global_to_local = {g_idx: l_idx for l_idx, g_idx in enumerate(comp_indices)}

            # Balance generation and load in this island
            p_gen = {g: self.topo.generators[g]["P_nom"] for g in comp_gens}
            p_load = {d: self.topo.loads[d]["P_nom"] for d in comp_loads}

            if p_g_total > p_d_total:
                # Surplus: scale down generation proportionally
                scale = p_d_total / p_g_total
                for g in comp_gens:
                    p_gen[g] *= scale
            else:
                # Deficit: scale down load (shed load) proportionally
                scale = p_g_total / p_d_total
                for d in comp_loads:
                    p_load[d] *= scale

            # Compute net active injections for the island
            P_inj_comp = np.zeros(n_comp)
            for g in comp_gens:
                P_inj_comp[global_to_local[g]] += p_gen[g]
            for d in comp_loads:
                P_inj_comp[global_to_local[d]] -= p_load[d]

            # Build B matrix for this island
            B_full = build_b_matrix(self.topo, breakers)
            B_comp = B_full[np.ix_(comp_indices, comp_indices)]

            # Select slack bus (largest generator in this island)
            island_slack = max(comp_gens, key=lambda g: self.topo.generators[g]["P_nom"])
            local_slack = global_to_local[island_slack]

            # Build reduced susceptance matrix B_red
            other_local_buses = [i for i in range(n_comp) if i != local_slack]
            B_red = B_comp[np.ix_(other_local_buses, other_local_buses)]

            # Solve for angles theta_red
            try:
                theta_red = np.linalg.solve(B_red, P_inj_comp[other_local_buses])
            except np.linalg.LinAlgError:
                theta_red = np.linalg.pinv(B_red) @ P_inj_comp[other_local_buses]

            # Expand to full local theta (slack is 0)
            theta_comp = np.zeros(n_comp)
            for idx, local_idx in enumerate(other_local_buses):
                theta_comp[local_idx] = theta_red[idx]

            # Calculate line flows for lines inside this island
            for line in self.topo.lines:
                lid = line["id"]
                f = line["from"]
                t = line["to"]
                x = line["X"]

                if f in comp and t in comp and breakers.get(lid, "CLOSED") == "CLOSED":
                    if abs(x) < 1e-6:
                        x = 1e-6 if x >= 0 else -1e-6
                    f_local = global_to_local[f]
                    t_local = global_to_local[t]
                    flows[lid] = (theta_comp[f_local] - theta_comp[t_local]) / x

        return flows

    def run_cascade(self, initial_tripped_lines: set = None, initial_tripped_buses: set = None) -> dict:
        """
        Simulates the cascading failure process starting from a set of tripped lines or buses.
        Returns:
            dict containing:
                'cascade_size': int (number of lines tripped during the cascade)
                'load_shed': float (total active load shed in MW/100, i.e., in p.u.)
                'unserved_energy': float
                'tripped_lines': list of line ids tripped
                'stages': list of dicts detailing each cascade stage
        """
        if initial_tripped_lines is None:
            initial_tripped_lines = set()
        if initial_tripped_buses is None:
            initial_tripped_buses = set()

        # Copy current breaker states
        breakers = {line["id"]: "CLOSED" for line in self.topo.lines}

        # Apply initial line outages
        for lid in initial_tripped_lines:
            if lid in breakers:
                breakers[lid] = "OPEN"

        # Apply initial bus outages by tripping all lines connected to those buses
        for bus_id in initial_tripped_buses:
            for line in self.topo.lines:
                if line["from"] == bus_id or line["to"] == bus_id:
                    breakers[line["id"]] = "OPEN"

        tripped_lines = set(initial_tripped_lines)
        for lid, state in breakers.items():
            if state == "OPEN":
                tripped_lines.add(lid)

        stages = []
        cascade_ended = False
        step = 0
        max_steps = 50 # Prevent infinite loops

        while not cascade_ended and step < max_steps:
            step += 1

            # 1. Identify connected components (islands)
            components = get_connected_components(self.topo, breakers)

            # 2. Calculate load shed in this step
            current_load_shed = 0.0
            for comp in components:
                comp_gens = [b for b in comp if b in self.topo.generators]
                comp_loads = [b for b in comp if b in self.topo.loads]

                p_g_total = sum(self.topo.generators[g]["P_nom"] for g in comp_gens)
                p_d_total = sum(self.topo.loads[d]["P_nom"] for d in comp_loads)

                if len(comp_gens) == 0:
                    # Blackout in this island: all loads shed
                    current_load_shed += p_d_total
                elif p_g_total < p_d_total:
                    # Generation deficit: load shed is mismatch
                    current_load_shed += (p_d_total - p_g_total)

            # 3. Solve power flow to get line flows
            flows = self._solve_dc_power_flow(breakers)

            # 4. Check for newly overloaded lines
            newly_overloaded = []
            for line in self.topo.lines:
                lid = line["id"]
                if breakers[lid] == "CLOSED":
                    flow_mag = abs(flows[lid])
                    capacity = self.line_capacities[lid]
                    if flow_mag > capacity:
                        newly_overloaded.append(lid)

            # Record stage details
            stages.append({
                "step": step,
                "load_shed": float(current_load_shed),
                "num_islands": len(components),
                "overloaded_lines": newly_overloaded.copy()
            })

            if len(newly_overloaded) > 0:
                # Trip all overloaded lines
                for lid in newly_overloaded:
                    breakers[lid] = "OPEN"
                    tripped_lines.add(lid)
            else:
                # No more overloads, cascade stops
                cascade_ended = True

        # Final metrics
        final_load_shed = stages[-1]["load_shed"]
        # Unserved energy proxy: load shed * nominal grid frequency time unit (say 1.0 hr)
        unserved_energy = final_load_shed * 1.0

        # Cascade size is lines tripped excluding initial tripped lines/bus connections
        initial_outages_count = len(initial_tripped_lines)
        # Count how many lines were opened by bus outages
        bus_outage_lines = set()
        for bus_id in initial_tripped_buses:
            for line in self.topo.lines:
                if line["from"] == bus_id or line["to"] == bus_id:
                    bus_outage_lines.add(line["id"])
        total_initial = len(initial_tripped_lines.union(bus_outage_lines))

        cascade_size = max(0, len(tripped_lines) - total_initial)

        return {
            "cascade_size": int(cascade_size),
            "load_shed": float(final_load_shed),
            "unserved_energy": float(unserved_energy),
            "tripped_lines": list(tripped_lines),
            "stages": stages
        }
