import time
import re
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("assistant.n8n_bridge")

class N8nOrchestrationBridge:
    def __init__(self, base_backoff_sec: float = 0.1, max_retries: int = 3):
        self.base_backoff_sec = base_backoff_sec
        self.max_retries = max_retries
        
        # Lists of executions and active retries
        self.executions: List[Dict[str, Any]] = []
        self.active_retries: List[Dict[str, Any]] = []
        
        # Flag to simulate network failure (can be toggled for tests)
        self.simulate_network_failure = False

    def validate_payload(self, payload: Dict[str, Any]) -> bool:
        """
        Enforces parameter injection checks on values to prevent command injection.
        Blocks characters: ; & | $ ` \
        """
        injection_pattern = re.compile(r"[;&|\$`\\]")
        for k, v in payload.items():
            val_str = str(v)
            if injection_pattern.search(val_str):
                logger.warning(f"Payload validation failed! Command injection pattern found in key '{k}': '{val_str}'")
                return False
        return True

    def dispatch_webhook(self, 
                         webhook_name: str, 
                         payload: Dict[str, Any], 
                         force_failure: bool = False) -> Dict[str, Any]:
        """
        Attempts to dispatch a webhook payload.
        If validation fails, rejects it.
        If network failure occurs, schedules it in the retry queue.
        """
        now = time.time()
        execution_id = f"exec_{int(now * 1000)}"
        
        # 1. Validate payload
        if not self.validate_payload(payload):
            result = {
                "execution_id": execution_id,
                "webhook_name": webhook_name,
                "payload": payload,
                "status": "REJECTED",
                "error": "command_injection_detected",
                "timestamp": int(now * 1000),
                "retry_count": 0
            }
            self.executions.append(result)
            return result
            
        # 2. Simulate dispatch
        failed = force_failure or self.simulate_network_failure
        
        if failed:
            # Add to active retries queue (exponential backoff check)
            next_delay = self.base_backoff_sec * (2 ** 0) # 0.1s base
            retry_item = {
                "execution_id": execution_id,
                "webhook_name": webhook_name,
                "payload": payload,
                "retry_count": 0,
                "next_attempt_time": now + next_delay,
                "force_failure": force_failure
            }
            self.active_retries.append(retry_item)
            logger.warning(f"Webhook '{webhook_name}' dispatch failed. Scheduled retry in {next_delay}s.")
            
            result = {
                "execution_id": execution_id,
                "webhook_name": webhook_name,
                "payload": payload,
                "status": "RETRACTED_FOR_RETRY",
                "timestamp": int(now * 1000),
                "retry_count": 0
            }
            self.executions.append(result)
            return result
        else:
            # Successful dispatch
            result = {
                "execution_id": execution_id,
                "webhook_name": webhook_name,
                "payload": payload,
                "status": "SUCCESS",
                "timestamp": int(now * 1000),
                "retry_count": 0
            }
            self.executions.append(result)
            logger.info(f"Webhook '{webhook_name}' successfully dispatched.")
            return result

    def tick(self) -> List[Dict[str, Any]]:
        """
        Iterates over active retries and re-evaluates them statefully over tick loops.
        Returns a list of completed executions from retries.
        """
        now = time.time()
        still_retrying = []
        completed = []
        
        for item in self.active_retries:
            if now >= item["next_attempt_time"]:
                # Retry dispatch
                curr_retry = item["retry_count"] + 1
                
                # Check network condition again
                failed = self.simulate_network_failure or item["force_failure"]
                
                if failed:
                    if curr_retry >= self.max_retries:
                        # Mark as final failure
                        result = {
                            "execution_id": item["execution_id"],
                            "webhook_name": item["webhook_name"],
                            "payload": item["payload"],
                            "status": "FAILED",
                            "error": "max_retries_exceeded",
                            "timestamp": int(now * 1000),
                            "retry_count": curr_retry
                        }
                        self.executions.append(result)
                        completed.append(result)
                        logger.error(f"Webhook '{item['webhook_name']}' failed after {curr_retry} retries.")
                    else:
                        # Schedule next attempt with exponential delay
                        next_delay = self.base_backoff_sec * (2 ** curr_retry)
                        new_item = item.copy()
                        new_item["retry_count"] = curr_retry
                        new_item["next_attempt_time"] = now + next_delay
                        still_retrying.append(new_item)
                        logger.warning(f"Webhook '{item['webhook_name']}' retry {curr_retry} failed. Next in {next_delay}s.")
                else:
                    # Retry success
                    result = {
                        "execution_id": item["execution_id"],
                        "webhook_name": item["webhook_name"],
                        "payload": item["payload"],
                        "status": "SUCCESS",
                        "timestamp": int(now * 1000),
                        "retry_count": curr_retry
                    }
                    self.executions.append(result)
                    completed.append(result)
                    logger.info(f"Webhook '{item['webhook_name']}' successfully dispatched on retry {curr_retry}.")
            else:
                still_retrying.append(item)
                
        self.active_retries = still_retrying
        
        # Enforce execution history limit
        if len(self.executions) > 20:
            self.executions = self.executions[-20:]
            
        return completed

    def clear_history(self):
        self.executions.clear()
        self.active_retries.clear()

    def get_status_summary(self) -> Dict[str, Any]:
        """
        Returns execution history logs and active retries status.
        """
        return {
            "executions": self.executions,
            "active_retries_count": len(self.active_retries),
            "active_retries": [
                {
                    "execution_id": r["execution_id"],
                    "webhook_name": r["webhook_name"],
                    "retry_count": r["retry_count"],
                    "seconds_until_next": max(0.0, round(r["next_attempt_time"] - time.time(), 2))
                }
                for r in self.active_retries
            ],
            "total_executions": len(self.executions)
        }
