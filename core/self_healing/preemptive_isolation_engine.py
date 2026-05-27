import os
import sys
import logging
from typing import Dict, Any, List, Set

# Setup import paths
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from topology_recovery_engine import TopologyRecoveryEngine

logger = logging.getLogger("self_healing.preemptive_isolation")

class PreemptiveIsolationEngine:
    """
    Identifies high-risk buses or lines and performs predictive isolation before failure
    to protect critical infrastructure, while estimating isolation side effects.
    """
    def __init__(self, topology_engine=None):
        self.topo_engine = topology_engine if topology_engine else TopologyRecoveryEngine()

    def analyze_isolation(self, telemetry: Dict[str, Any], predictive_stability: Dict[str, Any], attack_status: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Scans telemetry for high-risk elements (e.g. voltage decay, heavy overloads, cyber compromise)
        and proposes pre-emptive isolation commands.
        """
        if not telemetry:
            return {
                "preemptive_isolation_active": False,
                "recommended_isolation": [],
                "side_effects": {}
            }

        state = telemetry.get("state", {})
        breakers = state.get("breakers", {})
        buses = state.get("buses", {})
        lines = state.get("lines", {})

        compromised_nodes = set()
        if attack_status:
            compromised_nodes = set(attack_status.get("compromised_nodes", {}).keys())

        high_risk_elements = []

        # 1. Identify high-risk buses from voltage decay and compromise
        for bus_name, bus_data in buses.items():
            v = bus_data.get("voltage_pu", 1.0)
            is_compromised = bus_name in compromised_nodes
            
            # If bus voltage is collapsing (<0.88 p.u.) or under active cyber attack
            if (v < 0.88 and v > 0.0) or is_compromised:
                high_risk_elements.append({
                    "type": "BUS",
                    "id": bus_name,
                    "reason": f"Active compromise" if is_compromised else f"Voltage collapse ({v:.2f} p.u.)"
                })

        # 2. Identify high-risk lines from overload
        for line_id, line_data in lines.items():
            cap = line_data.get("capacity_pct", 0.0)
            if cap > 100.0:
                high_risk_elements.append({
                    "type": "LINE",
                    "id": line_id,
                    "reason": f"Extreme loading ({cap:.1f}%)"
                })

        recommended_isolation = []
        side_effects = {}

        # 3. Formulate isolation commands (opening breakers surrounding high-risk elements)
        for element in high_risk_elements:
            elem_id = element["id"]
            elem_type = element["type"]
            reason = element["reason"]

            candidate_breakers = []
            if elem_type == "BUS":
                bus_idx = int(elem_id.replace("Bus_", "")) - 1
                # Find lines connected to this bus that are currently CLOSED
                for line in self.topo_engine.topo.lines:
                    if (line["from"] == bus_idx or line["to"] == bus_idx):
                        lid = line["id"]
                        if breakers.get(lid, "CLOSED") == "CLOSED":
                            candidate_breakers.append(lid)
            elif elem_type == "LINE":
                if breakers.get(elem_id, "CLOSED") == "CLOSED":
                    candidate_breakers.append(elem_id)

            # Evaluate side effects of opening these breakers
            # side effects: does it isolate other healthy buses (especially critical ones like Bus 5)?
            for b_id in candidate_breakers:
                # Shield hospital (Bus 5) and control center (Bus 6) from accidental isolation
                # Check what components would form if we open this breaker
                temp_breakers = breakers.copy()
                temp_breakers[b_id] = "OPEN"
                
                graph = self.topo_engine.get_grid_graph(temp_breakers)
                components = self.topo_engine.get_connected_components(graph)
                
                # Check if any component contains loads but no generators
                isolates_load = False
                isolated_loads_list = []
                for comp in components:
                    has_gen = any(b in self.topo_engine.topo.generators for b in comp)
                    loads = [f"Bus_{b+1}" for b in comp if b in self.topo_engine.topo.loads]
                    if loads and not has_gen:
                        isolates_load = True
                        isolated_loads_list.extend(loads)

                # Estimate side effect severity
                if isolates_load:
                    side_effects[b_id] = {
                        "isolated_loads": list(set(isolated_loads_list)),
                        "severity": "HIGH" if "Bus_5" in isolated_loads_list or "Bus_6" in isolated_loads_list else "MEDIUM"
                    }
                    
                    # If it isolates the critical Bus_5 (hospital), block this isolation path unless there's no other way
                    if "Bus_5" in isolated_loads_list and elem_id != "Bus_5":
                        logger.warning(f"Blocking preemptive isolation on {b_id} because it would isolate critical hospital Bus 5")
                        continue

                recommended_isolation.append({
                    "command": "OPEN",
                    "target": b_id,
                    "reason": f"Preemptive Isolation: Isolate high-risk {elem_id} due to {reason}"
                })

        # Deduplicate recommendations
        unique_recs = []
        seen = set()
        for r in recommended_isolation:
            if r["target"] not in seen:
                seen.add(r["target"])
                unique_recs.append(r)

        return {
            "preemptive_isolation_active": len(unique_recs) > 0,
            "recommended_isolation": unique_recs,
            "side_effects": side_effects
        }
