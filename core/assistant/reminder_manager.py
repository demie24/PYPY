import time
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("assistant.reminder_manager")

class ReminderManager:
    def __init__(self, spam_cooldown: float = 10.0):
        # List of reminder dicts:
        # { "reminder_id": str, "text": str, "trigger_time": float, "recurring_interval": Optional[float], "created_at": float }
        self.reminders: List[Dict[str, Any]] = []
        self.triggered_history: List[Dict[str, Any]] = []
        self.spam_cooldown = spam_cooldown
        
        # Track last reminder text -> last_registered_time (float) to prevent spam
        self.last_registration_times: Dict[str, float] = {}

    def add_reminder(self, 
                     text: str, 
                     delay_sec: float, 
                     recurring_interval: Optional[float] = None) -> Dict[str, Any]:
        """
        Schedules a new reminder with delay in seconds.
        Enforces cooldown rules to prevent spam registration.
        """
        now = time.time()
        
        # Check spam cooldown
        last_reg = self.last_registration_times.get(text, 0.0)
        if now - last_reg < self.spam_cooldown:
            logger.warning(f"Reminder spam blocked: '{text}'")
            return {
                "status": "BLOCKED",
                "reason": "cooldown_active",
                "cooldown_remaining": round(self.spam_cooldown - (now - last_reg), 2)
            }
            
        self.last_registration_times[text] = now
        
        reminder_id = f"rem_{int(now * 1000)}"
        trigger_time = now + delay_sec
        
        reminder = {
            "reminder_id": reminder_id,
            "text": text,
            "trigger_time": trigger_time,
            "recurring_interval": recurring_interval,
            "created_at": now
        }
        
        self.reminders.append(reminder)
        logger.info(f"Scheduled reminder {reminder_id} in {delay_sec}s: '{text}' (Recurring: {recurring_interval})")
        return {
            "status": "SCHEDULED",
            "reminder_id": reminder_id,
            "reminder": reminder
        }

    def tick(self) -> List[Dict[str, Any]]:
        """
        Evaluates reminder triggers.
        Returns a list of triggered reminders.
        """
        now = time.time()
        triggered = []
        pending = []
        
        for rem in self.reminders:
            if now >= rem["trigger_time"]:
                # Trigger it!
                triggered_log = {
                    "reminder_id": rem["reminder_id"],
                    "text": rem["text"],
                    "triggered_at": int(now * 1000),
                    "original_created_at": int(rem["created_at"] * 1000)
                }
                triggered.append(rem)
                self.triggered_history.append(triggered_log)
                
                # Limit history size
                if len(self.triggered_history) > 20:
                    self.triggered_history.pop(0)
                
                # Handle recurring rescheduling
                if rem["recurring_interval"] and rem["recurring_interval"] > 0:
                    new_rem = rem.copy()
                    new_rem["trigger_time"] = now + rem["recurring_interval"]
                    new_rem["created_at"] = now
                    pending.append(new_rem)
            else:
                pending.append(rem)
                
        self.reminders = pending
        return triggered

    def cancel_reminder(self, reminder_id: str) -> bool:
        """
        Cancels a scheduled reminder by ID.
        """
        initial_len = len(self.reminders)
        self.reminders = [r for r in self.reminders if r["reminder_id"] != reminder_id]
        success = len(self.reminders) < initial_len
        if success:
            logger.info(f"Cancelled reminder: {reminder_id}")
        return success

    def clear_all(self):
        """
        Wipes active reminders.
        """
        self.reminders.clear()
        self.triggered_history.clear()
        self.last_registration_times.clear()

    def get_status_summary(self) -> Dict[str, Any]:
        """
        Returns serialized summary of reminders for telemetry and HMI.
        """
        now = time.time()
        active_list = []
        for r in self.reminders:
            active_list.append({
                "reminder_id": r["reminder_id"],
                "text": r["text"],
                "time_remaining_sec": max(0.0, round(r["trigger_time"] - now, 2)),
                "recurring_interval": r["recurring_interval"]
            })
            
        return {
            "active_reminders": active_list,
            "active_count": len(self.reminders),
            "triggered_history": self.triggered_history,
            "total_triggered": len(self.triggered_history)
        }
