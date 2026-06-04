import os
import sys
import time
import json
import logging
from collections import deque
from typing import Dict, Any, List
import paho.mqtt.client as mqtt

# Resolve local module pathing
adv_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(adv_dir, "..")))

from adversarial.attack_pattern_generator import AttackPatternGenerator
from adversarial.defense_evaluator import DefenseEvaluator
from adversarial.resilience_scorer import ResilienceScorer
from adversarial.campaign_simulator import CampaignSimulator
from adversarial.adversarial_memory import AdversarialMemory

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("adversarial.adversarial_coordinator")

MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))

class AdversarialCoordinator:
    def __init__(self):
        # Component Instances
        self.generator = AttackPatternGenerator()
        self.evaluator = DefenseEvaluator()
        self.scorer = ResilienceScorer()
        self.simulator = CampaignSimulator()
        self.memory = AdversarialMemory()

        # Stateful caches
        self.telemetry_history = deque(maxlen=20)
        self.event_history = deque(maxlen=100)

        self.latest_telemetry = None
        self.latest_threat = None
        self.latest_strategy = None
        self.latest_defense = None
        self.latest_self_healing = None

        self.last_cycle_time = 0.0
        self.last_telemetry_timestamp = 0
        self.min_cycle_interval = 0.5

    def handle_telemetry(self, payload: dict, client: mqtt.Client):
        """
        Ingest telemetry and coordinate adversarial simulation cycle.
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

        self.run_adversarial_cycle(client)

    def run_adversarial_cycle(self, client: mqtt.Client):
        """
        Execute core Layer 11C Adversarial Evaluation loop.
        """
        if not self.latest_telemetry:
            return

        # 1. Determine active campaign type to simulate based on state
        threat_score = float(self.latest_threat.get("threat_score", 0.0)) if self.latest_threat else 0.0
        
        if threat_score > 70.0:
            camp_type = "COORDINATED_MULTI_NODE"
        elif threat_score > 40.0:
            camp_type = "FDIA_ESCALATION"
        else:
            # Random selection for nominal testing cycles
            camp_type = self.generator.CAMPAIGN_TYPES[int(time.time()) % len(self.generator.CAMPAIGN_TYPES)]

        # 2. Generate Simulated Attack Campaign
        campaign = self.generator.generate_campaign(camp_type, target_node="Bus_5")

        # 3. Simulate System Response (incorporates simulated defenses)
        active_defenses = {
            "strategy": self.latest_strategy,
            "defense": self.latest_defense,
            "self_healing": self.latest_self_healing
        }
        sim_results = self.simulator.simulate_campaign(campaign, active_defenses)
        
        sim_events = sim_results["simulated_events"]
        sim_telemetry = sim_results["simulated_telemetry"]

        # 4. Evaluate Defenses reaction delay
        eval_metrics = self.evaluator.evaluate_defense(campaign, sim_events)

        # 5. Compute Resilience Scores
        resilience_scores = self.scorer.calculate_resilience(eval_metrics, sim_telemetry)

        # 6. Record to memory
        self.memory.record_simulation(campaign, eval_metrics, resilience_scores)

        # 7. Weakness Discovery & Recommendations
        weakness_summary = self.memory.get_weakness_summary()
        recommendations = self.generate_recommendations(weakness_summary)

        # 8. Publish Strategic Adversarial Output Topics
        now_ms = int(time.time() * 1000)
        try:
            client.publish("grid/adversarial/campaign", json.dumps({
                "timestamp": now_ms,
                "campaign": campaign,
                "eval_metrics": eval_metrics
            }))
            client.publish("grid/adversarial/resilience", json.dumps({
                "timestamp": now_ms,
                "resilience": resilience_scores
            }))
            client.publish("grid/adversarial/weaknesses", json.dumps({
                "timestamp": now_ms,
                "weaknesses": weakness_summary
            }))
            client.publish("grid/adversarial/recommendations", json.dumps({
                "timestamp": now_ms,
                "recommendations": recommendations
            }))
            
            logger.debug(f"Published Adversarial Coordination: {campaign['campaign_id']}")
        except Exception as e:
            logger.error(f"Failed to publish adversarial metrics: {e}")

    def generate_recommendations(self, weaknesses: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate recommendations to harden defenses based on discovered structural weaknesses.
        """
        recs = []
        
        high_risk = weaknesses.get("high_risk_nodes", [])
        for hr in high_risk:
            node = hr.get("node")
            fail_rate = hr.get("failure_rate", 0.0)
            if fail_rate > 0.0:
                recs.append({
                    "priority": "HIGH",
                    "category": "HARDENING",
                    "target": node,
                    "recommendation": f"Enforce secondary physical verification laws on node {node}. High vulnerability rate ({fail_rate * 100}%).",
                    "rationale": "Adaptive campaign simulations bypassed primary SCADA telemetry validations repeatedly."
                })

        slow_paths = weaknesses.get("slow_recovery_paths", [])
        for sp in slow_paths:
            path = sp.get("path_or_node")
            delay = sp.get("avg_restoration_delay", 0.0)
            if delay > 10.0:
                recs.append({
                    "priority": "MEDIUM",
                    "category": "RECOVERY",
                    "target": path,
                    "recommendation": f"Pre-allocate standby operators and redundant backup lines around {path} to reduce restoration delays.",
                    "rationale": f"Grid containment recovery latency took average of {delay}s during simulation."
                })

        # Default standard recommendation
        if not recs:
            recs.append({
                "priority": "LOW",
                "category": "NOMINAL",
                "target": "Bus_5",
                "recommendation": "Maintain default defense threshold configurations. System is highly resilient.",
                "rationale": "No critical vulnerabilities detected under simulation trials."
            })

        return recs

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info("Adversarial Coordinator daemon connected successfully to broker!")
            client.subscribe("grid/telemetry")
            client.subscribe("grid/threat")
            client.subscribe("grid/strategy")
            client.subscribe("grid/defense")
            client.subscribe("grid/self_healing")
            client.subscribe("grid/events")
        else:
            logger.error(f"Adversarial Coordinator MQTT Connection failed: rc {rc}")

    def on_message(self, client, userdata, msg):
        try:
            topic = msg.topic
            payload = json.loads(msg.payload.decode("utf-8"))

            if topic == "grid/telemetry":
                self.handle_telemetry(payload, client)
            elif topic == "grid/threat":
                self.latest_threat = payload
            elif topic == "grid/strategy":
                self.latest_strategy = payload
            elif topic == "grid/defense":
                self.latest_defense = payload
            elif topic == "grid/self_healing":
                self.latest_self_healing = payload
            elif topic == "grid/events":
                self.event_history.append(payload)

        except Exception as e:
            logger.error(f"Adversarial Coordinator error parsing message on {msg.topic}: {e}")

if __name__ == "__main__":
    coordinator = AdversarialCoordinator()
    
    client = mqtt.Client(client_id="adversarial_coordinator_engine")
    client.on_connect = coordinator.on_connect
    client.on_message = coordinator.on_message
    
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
        client.loop_forever()
    except KeyboardInterrupt:
        logger.info("Stopping Adversarial Coordinator...")
    except Exception as e:
        logger.error(f"MQTT adversarial coordinator daemon crash: {e}")
        sys.exit(1)
