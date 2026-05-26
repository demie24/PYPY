import time
import logging
from typing import Dict, Any, List, Tuple

logger = logging.getLogger("self_healing.operator_override")

class OperatorOverrideEngine:
    """
    Manages operator-in-the-loop overrides, emergency halts, locks, and audits.
    """
    def __init__(self):
        self.pause_autonomous = False
        self.emergency_stop_active = False
        self.restoration_mode = "SEMI_AUTONOMOUS"  # ADVISORY, SEMI_AUTONOMOUS, AUTO
        self.execution_delay = 0.0                 # Delay before AI action execution in seconds
        
        self.locked_breakers: List[str] = []       # Breakers locked from AI control
        self.manual_approvals: Dict[str, bool] = {} # target_action -> approved status
        self.audit_logs: List[Dict[str, Any]] = []
        self.history_actions_executed: List[Tuple[str, str]] = [] # list of (action_name, target) for rollbacks

    def set_pause(self, paused: bool):
        self.pause_autonomous = paused
        self._log_override("SYSTEM", "SET_PAUSE", f"Autonomous mode set to {'PAUSED' if paused else 'RUNNING'}")
        
    def trigger_emergency_stop(self):
        self.emergency_stop_active = True
        self.pause_autonomous = True
        self._log_override("SYSTEM", "EMERGENCY_STOP", "CRITICAL: Emergency stop engaged. All autonomous grid controls locked.")

    def clear_emergency_stop(self):
        self.emergency_stop_active = False
        self._log_override("SYSTEM", "CLEAR_EMERGENCY_STOP", "Emergency stop disengaged. Autonomy stands by.")

    def set_restoration_mode(self, mode: str):
        valid_modes = ["ADVISORY", "SEMI_AUTONOMOUS", "AUTO"]
        if mode in valid_modes:
            self.restoration_mode = mode
            self._log_override("SYSTEM", "LOCK_MODE", f"Restoration control mode locked to: {mode}")
        else:
            logger.warning(f"Invalid restoration mode requested: {mode}")

    def set_execution_delay(self, seconds: float):
        self.execution_delay = max(0.0, float(seconds))
        self._log_override("SYSTEM", "SET_DELAY", f"Autonomous action execution delay set to {self.execution_delay:.1f}s")

    def lock_breaker(self, breaker: str):
        if breaker not in self.locked_breakers:
            self.locked_breakers.append(breaker)
            self._log_override(breaker, "LOCK_BREAKER", f"Breaker {breaker} statefully locked from autonomous control.")
            
    def unlock_breaker(self, breaker: str):
        if breaker in self.locked_breakers:
            self.locked_breakers.remove(breaker)
            self._log_override(breaker, "UNLOCK_BREAKER", f"Breaker {breaker} statefully unlocked.")

    def approve_action(self, action_name: str, target: str):
        key = f"{action_name}_{target}"
        self.manual_approvals[key] = True
        self._log_override(target, "APPROVE_ACTION", f"Operator approved action: [{action_name}] on target {target}")

    def clear_approval(self, action_name: str, target: str):
        key = f"{action_name}_{target}"
        if key in self.manual_approvals:
            del self.manual_approvals[key]

    def is_action_allowed(self, action_name: str, target: str) -> Tuple[bool, str]:
        """
        Validates whether an action is permitted by checking overrides and mode settings.
        """
        if self.emergency_stop_active:
            return False, "Emergency stop active: all controls statefully locked."

        if self.pause_autonomous:
            return False, "Autonomous execution paused by operator."
            
        if target in self.locked_breakers:
            return False, f"Breaker {target} is locked by the operator."

        # Advisory mode blocks automatic executions unconditionally
        if self.restoration_mode == "ADVISORY":
            return False, "Advisory mode active: all AI recommendations require operator approval."

        # Semi-Autonomous mode requires operator approval flag
        if self.restoration_mode == "SEMI_AUTONOMOUS":
            key = f"{action_name}_{target}"
            if not self.manual_approvals.get(key, False):
                return False, f"Semi-Autonomous: Action [{action_name}] on {target} requires explicit operator approval."

        # Auto mode or explicitly approved semi-autonomous action is allowed
        return True, "Operator override check approved."
        
    def record_execution(self, action_name: str, target: str):
        self.history_actions_executed.append((action_name, target))
        # Clear manual approval once executed to avoid replay
        key = f"{action_name}_{target}"
        if key in self.manual_approvals:
            del self.manual_approvals[key]
        
    def get_last_executed_action(self) -> Tuple[str, str]:
        if self.history_actions_executed:
            return self.history_actions_executed[-1]
        return "", ""
        
    def pop_last_executed_action(self):
        if self.history_actions_executed:
            self.history_actions_executed.pop()
            
    def _log_override(self, target: str, action: str, details: str):
        log_entry = {
            "timestamp": int(time.time() * 1000),
            "target": target,
            "action": action,
            "details": details
        }
        self.audit_logs.append(log_entry)
        logger.info(f"[OPERATOR OVERRIDE AUDIT] {action} targeting {target}: {details}")
        
    def get_audit_logs(self) -> List[Dict[str, Any]]:
        return self.audit_logs[-30:] # return last 30 logs
