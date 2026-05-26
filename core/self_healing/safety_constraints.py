import numpy as np
from typing import Dict, Any, List, Tuple

class SafetyConstraintEngine:
    def __init__(self):
        # Hard limits
        self.V_MIN_HARD = 0.85
        self.V_MAX_HARD = 1.15
        self.V_MIN_SOFT = 0.90
        self.V_MAX_SOFT = 1.10
        self.MAX_LINE_LOAD_PU = 2.50  # 2.50 p.u. (250 MW)
        
        # Grid parameters
        self.line_connections = [
            (0, 3), # L1_4
            (1, 6), # L2_7
            (2, 8), # L3_9
            (3, 4), # L4_5
            (3, 8), # L4_9
            (4, 5), # L5_6
            (5, 6), # L6_7
            (6, 7), # L7_8
            (7, 8)  # L8_9
        ]
        self.line_names = ["L1_4", "L2_7", "L3_9", "L4_5", "L4_9", "L5_6", "L6_7", "L7_8", "L8_9"]
        self.bus_names = [f"Bus_{i}" for i in range(1, 10)]
        self.generators = [0, 1, 2] # Bus 1, 2, 3 (0-indexed)
        self.loads = [4, 5, 7]      # Bus 5, 6, 8 (0-indexed)
        
    def evaluate_constraints(self, 
                             telemetry: Dict[str, Any], 
                             action_name: str, 
                             target: str) -> Tuple[bool, List[str], float]:
        """
        Evaluates a candidate action against grid safety constraints.
        Returns:
            allowed: bool
            violated_rules: List[str]
            safety_score: float (0.0 to 1.0)
        """
        violated_rules = []
        state = telemetry.get("state", {})
        buses = state.get("buses", {})
        lines = state.get("lines", {})
        breakers = state.get("breakers", {})
        
        # 1. Voltage bounds check (Current state check)
        for b_name, b_data in buses.items():
            v = b_data.get("voltage_pu", 1.0)
            if v < self.V_MIN_HARD or v > self.V_MAX_HARD:
                violated_rules.append(f"Voltage violation at {b_name}: {v:.3f} p.u. outside [{self.V_MIN_HARD}, {self.V_MAX_HARD}]")
                
        # 2. Line loading check (Current state check)
        for l_name, l_data in lines.items():
            # load = sqrt(P^2 + Q^2) / V
            p = l_data.get("P_mw", 0.0) / 100.0
            q = l_data.get("Q_mvar", 0.0) / 100.0
            load_pu = np.sqrt(p**2 + q**2)
            if load_pu > self.MAX_LINE_LOAD_PU:
                violated_rules.append(f"Line overload on {l_name}: {load_pu:.2f} p.u. exceeds {self.MAX_LINE_LOAD_PU}")
                
        # 3. Anti-Islanding Protection check (Predictive check based on action)
        if action_name in ["ISOLATE_LINE", "OPEN_BREAKER", "ISOLATE_BUS", "ENABLE_ISLANDING"]:
            # Check what breakers would become OPEN
            temp_breakers = {l: (1 if status == "CLOSED" else 0) for l, status in breakers.items()}
            
            if action_name in ["ISOLATE_LINE", "OPEN_BREAKER"] and target in temp_breakers:
                temp_breakers[target] = 0
            elif action_name == "ISOLATE_BUS":
                # Open all breakers connected to target bus
                bus_idx = self.bus_names.index(target)
                for k, (f, t) in enumerate(self.line_connections):
                    if f == bus_idx or t == bus_idx:
                        temp_breakers[self.line_names[k]] = 0
            elif action_name == "ENABLE_ISLANDING":
                # Open specific boundary switches (e.g. L7_8, L4_5, etc.)
                for l in ["L7_8", "L4_5", "L8_9"]:
                    if l in temp_breakers:
                        temp_breakers[l] = 0
                        
            # Build current graph adjacency list
            adj = {i: [] for i in range(9)}
            for k, (f, t) in enumerate(self.line_connections):
                l_name = self.line_names[k]
                if temp_breakers.get(l_name, 1) == 1:
                    adj[f].append(t)
                    adj[t].append(f)
                    
            # Run DFS from generator nodes to find reachable buses
            visited = set()
            for gen in self.generators:
                self._dfs(gen, adj, visited)
                
            # Verify if all load buses can reach at least one generator
            for l_bus in self.loads:
                if l_bus not in visited:
                    violated_rules.append(f"Anti-Islanding: Opening {target} would isolate {self.bus_names[l_bus]} from generators.")
                    
        # 4. Topology Integrity / Connectivity check
        # Verify that we do not have floating de-energized buses with active switches
        if action_name == "RECONNECT_LINE" or action_name == "REROUTE_FLOW":
            # Action intends to CLOSE a line. Verify it doesn't close onto a faulted segment.
            # (Restoration policy constraints)
            if target in telemetry.get("attack_status", {}).get("compromised_nodes", {}):
                violated_rules.append(f"Safety Gating: Cannot close {target} under active cyber compromise.")
                
        # Calculate safety score based on count of violations
        num_violations = len(violated_rules)
        safety_score = max(0.0, 1.0 - 0.25 * num_violations)
        allowed = num_violations == 0
        
        return allowed, violated_rules, safety_score

    def _dfs(self, node: int, adj: Dict[int, List[int]], visited: set):
        visited.add(node)
        for neighbor in adj.get(node, []):
            if neighbor not in visited:
                self._dfs(neighbor, adj, visited)
