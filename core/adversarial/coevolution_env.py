import os
import sys
import copy
import random
import torch
import numpy as np
from typing import Dict, Any, Tuple, List

# Setup paths to import sibling modules
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(parent_dir)
sys.path.append(project_root)

from core.adversarial.pathogen_env import PathogenEnv
from core.adversarial.immune_memory import ImmuneMemory

class CoevolutionEnv(PathogenEnv):
    """
    Multi-Agent Gym Environment wrapping PathogenEnv for competitive co-evolution.
    Supports joint actions {"red": red_action, "blue": blue_action}.
    """
    def __init__(self):
        # Initialize attributes before super().__init__() because super().__init__() calls self.reset()
        self.quarantined_buses = set()
        self.isolated_buses = set()
        self.immune_memory = ImmuneMemory()
        self.enable_confidence_filter = True
        
        # Track initial nominal demand placeholder, will be set after super().__init__()
        self.nominal_demand = 0.0
        self.V_nom = np.ones(39)
        self.P_nom = np.zeros(39)
        
        super(CoevolutionEnv, self).__init__()
        
        # Track initial nominal demand for load shedding metrics
        self.nominal_demand = sum(load["P_nom"] for load in self.topo.loads.values())
        
        # Track nominal P/V states for deviations calculation
        # Solve initial nominal grid state to store reference
        try:
            breakers_closed = {line["id"]: "CLOSED" for line in self.topo.lines}
            loads_nom = {k: {"P": v["P_nom"], "Q": v["Q_nom"]} for k, v in self.topo.loads.items()}
            gen_P_nom = {k: v["P_nom"] for k, v in self.topo.generators.items()}
            gen_Q_nom = {k: v["Q_nom"] for k, v in self.topo.generators.items()}
            self.V_nom, _, self.P_nom, _, _ = self.physics.solve(
                breakers_closed, loads_nom, gen_P_nom, gen_Q_nom
            )
        except Exception:
            self.V_nom = np.ones(self.topo.num_buses)
            self.P_nom = np.zeros(self.topo.num_buses)

    def reset(self, seed=None, options=None) -> Tuple[Dict[str, np.ndarray], Dict[str, Any]]:
        # Ensure collections exist
        if not hasattr(self, 'quarantined_buses'):
            self.quarantined_buses = set()
        if not hasattr(self, 'isolated_buses'):
            self.isolated_buses = set()
        if not hasattr(self, 'immune_memory'):
            self.immune_memory = ImmuneMemory()
            
        self.last_decision = "NORMAL"
        self.last_threat_score = 0.1
            
        # Reset parent env states
        red_obs, info = super(CoevolutionEnv, self).reset(seed=seed, options=options)
        
        self.quarantined_buses.clear()
        self.isolated_buses.clear()
        
        # Compute deviation vector
        if hasattr(self, 'V_nom') and hasattr(self, 'P_nom'):
            V_dev = red_obs[0:39] - self.V_nom
            P_dev = red_obs[39:78] - self.P_nom
        else:
            V_dev = np.zeros(39)
            P_dev = np.zeros(39)
            
        loadings = red_obs[78:124]
        X_dev = np.concatenate([V_dev, P_dev, loadings]).astype(np.float32)
        
        # Query Immune Memory
        recall_flags, _ = self.immune_memory.query(X_dev)
        
        # Concatenate recall flags (6 dims) to build Blue Agent observation
        blue_obs = np.concatenate([red_obs, recall_flags]).astype(np.float32)
        
        obs_dict = {
            "red": red_obs,
            "blue": blue_obs
        }
        
        return obs_dict, info

    def step(self, action_dict: Dict[str, Any]) -> Tuple[Dict[str, np.ndarray], Dict[str, float], bool, bool, Dict[str, Any]]:
        """
        Executes a joint step where Red attacks and Blue mitigates.
        Args:
            action_dict: {"red": red_action, "blue": blue_action}
        """
        self.step_count += 1
        
        red_action = action_dict.get("red", {"type": 0, "target": 0, "magnitude": np.array([0.0], dtype=np.float32)})
        blue_action = action_dict.get("blue", {"type": 0, "target": 0})
        
        red_type = int(red_action.get("type", 0))
        red_target = int(red_action.get("target", 0))
        red_magnitude = float(red_action.get("magnitude", [0.0])[0])
        
        blue_type = int(blue_action.get("type", 0))
        blue_target = int(blue_action.get("target", 0))
        
        # --- 1. APPLY ATTACKS (Red Agent Actions) ---
        if red_type == 4: # TRIP_LINE
            line_idx = min(red_target, len(self.topo.lines) - 1)
            line_id = self.topo.lines[line_idx]["id"]
            self.breakers[line_id] = "OPEN"
        elif red_type == 1: # FDIA
            bus_id = min(red_target, self.topo.num_buses - 1)
            # If not quarantined, inject
            if bus_id not in self.quarantined_buses:
                self.active_fdia[bus_id] = red_magnitude
        elif red_type == 2: # REPLAY
            bus_id = min(red_target, self.topo.num_buses - 1)
            if bus_id not in self.quarantined_buses:
                self.active_replay[bus_id] = self.history_nodes[-10][bus_id, 2] if len(self.history_nodes) >= 10 else 1.0
        elif red_type == 3: # DOS
            if red_target < self.topo.num_buses:
                if red_target not in self.quarantined_buses:
                    self.active_dos.add(red_target)
            else:
                line_idx = min(red_target - self.topo.num_buses, len(self.topo.lines) - 1)
                self.active_dos.add(f"line_{line_idx}")

        # --- 2. APPLY MITIGATIONS (Blue Agent Actions) ---
        defense_cost = 0.0
        successful_mitigation_bonus = 0.0
        false_alarm_penalty = 0.0
        recovery_bonus = 0.0
        
        # Flag to track if Blue action was a false alarm
        is_attack_active = (red_type > 0 and red_target == blue_target) or \
                           (blue_target in self.active_fdia) or \
                           (blue_target in self.active_replay) or \
                           (blue_target in self.active_dos)
                           
        # Confidence-based isolation check
        if self.enable_confidence_filter and blue_type in [2, 3] and len(self.history_nodes) > 0:
            bus_id = min(blue_target, self.topo.num_buses - 1)
            
            # 1. GNN detector agreement
            gnn_risk, _ = self.gnn_detector.risk_scores(self.history_nodes[-1])
            gnn_agree = gnn_risk[bus_id] > 0.5
            
            # 2. PINN detector agreement (voltage deviation)
            pinn_agree = abs(self.history_nodes[-1][bus_id, 2] - 1.0) > 0.05
            
            # 3. Trust Score agreement
            trust_agree = self.bus_trust[bus_id] < 0.8
            
            # 4. Consensus Layer agreement
            consensus_agree = (self.last_decision in ["WARNING", "ANOMALY", "ATTACK_CONFIRMED", "ISOLATE_COMPONENT"]) or (self.last_threat_score > 0.4)
            
            agreements = sum([int(gnn_agree), int(pinn_agree), int(trust_agree), int(consensus_agree)])
            
            if agreements < 2:
                # Reject command: Convert to NO_ACTION (type 0)
                blue_type = 0
        
        if blue_type == 1: # ISSUE_WARNING
            defense_cost += 0.5
        elif blue_type == 2: # QUARANTINE_TELEMETRY
            bus_id = min(blue_target, self.topo.num_buses - 1)
            self.quarantined_buses.add(bus_id)
            # Purge active attacks on that bus
            if bus_id in self.active_fdia:
                self.active_fdia.pop(bus_id)
            if bus_id in self.active_replay:
                self.active_replay.pop(bus_id)
            if bus_id in self.active_dos:
                self.active_dos.remove(bus_id)
            
            defense_cost += 1.0
            if is_attack_active:
                successful_mitigation_bonus += 30.0
            else:
                false_alarm_penalty += 10.0
                
        elif blue_type == 3: # ISOLATE_BUS
            bus_id = min(blue_target, self.topo.num_buses - 1)
            self.isolated_buses.add(bus_id)
            # Open adjacent breakers physically to isolate bus
            for line in self.topo.lines:
                if line["from"] == bus_id or line["to"] == bus_id:
                    self.breakers[line["id"]] = "OPEN"
            
            defense_cost += 15.0
            if is_attack_active:
                successful_mitigation_bonus += 30.0
            else:
                false_alarm_penalty += 25.0
                
        elif blue_type == 4: # RECONNECT_LINE
            # Target maps to line index: target - 39
            line_idx = min(max(0, blue_target - 39), len(self.topo.lines) - 1)
            line_id = self.topo.lines[line_idx]["id"]
            if self.breakers[line_id] == "OPEN":
                self.breakers[line_id] = "CLOSED"
                recovery_bonus += 40.0
                
        elif blue_type == 5: # REROUTE_POWER
            # Scale down generation setpoints at target to relieve overload
            if blue_target in self.gen_P:
                self.gen_P[blue_target] *= 0.90
                defense_cost += 2.0
                
        elif blue_type == 6: # RESET_TRUST
            bus_id = min(blue_target, self.topo.num_buses - 1)
            if self.bus_trust[bus_id] < 0.90:
                self.bus_trust[bus_id] = 1.0
                recovery_bonus += 5.0

        # --- 3. SOLVE GRID PHYSICS (Ground Truth) ---
        blackout = False
        try:
            V, theta, P, Q, line_flows = self.physics.solve(
                self.breakers, self.loads, self.gen_P, self.gen_Q
            )
            solver_failed = self.physics.last_solver_status.get("mode") == "failed"
            voltage_collapse = np.sum(V < 0.70) > (0.30 * self.topo.num_buses)
            
            actual_load_served = 0.0
            for idx, row in self.physics.solver.net.load.iterrows():
                bus = int(row.bus)
                if V[bus] >= 0.50:
                    actual_load_served += float(row.p_mw) / 100.0
            
            load_shedding_blackout = (actual_load_served < 0.60 * self.nominal_demand)
            
            if solver_failed or voltage_collapse or load_shedding_blackout:
                blackout = True
        except Exception:
            blackout = True

        if blackout:
            V = np.zeros(self.topo.num_buses)
            theta = np.zeros(self.topo.num_buses)
            P = np.zeros(self.topo.num_buses)
            Q = np.zeros(self.topo.num_buses)
            line_flows = {line["id"]: {"P_flow": 0.0, "Q_flow": 0.0, "current": 0.0} for line in self.topo.lines}
            actual_load_served = 0.0

        # --- 4. APPLY ATTACKS TO SCADA TELEMETRY (Quarantine Override) ---
        scada_V = V.copy()
        scada_P = P.copy()
        
        # Inject FDIA (if not quarantined)
        for bus_id, val in self.active_fdia.items():
            if bus_id not in self.quarantined_buses:
                scada_V[bus_id] += val
                self.bus_trust[bus_id] = max(0.0, self.bus_trust[bus_id] - 0.15)
            
        # Inject Replay (if not quarantined)
        for bus_id, val in self.active_replay.items():
            if bus_id not in self.quarantined_buses:
                scada_V[bus_id] = val
                self.bus_trust[bus_id] = max(0.0, self.bus_trust[bus_id] - 0.10)
            
        # Inject DoS (if not quarantined)
        for target in self.active_dos:
            if isinstance(target, int):
                if target not in self.quarantined_buses:
                    scada_V[target] = 1.0
                    scada_P[target] = 0.0
                    self.bus_trust[target] = max(0.0, self.bus_trust[target] - 0.05)

        # Update ST-GNN Telemetry Buffers
        node_feats = np.stack([scada_P, Q, scada_V, theta], axis=-1).astype(np.float32)
        edge_feats = self._extract_edge_features(scada_V, theta, line_flows)
        self.history_nodes.append(node_feats)
        self.history_edges.append(edge_feats)

        # Run Cyber Defense Detectors (GNN, ST-GNN, PINN, Consensus)
        gnn_node_risk, _ = self.gnn_detector.risk_scores(node_feats)
        gnn_class = self.gnn_detector.classification(node_feats)
        
        seq_nodes_t = torch.tensor(np.array(self.history_nodes), dtype=torch.float32).unsqueeze(0)
        seq_edges_t = torch.tensor(np.array(self.history_edges), dtype=torch.float32).unsqueeze(0)
        with torch.no_grad():
            stgnn_node_risk_t, _ = self.stgnn_detector.model(seq_nodes_t, seq_edges_t)
            stgnn_node_risk = stgnn_node_risk_t.squeeze(0).cpu().numpy()
            
        mismatch_violations = 0
        for i in range(self.topo.num_buses):
            if scada_V[i] < 0.88 or scada_V[i] > 1.12:
                mismatch_violations += 1
        pinn_validity = max(0.0, 1.0 - (mismatch_violations * 0.10))

        pinn_outputs = {"physics_validation_score": pinn_validity, "physics_violations": []}
        lstm_outputs = {"anomaly_probability": 0.80 if red_type > 0 else 0.10, "predicted_attack_class": gnn_class}
        gnn_risk_dict = {i: float(gnn_node_risk[i]) for i in range(len(gnn_node_risk))}
        stgnn_risk_dict = {i: float(stgnn_node_risk[i]) for i in range(len(stgnn_node_risk))}
        gnn_outputs = {"criticality_scores": gnn_risk_dict, "topology_risk_scores": gnn_risk_dict}
        stgnn_outputs = {"future_node_risk": stgnn_risk_dict}

        consensus_res = self.decision_engine.evaluate(
            pinn_outputs, lstm_outputs, gnn_outputs, stgnn_outputs
        )
        global_decision = consensus_res["decision"]
        global_threat_score = consensus_res["threat_score"]

        # Update action and target histories
        self.action_history.append(red_type)
        self.target_history.append(red_target)

        # --- 5. CALCULATE REWARDS ---
        volt_dev = float(np.sum(np.abs(V - 1.0)))
        line_overloads = 0.0
        for lid, flow in line_flows.items():
            current = flow["current"]
            if current > 1.5:
                line_overloads += (current - 1.5)
        disruption_score = volt_dev + line_overloads

        # Red Agent Rewards (max disruption, max blackout, bypass defense)
        red_pos = 0.0
        red_neg = 0.0
        if blackout:
            red_pos += 50.0
        if blackout and global_decision not in ["ATTACK_CONFIRMED", "ISOLATE_COMPONENT"]:
            red_pos += 25.0
        if global_decision == "NORMAL":
            red_pos += 10.0
        elif global_decision in ["WARNING", "ANOMALY"]:
            red_pos += 5.0
            
        red_neg += -10.0 * mismatch_violations
        if global_threat_score > 0.5:
            red_neg += -10.0
        if global_decision == "ANOMALY":
            red_neg += -10.0
        elif global_decision == "ATTACK_CONFIRMED":
            red_neg += -20.0
        elif global_decision == "ISOLATE_COMPONENT":
            red_neg += -30.0
            
        effort_cost = 0.2 if red_type > 0 else 0.0
        red_reward = 1.0 * disruption_score + red_pos + red_neg - effort_cost

        # Blue Agent Rewards (minimize load shedding, voltages, overloads, avoid blackout, subtract cost)
        stability_reward = 0.0
        # Voltage violation penalty
        volt_viol = float(np.sum([max(0.0, 0.95 - v) + max(0.0, v - 1.05) for v in V]))
        stability_reward -= 5.0 * volt_viol
        # Thermal overload penalty
        stability_reward -= 5.0 * line_overloads
        # Load shedding penalty
        served_pct = actual_load_served / self.nominal_demand if self.nominal_demand > 0 else 1.0
        stability_reward -= 100.0 * (1.0 - served_pct)
        
        blackout_avoided_bonus = 100.0 if not blackout else 0.0
        
        # No-action nominal reward
        is_nominal = (red_type == 0 and len(self.active_fdia) == 0 and len(self.active_replay) == 0 and len(self.active_dos) == 0)
        no_action_nominal_bonus = 5.0 if (blue_type == 0 and is_nominal) else 0.0
        
        blue_reward = (
            stability_reward + 
            blackout_avoided_bonus + 
            successful_mitigation_bonus + 
            recovery_bonus +
            no_action_nominal_bonus - 
            defense_cost - 
            false_alarm_penalty
        )

        # Persist consensus decision and threat score
        self.last_decision = global_decision
        self.last_threat_score = global_threat_score

        # --- 6. CHECK TERMINATION ---
        terminated = False
        if blackout:
            terminated = True
        elif self.step_count >= self.max_steps:
            terminated = True
        truncated = False

        # --- 7. COMPILE OBSERVATIONS ---
        red_obs = self._get_observation(V, P, line_flows, gnn_node_risk, stgnn_node_risk, global_decision)
        
        # VAE Deviation query for memory
        V_dev = V - self.V_nom
        P_dev = P - self.P_nom
        loadings = np.array([line_flows.get(line["id"], {"current": 0.0})["current"] for line in self.topo.lines])
        X_dev = np.concatenate([V_dev, P_dev, loadings]).astype(np.float32)
        
        # Query Immune Memory for Blue Agent
        recall_flags, recalled_action = self.immune_memory.query(X_dev)
        blue_obs = np.concatenate([red_obs, recall_flags]).astype(np.float32)

        # Store successful defenses (if Blue mitigated successfully, reward is positive, and no blackout occurred)
        # Only store memories if: blackout == False, mitigation_success == True, false_isolation == False
        mitigation_success = (blue_type in [2, 3] and is_attack_active)
        false_isolation = (blue_type in [2, 3] and not is_attack_active)
        if not blackout and mitigation_success and not false_isolation:
            # Store in Key-Value database with quality score ranking
            self.immune_memory.store(X_dev, category=red_type, mitigation_action=blue_action, score=blue_reward)

        obs_dict = {
            "red": red_obs,
            "blue": blue_obs
        }
        reward_dict = {
            "red": float(red_reward),
            "blue": float(blue_reward)
        }
        
        info = {
            "global_decision": global_decision,
            "threat_score": global_threat_score,
            "blackout": blackout,
            "step": self.step_count,
            "disruption": disruption_score,
            "load_served_pct": served_pct,
            "recalled_action": recalled_action
        }

        return obs_dict, reward_dict, terminated, truncated, info
