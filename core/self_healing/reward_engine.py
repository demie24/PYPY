import numpy as np
from typing import Dict, Any, Tuple

class RewardEngine:
    def __init__(self):
        pass

    def compute_reward(self, 
                       prev_state: np.ndarray, 
                       curr_state: np.ndarray, 
                       action_id: int,
                       rollback_occurred: bool = False,
                       defense_status: Dict[str, Any] = None,
                       repeated_failed_action: bool = False,
                       step_count: int = 0) -> Tuple[float, Dict[str, float]]:
        """
        Computes an adaptive reinforcement learning reward signal based on cyber-physical transitions.
        
        State vector indices:
            - voltages: 0-8
            - angles: 9-17
            - active line flow loading: 18-26
            - reactive line flow loading: 27-35
            - breakers: 36-44
            - bus trust: 45-53
            - line trust: 54-62
            - anomaly score: 63
            - pinn confidence: 64
            - cascade risk: 65
            - flisr state: 66
            - observability: 67
            - attack probability: 68
            - threat severity: 69
            - islanding state: 70
            - override active: 71
        """
        details = {}
        
        prev_voltages = prev_state[0:9]
        curr_voltages = curr_state[0:9]
        
        prev_breakers = prev_state[36:45]
        curr_breakers = curr_state[36:45]
        
        prev_loading = prev_state[18:27]**2 + prev_state[27:36]**2
        curr_loading = curr_state[18:27]**2 + curr_state[27:36]**2
        
        prev_mean_trust = np.mean(prev_state[45:54])
        curr_mean_trust = np.mean(curr_state[45:54])
        
        # ==========================================
        # 1. ADAPTIVE VOLTAGE STABILITY REWARD
        # ==========================================
        # Scales penalties quadratically when voltages deviate further from nominal
        prev_dev = np.sum(np.maximum(0.0, 0.95 - prev_voltages)**2 + np.maximum(0.0, prev_voltages - 1.05)**2)
        curr_dev = np.sum(np.maximum(0.0, 0.95 - curr_voltages)**2 + np.maximum(0.0, curr_voltages - 1.05)**2)
        
        # Adaptive gain: larger voltage deviation = steeper penalty (scaled down for stability)
        adaptive_multiplier = 1.0 + 3.0 * curr_dev
        details["reward_stability"] = float(30.0 * (prev_dev - curr_dev) - 0.5 * curr_dev * adaptive_multiplier)
        
        # ==========================================
        # 2. RESTORATION SUCCESS REWARD
        # ==========================================
        # Transition from islanded/unstable (islanding > 0.5) to healthy grid
        prev_islanded = prev_state[70] > 0.5
        curr_islanded = curr_state[70] > 0.5
        
        details["reward_restoration_success"] = 0.0
        if prev_islanded and not curr_islanded and np.all(curr_voltages > 0.90):
            details["reward_restoration_success"] = 25.0

        # ==========================================
        # 3. TOPOLOGY PRESERVATION REWARD
        # ==========================================
        # Encourage keeping transmission lines energized. Value proportional to active breakers.
        details["reward_topology_preservation"] = float(15.0 * (np.sum(curr_breakers) / 9.0))
        
        # ==========================================
        # 4. ANTI-CASCADE REWARD
        # ==========================================
        # Reward reducing cascading risk index
        prev_risk = prev_state[65]
        curr_risk = curr_state[65]
        details["reward_anti_cascade"] = float(20.0 * max(0.0, prev_risk - curr_risk))

        # ==========================================
        # 5. TRUSTED STATE REWARD
        # ==========================================
        # Reward restoring telemetry trust
        details["reward_trusted_state"] = float(10.0 * max(0.0, curr_mean_trust - prev_mean_trust))

        # ==========================================
        # 6. OBSERVABILITY REWARD
        # ==========================================
        # Reward increasing/restoring state observability
        prev_obs = prev_state[67]
        curr_obs = curr_state[67]
        details["reward_observability"] = float(10.0 * max(0.0, curr_obs - prev_obs))

        # ==========================================
        # 7. MINIMAL CUSTOMER DISRUPTION REWARD
        # ==========================================
        # Reward keeping load buses energized (V > 0.9 pu). Load buses are at indices 4, 5, 7.
        load_bus_indices = [4, 5, 7]
        prev_serviced = sum(prev_voltages[idx] > 0.9 for idx in load_bus_indices)
        curr_serviced = sum(curr_voltages[idx] > 0.9 for idx in load_bus_indices)
        details["reward_customer_disruption"] = float((curr_serviced - prev_serviced) * 25.0 + curr_serviced * 8.0)

        # ==========================================
        # 8. POSITIVE LINE LOADING MARGINS REWARD
        # ==========================================
        # Reward keeping line flows safely below capacity limits (1.0 pu)
        curr_line_loadings = np.sqrt(curr_state[18:27]**2 + curr_state[27:36]**2)
        loading_margins = np.maximum(0.0, 1.0 - curr_line_loadings)
        details["reward_loading_margins"] = float(5.0 * np.mean(loading_margins))

        # ==========================================
        # 9. POSITIVE VOLTAGE RESTORATION REWARD
        # ==========================================
        # Reward step improvement of voltages moving closer to 1.0 pu nominal
        prev_dist = np.abs(prev_voltages - 1.0)
        curr_dist = np.abs(curr_voltages - 1.0)
        voltage_improvements = np.sum(np.maximum(0.0, prev_dist - curr_dist))
        details["reward_voltage_restoration"] = float(20.0 * voltage_improvements)

        # ==========================================
        # 9A. ANOMALY REDUCTION REWARD
        # ==========================================
        prev_anomaly = prev_state[63]
        curr_anomaly = curr_state[63]
        details["reward_anomaly_reduction"] = float(15.0 * max(0.0, prev_anomaly - curr_anomaly))

        # ==========================================
        # 9B. SURVIVAL & SAFE RECONFG REWARDS
        # ==========================================
        details["reward_safe_survival"] = 3.0 if not rollback_occurred else 0.0
        
        changed_breakers = np.sum(np.abs(curr_breakers - prev_breakers))
        details["reward_safe_breaker_action"] = 5.0 if (changed_breakers > 0.0 and not rollback_occurred) else 0.0

        # ==========================================
        # 9C. SUCCESSFUL THREAT/FAULT ISOLATION
        # ==========================================
        details["reward_successful_isolation"] = 0.0
        for i in range(9):
            if curr_breakers[i] < 0.5 and prev_breakers[i] > 0.5:
                line_trust = curr_state[54 + i]
                # If we tripped a low trust line successfully without rollback
                if line_trust < 0.5 and not rollback_occurred:
                    details["reward_successful_isolation"] = 15.0
                    break

        # ==========================================
        # 9D. SURVIVAL-FIRST: CONTAINMENT INCENTIVES
        # ==========================================
        details["reward_cyber_containment"] = 0.0
        details["penalty_premature_restoration"] = 0.0
        
        is_under_attack = curr_state[68] > 0.5 or prev_state[68] > 0.5
        if is_under_attack:
            # Containment actions (1: Isolate Line, 3: Reject Telemetry, 6: Isolate Bus)
            if action_id in [1, 3, 6]:
                # If we targeted a distrusted element (trust < 0.5)
                # Bus trust starts at 45, Line trust starts at 54
                is_degraded_target = False
                if action_id == 3 or action_id == 6:
                    # Bus action. Check if lowest bus trust is degraded
                    lowest_bus_trust = np.min(curr_state[45:54])
                    if lowest_bus_trust < 0.5:
                        is_degraded_target = True
                elif action_id == 1:
                    # Line action. Check if lowest line trust is degraded
                    lowest_line_trust = np.min(curr_state[54:63])
                    if lowest_line_trust < 0.5:
                        is_degraded_target = True
                        
                if is_degraded_target and not rollback_occurred:
                    details["reward_cyber_containment"] = 12.0
                    
            # Premature restoration actions (2: Reconnect Line, 8: Reroute Flow)
            if action_id in [2, 8] and (np.min(curr_state[45:54]) < 0.5 or np.min(curr_state[54:63]) < 0.5):
                details["penalty_premature_restoration"] = -10.0

        # ==========================================
        # 10. PENALTIES: UNSTABLE RESTORATION
        # ==========================================
        details["penalty_unstable_restoration"] = 0.0
        if np.any(curr_voltages < 0.90) or np.any(curr_voltages > 1.10):
            details["penalty_unstable_restoration"] = -5.0

        # ==========================================
        # 11. PENALTIES: OVERLOAD AMPLIFICATION
        # ==========================================
        details["penalty_overload_amplification"] = 0.0
        load_diff = np.sum(curr_loading) - np.sum(prev_loading)
        if load_diff > 0.05:
            details["penalty_overload_amplification"] = -10.0 * load_diff

        # ==========================================
        # 12. PENALTIES: UNSAFE BREAKER SWITCHING
        # ==========================================
        details["penalty_unsafe_breaker_switching"] = 0.0
        if changed_breakers > 0.0 and action_id != 0:
            details["penalty_unsafe_breaker_switching"] = -3.0

        # ==========================================
        # 13. PENALTIES: FALSE RESTORATION
        # ==========================================
        details["penalty_false_restoration"] = 0.0
        for i in range(9):
            if curr_breakers[i] > 0.5 and prev_breakers[i] < 0.5:
                line_trust = curr_state[54 + i]
                if line_trust < 0.5:
                    details["penalty_false_restoration"] = -8.0
                    break

        # ==========================================
        # 14. PENALTIES: TOPOLOGY FRAGMENTATION
        # ==========================================
        details["penalty_topology_fragmentation"] = 0.0
        if curr_islanded:
            details["penalty_topology_fragmentation"] = -5.0

        # ==========================================
        # 15. PENALTIES: CONFIDENCE COLLAPSE
        # ==========================================
        prev_conf = prev_state[64]
        curr_conf = curr_state[64]
        if prev_conf > 0.70 and curr_conf < 0.40:
            details["penalty_confidence_collapse"] = -4.0

        # ==========================================
        # 16. PENALTIES: ACTION ROLLBACK EVENT
        # ==========================================
        details["penalty_rollback_event"] = -5.0 if rollback_occurred else 0.0

        # ==========================================
        # 17. DEFENSE-AWARE REWARDS & PENALTIES
        # ==========================================
        details["reward_defense_alignment"] = 0.0
        details["penalty_defense_violation"] = 0.0
        
        if defense_status:
            is_containment = action_id in [1, 3, 6, 7]
            is_restoration = action_id in [2, 8, 9]
            
            restoration_locked = defense_status.get("restoration_lockdown_active", False)
            esc_level = defense_status.get("escalation_level", "ADVISORY")
            if esc_level in ["EMERGENCY_CONTAINMENT", "GRID_PRESERVATION"]:
                restoration_locked = True
                
            if restoration_locked and is_restoration:
                details["penalty_defense_violation"] = -10.0
                
            recommended_actions = defense_status.get("recommended_defense_actions", [])
            action_map = {
                1: "ISOLATE_LINE",
                3: "REJECT_TELEMETRY",
                6: "ISOLATE_BUS",
                7: "ENABLE_ISLANDING"
            }
            if is_containment and action_id in action_map:
                act_name = action_map[action_id]
                matching = any(rec.get("action") == act_name for rec in recommended_actions)
                if matching:
                    details["reward_defense_alignment"] = 20.0

        # Sum up total reward
        total_reward = sum(details.values())
        
        # Check against NaNs or Infs
        if not np.isfinite(total_reward):
            total_reward = -2.0
            
        return float(total_reward), details
