from typing import Dict, Any, List

class EmotionEngine:
    def __init__(self):
        self.assistant_mood = "calm"
        self.user_mood = "calm"
        self.user_mood_confidence = 1.0
        self.mood_history: List[str] = ["calm"]
        
        # Keyword-based emotional tone mapper
        self.mood_keywords = {
            "happy": ["gembira", "seronok", "best", "hebat", "gempak", "mantap", "bagus", "happy", "senang", "senyum"],
            "excited": ["wah", "jom", "excited", "yeah", "yes", "hebat gila", "padu", "power", "canggih"],
            "sad": ["sedih", "kecewa", "hampa", "gagal", "sad", "susah hati", "bimbang", "risau", "takut"],
            "tired": ["penat", "letih", "mengantuk", "malas", "tired", "sleepy", "lemah", "letih"],
            "serious": ["kecemasan", "bahaya", "penting", "cepat", "sistem rosak", "critical", "serius", "emergency", "attack", "serang", "pencerobohan"]
        }
        
    def detect_user_emotion(self, text: str) -> str:
        """
        Scans text keywords to infer user emotional state and calculates confidence score.
        """
        if not text or not isinstance(text, str):
            self.user_mood = "calm"
            self.user_mood_confidence = 1.0
            return "calm"
            
        clean_text = text.lower().strip()
        matched_mood = None
        match_count = 0
        
        for emotion, keywords in self.mood_keywords.items():
            current_matches = 0
            for kw in keywords:
                if kw in clean_text:
                    current_matches += 1
            if current_matches > 0:
                if matched_mood is None or current_matches > match_count:
                    matched_mood = emotion
                    match_count = current_matches
                    
        if matched_mood:
            self.user_mood = matched_mood
            # Confidence based on match count (scales up, maxing at 1.0)
            self.user_mood_confidence = min(0.5 + (match_count * 0.15), 1.0)
            return matched_mood
            
        self.user_mood = "calm"
        self.user_mood_confidence = 0.85
        return "calm"
        
    def modulate_assistant_emotion(self, user_mood: str, grid_critical: bool) -> str:
        """
        Adjusts assistant mood state incorporating user context and grid stress.
        If grid is under active attack or overload, immediately overrides to serious.
        Implements mood continuity/momentum via historical tracking.
        """
        if grid_critical:
            target_mood = "serious"
        else:
            # Empathy mapping
            if user_mood == "sad":
                target_mood = "sad"
            elif user_mood == "tired":
                target_mood = "tired"
            elif user_mood == "happy":
                target_mood = "happy"
            elif user_mood == "excited":
                target_mood = "excited"
            elif user_mood == "serious":
                target_mood = "focused"
            else:
                target_mood = "calm"
                
        # Mood continuity: Add target to history and keep last 3 ticks
        self.mood_history.append(target_mood)
        if len(self.mood_history) > 3:
            self.mood_history.pop(0)
            
        # Determine current mood based on majority or highest severity (serious > focused > happy/sad/tired > calm)
        # If grid is critical, serious is forced immediately
        if "serious" in self.mood_history:
            self.assistant_mood = "serious"
        elif "focused" in self.mood_history:
            self.assistant_mood = "focused"
        else:
            # Simple majority or last state
            self.assistant_mood = self.mood_history[-1]
            
        return self.assistant_mood
        
    def get_emotion_summary(self) -> Dict[str, Any]:
        return {
            "assistant_mood": self.assistant_mood,
            "user_mood": self.user_mood,
            "user_mood_confidence": self.user_mood_confidence,
            "mood_history": self.mood_history
        }
