import re
from typing import Dict, Any, Set, List

class SemanticIntentEngine:
    def __init__(self, jaccard_threshold: float = 0.40):
        self.jaccard_threshold = jaccard_threshold
        
        # Action mappings to reference keywords sets
        self.reference_keywords = {
            "open_youtube": {"youtube", "yt", "main", "pasang"},
            "open_browser": {"browser", "pelayar", "web", "google", "internet", "chrome"},
            "get_time": {"pukul", "jam", "time", "masa", "waktu", "jam-jam"},
            "get_system_status": {"status", "grid", "sistem", "keadaan", "ok", "health"},
            "open_dashboard": {"dashboard", "scada", "hmi", "buka"},
            "assistant_identity_response": {"siapa", "nama", "identity", "who", "diri"}
        }
        
        # Keywords suggesting pronoun references or context continuity request
        self.followup_keywords = {
            "yang tadi", "tadi tu", "buka balik", "yang awak cakap", 
            "yang operator minta", "seperti tadi", "yang lepas", "yang tu"
        }

    def _preprocess(self, text: str) -> Set[str]:
        """
        Cleans text, strips punctuation, and returns a set of lowercase words.
        """
        if not text:
            return set()
        clean = text.lower().strip()
        # Remove punctuation
        clean = re.sub(r"[^\w\s-]", "", clean)
        return set(clean.split())

    def calculate_jaccard(self, set_a: Set[str], set_b: Set[str]) -> float:
        """
        Computes the standard Jaccard Similarity between two sets.
        """
        if not set_a or not set_b:
            return 0.0
        intersection = set_a.intersection(set_b)
        union = set_a.union(set_b)
        return len(intersection) / len(union)

    def detect_intent(self, text: str, previous_action: str = None) -> Dict[str, Any]:
        """
        Detects intent utilizing fuzzy Jaccard matching, regex, and follow-up continuity.
        """
        if not text or not isinstance(text, str):
            return {
                "category": "UNKNOWN",
                "action": None,
                "confidence": 0.0,
                "parameters": {},
                "is_fuzzy": False,
                "is_followup": False
            }

        clean_text = text.lower().strip()
        input_words = self._preprocess(text)
        
        # 1. Check for ambiguous follow-up / conversational reference
        is_followup = False
        for kw in self.followup_keywords:
            if kw in clean_text:
                is_followup = True
                break
                
        if is_followup and previous_action:
            # Resolve to the previous action
            category = "COMMAND"
            if previous_action == "get_time":
                category = "UTILITY"
            elif previous_action == "assistant_identity_response":
                category = "CONVERSATION"
                
            return {
                "category": category,
                "action": previous_action,
                "confidence": 0.90,
                "parameters": {"resolved_from_context": True},
                "is_fuzzy": True,
                "is_followup": True
            }

        # 2. Fuzzy set matching using Jaccard Similarity
        best_action = None
        best_score = 0.0
        
        for action, ref_set in self.reference_keywords.items():
            score = self.calculate_jaccard(input_words, ref_set)
            # If the query contains the action keyword explicitly, give it a boost
            for word in input_words:
                if word in ref_set:
                    score = max(score, 0.45) # baseline hit
            if score > best_score:
                best_score = score
                best_action = action
                
        # 3. Fallback regex checks for precise matches
        if best_score < self.jaccard_threshold:
            # Let's check regex baseline
            regex_patterns = {
                "open_youtube": r"youtube|yt",
                "open_browser": r"browser|pelayar|web|internet",
                "get_time": r"pukul|jam|time|masa|waktu",
                "get_system_status": r"status|grid|sistem|keadaan",
                "open_dashboard": r"dashboard|scada|hmi",
                "assistant_identity_response": r"siapa (awak|kau|diri|nama)"
            }
            for action, pattern in regex_patterns.items():
                if re.search(pattern, clean_text):
                    best_action = action
                    best_score = 0.75
                    break

        if best_action and best_score >= self.jaccard_threshold:
            if best_action == "get_time":
                category = "UTILITY"
            elif best_action == "assistant_identity_response":
                category = "CONVERSATION"
            else:
                category = "COMMAND"
                
            # Basic parameter extraction
            params = {}
            if "zone" in clean_text:
                zone_match = re.search(r"zone\s*(\d+)", clean_text)
                if zone_match:
                    params["zone"] = f"zone_{zone_match.group(1)}"
            if "bus" in clean_text:
                bus_match = re.search(r"bus\s*(\d+)", clean_text)
                if bus_match:
                    params["bus"] = f"Bus_{bus_match.group(1)}"

            return {
                "category": category,
                "action": best_action,
                "confidence": round(best_score, 2),
                "parameters": params,
                "is_fuzzy": True,
                "is_followup": False
            }

        # 4. Check for greeting fallback
        greetings = {r"hai", r"hello", r"salam", r"assalamualaikum", r"hi", r"apa khabar"}
        for greet in greetings:
            if re.search(greet, clean_text):
                return {
                    "category": "CONVERSATION",
                    "action": "greeting",
                    "confidence": 0.80,
                    "parameters": {},
                    "is_fuzzy": False,
                    "is_followup": False
                }

        return {
            "category": "CONVERSATION",
            "action": "generic_chat",
            "confidence": 0.50,
            "parameters": {},
            "is_fuzzy": False,
            "is_followup": False
        }
