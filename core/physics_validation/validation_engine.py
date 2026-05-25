import os
import time
import json
import logging
import numpy as np
import paho.mqtt.client as mqtt

from kcl_validator import KCLValidator
from kvl_validator import KVLValidator
from physics_filter import PhysicsFilter
from trust_engine import TrustEngine
from adaptive_filter import AdaptiveTelemetryFilter

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("physics_validation.engine")

MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))

class PhysicsValidationEngine:
    def __init__(self):
        self.kcl_validator = KCLValidator()
        self.kvl_validator = KVLValidator()
        self.physics_filter = PhysicsFilter(self.kcl_validator, self.kvl_validator)
        
        self.trust_engine = TrustEngine()
        self.adaptive_filter = AdaptiveTelemetryFilter()
        
        # State caches
        self.latest_ai_threat_prob = 0.0
        
    def process_telemetry(self, telemetry, client):
        try:
            # 1. Run raw physics filter checks
            raw_report = self.physics_filter.validate(telemetry)
            
            # 2. Update trust scoring state statefully
            ai_prob = self.latest_ai_threat_prob
            self.trust_engine.update(telemetry, raw_report, ai_prob)
            trust_report = self.trust_engine.get_scores()
            trust_scores = self.trust_engine.trust_scores
            
            # 3. Apply adaptive telemetry filter
            filtered_telemetry, filter_actions = self.adaptive_filter.filter(telemetry, trust_scores)
            
            # 4. Check for physical deviations (voltage drops) in raw telemetry
            buses_data = telemetry["state"]["buses"]
            has_voltage_deviation = False
            for bname, bdata in buses_data.items():
                if bname in ["Bus_1", "Bus_3", "Bus_5", "Bus_7", "Bus_9"]:
                    v = float(bdata.get("voltage_pu", 1.0))
                    if v < 0.94 or v > 1.07:
                        has_voltage_deviation = True
                        break
                        
            # 5. Threat Fusion Logic to classify grid state
            impossible_state = raw_report["impossible_state"]
            phys_score = raw_report["physics_anomaly_score"]
            
            if impossible_state:
                physics_state = "IMPOSSIBLE_STATE"
            elif has_voltage_deviation:
                if ai_prob >= 0.50 or phys_score >= 40:
                    physics_state = "CYBER_ATTACK_INSTABILITY"
                else:
                    physics_state = "PHYSICAL_INSTABILITY"
            else:
                if ai_prob >= 0.30 or phys_score >= 30:
                    physics_state = "SUSPICIOUS"
                else:
                    physics_state = "NORMAL"
                    
            # 6. Calculate Fused Grid Confidence metrics
            avg_trust = float(np.mean(list(trust_scores.values())))
            global_grid_confidence = avg_trust * (1.0 - phys_score / 100.0) * (1.0 - ai_prob)
            global_grid_confidence_pct = round(global_grid_confidence * 100, 2)
            
            # Trusted state flag and degraded observability indicators
            trusted_state = (global_grid_confidence >= 0.70) and (not impossible_state) and (ai_prob < 0.50)
            degraded_observability = any(t < 0.70 for t in trust_scores.values())
            
            # 7. Compile outputs and publish
            timestamp_ms = int(time.time() * 1000)
            
            # A. Publish grid/physics_validation (for backward compatibility)
            payload_validation = {
                "timestamp": timestamp_ms,
                "physics_anomaly_score": phys_score,
                "kcl_error": raw_report["kcl_error"],
                "kvl_error": raw_report["kvl_error"],
                "physics_state": physics_state,
                "impossible_state": impossible_state,
                "impossible_violations": raw_report["impossible_violations"],
                "ai_threat_prob": ai_prob,
                "global_grid_confidence": global_grid_confidence_pct,
                "trusted_state": trusted_state,
                "degraded_observability": degraded_observability
            }
            client.publish("grid/physics_validation", json.dumps(payload_validation))
            
            # B. Publish grid/trust_scores
            trust_payload = {
                "timestamp": timestamp_ms,
                "bus_trust": trust_report["bus_trust"],
                "line_trust": trust_report["line_trust"],
                "details": trust_report["details"]
            }
            client.publish("grid/trust_scores", json.dumps(trust_payload))
            
            # C. Publish grid/adaptive_filter
            filter_payload = {
                "timestamp": timestamp_ms,
                "filter_actions": filter_actions,
                "global_grid_confidence": global_grid_confidence_pct,
                "trusted_state": trusted_state,
                "degraded_observability": degraded_observability,
                "filtered_telemetry": filtered_telemetry
            }
            client.publish("grid/adaptive_filter", json.dumps(filter_payload))
            
            logger.info(
                f"Published Validation | State: {physics_state} | Confidence: {global_grid_confidence_pct:.1f}% | "
                f"Trust Dev: {degraded_observability} | KCL: {raw_report['kcl_error']:.1f} MW"
            )
            
        except Exception as e:
            logger.error(f"Failed to process telemetry: {e}")

engine = PhysicsValidationEngine()

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info("Physics Validation Engine connected to MQTT!")
        client.subscribe("grid/telemetry")
        client.subscribe("grid/ai_threat_forecast")
        client.subscribe("grid/control")
    else:
        logger.error(f"MQTT Connection failed: rc {rc}")

def on_message(client, userdata, msg):
    try:
        topic = msg.topic
        payload = json.loads(msg.payload.decode("utf-8"))
        
        if topic == "grid/ai_threat_forecast":
            engine.latest_ai_threat_prob = float(payload.get("cyber_instability_probability", 0.0))
            
        elif topic == "grid/control":
            cmd = payload.get("command")
            if cmd == "RESET_ALARMS":
                engine.latest_ai_threat_prob = 0.0
                engine.trust_engine = TrustEngine()
                engine.adaptive_filter = AdaptiveTelemetryFilter()
                logger.info("Physics Validation and Trust engine states reset.")
                
        elif topic == "grid/telemetry":
            engine.process_telemetry(payload, client)
            
    except Exception as e:
        logger.error(f"Error handling message on {msg.topic}: {e}")

if __name__ == "__main__":
    client = mqtt.Client(client_id="ai_physics_validation_engine")
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
        client.loop_forever()
    except KeyboardInterrupt:
        logger.info("Stopping Physics Validation Engine...")
    except Exception as e:
        logger.error(f"MQTT Loop Error: {e}")
        os._exit(1)
