import os
import sys
import numpy as np
import random
from typing import Dict, Any, Tuple

# Setup paths
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(project_root)

from core.adversarial.pathogen_env import PathogenEnv
from core.adversarial.observation_masker import ObservationMasker
from core.adversarial.reconnaissance_engine import ReconnaissanceEngine
from core.adversarial.concurrent_attack_engine import ConcurrentAttackEngine

class ImperfectPathogenEnv(PathogenEnv):
    """
    Imperfect Pathogen Gym Environment wrapping PathogenEnv for POMDP evaluation.
    Integrates dynamic visibility filters, observation masking, and active scanning.
    Supports both SEQUENTIAL and CONCURRENT attack campaigns.
    """
    def __init__(self, mode: str = "B"):
        self.mode = mode
        self.masker = ObservationMasker()
        self.recon_engine = ReconnaissanceEngine()
        
        super(ImperfectPathogenEnv, self).__init__()
        
        self.campaign_mode = "SEQUENTIAL" # Can be set to "CONCURRENT"
        self.concurrent_engine = ConcurrentAttackEngine(self.topo)
        
        # State tracking
        self.visibility = 0.50 if mode == "B" else (0.20 if mode == "C" else (0.0 if mode == "D" else 1.0))
        self.compromised_buses = set([25]) # Start with Bus 25 compromised
        
        # Compounding alert parameter
        self.consecutive_scans_k = 1.0
        
        # Action space expansion to support recon choices
        # Action is dict: type (0-7), target (0-45), magnitude [-0.2, 0.2]
        # Action Types:
        # 0: NO_ACTION, 1: FDIA, 2: REPLAY, 3: DOS, 4: TRIP_LINE
        # 5: SCAN_BUS, 6: SCAN_LINE, 7: PROBE_DEVICE

    def reset(self, seed=None, options=None) -> Tuple[np.ndarray, Dict[str, Any]]:
        self.visibility = 0.50 if self.mode == "B" else (0.20 if self.mode == "C" else (0.0 if self.mode == "D" else 1.0))
        self.compromised_buses = set([25])
        self.consecutive_scans_k = 1.0
        self.recon_engine.reset()
        
        true_obs, info = super(ImperfectPathogenEnv, self).reset(seed=seed, options=options)
        self.last_true_obs = true_obs
        
        # Apply observation masking
        masked_obs = self.masker.apply_mask(
            true_obs=true_obs,
            mode=self.mode,
            visibility=self.visibility,
            compromised_buses=self.compromised_buses,
            active_dos=self.active_dos
        )
        
        return masked_obs, info

    def step(self, action: Dict[str, Any]) -> Tuple[np.ndarray, float, bool, bool, Dict[str, Any]]:
        act_type = int(action.get("type", 0))
        act_target = int(action.get("target", 0))
        act_magnitude = float(action.get("magnitude", [0.0])[0])
        
        # Default parameters
        info_gain = 0.0
        recon_cost = 0.0
        alert_triggered = False
        
        # Handle active scanning/recon actions directly
        is_recon = act_type in [5, 6, 7]
        
        # Grab pre-step state reference
        true_state = self.last_true_obs
        
        if is_recon:
            # 1. Execute scanning logic
            res = self.recon_engine.execute_scan(act_type, act_target, true_state)
            info_gain = res["information_gain"]
            
            # Map recon costs
            if act_type == 5:
                recon_cost = 1.5
                p_base = 0.05
            elif act_type == 6:
                recon_cost = 2.0
                p_base = 0.02
            else: # 7
                recon_cost = 4.0
                p_base = 0.15
                
            # 2. Calculate Compounding Alert Probability
            p_detect = 1.0 - (1.0 - p_base) ** self.consecutive_scans_k
            self.consecutive_scans_k += 1.0
            
            if random.random() < p_detect:
                alert_triggered = True
                # Penalize trust score of target bus
                bus_id = min(act_target, self.topo.num_buses - 1)
                self.bus_trust[bus_id] = max(0.0, self.bus_trust[bus_id] - 0.15)
                
            # Convert action to wait/no-action on physical grid
            exec_action = {"type": 0, "target": 0, "magnitude": np.array([0.0], dtype=np.float32)}
        else:
            # Cool down consecutive scans parameter
            self.consecutive_scans_k = max(1.0, self.consecutive_scans_k * 0.85)
            
            if self.campaign_mode == "CONCURRENT" and act_type > 0:
                # Resolve SOM community and trigger simultaneous multi-target attack
                som_res = self.concurrent_engine.som_engine.cluster_grid(2, 2)
                
                if act_type == 4: # TRIP_LINE
                    line_idx = min(act_target, len(self.topo.lines) - 1)
                    line_id = self.topo.lines[line_idx]["id"]
                    comm_id = som_res["line_clusters"][line_id]
                    
                    planner_res = self.concurrent_engine.plan_optimal_attack(
                        community_id=comm_id, num_targets=3, attack_type="TRIP_LINE"
                    )
                    # Open breakers for all planned target lines
                    for lid in planner_res["targets"]:
                        self.breakers[lid] = "OPEN"
                else:
                    bus_id = min(act_target, self.topo.num_buses - 1)
                    comm_id = som_res["bus_clusters"][bus_id]
                    
                    attack_type_str = "FDIA" if act_type == 1 else ("Replay" if act_type == 2 else "DoS")
                    planner_res = self.concurrent_engine.plan_optimal_attack(
                        community_id=comm_id, num_targets=3, attack_type=attack_type_str
                    )
                    # Apply concurrent cyber attacks
                    for b in planner_res["targets"]:
                        if act_type == 1: # FDIA
                            self.active_fdia[b] = act_magnitude
                            if b not in self.compromised_buses and random.random() < 0.30:
                                self.compromised_buses.add(b)
                        elif act_type == 2: # REPLAY
                            self.active_replay[b] = self.history_nodes[-10][b, 2] if len(self.history_nodes) >= 10 else 1.0
                        elif act_type == 3: # DoS
                            self.active_dos.add(b)
                            
                # Execute action as wait/no-action on physical grid since we applied targets concurrently
                exec_action = {"type": 0, "target": 0, "magnitude": np.array([0.0], dtype=np.float32)}
            else:
                exec_action = action
                # Successful compromised bus infection check (Sequential)
                if act_type == 1 and act_target not in self.compromised_buses:
                    if random.random() < 0.30:
                        self.compromised_buses.add(act_target)
            
        # Step ground-truth physics environment
        next_true_obs, reward, terminated, truncated, step_info = super(ImperfectPathogenEnv, self).step(exec_action)
        self.last_true_obs = next_true_obs
        
        # 3. Calibrated Dynamic Visibility Updates (Warfare Model)
        g_gain = 0.0
        if is_recon:
            # Diminishing returns on repeated scans
            g_gain = 0.15 / (1.0 + 0.2 * self.consecutive_scans_k)
            
        d_loss = 0.0
        decision = step_info.get("global_decision", "NORMAL")
        
        # Defender Countermeasures
        if decision in ["WARNING", "ANOMALY"]:
            d_loss += 0.15  # Firewall activation
        elif decision in ["ATTACK_CONFIRMED", "ISOLATE_COMPONENT"]:
            d_loss += 0.25  # Node isolation
            
        # Trust degradation penalty
        low_trust_buses = sum(1 for v in self.bus_trust.values() if v < 0.8)
        d_loss += 0.05 * low_trust_buses
        
        # Update visibility dynamics
        self.visibility = float(np.clip(self.visibility * (1.0 + g_gain) - d_loss, 0.0, 1.0))
        
        # 4. Calibrated Reward Rebalancing
        calibrated_reward = 0.20 * reward  # Scale down large raw physics penalties
        
        # Stealth reward
        if decision == "NORMAL":
            calibrated_reward += 9.0
            
        # Recon costs and information gains
        calibrated_reward = calibrated_reward - recon_cost + 4.5 * info_gain
        
        # Alert penalties
        if alert_triggered:
            calibrated_reward -= 15.0
            
        # Blackout success incentive
        if step_info.get("blackout", False):
            calibrated_reward += 200.0
            
        step_info["visibility"] = self.visibility
        step_info["information_gain"] = info_gain
        
        return self.apply_mask_only(next_true_obs), float(calibrated_reward), terminated, truncated, step_info

    def apply_mask_only(self, true_obs: np.ndarray) -> np.ndarray:
        return self.masker.apply_mask(
            true_obs=true_obs,
            mode=self.mode,
            visibility=self.visibility,
            compromised_buses=self.compromised_buses,
            active_dos=self.active_dos
        )

