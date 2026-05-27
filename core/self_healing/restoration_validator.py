import os
import sys
import logging
from typing import Dict, Any, List

# Setup import paths
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(CURRENT_DIR)

from restoration_sandbox import RestorationSandbox

logger = logging.getLogger("self_healing.restoration_validator")

class RestorationValidator:
    """
    Validates safety of restoration actions prior to breaker control close operations.
    Dry-runs commands in a isolated sandbox simulation to reject actions causing overloads/voltage collapse.
    """
    def __init__(self, sandbox=None):
        self.sandbox = sandbox if sandbox else RestorationSandbox()
        
    def validate_action(self, telemetry: Dict[str, Any], action_name: str, target: str) -> Dict[str, Any]:
        """
        Runs dry-run validation of a proposed close/open action in the sandbox.
        Rejects actions that violate voltage limits (nominal 0.90 to 1.10 p.u.)
        or overload conductors (> 1.10 p.u. capacity / 110%).
        """
        if not telemetry:
            return {
                "is_safe": False,
                "violations": ["Empty telemetry payload supplied to validator."],
                "safety_score": 0.0,
                "cascade_risk": 1.0,
                "confidence": 0.0,
                "predicted_voltages": [],
                "predicted_loadings": {}
            }

        # Synchronize sandbox state with current telemetry snapshot
        self.sandbox.reset_to_state(telemetry)
        
        # Execute dry-run action
        result = self.sandbox.dry_run_action(action_name, target)
        
        is_safe = result.get("allowed", False)
        violations = list(result.get("violations", []))
        
        predicted_voltages = result.get("predicted_voltages", [])
        predicted_loadings = result.get("predicted_loadings", {})
        
        # Apply strict Layer 6 voltage bounds: [0.90, 1.10] p.u.
        for idx, v in enumerate(predicted_voltages):
            bus_name = f"Bus_{idx + 1}"
            if v < 0.90:
                is_safe = False
                violations.append(f"{bus_name} predicted undervoltage: {v:.3f} p.u. (Limit: >= 0.90)")
            elif v > 1.10:
                is_safe = False
                violations.append(f"{bus_name} predicted overvoltage: {v:.3f} p.u. (Limit: <= 1.10)")
                
        # Apply strict Layer 6 conductor loading limits: <= 1.10 p.u. (110%)
        for lid, loading in predicted_loadings.items():
            if loading > 1.10:
                is_safe = False
                violations.append(f"Line {lid} predicted overload: {loading*100:.1f}% (Limit: <= 110%)")
                
        return {
            "is_safe": is_safe,
            "violations": violations,
            "safety_score": float(result.get("safety_score", 0.0)),
            "cascade_risk": float(result.get("cascade_risk", 1.0)),
            "confidence": float(result.get("confidence", 0.0)),
            "predicted_voltages": predicted_voltages,
            "predicted_loadings": predicted_loadings
        }
