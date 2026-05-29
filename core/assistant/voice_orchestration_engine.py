import time
import uuid
from typing import Dict, Any, Optional

class VoiceOrchestrationEngine:
    def __init__(self, session_timeout: float = 30.0):
        self.session_timeout = session_timeout
        
        # State registers
        self.state = "IDLE"  # Options: IDLE, WAKING, LISTENING, THINKING, SPEAKING
        self.active_session_id: Optional[str] = None
        self.session_expires_at: float = 0.0
        self.total_sessions_count = 0
        self.last_state_transition_time = time.time()

    def start_session(self) -> str:
        """
        Spawns a new voice interaction session.
        """
        self.active_session_id = str(uuid.uuid4())
        self.session_expires_at = time.time() + self.session_timeout
        self.total_sessions_count += 1
        self.transition_to("WAKING")
        return self.active_session_id

    def is_session_active(self) -> bool:
        """
        Returns True if a voice session is active and has not expired.
        """
        now = time.time()
        if self.active_session_id and now <= self.session_expires_at:
            return True
        # Clean up session if expired
        self.active_session_id = None
        self.session_expires_at = 0.0
        if self.state != "IDLE":
            self.transition_to("IDLE")
        return False

    def transition_to(self, new_state: str):
        """
        Transitions voice pipeline state and updates pacing logs.
        """
        valid_states = ["IDLE", "WAKING", "LISTENING", "THINKING", "SPEAKING"]
        if new_state in valid_states:
            self.state = new_state
            self.last_state_transition_time = time.time()

    def tick_session(self):
        """
        Extends the session expiry timer due to active voice interactions.
        """
        if self.active_session_id:
            self.session_expires_at = time.time() + self.session_timeout

    def end_session(self):
        """
        Terminates the active voice session and resets pipeline state.
        """
        self.active_session_id = None
        self.session_expires_at = 0.0
        self.transition_to("IDLE")

    def get_status_summary(self) -> Dict[str, Any]:
        session_active = self.is_session_active()
        time_left = max(0.0, self.session_expires_at - time.time()) if session_active else 0.0
        return {
            "voice_state": self.state,
            "session_active": session_active,
            "session_id": self.active_session_id,
            "time_remaining": round(time_left, 2),
            "total_sessions": self.total_sessions_count,
            "state_duration": round(time.time() - self.last_state_transition_time, 2)
        }
