from typing import Dict, Any

class ResponseEngine:
    def __init__(self):
        pass
        
    def generate_response(self, 
                          intent_action: str, 
                          action_result: Dict[str, Any], 
                          emotion: Dict[str, Any]) -> str:
        """
        Generates clean conversational responses in casual Malaysian Malay.
        Modulates responses based on emotion context. Ensures no markdown symbols are generated.
        """
        mood = emotion.get("assistant_mood", "calm")
        
        # 1. Identity response
        if intent_action == "assistant_identity_response":
            if mood == "happy":
                return "Hai! Saya pembantu AI pintar awak untuk grid ni. Seronok dapat bantu!"
            elif mood == "excited":
                return "Halo! Saya pembantu AI pintar untuk grid ni. Jom kita periksa status sistem!"
            elif mood == "serious":
                return "Saya pembantu AI keselamatan grid. Sistem sedang dipantau secara ketat."
            elif mood == "tired":
                return "Saya pembantu AI awak... ada apa-apa saya boleh tolong ke? Penat sikit hari ni."
            elif mood == "sad":
                return "Saya pembantu AI grid... harap hari ni semuanya berjalan lancar, sedih pula rasanya."
            else: # calm, focused
                return "Saya pembantu AI pintar untuk mengurus dan memantau status grid kuasa elektrik."
                
        # 2. Get system status response
        elif intent_action == "get_system_status":
            payload = action_result.get("payload", {})
            stability = payload.get("stability", "NORMAL")
            threat_score = payload.get("threat_score", 0.0)
            
            if stability == "CRITICAL":
                if mood == "serious":
                    return f"Bahaya! Keadaan grid kritikal sekarang. Tahap ancaman berada pada {threat_score:.1f} peratus. Sila ambil langkah berjaga-jaga."
                else:
                    return f"Sistem dalam bahaya! Tahap ancaman sangat tinggi, {threat_score:.1f} peratus. Harap bersedia untuk bertindak."
            elif stability == "WARNING":
                return f"Grid ada sedikit gangguan. Tahap ancaman semasa berada pada {threat_score:.1f} peratus."
            else:
                if mood == "happy":
                    return "Keadaan grid nampak sangat baik dan semua sistem berjalan lancar!"
                else:
                    return "Status grid nominal dan stabil sekarang. Tiada sebarang masalah dikesan."
                    
        # 3. Open dashboard
        elif intent_action == "open_dashboard":
            if mood == "excited":
                return "Boleh, saya bukakan dashboard SCADA sekarang juga!"
            elif mood == "tired":
                return "Okey... saya bukakan dashboard SCADA untuk awak."
            else:
                return "Sedia, saya bukakan dashboard SCADA untuk paparan utama."
                
        # 4. Open YouTube
        elif intent_action == "open_youtube":
            if mood == "serious":
                return "Maaf, kita tengah ada kecemasan sistem. Saya cadangkan kita fokus pada grid dulu."
            elif mood == "tired":
                return "Boleh... jom rehat kejap. Saya bukakan YouTube."
            else:
                return "Baik, saya bukakan laman YouTube di tab baharu."
                
        # 5. Open browser
        elif intent_action == "open_browser":
            return "Okey, saya bukakan pelayar web untuk awak sekarang."
            
        # 6. Get time
        elif intent_action == "get_time":
            payload = action_result.get("payload", {})
            t_str = payload.get("time", "waktu semasa")
            return f"Sekarang dah pukul {t_str}."
            
        # 7. Greeting responses
        elif intent_action == "greeting":
            if mood == "happy":
                return "Hai! Apa khabar? Ada apa-apa saya boleh tolong hari ni?"
            elif mood == "excited":
                return "Halo! Jom kita mulakan hari ni dengan bertenaga!"
            elif mood == "tired":
                return "Hai... khabar baik. Letih sikit tapi saya sedia tolong."
            elif mood == "sad":
                return "Hai... ada apa saya boleh bantu ke?"
            elif mood == "serious":
                return "Salam operator. Sedia menerima arahan kawalan sistem."
            else:
                return "Hai, salam. Ada apa-apa tugasan saya boleh bantu untuk grid hari ni?"
                
        # Fallback chat
        if mood == "serious":
            return "Saya faham. Sila beritahu saya sekiranya ada arahan keselamatan grid lain."
        elif mood == "happy":
            return "Faham! Jom kita teruskan kerja dengan baik."
        else:
            return "Okey, saya faham. Ada apa-apa lagi saya boleh tolong?"
