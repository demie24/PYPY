from typing import Dict, Any

class AssistantStateManager:
    def __init__(self):
        # States: IDLE, LISTENING, THINKING, EXECUTING, RESPONDING, ERROR
        self.state = "IDLE"
        
    def transition_to(self, new_state: str) -> bool:
        """
        State transitions verification logic.
        """
        valid_states = ["IDLE", "LISTENING", "THINKING", "EXECUTING", "RESPONDING", "ERROR"]
        if new_state not in valid_states:
            self.state = "ERROR"
            return False
            
        self.state = new_state
        return True
        
    def get_state_summary(self) -> Dict[str, Any]:
        return {
            "state": self.state
        }
