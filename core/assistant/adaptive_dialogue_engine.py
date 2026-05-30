import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("assistant.dialogue_engine")

class AdaptiveDialogueEngine:
    def __init__(self):
        self.state = "IDLE"  # IDLE, AWAITING_CLARIFICATION, RESOLVED
        self.pending_intent: Optional[Dict[str, Any]] = None
        self.pending_phrase = ""
        self.clarification_question = ""
        self.parameter_needed = ""

    def check_ambiguity(self, phrase: str, semantic_intent: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluates user intent and checks if critical parameters are missing.
        Fills clarification fields if ambiguity is found.
        """
        normalized = phrase.lower().strip()
        
        # Scenario A: Check latency but missing Bus/Node target
        if "latency" in normalized and not any(bus in normalized for bus in ["bus_1", "bus_3", "bus_5", "bus_7", "bus_9", "bus 1", "bus 3", "bus 5", "bus 7", "bus 9", "edge"]):
            self.state = "AWAITING_CLARIFICATION"
            self.pending_intent = semantic_intent
            self.pending_phrase = phrase
            self.parameter_needed = "target_bus"
            self.clarification_question = "Anda mahu saya semak latency untuk Bus 5 atau Bus 7?"
            logger.info("Ambiguity detected: Missing latency target bus.")
            return self.get_status_summary()

        # Scenario B: Monitor relay but missing specific line/relay breaker target
        if "monitor" in normalized and "relay" in normalized and not any(link in normalized for link in ["l1_4", "l4_5", "l7_8", "l8_9", "line"]):
            self.state = "AWAITING_CLARIFICATION"
            self.pending_intent = semantic_intent
            self.pending_phrase = phrase
            self.parameter_needed = "relay_line"
            self.clarification_question = "Relay mana yang anda mahu saya monitor? L1_4 atau L4_5?"
            logger.info("Ambiguity detected: Missing relay target breaker.")
            return self.get_status_summary()

        # Scenario C: Run workflow but missing workflow name
        if ("workflow" in normalized or "proses" in normalized) and ("trigger" in normalized or "jalankan" in normalized) and not any(wf in normalized for wf in ["status", "shed", "recovery", "load"]):
            self.state = "AWAITING_CLARIFICATION"
            self.pending_intent = semantic_intent
            self.pending_phrase = phrase
            self.parameter_needed = "workflow_name"
            self.clarification_question = "Boleh terangkan workflow mana yang mahu dilancarkan?"
            logger.info("Ambiguity detected: Missing workflow identifier.")
            return self.get_status_summary()

        # Scenario D: Schedule reminder but missing time duration
        if "ingatkan" in normalized and not any(time_unit in normalized for time_unit in ["saat", "minit", "malam", "petang", "jam", "sec", "min"]):
            self.state = "AWAITING_CLARIFICATION"
            self.pending_intent = semantic_intent
            self.pending_phrase = phrase
            self.parameter_needed = "delay_sec"
            self.clarification_question = "Berapa saat lagi peringatan ini perlu diaktifkan?"
            logger.info("Ambiguity detected: Missing reminder timing parameters.")
            return self.get_status_summary()

        # No ambiguity found
        self.state = "IDLE"
        self.pending_intent = None
        self.pending_phrase = ""
        self.clarification_question = ""
        self.parameter_needed = ""
        return self.get_status_summary()

    def resolve_clarification(self, answer: str) -> Dict[str, Any]:
        """
        Merges clarification inputs into the pending query state.
        Returns the resolved intent payload.
        """
        if self.state != "AWAITING_CLARIFICATION" or not self.pending_intent:
            return {"status": "FAILED", "error": "not_awaiting_clarification"}

        normalized_ans = answer.lower().strip()
        merged_intent = self.pending_intent.copy()
        merged_intent["clarified_value"] = answer

        # Perform parameter extraction & resolution mappings
        if self.parameter_needed == "target_bus":
            if "5" in normalized_ans or "bus 5" in normalized_ans or "bus_5" in normalized_ans:
                merged_intent["parameters"] = {"target": "Bus_5"}
            elif "7" in normalized_ans or "bus 7" in normalized_ans or "bus_7" in normalized_ans:
                merged_intent["parameters"] = {"target": "Bus_7"}
            else:
                merged_intent["parameters"] = {"target": answer} # raw mapping fallback
                
        elif self.parameter_needed == "relay_line":
            if "l1_4" in normalized_ans or "1" in normalized_ans:
                merged_intent["parameters"] = {"target": "L1_4"}
            elif "l4_5" in normalized_ans or "4" in normalized_ans:
                merged_intent["parameters"] = {"target": "L4_5"}
            else:
                merged_intent["parameters"] = {"target": answer}
                
        elif self.parameter_needed == "workflow_name":
            if "status" in normalized_ans or "check" in normalized_ans:
                merged_intent["parameters"] = {"workflow_name": "system_status_check"}
            elif "shed" in normalized_ans or "load" in normalized_ans:
                merged_intent["parameters"] = {"workflow_name": "emergency_load_shed"}
            else:
                merged_intent["parameters"] = {"workflow_name": answer}
                
        elif self.parameter_needed == "delay_sec":
            # Extract number
            nums = [int(s) for s in normalized_ans.split() if s.isdigit()]
            if nums:
                merged_intent["parameters"] = {"delay_sec": float(nums[0])}
            else:
                merged_intent["parameters"] = {"delay_sec": 5.0} # default test fallback

        self.state = "RESOLVED"
        logger.info(f"Dialogue ambiguity resolved using inputs: '{answer}'. Merged parameters: {merged_intent['parameters']}")
        
        # Reset properties
        resolved_details = {
            "status": "SUCCESS",
            "resolved_intent": merged_intent,
            "original_phrase": self.pending_phrase,
            "clarified_with": answer
        }
        
        self.pending_intent = None
        self.pending_phrase = ""
        self.clarification_question = ""
        self.parameter_needed = ""
        
        return resolved_details

    def clear_dialogue(self) -> None:
        self.state = "IDLE"
        self.pending_intent = None
        self.pending_phrase = ""
        self.clarification_question = ""
        self.parameter_needed = ""

    def get_status_summary(self) -> Dict[str, Any]:
        return {
            "dialogue_state": self.state,
            "parameter_needed": self.parameter_needed,
            "clarification_question": self.clarification_question,
            "has_pending_phrase": bool(self.pending_phrase)
        }
