import time
import copy
import logging
from typing import Dict, Any, List, Tuple

logger = logging.getLogger("self_healing.action_rollback")

class RollbackCheckpoint:
    """
    Encapsulates a snapshot of the grid control and trust parameters at a point in time.
    """
    def __init__(self, breakers: Dict[str, str], trust_scores: Dict[str, Any] = None, timestamp: float = None):
        self.timestamp = timestamp if timestamp else time.time()
        self.breakers = copy.deepcopy(breakers)
        self.trust_scores = copy.deepcopy(trust_scores) if trust_scores else {}

class ActionRollbackManager:
    """
    Manages checkpoints and handles operator and autonomous rollback sequences.
    """
    def __init__(self):
        self.checkpoints: List[RollbackCheckpoint] = []
        self.max_checkpoints = 20

    def push_checkpoint(self, breakers: Dict[str, str], trust_scores: Dict[str, Any] = None) -> RollbackCheckpoint:
        """
        Saves a snapshot of breaker states and trust scores onto the rollback stack.
        """
        checkpoint = RollbackCheckpoint(breakers, trust_scores)
        self.checkpoints.append(checkpoint)
        
        # Enforce rolling history limit
        if len(self.checkpoints) > self.max_checkpoints:
            self.checkpoints.pop(0)
            
        logger.info(f"[ROLLBACK ENGINE] New checkpoint pushed. Total stored: {len(self.checkpoints)}")
        return checkpoint

    def pop_checkpoint(self) -> RollbackCheckpoint:
        """
        Pops and returns the most recent checkpoint from the stack.
        """
        if self.checkpoints:
            checkpoint = self.checkpoints.pop()
            logger.info(f"[ROLLBACK ENGINE] Checkpoint popped. Remaining: {len(self.checkpoints)}")
            return checkpoint
        return None

    def rollback_to_last(self) -> Tuple[Dict[str, str], Dict[str, Any]]:
        """
        Retrieves the last checkpoint state to revert grid parameters.
        Returns:
            breakers: Dict[str, str] (restored breaker states)
            trust_scores: Dict[str, Any] (restored telemetry trust scores)
        """
        checkpoint = self.pop_checkpoint()
        if checkpoint:
            return checkpoint.breakers, checkpoint.trust_scores
        logger.warning("[ROLLBACK ENGINE] Rollback requested, but no checkpoints exist.")
        return {}, {}

    def undo_sequence(self, num_steps: int) -> Tuple[Dict[str, str], Dict[str, Any]]:
        """
        Undoes multiple steps of actions by rolling back to an older checkpoint.
        """
        if not self.checkpoints:
            logger.warning("[ROLLBACK ENGINE] Undo sequence requested, but checkpoints stack is empty.")
            return {}, {}
            
        target_checkpoint = None
        steps_undone = 0
        
        while self.checkpoints and steps_undone < num_steps:
            target_checkpoint = self.checkpoints.pop()
            steps_undone += 1
            
        if target_checkpoint:
            logger.info(f"[ROLLBACK ENGINE] Undid {steps_undone} steps. Remaining checkpoints: {len(self.checkpoints)}")
            return target_checkpoint.breakers, target_checkpoint.trust_scores
            
        return {}, {}

    def get_readiness_status(self) -> Dict[str, Any]:
        """
        Returns rollback metadata for dashboard rendering.
        """
        return {
            "checkpoints_count": len(self.checkpoints),
            "rollback_available": len(self.checkpoints) > 0,
            "last_checkpoint_time": int(self.checkpoints[-1].timestamp * 1000) if self.checkpoints else 0
        }
