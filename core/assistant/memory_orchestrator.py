from typing import Dict, Any, List

class MemoryOrchestrator:
    def __init__(self, limit: int = 10):
        self.limit = limit
        self.interactions: List[Dict[str, Any]] = []
        self.user_preferences: Dict[str, Any] = {
            "name": "Operator",
            "language": "ms",  # Malay
            "tone": "casual"
        }
        self.command_history: List[str] = []
        
    def add_interaction(self, role: str, text: str):
        """
        Appends interaction to short-term memory buffer. Summarizes if limits exceeded.
        """
        self.interactions.append({
            "role": role,
            "text": text
        })
        if len(self.interactions) > self.limit:
            self.summarize_memory()
            
    def record_command(self, command_name: str):
        """
        Logs executed actions to history queue.
        """
        self.command_history.append(command_name)
        if len(self.command_history) > 10:
            self.command_history.pop(0)
            
    def summarize_memory(self):
        """
        Consolidates old messages in interactions to a summary string to keep buffer short.
        """
        if len(self.interactions) < 4:
            return
        old_items = self.interactions[:4]
        summary_lines = []
        for item in old_items:
            summary_lines.append(f"{item['role']}: {item['text']}")
        
        summary_text = "Previously: " + " | ".join(summary_lines)
        self.interactions = [{"role": "system_summary", "text": summary_text}] + self.interactions[4:]
        
    def set_user_preference(self, key: str, value: Any):
        """
        Updates user preferences cache.
        """
        self.user_preferences[key] = value

    def clear_memory(self):
        """
        Clears all interaction and command history logs.
        """
        self.interactions = []
        self.command_history = []

    def get_memory_summary(self) -> Dict[str, Any]:
        """
        Returns serialized representation of memory.
        """
        return {
            "interactions": self.interactions,
            "user_preferences": self.user_preferences,
            "command_history": self.command_history
        }
