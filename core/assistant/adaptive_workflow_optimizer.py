import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("assistant.workflow_optimizer")

class AdaptiveWorkflowOptimizer:
    def __init__(self):
        self.recommendations: List[Dict[str, Any]] = []
        self.active_optimizations: Dict[str, Dict[str, Any]] = {}
        self.last_eval_time = 0.0

    def evaluate_efficiency(
        self, 
        grid_state: Dict[str, Any], 
        workflows_summary: Dict[str, Any],
        predicted_timings: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        """
        Formulates efficiency suggestions based on current grid stability and predicted durations.
        """
        self.recommendations = []
        
        threat_score = grid_state.get("threat", {}).get("threat_score", 0.0)
        latency = grid_state.get("telemetry", {}).get("latency_ms", 45.0)

        # 1. Delay Optimization Suggestion (nominal conditions)
        if threat_score < 30.0 and latency < 50.0:
            # We can speed up checks safely
            # Target standard system_status_check
            predicted_dur = predicted_timings.get("system_status_check", 5.0)
            if predicted_dur <= 5.0:
                self.recommendations.append({
                    "workflow_name": "system_status_check",
                    "optimization_type": "TRIM_DELAY",
                    "description": "Prestasi edge cemerlang. Cadangkan kurangkan sela masa (delay_sec) status check daripada 5.0s kepada 3.5s untuk penjimatan sumber.",
                    "parameter": "delay_sec",
                    "old_value": 5.0,
                    "new_value": 3.5,
                    "confidence": 0.90,
                    "status": "PENDING_APPROVAL"
                })

        # 2. Lockout Extension Suggestion (high threat environment)
        if threat_score > 75.0:
            # Need to expand spacing between steps to prevent breaker oscillation
            self.recommendations.append({
                "workflow_name": "emergency_load_shed",
                "optimization_type": "INFLATE_LOCKOUT",
                "description": "Ancaman grid kritikal dikesan. Cadangkan naikkan lockout suppression daripada 5.0s kepada 8.0s bagi mengelakkan trip berganda.",
                "parameter": "delay_sec",
                "old_value": 5.0,
                "new_value": 8.0,
                "confidence": 0.95,
                "status": "PENDING_APPROVAL"
            })

        return self.recommendations

    def approve_recommendation(self, workflow_name: str) -> Dict[str, Any]:
        """
        Operator Control Priority Rule: Requires explicit operator approval.
        """
        for r in self.recommendations:
            if r["workflow_name"] == workflow_name and r["status"] == "PENDING_APPROVAL":
                r["status"] = "APPROVED"
                self.active_optimizations[workflow_name] = r
                logger.info(f"Optimization approved by operator for {workflow_name}: set {r['parameter']}={r['new_value']}")
                return {"status": "SUCCESS", "message": f"Optimization for {workflow_name} approved."}
        return {"status": "FAILED", "error": "recommendation_not_found"}

    def get_optimized_delay(self, workflow_name: str, default_delay: float) -> float:
        """
        Returns the adapted timing values if optimization has been approved.
        """
        opt = self.active_optimizations.get(workflow_name)
        if opt and opt["status"] == "APPROVED":
            return float(opt["new_value"])
        return default_delay

    def get_status_summary(self) -> Dict[str, Any]:
        return {
            "recommendations_count": len(self.recommendations),
            "recommendations": self.recommendations,
            "active_optimizations_count": len(self.active_optimizations),
            "active_optimizations": list(self.active_optimizations.values())
        }
