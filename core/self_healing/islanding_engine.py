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
    Detects unstable regions and statefully isolates compromised or collapsing segments,
    establishing electrical islands while preserving critical infrastructure (e.g. Bus_5 hospital).
    """
    def __init__(self, topology_engine=None):
        self.topo_engine = topology_engine if topology_engine else TopologyRecoveryEngine()

    def analyze_islanding(self, telemetry: Dict[str, Any], attack_status: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Scans telemetry for voltage collapse, imbalances, and cyber attacks.
        Returns:
            - active_islands: list of detailed island metadata (including generation-load balances and survival modes).
            - unstable_zones: list of unstable islands.
            - healthy_zones: list of healthy islands.
            - splitting_commands: breaker open commands to isolate faults.
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
            generators_in_comp = [b_idx for b_idx in comp if b_idx in self.topo_engine.topo.generators]
            loads_in_comp = [b_idx for b_idx in comp if b_idx in self.topo_engine.topo.loads]
            has_gen = len(generators_in_comp) > 0

            # Calculate Active Generation vs Active Load inside this island
            comp_generation = 0.0
            comp_load = 0.0

            for b_idx in generators_in_comp:
                bus_name = f"Bus_{b_idx + 1}"
                bus_data = buses.get(bus_name, {})
                comp_generation += bus_data.get("P_mw", self.topo_engine.topo.generators[b_idx]["P_nom"])

            for b_idx in loads_in_comp:
                bus_name = f"Bus_{b_idx + 1}"
                bus_data = buses.get(bus_name, {})
                comp_load += bus_data.get("P_mw", self.topo_engine.topo.loads[b_idx]["P_nom"])

            is_deficient = has_gen and (comp_load > comp_generation)
            balance_ratio = (comp_generation / comp_load) if comp_load > 0 else 1.0

            # Determine component health: check for voltage collapse (< 0.85) or compromise flags
            is_unstable = False
            unstable_reasons = []

            for b_idx in comp:
                bus_name = f"Bus_{b_idx + 1}"
                bus_data = buses.get(bus_name, {})
                v = bus_data.get("voltage_pu", 1.0)

                # Check for voltage collapse or extreme overvoltage
                if v < 0.85 and v > 0.05:
                    is_unstable = True
                    unstable_reasons.append(f"{bus_name} voltage collapse ({v:.2f} p.u.)")
                elif v > 1.15:
                    is_unstable = True
                    unstable_reasons.append(f"{bus_name} overvoltage ({v:.2f} p.u.)")

                if bus_name in compromised_nodes:
                    is_unstable = True
                    unstable_reasons.append(f"{bus_name} cyber-compromised")

            # Check line overloads in component
            for line in self.topo_engine.topo.lines:
                lid = line["id"]
                if breakers.get(lid, "CLOSED") == "CLOSED" and line["from"] in comp and line["to"] in comp:
                    loading = lines.get(lid, {}).get("capacity_pct", 0.0)
                    if loading > 110.0:
                        is_unstable = True
                        unstable_reasons.append(f"{lid} severely overloaded ({loading:.1f}%)")

            # Identify critical buses in this island
            bus_labels = [f"Bus_{i + 1}" for i in comp]
            gen_labels = [f"Bus_{i + 1}" for i in generators_in_comp]
            load_labels = [f"Bus_{i + 1}" for i in loads_in_comp]

            # Define survival mode strategies (Critical infrastructure aware)
            if "Bus_5" in bus_labels:
                survival_mode = "SURVIVAL_CRITICAL"  # Primary control/hospital priority
            elif "Bus_8" in bus_labels:
                survival_mode = "DEGRADED_SURVIVAL"  # Heavy industry priority
            elif has_gen:
                survival_mode = "NOMINAL_ISLAND"
            else:
                survival_mode = "BLACKOUT"

            island_info = {
                "island_id": f"ISLAND_{idx + 1}",
                "buses": bus_labels,
                "generators": gen_labels,
                "loads": load_labels,
                "has_generation": has_gen,
                "generation_mw": comp_generation,
                "load_mw": comp_load,
                "is_deficient": is_deficient,
                "balance_ratio": round(balance_ratio, 2),
                "is_unstable": is_unstable,
                "reasons": unstable_reasons,
                "survival_mode": survival_mode
            }
            active_islands.append(island_info)

            # Adaptive boundary decision making
            if is_unstable:
                unstable_zones.append(island_info)
                # Propose boundary cuts to isolate unstable nodes
                for b_idx in comp:
                    bus_name = f"Bus_{b_idx + 1}"
                    v_pu = buses.get(bus_name, {}).get("voltage_pu", 1.0)
                    
                    # If this node is compromised or collapsed
                    if bus_name in compromised_nodes or (v_pu < 0.85 and v_pu > 0.05):
                        # Find all closed breakers connected to this node
                        for line in self.topo_engine.topo.lines:
                            if line["from"] == b_idx or line["to"] == b_idx:
                                lid = line["id"]
                                if breakers.get(lid, "CLOSED") == "CLOSED":
                                    # Verify that opening this breaker does not isolate Bus_5 from Gen_1/Gen_2/Gen_3
                                    # (Only run this safeguard when we are isolating nodes other than Bus_5 itself)
                                    if bus_name != "Bus_5":
                                        temp_breakers = breakers.copy()
                                        temp_breakers[lid] = "OPEN"
                                        temp_graph = self.topo_engine.get_grid_graph(temp_breakers)
                                        temp_comps = self.topo_engine.get_connected_components(temp_graph)
                                        
                                        bus5_comp = next((c for c in temp_comps if 4 in c), None) # Bus 5 index is 4
                                        if bus5_comp:
                                            has_gen_for_bus5 = any(g in bus5_comp for g in self.topo_engine.topo.generators)
                                            if not has_gen_for_bus5:
                                                logger.warning(
                                                    f"[ISLANDING PRESERVATION] Suppressing split command on {lid} "
                                                    f"to keep Bus_5 connected to a generator."
                                                )
                                                continue

                                    splitting_commands.append({
                                        "command": "OPEN",
                                        "target": lid,
                                        "reason": f"Grid Splitting: Adaptive boundary isolation of unstable {bus_name}"
                                    })
            else:
                healthy_zones.append(island_info)

        return {
            "active_islands": active_islands,
            "unstable_zones": unstable_zones,
            "healthy_zones": healthy_zones,
            "splitting_commands": splitting_commands
        }
