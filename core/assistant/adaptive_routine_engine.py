import time
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("assistant.adaptive_routine")

class AdaptiveRoutineEngine:
    def __init__(self, repeat_threshold: int = 2):
        self.repeat_threshold = repeat_threshold
        self.interaction_history: List[Dict[str, Any]] = []
        
        # Maps command_name -> list of float timestamps
        self.command_counts: Dict[str, List[float]] = {}
        self.routines_recommended: List[Dict[str, Any]] = []

    def record_interaction(self, command_name: str, phrase: str):
        """
        Logs a user action and counts frequency patterns to find habits.
        """
        now = time.time()
        self.interaction_history.append({
            "command": command_name,
            "phrase": phrase,
            "timestamp": int(now * 1000)
        })
        
        if len(self.interaction_history) > 50:
            self.interaction_history.pop(0)
            
        if command_name not in self.command_counts:
            self.command_counts[command_name] = []
        self.command_counts[command_name].append(now)
        
        # Clean older command counts (e.g. older than 1 hour) to check local temporal frequency
        one_hour_ago = now - 3600.0
        self.command_counts[command_name] = [t for t in self.command_counts[command_name] if t >= one_hour_ago]
        
        # Re-evaluate routines
        self._evaluate_routines(command_name)

    def _evaluate_routines(self, command_name: str):
        """
        Generates routine recommendation recommendations if commands are repeated frequently.
        """
        count = len(self.command_counts[command_name])
        
        if count >= self.repeat_threshold:
            # Recommend scheduling automation
            exists = any(r["command"] == command_name for r in self.routines_recommended)
            if not exists:
                message = ""
                routine_type = ""
                if command_name == "get_system_status":
                    message = "Saya perasan operator selalu check status sistem. Nak saya schedule status check setiap pagi?"
                    routine_type = "daily_system_check"
                elif command_name == "open_dashboard":
                    message = "I noticed you open dashboard on system anomalies. Automate dashboard popups during critical states?"
                    routine_type = "anomaly_dashboard_popup"
                else:
                    message = f"You run '{command_name}' frequently. Automate this routine workflow?"
                    routine_type = f"automate_{command_name}"
                    
                self.routines_recommended.append({
                    "routine_type": routine_type,
                    "command": command_name,
                    "recommendation_message": message,
                    "frequency_per_hr": count,
                    "timestamp": int(time.time() * 1000),
                    "accepted": False
                })
                logger.info(f"Generated adaptive routine suggestion: '{routine_type}'")

    def accept_routine(self, routine_type: str) -> bool:
        for r in self.routines_recommended:
            if r["routine_type"] == routine_type:
                r["accepted"] = True
                logger.info(f"Routine '{routine_type}' accepted by operator.")
                return True
        return False

    def clear_routines(self):
        self.interaction_history.clear()
        self.command_counts.clear()
        self.routines_recommended.clear()

    def get_status_summary(self) -> Dict[str, Any]:
        """
        Returns serialized routine recommendation summaries.
        """
        return {
            "recommended_routines": self.routines_recommended,
            "routines_count": len(self.routines_recommended),
            "interaction_history": self.interaction_history,
            "command_frequencies": {k: len(v) for k, v in self.command_counts.items()}
        }
