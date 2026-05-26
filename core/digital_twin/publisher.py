import os
import json
import time
import logging
from typing import Dict, Any, Callable
import paho.mqtt.client as mqtt

logger = logging.getLogger("digital_twin.publisher")

class TelemetryPublisher:
    def __init__(self, 
                 broker: str = "localhost", 
                 port: int = 1883,
                 on_control_cmd: Callable[[str, str], None] = None,
                 on_attack_cmd: Callable[[Dict[str, Any]], None] = None,
                 on_config_cmd: Callable[[Dict[str, Any]], None] = None):
        
        self.broker = broker
        self.port = port
        self.client = mqtt.Client(client_id="digital_twin_publisher_node")
        
        # Command hooks
        self.on_control_cmd = on_control_cmd
        self.on_attack_cmd = on_attack_cmd
        self.on_config_cmd = on_config_cmd
        
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message

    def start(self):
        try:
            self.client.connect(self.broker, self.port, keepalive=60)
            self.client.loop_start()
            logger.info(f"Publisher MQTT connected to {self.broker}:{self.port}")
        except Exception as e:
            logger.error(f"Publisher MQTT connection failed: {e}")
            raise e

    def stop(self):
        self.client.loop_stop()
        self.client.disconnect()
        logger.info("Publisher MQTT stopped.")

    def publish_telemetry(self, telemetry: Dict[str, Any]):
        try:
            self.client.publish("grid/telemetry", json.dumps(telemetry))
        except Exception as e:
            logger.error(f"Failed to publish telemetry to MQTT: {e}")

    def publish_event(self, source: str, event_desc: str, severity: str = "INFO"):
        try:
            event_payload = {
                "timestamp": int(time.time() * 1000),
                "source": source,
                "event": event_desc,
                "severity": severity
            }
            self.client.publish("grid/events", json.dumps(event_payload))
            logger.info(f"Broadcasted event log [{severity}]: {event_desc}")
        except Exception as e:
            logger.error(f"Failed to publish event log: {e}")

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info("Telemetry Publisher connected successfully!")
            client.subscribe("grid/control")
            client.subscribe("grid/attack")
            client.subscribe("grid/config")
        else:
            logger.error(f"MQTT connection failed with code {rc}")

    def _on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
            topic = msg.topic
            
            if topic == "grid/control":
                cmd = payload.get("command")
                target = payload.get("target")
                if cmd == "RESET_ALARMS":
                    if self.on_control_cmd:
                        self.on_control_cmd("SYSTEM", "RESET_ALARMS", payload)
                elif cmd and target and self.on_control_cmd:
                    self.on_control_cmd(target, cmd, payload)
                    
            elif topic == "grid/attack":
                if self.on_attack_cmd:
                    self.on_attack_cmd(payload)
                    
            elif topic == "grid/config":
                if self.on_config_cmd:
                    self.on_config_cmd(payload)
                    
        except json.JSONDecodeError:
            logger.warning(f"Malformed JSON received on MQTT {msg.topic}")
        except Exception as e:
            logger.error(f"Error handling message on {msg.topic}: {e}")
