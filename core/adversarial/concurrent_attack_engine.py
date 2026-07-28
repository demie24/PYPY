import os
import sys
import itertools
import numpy as np
from typing import Dict, List, Tuple, Any, Set

# Setup paths
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(parent_dir)
sys.path.append(project_root)
sys.path.append(os.path.join(parent_dir, "digital_twin"))
sys.path.append(os.path.join(parent_dir, "gnn"))
sys.path.append(os.path.join(parent_dir, "analytics"))

from core.digital_twin.grid_topology import GridTopology
from core.analytics.eb_cascading_failure_simulator import CascadingFailureSimulator
from core.analytics.som_vulnerability_engine import SomVulnerabilityEngine

class ConcurrentAttackEngine:
    """
    Coordinated concurrent attack planner and executor.
    Clusters grid nodes and branches, generates combinations, and plans
    optimal multi-target attacks using a multi-objective utility function.
    """
    def __init__(self, topo: GridTopology = None):
        self.topo = topo if topo is not None else GridTopology()
        self.cascade_sim = CascadingFailureSimulator(self.topo)
        self.som_engine = SomVulnerabilityEngine(self.topo)
        
        # Default Multi-Objective Weights
        # Objective = w_casc*CascadeSize + w_shed*LoadShed + w_bo*BlackoutProb - w_det*DetectProb - w_trust*TrustLoss
        self.weights = {
            "w_casc": 0.30,
            "w_shed": 0.40,
            "w_bo": 5.0,
            "w_det": 10.0,
            "w_trust": 2.0
        }

    def get_attack_combinations(self, elements: List[Any], num_targets: int) -> List[Tuple[Any]]:
        """
        Generates all distinct combinations of targets of size num_targets.
        """
        return list(itertools.combinations(elements, num_targets))

    def evaluate_attack_combination(self, targets: Tuple[Any], attack_type: str) -> Dict[str, float]:
        """
        Evaluates the physical and cyber consequences of a concurrent attack.
        """
        # Determine targets
        tripped_lines = set()
        compromised_buses = set()
        
        is_physical = attack_type == "TRIP_LINE"
        
        for t in targets:
            if isinstance(t, str) and (t.startswith("L_line") or t.startswith("L_trafo")):
                if is_physical:
                    tripped_lines.add(t)
            elif isinstance(t, int): # Bus index
                if is_physical:
                    # Trip all adjacent lines of this bus
                    adj_lines = [l["id"] for l in self.topo.lines if l["from"] == t or l["to"] == t]
                    tripped_lines.update(adj_lines)
                else:
                    compromised_buses.add(t)
            elif isinstance(t, str) and t.startswith("line_"):
                # Cyber attack on line
                pass
                
        # 1. Run physical cascade simulation
        if len(tripped_lines) > 0:
            res_cascade = self.cascade_sim.run_cascade(initial_tripped_lines=tripped_lines)
            cascade_size = float(res_cascade["cascade_size"])
            load_shed = float(res_cascade["load_shed"])
            blackout_prob = 1.0 if load_shed > 10.0 else (0.4 if load_shed > 2.0 else 0.0)
            
            # Physical trips are immediately detected
            detect_prob = 1.0
            trust_loss = len(tripped_lines) * 0.5
        else:
            # Cyber attack simulation (FDIA, DoS, Replay)
            cascade_size = 0.0
            load_shed = 0.0
            blackout_prob = 0.0
            
            # Evaluate cyber detection probability based on target criticalities
            # More critical generator transformers are audited more heavily
            detect_prob = 0.0
            trust_loss = 0.0
            
            for b in compromised_buses:
                # Get bus centrality (as proxy for monitoring intensity)
                bus_features = self.som_engine.get_bus_features()
                gnn_risk = bus_features[b, 0] # GNN risk score
                
                if attack_type == "FDIA":
                    # FDIA is noisy, high chance of PINN detection on high-criticality nodes
                    detect_prob += gnn_risk * 0.8
                    trust_loss += 0.3
                elif attack_type == "DoS":
                    # DoS is silent but causes state dropouts
                    detect_prob += gnn_risk * 0.4
                    trust_loss += 0.1
                elif attack_type == "Replay":
                    # Replay is stealthy
                    detect_prob += gnn_risk * 0.3
                    trust_loss += 0.15
                    
            detect_prob = min(1.0, detect_prob)
            
        return {
            "cascade_size": cascade_size,
            "load_shed": load_shed,
            "blackout_prob": blackout_prob,
            "detect_prob": detect_prob,
            "trust_loss": trust_loss
        }

    def plan_optimal_attack(self, community_id: int, num_targets: int, attack_type: str, custom_weights: Dict[str, float] = None, som_res: Dict = None) -> Dict[str, Any]:
        """
        Finds the optimal concurrent attack target set in a community.
        """
        weights = custom_weights if custom_weights is not None else self.weights
        
        # Get community elements
        if som_res is None:
            som_res = self.som_engine.cluster_grid(2, 2)
        comm = som_res["communities"][community_id]
        
        if attack_type == "TRIP_LINE":
            elements = comm["lines"]
        else:
            elements = comm["buses"]
            
        if len(elements) == 0:
            return {"targets": (), "score": -999.0, "metrics": {}}
            
        # Adjust target count if there are not enough elements
        n_targets = min(num_targets, len(elements))
        combos = self.get_attack_combinations(elements, n_targets)
        
        best_targets = ()
        best_score = -999.0
        best_metrics = {}
        
        for targets in combos:
            metrics = self.evaluate_attack_combination(targets, attack_type)
            
            # Compute Multi-Objective Utility Score
            score = (
                weights["w_casc"] * metrics["cascade_size"] +
                weights["w_shed"] * metrics["load_shed"] +
                weights["w_bo"] * metrics["blackout_prob"] -
                weights["w_det"] * metrics["detect_prob"] -
                weights["w_trust"] * metrics["trust_loss"]
            )
            
            if score > best_score:
                best_score = score
                best_targets = targets
                best_metrics = metrics
                
        return {
            "targets": best_targets,
            "score": best_score,
            "metrics": best_metrics,
            "community_id": community_id,
            "attack_type": attack_type
        }

if __name__ == "__main__":
    planner = ConcurrentAttackEngine()
    print("Planning concurrent TRIP_LINE attack (3 targets) on Community 1:")
    res = planner.plan_optimal_attack(community_id=1, num_targets=3, attack_type="TRIP_LINE")
    print(f"Optimal Targets: {res['targets']}")
    print(f"Expected Load Shed: {res['metrics']['load_shed']:.4f} pu")
    print(f"Expected Cascade Size: {res['metrics']['cascade_size']}")
