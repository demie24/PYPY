import time
import logging
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger("hardware.relay_planner")

class RelayExecutionPlanner:
    def __init__(self, state_manager: Any):
        self.state_manager = state_manager
        # active_plans: plan_id -> plan_details
        self.active_plans: Dict[str, Dict[str, Any]] = {}
        # Completed history of plans
        self.history: List[Dict[str, Any]] = []
        
    def create_switching_plan(self, plan_id: str, steps: List[Dict[str, Any]]) -> Tuple[bool, str]:
        """
        Creates a sequential switching plan and runs preliminary safety validation.
        Each step: {"command": "OPEN"/"CLOSE", "target": "L1_4", "delay_ms": 200}
        """
        # Validate that we have steps
        if not steps:
            return False, "Switching plan must contain at least one step."
            
        # Run safety validation on the proposed final layout of the plan
        # E.g. Check if final state of the sequence isolates the generator
        simulated_relays = {k: v["coil"] for k, v in self.state_manager.relays.items()}
        
        for step in steps:
            target = step.get("target")
            cmd = step.get("command")
            if not target or target not in simulated_relays:
                return False, f"Target breaker {target} not registered in grid topology."
            simulated_relays[target] = "CLOSED" if cmd in ["CLOSE", "CLOSED"] else "OPEN"
            
        # Run generator interlock check on simulated end state
        closed_gens = sum(1 for gid in ["L1_4", "L2_7", "L3_9"] if simulated_relays[gid] == "CLOSED")
        if closed_gens < 1:
            return False, "Plan Rejected: Proposed switching sequence would isolate all generator transformers."
            
        self.active_plans[plan_id] = {
            "plan_id": plan_id,
            "steps": steps,
            "current_step_idx": 0,
            "status": "PENDING",
            "completed_steps": [],
            "rollback_steps": [],
            "created_time": time.time(),
            "next_execution_time": time.time(),
            "active_tx_id": None
        }
        
        logger.info(f"Relay Switching Plan created successfully: plan_id={plan_id} ({len(steps)} steps)")
        return True, "Switching plan approved."

    def tick_plans(self, now: float) -> List[Tuple[str, int, Dict[str, Any]]]:
        """
        Processes active plans. Returns a list of steps ready to be dispatched to the bus.
        Each entry: (plan_id, step_idx, step_command_payload)
        """
        dispatched_steps = []
        finished_plans = []
        
        for plan_id, plan in list(self.active_plans.items()):
            status = plan["status"]
            
            if status in ["PENDING", "RUNNING"]:
                # If waiting for active tx ACK, do nothing
                if plan["active_tx_id"] is not None:
                    continue
                    
                if now >= plan["next_execution_time"]:
                    idx = plan["current_step_idx"]
                    steps = plan["steps"]
                    
                    if idx < len(steps):
                        # Dispatch step
                        step = steps[idx]
                        plan["status"] = "RUNNING"
                        dispatched_steps.append((plan_id, idx, step))
                        # Place placeholder tx_id that orchestrator will update
                        plan["active_tx_id"] = "DISPATCHING"
                    else:
                        # Plan fully completed successfully!
                        plan["status"] = "COMPLETED"
                        plan["end_time"] = time.time()
                        finished_plans.append(plan_id)
                        logger.info(f"Relay switching plan {plan_id} completed successfully.")
                        
            elif status == "ROLLBACK":
                if plan["active_tx_id"] is not None:
                    continue
                    
                if now >= plan["next_execution_time"]:
                    idx = plan["current_step_idx"]
                    rollback_steps = plan["rollback_steps"]
                    
                    if idx < len(rollback_steps):
                        # Dispatch rollback step
                        step = rollback_steps[idx]
                        dispatched_steps.append((plan_id, idx, step))
                        plan["active_tx_id"] = "DISPATCHING"
                    else:
                        # Rollback sequence completed
                        plan["status"] = "ROLLED_BACK"
                        plan["end_time"] = time.time()
                        finished_plans.append(plan_id)
                        logger.warning(f"Coordinated rollback sequence completed for plan {plan_id}.")
                        
        # Move completed plans from active list to history log
        for plan_id in finished_plans:
            plan = self.active_plans.pop(plan_id)
            self._archive_plan(plan)
            
        return dispatched_steps

    def mark_step_result(self, plan_id: str, step_idx: int, success: bool, tx_id: str, reason: str = ""):
        """
        Receives the result of a dispatched step command. Advances plan or triggers rollback.
        """
        if plan_id not in self.active_plans:
            return
            
        plan = self.active_plans[plan_id]
        if plan["active_tx_id"] != tx_id:
            # Stale response
            return
            
        plan["active_tx_id"] = None
        status = plan["status"]
        
        if status == "RUNNING":
            step = plan["steps"][step_idx]
            if success:
                # Add to completed list so we can roll it back if later steps fail
                plan["completed_steps"].append(step)
                plan["current_step_idx"] += 1
                delay_s = step.get("delay_ms", 0.0) / 1000.0
                plan["next_execution_time"] = time.time() + delay_s
                logger.debug(f"Plan {plan_id} step {step_idx} succeeded. Next step scheduled in {delay_s}s.")
            else:
                # Failure! Build rollback sequence in reverse order of completed steps
                logger.error(f"Plan {plan_id} step {step_idx} failed: {reason}. Initiating automated rollback!")
                self._trigger_rollback(plan_id, reason)
                
        elif status == "ROLLBACK":
            step = plan["rollback_steps"][step_idx]
            if success:
                plan["current_step_idx"] += 1
                delay_s = step.get("delay_ms", 0.0) / 1000.0
                plan["next_execution_time"] = time.time() + delay_s
            else:
                # Critical: Rollback step itself failed!
                plan["status"] = "ROLLBACK_FAILED"
                plan["end_time"] = time.time()
                plan["error"] = f"Rollback step failed: {reason}"
                self.active_plans.pop(plan_id)
                self._archive_plan(plan)
                logger.critical(f"FATAL: Automated rollback failed on plan {plan_id} at step {step_idx}: {reason}")

    def _trigger_rollback(self, plan_id: str, fail_reason: str):
        plan = self.active_plans[plan_id]
        plan["status"] = "ROLLBACK"
        plan["error"] = fail_reason
        
        # Build rollback steps: reverse order, opposite commands
        rollback_steps = []
        for step in reversed(plan["completed_steps"]):
            rev_cmd = "OPEN" if step["command"] in ["CLOSE", "CLOSED"] else "CLOSE"
            rollback_steps.append({
                "command": rev_cmd,
                "target": step["target"],
                "delay_ms": step.get("delay_ms", 100) # standard recovery speed
            })
            
        plan["rollback_steps"] = rollback_steps
        plan["current_step_idx"] = 0
        plan["next_execution_time"] = time.time() # start rollback immediately
        logger.warning(f"Coordinated rollback plan initialized for {plan_id} with {len(rollback_steps)} steps.")

    def _archive_plan(self, plan: Dict[str, Any]):
        self.history.append(plan)
        if len(self.history) > 30:
            self.history.pop(0)

    def get_telemetry_payload(self) -> Dict[str, Any]:
        """
        Builds telemetry status representing switching plans.
        """
        active_list = []
        for plan_id, plan in self.active_plans.items():
            active_list.append({
                "plan_id": plan_id,
                "status": plan["status"],
                "progress": f"{plan['current_step_idx']}/{len(plan['steps']) if plan['status'] != 'ROLLBACK' else len(plan['rollback_steps'])}",
                "error": plan.get("error", "")
            })
            
        recent_logs = []
        for plan in reversed(self.history):
            recent_logs.append({
                "timestamp": int(plan.get("end_time", time.time()) * 1000),
                "plan_id": plan["plan_id"],
                "status": plan["status"],
                "steps_count": len(plan["steps"]),
                "completed_count": len(plan["completed_steps"]),
                "error": plan.get("error", "")
            })
            
        return {
            "timestamp": int(time.time() * 1000),
            "active_plans": active_list,
            "history": recent_logs
        }
