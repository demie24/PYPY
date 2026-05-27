import numpy as np
from typing import Dict, Tuple

class RecoveryRewardEngine:
    """
    Formulates auxiliary reinforcement learning reward signals focused specifically
    on the quality of adaptive restoration sequences.
    """
    def __init__(self):
        pass

    def evaluate_restoration_quality(self, 
                                     prev_state: np.ndarray, 
                                     curr_state: np.ndarray, 
                                     action_id: int, 
                                     rollback_occurred: bool, 
                                     step_count: int) -> Tuple[float, Dict[str, float]]:
        """
        Computes the restoration quality reward.
        
        State vector mapping (same as reward_engine.py):
        - voltages: indices 0 to 8
        - islanding: index 70
        """
        details = {}
        
        prev_voltages = prev_state[0:9]
        curr_voltages = curr_state[0:9]
        
        prev_islanded = prev_state[70] > 0.5
        curr_islanded = curr_state[70] > 0.5

        # 1. Successful complete recovery
        # Transition from islanded/unstable to healthy grid (all voltages in [0.90, 1.10])
        details["reward_recovery_complete"] = 0.0
        if prev_islanded and not curr_islanded and np.all(curr_voltages > 0.90) and np.all(curr_voltages < 1.10):
            details["reward_recovery_complete"] = 50.0

        # 2. Minimized instability (voltage profile variance)
        mean_dev = np.mean(np.abs(curr_voltages - 1.0))
        details["reward_minimized_instability"] = float(20.0 * (1.0 - mean_dev))

        # 3. Reduced rollback count (harsh penalty for rollbacks)
        details["penalty_rollback_restoration"] = -25.0 if rollback_occurred else 0.0

        # 4. Faster restoration time (penalize steps taken exceeding 3)
        details["penalty_restoration_speed"] = float(-2.0 * max(0, step_count - 3))

        # 5. Minimized customer interruption (highly reward servicing load buses 5, 6, 8 -> indices 4, 5, 7)
        load_bus_indices = [4, 5, 7]
        prev_serviced = sum(prev_voltages[idx] > 0.95 for idx in load_bus_indices)
        curr_serviced = sum(curr_voltages[idx] > 0.95 for idx in load_bus_indices)
        
        # Reward keeping them energized, and extra bonus for transitions from offline to online
        details["reward_serviced_loads"] = float((curr_serviced - prev_serviced) * 15.0 + curr_serviced * 5.0)

        total_reward = sum(details.values())
        return total_reward, details
