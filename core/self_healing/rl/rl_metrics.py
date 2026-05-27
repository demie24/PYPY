import numpy as np
import time
from typing import Dict, Any, List

def calculate_grid_survivability(telemetry: Dict[str, Any]) -> float:
    """
    Calculates grid survivability score (0-100) based on nominal voltages and load service.
    """
    if not telemetry or "state" not in telemetry:
        return 100.0
        
    buses = telemetry["state"].get("buses", {})
    if not buses:
        return 100.0
        
    # Check voltages (nominal is 0.95 to 1.05 p.u.)
    voltages = [bus.get("voltage_pu", 1.0) for bus in buses.values()]
    nominal_voltages = sum(1 for v in voltages if 0.95 <= v <= 1.05)
    voltage_fraction = nominal_voltages / len(buses)
    
    # Check load buses serviced (buses 5, 6, 8 at indices 4, 5, 7 -> Bus_5, Bus_6, Bus_8)
    load_buses = ["Bus_5", "Bus_6", "Bus_8"]
    serviced_loads = 0
    total_loads = 0
    for bid, bus in buses.items():
        if bid in load_buses:
            total_loads += 1
            if bus.get("voltage_pu", 1.0) > 0.90:
                serviced_loads += 1
                
    load_fraction = (serviced_loads / total_loads) if total_loads > 0 else 1.0
    
    # Combined score
    score = 50.0 * voltage_fraction + 50.0 * load_fraction
    return round(score, 2)

def calculate_blackout_risk(telemetry: Dict[str, Any], cascade_prob: float = 0.0) -> float:
    """
    Estimates blackout risk (0-100) based on open breakers, voltage collapse, and cascade probability.
    """
    if not telemetry or "state" not in telemetry:
        return 0.0
        
    buses = telemetry["state"].get("buses", {})
    breakers = telemetry["state"].get("breakers", {})
    
    # Open breaker risk (higher number of open breakers = higher blackout risk)
    open_breakers = sum(1 for stat in breakers.values() if stat == "OPEN")
    breaker_risk = (open_breakers / len(breakers)) * 40.0 if breakers else 0.0
    
    # Voltage collapse risk (voltages < 0.88 p.u. are critical)
    critical_voltages = sum(1 for bus in buses.values() if bus.get("voltage_pu", 1.0) < 0.88)
    voltage_risk = (critical_voltages / len(buses)) * 40.0 if buses else 0.0
    
    # Cascade risk component
    cascade_risk = cascade_prob * 20.0
    
    total_risk = breaker_risk + voltage_risk + cascade_risk
    return round(max(0.0, min(100.0, total_risk)), 2)

def calculate_recovery_efficiency(actual_steps: int, nominal_min_steps: int = 2) -> float:
    """
    Calculates recovery efficiency % based on actual vs theoretical steps taken.
    """
    if actual_steps <= 0:
        return 100.0
    efficiency = (nominal_min_steps / actual_steps) * 100.0
    return round(max(0.0, min(100.0, efficiency)), 2)

def estimate_action_risk(action_name: str, 
                         target: str, 
                         telemetry: Dict[str, Any], 
                         trust_scores: Dict[str, Any] = None,
                         cyber_prob: float = 0.0,
                         sandbox_violations: List[str] = None) -> Dict[str, float]:
    """
    Estimates rollback probability and unsafe topology probability for a proposed action.
    Returns:
        {
            "rollback_probability": float,
            "unsafe_topology_probability": float,
            "restoration_confidence": float
        }
    """
    # Base rates
    rollback_prob = 0.05
    unsafe_topo_prob = 0.05
    
    is_restoration = action_name in ["RECONNECT_LINE", "REROUTE_FLOW", "ENABLE_RESTORATION"]
    is_containment = action_name in ["ISOLATE_LINE", "REJECT_TELEMETRY", "ISOLATE_BUS", "ENABLE_ISLANDING"]
    
    # Check target trust scores
    target_trust = 100.0
    if trust_scores and "details" in trust_scores and target in trust_scores["details"]:
        target_trust = trust_scores["details"][target].get("trust_score", 100.0)
        
    if target_trust < 70.0:
        # High risk of rollback if we interact with distrusted elements
        rollback_prob = max(rollback_prob, (100.0 - target_trust) / 100.0)
        if is_restoration:
            unsafe_topo_prob = max(unsafe_topo_prob, 0.70)
            
    # Under active attack, restoration actions have high rollback/unsafe risk
    if cyber_prob > 0.50 and is_restoration:
        rollback_prob = max(rollback_prob, 0.80)
        unsafe_topo_prob = max(unsafe_topo_prob, 0.75)
        
    # Check sandbox feedback
    if sandbox_violations:
        unsafe_topo_prob = max(unsafe_topo_prob, 0.90)
        rollback_prob = max(rollback_prob, 0.85)
        
    confidence = (1.0 - rollback_prob) * (1.0 - unsafe_topo_prob) * 100.0
    return {
        "rollback_probability": round(rollback_prob, 2),
        "unsafe_topology_probability": round(unsafe_topo_prob, 2),
        "restoration_confidence": round(confidence, 2)
    }

def calculate_containment_efficiency(compromised_nodes: List[str], isolated_nodes: List[str]) -> float:
    """
    Calculates containment efficiency % based on how many compromised nodes were successfully isolated.
    """
    if not compromised_nodes:
        return 100.0
    isolated_count = sum(1 for node in compromised_nodes if node in isolated_nodes)
    return round((isolated_count / len(compromised_nodes)) * 100.0, 2)

def calculate_policy_confidence(ppo_probs: np.ndarray, action_id: int) -> float:
    """
    Calculates the confidence percentage for the selected policy action.
    """
    if ppo_probs is None or len(ppo_probs) == 0:
        return 100.0
    if action_id < 0 or action_id >= len(ppo_probs):
        return 0.0
    return round(float(ppo_probs[action_id]) * 100.0, 2)

def compile_comprehensive_metrics(
    telemetry: Dict[str, Any],
    actual_steps: int,
    step_count: int,
    rollbacks: int,
    switch_count: int,
    start_time: float,
    compromised_nodes: List[str],
    isolated_nodes: List[str],
    ppo_probs: np.ndarray = None,
    action_id: int = 0,
    cascade_prob: float = 0.0
) -> Dict[str, Any]:
    """
    Compiles all RL maturity metrics.
    """
    survivability = calculate_grid_survivability(telemetry)
    blackout_risk = calculate_blackout_risk(telemetry, cascade_prob)
    rest_efficiency = calculate_recovery_efficiency(actual_steps)
    cont_efficiency = calculate_containment_efficiency(compromised_nodes, isolated_nodes)
    
    # Policy confidence
    pol_confidence = 100.0
    if ppo_probs is not None:
        pol_confidence = calculate_policy_confidence(ppo_probs, action_id)
        
    duration = time.time() - start_time if start_time > 0 else 0.0
    
    return {
        "restoration_latency_steps": step_count,
        "topology_survivability_score": survivability,
        "blackout_risk_pct": blackout_risk,
        "containment_efficiency_pct": cont_efficiency,
        "restoration_efficiency_pct": rest_efficiency,
        "policy_confidence_pct": pol_confidence,
        "relay_switch_count": switch_count,
        "rollback_frequency": rollbacks,
        "recovery_duration_seconds": round(duration, 2)
    }
