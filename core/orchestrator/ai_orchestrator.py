import os
import time
import json
import logging
import sys
import paho.mqtt.client as mqtt

# Ensure current directory is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from decision_engine import OrchestrationDecisionEngine
from action_recommender import ActionRecommender

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("orchestrator.main")

MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))

class AIOrchestrator:
    def __init__(self):
        self.decision_engine = OrchestrationDecisionEngine()
        self.action_recommender = ActionRecommender()
        
        # Unified grid state cache
        self.state_cache = {
            "telemetry": None,
            "ai_forecast": None,
            "multi_bus_forecast": None,
            "threat_aware_forecast": None,
            "physics_validation": None,
            "trust_scores": None,
            "threat": None,
            "flisr_state": "NORMAL",
            "flisr_auto": True
        }

    def update_state(self, topic, payload):
        """
        Updates the cache based on received topic.
        """
        if topic == "grid/telemetry":
            self.state_cache["telemetry"] = payload
        elif topic == "grid/ai_prediction":
            self.state_cache["ai_forecast"] = payload
        elif topic == "grid/ai_forecast_multi_bus":
            self.state_cache["multi_bus_forecast"] = payload
        elif topic == "grid/ai_threat_forecast":
            self.state_cache["threat_aware_forecast"] = payload
        elif topic == "grid/physics_validation":
            self.state_cache["physics_validation"] = payload
        elif topic == "grid/trust_scores":
            self.state_cache["trust_scores"] = payload
        elif topic == "grid/threat":
            self.state_cache["threat"] = payload
        elif topic == "grid/config":
            if "flisr_state" in payload:
                self.state_cache["flisr_state"] = payload["flisr_state"]
            if "flisr_auto" in payload:
                self.state_cache["flisr_auto"] = payload["flisr_auto"]

    def run_cycle(self, client):
        """
        Runs a decision-making and action recommendations cycle.
        """
        # Execute only if telemetry is present
        if not self.state_cache["telemetry"]:
            return
            
        try:
            # 1. Run Decision Engine
            report = self.decision_engine.evaluate(self.state_cache)
            
            # 2. Run Action Recommender
            actions = self.action_recommender.recommend(self.state_cache, report)
            
            # 3. Publish AI Orchestrator summary
            timestamp_ms = int(time.time() * 1000)
            orchestrator_payload = {
                "timestamp": timestamp_ms,
                "global_state": report["global_state"],
                "global_risk_level": report["global_risk_level"],
                "stability_score": report["stability_score"],
                "restoration_confidence": report["restoration_confidence"],
                "active_subsystems_reasoning": report["active_subsystems_reasoning"]
            }
            client.publish("grid/ai_orchestrator", json.dumps(orchestrator_payload))
            
            # 4. Publish Recommended Actions
            recommended_actions_payload = {
                "timestamp": timestamp_ms,
                "recommendations": actions
            }
            client.publish("grid/recommended_actions", json.dumps(recommended_actions_payload))
            
            logger.info(
                f"AI Orchestration cycle | Global State: {report['global_state']} | "
                f"Stability: {report['stability_score']}% | Actions Recommended: {len(actions)}"
            )
            
        except Exception as e:
            logger.error(f"Failed to run AI Orchestrator cycle: {e}")

    def reset(self):
        """
        Resets cache and engines.
        """
        self.state_cache = {
            "telemetry": None,
            "ai_forecast": None,
            "multi_bus_forecast": None,
            "threat_aware_forecast": None,
            "physics_validation": None,
            "trust_scores": None,
            "threat": None,
            "flisr_state": "NORMAL",
            "flisr_auto": True
        }
        self.decision_engine = OrchestrationDecisionEngine()
        self.action_recommender = ActionRecommender()
        logger.info("AI Orchestrator cache and engines reset.")

orchestrator = AIOrchestrator()

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info("AI Orchestrator connected to MQTT!")
        client.subscribe("grid/telemetry")
        client.subscribe("grid/ai_prediction")
        client.subscribe("grid/ai_forecast_multi_bus")
        client.subscribe("grid/ai_threat_forecast")
        client.subscribe("grid/physics_validation")
        client.subscribe("grid/trust_scores")
        client.subscribe("grid/threat")
        client.subscribe("grid/config")
        client.subscribe("grid/control")
    else:
        logger.error(f"MQTT Connection failed: rc {rc}")

def on_message(client, userdata, msg):
    try:
        topic = msg.topic
        payload = json.loads(msg.payload.decode("utf-8"))
        
        if topic == "grid/control":
            cmd = payload.get("command")
            if cmd == "RESET_ALARMS":
                orchestrator.reset()
        else:
            orchestrator.update_state(topic, payload)
            
            # Trigger cycle execution upon receiving telemetry tick
            if topic == "grid/telemetry":
                orchestrator.run_cycle(client)
                
    except Exception as e:
        logger.error(f"Error handling message on {msg.topic}: {e}")

if __name__ == "__main__":
    client = mqtt.Client(client_id="ai_orchestration_service")
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
        client.loop_forever()
    except KeyboardInterrupt:
        logger.info("Stopping AI Orchestrator...")
    except Exception as e:
        logger.error(f"MQTT Loop Error: {e}")
        sys.exit(1)
