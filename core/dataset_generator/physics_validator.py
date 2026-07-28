import numpy as np
from typing import Dict, List, Tuple

def validate_physics(P: np.ndarray, Q: np.ndarray, V: np.ndarray, theta: np.ndarray) -> Tuple[bool, List[str]]:
    """
    Validates the physical feasibility of an AC power system state.
    Inputs:
        P (np.ndarray): Nodal active injections in MW (39 elements).
        Q (np.ndarray): Nodal reactive injections in Mvar (39 elements).
        V (np.ndarray): Voltage magnitudes in p.u. (39 elements).
        theta (np.ndarray): Voltage angles in radians (39 elements).
    Returns:
        is_valid (bool): True if sample is physically valid.
        reasons (list): List of error strings if invalid.
    """
    reasons = []

    # 1. NaN and Inf Check
    if np.any(np.isnan(V)) or np.any(np.isnan(theta)) or np.any(np.isnan(P)) or np.any(np.isnan(Q)):
        reasons.append("Contains NaN values")
    if np.any(np.isinf(V)) or np.any(np.isinf(theta)) or np.any(np.isinf(P)) or np.any(np.isinf(Q)):
        reasons.append("Contains Inf values")

    if reasons:
        return False, reasons

    # 2. All-zero check (blackout or failure)
    if np.all(V < 0.1):
        reasons.append("All-zero voltage state vector (Blackout / Failure)")
        return False, reasons

    # 3. Voltage Bounds Check: 0.85 <= V <= 1.15 pu
    if np.any(V < 0.85) or np.any(V > 1.15):
        min_v, max_v = np.min(V), np.max(V)
        reasons.append(f"Voltage out of bounds: min={min_v:.4f}, max={max_v:.4f} pu (expected [0.85, 1.15])")

    # 4. Angle Bounds Check: -180 <= theta <= 180 degrees (converted from radians)
    theta_deg = np.degrees(theta)
    if np.any(theta_deg < -180.0) or np.any(theta_deg > 180.0):
        min_theta, max_theta = np.min(theta_deg), np.max(theta_deg)
        reasons.append(f"Angle out of bounds: min={min_theta:.2f}, max={max_theta:.2f} deg (expected [-180, 180])")

    # 5. Power Balance Check
    # In res_bus.p_mw: generators are negative, loads are positive.
    # Sum of all injections is P_loads - P_gens = - P_losses.
    # Therefore, sum of all injections must be negative, and absolute value (losses) must be positive.
    sum_P = np.sum(P)
    losses_P = -sum_P
    
    total_gen = np.sum([abs(p) for p in P if p < 0])
    total_load = np.sum([p for p in P if p > 0])
    
    if losses_P < 0.0:
        reasons.append(f"Negative active power losses: {losses_P:.2f} MW (physically impossible)")
    elif total_gen > 0 and losses_P > 0.15 * total_gen: # Allow up to 15% losses under severe contingencies
        reasons.append(f"Unreasonably high active power losses: {losses_P:.2f} MW ({losses_P/total_gen*100:.1f}% of generation)")
        
    return len(reasons) == 0, reasons
