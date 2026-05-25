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
