import numpy as np
import networkx as nx
from core.digital_twin.grid_topology import GridTopology
from core.analytics.ptdf_engine import PtdfEngine, get_connected_components

class ExtendedBetweennessEngine:
    def __init__(self, topo: GridTopology):
        self.topo = topo
        self.ptdf_engine = PtdfEngine(topo)

    def calculate_classical_betweenness(self, breakers: dict = None) -> tuple:
        """
        Computes the topological Classical Betweenness Centrality for all buses and lines.
        Returns:
            bus_cbc: dict mapping bus_id (0-38) -> float
            line_cbc: dict mapping line_id (e.g. 'L_line_0') -> float
        """
        if breakers is None:
            breakers = {line["id"]: "CLOSED" for line in self.topo.lines}

        # Build NetworkX Graph
        G = nx.Graph()
        G.add_nodes_from(range(self.topo.num_buses))

        line_map = {} # Maps (u, v) -> line_id
        for line in self.topo.lines:
            lid = line["id"]
            if breakers.get(lid, "CLOSED") == "CLOSED":
                u, v = line["from"], line["to"]
                G.add_edge(u, v)
                line_map[(u, v)] = lid
                line_map[(v, u)] = lid

        # Calculate centrality
        node_bc = nx.betweenness_centrality(G, normalized=True)
        edge_bc = nx.edge_betweenness_centrality(G, normalized=True)

        bus_cbc = {i: float(node_bc.get(i, 0.0)) for i in range(self.topo.num_buses)}

        line_cbc = {}
        for line in self.topo.lines:
            lid = line["id"]
            u, v = line["from"], line["to"]
            val = edge_bc.get((u, v), edge_bc.get((v, u), 0.0))
            line_cbc[lid] = float(val)

        return bus_cbc, line_cbc

    def calculate_electrical_betweenness(self, breakers: dict = None) -> tuple:
        """
        Computes the physics-aware Electrical Betweenness Centrality (EBC) for all buses and lines.
        EBC(l) = sum_{g in G, d in D} P_G(g) * P_D(d) * |PTDF_{l, g-d}|
        EBC(v) = 0.5 * sum_{l in adj(v)} EBC(l)
        Returns:
            bus_ebc: dict mapping bus_id (0-38) -> float
            line_ebc: dict mapping line_id -> float
        """
        if breakers is None:
            breakers = {line["id"]: "CLOSED" for line in self.topo.lines}

        # 1. Compute PTDF matrix
        ptdf_matrix = self.ptdf_engine.calculate_ptdf_matrix(breakers)

        # 2. Identify generator and load buses
        gens = list(self.topo.generators.keys())
        loads = list(self.topo.loads.keys())

        num_lines = len(self.topo.lines)
        line_ebc_arr = np.zeros(num_lines)

        # Determine connected components
        components = get_connected_components(self.topo, breakers)

        for g in gens:
            p_g = self.topo.generators[g]["P_nom"]
            g_island = next((comp for comp in components if g in comp), None)
            if g_island is None:
                continue

            for d in loads:
                if d not in g_island:
                    # Generator and load are in different islands, cannot exchange power
                    continue

                p_d = self.topo.loads[d]["P_nom"]
                # Power flow sensitivity for this transaction
                ptdf_trans = np.abs(ptdf_matrix[:, g] - ptdf_matrix[:, d])
                # Accumulate weighted sensitivity
                line_ebc_arr += p_g * p_d * ptdf_trans

        # Build line results dict
        line_ebc = {}
        for l_idx, line in enumerate(self.topo.lines):
            line_ebc[line["id"]] = float(line_ebc_arr[l_idx])

        # Calculate bus centrality as half sum of connected line EBCs
        bus_ebc = {i: 0.0 for i in range(self.topo.num_buses)}
        for line in self.topo.lines:
            lid = line["id"]
            u, v = line["from"], line["to"]
            val = line_ebc[lid]
            bus_ebc[u] += val
            bus_ebc[v] += val

        for i in range(self.topo.num_buses):
            bus_ebc[i] = float(bus_ebc[i] * 0.5)

        return bus_ebc, line_ebc

    def calculate_extended_betweenness(self, breakers: dict = None) -> tuple:
        """
        Computes Bompard's Extended Betweenness Centrality (ExBC) for all buses and lines.
        ExBC(l) = sum_{g in G, d in D} min(P_G(g), P_D(d)) * |PTDF_{l, g-d}|
        ExBC(v) = 0.5 * sum_{l in adj(v)} ExBC(l)
        Returns:
            bus_exbc: dict mapping bus_id (0-38) -> float
            line_exbc: dict mapping line_id -> float
        """
        if breakers is None:
            breakers = {line["id"]: "CLOSED" for line in self.topo.lines}

        # 1. Compute PTDF matrix
        ptdf_matrix = self.ptdf_engine.calculate_ptdf_matrix(breakers)

        # 2. Identify generator and load buses
        gens = list(self.topo.generators.keys())
        loads = list(self.topo.loads.keys())

        num_lines = len(self.topo.lines)
        line_exbc_arr = np.zeros(num_lines)

        # Determine connected components
        components = get_connected_components(self.topo, breakers)

        for g in gens:
            p_g = self.topo.generators[g]["P_nom"]
            g_island = next((comp for comp in components if g in comp), None)
            if g_island is None:
                continue

            for d in loads:
                if d not in g_island:
                    continue

                p_d = self.topo.loads[d]["P_nom"]
                ptdf_trans = np.abs(ptdf_matrix[:, g] - ptdf_matrix[:, d])
                # Optimized Extended Betweenness uses PG * PD to scale with generator capacity
                p_trans = p_g * p_d
                line_exbc_arr += p_trans * ptdf_trans

        # Build line results dict
        line_exbc = {}
        for l_idx, line in enumerate(self.topo.lines):
            line_exbc[line["id"]] = float(line_exbc_arr[l_idx])

        # Calculate bus centrality
        bus_exbc = {i: 0.0 for i in range(self.topo.num_buses)}
        for line in self.topo.lines:
            lid = line["id"]
            u, v = line["from"], line["to"]
            val = line_exbc[lid]
            bus_exbc[u] += val
            bus_exbc[v] += val

        for i in range(self.topo.num_buses):
            bus_exbc[i] = float(bus_exbc[i] * 0.5)

        return bus_exbc, line_exbc
