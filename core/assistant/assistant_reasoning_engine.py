from typing import Dict, Any, Optional

class AssistantReasoningEngine:
    def __init__(self):
        pass

    def reason(self, 
               intent: Dict[str, Any], 
               context: Dict[str, Any], 
               emotion: Dict[str, Any], 
               grid_state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Executes a 5-step cognitive reasoning pipeline to fuse signals and coordinate assistant behaviors.
        """
        threat_data = grid_state.get("threat", {}) if grid_state else {}
        threat_score = float(threat_data.get("threat_score", 0.0))
        
        # Step 1: Threat evaluation
        grid_critical = (threat_score > 70.0)
        
        # Step 2: Intent analysis
        action = intent.get("action")
        category = intent.get("category", "CONVERSATION")
        confidence = intent.get("confidence", 0.0)
        is_fuzzy = intent.get("is_fuzzy", False)
        is_followup = intent.get("is_followup", False)
        
        should_execute = False
        should_respond = True
        resolved_action = action
        reasoning_logs = []
        
        reasoning_logs.append(f"Grid threat score evaluated: {threat_score:.1f}% (Critical={grid_critical}).")
        reasoning_logs.append(f"Parsed intent category: {category} with action '{action}' (Confidence={confidence}).")
        
        if is_followup:
            reasoning_logs.append("Continuity reference detected. Action resolved from conversation memory.")
            
        # Step 3: Contextual Action Selection & Overrides
        if category in ["COMMAND", "UTILITY"] and confidence >= 0.40 and action:
            should_execute = True
            reasoning_logs.append(f"Action '{action}' meets confidence threshold and is marked for routing.")
            
        # Apply safety override locks
        if grid_critical and resolved_action == "open_youtube":
            should_execute = True
            resolved_action = "get_system_status"
            reasoning_logs.append("SAFETY OVERRIDE: YouTube request blocked due to critical grid threat score. Redirected to system status.")
            
        # Step 4: Automation Webhook Planning
        webhook_trigger = None
        if should_execute:
            if resolved_action in ["get_system_status", "open_dashboard"] and grid_critical:
                webhook_trigger = "n8n_security_alert"
                reasoning_logs.append("Automation planning: Grid is in high stress. Preparing n8n security alert hook.")
            elif resolved_action in ["open_youtube", "open_browser"] and not grid_critical:
                # Normal utility triggers
                webhook_trigger = None
            elif resolved_action == "get_system_status":
                webhook_trigger = "n8n_restoration"
                reasoning_logs.append("Automation planning: Mapping status query to n8n restoration flow.")

        # Step 5: Follow-Up Response Planning
        followup_recommendation = None
        if resolved_action == "get_system_status" and grid_critical:
            followup_recommendation = "Engage FLISR auto mode or lock out compromised ports."
            reasoning_logs.append("Follow-up planned: Suggesting critical mitigations to operator.")
        elif resolved_action == "open_dashboard":
            followup_recommendation = "Review active hardware twin alerts."
            reasoning_logs.append("Follow-up planned: Recommending alert scan.")

        return {
            "should_execute": should_execute,
            "should_respond": should_respond,
            "resolved_action": resolved_action,
            "parameters": intent.get("parameters", {}),
            "webhook_trigger": webhook_trigger,
            "followup_recommendation": followup_recommendation,
            "reasoning_logs": reasoning_logs,
            "grid_critical": grid_critical
        }
