import logging
from typing import Dict, List, Any

# Configure logging
logger = logging.getLogger("self_healing.degraded_operation_manager")

class DegradedOperationManager:
    """
    Manages grid operations during emergency/degraded states.
    Prioritizes critical load buses (Load 5 > Load 8 > Load 6) and computes
    controlled load shedding commands to prevent physical collapses or overloads,
    supporting partial-grid survival microgrids.
    """
    def __init__(self):
        # Bus mapping: index -> label, priority (1: highest, 3: lowest)
        self.load_priorities = {
            "Bus_5": {"idx": 4, "priority": 1, "P_nom": 125.0, "name": "Control Center / Hospital Zone"},
            "Bus_8": {"idx": 7, "priority": 2, "P_nom": 100.0, "name": "Heavy Industrial Substation"},
            "Bus_6": {"idx": 5, "priority": 3, "P_nom": 90.0, "name": "Residential / Commercial Center"}
        }
        # Generation sources
        self.gen_buses = {
            "Bus_1": {"idx": 0, "P_nom": 72.0},
            "Bus_2": {"idx": 1, "P_nom": 163.0},
            "Bus_3": {"idx": 2, "P_nom": 85.0}
        }
        
    def evaluate_grid_survival(self, telemetry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluates grid generation limits and line thermal loadings to suggest
        controlled load-shedding and partial-grid microgrid survival strategies.
        """
        if not telemetry:
            return {
                "active_degraded_mode": False,
                "critical_buses_secured": [],
                "load_shedding_active": False,
                "load_shed_summary": {},
                "survival_commands": [],
                "partial_grid_survival_active": False,
                "secured_microgrids": []
            }

        state = telemetry.get("state", {})
        buses = state.get("buses", {})
        lines = state.get("lines", {})
        breakers = state.get("breakers", {})

        # 1. Calculate active generation capacity
        gen_capacity = 0.0
        online_generators = []
        for g_name, g_data in self.gen_buses.items():
            b_val = buses.get(g_name, {})
            v = b_val.get("voltage_pu", 0.0)
            if v > 0.8:
                gen_capacity += b_val.get("P_mw", g_data["P_nom"])
                online_generators.append(g_name)

        # 2. Calculate current total load demand
        total_demand = 0.0
        active_demand = {}
        for l_name, l_data in self.load_priorities.items():
            b_val = buses.get(l_name, {})
            v = b_val.get("voltage_pu", 0.0)
            if v > 0.5:
                p_load = b_val.get("P_mw", l_data["P_nom"])
                total_demand += p_load
                active_demand[l_name] = p_load
            else:
                active_demand[l_name] = 0.0

        # 3. Check for severe line overloads (> 100% capacity)
        severe_overloads = []
        for lid, l_data in lines.items():
            loading = l_data.get("capacity_pct", 0.0)
            if loading > 100.0:
                severe_overloads.append((lid, loading))

        active_degraded_mode = False
        load_shedding_active = False
        load_shed_summary = {}
        survival_commands = []
        partial_grid_survival_active = False
        secured_microgrids = []

        # Enforce degraded mode if capacity is deficient or lines are severely overloaded
        generation_deficit = total_demand - gen_capacity
        if generation_deficit > 0.0 or len(severe_overloads) > 0 or len(online_generators) < len(self.gen_buses):
            active_degraded_mode = True

        # 4. Formulate Partial-Grid Survival microgrids and controlled load shedding
        if active_degraded_mode:
            # Check if grid fragmentation occurred
            # If critical hospital Bus_5 is isolated from Gen_1 but connected to Gen_2 or Gen_3, we form a microgrid
            # Bus_5 is index 4. Gen 1 is index 0. Gen 2 is index 1. Gen 3 is index 2.
            from core.self_healing.topology_recovery_engine import TopologyRecoveryEngine
            topo = TopologyRecoveryEngine()
            graph = topo.get_grid_graph(breakers)
            components = topo.get_connected_components(graph)
            
            bus5_comp = next((comp for comp in components if 4 in comp), None)
            
            if bus5_comp:
                # Check if Gen 1 is in this component
                if 0 not in bus5_comp and any(g in bus5_comp for g in [1, 2]):
                    # Bus 5 is isolated from Gen 1 but has Gen 2 or Gen 3 online.
                    # Formulate survival microgrid!
                    partial_grid_survival_active = True
                    microgrid_gen = "Bus_2" if 1 in bus5_comp else "Bus_3"
                    secured_microgrids.append({
                        "generator": microgrid_gen,
                        "priority_load": "Bus_5",
                        "status": "SURVIVAL_CRITICAL"
                    })
                    logger.warning(f"[DEGRADED OPERATION] Formulated emergency microgrid: Gen {microgrid_gen} shielding critical Bus_5.")

            # Calculate target deficit to shed
            deficit_to_shed = max(0.0, generation_deficit)

            for lid, loading in severe_overloads:
                overload_mw = (loading - 100.0) / 100.0 * 100.0
                deficit_to_shed += max(0.0, overload_mw)

            # Shed in reverse priority: Priority 3 (Bus 6), then Priority 2 (Bus 8), then Priority 1 (Bus 5)
            priority_order = sorted(self.load_priorities.keys(), key=lambda x: self.load_priorities[x]["priority"], reverse=True)

            remaining_to_shed = deficit_to_shed
            for l_name in priority_order:
                if remaining_to_shed <= 0.0:
                    break
                
                curr_load = active_demand.get(l_name, 0.0)
                if curr_load <= 0.0:
                    curr_load = self.load_priorities[l_name]["P_nom"]
                    
                shed_amount = min(curr_load, remaining_to_shed)
                if shed_amount > 1.0:
                    pct = (shed_amount / self.load_priorities[l_name]["P_nom"]) * 100.0
                    pct = min(100.0, max(0.0, pct))
                    
                    load_shed_summary[l_name] = float(round(pct, 1))
                    load_shedding_active = True
                    remaining_to_shed -= shed_amount
                    
                    survival_commands.append({
                        "command": "SHED_LOAD",
                        "target": l_name,
                        "percentage": float(round(pct, 1)),
                        "source": "DEGRADED_MANAGER_SURVIVAL"
                    })

        # 5. Check which critical load buses are secured (V > 0.90 p.u.)
        critical_buses_secured = []
        for l_name, l_data in self.load_priorities.items():
            v = buses.get(l_name, {}).get("voltage_pu", 0.0)
            if v > 0.90:
                critical_buses_secured.append(l_name)

        return {
            "active_degraded_mode": active_degraded_mode,
            "critical_buses_secured": critical_buses_secured,
            "load_shedding_active": load_shedding_active,
            "load_shed_summary": load_shed_summary,
            "survival_commands": survival_commands,
            "partial_grid_survival_active": partial_grid_survival_active,
            "secured_microgrids": secured_microgrids
        }
