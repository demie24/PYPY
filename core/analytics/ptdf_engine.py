import numpy as np
from core.digital_twin.grid_topology import GridTopology

def build_b_matrix(topo: GridTopology, breakers: dict = None) -> np.ndarray:
    """
    Builds the nodal susceptance (B) matrix for the grid.
    """
    if breakers is None:
        breakers = {line["id"]: "CLOSED" for line in topo.lines}

    num_buses = topo.num_buses
    B = np.zeros((num_buses, num_buses))

    for line in topo.lines:
        lid = line["id"]
        if breakers.get(lid, "CLOSED") != "CLOSED":
            continue

        f = line["from"]
        t = line["to"]
        x = line["X"]

        # Add epsilon to prevent division-by-zero
        if abs(x) < 1e-6:
            x = 1e-6 if x >= 0 else -1e-6

        b = 1.0 / x
        B[f, f] += b
        B[t, t] += b
        B[f, t] -= b
        B[t, f] -= b

    return B

def get_connected_components(topo: GridTopology, breakers: dict = None) -> list:
    """
    Finds the connected components (islands) in the grid using BFS.
    """
    if breakers is None:
        breakers = {line["id"]: "CLOSED" for line in topo.lines}

    num_buses = topo.num_buses
    visited = set()
    components = []

    adj = {i: [] for i in range(num_buses)}
    for line in topo.lines:
        f, t, lid = line["from"], line["to"], line["id"]
        if breakers.get(lid, "CLOSED") == "CLOSED":
            adj[f].append(t)
            adj[t].append(f)

    for i in range(num_buses):
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

def compute_ptdf(topo: GridTopology, breakers: dict = None, slack_bus: int = 30) -> np.ndarray:
    """
    Computes the Power Transfer Distribution Factors (PTDF) matrix of shape (num_lines, num_buses).
    Utilizes linear DC load flow approximation.
    """
    if breakers is None:
        breakers = {line["id"]: "CLOSED" for line in topo.lines}

    num_buses = topo.num_buses
    num_lines = len(topo.lines)

    # Initialize full PTDF matrix
    PTDF = np.zeros((num_lines, num_buses))

    # Get connected components (islands)
    components = get_connected_components(topo, breakers)

    # We solve PTDF for each island separately to handle disconnected systems properly
    for comp in components:
        if len(comp) <= 1:
            # Isolated node has no flows
            continue

        # Select an island-specific slack bus
        # If the global slack_bus is in the island, use it; otherwise use the first generator in the island,
        # or simply the first bus in the island.
        island_gens = [b for b in comp if b in topo.generators]
        island_slack = slack_bus if slack_bus in comp else (island_gens[0] if len(island_gens) > 0 else comp[0])

        # Build susceptance matrix for this island
        comp_indices = sorted(list(comp))
        n_comp = len(comp_indices)

        # Map global bus indices to local island indices
        global_to_local = {g_idx: l_idx for l_idx, g_idx in enumerate(comp_indices)}
        local_to_global = {l_idx: g_idx for l_idx, g_idx in enumerate(comp_indices)}

        # Extract sub-matrix B_comp
        B_full = build_b_matrix(topo, breakers)
        B_comp = B_full[np.ix_(comp_indices, comp_indices)]

        # Remove island slack bus to get reduced B
        local_slack = global_to_local[island_slack]
        other_local_buses = [i for i in range(n_comp) if i != local_slack]

        B_red = B_comp[np.ix_(other_local_buses, other_buses := other_local_buses)]

        try:
            X_red = np.linalg.inv(B_red)
        except np.linalg.LinAlgError:
            X_red = np.linalg.pinv(B_red)

        X_comp = np.zeros((n_comp, n_comp))
        X_comp[np.ix_(other_local_buses, other_local_buses)] = X_red

        # Map local X back to global dimensions for this island
        X_global = np.zeros((num_buses, num_buses))
        for r_idx in range(n_comp):
            for c_idx in range(n_comp):
                X_global[local_to_global[r_idx], local_to_global[c_idx]] = X_comp[r_idx, c_idx]

        # Calculate PTDF values for lines in this island
        for l_idx, line in enumerate(topo.lines):
            f = line["from"]
            t = line["to"]
            x = line["X"]

            # Line must connect buses inside this component and be closed
            if f in comp and t in comp and breakers.get(line["id"], "CLOSED") == "CLOSED":
                if abs(x) < 1e-6:
                    x = 1e-6 if x >= 0 else -1e-6
                for n in comp:
                    PTDF[l_idx, n] = (X_global[f, n] - X_global[t, n]) / x

    return PTDF

class PtdfEngine:
    def __init__(self, topo: GridTopology):
        self.topo = topo

    def calculate_ptdf_matrix(self, breakers: dict = None, slack_bus: int = 30) -> np.ndarray:
        return compute_ptdf(self.topo, breakers, slack_bus)

    def calculate_transaction_ptdf(self, source_bus: int, sink_bus: int, breakers: dict = None, slack_bus: int = 30) -> np.ndarray:
        """
        Computes PTDF vector for a transaction between source and sink buses.
        Returns a vector of length num_lines.
        """
        ptdf_matrix = self.calculate_ptdf_matrix(breakers, slack_bus)

        # Check connectivity
        components = get_connected_components(self.topo, breakers)
        source_island = next((comp for comp in components if source_bus in comp), None)

        if source_island is None or sink_bus not in source_island:
            # Disconnected, no flow possible
            return np.zeros(len(self.topo.lines))

        return ptdf_matrix[:, source_bus] - ptdf_matrix[:, sink_bus]
