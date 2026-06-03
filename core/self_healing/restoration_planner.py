import os
import sys
import logging
from typing import Dict, List, Any, Tuple

# Setup import paths
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(CURRENT_DIR)

from core.self_healing.topology_recovery_engine import TopologyRecoveryEngine
from core.self_healing.restoration_validator import RestorationValidator

logger = logging.getLogger("self_healing.restoration_planner")

class RestorationPlanner:
    """
    Generates prioritized multi-step breaker recovery sequences using context-aware,
    multi-objective optimization (criticality, cost, stability, cyber risk, and trust).
    """
    def __init__(self, topology_engine=None, validator=None):
        self.topo_engine = topology_engine if topology_engine else TopologyRecoveryEngine()
        self.validator = validator if validator else RestorationValidator()
        
    def plan_restoration(self, 
                         telemetry: Dict[str, Any], 
                         faulted_breakers: list = None,
                         trust_scores: Dict[str, Any] = None,
                         threat_data: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Generates an ordered sequence of restoration commands based on multi-objective scoring.
        """
        if not telemetry:
            return []

        state = telemetry.get("state", {})
        breakers = state.get("breakers", {})
        buses = state.get("buses", {})
        attack_status = telemetry.get("attack_status", {})
        compromised_nodes = set(attack_status.get("compromised_nodes", {}).keys())
        
        # 1. Run BFS/DFS topology analysis
        topo_analysis = self.topo_engine.analyze_topology(telemetry)
        isolated_segments = topo_analysis["isolated_segments"]
        reroute_options = topo_analysis["reroute_options"]
        
        # Filter out options that are in faulted_breakers
        if faulted_breakers:
            reroute_options = [opt for opt in reroute_options if opt["line_id"] not in faulted_breakers]
        
        # Filter out isolated segments that do not contain loads
        isolated_loads_exist = False
        for comp in isolated_segments:
            if any(self.topo_engine.topo.loads.get(bus) is not None for bus in comp):
                isolated_loads_exist = True
                break
                
        if not isolated_loads_exist:
            logger.info("No isolated loads identified. Active planning bypassed.")
            return []
            
        sequence = []
        
        # 2. Validate and score routing options
        validated_options = []
        for option in reroute_options:
            lid = option["line_id"]
            
            # --- CYBER RISK & TRUST PROTECTION (Unsafe restorations avoidance) ---
            # Get terminal buses for the line
            line_data = next((l for l in self.topo_engine.topo.lines if l["id"] == lid), None)
            if not line_data:
                continue
            
            from_bus = f"Bus_{line_data['from'] + 1}"
            to_bus = f"Bus_{line_data['to'] + 1}"
            
            # Block restoration if connecting to an actively compromised bus
            if from_bus in compromised_nodes or to_bus in compromised_nodes:
                logger.warning(f"[RESTORATION PLANNER] Bypassing option {lid} due to active cyber compromise on terminals.")
                continue
                
            # Block restoration if trust score of line or terminals is below threshold (50%)
            t_line = 100.0
            t_from = 100.0
            t_to = 100.0
            
            if trust_scores:
                # Support both flat and detailed trust score formats
                line_trust_map = trust_scores.get("line_trust", {})
                bus_trust_map = trust_scores.get("bus_trust", {})
                details = trust_scores.get("details", {})
                
                t_line = line_trust_map.get(lid, details.get(lid, {}).get("trust_score", 100.0))
                t_from = bus_trust_map.get(from_bus, details.get(from_bus, {}).get("trust_score", 100.0))
                t_to = bus_trust_map.get(to_bus, details.get(to_bus, {}).get("trust_score", 100.0))

            # Normalize to 0-100 scale
            t_line_norm = t_line if t_line > 1.0 else t_line * 100.0
            t_from_norm = t_from if t_from > 1.0 else t_from * 100.0
            t_to_norm = t_to if t_to > 1.0 else t_to * 100.0
            
            if min(t_line_norm, t_from_norm, t_to_norm) < 50.0:
                logger.warning(
                    f"[RESTORATION PLANNER] Bypassing option {lid} due to low trust "
                    f"(line: {t_line_norm:.1f}%, from: {t_from_norm:.1f}%, to: {t_to_norm:.1f}%)"
                )
                continue

            # Run dry-run validation in sandbox
            val_res = self.validator.validate_action(telemetry, "REROUTE_FLOW", lid)
            if not val_res["is_safe"]:
                logger.warning(f"Rerouting option {lid} rejected by sandbox: {val_res['violations']}")
                continue
                
            # Compute Multi-Objective Restoration Score
            safety_score = val_res["safety_score"]
            predicted_voltages = val_res["predicted_voltages"]
            predicted_loadings = val_res["predicted_loadings"]
            
            # (a) Critical Load Reward
            critical_reward = 0.0
            # Bus_5 is Hospital (index 4), Bus_8 is Industrial (index 7), Bus_6 is Residential (index 5)
            if buses.get("Bus_5", {}).get("voltage_pu", 1.0) < 0.85 and predicted_voltages[4] >= 0.90:
                critical_reward += 50.0  # High priority hospital restoration
            if buses.get("Bus_8", {}).get("voltage_pu", 1.0) < 0.85 and predicted_voltages[7] >= 0.90:
                critical_reward += 30.0  # Industrial restoration
            if buses.get("Bus_6", {}).get("voltage_pu", 1.0) < 0.85 and predicted_voltages[5] >= 0.90:
                critical_reward += 15.0  # Residential restoration

            # (b) Restoration Cost (penalty for switching steps)
            cost_penalty = -5.0  # Cost per breaker switch

            # (c) Stability Impact (voltage deviation & line loadings)
            v_dev = sum((v - 1.0)**2 for v in predicted_voltages)
            stability_penalty = -30.0 * v_dev
            
            max_load = max(predicted_loadings.values()) if predicted_loadings else 0.0
            overload_penalty = -20.0 * max(0.0, max_load - 0.95)

            # (d) Cyber Risk Penalty
            threat_score = float(threat_data.get("threat_score", 0.0)) if threat_data else 0.0
            cyber_penalty = 0.0
            if threat_score > 30.0:
                # Deduct points if near threat zones or if average path trust is degraded
                mean_path_trust = (t_line_norm + t_from_norm + t_to_norm) / 3.0
                cyber_penalty = -0.5 * (100.0 - mean_path_trust) - (threat_score * 0.1)

            total_score = safety_score + critical_reward + cost_penalty + stability_penalty + overload_penalty + cyber_penalty

            validated_options.append({
                "line_id": lid,
                "score": total_score,
                "confidence": val_res["confidence"]
            })
            
        # Sort options: highest score and confidence first
        validated_options.sort(key=lambda x: (x["score"], x["confidence"]), reverse=True)
        
        for opt in validated_options:
            sequence.append({
                "command": "CLOSE",
                "target": opt["line_id"],
                "reason": f"Reroute flow via tie-breaker {opt['line_id']} to restore subgrid segment (Restoration Score: {opt['score']:.1f})."
            })
            
        # 3. Rehearse the entire sequence sequentially in sandbox
        if sequence:
            rehearsal_steps = [(s["command"], s["target"]) for s in sequence]
            self.validator.sandbox.reset_to_state(telemetry)
            all_safe, results = self.validator.sandbox.rehearse_sequence(rehearsal_steps)
            if not all_safe:
                logger.error("Sequential rehearsal validation failed. Trimming unsafe steps...")
                safe_sequence = []
                for idx, step_res in enumerate(results):
                    if step_res["result"]["allowed"]:
                        safe_sequence.append(sequence[idx])
                    else:
                        logger.warning(f"Restoration step {sequence[idx]['target']} failed rehearsal.")
                return safe_sequence
                
        return sequence
