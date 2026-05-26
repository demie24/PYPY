import json
import logging
from typing import Dict, Any, List, Set

logger = logging.getLogger("cyber_defense.containment_engine")

class ContainmentEngine:
    """
    Executes containment command dispatches: isolates corrupted telemetry,
    locks unstable line topology, suppresses compromised breaker commands,
    and establishes zonal split isolation borders.
    """
    def __init__(self):
        self.isolated_telemetry: Set[str] = set()
        self.locked_breakers: Set[str] = set()
        self.active_containments: List[Dict[str, Any]] = []

    def dispatch_containment(self, 
                             coordinated_defense: Dict[str, Any], 
                             mqtt_client) -> List[Dict[str, Any]]:
        """
        Dispatches control actions based on the recommendations from the coordinator.
        Returns a log of dispatched actions.
        """
        dispatched_logs = []
        
        # 1. Handle recommended actions (e.g., REJECT_TELEMETRY, ISOLATE_LINE)
        recommended_actions = coordinated_defense.get("recommended_defense_actions", [])
        for rec in recommended_actions:
            action_type = rec.get("action")
            target = rec.get("target")
            priority = rec.get("priority", "MEDIUM")
            reason = rec.get("reason", "")
            
            if not target:
                continue
                
            if action_type == "REJECT_TELEMETRY":
                if target not in self.isolated_telemetry:
                    self.isolated_telemetry.add(target)
                    payload = {
                        "command": "REJECT_TELEMETRY",
                        "target": target,
                        "source": "AUTONOMOUS_CONTAINMENT"
                    }
                    try:
                        mqtt_client.publish("grid/control", json.dumps(payload))
                        log_msg = f"Dispatched telemetry isolation for {target} (Priority: {priority})"
                        logger.warning(log_msg)
                        dispatched_logs.append({
                            "action": "REJECT_TELEMETRY",
                            "target": target,
                            "status": "DISPATCHED",
                            "message": log_msg,
                            "reason": reason
                        })
                    except Exception as e:
                        logger.error(f"Failed to publish reject command: {e}")
                        
            elif action_type == "ISOLATE_LINE":
                payload = {
                    "command": "OPEN",
                    "target": target,
                    "source": "AUTONOMOUS_CONTAINMENT"
                }
                try:
                    mqtt_client.publish("grid/control", json.dumps(payload))
                    log_msg = f"Dispatched breaker trip command to isolate line {target}"
                    logger.warning(log_msg)
                    dispatched_logs.append({
                        "action": "ISOLATE_LINE",
                        "target": target,
                        "status": "DISPATCHED",
                        "message": log_msg,
                        "reason": reason
                    })
                except Exception as e:
                    logger.error(f"Failed to publish isolate command: {e}")

        # 2. Handle Breaker Lockdowns (lock downstream breakers in compromised nodes)
        lockdown_targets = coordinated_defense.get("breaker_lockdown_targets", [])
        for target in lockdown_targets:
            if target not in self.locked_breakers:
                self.locked_breakers.add(target)
                log_msg = f"Locking breaker {target} against autonomous restoration attempts."
                logger.warning(log_msg)
                dispatched_logs.append({
                    "action": "LOCK_BREAKER",
                    "target": target,
                    "status": "LOCKED",
                    "message": log_msg,
                    "reason": "Compromised topological neighborhood containment"
                })
                
        # Remove locks if they are no longer in the list (reconciliation/de-escalation)
        unlocked = []
        for locked in list(self.locked_breakers):
            if locked not in lockdown_targets:
                self.locked_breakers.remove(locked)
                unlocked.append(locked)
                
        for target in unlocked:
            log_msg = f"Releasing containment lock on breaker {target}."
            logger.info(log_msg)
            dispatched_logs.append({
                "action": "UNLOCK_BREAKER",
                "target": target,
                "status": "UNLOCKED",
                "message": log_msg,
                "reason": "Defense escalation level de-escalated"
            })

        # Update active containments cache
        self.active_containments = [
            {"target": item, "type": "TELEMETRY_ISOLATION"} for item in self.isolated_telemetry
        ] + [
            {"target": item, "type": "BREAKER_LOCKDOWN"} for item in self.locked_breakers
        ]
        
        return dispatched_logs

    def get_status(self) -> Dict[str, Any]:
        return {
            "isolated_telemetry_sources": list(self.isolated_telemetry),
            "locked_breakers": list(self.locked_breakers),
            "active_containments": self.active_containments
        }

    def reset(self, mqtt_client=None):
        """Resets the state of the containment engine."""
        # Restore telemetry trust for any isolated sources
        if mqtt_client:
            for target in list(self.isolated_telemetry):
                payload = {
                    "command": "RESTORE_TELEMETRY_TRUST",
                    "target": target,
                    "source": "CONTAINMENT_RESET"
                }
                mqtt_client.publish("grid/control", json.dumps(payload))
                
        self.isolated_telemetry.clear()
        self.locked_breakers.clear()
        self.active_containments.clear()
        logger.info("Containment engine states reset.")
