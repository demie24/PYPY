import numpy as np
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
        
    # Coordination confidence
    confidence = (1.0 - rollback_prob) * (1.0 - unsafe_topo_prob) * 100.0
    
    return {
        "rollback_probability": round(rollback_prob, 2),
        "unsafe_topology_probability": round(unsafe_topo_prob, 2),
        "restoration_confidence": round(confidence, 2)
    }
