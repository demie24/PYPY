from typing import Dict, Any, List

class RegionalAgent:
    """
    Evaluates cyber-physical threat state, topology risks, and physics consistency 
    for a specific sub-region of the power grid.
    """
    def __init__(self, region_id: int, name: str, buses: List[int], lines: List[str]):
        self.region_id = region_id
        self.name = name
        self.buses = buses
        self.lines = lines

    def evaluate(self, 
                 pinn_outputs: Any, 
                 lstm_outputs: Any, 
                 gnn_outputs: Any, 
                 stgnn_outputs: Any) -> Dict[str, Any]:
        """
        Parses multi-source inputs and computes regional metrics.
        
        Returns:
            Dict containing:
              local_threat_score: float (0.0 to 1.0)
              local_recommendation: str (NORMAL, WARNING, ANOMALY, ATTACK_CONFIRMED, ISOLATE_COMPONENT, RECOVERY_REQUIRED)
              physics_validity: float (0.0 to 1.0)
              future_risk: float (0.0 to 1.0)
              topology_risk: float (0.0 to 1.0)
        """
        # 1. Parse PINN / Physics Validity
        physics_validity = 1.0
        violations_count = 0
        if isinstance(pinn_outputs, (int, float)):
            physics_validity = float(pinn_outputs)
        elif isinstance(pinn_outputs, dict):
            physics_validity = pinn_outputs.get("physics_validation_score", 1.0)
            violations = pinn_outputs.get("physics_violations", [])
            # Count violations pertaining to this region's buses or lines
            for v in violations:
                bus_id = v.get("bus_id")
                line_id = v.get("line_id")
                if (bus_id is not None and bus_id in self.buses) or (line_id is not None and line_id in self.lines):
                    violations_count += 1
            if violations_count > 0:
                physics_validity = max(0.0, physics_validity - (violations_count * 0.15))

        # 2. Parse LSTM / Temporal Anomaly
        lstm_anomaly_prob = 0.0
        predicted_attack = "NORMAL"
        if isinstance(lstm_outputs, (int, float)):
            lstm_anomaly_prob = float(lstm_outputs)
            if lstm_anomaly_prob >= 0.5:
                predicted_attack = "ATTACK"
        elif isinstance(lstm_outputs, dict):
            lstm_anomaly_prob = lstm_outputs.get("anomaly_probability", 0.0)
            predicted_attack = lstm_outputs.get("predicted_attack_class", "NORMAL")

        # 3. Parse GNN / Current Risk & Topology Risk
        gnn_criticality = 0.0
        gnn_topology_risk = 0.0
        if isinstance(gnn_outputs, (int, float)):
            gnn_criticality = float(gnn_outputs)
            gnn_topology_risk = float(gnn_outputs)
        elif isinstance(gnn_outputs, dict):
            # Compute average criticality/topology scores for buses in this region
            crit_scores = gnn_outputs.get("criticality_scores", {})
            topo_scores = gnn_outputs.get("topology_risk_scores", {})
            
            regional_crits = []
            regional_topos = []
            
            for b in self.buses:
                # Handle keys that could be strings or ints in JSON/dict
                c_val = crit_scores.get(b, crit_scores.get(str(b)))
                t_val = topo_scores.get(b, topo_scores.get(str(b)))
                
                if c_val is not None:
                    regional_crits.append(float(c_val))
                if t_val is not None:
                    regional_topos.append(float(t_val))
                    
            gnn_criticality = sum(regional_crits) / len(regional_crits) if regional_crits else 0.0
            gnn_topology_risk = sum(regional_topos) / len(regional_topos) if regional_topos else 0.0

        # 4. Parse ST-GNN / Future Risk
        future_risk = 0.0
        if isinstance(stgnn_outputs, (int, float)):
            future_risk = float(stgnn_outputs)
        elif isinstance(stgnn_outputs, dict):
            future_node_risks = stgnn_outputs.get("future_node_risk", {})
            regional_future_risks = []
            for b in self.buses:
                fr_val = future_node_risks.get(b, future_node_risks.get(str(b)))
                if fr_val is not None:
                    regional_future_risks.append(float(fr_val))
            future_risk = sum(regional_future_risks) / len(regional_future_risks) if regional_future_risks else 0.0

        # 5. Fuse metrics into Local Threat Score
        # We weigh LSTM anomalies, GNN criticality, ST-GNN forecasting, and physics discrepancies
        pinn_threat = 1.0 - physics_validity
        local_threat_score = (
            0.30 * lstm_anomaly_prob +
            0.30 * gnn_criticality +
            0.30 * future_risk +
            0.10 * pinn_threat
        )
        local_threat_score = max(0.0, min(1.0, local_threat_score))

        # 6. Generate Local Recommendation
        # Order of severity: ISOLATE_COMPONENT > ATTACK_CONFIRMED > ANOMALY > WARNING > RECOVERY_REQUIRED > NORMAL
        if local_threat_score >= 0.85 and physics_validity < 0.5:
            rec = "ISOLATE_COMPONENT"
        elif local_threat_score >= 0.70 and (physics_validity < 0.75 or predicted_attack != "NORMAL"):
            rec = "ATTACK_CONFIRMED"
        elif local_threat_score >= 0.55:
            rec = "ANOMALY"
        elif local_threat_score >= 0.40 or future_risk >= 0.50:
            rec = "WARNING"
        elif physics_validity < 0.85 and local_threat_score < 0.40:
            rec = "RECOVERY_REQUIRED"
        else:
            rec = "NORMAL"

        return {
            "region_id": self.region_id,
            "region_name": self.name,
            "local_threat_score": round(local_threat_score, 4),
            "local_recommendation": rec,
            "physics_validity": round(physics_validity, 4),
            "future_risk": round(future_risk, 4),
            "topology_risk": round(gnn_topology_risk, 4)
        }
