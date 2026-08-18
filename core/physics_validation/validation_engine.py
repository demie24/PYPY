import os
import time
import json
import logging
import numpy as np
import paho.mqtt.client as mqtt
from pathlib import Path

from core.ai_runtime.readiness import ModelReadiness
from core.digital_twin.grid_topology import GridTopology
from core.mqtt_compat import create_client
from core.physics_validation.kcl_validator import KCLValidator
from core.physics_validation.kvl_validator import KVLValidator
from core.physics_validation.physics_filter import PhysicsFilter
from core.physics_validation.trust_engine import TrustEngine
from core.physics_validation.adaptive_filter import AdaptiveTelemetryFilter

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("physics_validation.engine")

MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))

class PhysicsValidationEngine:
    def __init__(self):
        self.topology = GridTopology(use_legacy_9bus=False)
        self.kcl_validator = KCLValidator(self.topology)
        self.kvl_validator = KVLValidator(self.topology)
        self.physics_filter = PhysicsFilter(self.kcl_validator, self.kvl_validator)
        
        self.trust_engine = TrustEngine(topology=self.topology)
        self.adaptive_filter = AdaptiveTelemetryFilter(topology=self.topology)
        self.readiness = ModelReadiness("trust", model_loaded=True, checkpoint="physics-rules-ieee39")
        
        # State caches
        self.latest_ai_threat_prob = 0.0
        
        # Validation window buffers (persistence threshold = 3 sweeps)
        self.anomaly_buffer = []
        self.impossible_buffer = []
        
    def process_telemetry(self, telemetry, client):
        self.readiness.record_telemetry()
        try:
            solver_status = telemetry.get("solver_status") or {}
            if solver_status and not solver_status.get("converged", False):
                raise ValueError(f"power_flow_non_convergence:{solver_status.get('mode', 'failed')}")
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
            for bdata in buses_data.values():
                v = float(bdata.get("voltage_pu", 1.0))
                if not np.isfinite(v) or v < 0.94 or v > 1.07:
                    has_voltage_deviation = True
                    break
                        
            # 5. Threat Fusion Logic to classify grid state
            impossible_state = raw_report["impossible_state"]
            phys_score = raw_report["physics_anomaly_score"]
            
            # Maintain persistence buffer for false-positive reduction (validation window = 3 samples)
            self.anomaly_buffer.append(phys_score >= 30)
            self.impossible_buffer.append(impossible_state)
            if len(self.anomaly_buffer) > 3:
                self.anomaly_buffer.pop(0)
            if len(self.impossible_buffer) > 3:
                self.impossible_buffer.pop(0)
                
            persistent_anomaly = all(self.anomaly_buffer) if len(self.anomaly_buffer) >= 3 else (phys_score >= 30)
            persistent_impossible = all(self.impossible_buffer) if len(self.impossible_buffer) >= 3 else impossible_state
            
            if persistent_impossible:
                physics_state = "IMPOSSIBLE_STATE"
            elif has_voltage_deviation:
                if ai_prob >= 0.50 or persistent_anomaly:
                    physics_state = "CYBER_ATTACK_INSTABILITY"
                else:
                    physics_state = "PHYSICAL_INSTABILITY"
            else:
                if ai_prob >= 0.30 or persistent_anomaly:
                    physics_state = "SUSPICIOUS"
                else:
                    physics_state = "NORMAL"
                    
            # 6. Calculate Fused Grid Confidence metrics
            avg_trust = float(np.mean(list(trust_scores.values())))
            global_grid_confidence = avg_trust * (1.0 - phys_score / 100.0) * (1.0 - ai_prob)
            global_grid_confidence_pct = round(global_grid_confidence * 100, 2)
            
            # Trusted state flag and degraded observability indicators (downgraded threshold to 60.0)
            trusted_state = (global_grid_confidence >= 0.65) and (not impossible_state) and (ai_prob < 0.50)
            degraded_observability = any(t < 0.60 for t in trust_scores.values())
            
            # 7. Compile outputs and publish
            timestamp_ms = int(time.time() * 1000)
            self.readiness.record_inference()
            status = self.readiness.snapshot(stale_after=15.0)
            Path("/tmp/pypy_trust_heartbeat.json").write_text(json.dumps(status), encoding="utf-8")
            client.publish("grid/ai/status/trust", json.dumps(status), retain=True)
            
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
                "final_operational_confidence_index": global_grid_confidence_pct,
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
            self.readiness.record_error(e)
            status = self.readiness.snapshot(stale_after=15.0)
            Path("/tmp/pypy_trust_heartbeat.json").write_text(json.dumps(status), encoding="utf-8")
            client.publish("grid/ai/status/trust", json.dumps(status), retain=True)
            logger.error(f"Failed to process telemetry: {e}")

engine = PhysicsValidationEngine()

def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        logger.info("Physics Validation Engine connected to MQTT!")
        client.subscribe(os.getenv("TELEMETRY_TOPIC", "pypy/grid/telemetry"))
        client.subscribe("grid/ai/fusion")
        client.subscribe("grid/control")
    else:
        logger.error(f"MQTT Connection failed: rc {rc}")

def on_message(client, userdata, msg):
    try:
        topic = msg.topic
        payload = json.loads(msg.payload.decode("utf-8"))
        
        if topic in ("grid/ai_threat_forecast", "grid/ai/fusion"):
            engine.latest_ai_threat_prob = float(payload.get("fused_risk", payload.get("cyber_instability_probability", 0.0)))
            
        elif topic == "grid/control":
            cmd = payload.get("command")
            if cmd == "RESET_ALARMS":
                engine.latest_ai_threat_prob = 0.0
                engine.trust_engine = TrustEngine(topology=engine.topology)
                engine.adaptive_filter = AdaptiveTelemetryFilter(topology=engine.topology)
                engine.anomaly_buffer.clear()
                engine.impossible_buffer.clear()
                logger.info("Physics Validation, Trust engine, and validation buffers reset.")
            elif cmd == "REJECT_TELEMETRY":
                tgt = payload.get("target")
                if tgt:
                    engine.trust_engine.reject_node(tgt)
                    logger.info(f"Operator rejected telemetry for {tgt}. Trust score forced to 0.0.")
                
        elif topic in (os.getenv("TELEMETRY_TOPIC", "pypy/grid/telemetry"), "grid/telemetry"):
            engine.process_telemetry(payload, client)
            
    except Exception as e:
        logger.error(f"Error handling message on {msg.topic}: {e}")

if __name__ == "__main__":
    client = create_client("ai_physics_validation_engine")
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
