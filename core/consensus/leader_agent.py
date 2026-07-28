import numpy as np
from typing import Dict, List, Any
from .trust_fusion import TrustFusionEngine

class LeaderAgent:
    """
    Aggregates regional decisions, runs the Trust Fusion Engine, resolves conflicts,
    and makes the final unified operational decision.
    """
    def __init__(self, trust_fusion: TrustFusionEngine):
        self.trust_fusion = trust_fusion
        self.action_space = [
            "NORMAL",
            "WARNING",
            "ANOMALY",
            "RECOVERY_REQUIRED",
            "ATTACK_CONFIRMED",
            "ISOLATE_COMPONENT"
        ]

    def evaluate_consensus(self, 
                           regional_outputs: List[Dict[str, Any]], 
                           pinn_conf: float, 
                           lstm_conf: float, 
                           gnn_conf: float, 
                           stgnn_conf: float) -> Dict[str, Any]:
        """
        Gathers regional evaluations and yields a unified global decision.
        """
        if not regional_outputs:
            return self._default_nominal_decision()

        # 1. Calculate Global Threat Score (average of local threat scores)
        local_threats = [r["local_threat_score"] for r in regional_outputs]
        global_threat_score = float(np.mean(local_threats))

        # 2. Calculate Global Confidence Score via Trust Fusion
        global_confidence = self.trust_fusion.fuse(pinn_conf, lstm_conf, gnn_conf, stgnn_conf)

        # 3. Compile regional recommendations
        recs = [r["local_recommendation"] for r in regional_outputs]
        
        # 4. Conflict Resolution & Final Decision Selection
        # Calculate base logits for each action to support PPO/DQN integration
        # Logits are computed using physics validity, threat score, confidence, and regional alerts
        avg_physics = float(np.mean([r["physics_validity"] for r in regional_outputs]))
        
        logits = {action: 0.0 for action in self.action_space}
        
        # Count frequency of regional recommendations
        rec_counts = {act: recs.count(act) for act in self.action_space}
        num_regions = len(regional_outputs)
        
        # Scoring heuristics for each action
        logits["NORMAL"] = (1.0 - global_threat_score) * avg_physics * 2.0 + (rec_counts["NORMAL"] / num_regions)
        logits["WARNING"] = global_threat_score * (1.0 - global_confidence) + (rec_counts["WARNING"] / num_regions)
        logits["ANOMALY"] = global_threat_score * global_confidence * 0.8 + (rec_counts["ANOMALY"] / num_regions)
        logits["RECOVERY_REQUIRED"] = (1.0 - global_threat_score) * (1.0 - avg_physics) * 1.5 + (rec_counts["RECOVERY_REQUIRED"] / num_regions)
        logits["ATTACK_CONFIRMED"] = global_threat_score * global_confidence * 1.5 + (rec_counts["ATTACK_CONFIRMED"] / num_regions)
        logits["ISOLATE_COMPONENT"] = global_threat_score * (1.0 - avg_physics) * global_confidence * 2.0 + (rec_counts["ISOLATE_COMPONENT"] / num_regions)

        # Softmax normalization to get probabilities/logits
        exp_logits = {k: np.exp(v) for k, v in logits.items()}
        sum_exp = sum(exp_logits.values())
        action_probs = {k: float(v / sum_exp) for k, v in exp_logits.items()}

        # Rule-based conflict resolution matrix (overriding raw logits for safety)
        final_decision = "NORMAL"
        
        # Priority rules
        if "ISOLATE_COMPONENT" in recs and (global_threat_score >= 0.70 or global_confidence >= 0.70):
            final_decision = "ISOLATE_COMPONENT"
        elif "ATTACK_CONFIRMED" in recs and (global_threat_score >= 0.60 or global_confidence >= 0.60):
            final_decision = "ATTACK_CONFIRMED"
        elif "ANOMALY" in recs and global_threat_score >= 0.50:
            final_decision = "ANOMALY"
        elif "WARNING" in recs and global_threat_score >= 0.35:
            final_decision = "WARNING"
        elif "RECOVERY_REQUIRED" in recs and avg_physics < 0.85:
            final_decision = "RECOVERY_REQUIRED"
        else:
            # Fallback to the argmax of logits
            final_decision = max(action_probs, key=action_probs.get)

        # Threat classification
        if global_threat_score >= 0.85:
            threat_level = "Critical"
        elif global_threat_score >= 0.60:
            threat_level = "High"
        elif global_threat_score >= 0.35:
            threat_level = "Medium"
        else:
            threat_level = "Low"

        return {
            "global_threat_score": round(global_threat_score, 4),
            "threat_level": threat_level,
            "global_confidence_score": round(global_confidence, 4),
            "final_decision": final_decision,
            "action_logits": action_probs,
            "regional_recommendations": rec_counts
        }

    def _default_nominal_decision(self) -> Dict[str, Any]:
        return {
            "global_threat_score": 0.0,
            "threat_level": "Low",
            "global_confidence_score": 1.0,
            "final_decision": "NORMAL",
            "action_logits": {act: (1.0 if act == "NORMAL" else 0.0) for act in self.action_space},
            "regional_recommendations": {act: 0 for act in self.action_space}
        }
