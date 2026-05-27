import os
import sys
import logging
from typing import Dict, Any, List, Set, Tuple

# Setup import paths
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from topology_recovery_engine import TopologyRecoveryEngine

logger = logging.getLogger("self_healing.microgrid_manager")

class MicrogridManager:
    """
    Manages autonomous operations within isolated healthy islands (microgrids).
    Tracks internal stability metrics and identifies local line restoration sequences.
    """
    def __init__(self, topology_engine=None):
        self.topo_engine = topology_engine if topology_engine else TopologyRecoveryEngine()

    def evaluate_microgrids(self, telemetry: Dict[str, Any], active_islands: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Evaluates stability metrics (voltage deviations, power balances) and restoration options
        specifically for isolated active islands.
        """
        if not telemetry or not active_islands:
            return {
                "microgrid_status": {},
                "local_restoration_options": []
            }

        state = telemetry.get("state", {})
        buses = state.get("buses", {})
        breakers = state.get("breakers", {})
        lines = state.get("lines", {})

        microgrid_status = {}
        local_restoration_options = []

        for island in active_islands:
            island_id = island["island_id"]
            if island["is_unstable"] or not island["has_generation"]:
                # Ignore unstable or un-energized islands (blackout zones)
                continue

            # Gather island details
            island_buses = island["buses"]
            gen_buses = island["generators"]
            load_buses = island["loads"]

            # Calculate total online generation in this island
            total_gen_mw = 0.0
            total_gen_capacity = 0.0
            for g_lbl in gen_buses:
                g_idx = int(g_lbl.replace("Bus_", "")) - 1
                b_data = buses.get(g_lbl, {})
                # Online if voltage is nominal
                if b_data.get("voltage_pu", 0.0) > 0.8:
                    total_gen_mw += b_data.get("P_mw", 0.0)
                    total_gen_capacity += self.topo_engine.topo.generators[g_idx]["P_nom"]

            # Calculate total load demand currently served in this island
            total_load_mw = 0.0
            for l_lbl in load_buses:
                total_load_mw += buses.get(l_lbl, {}).get("P_mw", 0.0)

            # Compute voltage stability indicators
            voltages = [buses.get(b, {}).get("voltage_pu", 1.0) for b in island_buses]
            avg_voltage = sum(voltages) / len(voltages) if voltages else 1.0
            voltage_variance = sum((v - avg_voltage)**2 for v in voltages) / len(voltages) if voltages else 0.0

            # Dynamic stability rating (0-100)
            stability_rating = 100.0 - (abs(avg_voltage - 1.0) * 200.0) - (voltage_variance * 500.0)
            stability_rating = max(0.0, min(100.0, stability_rating))

            microgrid_status[island_id] = {
                "buses_count": len(island_buses),
                "generation_mw": float(round(total_gen_mw, 2)),
                "generation_capacity": float(round(total_gen_capacity, 2)),
                "load_mw": float(round(total_load_mw, 2)),
                "avg_voltage": float(round(avg_voltage, 3)),
                "voltage_variance": float(round(voltage_variance, 5)),
                "stability_rating": float(round(stability_rating, 2))
            }

            # Local restoration: Find open breakers that are entirely inside this healthy island,
            # or connect a de-energized load bus directly to this healthy island.
            open_breakers = [lid for lid, status in breakers.items() if status == "OPEN"]
            for lid in open_breakers:
                line = next((l for l in self.topo_engine.topo.lines if l["id"] == lid), None)
                if not line:
                    continue
                u_lbl = f"Bus_{line['from'] + 1}"
                v_lbl = f"Bus_{line['to'] + 1}"

                # Case 1: Both buses are in the island but line is currently open
                if u_lbl in island_buses and v_lbl in island_buses:
                    local_restoration_options.append({
                        "command": "CLOSE",
                        "target": lid,
                        "island_id": island_id,
                        "reason": f"Microgrid Local Restoration: Close internal breaker {lid} to strengthen path mesh"
                    })
                # Case 2: One bus is in the island, other bus is in a de-energized island (no generation)
                else:
                    u_in_island = u_lbl in island_buses
                    v_in_island = v_lbl in island_buses
                    
                    other_lbl = v_lbl if u_in_island else u_lbl
                    
                    # Check if the other bus belongs to an un-energized island
                    other_island = next((isl for isl in active_islands if other_lbl in isl["buses"]), None)
                    if other_island and not other_island["has_generation"] and not other_island["is_unstable"]:
                        local_restoration_options.append({
                            "command": "CLOSE",
                            "target": lid,
                            "island_id": island_id,
                            "reason": f"Microgrid Local Restoration: Close tie breaker {lid} to restore de-energized load {other_lbl}"
                        })

        return {
            "microgrid_status": microgrid_status,
            "local_restoration_options": local_restoration_options
        }
