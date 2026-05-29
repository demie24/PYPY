import time
import math
from typing import Dict, Any

class AssistantPresenceEngine:
    def __init__(self):
        self.start_time = time.time()
        self.attention_state = "ATTENTIVE"  # FOCUS, ATTENTIVE, DIVERTED
        self.last_interaction_time = time.time()
        
        # Breathing frequencies by FSM state (Hz)
        self.frequencies = {
            "IDLE": 1.0,
            "LISTENING": 1.0,
            "THINKING": 0.5,
            "RESPONDING": 1.5,
            "EXECUTING": 1.5,
            "ERROR": 2.2
        }

    def update_attention(self, active_session: bool, active_attention: bool):
        """
        Statefully updates attention states based on user activity.
        """
        now = time.time()
        if active_session or active_attention:
            self.attention_state = "FOCUS"
            self.last_interaction_time = now
        else:
            # Shift to diverted if idle for more than 15 seconds
            if now - self.last_interaction_time > 15.0:
                self.attention_state = "DIVERTED"
            else:
                self.attention_state = "ATTENTIVE"

    def get_breathing_coordinate(self, fsm_state: str) -> float:
        """
        Generates a cyclic value from -1.0 to +1.0 using a sine-wave function,
        modulating frequency statefully depending on the active state.
        """
        freq = self.frequencies.get(fsm_state, 1.0)
        elapsed = time.time() - self.start_time
        
        # Add slight irregularity for ERROR state
        if fsm_state == "ERROR":
            # Blended sine waves to simulate irregular flutter
            val = 0.7 * math.sin(2 * math.pi * freq * elapsed) + 0.3 * math.sin(2 * math.pi * 5.0 * elapsed)
            return max(-1.0, min(1.0, val))
            
        return math.sin(2 * math.pi * freq * elapsed)

    def calculate_pacing_delay(self, 
                               emotion_mood: str, 
                               grid_critical: bool) -> float:
        """
        Calculates conversational response delay (seconds) to simulate pacing.
        If grid is critical, response is immediate (0.0s).
        """
        if grid_critical:
            return 0.0
            
        # Modulate pacing delay by mood
        if emotion_mood == "excited":
            return 0.15
        elif emotion_mood == "tired":
            return 1.10
        elif emotion_mood in ["serious", "focused"]:
            return 0.30
        else:
            # calm or default
            return 0.50

    def get_status_summary(self, fsm_state: str) -> Dict[str, Any]:
        elapsed = time.time() - self.last_interaction_time
        return {
            "attention_state": self.attention_state,
            "breathing_coordinate": round(self.get_breathing_coordinate(fsm_state), 4),
            "breathing_frequency_hz": self.frequencies.get(fsm_state, 1.0),
            "idle_duration_sec": round(elapsed, 2)
        }
