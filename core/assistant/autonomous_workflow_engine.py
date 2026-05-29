import time
import logging
from typing import Dict, Any, List, Optional, Callable

logger = logging.getLogger("assistant.autonomous_workflow")

class AutonomousWorkflowEngine:
    def __init__(self, workflow_cooldown: float = 10.0, max_call_depth: int = 3):
        self.workflow_cooldown = workflow_cooldown
        self.max_call_depth = max_call_depth
        
        # Maps workflow_name -> last_execution_time (float)
        self.last_execution_times: Dict[str, float] = {}
        
        # Delayed tasks queue:
        # { "task_id": str, "name": str, "trigger_time": float, "payload": Dict, "callback": Callable }
        self.delayed_tasks: List[Dict[str, Any]] = []
        
        # Active workflow executions logs
        # { "run_id": str, "name": str, "status": str, "steps": List[Dict], "started_at": float, "completed_at": Optional[float] }
        self.executions: List[Dict[str, Any]] = []
        
        # Track recursive call stack
        self.active_call_stack: List[str] = []

    def schedule_delayed_task(self, 
                              name: str, 
                              delay_sec: float, 
                              callback: Callable, 
                              payload: Dict[str, Any]) -> str:
        """
        Schedules a non-blocking delayed task.
        """
        now = time.time()
        task_id = f"task_{int(now * 1000)}"
        self.delayed_tasks.append({
            "task_id": task_id,
            "name": name,
            "trigger_time": now + delay_sec,
            "payload": payload,
            "callback": callback
        })
        logger.info(f"Scheduled delayed task '{name}' ({task_id}) in {delay_sec}s")
        return task_id

    def tick(self) -> List[Dict[str, Any]]:
        """
        Evaluates active delayed tasks.
        """
        now = time.time()
        triggered = []
        pending = []
        
        for task in self.delayed_tasks:
            if now >= task["trigger_time"]:
                try:
                    logger.info(f"Executing delayed task '{task['name']}' ({task['task_id']})")
                    # Fire callback
                    res = task["callback"](task["payload"])
                    triggered.append({
                        "task_id": task["task_id"],
                        "name": task["name"],
                        "result": res,
                        "timestamp": int(now * 1000)
                    })
                except Exception as e:
                    logger.error(f"Error executing delayed task callback '{task['name']}': {e}")
                    triggered.append({
                        "task_id": task["task_id"],
                        "name": task["name"],
                        "error": str(e),
                        "timestamp": int(now * 1000)
                    })
            else:
                pending.append(task)
                
        self.delayed_tasks = pending
        return triggered

    def execute_workflow(self, 
                         workflow_name: str, 
                         grid_state: Dict[str, Any], 
                         execute_step_fn: Callable) -> Dict[str, Any]:
        """
        Coordinates workflow execution, safety gates checks, cooldown limits,
        and recursive call stack loops prevention.
        """
        now = time.time()
        run_id = f"wf_run_{int(now * 1000)}"
        
        # 1. Cooldown Protection
        last_run = self.last_execution_times.get(workflow_name, 0.0)
        if now - last_run < self.workflow_cooldown:
            logger.warning(f"Workflow '{workflow_name}' rejected: Cooldown active.")
            res = {
                "run_id": run_id,
                "workflow_name": workflow_name,
                "status": "FAILED",
                "error": "cooldown_active",
                "message": f"Workflow is in cooldown. Please wait {round(self.workflow_cooldown - (now - last_run), 2)}s.",
                "steps": [],
                "timestamp": int(now * 1000)
            }
            self.executions.append(res)
            return res
            
        # 2. Recursive Loop Prevention Check
        if workflow_name in self.active_call_stack:
            logger.error(f"Recursive loop detected: '{workflow_name}' re-entered active stack {self.active_call_stack}!")
            res = {
                "run_id": run_id,
                "workflow_name": workflow_name,
                "status": "FAILED",
                "error": "recursive_loop_prevented",
                "message": "Recursive loop prevented. Call chain aborted.",
                "steps": [],
                "timestamp": int(now * 1000)
            }
            self.executions.append(res)
            return res
            
        if len(self.active_call_stack) >= self.max_call_depth:
            logger.error(f"Max call chain depth exceeded: {len(self.active_call_stack)} >= {self.max_call_depth}!")
            res = {
                "run_id": run_id,
                "workflow_name": workflow_name,
                "status": "FAILED",
                "error": "max_depth_exceeded",
                "message": f"Max workflow call depth of {self.max_call_depth} exceeded. Execution aborted.",
                "steps": [],
                "timestamp": int(now * 1000)
            }
            self.executions.append(res)
            return res
            
        # Add to stack trace
        self.active_call_stack.append(workflow_name)
        self.last_execution_times[workflow_name] = now
        
        wf_record = {
            "run_id": run_id,
            "workflow_name": workflow_name,
            "status": "RUNNING",
            "steps": [],
            "timestamp": int(now * 1000)
        }
        self.executions.append(wf_record)
        
        # 3. Confidence Gates checking (require >= 0.50 parameters for critical steps)
        threat_data = grid_state.get("threat", {})
        threat_conf = float(threat_data.get("confidence", 1.0))
        
        # Mocking workflow steps details
        steps = []
        if workflow_name == "emergency_load_shed":
            steps = ["check_threat_confidence", "shed_bus_5_load", "verify_voltage_levels"]
        elif workflow_name == "recursive_loop_test":
            steps = ["trigger_recursion_step"]
        elif workflow_name == "system_status_check":
            steps = ["validate_physics_step", "check_comms_status", "report_system_nominal"]
        else:
            steps = ["nominal_step_1", "nominal_step_2"]
            
        success = True
        error_msg = None
        
        for idx, step in enumerate(steps):
            step_record = {"step_name": step, "status": "PENDING"}
            wf_record["steps"].append(step_record)
            
            # Evaluate step safety overrides
            if step == "check_threat_confidence" or step == "shed_bus_5_load":
                if threat_conf < 0.50:
                    step_record["status"] = "FAILED"
                    step_record["error"] = "insufficient_confidence"
                    success = False
                    error_msg = "Confidence score too low (less than 0.50). Load shed rejected."
                    break
                    
            # Run simulation execution callback
            try:
                step_res = execute_step_fn(workflow_name, step)
                if step_res.get("status") == "SUCCESS":
                    step_record["status"] = "SUCCESS"
                    step_record["result"] = step_res.get("result")
                else:
                    step_record["status"] = "FAILED"
                    step_record["error"] = step_res.get("error", "unknown_step_failure")
                    success = False
                    error_msg = step_res.get("error")
                    break
            except Exception as e:
                step_record["status"] = "FAILED"
                step_record["error"] = str(e)
                success = False
                error_msg = str(e)
                break
                
        # Pop call stack
        self.active_call_stack.pop()
        
        # Update final execution record
        wf_record["status"] = "SUCCESS" if success else "FAILED"
        if error_msg:
            wf_record["error"] = error_msg
        wf_record["completed_at"] = time.time()
        
        # Limit history
        if len(self.executions) > 20:
            self.executions = self.executions[-20:]
            
        return wf_record

    def clear_history(self):
        self.executions.clear()
        self.delayed_tasks.clear()
        self.last_execution_times.clear()
        self.active_call_stack.clear()

    def get_remaining_cooldown(self, workflow_name: str) -> float:
        last_run = self.last_execution_times.get(workflow_name, 0.0)
        elapsed = time.time() - last_run
        return max(0.0, self.workflow_cooldown - elapsed)

    def get_status_summary(self) -> Dict[str, Any]:
        cooldowns = {}
        for wf in ["system_status_check", "emergency_load_shed", "recursive_loop_test"]:
            cooldowns[wf] = round(self.get_remaining_cooldown(wf), 2)
            
        return {
            "executions": self.executions,
            "delayed_tasks_count": len(self.delayed_tasks),
            "delayed_queue": [
                {
                    "task_id": t["task_id"],
                    "name": t["name"],
                    "time_remaining_sec": max(0.0, round(t["trigger_time"] - time.time(), 2))
                }
                for t in self.delayed_tasks
            ],
            "cooldown_timers": cooldowns,
            "call_stack": self.active_call_stack,
            "total_executions": len(self.executions)
        }
