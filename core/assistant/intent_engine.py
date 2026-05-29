import re
from typing import Dict, Any

class IntentEngine:
    def __init__(self):
        # Action keywords mappings
        self.command_keywords = {
            "open_youtube": [r"youtube", r"buka yt", r"main youtube", r"pasang youtube"],
            "open_browser": [r"browser", r"buka browser", r"pelayar web", r"chrome", r"internet"],
            "get_time": [r"pukul berapa", r"jam berapa", r"time", r"masa sekarang", r"waktu"],
            "get_system_status": [r"status", r"keadaan grid", r"grid ok", r"system status", r"status sistem", r"sistem ok"],
            "open_dashboard": [r"dashboard", r"buka dashboard", r"scada", r"hmi"],
            "assistant_identity_response": [r"siapa awak", r"siapa kau", r"identity", r"nama anda", r"siapa diri", r"who are you"]
        }

    def detect_intent(self, text: str) -> Dict[str, Any]:
        """
        Classifies input query into categories (COMMAND, CONVERSATION, UTILITY, UNKNOWN),
        resolves command target/action, and scores confidence.
        """
        if not text or not isinstance(text, str):
            return {
                "category": "UNKNOWN",
                "action": None,
                "confidence": 0.0,
                "parameters": {}
            }
            
        clean_text = text.lower().strip()
        
        # Check command/utility matches
        matched_action = None
        highest_score = 0.0
        
        for action, patterns in self.command_keywords.items():
            for pattern in patterns:
                if re.search(pattern, clean_text):
                    # Direct keyword match gives high confidence
                    matched_action = action
                    highest_score = 0.95
                    break
            if matched_action:
                break
                
        # If action detected, classify category
        if matched_action:
            if matched_action == "get_time":
                category = "UTILITY"
            elif matched_action == "assistant_identity_response":
                category = "CONVERSATION"
            else:
                category = "COMMAND"
                
            # Basic parameter parsing (e.g. target path, grid zones)
            params = {}
            if "zone" in clean_text:
                zone_match = re.search(r"zone\s*(\d+)", clean_text)
                if zone_match:
                    params["zone"] = f"zone_{zone_match.group(1)}"
                    
            return {
                "category": category,
                "action": matched_action,
                "confidence": highest_score,
                "parameters": params
            }
            
        # Fallback: check if it's general conversation/greetings
        greetings = [r"hai", r"hello", r"salam", r"assalamualaikum", r"hi", r"apa khabar", r"tanya sikit"]
        for greet in greetings:
            if re.search(greet, clean_text):
                return {
                    "category": "CONVERSATION",
                    "action": "greeting",
                    "confidence": 0.80,
                    "parameters": {}
                }
                
        # If it doesn't match any, it is unknown/generic conversational
        return {
            "category": "CONVERSATION",
            "action": "generic_chat",
            "confidence": 0.50,
            "parameters": {}
        }
