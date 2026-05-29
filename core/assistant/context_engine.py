import time
from typing import Dict, Any, Optional

class ContextEngine:
    def __init__(self):
        self.session_active = False
        self.last_interaction_time = 0.0
        self.current_topic: Optional[str] = None
        self.previous_intent: Optional[Dict[str, Any]] = None
        self.assistant_state = "IDLE"
        self.interaction_depth = 0
        
    def update_context(self, intent: Dict[str, Any], state: str):
        """
        Updates session parameters based on new interaction.
        """
        now = time.time()
        self.assistant_state = state
        
        # Session timeout check (e.g. 5 minutes timeout)
        if not self.session_active or (now - self.last_interaction_time > 300.0):
            self.session_active = True
            self.interaction_depth = 1
        else:
            self.interaction_depth += 1
            
        self.last_interaction_time = now
        
        # Determine topic from intent action
        action = intent.get("action")
        if action:
            self.current_topic = action
            
        self.previous_intent = intent
        
    def reset_context(self):
        """
        Resets context flags.
        """
        self.session_active = False
        self.last_interaction_time = 0.0
        self.current_topic = None
        self.previous_intent = None
        self.assistant_state = "IDLE"
        self.interaction_depth = 0

    def get_context_summary(self) -> Dict[str, Any]:
        """
        Returns serialized context payload.
        """
        return {
            "session_active": self.session_active,
            "last_interaction_time": self.last_interaction_time,
            "current_topic": self.current_topic,
            "assistant_state": self.assistant_state,
            "interaction_depth": self.interaction_depth,
            "previous_action": self.previous_intent.get("action") if self.previous_intent else None
        }
