import os
import sys
import copy
import logging
import numpy as np
from typing import Dict, Any, List, Tuple

# Setup import paths
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(CURRENT_DIR)
sys.path.append(os.path.abspath(os.path.join(CURRENT_DIR, "..", "digital_twin")))

try:
    from grid_topology import GridTopology
    from physics import GridPhysicsEngine
except ImportError:
    # Standalone mock fallbacks matching digital_twin module signatures
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

    class GridPhysicsEngine:
        def __init__(self, topology):
            self.topo = topology
        def solve(self, breakers, active_loads, generator_P, generator_Q):
            V = np.ones(9)
            theta = np.zeros(9)
            P = np.zeros(9)
            Q = np.zeros(9)
            line_flows = {line["id"]: {"P_flow": 0.1, "Q_flow": 0.02, "current": 0.1} for line in self.topo.lines}
            return V, theta, P, Q, line_flows

from core.self_healing.safety_constraints import SafetyConstraintEngine

logger = logging.getLogger("self_healing.restoration_sandbox")

class RestorationSandbox:
    """
    Stateful sandbox environment that handles isolated cyber-physical simulations.
    Enables dry-run action testing, sequential rehearsals, and safety validation
    without impacting active MQTT brokers or telemetry structures.
    """
    def __init__(self, topology=None, physics=None):
        self.topo = topology if topology else GridTopology()
        self.physics = physics if physics else GridPhysicsEngine(self.topo)
        self.safety = SafetyConstraintEngine()

        # Local sandbox copy of active grid state variables
        self.breakers = {line["id"]: "CLOSED" for line in self.topo.lines}
        self.loads = {}
        for bus_idx, load in self.topo.loads.items():
            # Convert MW to p.u. (100 MVA base)
            self.loads[bus_idx] = {"P": load["P_nom"] / 100.0 if load["P_nom"] > 10.0 else load["P_nom"], 
                                   "Q": load["Q_nom"] / 100.0 if load["Q_nom"] > 10.0 else load["Q_nom"]}
        
        self.gen_P = {k: (v["P_nom"] / 100.0 if v["P_nom"] > 10.0 else v["P_nom"]) for k, v in self.topo.generators.items()}
        self.gen_Q = {k: (v["Q_nom"] / 100.0 if v["Q_nom"] > 10.0 else v["Q_nom"]) for k, v in self.topo.generators.items()}

    def reset_to_state(self, telemetry: Dict[str, Any]):
        """
        Synchronizes the sandbox grid parameters with a specific telemetry snapshot.
        """
        if not telemetry or "state" not in telemetry:
            return
            
        state = telemetry["state"]
        # Sync breakers
        if "breakers" in state:
            self.breakers = copy.deepcopy(state["breakers"])
            
        # Sync loads
        if "buses" in state:
            for b_idx in self.topo.loads.keys():
                bus_name = f"Bus_{b_idx + 1}"
                if bus_name in state["buses"]:
                    b_data = state["buses"][bus_name]
                    # Try to parse P and Q, otherwise fallback to nominals
                    p_val = b_data.get("P_mw", self.topo.loads[b_idx]["P_nom"]) / 100.0
                    q_val = b_data.get("Q_mvar", self.topo.loads[b_idx]["Q_nom"]) / 100.0
                    self.loads[b_idx] = {"P": p_val, "Q": q_val}
                    
        # Sync generator setpoints
        for g_idx in self.topo.generators.keys():
            bus_name = f"Bus_{g_idx + 1}"
            if "buses" in state and bus_name in state["buses"]:
                b_data = state["buses"][bus_name]
                p_val = b_data.get("P_mw", self.topo.generators[g_idx]["P_nom"]) / 100.0
                q_val = b_data.get("Q_mvar", self.topo.generators[g_idx]["Q_nom"]) / 100.0
                self.gen_P[g_idx] = p_val
                self.gen_Q[g_idx] = q_val

    def dry_run_action(self, action_name: str, target: str) -> Dict[str, Any]:
        """
        Simulates execution of a single action in isolation.
        Returns predicted physical states and metrics without modifying the live grid.
        """
        # Save pre-dry-run state
        original_breakers = copy.deepcopy(self.breakers)
        
        # Apply hypothetical action changes to local breakers
        if action_name in ["ISOLATE_LINE", "OPEN_BREAKER", "OPEN"] and target in self.breakers:
            self.breakers[target] = "OPEN"
        elif action_name in ["RECONNECT_LINE", "REROUTE_FLOW", "CLOSE"] and target in self.breakers:
            self.breakers[target] = "CLOSED"
        elif action_name == "ISOLATE_BUS":
            # Open all lines connected to target bus
            try:
                bus_idx = int(target.split("_")[1]) - 1
                for line in self.topo.lines:
                    if line["from"] == bus_idx or line["to"] == bus_idx:
                        self.breakers[line["id"]] = "OPEN"
            except Exception:
                pass
        elif action_name == "ENABLE_ISLANDING":
            # Open zonal split lines L7_8, L4_5, L8_9
            for lid in ["L7_8", "L4_5", "L8_9"]:
                if lid in self.breakers:
                    self.breakers[lid] = "OPEN"

        # Solve power flow on the hypothetical state
        V, theta, P, Q, line_flows = self.physics.solve(
            self.breakers, self.loads, self.gen_P, self.gen_Q
        )

        # Build mock telemetry payload of the result to evaluate safety constraints
        hypothetical_telemetry = {
            "state": {
                "buses": {f"Bus_{i+1}": {"voltage_pu": float(V[i]), "angle_rad": float(theta[i])} for i in range(9)},
                "lines": {lid: {"P_mw": float(f["P_flow"]*100.0), "Q_mvar": float(f["Q_flow"]*100.0), "current_pu": float(f["current"])} for lid, f in line_flows.items()},
                "breakers": self.breakers.copy()
            }
        }

        # Check safety of result
        allowed, violations, safety_score = self.safety.evaluate_constraints(
            hypothetical_telemetry, "NO_ACTION", "SYSTEM"
        )

        # Estimate cascade risk and confidence
        cascade_risk = self.estimate_cascade_risk(line_flows)
        islanding = any(v < 0.20 for v in V)
        confidence = self.get_confidence_score(V, line_flows, islanding)

        # Restore original breaker states
        self.breakers = original_breakers

        return {
            "allowed": allowed,
            "violations": violations,
            "safety_score": float(safety_score),
            "cascade_risk": float(cascade_risk),
            "confidence": float(confidence),
            "islanding_active": islanding,
            "predicted_voltages": [float(v) for v in V],
            "predicted_loadings": {lid: float(f["current"]) for lid, f in line_flows.items()}
        }

    def rehearse_sequence(self, sequence: List[Tuple[str, str]]) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        Executes a sequence of actions inside the sandbox, accumulating state modifications.
        Returns a tuple of (all_actions_safe, list_of_step_results).
        """
        step_results = []
        all_safe = True
        
        for name, target in sequence:
            res = self.dry_run_action(name, target)
            step_results.append({
                "action": name,
                "target": target,
                "result": res
            })
            if not res["allowed"]:
                all_safe = False
                
            # Permanently apply safe changes in rehearsal state for subsequent steps
            if res["allowed"]:
                if name in ["ISOLATE_LINE", "OPEN_BREAKER", "OPEN"] and target in self.breakers:
                    self.breakers[target] = "OPEN"
                elif name in ["RECONNECT_LINE", "REROUTE_FLOW", "CLOSE"] and target in self.breakers:
                    self.breakers[target] = "CLOSED"
                elif name == "ISOLATE_BUS":
                    try:
                        bus_idx = int(target.split("_")[1]) - 1
                        for line in self.topo.lines:
                            if line["from"] == bus_idx or line["to"] == bus_idx:
                                self.breakers[line["id"]] = "OPEN"
                    except Exception:
                        pass
                elif name == "ENABLE_ISLANDING":
                    for lid in ["L7_8", "L4_5", "L8_9"]:
                        if lid in self.breakers:
                            self.breakers[lid] = "OPEN"
                            
        return all_safe, step_results

    def simulate_attack_replay(self, attack_type: str, target: str) -> Dict[str, Any]:
        """
        Simulates an attack injection in the sandbox to observe predicted topology degradation.
        """
        original_breakers = copy.deepcopy(self.breakers)
        
        # Simulate attack consequences
        if attack_type == "LINE_TRIP" and target in self.breakers:
            self.breakers[target] = "OPEN"
        elif attack_type == "COORDINATED_TRIP":
            # Trip multiple key lines (e.g. L4_5 and L7_8)
            for lid in ["L4_5", "L7_8"]:
                if lid in self.breakers:
                    self.breakers[lid] = "OPEN"
        elif attack_type == "SLACK_TRIP":
            if "L1_4" in self.breakers:
                self.breakers["L1_4"] = "OPEN"

        # Solve power flow on the compromised state
        V, theta, P, Q, line_flows = self.physics.solve(
            self.breakers, self.loads, self.gen_P, self.gen_Q
        )

        cascade_risk = self.estimate_cascade_risk(line_flows)
        islanding = any(v < 0.20 for v in V)
        confidence = self.get_confidence_score(V, line_flows, islanding)

        # Restore original breaker states
        self.breakers = original_breakers

        return {
            "attack_type": attack_type,
            "target": target,
            "cascade_risk": float(cascade_risk),
            "confidence": float(confidence),
            "islanding_active": islanding,
            "voltages": [float(v) for v in V]
        }

    def estimate_cascade_risk(self, line_flows: Dict[str, Any]) -> float:
        """
        Calculates a risk metric indicating the probability of cascading overload trips.
        Risk is computed based on line loading ratios exceeding the 1.0 p.u. threshold.
        """
        risk = 0.0
        for lid, flow in line_flows.items():
            curr = flow.get("current", 0.0)
            if curr > 1.0:
                # Quadratic risk penalty scaling for overloaded conductors
                risk += (curr - 1.0) ** 2
        return min(1.0, float(risk))

    def get_confidence_score(self, V: np.ndarray, line_flows: dict, islanding: bool) -> float:
        """
        Computes a restoration confidence score representing healing feasibility (0.0 to 1.0).
        """
        if islanding:
            return 0.1  # Severe connectivity loss
            
        score = 1.0
        
        # Penalize voltage deviations from nominal 1.0 p.u.
        voltage_dev = np.mean(np.abs(V - 1.0))
        score -= min(0.4, voltage_dev * 2.0)
        
        # Penalize transmission line overloads
        max_load = 0.0
        for lid, flow in line_flows.items():
            max_load = max(max_load, flow.get("current", 0.0))
            
        if max_load > 1.2:
            score -= 0.4
        elif max_load > 1.0:
            score -= 0.2
            
        return max(0.0, float(score))
