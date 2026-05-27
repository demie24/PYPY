import os
import json
import logging
import asyncio
from typing import Any
import paho.mqtt.client as mqtt
from gateway.store import store
from gateway.websocket_manager import ws_manager

logger = logging.getLogger("gateway.mqtt_manager")

class MQTTManager:
    def __init__(self):
        self.broker = os.getenv("MQTT_BROKER", "localhost")
        self.port = int(os.getenv("MQTT_PORT", 1883))
        self.client = mqtt.Client(client_id="fastapi_gateway_service")
        
        # Callbacks registration
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.loop: Optional[asyncio.AbstractEventLoop] = None

    def start(self, loop: asyncio.AbstractEventLoop):
        self.loop = loop
        try:
            self.client.connect(self.broker, self.port, keepalive=60)
            self.client.loop_start()
            logger.info(f"MQTT client started. Connecting to {self.broker}:{self.port}")
        except Exception as e:
            logger.error(f"MQTT client failed to start: {e}")

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
            # Subscriptions
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
        else:
            logger.error(f"MQTT Connection failed with return code {rc}")

    def _on_message(self, client, userdata, msg):
        try:
            topic = msg.topic
            payload = json.loads(msg.payload.decode("utf-8"))
            
            # 1. Update historical caches
            if topic == "grid/telemetry":
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
