import os
import sys
import logging
from typing import Dict, List, Set, Any, Tuple

# Setup import paths
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(CURRENT_DIR)
sys.path.append(os.path.abspath(os.path.join(CURRENT_DIR, "..", "digital_twin")))

try:
    from grid_topology import GridTopology
except ImportError:
    # Standalone mock fallback matching digital_twin signature
    class GridTopology:
        def __init__(self):
            self.num_buses = 9
            self.slack_bus = 0
            self.lines = [
                {"id": "L1_4", "from": 0, "to": 3, "X": 0.0576},
                {"id": "L2_7", "from": 1, "to": 6, "X": 0.0625},
                {"id": "L3_9", "from": 2, "to": 8, "X": 0.0586},
                {"id": "L4_5", "from": 3, "to": 4, "X": 0.085},
                {"id": "L4_9", "from": 3, "to": 8, "X": 0.092},
                {"id": "L5_6", "from": 4, "to": 5, "X": 0.161},
                {"id": "L6_7", "from": 5, "to": 6, "X": 0.072},
                {"id": "L7_8", "from": 6, "to": 7, "X": 0.161},
                {"id": "L8_9", "from": 7, "to": 8, "X": 0.1008}
            ]
            self.generators = {
                0: {"P_nom": 72.0, "Q_nom": 27.0},
                1: {"P_nom": 163.0, "Q_nom": 6.0},
                2: {"P_nom": 85.0, "Q_nom": -10.0}
            }
            self.loads = {
                4: {"P_nom": 125.0, "Q_nom": 50.0},
                5: {"P_nom": 90.0, "Q_nom": 30.0},
                7: {"P_nom": 100.0, "Q_nom": 35.0}
            }

logger = logging.getLogger("self_healing.topology_recovery_engine")

class TopologyRecoveryEngine:
    """
    Analyzes smart grid connectivity to construct a topological graph, identify
    de-energized/isolated load islands, and suggest alternative rerouting lines.
    """
    def __init__(self, topology=None):
        self.topo = topology if topology else GridTopology()
        
    def get_grid_graph(self, breakers: Dict[str, str]) -> Dict[int, List[Tuple[int, str]]]:
        """
        Builds adjacency list of grid buses: bus_idx -> list of (neighbor_bus_idx, line_id).
        A line is considered connected only if its breaker status is "CLOSED".
        """
        graph = {i: [] for i in range(self.topo.num_buses)}
        for line in self.topo.lines:
            lid = line["id"]
            if breakers.get(lid, "CLOSED") == "CLOSED":
                u, v = line["from"], line["to"]
                graph[u].append((v, lid))
                graph[v].append((u, lid))
        return graph

    def get_connected_components(self, graph: Dict[int, List[Tuple[int, str]]]) -> List[List[int]]:
        """
        Calculates connected components (islands) of buses in the current grid state using BFS.
        """
        visited = set()
        components = []
        for i in range(self.topo.num_buses):
            if i not in visited:
                comp = []
                queue = [i]
                visited.add(i)
                while queue:
                    curr = queue.pop(0)
                    comp.append(curr)
                    for neighbor, _ in graph[curr]:
                        if neighbor not in visited:
                            visited.add(neighbor)
                            queue.append(neighbor)
                components.append(comp)
        return components

    def analyze_topology(self, telemetry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Identifies active generator components, isolated segments, and rerouting alternatives.
        """
        state = telemetry.get("state", {})
        breakers = state.get("breakers", {})
        buses = state.get("buses", {})
        
        # Build current graph state
        graph = self.get_grid_graph(breakers)
        components = self.get_connected_components(graph)
        
        # Active generators defined as generators on buses with voltage > 0.8 p.u.
        active_gens = []
        for g_idx in self.topo.generators.keys():
            bus_name = f"Bus_{g_idx + 1}"
            voltage = buses.get(bus_name, {}).get("voltage_pu", 0.0)
            # Default to nominal if buses data isn't fully filled (e.g. mock telemetry)
            if buses and bus_name in buses:
                if voltage > 0.8:
                    active_gens.append(g_idx)
            else:
                # Fallback to nominal configuration if no telemetry values exist yet
                active_gens.append(g_idx)
                
        isolated_segments = []
        healthy_connected_to_gen = []
        
        for comp in components:
            has_active_gen = any(bus in active_gens for bus in comp)
            if not has_active_gen:
                # This component does not connect to any active generator bus
                isolated_segments.append(comp)
            else:
                healthy_connected_to_gen.extend(comp)
                
        # Find candidate alternate paths (open breakers that bridge isolated segments to energized zones)
        reroute_options = []
        open_breakers = [lid for lid, status in breakers.items() if status == "OPEN"]
        
        for lid in open_breakers:
            line = next((l for l in self.topo.lines if l["id"] == lid), None)
            if not line:
                continue
            u, v = line["from"], line["to"]
            
            u_in_gen = u in healthy_connected_to_gen
            v_in_gen = v in healthy_connected_to_gen
            
            is_u_isolated = any(u in seg for seg in isolated_segments)
            is_v_isolated = any(v in seg for seg in isolated_segments)
            
            # Closing lid connects an isolated segment to an energized component
            if (u_in_gen and is_v_isolated) or (v_in_gen and is_u_isolated):
                target_segment = next((seg for seg in isolated_segments if (u in seg or v in seg)), [])
                reroute_options.append({
                    "line_id": lid,
                    "connects_from": u,
                    "connects_to": v,
                    "isolated_segment": target_segment
                })
                
        return {
            "components": components,
            "isolated_segments": isolated_segments,
            "active_generators": active_gens,
            "reroute_options": reroute_options
        }
