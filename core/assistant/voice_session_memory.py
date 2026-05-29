import time
from typing import Dict, Any, List, Optional

class VoiceSessionMemory:
    def __init__(self):
        # Memory map: session_id -> { "messages": List[Dict], "commands": List[str], "created_at": float }
        self.session_memories: Dict[str, Dict[str, Any]] = {}
        self.latest_command: Optional[str] = None
        self.latest_voice_text: Optional[str] = None

    def initialize_session(self, session_id: str):
        """
        Registers a new session index.
        """
        if session_id not in self.session_memories:
            self.session_memories[session_id] = {
                "messages": [],
                "commands": [],
                "created_at": time.time()
            }

    def add_interaction(self, session_id: str, role: str, text: str, action: Optional[str] = None):
        """
        Caches voice interaction and details under the active session.
        """
        self.initialize_session(session_id)
        
        session = self.session_memories[session_id]
        interaction_log = {
            "role": role,
            "text": text,
            "timestamp": int(time.time() * 1000)
        }
        session["messages"].append(interaction_log)
        
        if role == "user":
            self.latest_voice_text = text
            
        if action:
            session["commands"].append(action)
            self.latest_command = action

    def recall_last_command(self, session_id: str) -> Optional[str]:
        """
        Recalls the last executed action/command in the active voice session.
        """
        if session_id in self.session_memories:
            commands = self.session_memories[session_id]["commands"]
            if commands:
                return commands[-1]
        return self.latest_command

    def clear_session(self, session_id: str):
        """
        Evicts session data from memory.
        """
        if session_id in self.session_memories:
            del self.session_memories[session_id]

    def clear_all(self):
        """
        Wipes entire memory.
        """
        self.session_memories.clear()
        self.latest_command = None
        self.latest_voice_text = None

    def get_session_summary(self, session_id: Optional[str]) -> Dict[str, Any]:
        """
        Returns serialized representation of voice session memory.
        """
        messages = []
        commands = []
        created_at = 0.0
        
        if session_id and session_id in self.session_memories:
            session = self.session_memories[session_id]
            messages = session["messages"]
            commands = session["commands"]
            created_at = session["created_at"]
            
        return {
            "active_session_id": session_id,
            "session_messages": messages,
            "session_commands": commands,
            "created_at": created_at,
            "latest_command": self.latest_command,
            "latest_voice_text": self.latest_voice_text,
            "total_cached_sessions": len(self.session_memories)
        }
