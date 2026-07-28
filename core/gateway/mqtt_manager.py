import os
import json
import logging
import asyncio
from typing import Dict, Any, Optional
import paho.mqtt.client as mqtt
from gateway.store import store
from gateway.websocket_manager import ws_manager
from gateway.translator import TelemetryTranslator

logger = logging.getLogger("gateway.mqtt_manager")

class MQTTManager:
    def __init__(self):
        self.broker = os.getenv("MQTT_BROKER", "localhost")
        self.port = int(os.getenv("MQTT_PORT", 1883))
        self.client = mqtt.Client(client_id="fastapi_gateway_service")
        self.translator = TelemetryTranslator()
        
        # Callbacks registration
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.loop: Optional[asyncio.AbstractEventLoop] = None

    def start(self, loop: asyncio.AbstractEventLoop):
        self.loop = loop
        def connect_loop():
            import time
            connected = False
            retry_delay = 1.0
            while not connected:
                try:
                    self.client.connect(self.broker, self.port, keepalive=60)
                    self.client.loop_start()
                    connected = True
                    logger.info(f"MQTT client connected successfully to {self.broker}:{self.port}")
                except Exception as e:
                    logger.warning(f"MQTT client connection failed: {e}. Retrying in {retry_delay}s...")
                    time.sleep(retry_delay)
                    retry_delay = min(15.0, retry_delay * 1.5)
        import threading
        threading.Thread(target=connect_loop, daemon=True).start()

    def stop(self):
        self.client.loop_stop()
        self.client.disconnect()
        logger.info("MQTT client stopped.")

    def publish(self, topic: str, payload: Any):
        try:
            msg_str = json.dumps(payload)
            self.client.publish(topic, msg_str)
            logger.info(f"Published message to {topic}: {msg_str}")
        except Exception as e:
            logger.error(f"Error publishing message to {topic}: {e}")

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info("Connected to MQTT Broker!")
            # Hierarchical AC subscriptions
            client.subscribe("pypy/grid/bus/+/metrics")
            client.subscribe("pypy/grid/line/+/flow")
            client.subscribe("pypy/grid/gen/+/status")
            client.subscribe("pypy/grid/telemetry")
            client.subscribe("pypy/+/+/telemetry")
            
            # Legacy Subscriptions
            client.subscribe("grid/telemetry")
            client.subscribe("grid/events")
            client.subscribe("grid/alerts")
            client.subscribe("grid/control")
            client.subscribe("grid/attack")
            client.subscribe("grid/config")
            client.subscribe("grid/threat")
            client.subscribe("grid/ai_prediction")
            client.subscribe("grid/ai_forecast_multi_bus")
            client.subscribe("grid/ai_threat_forecast")
            client.subscribe("grid/pinn_forecast")
            client.subscribe("grid/physics_validation")
            client.subscribe("grid/trust_scores")
            client.subscribe("grid/adaptive_filter")
            client.subscribe("grid/ai_orchestrator")
            client.subscribe("grid/recommended_actions")
            client.subscribe("grid/pre_rl")
            client.subscribe("grid/defense")
            
            # Layer 11A Predictive Defense subscriptions
            client.subscribe("prediction/threat_forecast")
            client.subscribe("prediction/pre_attack_alert")
            client.subscribe("prediction/future_risk")
            client.subscribe("prediction/trust_forecast")
            client.subscribe("prediction/escalation_probability")
            client.subscribe("prediction/recommended_prevention")

            # Layer 11B Strategic Coordination subscriptions
            client.subscribe("grid/strategy")
            client.subscribe("grid/strategy_priority")
            client.subscribe("grid/strategy_recommendation")
            client.subscribe("grid/strategy_memory")

            # Layer 11C Adversarial Defense subscriptions
            client.subscribe("grid/adversarial/campaign")
            client.subscribe("grid/adversarial/resilience")
            client.subscribe("grid/adversarial/weaknesses")
            client.subscribe("grid/adversarial/recommendations")

            # Layer 11D Adaptive Red vs Blue AI Arena subscriptions
            client.subscribe("grid/arena/match")
            client.subscribe("grid/arena/rewards")
            client.subscribe("grid/arena/evolution")
            client.subscribe("grid/arena/recommendations")

            client.subscribe("grid/l6_recovery")
            client.subscribe("grid/l6_adaptive_recovery")
            client.subscribe("grid/l6_containment")
            client.subscribe("grid/l6_degraded_mode")
            client.subscribe("grid/l6_survival")
            client.subscribe("grid/l6_islanding")
            client.subscribe("grid/l6_blackstart")
            client.subscribe("grid/l6_balancing")
            client.subscribe("grid/l6_predictive_stability")
            client.subscribe("grid/l6_survival_forecast")
            client.subscribe("grid/l6_proactive_actions")
            client.subscribe("grid/l6_self_preservation")
            client.subscribe("grid/l6_agents")
            client.subscribe("grid/l6_agent_consensus")
            client.subscribe("grid/l6_agent_conflicts")
            client.subscribe("grid/l6_distributed_state")
            client.subscribe("grid/l6_agent_confidence")
            client.subscribe("hardware/relay")
            client.subscribe("hardware/gpio")
            client.subscribe("hardware/sensor")
            client.subscribe("hardware/device_health")
            client.subscribe("hardware/command_log")
            client.subscribe("hardware/faults")
            client.subscribe("hardware/relay_faults")
            client.subscribe("hardware/anomalies")
            client.subscribe("hardware/virtual_devices")
            client.subscribe("hardware/spoofed_telemetry")
            client.subscribe("hardware/fault_propagation")
            client.subscribe("hardware/usb_events")
            client.subscribe("hardware/rogue_devices")
            client.subscribe("hardware/badusb")
            client.subscribe("hardware/intrusion_alerts")
            client.subscribe("hardware/device_trust")
            client.subscribe("hardware/attack_state")
            client.subscribe("hardware/attack_propagation")
            client.subscribe("hardware/orchestration")
            client.subscribe("hardware/edge_devices")
            client.subscribe("hardware/relay_execution")
            client.subscribe("hardware/distributed_bus")
            client.subscribe("hardware/synchronization")
            client.subscribe("hardware/orchestration_conflicts")
            client.subscribe("hardware/execution_gateway")
            client.subscribe("hardware/reliability")
            client.subscribe("hardware/safety_guard")
            client.subscribe("hardware/deployment_profiles")
            client.subscribe("hardware/telemetry_validation")
            client.subscribe("hardware/resilience")
            client.subscribe("hardware/disaster_recovery")
            client.subscribe("hardware/redundancy")
            client.subscribe("hardware/deployment_hardening")
            client.subscribe("hardware/large_scale_sync")
            client.subscribe("assistant/state")
            client.subscribe("assistant/intent")
            client.subscribe("assistant/emotion")
            client.subscribe("assistant/actions")
            client.subscribe("assistant/context")
            client.subscribe("assistant/memory")
            client.subscribe("assistant/response")
            client.subscribe("assistant/chat_input")
            client.subscribe("assistant/voice_input")
            client.subscribe("assistant/reset")
            client.subscribe("assistant/runtime")
            client.subscribe("assistant/semantic_intent")
            client.subscribe("assistant/contextual_memory")
            client.subscribe("assistant/reasoning")
            client.subscribe("assistant/automation_hooks")
            client.subscribe("assistant/semantic_response")
            client.subscribe("assistant/voice_state")
            client.subscribe("assistant/wake_word")
            client.subscribe("assistant/proactive")
            client.subscribe("assistant/voice_memory")
            client.subscribe("assistant/presence")
            client.subscribe("assistant/workflows")
            client.subscribe("assistant/reminders")
            client.subscribe("assistant/conditions")
            client.subscribe("assistant/n8n_bridge")
            client.subscribe("assistant/routines")
            client.subscribe("assistant/conversation_planning")
            client.subscribe("assistant/task_chains")
            client.subscribe("assistant/live_stream")
            client.subscribe("assistant/dialogue")
            client.subscribe("assistant/orchestration_planner")
            
            # Phase 9.6 subscriptions
            client.subscribe("assistant/predictive_coordination")
            client.subscribe("assistant/persistent_memory")
            client.subscribe("assistant/pattern_awareness")
            client.subscribe("assistant/workflow_optimizer")
            client.subscribe("assistant/cross_system_coordination")
            
            # Phase 9.7 subscriptions
            client.subscribe("assistant/edge_awareness")
            client.subscribe("assistant/relay_health")
            client.subscribe("assistant/telemetry_correlation")
            client.subscribe("assistant/synchronization_awareness")
            client.subscribe("assistant/cyber_physical_reasoning")

            # Phase 9.8 subscriptions
            client.subscribe("assistant/agent_coordination")
            client.subscribe("assistant/telemetry_agent")
            client.subscribe("assistant/relay_agent")
            client.subscribe("assistant/workflow_agent")
            client.subscribe("assistant/security_agent")

            # Phase 9.9 subscriptions
            client.subscribe("assistant/swarm_coordination")
            client.subscribe("assistant/federated_memory")
            client.subscribe("assistant/distributed_consensus")
            client.subscribe("assistant/edge_mesh")
            client.subscribe("assistant/swarm_anomaly_fusion")



        else:
            logger.error(f"MQTT Connection failed with return code {rc}")

    def _on_message(self, client, userdata, msg):
        try:
            topic = msg.topic
            payload = json.loads(msg.payload.decode("utf-8"))
            
            # 1. Update historical databases and caches
            if "pypy/grid/bus" in topic:
                from gateway.database import db
                db.save_bus_telemetry(payload)
                self.translator.update_bus(payload)
                
                # Trigger legacy translation on last bus update to sync sweeps
                if payload.get("bus_id") == 38:
                    legacy_payload = self.translator.build_legacy_telemetry()
                    self.client.publish("grid/telemetry", json.dumps(legacy_payload))
                    
            elif "pypy/grid/line" in topic:
                from gateway.database import db
                db.save_line_telemetry(payload)
                self.translator.update_line(payload)
                
            elif "pypy/grid/gen" in topic:
                from gateway.database import db
                db.save_gen_telemetry(payload)
                self.translator.update_gen(payload)
            
            # Legacy caches
            elif topic == "pypy/grid/telemetry":
                store.update_telemetry(payload)
            elif topic == "grid/telemetry":
                if not store.latest_telemetry or len(store.latest_telemetry.get("state", {}).get("buses", {})) <= 9:
                    store.update_telemetry(payload)
            elif topic == "grid/events":
                store.add_event(payload)
            elif topic == "grid/alerts":
                store.add_alert(payload)
            elif topic == "grid/config":
                store.update_config(payload)
            elif topic == "grid/threat":
                store.update_threat(payload)
            elif topic == "grid/ai_prediction":
                store.update_ai_prediction(payload)
            elif topic == "grid/ai_forecast_multi_bus":
                store.update_ai_forecast_multi_bus(payload)
            elif topic == "grid/ai_threat_forecast":
                store.update_ai_threat_forecast(payload)
            elif topic == "grid/pinn_forecast":
                store.update_pinn_forecast(payload)
            elif topic == "grid/physics_validation":
                store.update_physics_validation(payload)
            elif topic == "grid/trust_scores":
                store.update_trust_scores(payload)
            elif topic == "grid/adaptive_filter":
                store.update_adaptive_filter(payload)
            elif topic == "grid/ai_orchestrator":
                store.update_ai_orchestrator(payload)
            elif topic == "grid/recommended_actions":
                store.update_recommended_actions(payload)
            elif topic == "grid/pre_rl":
                store.update_pre_rl(payload)
            elif topic == "grid/defense":
                store.update_defense(payload)
            elif topic == "prediction/threat_forecast":
                store.update_prediction_threat_forecast(payload)
            elif topic == "prediction/pre_attack_alert":
                store.update_prediction_pre_attack_alert(payload)
            elif topic == "prediction/future_risk":
                store.update_prediction_future_risk(payload)
            elif topic == "prediction/trust_forecast":
                store.update_prediction_trust_forecast(payload)
            elif topic == "prediction/escalation_probability":
                store.update_prediction_escalation_probability(payload)
            elif topic == "prediction/recommended_prevention":
                store.update_prediction_recommended_prevention(payload)
            elif topic == "grid/strategy":
                store.update_strategy(payload)
            elif topic == "grid/strategy_priority":
                store.update_strategy_priority(payload)
            elif topic == "grid/strategy_recommendation":
                store.update_strategy_recommendation(payload)
            elif topic == "grid/strategy_memory":
                store.update_strategy_memory(payload)
            elif topic == "grid/adversarial/campaign":
                store.update_adversarial_campaign(payload)
            elif topic == "grid/adversarial/resilience":
                store.update_adversarial_resilience(payload)
            elif topic == "grid/adversarial/weaknesses":
                store.update_adversarial_weaknesses(payload)
            elif topic == "grid/adversarial/recommendations":
                store.update_adversarial_recommendations(payload)
            elif topic == "grid/arena/match":
                store.update_arena_match(payload)
            elif topic == "grid/arena/rewards":
                store.update_arena_rewards(payload)
            elif topic == "grid/arena/evolution":
                store.update_arena_evolution(payload)
            elif topic == "grid/arena/recommendations":
                store.update_arena_recommendations(payload)
            elif topic == "grid/l6_recovery":
                store.update_l6_recovery(payload)
            elif topic == "grid/l6_adaptive_recovery":
                store.update_l6_adaptive_recovery(payload)
            elif topic == "grid/l6_containment":
                store.update_l6_containment(payload)
            elif topic == "grid/l6_degraded_mode":
                store.update_l6_degraded_mode(payload)
            elif topic == "grid/l6_survival":
                store.update_l6_survival(payload)
            elif topic == "grid/l6_islanding":
                store.update_l6_islanding(payload)
            elif topic == "grid/l6_blackstart":
                store.update_l6_blackstart(payload)
            elif topic == "grid/l6_balancing":
                store.update_l6_balancing(payload)
            elif topic == "grid/l6_predictive_stability":
                store.update_l6_predictive_stability(payload)
            elif topic == "grid/l6_survival_forecast":
                store.update_l6_survival_forecast(payload)
            elif topic == "grid/l6_proactive_actions":
                store.update_l6_proactive_actions(payload)
            elif topic == "grid/l6_self_preservation":
                store.update_l6_self_preservation(payload)
            elif topic == "grid/l6_agents":
                store.update_l6_agents(payload)
            elif topic == "grid/l6_agent_consensus":
                store.update_l6_agent_consensus(payload)
            elif topic == "grid/l6_agent_conflicts":
                store.update_l6_agent_conflicts(payload)
            elif topic == "grid/l6_distributed_state":
                store.update_l6_distributed_state(payload)
            elif topic == "grid/l6_agent_confidence":
                store.update_l6_agent_confidence(payload)
            elif topic == "hardware/relay":
                store.update_hardware_relay(payload)
            elif topic == "hardware/gpio":
                store.update_hardware_gpio(payload)
            elif topic == "hardware/sensor":
                store.update_hardware_sensor(payload)
            elif topic == "hardware/device_health":
                store.update_hardware_device_health(payload)
            elif topic == "hardware/command_log":
                store.update_hardware_command_log(payload)
            elif topic == "hardware/faults":
                store.update_hardware_faults(payload)
            elif topic == "hardware/relay_faults":
                store.update_hardware_relay_faults(payload)
            elif topic == "hardware/anomalies":
                store.update_hardware_anomalies(payload)
            elif topic == "hardware/virtual_devices":
                store.update_hardware_virtual_devices(payload)
            elif topic == "hardware/spoofed_telemetry":
                store.update_hardware_spoofed_telemetry(payload)
            elif topic == "hardware/fault_propagation":
                store.update_hardware_fault_propagation(payload)
            elif topic == "hardware/usb_events":
                store.update_hardware_usb_events(payload)
            elif topic == "hardware/rogue_devices":
                store.update_hardware_rogue_devices(payload)
            elif topic == "hardware/badusb":
                store.update_hardware_badusb(payload)
            elif topic == "hardware/intrusion_alerts":
                store.update_hardware_intrusion_alerts(payload)
            elif topic == "hardware/device_trust":
                store.update_hardware_device_trust(payload)
            elif topic == "hardware/attack_state":
                store.update_hardware_attack_state(payload)
            elif topic == "hardware/attack_propagation":
                store.update_hardware_attack_propagation(payload)
            elif topic == "hardware/orchestration":
                store.update_hardware_orchestration(payload)
            elif topic == "hardware/edge_devices":
                store.update_hardware_edge_devices(payload)
            elif topic == "hardware/relay_execution":
                store.update_hardware_relay_execution(payload)
            elif topic == "hardware/distributed_bus":
                store.update_hardware_distributed_bus(payload)
            elif topic == "hardware/synchronization":
                store.update_hardware_synchronization(payload)
            elif topic == "hardware/orchestration_conflicts":
                store.update_hardware_orchestration_conflicts(payload)
            elif topic == "hardware/execution_gateway":
                store.update_hardware_execution_gateway(payload)
            elif topic == "hardware/reliability":
                store.update_hardware_reliability(payload)
            elif topic == "hardware/safety_guard":
                store.update_hardware_safety_guard(payload)
            elif topic == "hardware/deployment_profiles":
                store.update_hardware_deployment_profiles(payload)
            elif topic == "hardware/telemetry_validation":
                store.update_hardware_telemetry_validation(payload)
            elif topic == "hardware/resilience":
                store.update_hardware_resilience(payload)
            elif topic == "hardware/disaster_recovery":
                store.update_hardware_disaster_recovery(payload)
            elif topic == "hardware/redundancy":
                store.update_hardware_redundancy(payload)
            elif topic == "hardware/deployment_hardening":
                store.update_hardware_deployment_hardening(payload)
            elif topic == "hardware/large_scale_sync":
                store.update_hardware_large_scale_sync(payload)
            elif topic == "assistant/state":
                store.update_assistant_state(payload)
            elif topic == "assistant/intent":
                store.update_assistant_intent(payload)
            elif topic == "assistant/emotion":
                store.update_assistant_emotion(payload)
            elif topic == "assistant/actions":
                store.update_assistant_actions(payload)
            elif topic == "assistant/context":
                store.update_assistant_context(payload)
            elif topic == "assistant/memory":
                store.update_assistant_memory(payload)
            elif topic == "assistant/response":
                store.update_assistant_response(payload)
            elif topic == "assistant/runtime":
                store.update_assistant_runtime(payload)
            elif topic == "assistant/semantic_intent":
                store.update_assistant_semantic_intent(payload)
            elif topic == "assistant/contextual_memory":
                store.update_assistant_contextual_memory(payload)
            elif topic == "assistant/reasoning":
                store.update_assistant_reasoning(payload)
            elif topic == "assistant/automation_hooks":
                store.update_assistant_automation_hooks(payload)
            elif topic == "assistant/semantic_response":
                store.update_assistant_semantic_response(payload)
            elif topic == "assistant/voice_state":
                store.update_assistant_voice_state(payload)
            elif topic == "assistant/wake_word":
                store.update_assistant_wake_word(payload)
            elif topic == "assistant/proactive":
                store.update_assistant_proactive(payload)
            elif topic == "assistant/voice_memory":
                store.update_assistant_voice_memory(payload)
            elif topic == "assistant/presence":
                store.update_assistant_presence(payload)
            elif topic == "assistant/workflows":
                store.update_assistant_workflows(payload)
            elif topic == "assistant/reminders":
                store.update_assistant_reminders(payload)
            elif topic == "assistant/conditions":
                store.update_assistant_conditions(payload)
            elif topic == "assistant/n8n_bridge":
                store.update_assistant_n8n_bridge(payload)
            elif topic == "assistant/routines":
                store.update_assistant_routines(payload)
            elif topic == "assistant/conversation_planning":
                store.update_assistant_conversation_planning(payload)
            elif topic == "assistant/task_chains":
                store.update_assistant_task_chains(payload)
            elif topic == "assistant/live_stream":
                store.update_assistant_live_stream(payload)
            elif topic == "assistant/dialogue":
                store.update_assistant_dialogue(payload)
            elif topic == "assistant/orchestration_planner":
                store.update_assistant_orchestration_planner(payload)
                
            # Phase 9.6 updaters
            elif topic == "assistant/predictive_coordination":
                store.update_assistant_predictive_coordination(payload)
            elif topic == "assistant/persistent_memory":
                store.update_assistant_persistent_memory(payload)
            elif topic == "assistant/pattern_awareness":
                store.update_assistant_pattern_awareness(payload)
            elif topic == "assistant/workflow_optimizer":
                store.update_assistant_workflow_optimizer(payload)
            elif topic == "assistant/cross_system_coordination":
                store.update_assistant_cross_system_coordination(payload)

            # Phase 9.7 updaters
            elif topic == "assistant/edge_awareness":
                store.update_assistant_edge_awareness(payload)
            elif topic == "assistant/relay_health":
                store.update_assistant_relay_health(payload)
            elif topic == "assistant/telemetry_correlation":
                store.update_assistant_telemetry_correlation(payload)
            elif topic == "assistant/synchronization_awareness":
                store.update_assistant_synchronization_awareness(payload)
            elif topic == "assistant/cyber_physical_reasoning":
                store.update_assistant_cyber_physical_reasoning(payload)

            # Phase 9.8 updaters
            elif topic == "assistant/agent_coordination":
                store.update_assistant_agent_coordination(payload)
            elif topic == "assistant/telemetry_agent":
                store.update_assistant_telemetry_agent(payload)
            elif topic == "assistant/relay_agent":
                store.update_assistant_relay_agent(payload)
            elif topic == "assistant/workflow_agent":
                store.update_assistant_workflow_agent(payload)
            elif topic == "assistant/security_agent":
                store.update_assistant_security_agent(payload)

            # Phase 9.9 handlers
            elif topic == "assistant/swarm_coordination":
                store.update_assistant_swarm_coordination(payload)
            elif topic == "assistant/federated_memory":
                store.update_assistant_federated_memory(payload)
            elif topic == "assistant/distributed_consensus":
                store.update_assistant_distributed_consensus(payload)
            elif topic == "assistant/edge_mesh":
                store.update_assistant_edge_mesh(payload)
            elif topic == "assistant/swarm_anomaly_fusion":
                store.update_assistant_swarm_anomaly_fusion(payload)




                
            # 2. Package for WebSockets
            ws_payload = {
                "topic": topic,
                "payload": payload
            }
            
            # 3. Schedule broadcast on the main asyncio event loop
            if self.loop and self.loop.is_running():
                asyncio.run_coroutine_threadsafe(
                    ws_manager.broadcast(ws_payload), 
                    self.loop
                )
        except json.JSONDecodeError:
            logger.warning(f"MQTT received malformed non-JSON payload on {msg.topic}")
        except Exception as e:
            logger.error(f"Error handling MQTT message on {msg.topic}: {e}")

mqtt_manager = MQTTManager()
