import os
import sys
import time
import json
import logging
from collections import deque
import paho.mqtt.client as mqtt

# Resolve local module pathing
strategy_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(strategy_dir, "..")))

from strategy.strategy_memory import StrategyMemory
from strategy.priority_engine import PriorityEngine
from strategy.resource_allocator import ResourceAllocator
from strategy.impact_estimator import ImpactEstimator
from strategy.action_simulator import ActionSimulator

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("strategy.strategic_coordinator")

MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))

class StrategicCoordinator:
    def __init__(self):
        # Component Instances
        self.memory = StrategyMemory()
        self.priority_engine = PriorityEngine()
        self.resource_allocator = ResourceAllocator()
        self.impact_estimator = ImpactEstimator()
        self.action_simulator = ActionSimulator()

        # Stateful Caches for incoming data
        self.telemetry_history = deque(maxlen=15)
        self.alert_history = deque(maxlen=30)
        self.event_history = deque(maxlen=50)

        self.latest_telemetry = None
        self.latest_threat = None
        self.latest_defense = None
        self.latest_self_healing = None
        
        # Layer 11A forecasts
        self.latest_prediction_threat_forecast = None
        self.latest_prediction_pre_attack_alert = None
        self.latest_prediction_future_risk = None
        self.latest_prediction_trust_forecast = None

        # Throttling & Ordering
        self.last_cycle_time = 0.0
        self.last_telemetry_timestamp = 0
        self.min_cycle_interval = 0.5

    def handle_telemetry(self, payload: dict, client: mqtt.Client):
        """
        Ingest telemetry and coordinate strategic analysis loop.
        """
        now = time.time()
        if now - self.last_cycle_time < self.min_cycle_interval:
            return

        pkt_ts = payload.get("timestamp", 0)
        if pkt_ts <= self.last_telemetry_timestamp:
            return

        self.last_telemetry_timestamp = pkt_ts
        self.last_cycle_time = now
        self.latest_telemetry = payload
        self.telemetry_history.append(payload)

        self.run_coordination_cycle(client)

    def run_coordination_cycle(self, client: mqtt.Client):
        """
        Execute core Layer 11B Strategic Planning.
        """
        if not self.latest_telemetry:
            return

        # 1. Identify Priorities
        priority_order = self.priority_engine.evaluate_priorities(
            self.latest_telemetry,
            self.latest_threat if self.latest_threat else {},
            list(self.alert_history),
            self.latest_prediction_future_risk
        )

        # 2. Allocate resources based on priority
        resource_alloc = self.resource_allocator.allocate_resources(
            priority_order,
            self.latest_prediction_future_risk if self.latest_prediction_future_risk else {}
        )

        # 3. Simulate candidate actions
        candidates = self.action_simulator.simulate_candidates(
            self.latest_telemetry,
            self.latest_threat if self.latest_threat else {},
            list(self.alert_history),
            self.latest_prediction_future_risk
        )

        # 4. Estimate impacts pre-execution with memory metrics scale
        simulated_evaluations = []
        for candidate in candidates:
            action_name = candidate["action"]
            metrics = self.memory.get_metrics(action_name)
            est = self.impact_estimator.estimate_impact(
                action_name,
                metrics,
                priority_order,
                self.latest_prediction_future_risk if self.latest_prediction_future_risk else {}
            )
            
            # Combine candidate parameters and simulated estimates
            simulated_evaluations.append({
                "action": action_name,
                "risk_score": candidate["risk_score"],
                "benefit_score": candidate["benefit_score"],
                "stability_score": candidate["stability_score"],
                "predicted_stability_gain": est["predicted_stability_gain"],
                "predicted_risk_reduction": est["predicted_risk_reduction"],
                "confidence": est["confidence"]
            })

        # 5. Decide on the safest strategic recommendation
        # Pick the action with maximum (benefit_score * confidence - risk_score)
        best_action = None
        best_score = -999.0

        for eval_act in simulated_evaluations:
            score = (eval_act["benefit_score"] * eval_act["confidence"]) - eval_act["risk_score"]
            if score > best_score:
                best_score = score
                best_action = eval_act

        if not best_action:
            # Fallback action
            best_action = {
                "action": "DEFENSE_ESCALATION",
                "risk_score": 0.15,
                "benefit_score": 0.25,
                "stability_score": 0.90,
                "predicted_stability_gain": 0.15,
                "predicted_risk_reduction": 0.15,
                "confidence": 0.90
            }

        # Format dashboard-compatible strategic response
        now_ms = int(time.time() * 1000)
        
        # Priority mapping for dashboard display
        dash_priority = "LOW"
        if len(priority_order) > 0 and priority_order[0] in ["CYBER_ATTACK", "VOLTAGE_COLLAPSE"]:
            dash_priority = "HIGH"
        elif len(priority_order) > 0 and priority_order[0] != "NOMINAL_MONITORING":
            dash_priority = "MEDIUM"

        strategy_recommendation = {
            "timestamp": now_ms,
            "recommended_strategy": best_action["action"],
            "confidence": best_action["confidence"],
            "expected_risk_reduction": best_action["predicted_risk_reduction"],
            "priority": dash_priority,
            "resource_allocation": resource_alloc
        }

        strategy_memory_state = {
            "timestamp": now_ms,
            "history": self.memory.history
        }

        # 6. Publish strategic states
        try:
            client.publish("grid/strategy", json.dumps({
                "timestamp": now_ms,
                "evaluations": simulated_evaluations
            }))
            client.publish("grid/strategy_priority", json.dumps({
                "timestamp": now_ms,
                "priority_order": priority_order
            }))
            client.publish("grid/strategy_recommendation", json.dumps(strategy_recommendation))
            client.publish("grid/strategy_memory", json.dumps(strategy_memory_state))
            
            logger.debug(f"Published Strategic Coordination loop: {best_action['action']}")
        except Exception as e:
            logger.error(f"Failed to publish strategic coordinator metrics: {e}")

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info("Strategic Coordinator daemon connected successfully to broker!")
            client.subscribe("grid/telemetry")
            client.subscribe("grid/threat")
            client.subscribe("grid/defense")
            client.subscribe("grid/self_healing")
            client.subscribe("grid/events")
            client.subscribe("grid/alerts")
            
            # Forecast topics from Layer 11A
            client.subscribe("prediction/threat_forecast")
            client.subscribe("prediction/pre_attack_alert")
            client.subscribe("prediction/future_risk")
            client.subscribe("prediction/trust_forecast")
        else:
            logger.error(f"Strategic Coordinator MQTT Connection failed: rc {rc}")

    def on_message(self, client, userdata, msg):
        try:
            topic = msg.topic
            payload = json.loads(msg.payload.decode("utf-8"))

            if topic == "grid/telemetry":
                self.handle_telemetry(payload, client)
            elif topic == "grid/threat":
                self.latest_threat = payload
            elif topic == "grid/defense":
                self.latest_defense = payload
            elif topic == "grid/self_healing":
                self.latest_self_healing = payload
            elif topic == "grid/events":
                self.event_history.append(payload)
                # Listen to event history to dynamically verify success feedback
                # e.g., if we recommend "PREEMPTIVE_REROUTE" and we see success/failure logs
                self.process_feedback_events(payload)
            elif topic == "grid/alerts":
                self.alert_history.append(payload)
            elif topic == "prediction/threat_forecast":
                self.latest_prediction_threat_forecast = payload
            elif topic == "prediction/pre_attack_alert":
                self.latest_prediction_pre_attack_alert = payload
            elif topic == "prediction/future_risk":
                self.latest_prediction_future_risk = payload
            elif topic == "prediction/trust_forecast":
                self.latest_prediction_trust_forecast = payload

        except Exception as e:
            logger.error(f"Strategic Coordinator error parsing message on {msg.topic}: {e}")

    def process_feedback_events(self, event_payload: dict):
        """
        Processes grid events statefully to record execution feedback (success/fail) in StrategyMemory.
        """
        event_text = event_payload.get("event", "").upper()
        
        # Check for feedback keywords matching our candidate actions
        for action in self.action_simulator.CANDIDATE_ACTIONS:
            if action in event_text:
                success = "SUCCESS" in event_text or "COMPLETED" in event_text or "STABILIZED" in event_text
                rolled_back = "ROLLBACK" in event_text or "ABORTED" in event_text or "FAILED" in event_text
                
                self.memory.record_action(action, success, rolled_back)
                logger.info(f"Feedback logged for strategic action {action} | Success: {success}, Rolled Back: {rolled_back}")

if __name__ == "__main__":
    coordinator = StrategicCoordinator()
    
    client = mqtt.Client(client_id="strategic_coordinator_engine")
    client.on_connect = coordinator.on_connect
    client.on_message = coordinator.on_message
    
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
        client.loop_forever()
    except KeyboardInterrupt:
        logger.info("Stopping Strategic Coordinator...")
    except Exception as e:
        logger.error(f"MQTT strategic coordinator daemon crash: {e}")
        sys.exit(1)
