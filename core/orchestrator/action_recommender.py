import logging

logger = logging.getLogger("orchestrator.action_recommender")

class ActionRecommender:
    def __init__(self):
        # Track historical trips to recommend lockout
        self.breaker_trip_counts = {}
        
    def recommend(self, grid_state, decision_report):
        """
        Formulates specific, prioritized operator recommendations based on global decision reports.
        """
        telemetry = grid_state.get("telemetry")
        physics_val = grid_state.get("physics_validation")
        trust_scores = grid_state.get("trust_scores")
        threat_aware_forecast = grid_state.get("threat_aware_forecast")
        flisr_state = grid_state.get("flisr_state", "NORMAL")
        
        recommendations = []
        
        if not telemetry:
            return recommendations
            
        buses = telemetry.get("state", {}).get("buses", {})
        lines = telemetry.get("state", {}).get("lines", {})
        breakers = telemetry.get("state", {}).get("breakers", {})
        attack_status = telemetry.get("attack_status", {})
        active_attack = attack_status.get("active_attack")
        
        global_state = decision_report.get("global_state", "NORMAL")
        stability_score = decision_report.get("stability_score", 100.0)
        
        # 1. Recommendation: ISOLATE_LINE (for thermal overload)
        for line_id, line_data in lines.items():
            cap = line_data.get("capacity_pct", 0.0)
            if cap > 100.0 and breakers.get(line_id) == "CLOSED":
                recommendations.append({
                    "action": "ISOLATE_LINE",
                    "target": line_id,
                    "priority": "CRITICAL" if cap > 120.0 else "HIGH",
                    "description": f"Isolate overloaded transmission line {line_id.replace('_', ' ')}.",
                    "reasoning": f"Line capacity reaches {cap:.1f}% load, creating a severe thermal overload and cascade risk."
                })
                
        # 2. Recommendation: TELEMETRY_DISTRUST (for low trust sensors)
        if trust_scores and "details" in trust_scores:
            for node, details in trust_scores["details"].items():
                t_score = details.get("trust_score", 100.0)
                if t_score < 50.0:
                    recommendations.append({
                        "action": "TELEMETRY_DISTRUST",
                        "target": node,
                        "priority": "HIGH" if t_score < 30.0 else "MEDIUM",
                        "description": f"Ignore and distrust telemetry measurements from {node.replace('_', ' ')}.",
                        "reasoning": f"Sensor trust score has dropped to {t_score:.1f}% due to repeated physical law violations."
                    })
                    
        # 3. Recommendation: BREAKER_LOCKOUT (for oscillating or cyber-compromised breakers)
        # Check if active attack has compromised breakers
        if active_attack in ["TRIP", "coordinated_cyber_physical"] and attack_status.get("compromised_nodes"):
            for comp_node in attack_status["compromised_nodes"].keys():
                if comp_node in breakers:
                    recommendations.append({
                        "action": "BREAKER_LOCKOUT",
                        "target": comp_node,
                        "priority": "CRITICAL",
                        "description": f"Engage breaker lockout mechanism on {comp_node}.",
                        "reasoning": f"Active cyber intrusion targeting {comp_node} breaker control commands detected."
                    })
                    
        # 4. Recommendation: FLISR_SUPPRESSION (when re-routing is unsafe due to cyber attacks)
        if flisr_state != "NORMAL" and global_state == "CYBER_ATTACK":
            recommendations.append({
                "action": "FLISR_SUPPRESSION",
                "target": "FLISR_ENGINE",
                "priority": "CRITICAL",
                "description": "Suppress active FLISR healing and re-routing algorithms.",
                "reasoning": "Automatic restoration path is insecure under active cyber attack and compromised sensor feedback."
            })
            
        # 5. Recommendation: REROUTE_LOAD (when load bus is islanded/unfed but healthy tie lines are open)
        if breakers.get("L7_8") == "OPEN" and any(b.get("voltage_pu", 1.0) < 0.20 for b in buses.values()):
            # Check if tie-breaker line L7_8 is trusted
            l78_trust = 100.0
            if trust_scores and "details" in trust_scores:
                l78_trust = trust_scores["details"].get("L7_8", {}).get("trust_score", 100.0)
                
            if l78_trust >= 75.0 and global_state != "CYBER_ATTACK":
                recommendations.append({
                    "action": "REROUTE_LOAD",
                    "target": "L7_8",
                    "priority": "HIGH",
                    "description": "Close Normally Open tie-breaker L7 8 to restore islanded load sector.",
                    "reasoning": "Sector is unpowered but tie-line sensors are healthy and cyber-consistent."
                })
                
        # 6. Recommendation: OPERATOR_ESCALATION (for general emergency/catastrophic failures)
        if global_state == "EMERGENCY_MODE" or stability_score < 45.0:
            recommendations.append({
                "action": "OPERATOR_ESCALATION",
                "target": "CONTROL_ROOM",
                "priority": "CRITICAL",
                "description": "Escalate control to manual operator override immediately.",
                "reasoning": "Grid physical stability limits breached and global telemetry trust is lost. Autonomous safety limits exceeded."
            })
            
        # Sort recommendations by priority: CRITICAL > HIGH > MEDIUM > LOW
        priority_weights = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}
        recommendations.sort(key=lambda x: priority_weights.get(x["priority"], 0), reverse=True)
        
        return recommendations
