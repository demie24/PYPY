import os
import sys
import logging
from typing import Dict, Any, List, Set, Tuple

# Setup import paths
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(CURRENT_DIR)

from core.self_healing.topology_recovery_engine import TopologyRecoveryEngine

logger = logging.getLogger("self_healing.cascading_containment_engine")

class CascadingContainmentEngine:
    """
    Predicts propagation paths for line overloads and cyber-attack instability.
    Recommends optimal breaker isolation boundaries to quarantine deviations and prevent cascade.
    """
    def __init__(self, topology_engine=None):
        self.topo_engine = topology_engine if topology_engine else TopologyRecoveryEngine()
        
    def analyze_cascading_risk(self, telemetry: Dict[str, Any], attack_status: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Analyzes line loadings, calculates a cascading risk score, and recommends preemptive
        breaker trips or isolation boundaries.
        """
        if not telemetry:
            return {
                "propagation_zones": [],
                "instability_spread_risk": 0.0,
                "isolation_boundary": [],
                "cascading_risk_score": 0.0,
                "stabilization_first_required": False,
                "preemptive_trips": []
            }

        state = telemetry.get("state", {})
        breakers = state.get("breakers", {})
        lines = state.get("lines", {})
        buses = state.get("buses", {})

        # 1. Identify overloaded lines (> 85% loading)
        overloaded_lines = []
        for lid, l_data in lines.items():
            loading = l_data.get("capacity_pct", 0.0)
            if loading > 85.0:
                overloaded_lines.append((lid, loading))

        # Sort overloaded lines by loading descending
        overloaded_lines.sort(key=lambda x: x[1], reverse=True)

        propagation_zones = set()
        instability_spread_risk = 0.0

        # Build current graph state
        graph = self.topo_engine.get_grid_graph(breakers)

        # 2. For each overloaded line, find alternative routing paths (propagation zones)
        for lid, loading in overloaded_lines:
            line_data = next((l for l in self.topo_engine.topo.lines if l["id"] == lid), None)
            if not line_data:
                continue
            u, v = line_data["from"], line_data["to"]

            # Temp remove overloaded line from graph to find alternate paths
            alt_graph = {node: [edge for edge in edges if edge[1] != lid] for node, edges in graph.items()}
            alt_paths = self._find_all_paths(alt_graph, u, v, max_depth=4)
            
            for path in alt_paths:
                for edge_lid in path:
                    propagation_zones.add(edge_lid)

        # Estimate instability spread risk
        max_zone_load = 0.0
        if propagation_zones:
            zone_loadings = []
            for p_lid in propagation_zones:
                l_pct = lines.get(p_lid, {}).get("capacity_pct", 0.0)
                zone_loadings.append(l_pct)
            
            max_zone_load = max(zone_loadings) if zone_loadings else 0.0
            instability_spread_risk = max(0.0, min(1.0, (max_zone_load - 50.0) / 60.0))
        elif overloaded_lines:
            instability_spread_risk = 0.5

        # 3. Compute Cascading Risk Score (0.0 to 1.0)
        # Scales with the number of overloaded lines, the severity of maximum overload, and spread risk
        overload_severity = 0.0
        if overloaded_lines:
            max_overload = overloaded_lines[0][1] # highest loading
            overload_severity = max(0.0, (max_overload - 85.0) / 40.0)  # 85% is 0, 125% is 1.0

        cascading_risk_score = 0.4 * overload_severity + 0.3 * instability_spread_risk + 0.3 * (len(overloaded_lines) / 9.0)
        cascading_risk_score = max(0.0, min(1.0, cascading_risk_score))

        # 4. Stabilization-First Gating Rule
        # Enforce stabilization-first if cascading risk is high or voltages are collapsing
        stabilization_first_required = cascading_risk_score > 0.50 or any(
            b.get("voltage_pu", 1.0) < 0.90 and b.get("voltage_pu", 1.0) > 0.05 for b in buses.values()
        )

        # 5. Preemptive Breaker Actions & Isolation Boundaries
        isolation_boundary = set()
        preemptive_trips = []

        compromised_nodes = set()
        if attack_status:
            compromised_nodes = set(attack_status.get("compromised_nodes", {}).keys())

        # Check telemetry buses for voltage collapses or compromised flags
        for bus_name, b_data in buses.items():
            v_pu = b_data.get("voltage_pu", 1.0)
            is_compromised = bus_name in compromised_nodes
            
            # If bus is compromised or collapsed
            if is_compromised or (v_pu < 0.85 and v_pu > 0.05):
                bus_idx = int(bus_name.replace("Bus_", "")) - 1
                for line in self.topo_engine.topo.lines:
                    if line["from"] == bus_idx or line["to"] == bus_idx:
                        if breakers.get(line["id"], "CLOSED") == "CLOSED":
                            isolation_boundary.add(line["id"])

        # Also add severely overloaded lines directly to the boundary
        for lid, loading in overloaded_lines:
            if loading > 105.0:
                isolation_boundary.add(lid)
                
                # Preemptive trip recommendation if overload is critical (>108%) to prevent damage and cascade
                if loading > 108.0:
                    # Check if this line is connected to critical Bus_5 (hospital) terminal
                    line_data = next((l for l in self.topo_engine.topo.lines if l["id"] == lid), None)
                    if line_data and (line_data["from"] == 4 or line_data["to"] == 4): # Bus 5 index is 4
                        # Hospital line overload: we trip to prevent physical fires, but log warnings
                        logger.warning(f"[PREEMPTIVE CONTAINMENT] Recommending preemptive trip on line {lid} feeding critical Bus 5 due to overloading.")
                    
                    preemptive_trips.append({
                        "command": "OPEN",
                        "target": lid,
                        "reason": f"Preemptive trip to prevent cascading line collapse on {lid} (loading: {loading:.1f}%)"
                    })

        return {
            "propagation_zones": list(propagation_zones),
            "instability_spread_risk": float(round(instability_spread_risk, 3)),
            "isolation_boundary": list(isolation_boundary),
            "cascading_risk_score": float(round(cascading_risk_score, 3)),
            "stabilization_first_required": stabilization_first_required,
            "preemptive_trips": preemptive_trips
        }

    def _find_all_paths(self, graph: Dict[int, List[Tuple[int, str]]], start: int, end: int, max_depth: int = 4) -> List[List[str]]:
        """
        BFS-based path finder returning list of paths (each path is a list of line IDs).
        """
        paths = []
        queue = [(start, [], set([start]))]  # (curr_node, path_lines, visited_nodes)

        while queue:
            node, path, visited = queue.pop(0)

            if len(path) > max_depth:
                continue

            if node == end:
                if path:
                    paths.append(path)
                continue

            for neighbor, lid in graph.get(node, []):
                if neighbor not in visited:
                    new_visited = visited.copy()
                    new_visited.add(neighbor)
                    queue.append((neighbor, path + [lid], new_visited))

        return paths
