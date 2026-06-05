import os
import sys
import time
import json
import logging
import paho.mqtt.client as mqtt
from typing import Dict, Any, List

# Setup local module imports
arena_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(arena_dir, "..")))

from arena.red_agent import RedAgent
from arena.blue_agent import BlueAgent
from arena.arena_simulator import ArenaSimulator
from arena.arena_memory import ArenaMemory

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("arena.arena_coordinator")

MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))

class ArenaCoordinator:
    def __init__(self):
        # AI Arena components
        self.red = RedAgent()
        self.blue = BlueAgent()
        self.simulator = ArenaSimulator()
        self.memory = ArenaMemory()

        # Load persisted Q-tables
        saved = self.memory.load_state()
        self.red.q_table = saved.get("red_q_table", {})
        self.blue.q_table = saved.get("blue_q_table", {})

        # State cache
        self.last_red_action = {"target": "Bus_5", "severity": 0.5, "stealth": 0.5, "type": "NOMINAL"}
        self.last_blue_action = {"anomaly_threshold": 0.5, "trust_decay_speed": "NORMAL", "rollback_lockout": 30.0, "routing_strategy": "SHORTEST_PATH"}

        self.round_counter = len(self.memory.history)
        self.last_cycle_time = 0.0
        self.min_cycle_interval = 0.5
        self.last_telemetry_timestamp = 0

    def handle_telemetry(self, payload: dict, client: mqtt.Client):
        """
        Trigger an adaptive coevolution match round on telemetry updates.
        """
        now = time.time()
        if now - self.last_cycle_time < self.min_cycle_interval:
            return

        pkt_ts = payload.get("timestamp", 0)
        if pkt_ts <= self.last_telemetry_timestamp:
            return

        self.last_telemetry_timestamp = pkt_ts
        self.last_cycle_time = now

        self.run_match_round(client)

    def run_match_round(self, client: mqtt.Client):
        """
        Execute one round of Red vs Blue AI coevolution.
        """
        self.round_counter += 1
        
        # 1. Red Agent selects action based on current Blue posture
        red_idx, red_params = self.red.select_action(self.last_blue_action)
        red_target, red_type, red_sev, red_stealth = red_params

        # 2. Blue Agent selects action based on current Red threat
        blue_idx, blue_params = self.blue.select_action(self.last_red_action)
        blue_thresh, blue_decay, blue_rollback, blue_routing = blue_params

        # 3. Simulate Match
        results = self.simulator.run_match(red_params, blue_params)

        # 4. Compute Rewards
        # Red rewards: higher disruption (voltage/frequency deviations) + slower detection & containment
        red_reward = (
            (results["voltage_deviation"] * 12.0) +
            (results["frequency_deviation"] * 6.0) -
            (results["detection_delay"] * 0.15) -
            (4.0 if results["mitigation_success"] else 0.0)
        )

        # Blue rewards: successful mitigation + fast times - disruption - false alarm penalty
        blue_reward = (
            (6.0 if results["mitigation_success"] else -4.0) -
            (results["voltage_deviation"] * 15.0) -
            (results["containment_delay"] * 0.25) -
            (results["restoration_delay"] * 0.08) -
            (3.0 if results["false_alarm"] else 0.0)
        )

        # 5. Update Q-tables (learning step)
        next_red_action = {"target": red_target, "severity": red_sev, "stealth": red_stealth, "type": red_type}
        next_blue_action = {
            "anomaly_threshold": blue_thresh, 
            "trust_decay_speed": blue_decay, 
            "rollback_lockout": blue_rollback, 
            "routing_strategy": blue_routing
        }

        self.red.update_q_value(self.last_blue_action, red_idx, red_reward, next_blue_action)
        self.blue.update_q_value(self.last_red_action, blue_idx, blue_reward, next_red_action)

        # Update exploration parameters (decay epsilon)
        self.red.decay_exploration()
        self.blue.decay_exploration()

        # Update cache
        self.last_red_action = next_red_action
        self.last_blue_action = next_blue_action

        # 6. Save to history & persist state periodically
        self.memory.record_match(
            self.round_counter, 
            self.last_red_action, 
            self.last_blue_action, 
            results, 
            red_reward, 
            blue_reward
        )
        
        if self.round_counter % 10 == 0:
            self.memory.save_state(self.red.q_table, self.blue.q_table)

        # 7. Extract best parameters for Blue recommendations
        recommendations = self.get_best_defense_recommendations()

        # 8. Publish MQTT Topics
        now_ms = int(time.time() * 1000)
        try:
            client.publish("grid/arena/match", json.dumps({
                "timestamp": now_ms,
                "round_id": self.round_counter,
                "red_action": self.last_red_action,
                "blue_action": self.last_blue_action,
                "results": results
            }))
            client.publish("grid/arena/rewards", json.dumps({
                "timestamp": now_ms,
                "round_id": self.round_counter,
                "red_reward": round(red_reward, 3),
                "blue_reward": round(blue_reward, 3)
            }))
            client.publish("grid/arena/evolution", json.dumps({
                "timestamp": now_ms,
                "round_id": self.round_counter,
                "epsilon_red": round(self.red.epsilon, 4),
                "epsilon_blue": round(self.blue.epsilon, 4),
                "total_rounds": self.round_counter
            }))
            client.publish("grid/arena/recommendations", json.dumps({
                "timestamp": now_ms,
                "recommendations": recommendations
            }))
            
            logger.debug(f"AI Arena match round {self.round_counter} completed.")
        except Exception as e:
            logger.error(f"Failed to publish Arena coordination events: {e}")

    def get_best_defense_recommendations(self) -> Dict[str, Any]:
        """
        Scan the Q-table for actions that achieved high rewards to build the recommended defense.
        """
        best_q = -999.0
        best_action = self.blue.actions[1] # Default fallback

        for state, q_values in self.blue.q_table.items():
            for idx, q in enumerate(q_values):
                if q > best_q:
                    best_q = q
                    best_action = self.blue.actions[idx]

        thresh, decay, rollback, routing = best_action
        return {
            "optimal_anomaly_threshold": thresh,
            "optimal_trust_decay": decay,
            "optimal_rollback_lockout": rollback,
            "optimal_routing_strategy": routing,
            "confidence_score": round(min(1.0, max(0.1, (best_q + 10.0) / 20.0)), 2)
        }

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info("Arena Coordinator daemon connected successfully to broker!")
            client.subscribe("grid/telemetry")
        else:
            logger.error(f"Arena Coordinator MQTT connection failed: rc {rc}")

    def on_message(self, client, userdata, msg):
        try:
            topic = msg.topic
            payload = json.loads(msg.payload.decode("utf-8"))

            if topic == "grid/telemetry":
                self.handle_telemetry(payload, client)
        except Exception as e:
            logger.error(f"Arena Coordinator error parsing message: {e}")

if __name__ == "__main__":
    coordinator = ArenaCoordinator()
    
    client = mqtt.Client(client_id="ai_arena_coevolution_coordinator")
    client.on_connect = coordinator.on_connect
    client.on_message = coordinator.on_message
    
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
        client.loop_forever()
    except KeyboardInterrupt:
        logger.info("Stopping AI Arena Coordinator...")
    except Exception as e:
        logger.error(f"MQTT arena coordinator daemon crash: {e}")
        sys.exit(1)
