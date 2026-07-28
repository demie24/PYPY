import os
import sys
import time
import copy
import random
from collections import deque
from typing import Dict, Any, Tuple, List
import numpy as np
import torch
import gymnasium as gym
from gymnasium import spaces

# Setup paths to import sibling modules
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(parent_dir)
sys.path.append(project_root)
sys.path.append(os.path.join(parent_dir, "digital_twin"))
sys.path.append(os.path.join(parent_dir, "gnn"))
sys.path.append(os.path.join(parent_dir, "consensus"))

# Import system modules
try:
    from core.digital_twin.grid_topology import GridTopology
    from core.digital_twin.physics import GridPhysicsEngine
    from core.gnn.graph_detector import GraphAnomalyDetector
    from core.gnn.propagation_detector import SpatioTemporalPropagationDetector
    from core.consensus.decision_engine import DecisionEngine
except ImportError as e:
    # Print error for visibility and raise
    print(f"PathogenEnv Import Error: {e}")
    raise e

class PathogenEnv(gym.Env):
    """
    Gymnasium Environment representing the Artificial Pathogen Engine for the IEEE 39-Bus grid.
    Attacker learns sequence attacks (FDIA, replay, DoS, Trip Line) to compromise grid stability.
    """
    def __init__(self):
        super(PathogenEnv, self).__init__()
        
        self.topo = GridTopology()
        self.physics = GridPhysicsEngine(self.topo)
        
        # Load approved detection models and consensus layer
        self.gnn_detector = GraphAnomalyDetector()
        self.stgnn_detector = SpatioTemporalPropagationDetector()
        self.decision_engine = DecisionEngine()
        
        # Map labels to consensus index
        self.consensus_states = [
            "NORMAL",
            "WARNING",
            "ANOMALY",
            "RECOVERY_REQUIRED",
            "ATTACK_CONFIRMED",
            "ISOLATE_COMPONENT"
        ]
        
        # 20-step historical node/edge features cache for ST-GNN
        self.history_nodes = deque(maxlen=20)
        self.history_edges = deque(maxlen=20)
        
        self.step_count = 0
        self.max_steps = 50
        
        # Active attacker modifications dictionary
        self.active_fdia = {}
        self.active_dos = set()
        self.active_replay = {}
        
        # Define Action Space: Dict
        # type: 0=NO_ACTION, 1=FDIA, 2=REPLAY, 3=DOS, 4=TRIP_LINE
        # target: 0..45 (maps to 39 buses or 46 lines)
        # magnitude: Continuous injection delta in [-0.20, +0.20] pu
        self.action_space = spaces.Dict({
            "type": spaces.Discrete(5),
            "target": spaces.Discrete(46),
            "magnitude": spaces.Box(low=-0.20, high=0.20, shape=(1,), dtype=np.float32)
        })
        
        # Define 293-dimensional Observation Space
        # 170 physical metrics + 123 cyber defense signals
        self.observation_space = spaces.Box(
            low=-10.0, high=10.0, shape=(293,), dtype=np.float32
        )
        
        self.reset()

    def reset(self, seed=None, options=None) -> Tuple[np.ndarray, Dict[str, Any]]:
        if seed is not None:
            random.seed(seed)
            np.random.seed(seed)
            
        self.step_count = 0
        
        # 1. Reset physical digital twin parameters
        self.breakers = {line["id"]: "CLOSED" for line in self.topo.lines}
        
        # Load baseline nominal values and add minor load fluctuations (scenario diversity)
        self.loads = {}
        for bus_idx, load in self.topo.loads.items():
            fluc = 1.0 + random.uniform(-0.05, 0.05)
            self.loads[bus_idx] = {
                "P": load["P_nom"] * fluc,
                "Q": load["Q_nom"] * fluc
            }
            
        self.gen_P = {k: v["P_nom"] for k, v in self.topo.generators.items()}
        self.gen_Q = {k: v["Q_nom"] for k, v in self.topo.generators.items()}
        
        # 2. Reset attacker states
        self.active_fdia.clear()
        self.active_dos.clear()
        self.active_replay.clear()
        
        # Initialize stateful trust scores
        self.bus_trust = {i: 1.0 for i in range(self.topo.num_buses)}
        
        # Track action and target history for multi-stage planning and anti-spam rewards
        self.action_history = deque(maxlen=10)
        self.target_history = deque(maxlen=10)
        
        # 3. Pre-populate history queue with nominal steps to warm up ST-GNN
        self.history_nodes.clear()
        self.history_edges.clear()
        
        # Solve initial state
        V, theta, P, Q, line_flows = self.physics.solve(
            self.breakers, self.loads, self.gen_P, self.gen_Q
        )
        
        for _ in range(20):
            node_feats = np.stack([P, Q, V, theta], axis=-1).astype(np.float32)
            self.history_nodes.append(node_feats)
            
            # Extract edge features
            edge_feats = self._extract_edge_features(V, theta, line_flows)
            self.history_edges.append(edge_feats)
            
        obs = self._get_observation(V, P, line_flows)
        info = {
            "status": "Nominal Reset",
            "global_decision": "NORMAL"
        }
        return obs, info

    def step(self, action: Dict[str, Any]) -> Tuple[np.ndarray, float, bool, bool, Dict[str, Any]]:
        self.step_count += 1
        
        # Extract action choices
        act_type = int(action.get("type", 0))
        act_target = int(action.get("target", 0))
        act_magnitude = float(action.get("magnitude", [0.0])[0])
        
        # 1. Process Physical Attack Actions
        # Trip Line directly affects grid breaker physics
        if act_type == 4: # TRIP_LINE
            line_idx = min(act_target, len(self.topo.lines) - 1)
            line_id = self.topo.lines[line_idx]["id"]
            self.breakers[line_id] = "OPEN"
        elif act_type == 1: # FDIA
            bus_id = min(act_target, self.topo.num_buses - 1)
            self.active_fdia[bus_id] = act_magnitude
        elif act_type == 2: # REPLAY
            bus_id = min(act_target, self.topo.num_buses - 1)
            # Replay sample from 10 steps ago in history
            self.active_replay[bus_id] = self.history_nodes[-10][bus_id, 2] if len(self.history_nodes) >= 10 else 1.0
        elif act_type == 3: # DOS
            # Block bus telemetry
            if act_target < self.topo.num_buses:
                self.active_dos.add(act_target)
            else:
                line_idx = min(act_target - self.topo.num_buses, len(self.topo.lines) - 1)
                self.active_dos.add(f"line_{line_idx}")

        # 2. Solve Physical Power Flow Solver (Ground Truth)
        blackout = False
        try:
            V, theta, P, Q, line_flows = self.physics.solve(
                self.breakers, self.loads, self.gen_P, self.gen_Q
            )
            # Rigorous Blackout Definition:
            # A. Solver completely failed to converge (status mode failed)
            solver_failed = self.physics.last_solver_status.get("mode") == "failed"
            
            # B. Voltage collapse on multiple buses (>30% of buses drop below 0.70 pu)
            voltage_collapse = np.sum(V < 0.70) > (0.30 * self.topo.num_buses)
            
            # C. Total active power load loss > 40% (meaning load served < 60% of nominal demand)
            nominal_demand = sum(load["P_nom"] for load in self.topo.loads.values())
            actual_load_served = 0.0
            for idx, row in self.physics.solver.net.load.iterrows():
                bus = int(row.bus)
                if V[bus] >= 0.50:
                    actual_load_served += float(row.p_mw) / 100.0
            
            load_shedding_blackout = (actual_load_served < 0.60 * nominal_demand)
            
            if solver_failed or voltage_collapse or load_shedding_blackout:
                blackout = True
        except Exception:
            # AC Solver failed to converge or other error = voltage collapse / blackout
            blackout = True

        if blackout:
            V = np.zeros(self.topo.num_buses)
            theta = np.zeros(self.topo.num_buses)
            P = np.zeros(self.topo.num_buses)
            Q = np.zeros(self.topo.num_buses)
            line_flows = {line["id"]: {"P_flow": 0.0, "Q_flow": 0.0, "current": 0.0} for line in self.topo.lines}

        # 3. Apply Attacks to Scada Telemetry (Compromised measurements)
        scada_V = V.copy()
        scada_P = P.copy()
        
        # Inject FDIA
        for bus_id, val in self.active_fdia.items():
            scada_V[bus_id] += val
            self.bus_trust[bus_id] = max(0.0, self.bus_trust[bus_id] - 0.15) # trust decay
            
        # Inject Replay
        for bus_id, val in self.active_replay.items():
            scada_V[bus_id] = val
            self.bus_trust[bus_id] = max(0.0, self.bus_trust[bus_id] - 0.10)
            
        # Inject DoS (Telemetry freeze/defaults)
        for target in self.active_dos:
            if isinstance(target, int):
                scada_V[target] = 1.0
                scada_P[target] = 0.0
                self.bus_trust[target] = max(0.0, self.bus_trust[target] - 0.05)

        # 4. Update ST-GNN Telemetry Buffers
        node_feats = np.stack([scada_P, Q, scada_V, theta], axis=-1).astype(np.float32)
        edge_feats = self._extract_edge_features(scada_V, theta, line_flows)
        
        self.history_nodes.append(node_feats)
        self.history_edges.append(edge_feats)

        # 5. Run Cybersecurity Defense Detection (PINN, GNN, ST-GNN, Consensus)
        # Static GNN dynamic risks
        gnn_node_risk, gnn_edge_risk = self.gnn_detector.risk_scores(node_feats)
        gnn_class = self.gnn_detector.classification(node_feats)
        
        # ST-GNN forecasting
        # Combine historical sequence to (1, 20, 39, 4)
        seq_nodes_t = torch.tensor(np.array(self.history_nodes), dtype=torch.float32).unsqueeze(0)
        seq_edges_t = torch.tensor(np.array(self.history_edges), dtype=torch.float32).unsqueeze(0)
        
        with torch.no_grad():
            stgnn_node_risk_t, stgnn_edge_risk_t = self.stgnn_detector.model(seq_nodes_t, seq_edges_t)
            stgnn_node_risk = stgnn_node_risk_t.squeeze(0).cpu().numpy()
            
        # Calculate algebraic physics anomalies (PINN mock validation score)
        mismatch_violations = 0
        for i in range(self.topo.num_buses):
            # Compute rough node injection mismatch
            if scada_V[i] < 0.88 or scada_V[i] > 1.12:
                mismatch_violations += 1
        pinn_validity = max(0.0, 1.0 - (mismatch_violations * 0.10))

        # Pack outputs for Consensus Engine
        pinn_outputs = {"physics_validation_score": pinn_validity, "physics_violations": []}
        lstm_outputs = {"anomaly_probability": 0.80 if act_type > 0 else 0.10, "predicted_attack_class": gnn_class}
        # Convert arrays to dicts for regional agents compatibility
        gnn_risk_dict = {i: float(gnn_node_risk[i]) for i in range(len(gnn_node_risk))}
        stgnn_risk_dict = {i: float(stgnn_node_risk[i]) for i in range(len(stgnn_node_risk))}

        gnn_outputs = {"criticality_scores": gnn_risk_dict, "topology_risk_scores": gnn_risk_dict}
        stgnn_outputs = {"future_node_risk": stgnn_risk_dict}

        consensus_res = self.decision_engine.evaluate(
            pinn_outputs, lstm_outputs, gnn_outputs, stgnn_outputs
        )
        global_decision = consensus_res["decision"]
        global_threat_score = consensus_res["threat_score"]

        # 6. Simulate Defensive Self-Healing Response
        if global_decision == "ISOLATE_COMPONENT":
            # Isolate the highest GNN risk node in the system
            worst_bus = int(np.argmax(gnn_node_risk))
            # Open adjacent breakers
            for line in self.topo.lines:
                if line["from"] == worst_bus or line["to"] == worst_bus:
                    self.breakers[line["id"]] = "OPEN"
        elif global_decision == "RECOVERY_REQUIRED":
            # Reconnect one tripped line to restore service
            for lid, state in self.breakers.items():
                if state == "OPEN" and lid != "L7_8":
                    self.breakers[lid] = "CLOSED"
                    break

        # Update action and target histories
        self.action_history.append(act_type)
        self.target_history.append(act_target)

        # 7. Formulate Pathogen Rewards
        # Disruption: sum of voltage deviations and line loadings
        volt_dev = float(np.sum(np.abs(V - 1.0)))
        
        line_overloads = 0.0
        for lid, flow in line_flows.items():
            current = flow["current"]
            # Nominal thermal rating limit of 1.5 pu for overload checks
            if current > 1.5:
                line_overloads += (current - 1.5)

        disruption_reward = volt_dev + line_overloads

        # New Reward Components
        pos_rewards = 0.0
        neg_penalties = 0.0

        # A. Positive Rewards
        # 1. Blackout success (scaled down to prevent brute-force dominance)
        if blackout:
            pos_rewards += 50.0

        # 2. Consensus bypass: blackout achieved without triggering severe consensus states
        if blackout and global_decision not in ["ATTACK_CONFIRMED", "ISOLATE_COMPONENT"]:
            pos_rewards += 25.0

        # 3. Remaining undetected (stealth bonus)
        if global_decision == "NORMAL":
            pos_rewards += 10.0
        elif global_decision in ["WARNING", "ANOMALY"]:
            pos_rewards += 5.0

        # 4. Stealth preservation (no trust decay)
        trust_decay = float(np.sum([1.0 - t for t in self.bus_trust.values()]))
        if trust_decay == 0.0:
            pos_rewards += 5.0

        # 5. Delayed multi-stage attack sequence bonus (TRIP_LINE -> NO_ACTION -> FDIA or REPLAY)
        if len(self.action_history) >= 3:
            # check: action_history[-3] == 4 (TRIP), action_history[-2] == 0 (NO_ACTION/WAIT), action_history[-1] in [1, 2] (FDIA/REPLAY)
            if self.action_history[-3] == 4 and self.action_history[-2] == 0 and self.action_history[-1] in [1, 2]:
                pos_rewards += 15.0

        # B. Negative Penalties
        # 1. PINN detection penalty (number of voltage violations)
        neg_penalties += -10.0 * mismatch_violations

        # 2. LSTM detection (based on threat score threshold)
        if global_threat_score > 0.5:
            neg_penalties += -10.0

        # 3. Consensus escalation
        if global_decision == "ANOMALY":
            neg_penalties += -10.0
        elif global_decision == "ATTACK_CONFIRMED":
            neg_penalties += -20.0
        elif global_decision == "ISOLATE_COMPONENT":
            neg_penalties += -30.0

        # 4. Brute-force repeated attacks (same action repeated 3 times consecutively)
        if len(self.action_history) >= 3:
            if self.action_history[-1] == self.action_history[-2] == self.action_history[-3] and self.action_history[-1] != 0:
                neg_penalties += -15.0

        # 5. Excessive line tripping (more than 3 lines tripped in the same episode)
        tripped_lines_count = sum(1 for state in self.breakers.values() if state == "OPEN")
        if tripped_lines_count > 3:
            neg_penalties += -15.0

        # 6. Repeated targeting of same asset within last 3 steps
        if len(self.target_history) >= 2:
            last_target = self.target_history[-1]
            # Check how many times it occurred in last 3 target steps
            recent_targets = list(self.target_history)[-3:]
            if recent_targets.count(last_target) > 1 and act_type != 0:
                neg_penalties += -5.0

        effort_cost = 0.2 if act_type > 0 else 0.0

        reward = (
            1.0 * disruption_reward +
            pos_rewards +
            neg_penalties -
            effort_cost
        )
        
        # 8. Check Termination
        terminated = False
        if blackout:
            terminated = True
        elif self.step_count >= self.max_steps:
            terminated = True
            
        truncated = False
        
        # Compile next observation vector
        next_obs = self._get_observation(V, P, line_flows, gnn_node_risk, stgnn_node_risk, global_decision)
        
        info = {
            "global_decision": global_decision,
            "threat_score": global_threat_score,
            "blackout": blackout,
            "step": self.step_count,
            "disruption": disruption_reward
        }
        
        return next_obs, float(reward), terminated, truncated, info

    def _extract_edge_features(self, V: np.ndarray, theta: np.ndarray, line_flows: dict) -> np.ndarray:
        """
        Extracts consistent edge features array matching v9.5 models.
        """
        edge_feats_list = []
        for line in self.topo.lines:
            lid = line["id"]
            flow = line_flows.get(lid, {"P_flow": 0.0, "Q_flow": 0.0, "current": 0.0})
            
            p_fl = flow.get("P_flow", 0.0)
            q_fl = flow.get("Q_flow", 0.0)
            curr = flow.get("current", 0.0)
            
            # Tripped status
            tripped = 1.0 if self.breakers[lid] == "OPEN" else 0.0
            
            # Line vs Trafo flag
            is_trafo = 1.0 if "trafo" in lid else 0.0
            is_line = 1.0 if "line" in lid else 0.0
            
            edge_feats_list.append([p_fl, q_fl, curr / 1.5, is_line, is_trafo])
            
        return np.array(edge_feats_list, dtype=np.float32)

    def _get_observation(self, 
                         V: np.ndarray, 
                         P: np.ndarray, 
                         line_flows: dict, 
                         gnn_risk: np.ndarray = None, 
                         stgnn_risk: np.ndarray = None, 
                         consensus_decision: str = "NORMAL") -> np.ndarray:
        """
        Packs physical and cyber states into a flat 293-dimensional vector.
        """
        # 1. Voltages (39)
        voltages = V.copy()
        
        # 2. Injections (39)
        injections = P.copy()
        
        # 3. Line loadings (46)
        loadings = []
        for line in self.topo.lines:
            flow = line_flows.get(line["id"], {"current": 0.0})
            loadings.append(flow["current"])
        loadings = np.array(loadings)
        
        # 4. Breaker states (46)
        breakers_vec = np.array([1.0 if self.breakers[l["id"]] == "CLOSED" else 0.0 for l in self.topo.lines])
        
        # 5. GNN Risk Scores (39)
        if gnn_risk is None:
            gnn_risk = np.zeros(self.topo.num_buses)
            
        # 6. ST-GNN Risk Forecast (39)
        if stgnn_risk is None:
            stgnn_risk = np.zeros(self.topo.num_buses)
            
        # 7. Bus trust scores (39)
        trust_vec = np.array([self.bus_trust[i] for i in range(self.topo.num_buses)])
        
        # 8. Consensus state (6)
        one_hot_consensus = np.zeros(len(self.consensus_states))
        if consensus_decision in self.consensus_states:
            idx = self.consensus_states.index(consensus_decision)
            one_hot_consensus[idx] = 1.0
            
        # Stack to 293 dims
        obs = np.concatenate([
            voltages,
            injections,
            loadings,
            breakers_vec,
            gnn_risk,
            stgnn_risk,
            trust_vec,
            one_hot_consensus
        ]).astype(np.float32)
        
        return obs
