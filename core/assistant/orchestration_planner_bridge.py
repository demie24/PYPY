import logging
import json
import time
from typing import Dict, Any

logger = logging.getLogger("assistant.planner_bridge")

class OrchestrationPlannerBridge:
    def __init__(self, confidence_threshold: float = 0.50, min_stability: float = 30.0):
        self.confidence_threshold = confidence_threshold
        self.min_stability = min_stability
        self.validation_logs = []
        self.last_execution_status = "IDLE"
        self.last_confidence_score = 1.0

    def evaluate_confidence_and_safety(self, step: Dict[str, Any], grid_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validates safety constraints before executing critical planning steps.
        Enforces:
        - Confidence threshold (>= 0.50)
        - Excess escalation prevention (stability >= 30.0%)
        """
        objective = step.get("objective")
        parameters = step.get("parameters", {})
        
        # Determine if action is a critical grid control command
        is_critical = (
            objective == "TRIGGER_WORKFLOW" and parameters.get("workflow_name") == "emergency_load_shed"
        ) or (objective == "SHED_LOAD" or objective == "TRIP_BREAKER")

        if is_critical:
            threat_data = grid_state.get("threat", {})
            confidence = threat_data.get("confidence", 1.0)
            threat_score = threat_data.get("threat_score", 0.0)
            
            # Check grid stability index if available
            stability = grid_state.get("telemetry", {}).get("stability_index", 100.0)
            # Alternate mapping checks
            if "stability_score" in grid_state:
                stability = grid_state["stability_score"]
            elif "stability" in grid_state:
                stability = grid_state["stability"]

            self.last_confidence_score = confidence

            # Rule A: Confidence check
            if confidence < self.confidence_threshold:
                err_msg = f"Confidence score too low (less than {self.confidence_threshold:.2f}). Load shed rejected."
                self.validation_logs.append(f"SAFETY REJECTION: {err_msg}")
                return {"status": "FAILED", "error": err_msg}

            # Rule B: Excessive Escalation check
            if stability < self.min_stability:
                err_msg = "Grid stability collapsed below 30%. Operator manual override required."
                self.validation_logs.append(f"CRITICAL ESCALATION: {err_msg}")
                return {"status": "FAILED", "error": "escalate_to_operator", "reason": err_msg}

        return {"status": "SUCCESS"}

    def execute_step(
        self,
        chain_id: str,
        step: Dict[str, Any],
        grid_state: Dict[str, Any],
        n8n_bridge: Any,
        workflow_engine: Any,
        reminder_mgr: Any,
        mqtt_client: Any
    ) -> Dict[str, Any]:
        """
        Coordinates execution of a step against the corresponding subsystem.
        """
        objective = step.get("objective")
        params = step.get("parameters", {})
        
        # 1. Enforce safety checks
        safety_eval = self.evaluate_confidence_and_safety(step, grid_state)
        if safety_eval["status"] != "SUCCESS":
            self.last_execution_status = "SAFETY_BLOCKED"
            return safety_eval

        # 2. Map objectives to backend subsystems
        self.validation_logs.append(f"Bridging objective '{objective}' to backend at {time.strftime('%X')}")

        if objective == "MEASURE_LATENCY":
            # Simulate latency sweep or pull from state
            latency = grid_state.get("telemetry", {}).get("latency_ms", 45.0)
            # Alternate trigger parameter check
            if "latency_ms" in grid_state:
                latency = grid_state["latency_ms"]
            elif "latency" in grid_state:
                latency = grid_state["latency"]
            self.last_execution_status = "SUCCESS"
            return {"status": "SUCCESS", "result": latency}

        elif objective == "CHECK_LIMIT":
            field = params.get("field", "latency_ms")
            operator = params.get("operator", ">")
            threshold = params.get("threshold", 100.0)
            
            # Fetch current value from grid_state
            val = grid_state.get("telemetry", {}).get(field, 0.0)
            if "telemetry" not in grid_state or field not in grid_state["telemetry"]:
                # Try outer levels
                val = grid_state.get(field, 0.0)
                
            self.validation_logs.append(f"Evaluating limits: measured {field}={val} against threshold {operator}{threshold}")
            
            # Perform check
            triggered = False
            if operator == ">" and val > threshold:
                triggered = True
            elif operator == "<" and val < threshold:
                triggered = True
            elif operator == "==" and val == threshold:
                triggered = True
                
            if triggered:
                self.last_execution_status = "SUCCESS"
                return {"status": "SUCCESS", "result": "threshold_exceeded"}
            else:
                self.last_execution_status = "FAILED"
                return {"status": "FAILED", "error": "limit_not_exceeded", "reason": f"Value {val} is within limits ({operator}{threshold})."}

        elif objective == "TRIGGER_WORKFLOW":
            wf_name = params.get("workflow_name", "system_status_check")
            # If n8n workflow flag is enabled, route via n8n bridge
            if params.get("route_via_n8n", False) or "n8n" in wf_name:
                n8n_res = n8n_bridge.dispatch_webhook(f"n8n_{wf_name}", {"chain_id": chain_id})
                self.last_execution_status = n8n_res["status"]
                return n8n_res
            else:
                # Direct trigger using workflow callback hook
                wf_res = workflow_engine.execute_workflow(
                    wf_name,
                    grid_state,
                    # mock step executor pass-through
                    lambda wf, step_name: {"status": "SUCCESS"}
                )
                self.last_execution_status = wf_res["status"]
                return wf_res

        elif objective == "SCHEDULE_REMINDER":
            text = params.get("text", "Task Chain Alert")
            delay = params.get("delay_sec", 5.0)
            rem_res = reminder_mgr.add_reminder(text, delay)
            self.last_execution_status = rem_res["status"]
            return rem_res

        elif objective == "OPEN_DASHBOARD":
            panel = params.get("panel", "AssistantCognition")
            # Publish control command
            if mqtt_client:
                mqtt_client.publish("grid/control", json.dumps({
                    "command": "NAVIGATE_PANEL",
                    "panel": panel
                }))
            self.last_execution_status = "SUCCESS"
            return {"status": "SUCCESS", "result": f"Navigated to panel: {panel}"}

        elif objective in ["MONITOR_RELAY", "AWAIT_STABILITY", "MONITOR_MQTT"]:
            # Stateful monitor wait checks
            target = params.get("target", "relay_unstable")
            expected = params.get("expected_value", False)
            
            # Fetch target value
            curr_val = grid_state.get(target)
            if curr_val is None:
                # Look in telemetry
                curr_val = grid_state.get("telemetry", {}).get(target)
            if curr_val is None:
                # Look in threat
                curr_val = grid_state.get("threat", {}).get(target)
                
            self.validation_logs.append(f"Monitoring '{target}': current={curr_val}, expected={expected}")
            
            if curr_val == expected:
                self.last_execution_status = "SUCCESS"
                return {"status": "SUCCESS", "result": "stability_reached"}
            else:
                self.last_execution_status = "PAUSED"
                return {"status": "PAUSED"} # Wait and evaluate on next tick

        # Generic action router fallback
        self.last_execution_status = "SUCCESS"
        return {"status": "SUCCESS", "result": "generic_objective_ignored"}

    def get_status_summary(self) -> Dict[str, Any]:
        return {
            "last_execution_status": self.last_execution_status,
            "last_confidence_score": self.last_confidence_score,
            "validation_logs_count": len(self.validation_logs),
            "validation_logs": self.validation_logs[-5:]
        }
