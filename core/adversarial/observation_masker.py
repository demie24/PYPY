import numpy as np
from typing import Dict, Any, Tuple

class ObservationMasker:
    """
    Observation Masker supporting Mode A, B, C, D observability rules,
    adaptive visibility function calculations, and Gaussian noise injection.
    """
    def __init__(self, num_buses: int = 39, num_lines: int = 46):
        self.num_buses = num_buses
        self.num_lines = num_lines
        
        # Base observation dims mapping
        # 1. voltages (39)
        # 2. injections (39)
        # 3. loadings (46)
        # 4. breakers (46)
        # 5. gnn_risk (39)
        # 6. stgnn_risk (39)
        # 7. trust (39)
        # 8. consensus (6)
        # Total = 293

    def apply_mask(
        self,
        true_obs: np.ndarray,
        mode: str,
        visibility: float,
        compromised_buses: set,
        active_dos: set
    ) -> np.ndarray:
        """
        Applies masking and noise constraints on the 293-dimensional observation.
        """
        obs = true_obs.copy()
        
        # Slice ranges
        voltages = obs[0:39]
        injections = obs[39:78]
        loadings = obs[78:124]
        breakers = obs[124:170]
        gnn_risk = obs[170:209]
        stgnn_risk = obs[209:248]
        trust = obs[248:287]
        consensus = obs[287:293]

        if mode == "A":
            # 100% visibility, no noise
            return obs

        elif mode == "B":
            # 50% visibility + noise (sigma = 0.01)
            # Mask out cyber layers (trust, gnn_risk, stgnn_risk, consensus)
            gnn_risk.fill(0.0)
            stgnn_risk.fill(0.0)
            trust.fill(0.0)
            consensus.fill(0.0)
            
            # Inject noise on raw telemetry parameters
            sigma = 0.01
            # Apply DoS scaling
            if len(active_dos) > 0:
                sigma += 0.005 * len(active_dos)
            
            # Apply trust decay noise modifier (if average trust drops, noise increases)
            avg_trust = np.mean(true_obs[248:287])
            sigma += 0.01 * (1.0 - avg_trust)
            
            # Add Gaussian noise
            voltages += np.random.normal(0, sigma, size=39)
            injections += np.random.normal(0, sigma, size=39)
            loadings += np.random.normal(0, sigma, size=46)

        elif mode == "C":
            # 20% visibility + noise (sigma = 0.03)
            # Mask out cyber layers
            gnn_risk.fill(0.0)
            stgnn_risk.fill(0.0)
            trust.fill(0.0)
            consensus.fill(0.0)
            
            # Attacker only observes values at compromised buses
            uncompromised_mask = np.array([i not in compromised_buses for i in range(39)])
            
            voltages[uncompromised_mask] = 1.0 # default voltage
            injections[uncompromised_mask] = 0.0 # default injection
            
            # Loadings masked for uncompromised nodes (use default)
            loadings.fill(0.0)
            
            # Hide non-adjacent line breaker states
            # Simple rule: keep breaker states only if they connect to compromised buses
            # (In simulation, we can zero out or use 1.0 CLOSED as default)
            
            sigma = 0.03
            if len(active_dos) > 0:
                sigma += 0.01 * len(active_dos)
                
            # Add Gaussian noise
            voltages += np.random.normal(0, sigma, size=39)
            injections += np.random.normal(0, sigma, size=39)

        elif mode == "D":
            # Black Box: Adjacency/topology only. Mask all telemetry.
            voltages.fill(1.0)
            injections.fill(0.0)
            loadings.fill(0.0)
            breakers.fill(1.0)
            gnn_risk.fill(0.0)
            stgnn_risk.fill(0.0)
            trust.fill(0.0)
            consensus.fill(0.0)

        # Re-pack observation vector
        masked_obs = np.concatenate([
            voltages,
            injections,
            loadings,
            breakers,
            gnn_risk,
            stgnn_risk,
            trust,
            consensus
        ]).astype(np.float32)

        return masked_obs
