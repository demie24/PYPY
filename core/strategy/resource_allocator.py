import logging
from typing import List, Dict, Any

logger = logging.getLogger("strategy.resource_allocator")

class ResourceAllocator:
    def __init__(self, max_operators: int = 3, max_relays: int = 5, backup_lines: List[str] = None):
        self.max_operators = max_operators
        self.max_relays = max_relays
        self.backup_lines = backup_lines if backup_lines is not None else ["L7_8"]
        
        # Current available resources
        self.available_operators = max_operators
        self.available_relays = max_relays
        self.available_backup_lines = list(self.backup_lines)

    def allocate_resources(self, priority_order: List[str], risk_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculates optimal allocation of operators, relays, and backup lines based on active grid priorities.
        """
        # Reset availability state for calculation cycle
        self.available_operators = self.max_operators
        self.available_relays = self.max_relays
        self.available_backup_lines = list(self.backup_lines)

        dispatched_operators = {}
        reserved_backup_lines = []
        allocated_relays = {}
        rationales = []

        node_risks = risk_data.get("node_risk_scores", {})
        asset_risks = risk_data.get("asset_risk_scores", {})

        for priority in priority_order:
            if self.available_operators == 0 and self.available_relays == 0 and not self.available_backup_lines:
                break

            if priority == "CYBER_ATTACK":
                # Find most high-risk compromised/threatened nodes
                threatened = [node for node, score in node_risks.items() if score > 50.0]
                if not threatened:
                    threatened = ["Bus_5"]  # Priority node default
                
                for node in threatened:
                    if self.available_operators > 0:
                        dispatched_operators[node] = dispatched_operators.get(node, 0) + 1
                        self.available_operators -= 1
                        rationales.append(f"Dispatched operator to {node} to secure cybersecurity controls.")
                    if self.available_relays > 0:
                        allocated_relays[node] = allocated_relays.get(node, 0) + 1
                        self.available_relays -= 1

            elif priority == "VOLTAGE_COLLAPSE":
                # Requires operator intervention and relays configuration
                critical_buses = [b for b, v in node_risks.items() if v > 60.0]
                for bus in critical_buses:
                    if self.available_operators > 0:
                        dispatched_operators[bus] = dispatched_operators.get(bus, 0) + 1
                        self.available_operators -= 1
                        rationales.append(f"Dispatched operator to {bus} for voltage stabilization.")
                    if self.available_relays > 0:
                        allocated_relays[bus] = allocated_relays.get(bus, 0) + 1
                        self.available_relays -= 1

            elif priority == "LINE_OVERLOAD":
                # Reserve backup lines to reroute flows
                stressed_lines = [l for l, score in asset_risks.items() if score > 50.0]
                for l in stressed_lines:
                    if self.available_backup_lines:
                        bl = self.available_backup_lines.pop(0)
                        reserved_backup_lines.append(bl)
                        rationales.append(f"Reserved backup line {bl} to relieve overload on line {l}.")
                    
                    if self.available_operators > 0:
                        dispatched_operators[l] = dispatched_operators.get(l, 0) + 1
                        self.available_operators -= 1
                        rationales.append(f"Dispatched operator to monitor overloading line {l} thermal characteristics.")

            elif priority == "GENERATOR_INSTABILITY":
                # Needs operators dispatched to generation buses
                for gen in ["Bus_1", "Bus_2", "Bus_3"]:
                    if self.available_operators > 0:
                        dispatched_operators[gen] = dispatched_operators.get(gen, 0) + 1
                        self.available_operators -= 1
                        rationales.append(f"Dispatched operator to generator bus {gen} to monitor governor/exciter parameters.")

            elif priority == "RESTORATION_FAILURE":
                # Allocate relays to lock down breaker configs
                if self.available_relays > 1:
                    allocated_relays["RECOVERY_LOCK"] = 2
                    self.available_relays -= 2
                    rationales.append("Allocated redundant safety relays to lock down restoration breakers.")

        if not rationales:
            rationales.append("Nominal operations. All resources held in standby reserve.")

        return {
            "dispatched_operators": dispatched_operators,
            "reserved_backup_lines": reserved_backup_lines,
            "allocated_relays": allocated_relays,
            "available_operators_remaining": self.available_operators,
            "available_relays_remaining": self.available_relays,
            "available_backup_lines_remaining": self.available_backup_lines,
            "allocation_rationale": " ".join(rationales)
        }
