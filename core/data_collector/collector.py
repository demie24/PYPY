import os
import csv
import time
import json
import logging
from collections import deque
import numpy as np
import paho.mqtt.client as mqtt

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("data_collector.collector")

MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))

DATA_DIR = "/app/data_collector/data" if os.path.exists("/app") else "./data"
CSV_PATH = os.path.join(DATA_DIR, "telemetry_dataset.csv")

# Ensure target directories exist
os.makedirs(DATA_DIR, exist_ok=True)

class DatasetCollector:
    def __init__(self, sequence_length=10, max_buffer_size=100):
        self.sequence_length = sequence_length
        self.buffer = deque(maxlen=max_buffer_size)
        
        # State caches
        self.latest_anomaly_score = 0.0
        self.latest_threat_score = 0.0
        self.latest_cascade_probability = 0.0
        self.latest_propagation_risk = 0  # 0=LOW, 1=MEDIUM, 2=HIGH
        self.latest_flisr_state = "NORMAL"
        
        # Line layout definitions
        self.line_ids = ["L1_4", "L2_7", "L3_9", "L4_5", "L4_9", "L5_6", "L6_7", "L7_8", "L8_9"]
        
        # CSV headers
        self.headers = [
            "timestamp",
            # Bus voltages (9)
            "bus_1_v", "bus_2_v", "bus_3_v", "bus_4_v", "bus_5_v", "bus_6_v", "bus_7_v", "bus_8_v", "bus_9_v",
            # Bus voltage angles (9)
            "bus_1_angle", "bus_2_angle", "bus_3_angle", "bus_4_angle", "bus_5_angle", "bus_6_angle", "bus_7_angle", "bus_8_angle", "bus_9_angle",
            # Bus active power injections (9)
            "bus_1_P", "bus_2_P", "bus_3_P", "bus_4_P", "bus_5_P", "bus_6_P", "bus_7_P", "bus_8_P", "bus_9_P",
            # Bus reactive power injections (9)
            "bus_1_Q", "bus_2_Q", "bus_3_Q", "bus_4_Q", "bus_5_Q", "bus_6_Q", "bus_7_Q", "bus_8_Q", "bus_9_Q",
            # Line active power flows (9)
            "line_L1_4_P", "line_L2_7_P", "line_L3_9_P", "line_L4_5_P", "line_L4_9_P", "line_L5_6_P", "line_L6_7_P", "line_L7_8_P", "line_L8_9_P",
            # Line reactive power flows (9)
            "line_L1_4_Q", "line_L2_7_Q", "line_L3_9_Q", "line_L4_5_Q", "line_L4_9_Q", "line_L5_6_Q", "line_L6_7_Q", "line_L7_8_Q", "line_L8_9_Q",
            # Line currents in p.u. (9)
            "line_L1_4_I", "line_L2_7_I", "line_L3_9_I", "line_L4_5_I", "line_L4_9_I", "line_L5_6_I", "line_L6_7_I", "line_L7_8_I", "line_L8_9_I",
            # Breaker states (9)
            "breaker_L1_4", "breaker_L2_7", "breaker_L3_9", "breaker_L4_5", "breaker_L4_9", "breaker_L5_6", "breaker_L6_7", "breaker_L7_8", "breaker_L8_9",
            # Cyber indicators & decision states (10)
            "anomaly_score",
            "threat_score",
            "attack_active",
            "flisr_state_encoded",
            "attack_type",
            "fdia_active",
            "replay_active",
            "breaker_attack_active",
            "cascade_probability",
            "propagation_risk_encoded"
        ]
        
        self._initialize_csv()

    def _initialize_csv(self):
        # Write headers if CSV file does not exist or is empty
        file_exists = os.path.exists(CSV_PATH)
        is_empty = file_exists and os.path.getsize(CSV_PATH) == 0
        
        if not file_exists or is_empty:
            logger.info(f"Creating new dataset CSV at {CSV_PATH} with {len(self.headers)} columns.")
            with open(CSV_PATH, mode="w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(self.headers)

    def encode_flisr_state(self, state_str):
        mapping = {
            "NORMAL": 0,
            "FAULT_DETECTED": 1,
            "ISOLATION": 2,
            "RESTORATION": 3,
            "RESTORED": 4
        }
        return mapping.get(state_str, 0)

    def process_telemetry(self, telemetry):
        try:
            # 1. Parse timestamp
            ts = telemetry.get("timestamp", int(time.time() * 1000))
            
            # 2. Extract Bus Voltages
            bus_voltages = []
            for i in range(1, 10):
                bus_key = f"Bus_{i}"
                bus_voltages.append(telemetry["state"]["buses"][bus_key]["voltage_pu"])
                
            # 2b. Extract Bus Angles
            bus_angles = []
            for i in range(1, 10):
                bus_key = f"Bus_{i}"
                bus_angles.append(telemetry["state"]["buses"][bus_key]["angle_rad"])

            # 2c. Extract Bus Active Power Injections (P_mw)
            bus_Ps = []
            for i in range(1, 10):
                bus_key = f"Bus_{i}"
                bus_Ps.append(telemetry["state"]["buses"][bus_key]["P_mw"])

            # 2d. Extract Bus Reactive Power Injections (Q_mvar)
            bus_Qs = []
            for i in range(1, 10):
                bus_key = f"Bus_{i}"
                bus_Qs.append(telemetry["state"]["buses"][bus_key]["Q_mvar"])

            # 3. Extract Line Active Power Flows (P_mw)
            line_Ps = []
            for lid in self.line_ids:
                line_Ps.append(telemetry["state"]["lines"][lid]["P_mw"])

            # 3b. Extract Line Reactive Power Flows (Q_mvar)
            line_Qs = []
            for lid in self.line_ids:
                line_Qs.append(telemetry["state"]["lines"][lid]["Q_mvar"])

            # 3c. Extract Line Currents (current_pu)
            line_Is = []
            for lid in self.line_ids:
                line_Is.append(telemetry["state"]["lines"][lid]["current_pu"])
                
            # 4. Extract Breaker States (CLOSED=1, OPEN=0)
            breaker_states = []
            for lid in self.line_ids:
                status = telemetry["state"]["breakers"].get(lid, "CLOSED")
                breaker_states.append(1 if status == "CLOSED" else 0)
                
            # 5. Extract active attack status flag and encode specific attack type
            attack_status = telemetry.get("attack_status", {})
            active_attack = attack_status.get("active_attack")
            attack_active = 1 if active_attack is not None else 0
            
            fdia_active = 0
            replay_active = 0
            breaker_attack_active = 0
            attack_type = 0  # 0=NORMAL, 1=FDIA, 2=REPLAY, 3=TRIP, 4=DOS, 5=SENSOR_SPOOFING
            
            if active_attack:
                compromised = attack_status.get("compromised_nodes", {})
                if active_attack == "FDIA":
                    fdia_active = 1
                    attack_type = 1
                elif active_attack == "REPLAY":
                    replay_active = 1
                    attack_type = 2
                elif active_attack == "TRIP":
                    breaker_attack_active = 1
                    attack_type = 3
                elif active_attack == "SCENARIO":
                    for node, comp in compromised.items():
                        ctype = comp.get("type")
                        if ctype == "FDIA":
                            fdia_active = 1
                            attack_type = 1
                        elif ctype == "REPLAY":
                            replay_active = 1
                            attack_type = 2
                        elif ctype in ["BREAKER_MANIPULATION", "TRIP"]:
                            breaker_attack_active = 1
                            attack_type = 3
                        elif ctype == "DOS":
                            attack_type = 4
                        elif ctype == "SENSOR_SPOOFING":
                            attack_type = 5
                else:
                    active_str = str(active_attack).upper()
                    if "FDIA" in active_str:
                        fdia_active = 1
                        attack_type = 1
                    elif "REPLAY" in active_str:
                        replay_active = 1
                        attack_type = 2
                    elif "TRIP" in active_str or "BREAKER" in active_str:
                        breaker_attack_active = 1
                        attack_type = 3
                    elif "DOS" in active_str:
                        attack_type = 4
                    elif "SENSOR" in active_str:
                        attack_type = 5
            
            # 6. Construct synchronized sample row
            row_data = [
                ts,
                *bus_voltages,
                *bus_angles,
                *bus_Ps,
                *bus_Qs,
                *line_Ps,
                *line_Qs,
                *line_Is,
                *breaker_states,
                self.latest_anomaly_score,
                self.latest_threat_score,
                attack_active,
                self.encode_flisr_state(self.latest_flisr_state),
                attack_type,
                fdia_active,
                replay_active,
                breaker_attack_active,
                self.latest_cascade_probability,
                self.latest_propagation_risk
            ]
            
            # 7. Append sample row to CSV
            with open(CSV_PATH, mode="a", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(row_data)
                
            # 8. Append feature vector (excluding timestamp) to rolling buffer
            # Feature size: 82 features (excluding timestamp)
            feature_vector = row_data[1:]
            self.buffer.append(feature_vector)
            
            # 9. Verify rolling window sequence generation shape
            if len(self.buffer) >= self.sequence_length:
                # Retrieve the last L samples
                window = list(self.buffer)[-self.sequence_length:]
                np_window = np.array(window)
                logger.info(f"LSTM training window verified. Sequence length={self.sequence_length}, Feature count={np_window.shape[1]}. Array shape={np_window.shape}")
            else:
                logger.info(f"Dataset buffer warming up: {len(self.buffer)}/{self.sequence_length} samples.")
                
        except KeyError as e:
            logger.error(f"Error parsing telemetry payload structure: missing key {e}")
        except Exception as e:
            logger.error(f"Failed to process telemetry sample: {e}")

collector = DatasetCollector()

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info("Dataset Collector connected to MQTT!")
        client.subscribe("grid/telemetry")
        client.subscribe("grid/alerts")
        client.subscribe("grid/threat")
        client.subscribe("grid/config")
        client.subscribe("grid/control")
    else:
        logger.error(f"Dataset Collector connection failed: rc {rc}")

def on_message(client, userdata, msg):
    try:
        topic = msg.topic
        payload = json.loads(msg.payload.decode("utf-8"))

        if topic == "grid/alerts":
            # Record the reconstruction error/loss as the anomaly score
            collector.latest_anomaly_score = float(payload.get("loss", 0.0))

        elif topic == "grid/threat":
            # Record the latest threat scoring index and additional metrics
            collector.latest_threat_score = int(payload.get("threat_score", 0))
            collector.latest_cascade_probability = float(payload.get("cascade_probability", 0.0))
            risk_str = payload.get("propagation_risk", "LOW").upper()
            risk_mapping = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}
            collector.latest_propagation_risk = risk_mapping.get(risk_str, 0)

        elif topic == "grid/config":
            # Record latest FLISR FSM state
            if "flisr_state" in payload:
                collector.latest_flisr_state = payload["flisr_state"]

        elif topic == "grid/control":
            # Handle reset commands
            cmd = payload.get("command")
            if cmd == "RESET_ALARMS":
                collector.latest_anomaly_score = 0.0
                collector.latest_threat_score = 0.0
                collector.latest_cascade_probability = 0.0
                collector.latest_propagation_risk = 0
                collector.latest_flisr_state = "NORMAL"
                collector.buffer.clear()
                logger.info("Dataset Collector cache and memory buffer reset.")

        elif topic == "grid/telemetry":
            # Telemetry snapshot is received at 1Hz, triggering dataset logging
            collector.process_telemetry(payload)

    except Exception as e:
        logger.error(f"Error handling message on {msg.topic}: {e}")

if __name__ == "__main__":
    client = mqtt.Client(client_id="telemetry_dataset_collector")
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
        client.loop_forever()
    except KeyboardInterrupt:
        logger.info("Stopping Dataset Collector...")
    except Exception as e:
        logger.error(f"MQTT Loop Error: {e}")
        os._exit(1)
