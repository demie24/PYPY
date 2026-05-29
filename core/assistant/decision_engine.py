from typing import Dict, Any

class DecisionEngine:
    def __init__(self):
        pass
        
    def determine_routing(self, 
                          intent: Dict[str, Any], 
                          context: Dict[str, Any], 
                          emotion: Dict[str, Any]) -> Dict[str, Any]:
        """
        Synthesizes state inputs to select appropriate execution triggers and routing pathways.
        Determines whether to trigger immediate action execution, pure conversational response, or both.
        """
        category = intent.get("category", "CONVERSATION")
        action = intent.get("action")
        confidence = intent.get("confidence", 0.0)
        
        should_execute = False
        should_respond = True
        
        # Commands and utilities with high confidence are routed to execution
        if category in ["COMMAND", "UTILITY"] and confidence >= 0.70 and action:
            should_execute = True
            
        # Prioritize system safety locks: If serious mood is active, block recreational commands like open_youtube
        assistant_mood = emotion.get("assistant_mood", "calm")
        if assistant_mood in ["serious", "focused"] and action == "open_youtube":
            should_execute = False
            # Force redirection to get system status
            action = "get_system_status"
            intent["action"] = "get_system_status"
            intent["category"] = "COMMAND"
            category = "COMMAND"
            should_execute = True
            
        return {
            "should_execute": should_execute,
            "should_respond": should_respond,
            "route": category,
            "resolved_action": action,
            "parameters": intent.get("parameters", {})
        }
