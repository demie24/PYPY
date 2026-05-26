import logging
from typing import Dict, Any, Tuple, List
from safety_constraints import SafetyConstraintEngine

logger = logging.getLogger("self_healing.trusted_action_filter")

class TrustedActionFilter:
    """
    Validates proposed actions against strict physical grid constraints and telemetry trust scores.
    Intercepts and rejects unsafe commands prior to grid control dispatch.
    """
    def __init__(self):
        self.safety_engine = SafetyConstraintEngine()
        
        # Thresholds
        self.min_trust_threshold = 0.50          # Rejects actions targeting elements with trust < 50%
        self.min_observability_confidence = 0.40  # Rejects actions if state observability < 40%
        self.max_physics_anomaly_score = 0.40     # Rejects actions if physics anomaly > 40% (on 0.0 - 1.0 scale)
        
    def filter_action(self, 
                      action: Dict[str, Any], 
                      target: str, 
                      telemetry: Dict[str, Any], 
                      trust_scores: Dict[str, Any] = None,
                      pinn_forecast: Dict[str, Any] = None,
                      physics_validation: Dict[str, Any] = None) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Gates the candidate action against cybersecurity trust and physical limits.
        
        Returns:
            allowed: bool
            reason: str
            metrics: Dict[str, Any] (diagnostics and rollback recommendation flags)
        """
        action_name = action.get("name", "INVALID_ACTION")
        action_type = action.get("type", "INVALID")
        
        metrics = {
            "physics_consistent": True,
            "topology_safe": True,
            "telemetry_trusted": True,
            "observability_confident": True,
            "restoration_feasible": True,
            "safety_score": 1.0,
            "rollback_recommended": False,
            "violations": []
        }
        
        # ==========================================
        # 1. Physics consistency & Anomaly gating
        # ==========================================
        if physics_validation:
            anomaly_score = physics_validation.get("physics_anomaly_score", 0.0)
            # Support both 0-100 and 0.0-1.0 scale from telemetry
            norm_anomaly = anomaly_score / 100.0 if anomaly_score > 1.0 else anomaly_score
            if norm_anomaly > self.max_physics_anomaly_score:
                metrics["physics_consistent"] = False
                metrics["violations"].append(
                    f"Grid physics validation failed: anomaly score {norm_anomaly*100:.1f}% exceeds threshold {self.max_physics_anomaly_score*100:.1f}%"
                )
                # Severe inconsistency flags rollback recommendation
                metrics["rollback_recommended"] = True
                
        # ==========================================
        # 2. Telemetry trust checks (Minimum 50%)
        # ==========================================
        if trust_scores:
            bus_trust = trust_scores.get("bus_trust", {})
            line_trust = trust_scores.get("line_trust", {})
            
            t_trust = 100.0
            if target.startswith("Bus_"):
                t_trust = bus_trust.get(target, 100.0)
            elif target in line_trust:
                t_trust = line_trust.get(target, 100.0)
                
            norm_trust = t_trust / 100.0 if t_trust > 1.0 else t_trust
            if norm_trust < self.min_trust_threshold:
                metrics["telemetry_trusted"] = False
                metrics["violations"].append(
                    f"Telemetry trust check failed: target {target} trust {norm_trust*100:.1f}% is below limit {self.min_trust_threshold*100:.1f}%"
                )
                
        # ==========================================
        # 3. Observability quality gating (Minimum 40%)
        # ==========================================
        if pinn_forecast:
            confidence = pinn_forecast.get("global_physics_confidence", 1.0)
            norm_conf = confidence / 100.0 if confidence > 1.0 else confidence
            if norm_conf < self.min_observability_confidence:
                metrics["observability_confident"] = False
                metrics["violations"].append(
                    f"Observability degraded: global confidence {norm_conf*100:.1f}% is below limit {self.min_observability_confidence*100:.1f}%"
                )

        # ==========================================
        # 4. Topology, Voltages, and Islanding checks
        # ==========================================
        topo_safe, topo_violations, safety_score = self.safety_engine.evaluate_constraints(
            telemetry or {"state": {}}, action_name, target
        )
        metrics["safety_score"] = safety_score
        if not topo_safe:
            metrics["topology_safe"] = False
            metrics["violations"].extend(topo_violations)
            
            # If opening a breaker causes severe voltage collapse or islands a bus, recommend rollback
            if any("isolate" in v.lower() or "islanding" in v.lower() or "overload" in v.lower() for v in topo_violations):
                metrics["rollback_recommended"] = True

        # ==========================================
        # 5. Restoration feasibility
        # ==========================================
        # Cannot restore a breaker that is actively faulted or compromised
        if action_name in ["RECONNECT_LINE", "REROUTE_FLOW", "ENABLE_RESTORATION"]:
            attack_status = telemetry.get("attack_status", {})
            compromised_nodes = attack_status.get("compromised_nodes", [])
            if target in compromised_nodes:
                metrics["restoration_feasible"] = False
                metrics["violations"].append(
                    f"Feasibility gate: cannot restore command to {target} under active cyber compromise."
                )

        # Overall validation summary
        allowed = (
            metrics["physics_consistent"] and 
            metrics["topology_safe"] and 
            metrics["telemetry_trusted"] and 
            metrics["observability_confident"] and
            metrics["restoration_feasible"]
        )
        
        reason = "Action approved. All pre-RL security and physics constraint gates verified."
        if not allowed:
            reason = "Action REJECTED: " + "; ".join(metrics["violations"])
            logger.warning(f"Trusted Action Filter blocked command [{action_name}] targeting {target}. Details: {reason}")
            
        return allowed, reason, metrics
