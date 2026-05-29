import time
from typing import Dict, Any, Optional

class ActionRouter:
    def __init__(self):
        # Hooks for future n8n workflows
        self.n8n_hooks: Dict[str, str] = {
            "n8n_restoration": "http://n8n-broker:5678/webhook/restoration",
            "n8n_security_alert": "http://n8n-broker:5678/webhook/security_alert"
        }
        
    def route_action(self, 
                     action_name: str, 
                     parameters: Dict[str, Any], 
                     grid_state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Translates resolved action triggers into execution payloads.
        Integrates grid data if status query is requested.
        """
        timestamp = int(time.time() * 1000)
        
        if action_name == "open_youtube":
            return {
                "action": "open_youtube",
                "status": "SUCCESS",
                "payload": {
                    "url": "https://www.youtube.com",
                    "target_page": "youtube"
                },
                "timestamp": timestamp
            }
            
        elif action_name == "open_browser":
            return {
                "action": "open_browser",
                "status": "SUCCESS",
                "payload": {
                    "url": "https://www.google.com",
                    "target_page": "browser"
                },
                "timestamp": timestamp
            }
            
        elif action_name == "get_time":
            local_time = time.strftime("%H:%M:%S", time.localtime())
            return {
                "action": "get_time",
                "status": "SUCCESS",
                "payload": {
                    "time": local_time
                },
                "timestamp": timestamp
            }
            
        elif action_name == "get_system_status":
            # Extract basic metrics from grid state
            telemetry = grid_state.get("telemetry", {}) if grid_state else {}
            threat = grid_state.get("threat", {}) if grid_state else {}
            
            # Read state details
            threat_score = threat.get("threat_score", 0.0)
            
            grid_stability = "NORMAL"
            if threat_score > 70.0:
                grid_stability = "CRITICAL"
            elif threat_score > 30.0:
                grid_stability = "WARNING"
                
            return {
                "action": "get_system_status",
                "status": "SUCCESS",
                "payload": {
                    "stability": grid_stability,
                    "threat_score": threat_score,
                    "active_attack": bool(threat.get("affected_nodes")),
                    "voltage_nominal": telemetry.get("state", {}).get("buses", {}) != {}
                },
                "timestamp": timestamp
            }
            
        elif action_name == "open_dashboard":
            return {
                "action": "open_dashboard",
                "status": "SUCCESS",
                "payload": {
                    "target_page": "dashboard"
                },
                "timestamp": timestamp
            }
            
        elif action_name == "assistant_identity_response":
            return {
                "action": "assistant_identity_response",
                "status": "SUCCESS",
                "payload": {
                    "name": "Intelligent Grid Assistant",
                    "version": "Phase 9.1"
                },
                "timestamp": timestamp
            }
            
        # Fallback for future hooks or unsupported actions
        if action_name in self.n8n_hooks:
            return {
                "action": action_name,
                "status": "PENDING_AUTOMATION",
                "payload": {
                    "n8n_url": self.n8n_hooks[action_name],
                    "parameters": parameters
                },
                "timestamp": timestamp
            }
            
        return {
            "action": action_name,
            "status": "UNSUPPORTED",
            "payload": {},
            "timestamp": timestamp
        }
