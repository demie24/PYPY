import time
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("assistant.condition_monitor")

class ConditionMonitorEngine:
    def __init__(self):
        # List of watched conditions:
        # { "condition_id": str, "type": str, "target_field": str, "operator": str, "threshold": Any, "cooldown": float, "is_recurring": bool, "last_triggered": float }
        self.watches: Dict[str, Dict[str, Any]] = {}
        self.trigger_history: List[Dict[str, Any]] = []
        
        # Load default system watches
        self._register_default_watches()

    def _register_default_watches(self):
        """
        Registers default system telemetry condition monitors.
        """
        self.register_watch(
            condition_id="high_latency_watch",
            watch_type="telemetry_threshold",
            target_field="latency_ms",
            operator=">",
            threshold=500.0,
            cooldown=45.0,
            is_recurring=True
        )
        self.register_watch(
            condition_id="broker_disconnect_watch",
            watch_type="comms_status",
            target_field="comms_online",
            operator="==",
            threshold=False,
            cooldown=45.0,
            is_recurring=True
        )
        self.register_watch(
            condition_id="critical_threat_watch",
            watch_type="threat_level",
            target_field="threat_score",
            operator=">",
            threshold=70.0,
            cooldown=45.0,
            is_recurring=True
        )

    def register_watch(self,
                       condition_id: str,
                       watch_type: str,
                       target_field: str,
                       operator: str,
                       threshold: Any,
                       cooldown: float = 45.0,
                       is_recurring: bool = True) -> bool:
        """
        Registers a new condition watch.
        """
        self.watches[condition_id] = {
            "condition_id": condition_id,
            "type": watch_type,
            "target_field": target_field,
            "operator": operator,
            "threshold": threshold,
            "cooldown": cooldown,
            "is_recurring": is_recurring,
            "last_triggered": 0.0
        }
        logger.info(f"Registered condition monitor: {condition_id} watches {target_field} {operator} {threshold}")
        return True

    def remove_watch(self, condition_id: str) -> bool:
        if condition_id in self.watches:
            del self.watches[condition_id]
            logger.info(f"Removed condition monitor: {condition_id}")
            return True
        return False

    def scan(self, grid_state: Dict[str, Any], hardware_state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Inspects telemetry metrics and evaluates registered conditions.
        Returns a list of triggered condition payloads.
        """
        now = time.time()
        triggered_watches = []
        
        # Flatten state keys for easier lookups
        flat_state = {}
        
        # Pull telemetry
        telem = grid_state.get("telemetry", {})
        for k, v in telem.items():
            flat_state[k] = v
            
        # Pull threat
        threat = grid_state.get("threat", {})
        flat_state["threat_score"] = float(threat.get("threat_score", 0.0))
        flat_state["confidence"] = float(threat.get("confidence", 1.0))
        
        # Pull flags
        flat_state["comms_online"] = grid_state.get("comms_online", True) and hardware_state.get("comms_online", True)
        flat_state["relay_unstable"] = grid_state.get("relay_unstable", False) or hardware_state.get("relay_unstable", False)
        flat_state["sync_recovered"] = grid_state.get("sync_recovered", False) or hardware_state.get("sync_recovered", False)
        
        # Pull hardware
        flat_state["latency_ms"] = float(hardware_state.get("latency_ms", 0.0))
        flat_state["drift_sec"] = float(hardware_state.get("drift_sec", 0.0))
        flat_state["latency_spike"] = hardware_state.get("latency_spike", False)
        
        # Evaluate watches
        for cond_id, w in list(self.watches.items()):
            field = w["target_field"]
            if field not in flat_state:
                continue
                
            val = flat_state[field]
            op = w["operator"]
            thresh = w["threshold"]
            
            # Perform check
            match = False
            try:
                if op == ">":
                    match = float(val) > float(thresh)
                elif op == "<":
                    match = float(val) < float(thresh)
                elif op == "==":
                    match = val == thresh
                elif op == "!=":
                    match = val != thresh
            except Exception as e:
                logger.error(f"Error checking condition {cond_id}: {e}")
                continue
                
            if match:
                # Check cooldown limits
                last_trig = w["last_triggered"]
                if now - last_trig >= w["cooldown"]:
                    # Trigger condition escalation event
                    w["last_triggered"] = now
                    
                    event_payload = {
                        "condition_id": cond_id,
                        "type": w["type"],
                        "target_field": field,
                        "current_value": val,
                        "threshold": thresh,
                        "timestamp": int(now * 1000)
                    }
                    
                    triggered_watches.append(event_payload)
                    self.trigger_history.append(event_payload)
                    
                    if len(self.trigger_history) > 20:
                        self.trigger_history.pop(0)
                        
                    if not w["is_recurring"]:
                        # Remove if single-shot
                        del self.watches[cond_id]
                        
        return triggered_watches

    def clear_history(self):
        self.trigger_history.clear()

    def get_status_summary(self) -> Dict[str, Any]:
        """
        Returns serialized watches list and escalation logs.
        """
        now = time.time()
        watches_list = []
        for cond_id, w in self.watches.items():
            elapsed = now - w["last_triggered"]
            cooldown_left = max(0.0, w["cooldown"] - elapsed) if w["last_triggered"] > 0.0 else 0.0
            
            watches_list.append({
                "condition_id": cond_id,
                "type": w["type"],
                "target_field": w["target_field"],
                "operator": w["operator"],
                "threshold": w["threshold"],
                "cooldown_remaining_sec": round(cooldown_left, 2),
                "is_recurring": w["is_recurring"]
            })
            
        return {
            "registered_watches": watches_list,
            "watches_count": len(self.watches),
            "trigger_history": self.trigger_history,
            "total_triggers": len(self.trigger_history)
        }
