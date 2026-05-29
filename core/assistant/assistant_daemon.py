import os
import sys
import json
import time
import logging
import paho.mqtt.client as mqtt

# Configure paths
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(CURRENT_DIR))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.assistant.intent_engine import IntentEngine
from core.assistant.context_engine import ContextEngine
from core.assistant.memory_orchestrator import MemoryOrchestrator
from core.assistant.emotion_engine import EmotionEngine
from core.assistant.decision_engine import DecisionEngine
from core.assistant.action_router import ActionRouter
from core.assistant.response_engine import ResponseEngine
from core.assistant.assistant_state_manager import AssistantStateManager

# Semantic engines imports
from core.assistant.semantic_intent_engine import SemanticIntentEngine
from core.assistant.contextual_memory_engine import ContextualMemoryEngine
from core.assistant.assistant_reasoning_engine import AssistantReasoningEngine
from core.assistant.automation_hook_manager import AutomationHookManager
from core.assistant.semantic_response_engine import SemanticResponseEngine

# Voice & Proactive engines imports
from core.assistant.wake_word_manager import WakeWordManager
from core.assistant.voice_orchestration_engine import VoiceOrchestrationEngine
from core.assistant.voice_session_memory import VoiceSessionMemory
from core.assistant.proactive_assistant_engine import ProactiveAssistantEngine
from core.assistant.assistant_presence_engine import AssistantPresenceEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("assistant.daemon")

