import time
import uuid
from typing import Dict, Any, List, Optional

class ContextualMemoryEngine:
    def __init__(self, thread_timeout: float = 300.0, limit: int = 10):
        self.thread_timeout = thread_timeout
        self.limit = limit
        
        # State registers
        self.active_thread_id: Optional[str] = None
        self.last_interaction_time: float = 0.0
        self.active_subject: Optional[str] = None
        
        # Historical registry of conversation threads
        # Map: thread_id -> { "start_time": float, "last_time": float, "subject": str, "messages": List[Dict] }
        self.threads: Dict[str, Dict[str, Any]] = {}
        
        # Cache for recent entity references (e.g. specific grid bus, line, or url)
        self.recent_references: Dict[str, Any] = {}
        
    def get_or_create_thread(self) -> str:
        """
        Returns the active thread ID, or spawns a new thread if the timeout expired.
        """
        now = time.time()
        if not self.active_thread_id or (now - self.last_interaction_time > self.thread_timeout):
            self.active_thread_id = str(uuid.uuid4())
            self.threads[self.active_thread_id] = {
                "start_time": now,
                "last_time": now,
                "subject": "general",
                "messages": []
            }
        
        self.last_interaction_time = now
        return self.active_thread_id

    def add_interaction(self, role: str, text: str, intent_action: str = None, entities: Dict[str, Any] = None):
        """
        Groups interaction into the active thread, updates the subject, and caches entity references.
        """
        thread_id = self.get_or_create_thread()
        thread = self.threads[thread_id]
        thread["last_time"] = time.time()
        
        # Update thread subject if a specific intent action is detected
        if intent_action and intent_action != "generic_chat" and intent_action != "greeting":
            self.active_subject = intent_action
            thread["subject"] = intent_action
            
        # Cache specific entities if present in the parameters (e.g., bus, zone, url)
        if entities:
            for k, v in entities.items():
                self.recent_references[k] = v
                
        # Append message
        msg_payload = {
            "role": role,
            "text": text,
            "timestamp": int(time.time() * 1000)
        }
        thread["messages"].append(msg_payload)
        
        # Enforce memory constraints on the active thread
        if len(thread["messages"]) > self.limit:
            self._consolidate_thread(thread)

    def _consolidate_thread(self, thread: Dict[str, Any]):
        """
        Consolidates the oldest messages in a thread into a single summary block.
        """
        messages = thread["messages"]
        if len(messages) < 4:
            return
            
        old_items = messages[:4]
        summary_lines = []
        for msg in old_items:
            summary_lines.append(f"{msg['role']}: {msg['text']}")
            
        summary_text = "Thread Summary: " + " | ".join(summary_lines)
        consolidated_msg = {
            "role": "system_summary",
            "text": summary_text,
            "timestamp": old_items[-1]["timestamp"]
        }
        
        thread["messages"] = [consolidated_msg] + messages[4:]

    def recall_reference(self, entity_key: str) -> Optional[Any]:
        """
        Recalls a cached entity reference by key.
        """
        return self.recent_references.get(entity_key)

    def clear_memory(self):
        """
        Wipes all threads, references, and resets state registers.
        """
        self.active_thread_id = None
        self.last_interaction_time = 0.0
        self.active_subject = None
        self.threads.clear()
        self.recent_references.clear()

    def get_memory_summary(self) -> Dict[str, Any]:
        """
        Returns serialized representation of contextual memory.
        """
        active_thread = self.threads.get(self.active_thread_id) if self.active_thread_id else None
        
        return {
            "active_thread_id": self.active_thread_id,
            "active_subject": self.active_subject,
            "recent_references": self.recent_references,
            "active_messages": active_thread["messages"] if active_thread else [],
            "thread_count": len(self.threads)
        }
