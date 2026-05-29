import time
from typing import Dict, Any, Optional, List

class ProactiveAssistantEngine:
    def __init__(self, cooldown_period: float = 45.0):
        self.cooldown_period = cooldown_period
        
        # Maps alert_category -> last_triggered_timestamp (float)
        self.last_triggered_times: Dict[str, float] = {}
        self.notification_history: List[Dict[str, Any]] = []

    def scan_grid_state(self, 
                        grid_state: Dict[str, Any], 
                        hardware_state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Passively scans grid states, checks threat indices and latency boundaries,
        and generates non-intrusive Malay recommendations gated by safety rules.
        """
        threat_data = grid_state.get("threat", {})
        threat_score = float(threat_data.get("threat_score", 0.0))
        threat_confidence = float(threat_data.get("confidence", 1.0))
        grid_critical = (threat_score > 70.0)
        
        # 1. Require contextual confidence check (threshold >= 0.50)
        if threat_confidence < 0.50:
            return None
            
        now = time.time()
        
        # 2. Check individual alert conditions
        alert_category = None
        message = None
        is_minor = False
        
        # Check condition A: MQTT Comms offline
        # Look for explicit flags: comms_online = False
        if grid_state.get("comms_online") is False or hardware_state.get("comms_online") is False:
            alert_category = "broker_disconnect"
            message = "baby, MQTT broker disconnected"
            is_minor = False
            
        # Check condition B: Relay unstable
        elif grid_state.get("relay_unstable") is True or hardware_state.get("relay_unstable") is True:
            alert_category = "relay_unstable"
            message = "sistem relay nampak unstable"
            is_minor = False
            
        # Check condition C: Sync recovery
        elif grid_state.get("sync_recovered") is True or hardware_state.get("sync_recovered") is True:
            alert_category = "sync_recovered"
            message = "telemetry synchronization dah recover"
            is_minor = True
            
        # Check condition D: Latency spike
        # Check if latency exceeds 500ms or drift exceeds 0.5s or explicit flag
        else:
            latency_spike = False
            latency_ms = hardware_state.get("latency_ms", 0.0)
            drift_sec = hardware_state.get("drift_sec", 0.0)
            
            if latency_ms > 500.0 or drift_sec > 0.5 or hardware_state.get("latency_spike") is True:
                latency_spike = True
                
            if latency_spike:
                alert_category = "latency_spike"
                message = "saya detect latency spike pada edge node"
                is_minor = True

        # 3. Apply safety constraints
        if not alert_category or not message:
            return None
            
        # Rule 3A: Cooldown guard (avoid spam and repetitive alerts)
        last_triggered = self.last_triggered_times.get(alert_category, 0.0)
        if now - last_triggered < self.cooldown_period:
            return None
            
        # Rule 3B: Interruptions lockout (suppress minor warnings if grid threat > 70.0)
        if grid_critical and is_minor:
            return None
            
        # 4. Trigger alert proactive action
        self.last_triggered_times[alert_category] = now
        notification_payload = {
            "category": alert_category,
            "message": message,
            "timestamp": int(now * 1000),
            "is_minor": is_minor,
            "threat_score": threat_score,
            "confidence": threat_confidence
        }
        self.notification_history.append(notification_payload)
        
        # Enforce history limit
        if len(self.notification_history) > 20:
            self.notification_history.pop(0)
            
        return notification_payload

    def get_remaining_cooldown(self, category: str) -> float:
        """
        Returns seconds remaining of the cooldown for a category.
        """
        last_triggered = self.last_triggered_times.get(category, 0.0)
        elapsed = time.time() - last_triggered
        return max(0.0, self.cooldown_period - elapsed)

    def reset_cooldowns(self):
        """
        Clears trigger logs.
        """
        self.last_triggered_times.clear()
        self.notification_history.clear()

    def get_automation_summary(self) -> Dict[str, Any]:
        cooldowns = {}
        for cat in ["broker_disconnect", "relay_unstable", "sync_recovered", "latency_spike"]:
            cooldowns[cat] = round(self.get_remaining_cooldown(cat), 2)
            
        return {
            "total_notifications_sent": len(self.notification_history),
            "cooldown_timers": cooldowns,
            "latest_notification": self.notification_history[-1] if self.notification_history else None,
            "history": self.notification_history
        }
