import time
import uuid
import re
from typing import Dict, Any, List, Optional

class ConversationalPlanningEngine:
    def __init__(self, max_steps: int = 5):
        self.max_steps = max_steps
        self.active_plans: Dict[str, Dict[str, Any]] = {}
        self.plan_history: List[Dict[str, Any]] = []

    def create_plan(self, query: str, semantic_intent: Dict[str, Any]) -> Dict[str, Any]:
        """
        Decomposes a query into a multi-step sequence of objectives.
        Enforces Runaway Chain Prevention (max 5 steps).
        """
        plan_id = f"plan_{uuid.uuid4().hex[:8]}"
        steps = []
        reasoning_logs = []
        
        normalized = query.lower().strip()
        reasoning_logs.append(f"Decomposing user request: '{query}'")

        # Decompose specific templates or use default intent fallback
        if "latency" in normalized and ("tinggi" in normalized or "high" in normalized) and ("trigger" in normalized or "jalankan" in normalized):
            reasoning_logs.append("Matched pattern: Latency check with recovery trigger")
            steps = [
                {
                    "step_id": f"{plan_id}_s1",
                    "objective": "MEASURE_LATENCY",
                    "description": "Semak latency semasa edge node",
                    "status": "PENDING",
                    "dependencies": [],
                    "parameters": {"target": "latency_ms"}
                },
                {
                    "step_id": f"{plan_id}_s2",
                    "objective": "CHECK_LIMIT",
                    "description": "Nilaikan sama ada latency melebihi 100ms",
                    "status": "PENDING",
                    "dependencies": [f"{plan_id}_s1"],
                    "parameters": {"field": "latency_ms", "operator": ">", "threshold": 100.0}
                },
                {
                    "step_id": f"{plan_id}_s3",
                    "objective": "TRIGGER_WORKFLOW",
                    "description": "Jalankan recovery workflow jika latency tinggi",
                    "status": "PENDING",
                    "dependencies": [f"{plan_id}_s2"],
                    "parameters": {"workflow_name": "system_status_check"}
                }
            ]
        elif "dashboard" in normalized and "monitor" in normalized and "relay" in normalized:
            reasoning_logs.append("Matched pattern: Open dashboard and monitor relay stability")
            steps = [
                {
                    "step_id": f"{plan_id}_s1",
                    "objective": "OPEN_DASHBOARD",
                    "description": "Buka dashboard panel HMI",
                    "status": "PENDING",
                    "dependencies": [],
                    "parameters": {"panel": "AssistantCognition"}
                },
                {
                    "step_id": f"{plan_id}_s2",
                    "objective": "MONITOR_RELAY",
                    "description": "Mula memantau keadaan relay",
                    "status": "PENDING",
                    "dependencies": [f"{plan_id}_s1"],
                    "parameters": {"target": "relay_unstable"}
                },
                {
                    "step_id": f"{plan_id}_s3",
                    "objective": "AWAIT_STABILITY",
                    "description": "Tunggu sehingga status relay stabil",
                    "status": "PENDING",
                    "dependencies": [f"{plan_id}_s2"],
                    "parameters": {"target": "relay_unstable", "expected_value": False}
                }
            ]
        elif "mqtt" in normalized and "ingatkan" in normalized and "disconnect" in normalized:
            reasoning_logs.append("Matched pattern: Schedule reminder and check MQTT status")
            steps = [
                {
                    "step_id": f"{plan_id}_s1",
                    "objective": "SCHEDULE_REMINDER",
                    "description": "Jadualkan peringatan semak MQTT",
                    "status": "PENDING",
                    "dependencies": [],
                    "parameters": {"text": "Check MQTT Connection", "delay_sec": 5.0}
                },
                {
                    "step_id": f"{plan_id}_s2",
                    "objective": "MONITOR_MQTT",
                    "description": "Periksa status sambungan broker MQTT",
                    "status": "PENDING",
                    "dependencies": [f"{plan_id}_s1"],
                    "parameters": {"target": "comms_online"}
                },
                {
                    "step_id": f"{plan_id}_s3",
                    "objective": "NOTIFY_DISCONNECT",
                    "description": "Hantar notifikasi sekiranya sambungan terputus",
                    "status": "PENDING",
                    "dependencies": [f"{plan_id}_s2"],
                    "parameters": {"target": "comms_online", "alert_on_value": False}
                }
            ]
        elif "monitoring routine" in normalized or "routine monitoring" in normalized or "sistem edge node" in normalized:
            reasoning_logs.append("Matched pattern: Create edge node monitoring routine")
            steps = [
                {
                    "step_id": f"{plan_id}_s1",
                    "objective": "CREATE_ROUTINE",
                    "description": "Bina monitoring routine baharu untuk sistem edge",
                    "status": "PENDING",
                    "dependencies": [],
                    "parameters": {"routine_type": "edge_telemetry_scan"}
                },
                {
                    "step_id": f"{plan_id}_s2",
                    "objective": "MONITOR_EDGE",
                    "description": "Pantau telemetry edge node secara berterusan",
                    "status": "PENDING",
                    "dependencies": [f"{plan_id}_s1"],
                    "parameters": {"target": "latency_ms"}
                }
            ]
        else:
            # Fallback to single step derived from intent category
            category = semantic_intent.get("category", "UNKNOWN")
            action = semantic_intent.get("action", "unknown")
            reasoning_logs.append(f"No match for sequential pattern. Falling back to single-step: {category}")
            steps = [
                {
                    "step_id": f"{plan_id}_s1",
                    "objective": category,
                    "description": f"Jalankan tindakan berpandukan intent {action}",
                    "status": "PENDING",
                    "dependencies": [],
                    "parameters": {"action": action, "original_query": query}
                }
            ]

        # Enforce Runaway Chain Prevention limit
        if len(steps) > self.max_steps:
            reasoning_logs.append(f"WARNING: Plan size ({len(steps)}) exceeds max_steps ({self.max_steps}). Truncating chain.")
            steps = steps[:self.max_steps]

        plan = {
            "plan_id": plan_id,
            "original_query": query,
            "status": "CREATED",
            "steps": steps,
            "reasoning_logs": reasoning_logs,
            "timestamp": int(time.time() * 1000)
        }
        self.active_plans[plan_id] = plan
        return plan

    def get_plan(self, plan_id: str) -> Optional[Dict[str, Any]]:
        return self.active_plans.get(plan_id)

    def update_step_status(self, plan_id: str, step_id: str, status: str, log_message: str = None) -> bool:
        plan = self.get_plan(plan_id)
        if not plan:
            return False
            
        for step in plan["steps"]:
            if step["step_id"] == step_id:
                step["status"] = status
                if log_message:
                    plan["reasoning_logs"].append(log_message)
                
                # Update global plan status if all complete
                all_done = True
                failed = False
                for s in plan["steps"]:
                    if s["status"] == "FAILED":
                        failed = True
                    elif s["status"] != "SUCCESS":
                        all_done = False
                
                if failed:
                    plan["status"] = "FAILED"
                    if plan_id in self.active_plans:
                        self.plan_history.append(self.active_plans.pop(plan_id))
                elif all_done:
                    plan["status"] = "COMPLETED"
                    if plan_id in self.active_plans:
                        self.plan_history.append(self.active_plans.pop(plan_id))
                return True
        return False

    def get_status_summary(self) -> Dict[str, Any]:
        return {
            "active_plans_count": len(self.active_plans),
            "active_plans": list(self.active_plans.values()),
            "history_count": len(self.plan_history),
            "plan_history": self.plan_history[-5:] # Last 5 records
        }
