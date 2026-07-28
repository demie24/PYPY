import numpy as np
from typing import Dict, Any, Tuple, Set

class MissingDataSimulator:
    """
    Simulates various missing-data conditions on the 293-dimensional grid observation vector:
    A. Random sensor failures (5% to 50% mask ratios)
    B. Targeted DoS attacks on critical buses / lines
    C. MQTT packet loss (burst or random dropouts)
    D. Quarantine events (based on packet verification drops)
    """
    def __init__(self, num_buses: int = 39, num_lines: int = 46):
        self.num_buses = num_buses
        self.num_lines = num_lines

    def simulate_sensor_failure(self, true_obs: np.ndarray, mask_ratio: float) -> Tuple[np.ndarray, np.ndarray]:
        """
        Simulates random sensor failure across physical telemetry parameters (voltages, injections, loadings).
        Returns:
            masked_obs: observation with failed values replaced by default/masked entries.
            missing_mask: boolean mask indicating which parameters are missing.
        """
        masked = true_obs.copy()
        missing_mask = np.zeros_like(true_obs, dtype=bool)
        
        # Slices: 0:39 voltage, 39:78 injection, 78:124 loading
        physical_dims = 124
        
        # Determine number of features to drop
        num_dropped = int(physical_dims * mask_ratio)
        dropped_indices = np.random.choice(physical_dims, num_dropped, replace=False)
        
        for idx in dropped_indices:
            missing_mask[idx] = True
            if idx < 39:
                masked[idx] = 1.0  # default nominal voltage magnitude
            elif idx < 78:
                masked[idx] = 0.0  # default nominal injection power
            else:
                masked[idx] = 0.0  # default nominal line loading
                
        return masked, missing_mask

    def simulate_targeted_dos(self, true_obs: np.ndarray, target_buses: Set[int]) -> Tuple[np.ndarray, np.ndarray]:
        """
        Simulates targeted DoS attacks on specific critical buses.
        All telemetry from these buses (voltages, injections, and loadings of connected lines) is completely lost.
        """
        masked = true_obs.copy()
        missing_mask = np.zeros_like(true_obs, dtype=bool)
        
        for bus_id in target_buses:
            # Mask voltage
            missing_mask[bus_id] = True
            masked[bus_id] = 1.0
            
            # Mask active injection
            inj_idx = 39 + bus_id
            missing_mask[inj_idx] = True
            masked[inj_idx] = 0.0
            
        return masked, missing_mask

    def simulate_mqtt_packet_loss(self, true_obs: np.ndarray, burst_length: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Simulates burst MQTT packet loss. Entire sequences of consecutive channels drop.
        """
        masked = true_obs.copy()
        missing_mask = np.zeros_like(true_obs, dtype=bool)
        
        physical_dims = 124
        # Select start of burst
        start_idx = np.random.randint(0, max(1, physical_dims - burst_length))
        
        for idx in range(start_idx, min(physical_dims, start_idx + burst_length)):
            missing_mask[idx] = True
            if idx < 39:
                masked[idx] = 1.0
            elif idx < 78:
                masked[idx] = 0.0
            else:
                masked[idx] = 0.0
                
        return masked, missing_mask

    def simulate_quarantine(self, true_obs: np.ndarray, quarantined_buses: Set[int]) -> Tuple[np.ndarray, np.ndarray]:
        """
        Simulates quarantine events where suspicious/compromised buses have their telemetry completely sandboxed.
        """
        return self.simulate_targeted_dos(true_obs, quarantined_buses)
