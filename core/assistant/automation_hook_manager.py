import time
import re
from typing import Dict, Any, Optional

class AutomationHookManager:
    def __init__(self):
        # Webhook targets mapping
        self.endpoints = {
            "n8n_restoration": "http://n8n-broker:5678/webhook/restoration",
            "n8n_security_alert": "http://n8n-broker:5678/webhook/security_alert"
        }
        
        # Statistics registry
        self.trigger_count = 0
        self.latest_hook_status: Dict[str, Any] = {}

    def validate_parameters(self, params: Dict[str, Any]) -> bool:
        """
        Validates parameters to prevent remote injection attacks or malicious strings.
        Returns True if clean, False otherwise.
        """
        if not params:
            return True
            
        # Regex to prevent shell/code injections: blocks characters like ;, &, |, $, `, \
        injection_pattern = re.compile(r"[;&\|$`\\]")
        
        for key, val in params.items():
            str_val = str(val)
            if injection_pattern.search(str_val):
                return False
                
        return True

    def trigger_webhook(self, webhook_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Simulates dispatching webhook trigger payload.
        Verifies allowlist endpoints and executes security validations.
        """
        timestamp = int(time.time() * 1000)
        self.trigger_count += 1
        
        # Endpoint authorization check
        if webhook_name not in self.endpoints:
            status = {
                "hook_name": webhook_name,
                "status": "FAILED",
                "message": "UNAUTHORIZED_ENDPOINT",
                "timestamp": timestamp,
                "payload": {}
            }
            self.latest_hook_status = status
            return status

        # Security validation check
        params = payload.get("parameters", {})
        if not self.validate_parameters(params):
            status = {
                "hook_name": webhook_name,
                "status": "FAILED",
                "message": "SECURITY_VALIDATION_BLOCKED",
                "timestamp": timestamp,
                "payload": {}
            }
            self.latest_hook_status = status
            return status

        # Construct payload trigger
        url = self.endpoints[webhook_name]
        trigger_payload = {
            "trigger_id": f"trigger_{self.trigger_count}_{int(time.time())}",
            "endpoint_url": url,
            "timestamp": timestamp,
            "data": payload
        }
        
        status = {
            "hook_name": webhook_name,
            "status": "SUCCESS",
            "message": "TRIGGERED",
            "timestamp": timestamp,
            "payload": trigger_payload
        }
        self.latest_hook_status = status
        return status

    def get_automation_summary(self) -> Dict[str, Any]:
        return {
            "trigger_count": self.trigger_count,
            "latest_hook_status": self.latest_hook_status,
            "supported_hooks": list(self.endpoints.keys())
        }
