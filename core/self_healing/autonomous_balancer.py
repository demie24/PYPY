import logging
from typing import Dict, Any, List

logger = logging.getLogger("self_healing.autonomous_balancer")

class AutonomousBalancer:
    """
    Monitors generation-load imbalances in grid islands statefully.
    Formulates frequency metrics and recommends balancing control commands (generator adjust, load shed).
    """
    def __init__(self):
        # Base nominal frequency (Hz)
        self.nominal_freq = 60.0
        # Tracks frequencies of islands statefully to simulate system inertia
        self.island_frequencies = {}

    def balance_grid(self, telemetry: Dict[str, Any], active_islands: List[Dict[str, Any]], critical_guard) -> Dict[str, Any]:
        """
        Calculates generation-load imbalances and frequency deviations per island.
        Formulates stabilizing generator adjustment or load shedding commands.
        """
        if not telemetry or not active_islands:
            return {
                "frequencies": {},
                "balancing_commands": [],
                "mismatches": {}
            }

        state = telemetry.get("state", {})
        buses = state.get("buses", {})
        breakers = state.get("breakers", {})

        balancing_commands = []
        frequencies = {}
        mismatches = {}

        for island in active_islands:
            island_id = island["island_id"]
            if not island["has_generation"]:
                # De-energized blackout island
                frequencies[island_id] = 0.0
                mismatches[island_id] = 0.0
                continue

            island_buses = island["buses"]
            gen_buses = island["generators"]
            load_buses = island["loads"]

            # Calculate total generation in island
            total_gen_mw = 0.0
            for g_lbl in gen_buses:
                total_gen_mw += buses.get(g_lbl, {}).get("P_mw", 0.0)

            # Calculate total active loads in island
            total_load_mw = 0.0
            for l_lbl in load_buses:
                total_load_mw += buses.get(l_lbl, {}).get("P_mw", 0.0)

            mismatch_mw = total_gen_mw - total_load_mw
            mismatches[island_id] = float(round(mismatch_mw, 2))

            # Simulate dynamic frequency trajectory for this island
            # If mismatch > 0 (over-generation), frequency rises; mismatch < 0 (under-generation), frequency drops.
            prev_freq = self.island_frequencies.get(island_id, self.nominal_freq)
            
            # Simple swing equation emulation: delta_f = mismatch_mw * 0.02
            target_freq = self.nominal_freq + mismatch_mw * 0.02
            
            # Apply inertia smoothing
            alpha = 0.30
            freq = prev_freq + alpha * (target_freq - prev_freq)
            freq = max(55.0, min(65.0, freq))
            self.island_frequencies[island_id] = freq
            frequencies[island_id] = float(round(freq, 2))

            # Formulate emergency balancing actions if frequency drifts
            # 1. Under-frequency (freq < 59.7 Hz) -> requires load shedding
            if freq < 59.7:
                # Find best load to shed in this island, guarded by priority
                target_bus = critical_guard.select_load_to_shed(load_buses, telemetry)
                if target_bus:
                    # Request shedding 15% load
                    balancing_commands.append({
                        "command": "SHED_LOAD",
                        "target": target_bus,
                        "percentage": 15.0,
                        "source": "AUTONOMOUS_BALANCER",
                        "reason": f"Under-frequency stabilization: Shed load on {target_bus} to restore frequency"
                    })

            # 2. Over-frequency (freq > 60.3 Hz) -> requires generator reduction
            elif freq > 60.3:
                # Reduce output of the largest online generator in this island
                online_gens = [g for g in gen_buses if buses.get(g, {}).get("voltage_pu", 0.0) > 0.8]
                if online_gens:
                    # Pick generator on Bus_2 or Bus_3 (slack bus Bus_1 usually absorbs mismatch, but in isolated island Bus_2 or Bus_3 can be adjusted)
                    target_gen = max(online_gens, key=lambda g: buses.get(g, {}).get("P_mw", 0.0))
                    curr_p = buses.get(target_gen, {}).get("P_mw", 100.0)
                    # Reduce output by 15 MW
                    new_p = max(10.0, curr_p - 15.0)
                    balancing_commands.append({
                        "command": "ADJUST_GEN",
                        "target": target_gen,
                        "P_mw": float(round(new_p, 2)),
                        "source": "AUTONOMOUS_BALANCER",
                        "reason": f"Over-frequency stabilization: Reduce generator {target_gen} output to {new_p:.1f} MW"
                    })

        return {
            "frequencies": frequencies,
            "balancing_commands": balancing_commands,
            "mismatches": mismatches
        }

    def reset(self):
        self.island_frequencies.clear()
