import time
import re
from typing import Dict, Any, Optional

class SemanticResponseEngine:
    def __init__(self):
        pass

    def clean_tts(self, text: str) -> str:
        """
        Removes any formatting characters (markdown, bold, asterisks, headers)
        to make responses voice-ready for Speech Synthesizers (TTS).
        """
        if not text:
            return ""
        # Remove asterisks
        cleaned = text.replace("*", "")
        # Remove markdown headers
        cleaned = re.sub(r"^#+\s+", "", cleaned, flags=re.MULTILINE)
        # Remove other markdown artifacts like _
        cleaned = cleaned.replace("_", "")
        return cleaned.strip()

    def generate_response(self, 
                          reasoning: Dict[str, Any], 
                          action_result: Dict[str, Any], 
                          emotion: Dict[str, Any]) -> str:
        """
        Generates natural context-aware response based on reasoning outcomes, results, and emotions.
        """
        import re # Ensure re is imported locally
        
        assistant_mood = emotion.get("assistant_mood", "calm")
        resolved_action = reasoning.get("resolved_action")
        parameters = reasoning.get("parameters", {})
        is_followup = parameters.get("resolved_from_context", False)
        grid_critical = reasoning.get("grid_critical", False)
        
        # 1. Base Greetings
        if resolved_action == "greeting":
            if assistant_mood == "excited":
                return "Wah hello operator! Sedia nak bantu operator hari ni!"
            elif assistant_mood in ["serious", "focused"]:
                return "Sistem bersedia. Sila masukkan arahan operator."
            elif assistant_mood == "tired":
                return "Hai operator. Penat sikit lah hari ni, tapi saya sedia membantu je."
            else:
                return "Salam operator. Ada apa-apa saya boleh bantu hari ni?"

        # 2. Unknown action fallback
        if not resolved_action or resolved_action == "generic_chat":
            if assistant_mood in ["serious", "focused"]:
                return "Saya tak faham maksud operator. Sila berikan arahan sistem yang lebih spesifik."
            return "Minta maaf operator, saya tak berapa faham maksud tu. Boleh jelaskan sikit lagi tak?"

        # 3. Action response mapping
        response = ""
        payload = action_result.get("payload", {})
        
        # Adjust tone suffix depending on mood
        suffix = ""
        if assistant_mood not in ["serious", "focused"]:
            suffix = " je" if assistant_mood == "calm" else " lah"

        if resolved_action == "open_youtube":
            if is_followup:
                response = f"Saya dah bukakan YouTube yang operator minta tadi tu{suffix}."
            else:
                response = f"Saya dah bukakan YouTube untuk operator{suffix}."

        elif resolved_action == "open_browser":
            if is_followup:
                response = f"Saya dah lancarkan pelayar web Google yang kita cakap tadi tu."
            else:
                response = f"Saya dah launching pelayar web Google untuk operator{suffix}."

        elif resolved_action == "get_time":
            time_val = payload.get("time", time.strftime("%H:%M:%S"))
            if assistant_mood in ["serious", "focused"]:
                response = f"Masa sistem semasa ialah pukul {time_val}."
            else:
                response = f"Sekarang dah pukul {time_val}{suffix}."

        elif resolved_action == "get_system_status":
            stability = payload.get("stability", "NORMAL")
            threat_score = payload.get("threat_score", 0.0)
            
            if stability == "CRITICAL" or grid_critical:
                response = f"Grid kita tengah kritikal! Bahaya pencerobohan siber dikesan dengan threat score {threat_score:.1f} peratus. Operator kena alert!"
            elif stability == "WARNING":
                response = f"Ada sedikit stress dikesan kat grid kita. Threat score ialah {threat_score:.1f} peratus. Boleh monitor dashboard."
            else:
                response = f"Status grid kita nampak ok sangat sekarang. Semua nominal dengan threat score {threat_score:.1f} peratus."

        elif resolved_action == "open_dashboard":
            if is_followup:
                response = "Dashboard HMI yang operator minta tadi tu dah sedia dibuka."
            else:
                response = f"Saya dah bukakan dashboard HMI untuk operator monitor status grid{suffix}."

        elif resolved_action == "assistant_identity_response":
            response = "Saya ialah Intelligent Grid Assistant sistem PYPY versi sembilan per dua. Sedia berbakti untuk operator!"

        else:
            response = f"Tindakan '{resolved_action}' telah diproses tetapi respons belum dikonfigurasi."

        # Add follow-up recommendations if reasoning planned them
        recommendation = reasoning.get("followup_recommendation")
        if recommendation and assistant_mood not in ["serious", "focused"]:
            response += f" Cadangan saya: {recommendation}."
        elif recommendation:
            response += f" Cadangan tindakan: {recommendation}."

        # Clean formatting characters to ensure speech compatibility
        # Replace bold and markdown styling markers
        response = response.replace("*", "")
        response = response.replace("_", "")
        response = re.sub(r"^#+\s+", "", response, flags=re.MULTILINE)
        
        return response.strip()
