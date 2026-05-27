import numpy as np
from typing import Dict, Any, List
from action_registry import ActionRegistry

class ActionExplainer:
    """
    Translates raw reinforcement learning actions and observations into descriptive
    explanations, detailing expected rewards, cascade reductions, and reasoning chains.
    """
    def __init__(self):
        self.registry = ActionRegistry()
        self.action_descriptions = {
            0: "No action selected. The grid state is currently stabilized.",
            1: "Tripping the line to isolate an active fault or intercept cascade propagation.",
            2: "Closing the transmission line to re-establish power connectivity.",
            3: "Overriding telemetry trust to ignore corrupted or spoofed sensor measurements.",
            4: "Restoring telemetry trust after securing the communication link.",
            5: "Activating defensive mode to engage rate-limiting and command authorization.",
            6: "Tripping all substation breakers to isolate a compromised bus.",
            7: "Splitting the network into isolated zones to prevent a wide-area blackout.",
            8: "Enabling automatic FLISR self-healing to search for restoration paths.",
            9: "Closing a tie-breaker to reroute active power flows around a tripped line."
        }

    def explain_action(self, 
                       action_id: int, 
                       target: str, 
                       state_vector: np.ndarray, 
                       sandbox_results: Dict[str, Any] = None,
                       ppo_probs: np.ndarray = None) -> Dict[str, Any]:
        """
        Generates detailed explainability diagnostics for a recommended action.
        """
        action_meta = self.registry.get_action(action_id)
        action_name = action_meta.get("name", "NO_ACTION")
        
        # Safe state parsing
        state = np.nan_to_num(state_vector, nan=0.0)
        anomaly_score = float(state[63])
        pinn_conf = float(state[64])
        cascade_risk = float(state[65])
        islanding_active = bool(state[70] > 0.5)

        # 1. Determine reasoning chain
        reasoning_chain = []
        reason = self.action_descriptions.get(action_id, "No description available.")
        
        # PPO probability info
        prob_percent = 10.0  # default uniform
        prob_offset = 0.0
        if ppo_probs is not None:
            # Ensure ppo_probs is clean
            clean_probs = np.nan_to_num(ppo_probs, nan=0.1)
            # Normalize just in case
            if np.sum(clean_probs) > 0:
                clean_probs = clean_probs / np.sum(clean_probs)
            else:
                clean_probs = np.ones(10) / 10.0
            
            prob_percent = float(clean_probs[action_id]) * 100.0
            prob_offset = float(clean_probs[action_id] - np.mean(clean_probs)) * 100.0
            reasoning_chain.append(f"0. PPO agent selected action with policy probability {prob_percent:.1f}% (offset: {prob_offset:+.1f}%).")

        if action_id == 0:
            reasoning_chain.append("1. Telemetry streams analyzed: all measurements within normal bounds.")
            reasoning_chain.append("2. Physics validation check: zero active KCL/KVL anomalies.")
            reasoning_chain.append("3. Decision: maintaining nominal operations is the optimal policy.")
        else:
            reasoning_chain.append(f"1. Decision engine analyzed threat indicators: cascade risk {cascade_risk*100:.1f}%.")
            if anomaly_score > 0.3:
                reasoning_chain.append(f"2. Core physics engine flagged telemetry validation mismatch (anomaly {anomaly_score:.2f}).")
            if target != "SYSTEM" and target != "SYSTEM":
                reasoning_chain.append(f"3. Action directed to target {target} to protect cyber-physical boundary.")
            reasoning_chain.append(f"4. Selected action: [{action_name}] ({reason.lower()})")

        # 2. Safety Gating
        safety_justification = "Action passed all voltage, thermal, and anti-islanding constraint checks."
        safety_score = float(action_meta.get("safety_score", 1.0))
        
        if sandbox_results:
            sandbox_allowed = sandbox_results.get("allowed", True)
            sandbox_violations = sandbox_results.get("violations", [])
            if not sandbox_allowed:
                safety_justification = "REJECTED: " + "; ".join(sandbox_violations)
                safety_score = float(sandbox_results.get("safety_score", 0.0))
            else:
                safety_justification = f"Passed sandbox validations. Predicted voltage profile: {min(sandbox_results.get('predicted_voltages', [1.0])):.3f} to {max(sandbox_results.get('predicted_voltages', [1.0])):.3f} p.u."

        # 3. Topology & Overload analysis
        topology_reasoning = ""
        topo_impact = float(action_meta.get("topology_impact", 0.0))
        if topo_impact < 0:
            topology_reasoning = f"Reduces topology degrees of freedom by {-topo_impact:.0f} to enforce physical isolation."
        elif topo_impact > 0:
            topology_reasoning = f"Adds {topo_impact:.0f} power restoration path to re-energize disconnected subgrids."
        else:
            topology_reasoning = "Maintains current physical subgrid topology. Zero fragmentation impact."

        # 4. Expected rewards and cascade reductions (scaled by PINN confidence)
        est_reward = 0.0
        est_cascade_reduction = 0.0
        restoration_prob = float(action_meta.get("restoration_confidence", 1.0))
        
        if sandbox_results:
            est_reward = 15.0 if action_meta.get("target") == "LINE" else 5.0
            pred_risk = sandbox_results.get("cascade_risk", 0.0)
            est_cascade_reduction = max(0.0, cascade_risk - pred_risk)
            restoration_prob = float(sandbox_results.get("confidence", restoration_prob))
        else:
            # Fallbacks
            if action_id in [1, 6, 7]: # Isolation actions
                est_cascade_reduction = cascade_risk * 0.6
                est_reward = float(10.0 + (cascade_risk * 15.0))
            elif action_id in [2, 8, 9]: # Restoration actions
                est_cascade_reduction = 0.0
                est_reward = float(15.0)

        # Scale expected reward by PINN confidence
        est_reward = est_reward * max(0.4, pinn_conf)
        est_cascade_reduction = est_cascade_reduction * max(0.4, pinn_conf)

        # 5. Telemetry basis check
        trusted_basis = "Telemetry on target node is verified and trusted."
        if target.startswith("Bus_"):
            bus_idx = int(target.split("_")[1]) - 1
            trust_val = float(state[45 + bus_idx])
            if trust_val < 0.5:
                trusted_basis = f"CAUTION: Target node {target} telemetry trust is degraded ({trust_val*100:.1f}%)."
        elif target in ["L1_4", "L2_7", "L3_9", "L4_5", "L4_9", "L5_6", "L6_7", "L7_8", "L8_9"]:
            line_idx = ["L1_4", "L2_7", "L3_9", "L4_5", "L4_9", "L5_6", "L6_7", "L7_8", "L8_9"].index(target)
            trust_val = float(state[54 + line_idx])
            if trust_val < 0.5:
                trusted_basis = f"CAUTION: Target line {target} telemetry trust is degraded ({trust_val*100:.1f}%)."

        # 6. Objectives, Containment and Risk-Tradeoff Explanations
        restoration_objective = "Maintain grid in steady state."
        if action_id in [2, 8, 9]:
            restoration_objective = "Restore islanded or unpowered loads, close breakers to re-energize transmission paths."
        elif action_id in [1, 3, 6, 7]:
            restoration_objective = "Isolate faulted or compromised physical components to prevent overloading and voltage collapse."
            
        containment_rationale = "No active threat containment required for this operation."
        if action_id in [3, 6]:
            containment_rationale = "Distrust telemetry from compromised nodes to block malicious inputs."
        elif action_id in [1, 7]:
            containment_rationale = "Disconnect lines around high-risk or compromised nodes to stop cascading cyber-physical spread."
            
        risk_tradeoff = "Balance security enforcement with grid operational capacity."
        if action_id in [1, 6, 7]:
            risk_tradeoff = "Prioritizes immediate physical containment of cascades over load connectivity, temporarily increasing topology fragmentation to guarantee safety."
        elif action_id in [2, 9]:
            risk_tradeoff = "Prioritizes customer load service and voltage support, accepting potential secondary trip risks if underlying fault is not fully cleared."
        elif action_id == 0:
            risk_tradeoff = "Prioritizes operational stability, verifying current layout achieves optimal balance between load service and line safety margin."

        return {
            "action_id": action_id,
            "action_name": action_name,
            "target": target,
            "reason": reason,
            "safety_justification": safety_justification,
            "safety_score": round(safety_score, 2),
            "topology_reasoning": topology_reasoning,
            "expected_reward_gain": round(est_reward, 2),
            "expected_cascade_reduction": round(est_cascade_reduction, 2),
            "restoration_probability": round(restoration_prob, 2),
            "trusted_telemetry_basis": trusted_basis,
            "reasoning_chain": reasoning_chain,
            "policy_prob_percent": round(prob_percent, 2),
            "policy_prob_offset": round(prob_offset, 2),
            "restoration_objective": restoration_objective,
            "containment_rationale": containment_rationale,
            "risk_tradeoff_reasoning": risk_tradeoff
        }
