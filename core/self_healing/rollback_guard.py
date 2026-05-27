import time
import logging
from typing import List, Dict, Tuple, Any

logger = logging.getLogger("self_healing.rollback_guard")

class RollbackGuard:
    """
    Prevents repeated switching loop oscillations and blocks restoration attempts
    on breakers that recently failed safety verifications.
    """
    def __init__(self):
        self.lockouts: Dict[str, float] = {}  # breaker_id -> lockout_expiry_timestamp
        self.rollback_count: int = 0
        
    def reset(self):
        self.lockouts.clear()
        self.rollback_count = 0
        logger.info("RollbackGuard state cleared.")
        
    def lockout(self, target: str, duration: float = 60.0):
        """
        Locks out a breaker from close operations for the specified duration.
        """
        expiry = time.time() + duration
        self.lockouts[target] = expiry
        self.rollback_count += 1
        logger.warning(f"[ROLLBACK GUARD] Locked out breaker {target} for {duration} seconds.")
        
    def is_locked_out(self, target: str) -> bool:
        """
        Checks if a breaker is currently locked out.
        """
        if target in self.lockouts:
            if time.time() < self.lockouts[target]:
                return True
            else:
                # Lockout expired, clean it up
                del self.lockouts[target]
        return False
        
    def detect_oscillation(self, action_logs: List[Dict[str, Any]]) -> Tuple[bool, str]:
        """
        Checks if any breaker has been closed and opened repeatedly in a short window.
        Returns (oscillation_detected, reason_string).
        """
        now_ms = time.time() * 1000
        toggles = {}
        
        # We check logs within a 60-second window
        for log in action_logs:
            timestamp = log.get("timestamp", 0)
            if now_ms - timestamp < 60000:
                target = log.get("target")
                if target:
                    toggles[target] = toggles.get(target, 0) + 1
                    
        for target, count in toggles.items():
            # If a breaker was commanded 3 or more times (close/open/close or similar)
            if count >= 3:
                return True, f"Breaker {target} commanded {count} times within 60s (oscillation loop detected)."
                
        return False, ""
