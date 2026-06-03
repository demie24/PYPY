import logging
import numpy as np

logger = logging.getLogger("orchestrator.decision_engine")

class OrchestrationDecisionEngine:
    def __init__(self):
        self.current_state = "NORMAL"
        self.state_candidate = "NORMAL"
        self.candidate_count = 0

    def evaluate(self, grid_state):
        """
        Fuses forecasts, validations, and trust metrics to evaluate stability, risk, and autonomous states.
        """
        telemetry = grid_state.get("telemetry")
        ai_forecast = grid_state.get("ai_forecast")  # single-bus forecast
        multi_bus_forecast = grid_state.get("multi_bus_forecast")
        threat_aware_forecast = grid_state.get("threat_aware_forecast")
        physics_val = grid_state.get("physics_validation")
        trust_scores = grid_state.get("trust_scores")
        threat_data = grid_state.get("threat")  # from threat scorer
        flisr_state = grid_state.get("flisr_state", "NORMAL")
        flisr_auto = grid_state.get("flisr_auto", True)
        
        if not telemetry:
            return self._default_nominal_response()
            
        buses = telemetry.get("state", {}).get("buses", {})
        lines = telemetry.get("state", {}).get("lines", {})
        breakers = telemetry.get("state", {}).get("breakers", {})
        attack_status = telemetry.get("attack_status", {})
        active_attack = attack_status.get("active_attack")
        
        # 1. Compute Cyber-Physical Stability Score (0 - 100)
        stability = 100.0
        
        # Subtract points for overloaded lines
        overloads_penalty = 0.0
        for line_id, line_data in lines.items():
            cap = line_data.get("capacity_pct", 0.0)
            if cap > 100.0:
                overloads_penalty += min(20.0, (cap - 100.0) * 0.5)
        stability -= overloads_penalty
        
        # Subtract points for voltage deviations with criticality-aware multipliers and blackout rules
        voltage_penalty = 0.0
        for bus_name, bus_data in buses.items():
            v_pu = bus_data.get("voltage_pu", 1.0)
            
            # Context-aware node criticality scaling
            if bus_name == "Bus_5":  # Hospital / Control Center
                weight = 2.0
                failure_penalty = 40.0
            elif bus_name == "Bus_8":  # Heavy Industrial
                weight = 1.5
                failure_penalty = 25.0
            elif bus_name == "Bus_6":  # Residential
                weight = 1.0
                failure_penalty = 15.0
            else:
                weight = 1.0
                failure_penalty = 10.0
                
            if v_pu < 0.2:
                # Absolute failure/unpowered critical load
                voltage_penalty += failure_penalty
            else:
                dev = abs(v_pu - 1.0)
                if dev > 0.05:
                    voltage_penalty += min(15.0, (dev - 0.05) * 150) * weight
        stability -= voltage_penalty
        
        # Subtract points for physics violations
        phys_score = 0.0
        impossible_state = False
        if physics_val:
            phys_score = float(physics_val.get("physics_anomaly_score", 0.0))
            impossible_state = bool(physics_val.get("impossible_state", False))
            stability -= phys_score * 0.3
            
        # Subtract points for degraded sensor trust
        if trust_scores and "details" in trust_scores:
            low_trust_count = 0
            for node, details in trust_scores["details"].items():
                t_score = details.get("trust_score", 100.0)
                if t_score < 70.0:
                    low_trust_count += 1
            stability -= min(25.0, low_trust_count * 5.0)
            
        # Subtract points for open breakers (excluding Normally Open tie-breaker L7_8)
        open_breakers_count = sum(1 for lid, stat in breakers.items() if lid != "L7_8" and stat == "OPEN")
        stability -= min(30.0, open_breakers_count * 10.0)

        # Incorporate predictive stability collapse probability
        pred_stability = grid_state.get("l6_predictive_stability")
        collapse_prob_val = 0.0
        horizon_val = 999.0
        if pred_stability:
            collapse_prob_val = float(pred_stability.get("collapse_probability", 0.0))
            horizon_val = float(pred_stability.get("survivability_horizon", 999.0))
            stability -= collapse_prob_val * 0.2
            
        # Add distributed resilience and hardening penalties
        resilience = grid_state.get("hardware_resilience")
        large_scale_sync = grid_state.get("hardware_large_scale_sync")
        deployment_hardening = grid_state.get("hardware_deployment_hardening")
        
        if resilience:
            res_state = resilience.get("resilience_state", "NOMINAL")
            if res_state == "CRITICAL":
                stability -= 15.0
            elif res_state == "EMERGENCY":
                stability -= 30.0
                
        if large_scale_sync and large_scale_sync.get("congestion_detected"):
            stability -= 5.0
            
        if deployment_hardening and deployment_hardening.get("deployment_safety_status") == "INSECURE":
            stability -= 10.0
        
        stability_score = max(0.0, min(100.0, round(stability, 2)))
        
        # 2. Compute Restoration Confidence (0 - 100)
        restoration_confidence = 100.0
        if flisr_state != "NORMAL":
            # If tie-breaker line L7_8 is compromised or open/distrusted, confidence drops
            l78_trust = 100.0
            if trust_scores and "details" in trust_scores:
                l78_trust = trust_scores["details"].get("L7_8", {}).get("trust_score", 100.0)
                
            if l78_trust < 70.0:
                restoration_confidence -= 40.0
                
            if impossible_state:
                restoration_confidence -= 30.0
                
            if phys_score > 40.0:
                restoration_confidence -= 20.0
                
            # If forecast predicts ongoing risk of instability
            if threat_aware_forecast:
                cyber_prob = float(threat_aware_forecast.get("cyber_instability_probability", 0.0))
                restoration_confidence -= cyber_prob * 30.0
        
        # Reduce restoration confidence under high predictive collapse risk
        if collapse_prob_val > 0.0:
            restoration_confidence -= collapse_prob_val * 0.25
                
        restoration_confidence = max(0.0, min(100.0, round(restoration_confidence, 2)))
        
        # 3. Classify Autonomous State Logic with Weighted Decision Fusion
        cyber_prob = 0.0
        if threat_aware_forecast:
            cyber_prob = float(threat_aware_forecast.get("cyber_instability_probability", 0.0))
        elif ai_forecast:
            cyber_prob = float(ai_forecast.get("predicted_threat", 0.0)) / 100.0
            
        grid_conf = 100.0
        if physics_val:
            grid_conf = float(physics_val.get("global_grid_confidence", 100.0))
            
        cascade_prob = 0.0
        if threat_data:
            cascade_prob = float(threat_data.get("cascade_probability", 0.0))
            
        # Compute Average Telemetry Trust Score (nominal is 100)
        trust_avg = 100.0
        if trust_scores and "bus_trust" in trust_scores and len(trust_scores["bus_trust"]) > 0:
            trust_avg = sum(trust_scores["bus_trust"].values()) / len(trust_scores["bus_trust"])
        elif trust_scores and "details" in trust_scores and len(trust_scores["details"]) > 0:
            trust_vals = [d.get("trust_score", 100.0) for d in trust_scores["details"].values() if "trust_score" in d]
            if trust_vals:
                trust_avg = sum(trust_vals) / len(trust_vals)

        # Weighted Decision Fusion Formula:
        # F_fusion = 0.40 * cyber_prob + 0.35 * (phys_score / 100) + 0.25 * (1 - trust_avg / 100)
        t_factor = 1.0 - (trust_avg / 100.0)
        consensus_threat_score = 0.40 * cyber_prob + 0.35 * (phys_score / 100.0) + 0.25 * t_factor
        consensus_threat_score = max(0.0, min(1.0, round(consensus_threat_score, 4)))

        # Conflict Arbitration logic
        is_cyber_attack = False
        if active_attack:
            is_cyber_attack = True
        elif cyber_prob >= 0.50 and phys_score < 20.0:
            if trust_avg < 70.0:
                is_cyber_attack = True  # Arbitrated: sensor tampering/FDIA bypassing physics checks
        elif phys_score >= 40.0 and cyber_prob < 0.40:
            if trust_avg >= 75.0:
                is_cyber_attack = False  # Arbitrated: physical anomaly/fault, not a cyber attack
            else:
                is_cyber_attack = True  # Arbitrated: cyber-attack disguised as physical fault with corrupted trust
        elif phys_score >= 40.0 and cyber_prob >= 0.50:
            is_cyber_attack = True  # Confirmed cyber-physical attack
            
        if consensus_threat_score >= 0.50:
            is_cyber_attack = True

        if stability_score < 40.0 or grid_conf < 40.0 or collapse_prob_val >= 75.0 or horizon_val < 15.0:
            raw_state = "EMERGENCY_STABILIZATION"
        elif is_cyber_attack:
            raw_state = "CYBER_ATTACK"
        elif (stability_score < 75.0 and overloads_penalty > 0.0 and cascade_prob >= 0.40) or collapse_prob_val >= 40.0 or horizon_val < 45.0:
            raw_state = "CASCADING_INSTABILITY"
        elif flisr_state in ["RESTORATION", "ISOLATION", "RESTORED"]:
            raw_state = "AUTONOMOUS_RECOVERY"
        elif open_breakers_count > 0 or (trust_scores and any(t.get("trust_score", 100.0) < 70.0 for t in trust_scores.get("details", {}).values())):
            raw_state = "DEGRADED"
        else:
            raw_state = "NORMAL"

        # State transition hysteresis (requires 3 consecutive ticks to transition)
        if raw_state == self.current_state:
            self.state_candidate = raw_state
            self.candidate_count = 0
        else:
            if raw_state == self.state_candidate:
                self.candidate_count += 1
            else:
                self.state_candidate = raw_state
                self.candidate_count = 1
                
            if self.candidate_count >= 3:
                self.current_state = raw_state
                self.candidate_count = 0
                
        global_state = self.current_state
            
        # 4. Compute Global Risk Level
        if global_state in ["EMERGENCY_STABILIZATION", "CYBER_ATTACK"] and stability_score < 50.0:
            global_risk = "CRITICAL"
        elif stability_score < 70.0 or global_state in ["CASCADING_INSTABILITY", "CYBER_ATTACK"]:
            global_risk = "HIGH"
        elif stability_score < 85.0 or global_state == "DEGRADED":
            global_risk = "MEDIUM"
        else:
            global_risk = "LOW"
            
        # 5. Compile Subsystem Reasoning Diagnostics
        reasoning = {}
        
        # AI Forecaster Reasoning
        if threat_aware_forecast:
            cyber_pct = cyber_prob * 100
            status_text = threat_aware_forecast.get("status", "NORMAL")
            reasoning["ai_forecaster"] = f"Cyber instability risk forecast is {status_text} ({cyber_pct:.1f}% probability)."
        elif ai_forecast:
            pred_threat = float(ai_forecast.get("predicted_threat", 0.0))
            risk = ai_forecast.get("cascade_risk", "LOW")
            reasoning["ai_forecaster"] = f"Single-bus model predicts {pred_threat:.0f}% future threat index (Risk: {risk})."
        else:
            reasoning["ai_forecaster"] = "Forecasting model warming up..."
            
        # Physics Validator Reasoning
        if physics_val:
            state = physics_val.get("physics_state", "NORMAL")
            kcl = float(physics_val.get("kcl_error", 0.0))
            kvl = float(physics_val.get("kvl_error", 0.0))
            reasoning["physics_validator"] = f"Kirchhoff state is {state}. KCL Error: {kcl:.1f} MW. KVL Error: {kvl:.4f} p.u."
        else:
            reasoning["physics_validator"] = "Physics laws validation engine idle..."
            
        # Trust Engine Reasoning
        if trust_scores and "bus_trust" in trust_scores:
            lowest_bus = min(trust_scores["bus_trust"].items(), key=lambda x: x[1])
            if lowest_bus[1] < 70.0:
                reasoning["trust_engine"] = f"Distrusted sensor detected at {lowest_bus[0]} (Trust: {lowest_bus[1]:.0f}%). Observability degraded."
            else:
                reasoning["trust_engine"] = f"Telemetry channels verified healthy. Average bus trust: {lowest_bus[1]:.0f}%."
        else:
            reasoning["trust_engine"] = "Telemetry trust engine calculating reliability indices..."
            
        # FLISR FSM State Reasoning
        if flisr_state == "NORMAL":
            reasoning["flisr_state"] = "Grid topology nominal. Healing automation idle."
        elif flisr_state == "FAULT_DETECTED":
            reasoning["flisr_state"] = "Line fault detected. Isolation timer initiated."
        elif flisr_state == "ISOLATED":
            reasoning["flisr_state"] = "Fault successfully isolated. Re-routing analysis starting."
        elif flisr_state == "RESTORED":
            reasoning["flisr_state"] = "Grid reconfiguration committed. Alternate paths active."
        else:
            reasoning["flisr_state"] = f"Automatic FSM actively executing: {flisr_state} sequence."
 
        # Add Predictive Stability Reasoning
        if pred_stability:
            policy = grid_state.get("l6_self_preservation", {}).get("active_policy", "NOMINAL")
            reasoning["predictive_stability"] = f"Stability Horizon: {horizon_val}s. Collapse Prob: {collapse_prob_val}%. Preservation Policy: {policy}."
        else:
            reasoning["predictive_stability"] = "Predictive stability model warming up..."
            
        # Add distributed resilience & hardening reasoning
        if resilience and deployment_hardening:
            res_state = resilience.get("resilience_state", "NOMINAL")
            surv_score = resilience.get("survivability_score", 100.0)
            comp_score = deployment_hardening.get("compliance_score", 100.0)
            reasoning["resilience_hardening"] = f"Resilience state is {res_state} (Survivability: {surv_score:.1f}%, Hardening: {comp_score:.1f}% Compliance)."
        else:
            reasoning["resilience_hardening"] = "Resilience and hardening monitors initializing..."
            
        return {
            "global_state": global_state,
            "global_risk_level": global_risk,
            "stability_score": stability_score,
            "restoration_confidence": restoration_confidence,
            "consensus_threat_score": consensus_threat_score,
            "trust_avg": round(trust_avg, 2),
            "active_subsystems_reasoning": reasoning
        }

    def _default_nominal_response(self):
        return {
            "global_state": "NORMAL",
            "global_risk_level": "LOW",
            "stability_score": 100.0,
            "restoration_confidence": 100.0,
            "consensus_threat_score": 0.0,
            "trust_avg": 100.0,
            "active_subsystems_reasoning": {
                "ai_forecaster": "Inference idle.",
                "physics_validator": "Validation idle.",
                "trust_engine": "Trust engine idle.",
                "flisr_state": "Healing loop idle."
            }
        }
