from typing import Dict, Any
import os
import sys
import json
import time
import logging
import paho.mqtt.client as mqtt
from typing import Dict, Any, List

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

# Autonomous Workflow & Assistant Operations engines imports
from core.assistant.reminder_manager import ReminderManager
from core.assistant.condition_monitor_engine import ConditionMonitorEngine
from core.assistant.n8n_orchestration_bridge import N8nOrchestrationBridge
from core.assistant.adaptive_routine_engine import AdaptiveRoutineEngine
from core.assistant.autonomous_workflow_engine import AutonomousWorkflowEngine

# Phase 9.5 engines imports
from core.assistant.conversational_planning_engine import ConversationalPlanningEngine
from core.assistant.task_chain_manager import TaskChainManager
from core.assistant.live_conversation_stream import LiveConversationStream
from core.assistant.adaptive_dialogue_engine import AdaptiveDialogueEngine
from core.assistant.orchestration_planner_bridge import OrchestrationPlannerBridge

# Phase 9.6 engines imports
from core.assistant.predictive_coordination_engine import PredictiveCoordinationEngine
from core.assistant.persistent_routine_memory import PersistentRoutineMemory
from core.assistant.pattern_awareness_engine import PatternAwarenessEngine
from core.assistant.adaptive_workflow_optimizer import AdaptiveWorkflowOptimizer
from core.assistant.cross_system_coordination_manager import CrossSystemCoordinationManager

# Phase 9.7 engines imports
from core.assistant.edge_awareness_engine import EdgeAwarenessEngine
from core.assistant.relay_health_monitor import RelayHealthMonitor
from core.assistant.telemetry_correlation_engine import TelemetryCorrelationEngine
from core.assistant.synchronization_awareness_manager import SynchronizationAwarenessManager
from core.assistant.cyber_physical_reasoning_engine import CyberPhysicalReasoningEngine

# Phase 9.8 agent imports
from core.assistant.telemetry_agent import TelemetryAgent
from core.assistant.relay_agent import RelayAgent
from core.assistant.workflow_agent import WorkflowAgent
from core.assistant.security_agent import SecurityAgent
from core.assistant.agent_coordination_engine import AgentCoordinationEngine

