import os
import sys
import json
import time
import logging
import paho.mqtt.client as mqtt

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("/app/logs/notifications.log" if os.path.exists("/app/logs") else "notifications.log")
    ]
)
logger = logging.getLogger("notification_service")

class NotificationOrchestrator:
    def __init__(self):
        self.broker = os.getenv("MQTT_BROKER", "localhost")
        self.port = int(os.getenv("MQTT_PORT", 1883))
        self.client = mqtt.Client(client_id="mobile_push_notification_service")
        
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        
        # Alert prioritization and tracking state
        self.last_sent_alerts = {}  # key -> timestamp
        self.cooldown_period = 15.0  # seconds to suppress repeat notifications
        self.registered_tokens = set(["mock-operator-token-expo-ios-10294"])
        self.ack_history = {}       # alert_id -> acknowledged boolean

    def start(self):
        logger.info(f"Connecting to MQTT Broker at {self.broker}:{self.port}...")
        try:
            self.client.connect(self.broker, self.port, keepalive=60)
            self.client.loop_forever()
        except KeyboardInterrupt:
            logger.info("Notification service stopped by user.")
        except Exception as e:
            logger.critical(f"MQTT connection failed: {e}")
            sys.exit(1)

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info("Connected to MQTT Broker!")
            # Subscriptions
            client.subscribe("grid/alerts")
            client.subscribe("grid/threat")
            client.subscribe("grid/telemetry")
            client.subscribe("mobile/operator/state")
            client.subscribe("mobile/alerts/ack")
        else:
            logger.error(f"MQTT Connection failed with return code {rc}")

    def _on_message(self, client, userdata, msg):
        try:
            topic = msg.topic
            payload = json.loads(msg.payload.decode("utf-8"))
            
            if topic == "grid/alerts":
                self.process_grid_alert(payload)
            elif topic == "grid/threat":
                self.process_threat_score(payload)
            elif topic == "mobile/alerts/ack":
                self.process_operator_ack(payload)
            elif topic == "mobile/operator/state":
                logger.info(f"Operator State Update: {payload}")
                
        except json.JSONDecodeError:
            logger.warning(f"Malformed JSON payload on topic {msg.topic}")
        except Exception as e:
            logger.error(f"Error handling message on {msg.topic}: {e}")

    def process_grid_alert(self, alert_payload: dict):
        alert_id = alert_payload.get("alert_id") or alert_payload.get("id") or str(int(time.time() * 1000))
        event_text = alert_payload.get("event") or alert_payload.get("msg") or "Anomaly detected"
        source = alert_payload.get("source") or "SYSTEM"
        severity = alert_payload.get("severity") or "WARNING"
        timestamp = alert_payload.get("timestamp") or int(time.time() * 1000)

        # 1. Cooldown suppression logic to prevent notification storm
        suppression_key = f"{source}:{severity}:{event_text[:20]}"
        now = time.time()
        if suppression_key in self.last_sent_alerts:
            elapsed = now - self.last_sent_alerts[suppression_key]
            if elapsed < self.cooldown_period:
                logger.info(f"Alert suppressed (cooldown): {event_text} (elapsed: {elapsed:.1f}s)")
                return

        self.last_sent_alerts[suppression_key] = now
        self.ack_history[alert_id] = False

        # 2. Dispatch simulated push notification payload
        self.dispatch_simulated_push(alert_id, source, event_text, severity, timestamp)

    def process_threat_score(self, threat_payload: dict):
        threat_score = threat_payload.get("threat_score", 0.0)
        attack_active = threat_payload.get("attack_active", False)
        
        # Prioritized alert on high threat score transitions
        if threat_score > 75.0 or attack_active:
            suppression_key = "threat:critical_override"
            now = time.time()
            if suppression_key not in self.last_sent_alerts or (now - self.last_sent_alerts[suppression_key]) > 30.0:
                self.last_sent_alerts[suppression_key] = now
                self.dispatch_simulated_push(
                    alert_id=f"threat-crit-{int(now)}",
                    source="THREAT_ENGINE",
                    event_text=f"CRITICAL OVERRIDE ACTIVE: Global Threat Index is {threat_score:.1f}%!",
                    severity="CRITICAL",
                    timestamp=int(now * 1000)
                )

    def process_operator_ack(self, ack_payload: dict):
        alert_id = ack_payload.get("alert_id")
        operator_id = ack_payload.get("operator_id", "Field_Operator_Mobile")
        
        if alert_id:
            self.ack_history[alert_id] = True
            logger.info(f"Operator '{operator_id}' acknowledged alert ID: {alert_id}")
            
            # Sync acknowledgment back to both desktop and physical nodes
            sync_payload = {
                "timestamp": int(time.time() * 1000),
                "source": "MOBILE_OPS",
                "event": f"Alert {alert_id} acknowledged by operator via mobile companion app.",
                "severity": "INFO",
                "alert_id": alert_id,
                "acknowledged": True
            }
            self.client.publish("grid/events", json.dumps(sync_payload))

    def dispatch_simulated_push(self, alert_id: str, source: str, text: str, severity: str, timestamp: int):
        push_payload = {
            "to": list(self.registered_tokens),
            "notification": {
                "title": f"[{severity}] S-GRID WARNING",
                "body": text,
                "sound": "default" if severity != "CRITICAL" else "critical_siren.wav"
            },
            "data": {
                "alert_id": alert_id,
                "source": source,
                "severity": severity,
                "timestamp": timestamp,
                "priority": "high" if severity == "CRITICAL" else "normal"
            }
        }
        
        # Print fcm push notification log
        logger.info(f"DISPATCHED MOCK PUSH NOTIFICATION (FCM Payload):\n{json.dumps(push_payload, indent=2)}")

if __name__ == "__main__":
    orchestrator = NotificationOrchestrator()
    orchestrator.start()
