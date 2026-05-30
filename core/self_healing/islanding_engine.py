import os
import sys
import logging
from typing import Dict, Any, List, Set, Tuple

# Setup import paths
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from core.self_healing.topology_recovery_engine import TopologyRecoveryEngine

logger = logging.getLogger("self_healing.islanding_engine")

class IslandingEngine:
    """
    Detects unstable regions and splits the grid into electrical islands to isolate compromised
    or collapsing segments, preserving healthy zones.
    """
    def __init__(self, topology_engine=None):
        self.topo_engine = topology_engine if topology_engine else TopologyRecoveryEngine()

    def analyze_islanding(self, telemetry: Dict[str, Any], attack_status: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Scans telemetry for voltage collapses and cyber attacks.
        Returns active islands, health classifications, and recommended islanding breaker openings.
        """
        if not telemetry:
            return {
                "active_islands": [],
                "unstable_zones": [],
                "healthy_zones": [],
                "splitting_commands": []
            }

        state = telemetry.get("state", {})
        breakers = state.get("breakers", {})
        buses = state.get("buses", {})
        lines = state.get("lines", {})

        # Build current graph state
        graph = self.topo_engine.get_grid_graph(breakers)
        components = self.topo_engine.get_connected_components(graph)

        active_islands = []
        unstable_zones = []
        healthy_zones = []
        splitting_commands = []

        compromised_nodes = set()
        if attack_status:
            compromised_nodes = set(attack_status.get("compromised_nodes", {}).keys())

        # Classify each connected component (island)
        for idx, comp in enumerate(components):
            # Check if this component has online generators
            generators_in_comp = [b_idx for b_idx in comp if b_idx in self.topo_engine.topo.generators]
            loads_in_comp = [b_idx for b_idx in comp if b_idx in self.topo_engine.topo.loads]

            has_gen = len(generators_in_comp) > 0
            
            # Determine component health: check for undervoltage (< 0.85) or compromise flags
            is_unstable = False
            unstable_reasons = []
            
            for b_idx in comp:
                bus_name = f"Bus_{b_idx + 1}"
                bus_data = buses.get(bus_name, {})
                v = bus_data.get("voltage_pu", 1.0)
                
                # Check for voltage collapse or spoofed/distrusted flags
                if v < 0.85:
                    is_unstable = True
                    unstable_reasons.append(f"{bus_name} voltage collapse ({v:.2f} p.u.)")
                elif v > 1.15:
                    is_unstable = True
                    unstable_reasons.append(f"{bus_name} overvoltage ({v:.2f} p.u.)")
                
                if bus_name in compromised_nodes:
                    is_unstable = True
                    unstable_reasons.append(f"{bus_name} cyber-compromised")

            # Check if any line in component is severely overloaded (> 110%)
            for line in self.topo_engine.topo.lines:
                lid = line["id"]
                if breakers.get(lid, "CLOSED") == "CLOSED" and line["from"] in comp and line["to"] in comp:
                    loading = lines.get(lid, {}).get("capacity_pct", 0.0)
                    if loading > 110.0:
                        is_unstable = True
                        unstable_reasons.append(f"{lid} severely overloaded ({loading:.1f}%)")

            # Map index to bus label lists
            bus_labels = [f"Bus_{i + 1}" for i in comp]
            gen_labels = [f"Bus_{i + 1}" for i in generators_in_comp]
            load_labels = [f"Bus_{i + 1}" for i in loads_in_comp]

            island_info = {
                "island_id": f"ISLAND_{idx + 1}",
                "buses": bus_labels,
                "generators": gen_labels,
                "loads": load_labels,
                "has_generation": has_gen,
                "is_unstable": is_unstable,
                "reasons": unstable_reasons
            }
            active_islands.append(island_info)

            if is_unstable:
                unstable_zones.append(island_info)
                # If this unstable island connects to healthy islands, recommend boundary splits.
                # Find lines that bridge this component to another component, but wait,
                # since they are already separate connected components in the graph, there are no closed lines between them.
                # However, if we have a larger single connected component containing both healthy and unstable nodes,
                # we want to split *it* beforehand.
                # Let's perform a node-level check. If a single connected component contains both healthy nodes
                # (voltages in [0.90, 1.10]) and highly unstable/compromised nodes, we propose opening the lines
                # connected directly to the unstable nodes to isolate them.
                for b_idx in comp:
                    bus_name = f"Bus_{b_idx + 1}"
                    # If this specific node is unstable/compromised, isolate it by opening connected closed lines
                    if bus_name in compromised_nodes or buses.get(bus_name, {}).get("voltage_pu", 1.0) < 0.85:
                        for line in self.topo_engine.topo.lines:
                            if line["from"] == b_idx or line["to"] == b_idx:
                                if breakers.get(line["id"], "CLOSED") == "CLOSED":
                                    splitting_commands.append({
                                        "command": "OPEN",
                                        "target": line["id"],
                                        "reason": f"Grid Splitting: Isolate unstable node {bus_name}"
                                    })
            else:
                healthy_zones.append(island_info)

        return {
            "active_islands": active_islands,
            "unstable_zones": unstable_zones,
            "healthy_zones": healthy_zones,
            "splitting_commands": splitting_commands
        }