# Phase 9.9 swarm imports
from core.assistant.federated_memory_manager import FederatedMemoryManager
from core.assistant.distributed_consensus_engine import DistributedConsensusEngine
from core.assistant.edge_mesh_orchestrator import EdgeMeshOrchestrator
from core.assistant.swarm_anomaly_fusion_engine import SwarmAnomalyFusionEngine
from core.assistant.swarm_coordination_engine import SwarmCoordinationEngine


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
        
        # Autonomous Workflow & Assistant Operations engines initialization
        self.reminder_mgr = ReminderManager()
        self.condition_monitor = ConditionMonitorEngine()
        self.n8n_bridge = N8nOrchestrationBridge()
        self.adaptive_routine = AdaptiveRoutineEngine()
        self.workflow_engine = AutonomousWorkflowEngine()
        
        # Phase 9.5 engines initialization
        self.planning_engine = ConversationalPlanningEngine()
        self.task_chain_mgr = TaskChainManager()
        self.live_stream = LiveConversationStream()
        self.dialogue_engine = AdaptiveDialogueEngine()
        self.planner_bridge = OrchestrationPlannerBridge()
        
        # Phase 9.6 engines initialization
        self.predictive_coordination = PredictiveCoordinationEngine()
        self.persistent_memory = PersistentRoutineMemory()
        self.pattern_awareness = PatternAwarenessEngine()
        self.workflow_optimizer = AdaptiveWorkflowOptimizer()
        self.cross_coordination = CrossSystemCoordinationManager()

        # Phase 9.7 engines initialization
        self.edge_awareness = EdgeAwarenessEngine()
        self.relay_health = RelayHealthMonitor()
        self.telemetry_correlation = TelemetryCorrelationEngine()
        self.sync_awareness = SynchronizationAwarenessManager()
        self.cyber_physical_reasoning = CyberPhysicalReasoningEngine()

        # Phase 9.8 engines initialization
        self.telemetry_agent = TelemetryAgent()
        self.relay_agent = RelayAgent()
        self.workflow_agent = WorkflowAgent()
        self.security_agent = SecurityAgent()
        self.agent_coordination = AgentCoordinationEngine(
            self.telemetry_agent,
            self.relay_agent,
            self.workflow_agent,
            self.security_agent
        )
        self.latest_agent_coordination = self.agent_coordination.get_status_summary()

        # Phase 9.9 swarm initialization
        self.federated_memory = FederatedMemoryManager()
        self.distributed_consensus = DistributedConsensusEngine()
        self.edge_mesh = EdgeMeshOrchestrator()
        self.anomaly_fusion = SwarmAnomalyFusionEngine()
        self.swarm_coordination = SwarmCoordinationEngine(
            self.federated_memory,
            self.distributed_consensus,
            self.edge_mesh,
            self.anomaly_fusion
        )
        self.latest_swarm_coordination = self.swarm_coordination.get_status_summary()

        # Phase 9.7 simulation overrides
        self.edge_sim_overrides = {
            "esp32_zone1": {},
            "esp32_zone2": {},
            "esp32_zone3": {},
            "plc_primary": {},
            "plc_backup": {},
            "esp32_backup": {}
        }
        self.breaker_sim_overrides = {}
        
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
        
        self.latest_workflows = self.workflow_engine.get_status_summary()
        self.latest_reminders = self.reminder_mgr.get_status_summary()
        self.latest_conditions = self.condition_monitor.get_status_summary()
        self.latest_n8n_bridge = self.n8n_bridge.get_status_summary()
        self.latest_routines = self.adaptive_routine.get_status_summary()
        
        # New Phase 9.5 caches
        self.latest_planning = self.planning_engine.get_status_summary()
        self.latest_task_chains = self.task_chain_mgr.get_status_summary()
        self.latest_live_stream = self.live_stream.get_status_summary()
        self.latest_dialogue = self.dialogue_engine.get_status_summary()
        self.latest_planner_bridge = self.planner_bridge.get_status_summary()
        
        # New Phase 9.6 caches
        self.latest_predictive_coordination = self.predictive_coordination.get_status_summary()
        self.latest_persistent_memory = self.persistent_memory.get_status_summary()
        self.latest_pattern_awareness = self.pattern_awareness.get_status_summary()
        self.latest_workflow_optimizer = self.workflow_optimizer.get_status_summary()
        self.latest_cross_system_coordination = self.cross_coordination.get_status_summary()

        # New Phase 9.7 caches
        self.latest_edge_awareness = self.edge_awareness.get_status_summary()
        self.latest_relay_health = self.relay_health.get_status_summary()
        self.latest_telemetry_correlation = self.telemetry_correlation.get_status_summary()
        self.latest_synchronization_awareness = self.sync_awareness.get_status_summary()
        self.latest_cyber_physical_reasoning = self.cyber_physical_reasoning.evaluate_state(
            self.latest_edge_awareness,
            self.latest_relay_health,
            self.latest_telemetry_correlation,
            self.latest_synchronization_awareness
        )
        
        # New Phase 9.8 caches
        self.latest_agent_coordination = self.agent_coordination.get_status_summary()
        
        # New Phase 9.9 caches
        self.latest_swarm_coordination = self.swarm_coordination.get_status_summary()
        
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
        
    def _execute_workflow_step(self, workflow_name: str, step_name: str) -> Dict[str, Any]:
        if workflow_name == "recursive_loop_test" and step_name == "trigger_recursion_step":
            logger.info("Simulation: Attempting recursive workflow execution call")
            return self.workflow_engine.execute_workflow(workflow_name, self.grid_state, self._execute_workflow_step)
        
        if step_name == "shed_bus_5_load":
            logger.info("Executing load shed step: shedding Bus_5 load")
            self.client.publish("grid/control", json.dumps({
                "command": "SHED_LOAD",
                "bus_id": "Bus_5",
                "percentage": 100.0
            }))
            
        return {"status": "SUCCESS", "result": f"Executed {step_name} successfully"}

    def _workflow_task_callback(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        wf_to_trigger = payload.get("trigger_workflow")
        if wf_to_trigger:
            self.workflow_engine.execute_workflow(wf_to_trigger, self.grid_state, self._execute_workflow_step)
        return {"status": "SUCCESS", "payload": payload}

    def _execute_chain_step(self, chain_id: str, step: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(f"Daemon executing plan step: {step['objective']} on chain {chain_id}")
        res = self.planner_bridge.execute_step(
            chain_id=chain_id,
            step=step,
            grid_state=self.grid_state,
            n8n_bridge=self.n8n_bridge,
            workflow_engine=self.workflow_engine,
            reminder_mgr=self.reminder_mgr,
            mqtt_client=self.client
        )
        self.planning_engine.update_step_status(
            plan_id=chain_id,
            step_id=step.get("step_id", ""),
            status=res.get("status", "SUCCESS"),
            log_message=f"Step '{step['objective']}' execution result: {res.get('status')}"
        )
        return res
        
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
            
        # 4. Tick Autonomous Workflows, Reminders, and Webhooks
        self.workflow_engine.tick()
        
        triggered_reminders = self.reminder_mgr.tick()
        for r in triggered_reminders:
            logger.info(f"Triggered reminder: '{r['text']}'")
            # Publish to assistant/response
            t_ms = int(time.time() * 1000)
            self.client.publish("assistant/response", json.dumps({
                "timestamp": t_ms,
                "text": f"Peringatan: {r['text']}",
                "is_voice": False,
                "action": {"status": "SUCCESS", "action": "reminder_trigger"},
                "reasoning": {
                    "should_execute": False,
                    "should_respond": True,
                    "resolved_action": "reminder_trigger",
                    "parameters": {"text": r['text']},
                    "webhook_trigger": None,
                    "followup_recommendation": None,
                    "reasoning_logs": [f"Reminder triggered: {r['text']}"],
                    "grid_critical": False
                },
                "automation_hook": {}
            }))
            self.contextual_mem.add_interaction(role="assistant", text=f"Peringatan: {r['text']}")
            
        triggered_conditions = self.condition_monitor.scan(self.grid_state, self.hardware_sim_state)
        for c in triggered_conditions:
            logger.info(f"Triggered condition watch: {c['condition_id']}")
            # Auto-trigger corresponding workflows
            if c["condition_id"] == "critical_threat_watch":
                self.workflow_engine.execute_workflow("emergency_load_shed", self.grid_state, self._execute_workflow_step)
            elif c["condition_id"] == "high_latency_watch":
                self.workflow_engine.execute_workflow("system_status_check", self.grid_state, self._execute_workflow_step)
                
        self.n8n_bridge.tick()
        
        # Phase 9.5 ticks
        self.live_stream.tick()
        self.task_chain_mgr.tick(self._execute_chain_step, self.grid_state)
        
        # Phase 9.6 ticks
        latency_val = self.grid_state.get("telemetry", {}).get("latency_ms", 45.0)
        self.predictive_coordination.add_latency_point(latency_val)
        self.predictive_coordination.analyze_trends(self.grid_state, self.hardware_sim_state)
        self.pattern_awareness.analyze_patterns(self.grid_state, self.latest_workflows)
        self.workflow_optimizer.evaluate_efficiency(
            self.grid_state,
            self.latest_workflows,
            self.predictive_coordination.get_status_summary().get("workflow_timings", {})
        )
        self.cross_coordination.tick_synchronization(
            self.grid_state,
            self.hardware_sim_state,
            self.workflow_optimizer.recommendations
        )

        # Phase 9.7 ticks
        # 1. Update edge awareness states
        for node_id in self.edge_sim_overrides:
            override = self.edge_sim_overrides[node_id]
            if node_id == "esp32_zone1":
                default_latency = self.grid_state.get("telemetry", {}).get("latency_ms", 45.0)
                default_online = self.grid_state.get("comms_online", True)
                default_drift = self.hardware_sim_state.get("drift_sec", 0.0)
            else:
                default_latency = 45.0 if "esp32" in node_id else 12.0
                default_online = True
                default_drift = 0.0
                
            latency = override.get("latency_ms", default_latency)
            packet_loss = override.get("packet_loss_pct", 0.0)
            online = override.get("online", default_online)
            drift = override.get("drift_sec", default_drift)
            
            self.edge_awareness.update_edge_state(node_id, latency, packet_loss, online, drift)

        # 2. Update relay health states based on breaker telemetry
        telemetry = self.grid_state.get("telemetry", {})
        breaker_keys = ["L1_4", "L2_8", "L3_6", "L4_5", "L5_6", "L6_7", "L7_8", "L8_9", "L4_9"]
        for bk in breaker_keys:
            tel_key = f"breaker_{bk}"
            if tel_key in telemetry:
                state_val = "CLOSED" if telemetry[tel_key] == 1.0 else "OPEN"
                timing = self.breaker_sim_overrides.get(bk, {}).get("timing_ms", 50.0)
                self.relay_health.update_relay_state(bk, state_val, timing_ms=timing)

        # 3. Add telemetry snapshot to correlation engine
        self.telemetry_correlation.add_telemetry_snapshot(telemetry, time.time())

        # 4. Update sync awareness drifts
        for node_id in self.edge_sim_overrides:
            override = self.edge_sim_overrides[node_id]
            if node_id == "esp32_zone1":
                default_drift = self.hardware_sim_state.get("drift_sec", 0.0)
            else:
                default_drift = 0.0
            drift = override.get("drift_sec", default_drift)
            self.sync_awareness.update_node_drift(node_id, drift)

        # 5. Evaluate unified cyber-physical reasoning
        t_score = self.grid_state.get("threat", {}).get("threat_score", 0.0)
        t_conf = self.grid_state.get("threat", {}).get("confidence", 1.0)
        self.latest_cyber_physical_reasoning = self.cyber_physical_reasoning.evaluate_state(
            edge_sum=self.edge_awareness.get_status_summary(),
            relay_sum=self.relay_health.get_status_summary(),
            correlation_sum=self.telemetry_correlation.get_status_summary(),
            sync_sum=self.sync_awareness.get_status_summary(),
            threat_score=t_score,
            threat_confidence=t_conf
        )

        # Update Phase 9.7 caches
        self.latest_edge_awareness = self.edge_awareness.get_status_summary()
        self.latest_relay_health = self.relay_health.get_status_summary()
        self.latest_telemetry_correlation = self.telemetry_correlation.get_status_summary()
        self.latest_synchronization_awareness = self.sync_awareness.get_status_summary()

        # Phase 9.8 Coordinate specialized assistant agents
        active_attacks = []
        attack_status = telemetry.get("attack_status", {})
        if isinstance(attack_status, dict) and attack_status.get("active_attack"):
            active_attacks.append(attack_status["active_attack"])
        elif telemetry.get("attack_active") == 1:
            active_attacks.append("stealthy_fdia")

        self.latest_agent_coordination = self.agent_coordination.coordinate_agents(
            telemetry=telemetry,
            sync_states=self.latest_synchronization_awareness,
            relay_summary=self.latest_relay_health,
            workflows_summary=self.latest_workflows,
            task_chains_summary=self.latest_task_chains,
            threat_summary=self.grid_state.get("threat", {}),
            active_attacks=active_attacks
        )
        
        # Phase 9.9 Swarm Coordination Tick
        self.latest_swarm_coordination = self.swarm_coordination.coordinate_swarm(
            telemetry=telemetry,
            sync_states=self.latest_synchronization_awareness,
            edge_summary=self.latest_edge_awareness,
            relay_summary=self.latest_agent_coordination.get("relay_agent", {}),
            security_summary=self.latest_agent_coordination.get("security_agent", {}),
            active_attacks=active_attacks
        )
        
        # 5. Update voice orchestration summaries
        self.latest_voice_state = self.voice_orch_eng.get_status_summary()
        self.latest_wake_word = self.wake_word_mgr.get_status_summary()
        self.latest_proactive = self.proactive_eng.get_automation_summary()
        
        active_sess_id = self.voice_orch_eng.active_session_id
        self.latest_voice_memory = self.voice_session_mem.get_session_summary(active_sess_id)
        
        # Update autonomous caches
        self.latest_workflows = self.workflow_engine.get_status_summary()
        self.latest_reminders = self.reminder_mgr.get_status_summary()
        self.latest_conditions = self.condition_monitor.get_status_summary()
        self.latest_n8n_bridge = self.n8n_bridge.get_status_summary()
        self.latest_routines = self.adaptive_routine.get_status_summary()
        
        # Update Phase 9.5 caches
        self.latest_planning = self.planning_engine.get_status_summary()
        self.latest_task_chains = self.task_chain_mgr.get_status_summary()
        self.latest_live_stream = self.live_stream.get_status_summary()
        self.latest_dialogue = self.dialogue_engine.get_status_summary()
        self.latest_planner_bridge = self.planner_bridge.get_status_summary()
        
        # Update Phase 9.6 caches
        self.latest_predictive_coordination = self.predictive_coordination.get_status_summary()
        self.latest_persistent_memory = self.persistent_memory.get_status_summary()
        self.latest_pattern_awareness = self.pattern_awareness.get_status_summary()
        self.latest_workflow_optimizer = self.workflow_optimizer.get_status_summary()
        self.latest_cross_system_coordination = self.cross_coordination.get_status_summary()
        
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
            
            # Subscribe to Phase 9.4 simulation topics
            client.subscribe("assistant/workflow_trigger")
            client.subscribe("assistant/reminder_trigger")
            client.subscribe("assistant/condition_trigger")
            client.subscribe("assistant/n8n_bridge_trigger")
            client.subscribe("assistant/routine_trigger")
            
            # Subscribe to Phase 9.5 simulation topics
            client.subscribe("assistant/plan_simulation")
            client.subscribe("assistant/chain_simulation")
            client.subscribe("assistant/stream_simulation")
            client.subscribe("assistant/dialogue_simulation")
            client.subscribe("assistant/orchestration_simulation")
            
            # Subscribe to Phase 9.6 simulation topics
            client.subscribe("assistant/predictive_coordination_simulation")
            client.subscribe("assistant/persistent_memory_simulation")
            client.subscribe("assistant/pattern_awareness_simulation")
            client.subscribe("assistant/workflow_optimizer_simulation")
            client.subscribe("assistant/cross_system_coordination_simulation")
            
            client.subscribe("assistant/edge_awareness_simulation")
            client.subscribe("assistant/relay_health_simulation")
            client.subscribe("assistant/telemetry_correlation_simulation")
            client.subscribe("assistant/synchronization_awareness_simulation")
            client.subscribe("assistant/cyber_physical_reasoning_simulation")
            client.subscribe("assistant/agent_coordination_simulation")
            client.subscribe("assistant/swarm_coordination_simulation")

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
            elif topic == "assistant/workflow_trigger":
                action = payload.get("action")
                if action == "execute":
                    self.workflow_engine.execute_workflow(payload.get("workflow_name"), self.grid_state, self._execute_workflow_step)
                elif action == "schedule_delayed":
                    self.workflow_engine.schedule_delayed_task(
                        payload.get("task_name", "delayed_status_check"),
                        float(payload.get("delay_sec", 5.0)),
                        self._workflow_task_callback,
                        payload.get("payload", {})
                    )
                elif action == "clear":
                    self.workflow_engine.clear_history()
                
                self.latest_workflows = self.workflow_engine.get_status_summary()
                self.publish_telemetry()
            elif topic == "assistant/reminder_trigger":
                action = payload.get("action")
                if action == "schedule":
                    self.reminder_mgr.add_reminder(
                        payload.get("text", "Default Reminder"),
                        float(payload.get("delay_sec", 5.0)),
                        payload.get("recurring_interval")
                    )
                elif action == "cancel":
                    self.reminder_mgr.cancel_reminder(payload.get("reminder_id", ""))
                elif action == "clear":
                    self.reminder_mgr.clear_all()
                
                self.latest_reminders = self.reminder_mgr.get_status_summary()
                self.publish_telemetry()
            elif topic == "assistant/condition_trigger":
                action = payload.get("action")
                if action == "register":
                    self.condition_monitor.register_watch(
                        payload.get("condition_id"),
                        payload.get("watch_type", "custom"),
                        payload.get("target_field"),
                        payload.get("operator"),
                        payload.get("threshold"),
                        float(payload.get("cooldown", 45.0)),
                        bool(payload.get("is_recurring", True))
                    )
                elif action == "remove":
                    self.condition_monitor.remove_watch(payload.get("condition_id"))
                elif action == "clear":
                    self.condition_monitor.clear_history()
                
                self.latest_conditions = self.condition_monitor.get_status_summary()
                self.publish_telemetry()
            elif topic == "assistant/n8n_bridge_trigger":
                action = payload.get("action")
                if action == "dispatch":
                    self.n8n_bridge.simulate_network_failure = bool(payload.get("simulate_network_failure", False))
                    self.n8n_bridge.dispatch_webhook(
                        payload.get("webhook_name", "test_webhook"),
                        payload.get("payload", {}),
                        bool(payload.get("force_failure", False))
                    )
                elif action == "clear":
                    self.n8n_bridge.clear_history()
                
                self.latest_n8n_bridge = self.n8n_bridge.get_status_summary()
                self.publish_telemetry()
            elif topic == "assistant/routine_trigger":
                action = payload.get("action")
                if action == "record":
                    self.adaptive_routine.record_interaction(payload.get("command"), payload.get("phrase", ""))
                elif action == "accept":
                    self.adaptive_routine.accept_routine(payload.get("routine_type"))
                elif action == "clear":
                    self.adaptive_routine.clear_routines()
                
                self.latest_routines = self.adaptive_routine.get_status_summary()
                self.publish_telemetry()
            elif topic == "assistant/plan_simulation":
                action = payload.get("action")
                if action == "create":
                    self.planning_engine.create_plan(
                        payload.get("query", ""),
                        payload.get("intent", {})
                    )
                elif action == "update_step":
                    self.planning_engine.update_step_status(
                        payload.get("plan_id"),
                        payload.get("step_id"),
                        payload.get("status"),
                        payload.get("log")
                    )
                self.latest_planning = self.planning_engine.get_status_summary()
                self.publish_telemetry()
            elif topic == "assistant/chain_simulation":
                action = payload.get("action")
                if action == "submit":
                    plan = payload.get("plan")
                    if not plan and self.planning_engine.active_plans:
                        plan = list(self.planning_engine.active_plans.values())[-1]
                    if plan:
                        self.task_chain_mgr.submit_chain(plan)
                elif action == "cancel":
                    self.task_chain_mgr.cancel_chain(payload.get("chain_id"))
                self.latest_task_chains = self.task_chain_mgr.get_status_summary()
                self.publish_telemetry()
            elif topic == "assistant/stream_simulation":
                action = payload.get("action")
                if action == "start":
                    self.live_stream.start_stream(payload.get("text", "Default streaming text"))
                elif action == "interrupt":
                    self.live_stream.interrupt()
                self.latest_live_stream = self.live_stream.get_status_summary()
                self.publish_telemetry()
            elif topic == "assistant/dialogue_simulation":
                action = payload.get("action")
                if action == "check":
                    self.dialogue_engine.check_ambiguity(
                        payload.get("phrase", ""),
                        payload.get("intent", {})
                    )
                elif action == "resolve":
                    self.dialogue_engine.resolve_clarification(payload.get("answer", ""))
                elif action == "clear":
                    self.dialogue_engine.clear_dialogue()
                self.latest_dialogue = self.dialogue_engine.get_status_summary()
                self.publish_telemetry()
            elif topic == "assistant/orchestration_simulation":
                action = payload.get("action")
                if action == "set_safety":
                    self.planner_bridge.confidence_threshold = float(payload.get("confidence_threshold", 0.50))
                    self.planner_bridge.min_stability = float(payload.get("min_stability", 30.0))
                elif action == "evaluate":
                    self.planner_bridge.evaluate_confidence_and_safety(
                        payload.get("step", {}),
                        self.grid_state
                    )
                self.latest_planner_bridge = self.planner_bridge.get_status_summary()
                self.publish_telemetry()
            elif topic == "assistant/predictive_coordination_simulation":
                action = payload.get("action")
                if action == "add_latency":
                    self.predictive_coordination.add_latency_point(float(payload.get("latency", 45.0)))
                self.latest_predictive_coordination = self.predictive_coordination.get_status_summary()
                self.publish_telemetry()
            elif topic == "assistant/persistent_memory_simulation":
                action = payload.get("action")
                if action == "add_interaction":
                    self.persistent_memory.add_interaction(
                        payload.get("query", "Default query"),
                        payload.get("resolved_action", "MEASURE_LATENCY")
                    )
                elif action == "clear":
                    self.persistent_memory.clear_memory()
                self.latest_persistent_memory = self.persistent_memory.get_status_summary()
                self.publish_telemetry()
            elif topic == "assistant/pattern_awareness_simulation":
                action = payload.get("action")
                if action == "analyze":
                    self.pattern_awareness.analyze_patterns(self.grid_state, self.latest_workflows)
                elif action == "reset":
                    self.pattern_awareness.reset_counters()
                self.latest_pattern_awareness = self.pattern_awareness.get_status_summary()
                self.publish_telemetry()
            elif topic == "assistant/workflow_optimizer_simulation":
                action = payload.get("action")
                if action == "approve":
                    self.workflow_optimizer.approve_recommendation(payload.get("workflow_name"))
                self.latest_workflow_optimizer = self.workflow_optimizer.get_status_summary()
                self.publish_telemetry()
            elif topic == "assistant/cross_system_coordination_simulation":
                self.cross_coordination.tick_synchronization(
                    self.grid_state,
                    self.hardware_sim_state,
                    self.workflow_optimizer.recommendations
                )
                self.latest_cross_system_coordination = self.cross_coordination.get_status_summary()
                self.publish_telemetry()
                
            elif topic == "assistant/edge_awareness_simulation":
                action = payload.get("action")
                if action == "set_health":
                    node_id = payload.get("node_id")
                    if node_id in self.edge_sim_overrides:
                        self.edge_sim_overrides[node_id] = {
                            "latency_ms": payload.get("latency_ms"),
                            "packet_loss_pct": payload.get("packet_loss_pct"),
                            "online": payload.get("online"),
                            "drift_sec": payload.get("drift_sec")
                        }
                elif action == "reset":
                    for k in self.edge_sim_overrides:
                        self.edge_sim_overrides[k].clear()
                self.latest_edge_awareness = self.edge_awareness.get_status_summary()
                self.publish_telemetry()
                
            elif topic == "assistant/relay_health_simulation":
                action = payload.get("action")
                breaker_id = payload.get("breaker_id")
                if action == "trigger_oscillation" and breaker_id:
                    # Toggle multiple times to trigger rapid transitions
                    initial_state = self.relay_health.breakers.get(breaker_id, {}).get("state", "CLOSED")
                    for i in range(5):
                        temp_state = "OPEN" if i % 2 == 0 else "CLOSED"
                        self.relay_health.update_relay_state(breaker_id, temp_state, timing_ms=50.0)
                    # Restore initial state
                    self.relay_health.update_relay_state(breaker_id, initial_state, timing_ms=50.0)
                elif action == "set_wear" and breaker_id:
                    if breaker_id in self.relay_health.breakers:
                        self.relay_health.breakers[breaker_id]["switch_count"] = int(payload.get("switch_count", 170))
                        self.relay_health.breakers[breaker_id]["wear_pct"] = min(100.0, self.relay_health.breakers[breaker_id]["switch_count"] * 0.5)
                elif action == "set_latency" and breaker_id:
                    if breaker_id in self.relay_health.breakers:
                        self.relay_health.breakers[breaker_id]["timing_ms"] = float(payload.get("timing_ms", 150.0))
                elif action == "reset":
                    self.relay_health.reset_engine()
                self.latest_relay_health = self.relay_health.get_status_summary()
                self.publish_telemetry()
                
            elif topic == "assistant/telemetry_correlation_simulation":
                action = payload.get("action")
                if action == "inject_correlation":
                    injected = payload.get("snapshot", {})
                    self.telemetry_correlation.add_telemetry_snapshot(injected, time.time())
                elif action == "reset":
                    self.telemetry_correlation.reset_engine()
                self.latest_telemetry_correlation = self.telemetry_correlation.get_status_summary()
                self.publish_telemetry()
                
            elif topic == "assistant/synchronization_awareness_simulation":
                action = payload.get("action")
                if action == "trigger_drift":
                    node_id = payload.get("node_id")
                    drift_sec = float(payload.get("drift_sec", 0.08))
                    if node_id in self.edge_sim_overrides:
                        self.edge_sim_overrides[node_id]["drift_sec"] = drift_sec
                elif action == "reset":
                    self.sync_awareness.reset_engine()
                self.latest_synchronization_awareness = self.sync_awareness.get_status_summary()
                self.publish_telemetry()
                
            elif topic == "assistant/cyber_physical_reasoning_simulation":
                # Simulated threat update
                threat_score = float(payload.get("threat_score", 0.0))
                threat_confidence = float(payload.get("confidence", 1.0))
                self.grid_state["threat"] = {"threat_score": threat_score, "confidence": threat_confidence}
                self.latest_cyber_physical_reasoning = self.cyber_physical_reasoning.evaluate_state(
                    edge_sum=self.latest_edge_awareness,
                    relay_sum=self.latest_relay_health,
                    correlation_sum=self.latest_telemetry_correlation,
                    sync_sum=self.latest_synchronization_awareness,
                    threat_score=threat_score,
                    threat_confidence=threat_confidence
                )
                self.publish_telemetry()
                
            elif topic == "assistant/agent_coordination_simulation":
                action = payload.get("action")
                if action == "set_mode":
                    mode = payload.get("mode")
                    self.agent_coordination.simulation_mode = mode
                    if mode == "drift_storm":
                        self.edge_sim_overrides["esp32_zone1"]["drift_sec"] = 0.03
                        self.edge_sim_overrides["esp32_zone2"]["drift_sec"] = 0.04
                        self.edge_sim_overrides["esp32_zone3"]["drift_sec"] = 0.05
                    elif mode == "relay_spikes":
                        for i in range(5):
                            temp_state = "OPEN" if i % 2 == 0 else "CLOSED"
                            self.relay_health.update_relay_state("L1_4", temp_state, timing_ms=50.0)
                elif action == "reset":
                    self.agent_coordination.reset_engine()
                    for k in self.edge_sim_overrides:
                        self.edge_sim_overrides[k].clear()
                    self.relay_health.reset_engine()
                self.latest_agent_coordination = self.agent_coordination.get_status_summary()
                self.publish_telemetry()

            elif topic == "assistant/swarm_coordination_simulation":
                action = payload.get("action")
                if action == "set_mode":
                    mode = payload.get("mode")
                    self.swarm_coordination.simulation_mode = mode
                    if mode == "drift_storm" or mode == "distributed_drift_escalation":
                        self.edge_sim_overrides["esp32_zone1"]["drift_sec"] = 0.03
                        self.edge_sim_overrides["esp32_zone2"]["drift_sec"] = 0.04
                        self.edge_sim_overrides["esp32_zone3"]["drift_sec"] = 0.05
                    elif mode == "edge_mesh_partition_failures":
                        self.edge_sim_overrides["esp32_zone2"]["online"] = True
                        self.edge_sim_overrides["esp32_zone3"]["online"] = True
                elif action == "reset":
                    self.swarm_coordination.reset_engine()
                    for k in self.edge_sim_overrides:
                        self.edge_sim_overrides[k].clear()
                self.latest_swarm_coordination = self.swarm_coordination.get_status_summary()
                self.publish_telemetry()

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
        
        # Check streaming interruption (Interruption-Aware Streaming rule)
        if self.live_stream.is_streaming:
            self.live_stream.interrupt()
            self.latest_live_stream = self.live_stream.get_status_summary()
            logger.info("Live stream interrupted by new user request.")
        
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
        
        # Cyber-Physical reasoning query intercept (Phase 9.7)
        threat_score = self.grid_state.get("threat", {}).get("threat_score", 0.0)
        threat_confidence = self.grid_state.get("threat", {}).get("confidence", 1.0)
        grid_critical = (threat_score > 70.0)
        
        # Multi-Agent query intercept (Phase 9.8)
        # Swarm query intercept (Phase 9.9)
        swarm_response = self.swarm_coordination.handle_query(text)
        if swarm_response:
            self._respond(
                swarm_response,
                is_voice,
                reasoning={
                    "should_execute": False,
                    "should_respond": True,
                    "resolved_action": "swarm_coordination_query",
                    "reasoning_logs": ["Swarm intelligence query resolved by Swarm Coordinator."],
                    "grid_critical": grid_critical
                }
            )
            return

        agent_response = self.agent_coordination.handle_query(text)
        if agent_response:
            self._respond(
                agent_response,
                is_voice,
                reasoning={
                    "should_execute": False,
                    "should_respond": True,
                    "resolved_action": "agent_coordination_query",
                    "reasoning_logs": ["Multi-agent coordination query resolved by Coordinator."],
                    "grid_critical": grid_critical
                }
            )
            return
        
        cp_response = self.cyber_physical_reasoning.handle_query(
            text,
            edge_sum=self.latest_edge_awareness,
            relay_sum=self.latest_relay_health,
            correlation_sum=self.latest_telemetry_correlation,
            sync_sum=self.latest_synchronization_awareness,
            threat_score=threat_score,
            threat_confidence=threat_confidence
        )
        if cp_response:
            self._respond(
                cp_response,
                is_voice,
                reasoning={
                    "should_execute": False,
                    "should_respond": True,
                    "resolved_action": "cyber_physical_query",
                    "reasoning_logs": ["Cyber-physical awareness query resolved directly by Reasoning Engine."],
                    "grid_critical": grid_critical
                }
            )
            return
            
        # 4. Intent detection & Dialogue Clarification Check
        semantic_intent = None
        if self.dialogue_engine.state == "AWAITING_CLARIFICATION":
            res = self.dialogue_engine.resolve_clarification(text)
            if res["status"] == "SUCCESS":
                semantic_intent = res["resolved_intent"]
                # Override text and logs
                text = res["original_phrase"]
                logger.info(f"Resolved dialogue clarification: {semantic_intent}")
            else:
                response_text = self.dialogue_engine.clarification_question
                self._respond(response_text, is_voice)
                return
        else:
            intent = self.intent_eng.detect_intent(text)
            semantic_intent = self.semantic_intent_eng.detect_intent(
                text, 
                previous_action=self.contextual_mem.active_subject
            )
            self.latest_semantic_intent = semantic_intent
            
            # Check ambiguity
            self.dialogue_engine.check_ambiguity(text, semantic_intent)
            self.latest_dialogue = self.dialogue_engine.get_status_summary()
            if self.dialogue_engine.state == "AWAITING_CLARIFICATION":
                response_text = self.dialogue_engine.clarification_question
                self._respond(response_text, is_voice)
                return

        # 5. Context update
        self.context_eng.update_context(semantic_intent, self.state_mgr.state)
        
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
        self.persistent_memory.add_interaction(text, semantic_intent.get("action"))

        
        # 8. Conversational planning check (Multi-Step task sequencing)
        plan = self.planning_engine.create_plan(text, semantic_intent)
        self.latest_planning = self.planning_engine.get_status_summary()
        if len(plan["steps"]) > 1:
            chain_res = self.task_chain_mgr.submit_chain(plan)
            self.latest_task_chains = self.task_chain_mgr.get_status_summary()
            if chain_res["status"] == "SUBMITTED":
                response_text = f"Saya telah menjadualkan pelan tindakan multi-step untuk: {plan['original_query']}. Langkah pertama: {plan['steps'][0]['description']}."
                self._respond(
                    response_text,
                    is_voice,
                    action_result=chain_res,
                    reasoning={
                        "should_execute": True,
                        "should_respond": True,
                        "resolved_action": "submit_chain",
                        "reasoning_logs": plan["reasoning_logs"],
                        "grid_critical": False
                    }
                )
                return
            elif chain_res["status"] == "REJECTED":
                response_text = f"Tindakan disekat: {chain_res['reason']}"
                self._respond(
                    response_text,
                    is_voice,
                    action_result=chain_res,
                    reasoning={
                        "should_execute": False,
                        "should_respond": True,
                        "resolved_action": "submit_chain_rejected",
                        "reasoning_logs": plan["reasoning_logs"],
                        "grid_critical": False
                    }
                )
                return

        # 9. Reasoning & Decision Routing (Standard Single Step)
        reasoning = self.reasoning_eng.reason(
            intent=semantic_intent,
            context=self.context_eng.get_context_summary(),
            emotion=self.emotion_eng.get_emotion_summary(),
            grid_state=self.grid_state
        )
        self.latest_reasoning = reasoning
        
        # 10. Execution path
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
            self.adaptive_routine.record_interaction(action_name, text)
            
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
            
        # 11. Response formulation
        response_text = self.semantic_response_eng.generate_response(
            reasoning=reasoning,
            action_result=action_result,
            emotion=self.emotion_eng.get_emotion_summary()
        )
        
        self._respond(response_text, is_voice, action_result=action_result, reasoning=reasoning, hook_status=hook_status)
        
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
        
        self.reminder_mgr.clear_all()
        self.condition_monitor.clear_history()
        self.n8n_bridge.clear_history()
        self.adaptive_routine.clear_routines()
        self.workflow_engine.clear_history()
        
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
        
        self.latest_workflows = self.workflow_engine.get_status_summary()
        self.latest_reminders = self.reminder_mgr.get_status_summary()
        self.latest_conditions = self.condition_monitor.get_status_summary()
        self.latest_n8n_bridge = self.n8n_bridge.get_status_summary()
        self.latest_routines = self.adaptive_routine.get_status_summary()

        # Reset Phase 9.5 engines and states
        self.planning_engine.active_plans.clear()
        self.planning_engine.plan_history.clear()
        self.task_chain_mgr.active_chains.clear()
        self.task_chain_mgr.completed_chains.clear()
        self.live_stream.is_streaming = False
        self.live_stream.status = "IDLE"
        self.live_stream.output_buffer = ""
        self.dialogue_engine.clear_dialogue()
        self.planner_bridge.validation_logs.clear()
        
        self.latest_planning = self.planning_engine.get_status_summary()
        self.latest_task_chains = self.task_chain_mgr.get_status_summary()
        self.latest_live_stream = self.live_stream.get_status_summary()
        self.latest_dialogue = self.dialogue_engine.get_status_summary()
        self.latest_planner_bridge = self.planner_bridge.get_status_summary()
        
        # Reset Phase 9.6 engines and states
        self.predictive_coordination.latency_history.clear()
        self.predictive_coordination.workflow_execution_history.clear()
        self.predictive_coordination.forecasts.clear()
        self.predictive_coordination.suggestions.clear()
        self.persistent_memory.clear_memory()
        self.pattern_awareness.reset_counters()
        self.workflow_optimizer.recommendations.clear()
        self.workflow_optimizer.active_optimizations.clear()
        self.cross_coordination.conflict_logs.clear()
        self.cross_coordination.sync_state = "SYNCED"
        self.cross_coordination.drift_sec = 0.0
        
        # Phase 9.7 resets
        self.edge_awareness.reset_engine()
        self.relay_health.reset_engine()
        self.telemetry_correlation.reset_engine()
        self.sync_awareness.reset_engine()
        for k in self.edge_sim_overrides:
            self.edge_sim_overrides[k].clear()
        self.breaker_sim_overrides.clear()
        
        # Phase 9.8 resets
        self.agent_coordination.reset_engine()
        self.latest_agent_coordination = self.agent_coordination.get_status_summary()
        
        # Phase 9.9 resets
        self.swarm_coordination.reset_engine()
        self.latest_swarm_coordination = self.swarm_coordination.get_status_summary()

        
        self.latest_predictive_coordination = self.predictive_coordination.get_status_summary()
        self.latest_persistent_memory = self.persistent_memory.get_status_summary()
        self.latest_pattern_awareness = self.pattern_awareness.get_status_summary()
        self.latest_workflow_optimizer = self.workflow_optimizer.get_status_summary()
        self.latest_cross_system_coordination = self.cross_coordination.get_status_summary()
        
        self.state_mgr.transition_to("IDLE")
        self.publish_telemetry()

        
    def _respond(self, response_text: str, is_voice: bool, action_result: Dict[str, Any] = {}, reasoning: Dict[str, Any] = {}, hook_status: Dict[str, Any] = {}):
        # Calculate presence delay simulation
        threat_score = self.grid_state["threat"].get("threat_score", 0.0)
        grid_critical = (threat_score > 70.0)
        pacing_delay = self.presence_eng.calculate_pacing_delay(
            emotion_mood=self.emotion_eng.get_emotion_summary().get("assistant_mood", "calm"),
            grid_critical=grid_critical
        )
        if pacing_delay > 0.0:
            time.sleep(pacing_delay)
            
        self.state_mgr.transition_to("RESPONDING")
        if is_voice:
            self.voice_orch_eng.transition_to("SPEAKING")
        self.publish_telemetry()
        
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
        
        # Start streaming response chunks
        self.live_stream.start_stream(response_text)
        self.latest_live_stream = self.live_stream.get_status_summary()
        
        # Transition back to IDLE
        self.state_mgr.transition_to("IDLE")
        if is_voice:
            self.voice_orch_eng.transition_to("LISTENING")
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
        # 18. assistant/workflows [NEW]
        self.client.publish("assistant/workflows", json.dumps({
            "timestamp": t_ms,
            "workflows": self.latest_workflows
        }))
        # 19. assistant/reminders [NEW]
        self.client.publish("assistant/reminders", json.dumps({
            "timestamp": t_ms,
            "reminders": self.latest_reminders
        }))
        # 20. assistant/conditions [NEW]
        self.client.publish("assistant/conditions", json.dumps({
            "timestamp": t_ms,
            "conditions": self.latest_conditions
        }))
        # 21. assistant/n8n_bridge [NEW]
        self.client.publish("assistant/n8n_bridge", json.dumps({
            "timestamp": t_ms,
            "n8n_bridge": self.latest_n8n_bridge
        }))
        # 22. assistant/routines [NEW]
        self.client.publish("assistant/routines", json.dumps({
            "timestamp": t_ms,
            "routines": self.latest_routines
        }))
        
        # 23. assistant/conversation_planning [NEW]
        self.client.publish("assistant/conversation_planning", json.dumps(self.latest_planning))
        # 24. assistant/task_chains [NEW]
        self.client.publish("assistant/task_chains", json.dumps(self.latest_task_chains))
        # 25. assistant/live_stream [NEW]
        self.client.publish("assistant/live_stream", json.dumps(self.latest_live_stream))
        # 26. assistant/dialogue [NEW]
        self.client.publish("assistant/dialogue", json.dumps(self.latest_dialogue))
        # 27. assistant/orchestration_planner [NEW]
        self.client.publish("assistant/orchestration_planner", json.dumps(self.latest_planner_bridge))
        
        # Phase 9.6 publishes
        # 28. assistant/predictive_coordination [NEW]
        self.client.publish("assistant/predictive_coordination", json.dumps(self.latest_predictive_coordination))
        # 29. assistant/persistent_memory [NEW]
        self.client.publish("assistant/persistent_memory", json.dumps(self.latest_persistent_memory))
        # 30. assistant/pattern_awareness [NEW]
        self.client.publish("assistant/pattern_awareness", json.dumps(self.latest_pattern_awareness))
        # 31. assistant/workflow_optimizer [NEW]
        self.client.publish("assistant/workflow_optimizer", json.dumps(self.latest_workflow_optimizer))
        # 32. assistant/cross_system_coordination [NEW]
        self.client.publish("assistant/cross_system_coordination", json.dumps(self.latest_cross_system_coordination))
        
        # Phase 9.7 publishes
        # 33. assistant/edge_awareness [NEW]
        self.client.publish("assistant/edge_awareness", json.dumps(self.latest_edge_awareness))
        # 34. assistant/relay_health [NEW]
        self.client.publish("assistant/relay_health", json.dumps(self.latest_relay_health))
        # 35. assistant/telemetry_correlation [NEW]
        self.client.publish("assistant/telemetry_correlation", json.dumps(self.latest_telemetry_correlation))
        # 36. assistant/synchronization_awareness [NEW]
        self.client.publish("assistant/synchronization_awareness", json.dumps(self.latest_synchronization_awareness))
        # 37. assistant/cyber_physical_reasoning [NEW]
        self.client.publish("assistant/cyber_physical_reasoning", json.dumps(self.latest_cyber_physical_reasoning))

        # Phase 9.8 publishes
        # 38. assistant/agent_coordination [NEW]
        self.client.publish("assistant/agent_coordination", json.dumps(self.latest_agent_coordination))
        # 39. assistant/telemetry_agent [NEW]
        self.client.publish("assistant/telemetry_agent", json.dumps(self.latest_agent_coordination["telemetry_agent"]))
        # 40. assistant/relay_agent [NEW]
        self.client.publish("assistant/relay_agent", json.dumps(self.latest_agent_coordination["relay_agent"]))
        # 41. assistant/workflow_agent [NEW]
        self.client.publish("assistant/workflow_agent", json.dumps(self.latest_agent_coordination["workflow_agent"]))
        # 42. assistant/security_agent [NEW]
        self.client.publish("assistant/security_agent", json.dumps(self.latest_agent_coordination["security_agent"]))

        # Phase 9.9 publishes
        # 43. assistant/swarm_coordination [NEW]
        self.client.publish("assistant/swarm_coordination", json.dumps(self.latest_swarm_coordination))
        # 44. assistant/federated_memory [NEW]
        self.client.publish("assistant/federated_memory", json.dumps(self.latest_swarm_coordination["federated_memory"]))
        # 45. assistant/distributed_consensus [NEW]
        self.client.publish("assistant/distributed_consensus", json.dumps(self.latest_swarm_coordination["distributed_consensus"]))
        # 46. assistant/edge_mesh [NEW]
        self.client.publish("assistant/edge_mesh", json.dumps(self.latest_swarm_coordination["edge_mesh"]))
        # 47. assistant/swarm_anomaly_fusion [NEW]
        self.client.publish("assistant/swarm_anomaly_fusion", json.dumps(self.latest_swarm_coordination["anomaly_fusion"]))



if __name__ == "__main__":
    daemon = AssistantDaemon()
    daemon.start()
