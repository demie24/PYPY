import numpy as np
from typing import Dict, Any, Tuple

class ReconnaissanceEngine:
    """
    Subsystem simulating attacker active scanning probes (SCAN_BUS, SCAN_LINE, PROBE_DEVICE).
    Computes noise reductions and returns Shannon Information Gain (IG).
    """
    def __init__(self, num_buses: int = 39):
        self.num_buses = num_buses
        
        # Track uncertainty standard deviations for each bus parameters: bus -> variance
        # Initialize default variance (state entropy indicator)
        self.bus_variances = np.ones(num_buses) * 0.15 # baseline high entropy prior

    def execute_scan(self, action_type: int, target: int, true_state: np.ndarray) -> Dict[str, Any]:
        """
        Executes active reconnaissance and updates variance tracking.
        Returns telemetry estimate, local uncertainty, and Information Gain (IG).
        """
        # SCAN_BUS (Discrete Action Code 5)
        # SCAN_LINE (Discrete Action Code 6)
        # PROBE_DEVICE (Discrete Action Code 7)
        
        ig = 0.0
        estimate = 0.0
        
        if action_type == 5: # SCAN_BUS
            bus_id = min(target, self.num_buses - 1)
            true_v = true_state[bus_id]
            
            # Calculate information gain (IG = H_before - H_after)
            # Shannon Entropy for Gaussian: H = 0.5 * ln(2 * pi * e * var)
            var_before = self.bus_variances[bus_id]
            var_after = max(0.001, var_before * 0.20) # 80% reduction in variance
            
            ig = 0.5 * np.log(var_before / var_after)
            
            # Update local state tracking
            self.bus_variances[bus_id] = var_after
            
            # Formulate noisy telemetry estimate
            estimate = true_v + np.random.normal(0, np.sqrt(var_after))
            
        elif action_type == 6: # SCAN_LINE
            # Targets line breaker directly, return binary info (no variance update needed)
            ig = 0.20
            estimate = 1.0 # Breaker CLOSED estimation
            
        elif action_type == 7: # PROBE_DEVICE
            bus_id = min(target, self.num_buses - 1)
            var_before = self.bus_variances[bus_id]
            var_after = max(0.0005, var_before * 0.10) # 90% reduction
            ig = 0.5 * np.log(var_before / var_after)
            self.bus_variances[bus_id] = var_after
            estimate = float(true_state[248 + bus_id]) # Return exact trust score estimate

        return {
            "estimated_state": float(estimate),
            "uncertainty": float(self.bus_variances[target] if target < self.num_buses else 0.01),
            "information_gain": float(ig)
        }

    def reset(self) -> None:
        """
        Resets entropy trackers.
        """
        self.bus_variances.fill(0.15)