class AssistantDaemon:
    def __init__(self):
        self.broker = os.getenv("MQTT_BROKER", "localhost")
        self.port = int(os.getenv("MQTT_PORT", 1883))
        self.client = mqtt.Client(client_id="assistant_service")
        
        # Original Engines initialization
        self.intent_eng = IntentEngine()
        self.context_eng = ContextEngine()
        self.memory_orch = MemoryOrchestrator()
        self.emotion_eng = EmotionEngine()
        self.decision_eng = DecisionEngine()
        self.action_rt = ActionRouter()
        self.response_eng = ResponseEngine()
        self.state_mgr = AssistantStateManager()
        
        # Semantic engines initialization
        self.semantic_intent_eng = SemanticIntentEngine()
        self.contextual_mem = ContextualMemoryEngine()
        self.reasoning_eng = AssistantReasoningEngine()
        self.automation_hook_mgr = AutomationHookManager()
        self.semantic_response_eng = SemanticResponseEngine()
        
        # Voice & Proactive engines initialization
        self.wake_word_mgr = WakeWordManager()
        self.voice_orch_eng = VoiceOrchestrationEngine()
        self.voice_session_mem = VoiceSessionMemory()
        self.proactive_eng = ProactiveAssistantEngine()
        self.presence_eng = AssistantPresenceEngine()
        
        # Hardware simulation state registers for proactive triggers
        self.hardware_sim_state = {
            "latency_ms": 0.0,
            "drift_sec": 0.0,
            "latency_spike": False,
            "comms_online": True,
            "relay_unstable": False,
            "sync_recovered": False
        }
        
        # Telemetry cache registers
        self.latest_semantic_intent = {
            "category": "UNKNOWN",
            "action": None,
            "confidence": 0.0,
            "parameters": {},
            "is_fuzzy": False,
            "is_followup": False
        }
        self.latest_reasoning = {
            "should_execute": False,
            "should_respond": False,
            "resolved_action": None,
            "parameters": {},
            "webhook_trigger": None,
            "followup_recommendation": None,
            "reasoning_logs": ["Assistant daemon initialized."],
            "grid_critical": False
        }
        self.latest_semantic_response = {
            "text": "",
            "clean_tts_text": "",
            "timestamp": 0
        }
        
        # New Voice & Proactive caches
        self.latest_voice_state = self.voice_orch_eng.get_status_summary()
        self.latest_wake_word = self.wake_word_mgr.get_status_summary()
        self.latest_proactive = self.proactive_eng.get_automation_summary()
        self.latest_voice_memory = self.voice_session_mem.get_session_summary(None)
        self.latest_presence = self.presence_eng.get_status_summary("IDLE")
        
        # Grid cache
        self.grid_state = {
            "telemetry": {},
            "threat": {},
            "comms_online": True,
            "relay_unstable": False,
            "sync_recovered": False
        }
        
        self.start_time = time.time()
        
        # Client callbacks
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        
    def start(self):
        logger.info(f"Connecting to MQTT Broker {self.broker}:{self.port}...")
        self.client.connect(self.broker, self.port, keepalive=60)
        self.client.loop_start()
        
        # Publish initial states
        self.publish_telemetry()
        
        # Main tick loop
        try:
            while True:
                # Periodic runtime heartbeats
                t_ms = int(time.time() * 1000)
                uptime = int(time.time() - self.start_time)
                self.client.publish("assistant/runtime", json.dumps({
                    "timestamp": t_ms,
                    "status": "ONLINE",
                    "uptime_sec": uptime
                }))
                
                # Perform periodic scans and presence updates
                self.tick_periodic_presence_and_proactive()
                
                time.sleep(1.0)
        except KeyboardInterrupt:
            logger.info("Stopping daemon...")
            self.client.loop_stop()
            self.client.disconnect()

    def tick_periodic_presence_and_proactive(self):
        """
        Calculates presence breathing coordinates, updates attention state, 
        scans grid conditions passively, and executes proactive initiatives.
        """
        # 1. Update attention focus state
        active_sess = self.voice_orch_eng.is_session_active()
        active_att = self.wake_word_mgr.is_attention_locked()
        self.presence_eng.update_attention(active_sess, active_att)
        
        # 2. breathing coordinate calculations
        self.latest_presence = self.presence_eng.get_status_summary(self.state_mgr.state)
        
        # 3. Passive grid scanning
        threat_score = self.grid_state["threat"].get("threat_score", 0.0)
        threat_confidence = self.grid_state["threat"].get("confidence", 1.0)
        
        proactive_alert = self.proactive_eng.scan_grid_state(
            grid_state={
                "threat": {"threat_score": threat_score, "confidence": threat_confidence},
                "comms_online": self.grid_state.get("comms_online", True),
                "relay_unstable": self.grid_state.get("relay_unstable", False),
                "sync_recovered": self.grid_state.get("sync_recovered", False)
            },
            hardware_state=self.hardware_sim_state
        )
        
        # If alert triggers, initiate proactive voice responses
        if proactive_alert:
            logger.info(f"PROACTIVE ACTION DISPATCHED: {proactive_alert['message']}")
            old_state = self.state_mgr.state
            self.state_mgr.transition_to("RESPONDING")
            self.publish_telemetry()
            
            # Format and publish response topic (no markdown synthesis)
            t_ms = int(time.time() * 1000)
            self.client.publish("assistant/response", json.dumps({
                "timestamp": t_ms,
                "text": proactive_alert["message"],
                "is_voice": True,
                "action": {"status": "SUCCESS", "action": "proactive_initiative"},
                "reasoning": {
                    "should_execute": False,
                    "should_respond": True,
                    "resolved_action": "proactive_initiative",
                    "parameters": {"message": proactive_alert["message"]},
                    "webhook_trigger": None,
                    "followup_recommendation": None,
                    "reasoning_logs": [f"Proactive notification triggered: {proactive_alert['category']}"],
                    "grid_critical": (threat_score > 70.0)
                },
                "automation_hook": {}
            }))
            
            # Record proactive interaction in memories
            self.contextual_mem.add_interaction(role="assistant", text=proactive_alert["message"])
            if self.voice_orch_eng.active_session_id:
                self.voice_session_mem.add_interaction(
                    self.voice_orch_eng.active_session_id, 
                    "assistant", 
                    proactive_alert["message"]
                )
                
            self.state_mgr.transition_to(old_state)
            
        # 4. Update voice orchestration summaries
        self.latest_voice_state = self.voice_orch_eng.get_status_summary()
        self.latest_wake_word = self.wake_word_mgr.get_status_summary()
        self.latest_proactive = self.proactive_eng.get_automation_summary()
        
        active_sess_id = self.voice_orch_eng.active_session_id
        self.latest_voice_memory = self.voice_session_mem.get_session_summary(active_sess_id)
        
        self.publish_telemetry()
            
    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info("Connected to MQTT Broker successfully!")
            client.subscribe("assistant/chat_input")
            client.subscribe("assistant/voice_input")
            client.subscribe("grid/telemetry")
            client.subscribe("grid/threat")
            client.subscribe("assistant/reset")
            client.subscribe("assistant/wake_word_trigger")
            client.subscribe("assistant/proactive_trigger")
        else:
            logger.error(f"MQTT Connection failed with code {rc}")
            
    def _on_message(self, client, userdata, msg):
        try:
            topic = msg.topic
            payload = json.loads(msg.payload.decode("utf-8"))
            
            if topic == "grid/telemetry":
                self.grid_state["telemetry"] = payload
            elif topic == "grid/threat":
                self.grid_state["threat"] = payload
            elif topic == "assistant/reset":
                self.reset_assistant()
            elif topic == "assistant/wake_word_trigger":
                # Simulated wake trigger input
                text_input = payload.get("audio_text") or payload.get("text", "")
                self.process_wake_trigger(text_input)
            elif topic == "assistant/proactive_trigger":
                # Simulated passive grid alert parameters
                for k, v in payload.items():
                    if k in self.hardware_sim_state:
                        self.hardware_sim_state[k] = v
                    if k in self.grid_state:
                        self.grid_state[k] = v
                self.tick_periodic_presence_and_proactive()
            elif topic in ["assistant/chat_input", "assistant/voice_input"]:
                # Process user request
                is_voice = (topic == "assistant/voice_input")
                text_input = payload.get("audio_text") if is_voice else payload.get("text")
                self.process_request(text_input, is_voice)
        except Exception as e:
            logger.error(f"Error handling message on topic {msg.topic}: {e}")
            self.state_mgr.transition_to("ERROR")
            self.publish_telemetry()

    def process_wake_trigger(self, text: str):
        """
        Processes simulated wake word activation triggers.
        """
        if not text:
            return
        logger.info(f"Processing wake word simulation: '{text}'")
        wake_result = self.wake_word_mgr.detect_wake_word(text)
        self.latest_wake_word = self.wake_word_mgr.get_status_summary()
        
        if wake_result["detected"]:
            session_id = self.voice_orch_eng.start_session()
            self.voice_session_mem.initialize_session(session_id)
            self.voice_session_mem.add_interaction(session_id, "user", f"[Wake Word Detected: {text}]")
            self.latest_voice_state = self.voice_orch_eng.get_status_summary()
            self.latest_voice_memory = self.voice_session_mem.get_session_summary(session_id)
            logger.info(f"Wake word matched! Started session: {session_id}")
            
        self.publish_telemetry()
            
    def process_request(self, text: str, is_voice: bool = False):
        if not text:
            return
            
        logger.info(f"Processing input (Voice={is_voice}): '{text}'")
        
        # 1. Voice specific routing locks
        if is_voice:
            # Check wake word detection / false activation protection
            wake_result = self.wake_word_mgr.detect_wake_word(text)
            self.latest_wake_word = self.wake_word_mgr.get_status_summary()
            
            # Require active wake-word attention lockout
            if not self.wake_word_mgr.is_attention_locked():
                logger.info("Voice request ignored: attention lockout active (No wake word).")
                return
                
            # Manage session lifecycle
            if not self.voice_orch_eng.is_session_active():
                session_id = self.voice_orch_eng.start_session()
            else:
                session_id = self.voice_orch_eng.active_session_id
                self.voice_orch_eng.tick_session()
                self.voice_orch_eng.transition_to("LISTENING")
                
            # Extend attention limits
            self.wake_word_mgr.extend_attention()
            self.latest_voice_state = self.voice_orch_eng.get_status_summary()
            
            # Log voice session memory
            self.voice_session_mem.add_interaction(session_id, "user", text)
            self.latest_voice_memory = self.voice_session_mem.get_session_summary(session_id)
        
        # 2. State transition: LISTENING
        self.state_mgr.transition_to("LISTENING")
        self.publish_telemetry()
        time.sleep(0.05)
        
        # 3. State transition: THINKING
        self.state_mgr.transition_to("THINKING")
        if is_voice:
            self.voice_orch_eng.transition_to("THINKING")
        self.publish_telemetry()
        
        # 4. Intent detection (Fuzzy set Jaccard matching + fallback references)
        intent = self.intent_eng.detect_intent(text)
        semantic_intent = self.semantic_intent_eng.detect_intent(
            text, 
            previous_action=self.contextual_mem.active_subject
        )
        self.latest_semantic_intent = semantic_intent
        
        # 5. Context update
        self.context_eng.update_context(intent, self.state_mgr.state)
        
        # 6. Emotion mapping
        user_mood = self.emotion_eng.detect_user_emotion(text)
        threat_score = self.grid_state["threat"].get("threat_score", 0.0)
        grid_critical = (threat_score > 70.0)
        self.emotion_eng.modulate_assistant_emotion(user_mood, grid_critical)
        
        # 7. Memory store user input
        self.memory_orch.add_interaction("user", text)
        self.contextual_mem.add_interaction(
            role="user", 
            text=text, 
            intent_action=semantic_intent.get("action"), 
            entities=semantic_intent.get("parameters")
        )
        
        # 8. Reasoning & Decision Routing
        reasoning = self.reasoning_eng.reason(
            intent=semantic_intent,
            context=self.context_eng.get_context_summary(),
            emotion=self.emotion_eng.get_emotion_summary(),
            grid_state=self.grid_state
        )
        self.latest_reasoning = reasoning
        
        # 9. Execution path
        action_result = {}
        hook_status = {}
        
        if reasoning["should_execute"]:
            self.state_mgr.transition_to("EXECUTING")
            if is_voice:
                self.voice_orch_eng.transition_to("THINKING") # still executing
            self.publish_telemetry()
            
            action_name = reasoning["resolved_action"]
            action_result = self.action_rt.route_action(
                action_name=action_name,
                parameters=reasoning["parameters"],
                grid_state=self.grid_state
            )
            self.memory_orch.record_command(action_name)
            
            if is_voice:
                self.voice_session_mem.add_interaction(
                    self.voice_orch_eng.active_session_id,
                    "user_command",
                    f"[Executed: {action_name}]",
                    action=action_name
                )
            
            # Automation hook dispatch
            if reasoning["webhook_trigger"]:
                hook_status = self.automation_hook_mgr.trigger_webhook(
                    reasoning["webhook_trigger"], 
                    action_result
                )
            time.sleep(0.05)
            
        # 10. Response formulation
        self.state_mgr.transition_to("RESPONDING")
        if is_voice:
            self.voice_orch_eng.transition_to("SPEAKING")
        self.publish_telemetry()
        
        # Calculate presence delay simulation
        pacing_delay = self.presence_eng.calculate_pacing_delay(
            emotion_mood=self.emotion_eng.get_emotion_summary().get("assistant_mood", "calm"),
            grid_critical=grid_critical
        )
        if pacing_delay > 0.0:
            time.sleep(pacing_delay)
        
        # Generate semantic, context-aware Malay response
        response_text = self.semantic_response_eng.generate_response(
            reasoning=reasoning,
            action_result=action_result,
            emotion=self.emotion_eng.get_emotion_summary()
        )
        
        self.latest_semantic_response = {
            "text": response_text,
            "clean_tts_text": self.semantic_response_eng.clean_tts(response_text),
            "timestamp": int(time.time() * 1000)
        }
        
        # Store response in memory
        self.memory_orch.add_interaction("assistant", response_text)
        self.contextual_mem.add_interaction(role="assistant", text=response_text)
        if is_voice:
            self.voice_session_mem.add_interaction(
                self.voice_orch_eng.active_session_id, 
                "assistant", 
                response_text
            )
            self.latest_voice_memory = self.voice_session_mem.get_session_summary(self.voice_orch_eng.active_session_id)
        
        # Publish response text
        self.client.publish("assistant/response", json.dumps({
            "timestamp": int(time.time() * 1000),
            "text": response_text,
            "is_voice": is_voice,
            "action": action_result,
            "reasoning": reasoning,
            "automation_hook": hook_status
        }))
        
        # 11. Finish -> IDLE state
        self.state_mgr.transition_to("IDLE")
        if is_voice:
            self.voice_orch_eng.transition_to("LISTENING") # Returns to listening until attention expires
        self.publish_telemetry()
        
    def reset_assistant(self):
        """
        Resets context and clears memories.
        """
        logger.info("Resetting assistant registers...")
        self.context_eng.reset_context()
        self.memory_orch.clear_memory()
        self.contextual_mem.clear_memory()
        self.wake_word_mgr.reset_attention()
        self.voice_orch_eng.end_session()
        self.voice_session_mem.clear_all()
        self.proactive_eng.reset_cooldowns()
        
        self.hardware_sim_state = {
            "latency_ms": 0.0,
            "drift_sec": 0.0,
            "latency_spike": False,
            "comms_online": True,
            "relay_unstable": False,
            "sync_recovered": False
        }
        
        self.latest_semantic_intent = {
            "category": "UNKNOWN",
            "action": None,
            "confidence": 0.0,
            "parameters": {},
            "is_fuzzy": False,
            "is_followup": False
        }
        self.latest_reasoning = {
            "should_execute": False,
            "should_respond": False,
            "resolved_action": None,
            "parameters": {},
            "webhook_trigger": None,
            "followup_recommendation": None,
            "reasoning_logs": ["Assistant registers reset."],
            "grid_critical": False
        }
        self.latest_semantic_response = {
            "text": "",
            "clean_tts_text": "",
            "timestamp": int(time.time() * 1000)
        }
        
        self.latest_voice_state = self.voice_orch_eng.get_status_summary()
        self.latest_wake_word = self.wake_word_mgr.get_status_summary()
        self.latest_proactive = self.proactive_eng.get_automation_summary()
        self.latest_voice_memory = self.voice_session_mem.get_session_summary(None)
        self.latest_presence = self.presence_eng.get_status_summary("IDLE")
        
        self.state_mgr.transition_to("IDLE")
        self.publish_telemetry()
        
    def publish_telemetry(self):
        """
        Publishes separate topics for state, intent, emotion, actions, context, memory, voice.
        """
        t_ms = int(time.time() * 1000)
        
        # 1. assistant/state
        self.client.publish("assistant/state", json.dumps({
            "timestamp": t_ms,
            "state": self.state_mgr.state
        }))
        # 2. assistant/intent
        self.client.publish("assistant/intent", json.dumps({
            "timestamp": t_ms,
            "intent": self.intent_eng.command_keywords
        }))
        # 3. assistant/emotion
        self.client.publish("assistant/emotion", json.dumps({
            "timestamp": t_ms,
            "emotion": self.emotion_eng.get_emotion_summary()
        }))
        # 4. assistant/actions
        self.client.publish("assistant/actions", json.dumps({
            "timestamp": t_ms,
            "command_history": self.memory_orch.command_history
        }))
        # 5. assistant/context
        self.client.publish("assistant/context", json.dumps({
            "timestamp": t_ms,
            "context": self.context_eng.get_context_summary()
        }))
        # 6. assistant/memory
        self.client.publish("assistant/memory", json.dumps({
            "timestamp": t_ms,
            "memory": self.memory_orch.get_memory_summary()
        }))
        # 7. assistant/runtime
        uptime = int(time.time() - self.start_time)
        self.client.publish("assistant/runtime", json.dumps({
            "timestamp": t_ms,
            "status": "ONLINE",
            "uptime_sec": uptime
        }))
        # 8. assistant/semantic_intent
        self.client.publish("assistant/semantic_intent", json.dumps({
            "timestamp": t_ms,
            "semantic_intent": self.latest_semantic_intent
        }))
        # 9. assistant/contextual_memory
        self.client.publish("assistant/contextual_memory", json.dumps({
            "timestamp": t_ms,
            "contextual_memory": self.contextual_mem.get_memory_summary()
        }))
        # 10. assistant/reasoning
        self.client.publish("assistant/reasoning", json.dumps({
            "timestamp": t_ms,
            "reasoning": self.latest_reasoning
        }))
        # 11. assistant/automation_hooks
        self.client.publish("assistant/automation_hooks", json.dumps({
            "timestamp": t_ms,
            "automation_hooks": self.automation_hook_mgr.get_automation_summary()
        }))
        # 12. assistant/semantic_response
        self.client.publish("assistant/semantic_response", json.dumps({
            "timestamp": t_ms,
            "semantic_response": self.latest_semantic_response
        }))
        # 13. assistant/voice_state [NEW]
        self.client.publish("assistant/voice_state", json.dumps({
            "timestamp": t_ms,
            "voice_state": self.latest_voice_state
        }))
        # 14. assistant/wake_word [NEW]
        self.client.publish("assistant/wake_word", json.dumps({
            "timestamp": t_ms,
            "wake_word": self.latest_wake_word
        }))
        # 15. assistant/proactive [NEW]
        self.client.publish("assistant/proactive", json.dumps({
            "timestamp": t_ms,
            "proactive": self.latest_proactive
        }))
        # 16. assistant/voice_memory [NEW]
        self.client.publish("assistant/voice_memory", json.dumps({
            "timestamp": t_ms,
            "voice_memory": self.latest_voice_memory
        }))
        # 17. assistant/presence [NEW]
        self.client.publish("assistant/presence", json.dumps({
            "timestamp": t_ms,
            "presence": self.latest_presence
        }))

if __name__ == "__main__":
    daemon = AssistantDaemon()
    daemon.start()
