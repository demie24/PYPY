import time
import logging
from typing import Dict, Any, List, Optional, Callable

logger = logging.getLogger("assistant.task_chain_manager")

class TaskChainManager:
    def __init__(self, step_timeout_sec: float = 15.0, max_active_chains: int = 3):
        self.step_timeout_sec = step_timeout_sec
        self.max_active_chains = max_active_chains
        self.active_chains: Dict[str, Dict[str, Any]] = {}
        self.completed_chains: List[Dict[str, Any]] = []

    def submit_chain(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        Submits a conversational plan as a stateful task chain.
        Enforces:
        - Runaway Chain Prevention (max 3 active chains).
        - Recursive Chain Detection (reject duplicate queries in the active chain stack).
        """
        plan_id = plan["plan_id"]
        original_query = plan["original_query"]

        # 1. Runaway Chain Prevention
        if len(self.active_chains) >= self.max_active_chains:
            return {
                "status": "REJECTED",
                "error": "runaway_chain_prevention",
                "reason": "Max active task chains limit reached (3 active chains max)."
            }

        # 2. Recursive Chain Detection
        for active_id, active in self.active_chains.items():
            if active["original_query"] == original_query:
                return {
                    "status": "REJECTED",
                    "error": "recursive_chain_prevented",
                    "reason": f"Recursive loop block: Task chain '{original_query}' is already running."
                }

        # Format chain state
        chain = {
            "chain_id": plan_id,
            "original_query": original_query,
            "status": "PENDING",
            "steps": plan["steps"],
            "current_step_idx": 0,
            "step_started_at": 0.0,
            "logs": [f"Chain submitted at {time.strftime('%X')}"],
            "timestamp": int(time.time() * 1000)
        }
        self.active_chains[plan_id] = chain
        return {"status": "SUBMITTED", "chain_id": plan_id}

    def cancel_chain(self, chain_id: str) -> bool:
        if chain_id in self.active_chains:
            chain = self.active_chains.pop(chain_id)
            chain["status"] = "CANCELLED"
            chain["logs"].append("Chain cancelled by user/operator command.")
            self.completed_chains.append(chain)
            return True
        return False

    def tick(self, execute_step_fn: Callable[[str, Dict[str, Any]], Dict[str, Any]], grid_state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Ticks execution of all active chains.
        Enforces step timeouts (default 15s) and dependency checks.
        """
        completed_signals = []
        now = time.time()
        
        # Iterate over a copy of active keys
        for chain_id in list(self.active_chains.keys()):
            chain = self.active_chains[chain_id]
            steps = chain["steps"]
            idx = chain["current_step_idx"]

            # Verify index boundaries
            if idx >= len(steps):
                chain["status"] = "COMPLETED"
                chain["logs"].append("All plan steps executed successfully.")
                self.completed_chains.append(self.active_chains.pop(chain_id))
                completed_signals.append({"chain_id": chain_id, "status": "COMPLETED"})
                continue

            step = steps[idx]
            
            # Initiate state changes
            if chain["status"] == "PENDING":
                chain["status"] = "EXECUTING"
                chain["step_started_at"] = now
                step["status"] = "RUNNING"
                chain["logs"].append(f"Started step '{step['objective']}': {step['description']}")
            elif chain["status"] == "PAUSED":
                # Check if delay completed
                delay_sec = step["parameters"].get("delay_sec", 0.0)
                if now - chain["step_started_at"] >= delay_sec:
                    chain["status"] = "EXECUTING"
                    chain["step_started_at"] = now
                    step["status"] = "RUNNING"
                    chain["logs"].append(f"Resumed execution after {delay_sec}s delay.")
                else:
                    # Still waiting
                    continue

            # Check for Step Timeout (Safety Rule)
            if chain["status"] == "EXECUTING" and (now - chain["step_started_at"] > self.step_timeout_sec):
                step["status"] = "FAILED"
                chain["status"] = "FAILED"
                chain["logs"].append(f"Step '{step['objective']}' timed out after {self.step_timeout_sec}s.")
                self.completed_chains.append(self.active_chains.pop(chain_id))
                completed_signals.append({"chain_id": chain_id, "status": "TIMEOUT", "error": f"Step timeout after {self.step_timeout_sec}s"})
                continue

            # Execute Step Logic
            if chain["status"] == "EXECUTING":
                # Check Dependencies (Dependency Guard)
                dep_ok = True
                for dep in step["dependencies"]:
                    # Find dependency status
                    for prev_step in steps[:idx]:
                        if prev_step["step_id"] == dep and prev_step["status"] != "SUCCESS":
                            dep_ok = False
                
                if not dep_ok:
                    step["status"] = "FAILED"
                    chain["status"] = "FAILED"
                    chain["logs"].append(f"Dependency check failed for '{step['objective']}'.")
                    self.completed_chains.append(self.active_chains.pop(chain_id))
                    completed_signals.append({"chain_id": chain_id, "status": "FAILED", "error": "dependency_failed"})
                    continue

                # Run callback execution hook
                res = execute_step_fn(chain_id, step)
                status = res.get("status", "SUCCESS")
                
                if status == "SUCCESS":
                    step["status"] = "SUCCESS"
                    chain["logs"].append(f"Completed step '{step['objective']}' successfully.")
                    chain["current_step_idx"] += 1
                    chain["step_started_at"] = now
                    
                    # Look ahead to see if next step is a delay/wait step
                    next_idx = chain["current_step_idx"]
                    if next_idx < len(steps):
                        next_step = steps[next_idx]
                        if next_step["objective"] == "SCHEDULE_REMINDER" or "delay_sec" in next_step["parameters"]:
                            chain["status"] = "PAUSED"
                            next_step["status"] = "RUNNING"
                            chain["logs"].append(f"Pausing execution: delay step scheduled.")
                        else:
                            # Start next step directly on next tick
                            chain["step_started_at"] = now
                            next_step["status"] = "RUNNING"
                            chain["logs"].append(f"Initiated step '{next_step['objective']}'")
                    else:
                        # Reached completion
                        chain["status"] = "COMPLETED"
                        chain["logs"].append("All plan steps executed successfully.")
                        self.completed_chains.append(self.active_chains.pop(chain_id))
                        completed_signals.append({"chain_id": chain_id, "status": "COMPLETED"})
                        
                elif status == "PAUSED":
                    chain["status"] = "PAUSED"
                    chain["step_started_at"] = now # mark delay start
                    step["status"] = "RUNNING"
                    chain["logs"].append(f"Paused execution at step '{step['objective']}' for dynamic wait/delay.")
                
                elif status == "FAILED":
                    # Attempt Recovery Continuation
                    recovery_wf = step["parameters"].get("recovery_workflow")
                    if recovery_wf:
                        chain["logs"].append(f"Step failed. Initiating recovery continuation workflow '{recovery_wf}'.")
                        # Run recovery action directly
                        rec_res = execute_step_fn(chain_id, {"objective": "TRIGGER_WORKFLOW", "parameters": {"workflow_name": recovery_wf}})
                        if rec_res.get("status") == "SUCCESS":
                            step["status"] = "SUCCESS" # recover
                            chain["logs"].append("Recovery continuation completed successfully.")
                            chain["current_step_idx"] += 1
                            chain["step_started_at"] = now
                            continue
                    
                    step["status"] = "FAILED"
                    chain["status"] = "FAILED"
                    chain["logs"].append(f"Step '{step['objective']}' execution failed: {res.get('error', 'unknown error')}")
                    self.completed_chains.append(self.active_chains.pop(chain_id))
                    completed_signals.append({"chain_id": chain_id, "status": "FAILED", "error": res.get("error", "execution_failed")})
                    
        return completed_signals

    def get_status_summary(self) -> Dict[str, Any]:
        return {
            "active_chains_count": len(self.active_chains),
            "active_chains": list(self.active_chains.values()),
            "completed_chains_count": len(self.completed_chains),
            "completed_chains": self.completed_chains[-5:] # Last 5 records
        }
