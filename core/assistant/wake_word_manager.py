import time
from typing import Dict, Any

class WakeWordManager:
    def __init__(self, attention_timeout: float = 8.0):
        self.attention_timeout = attention_timeout
        
        # State registers
        self.attention_active = False
        self.attention_locked_until = 0.0
        self.last_wake_word = None
        self.last_confidence = 0.0
        
        # Wake words and matching confidence mappings
        self.wake_words = {
            "hey pypy": 1.0,
            "baby": 1.0,
            "assistant": 1.0,
            "pypy": 0.8,
            "hey baby": 1.0,
            "assistent": 0.8
        }

    def detect_wake_word(self, text: str) -> Dict[str, Any]:
        """
        Checks if text contains a wake word, calculates matching confidence,
        and statefully locks the assistant attention if confidence >= 0.70.
        """
        if not text:
            return {
                "detected": False,
                "wake_word": None,
                "confidence": 0.0,
                "attention_active": self.is_attention_locked()
            }
            
        clean_text = text.lower().strip()
        best_match = None
        best_conf = 0.0
        
        for word, conf in self.wake_words.items():
            if word in clean_text:
                if conf > best_conf:
                    best_conf = conf
                    best_match = word
                    
        # Apply false activation protection (gate confidence >= 0.70)
        detected = (best_conf >= 0.70)
        
        if detected:
            self.attention_active = True
            self.attention_locked_until = time.time() + self.attention_timeout
            self.last_wake_word = best_match
            self.last_confidence = best_conf
            
        return {
            "detected": detected,
            "wake_word": best_match,
            "confidence": best_conf,
            "attention_active": self.is_attention_locked()
        }

    def is_attention_locked(self) -> bool:
        """
        Returns True if the attention window is active and has not expired yet.
        """
        now = time.time()
        if self.attention_active and now <= self.attention_locked_until:
            return True
        self.attention_active = False
        return False

    def extend_attention(self, duration: float = None):
        """
        Extends the active attention window (default to attention_timeout).
        """
        ext = duration if duration is not None else self.attention_timeout
        self.attention_active = True
        self.attention_locked_until = time.time() + ext

    def get_time_remaining(self) -> float:
        """
        Returns attention seconds remaining, or 0.0 if expired.
        """
        if not self.is_attention_locked():
            return 0.0
        return max(0.0, self.attention_locked_until - time.time())

    def reset_attention(self):
        """
        Clears attention lockout state.
        """
        self.attention_active = False
        self.attention_locked_until = 0.0
        self.last_wake_word = None
        self.last_confidence = 0.0

    def get_status_summary(self) -> Dict[str, Any]:
        return {
            "attention_active": self.is_attention_locked(),
            "time_remaining": round(self.get_time_remaining(), 2),
            "last_wake_word": self.last_wake_word,
            "last_confidence": self.last_confidence
        }
