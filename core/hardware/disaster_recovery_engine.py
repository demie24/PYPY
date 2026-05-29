import time
import logging
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger("hardware.disaster_recovery")

class DisasterRecoveryEngine:
    def __init__(self):
        self.active_workflow: Optional[str] = None
        self.workflow_status = "IDLE"  # IDLE, IN_PROGRESS, COMPLETED, FAILED, ROLLING_BACK
        self.restoration_stage = 0
        self.recovery_checkpoints: Dict[str, Dict[str, str]] = {}
        self.rollback_active = False
        
        # Priority mapping for grid elements
        self.prioritized_infrastructure = ["L1_4", "L4_5", "L5_6", "L2_7", "L6_7", "L4_9", "L3_9", "L8_9", "L7_8"]
        
        # Dependencies mapping: target breaker -> list of breakers that must be CLOSED first
        self.restoration_dependencies = {
            "L4_5": ["L1_4"],
            "L5_6": ["L4_5"],
            "L6_7": ["L2_7"],
            "L4_9": ["L1_4"],
            "L8_9": ["L3_9"]
        }
        
        # Stages details for restoration workflows
        self.workflows = {
            "BLACKSTART_RESTORATION": [
                {"stage": 1, "action": "CLOSE", "target": "L1_4", "description": "Energize main generation path L1_4"},
                {"stage": 2, "action": "CLOSE", "target": "L4_5", "description": "Energize hospital bus path L4_5"},
                {"stage": 3, "action": "CLOSE", "target": "L5_6", "description": "Energize support load path L5_6"}
            ],
            "SYSTEM_RESET_RECOVERY": [
                {"stage": 1, "action": "OPEN", "target": "L7_8", "description": "Open tie-breaker L7_8 for segment isolation"},
                {"stage": 2, "action": "CLOSED", "target": "L1_4", "description": "Force close radial generator line L1_4"},
                {"stage": 3, "action": "CLOSED", "target": "L2_7", "description": "Force close generator connection L2_7"}
            ]
        }
        
    def start_recovery_workflow(self, workflow_name: str, current_breaker_states: Dict[str, str]) -> Tuple[bool, str]:
        """
        Triggers an automated staged disaster recovery sequence.
        Saves initial state as fallback checkpoint.
        """
        if workflow_name not in self.workflows:
            return False, f"Unknown disaster recovery workflow: {workflow_name}"
            
        self.active_workflow = workflow_name
        self.workflow_status = "IN_PROGRESS"
        self.restoration_stage = 1
        self.rollback_active = False
        
        # Save initial checkpoint
        checkpoint_id = f"init_{workflow_name}_{int(time.time())}"
        self.save_checkpoint(checkpoint_id, current_breaker_states)
        logger.info(f"Disaster Recovery workflow {workflow_name} initiated. Saved checkpoint {checkpoint_id}")
        
        return True, f"Workflow {workflow_name} started. Stage 1/3 pending."
        
    def save_checkpoint(self, checkpoint_id: str, breaker_states: Dict[str, str]):
        """
        Saves a copy of the breaker states configuration.
        """
        self.recovery_checkpoints[checkpoint_id] = breaker_states.copy()
        
    def execute_next_step(self, current_breaker_states: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """
        Calculates and returns the command representing the next restoration step,
        validating source paths and dependency requirements.
        """
        if self.workflow_status != "IN_PROGRESS" or not self.active_workflow:
            return None
            
        steps = self.workflows[self.active_workflow]
        current_step = None
        for step in steps:
            if step["stage"] == self.restoration_stage:
                current_step = step
                break
                
        if not current_step:
            self.workflow_status = "COMPLETED"
            self.active_workflow = None
            return None
            
        target = current_step["target"]
        action = current_step["action"]
        
        # Check restoration dependencies
        dependencies = self.restoration_dependencies.get(target, [])
        for dep in dependencies:
            state = current_breaker_states.get(dep, "OPEN")
            if state != "CLOSED" and state != "CLOSE":
                # Dependency not met!
                logger.error(f"Disaster Recovery blocked on stage {self.restoration_stage}. Dependent breaker {dep} is not CLOSED.")
                self.workflow_status = "FAILED"
                return None
                
        # Return command payload
        return {
            "command": action,
            "target": target,
            "source": "SAFETY_GUARD"  # Executed by safety guard override auth level
        }
        
    def handle_step_failure(self, failed_breaker: str, last_known_states: Dict[str, str]) -> List[Dict[str, Any]]:
        """
        Triggered when a restoration step fails (e.g. timeout or block).
        Initiates automated rollback sequence to last checkpoint.
        """
        self.rollback_active = True
        self.workflow_status = "ROLLING_BACK"
        logger.critical(f"Disaster Recovery step failed on {failed_breaker}! Initiating automated rollback sequence.")
        
        # Find latest checkpoint
        if not self.recovery_checkpoints:
            return []
            
        latest_checkpoint_id = list(self.recovery_checkpoints.keys())[-1]
        target_states = self.recovery_checkpoints[latest_checkpoint_id]
        
        rollback_commands = []
        for breaker_id, desired_state in target_states.items():
            current_state = last_known_states.get(breaker_id)
            if current_state != desired_state:
                rollback_commands.append({
                    "command": desired_state,
                    "target": breaker_id,
                    "source": "SAFETY_GUARD"
                })
        return rollback_commands

    def get_telemetry_payload(self) -> Dict[str, Any]:
        """
        Serializes current disaster recovery status.
        """
        return {
            "timestamp": int(time.time() * 1000),
            "active_workflow": self.active_workflow,
            "workflow_status": self.workflow_status,
            "restoration_stage": self.restoration_stage,
            "recovery_checkpoints": list(self.recovery_checkpoints.keys()),
            "restoration_dependencies": self.restoration_dependencies,
            "rollback_active": self.rollback_active,
            "prioritized_infrastructure": self.prioritized_infrastructure
        }
