from typing import Dict, Any, List

class ActionRegistry:
    def __init__(self):
        # 10 categories of discrete actions
        self.ACTIONS = {
            0: {"name": "NO_ACTION", "type": "SYSTEM", "target": "SYSTEM", "safety_score": 1.0, "operational_risk": 0.0, "topology_impact": 0.0, "restoration_confidence": 1.0, "rollback_supported": True},
            1: {"name": "ISOLATE_LINE", "type": "TRIP", "target": "LINE", "safety_score": 0.8, "operational_risk": 0.3, "topology_impact": -1.0, "restoration_confidence": 0.9, "rollback_supported": True},
            2: {"name": "RECONNECT_LINE", "type": "CLOSE", "target": "LINE", "safety_score": 0.7, "operational_risk": 0.4, "topology_impact": 1.0, "restoration_confidence": 0.8, "rollback_supported": True},
            3: {"name": "REJECT_TELEMETRY", "type": "TRUST_OVERRIDE", "target": "NODE", "safety_score": 0.9, "operational_risk": 0.1, "topology_impact": 0.0, "restoration_confidence": 0.95, "rollback_supported": True},
            4: {"name": "RESTORE_TELEMETRY_TRUST", "type": "TRUST_CLEAR", "target": "NODE", "safety_score": 0.9, "operational_risk": 0.1, "topology_impact": 0.0, "restoration_confidence": 0.95, "rollback_supported": True},
            5: {"name": "ACTIVATE_DEFENSIVE_MODE", "type": "CONFIG", "target": "ORCHESTRATOR", "safety_score": 0.95, "operational_risk": 0.05, "topology_impact": 0.0, "restoration_confidence": 1.0, "rollback_supported": True},
            6: {"name": "ISOLATE_BUS", "type": "TRIP", "target": "BUS", "safety_score": 0.6, "operational_risk": 0.6, "topology_impact": -2.0, "restoration_confidence": 0.7, "rollback_supported": True},
            7: {"name": "ENABLE_ISLANDING", "type": "TRIP", "target": "ZONE", "safety_score": 0.55, "operational_risk": 0.7, "topology_impact": -3.0, "restoration_confidence": 0.6, "rollback_supported": True},
            8: {"name": "ENABLE_RESTORATION", "type": "CLOSE", "target": "FLISR", "safety_score": 0.8, "operational_risk": 0.2, "topology_impact": 1.0, "restoration_confidence": 0.85, "rollback_supported": True},
            9: {"name": "REROUTE_FLOW", "type": "CLOSE", "target": "LINE", "safety_score": 0.75, "operational_risk": 0.3, "topology_impact": 1.0, "restoration_confidence": 0.8, "rollback_supported": True}
        }

    def get_action(self, action_id: int) -> Dict[str, Any]:
        """
        Retrieves action details by unique ID.
        """
        return self.ACTIONS.get(action_id, {
            "name": "INVALID_ACTION", 
            "type": "INVALID", 
            "target": "INVALID", 
            "safety_score": 0.0, 
            "operational_risk": 1.0, 
            "topology_impact": 0.0, 
            "restoration_confidence": 0.0, 
            "rollback_supported": False
        })

    def validate_action_syntax(self, action_id: int, target: str) -> bool:
        """
        Verifies that target parameter syntax is correct for the action category.
        """
        action = self.get_action(action_id)
        if action["name"] == "INVALID_ACTION":
            return False
            
        t_type = action["target"]
        if t_type == "LINE":
            # e.g., L1_4, L7_8, etc.
            return target in ["L1_4", "L2_7", "L3_9", "L4_5", "L4_9", "L5_6", "L6_7", "L7_8", "L8_9"]
        elif t_type == "NODE" or t_type == "BUS":
            # e.g., Bus_1, Bus_5, etc.
            return target in [f"Bus_{i}" for i in range(1, 10)]
        elif t_type == "ZONE":
            return target in ["ZONE_1", "ZONE_2", "ZONE_3", "ISLAND_A", "ISLAND_B"]
        elif t_type == "ORCHESTRATOR":
            return target in ["ADVISORY", "SEMI_AUTONOMOUS", "EMERGENCY_DEFENSE"]
        elif t_type == "SYSTEM" or t_type == "FLISR":
            return target == "SYSTEM"
            
        return False
        
    def list_actions(self) -> List[Dict[str, Any]]:
        return [dict(action_id=aid, **data) for aid, data in self.ACTIONS.items()]
