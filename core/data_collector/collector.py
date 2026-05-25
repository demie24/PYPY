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
        self.latest_flisr_state = "NORMAL"
        
        # Line layout definitions
        self.line_ids = ["L1_4", "L2_7", "L3_9", "L4_5", "L4_9", "L5_6", "L6_7", "L7_8", "L8_9"]
        
        # CSV headers
        self.headers = [
            "timestamp",
            "bus_1_v", "bus_2_v", "bus_3_v", "bus_4_v", "bus_5_v", "bus_6_v", "bus_7_v", "bus_8_v", "bus_9_v",
            "line_L1_4_load", "line_L2_7_load", "line_L3_9_load", "line_L4_5_load", "line_L4_9_load", "line_L5_6_load", "line_L6_7_load", "line_L7_8_load", "line_L8_9_load",
            "breaker_L1_4", "breaker_L2_7", "breaker_L3_9", "breaker_L4_5", "breaker_L4_9", "breaker_L5_6", "breaker_L6_7", "breaker_L7_8", "breaker_L8_9",
            "anomaly_score",
            "threat_score",
            "attack_active",
            "flisr_state_encoded"
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
                
            # 3. Extract Line Loads
            line_loads = []
            for lid in self.line_ids:
                line_loads.append(telemetry["state"]["lines"][lid]["capacity_pct"])
                
            # 4. Extract Breaker States (CLOSED=1, OPEN=0)
            breaker_states = []
            for lid in self.line_ids:
                status = telemetry["state"]["breakers"].get(lid, "CLOSED")
                breaker_states.append(1 if status == "CLOSED" else 0)
                
            # 5. Extract active attack status flag
            attack_active = 1 if telemetry.get("attack_status", {}).get("active_attack") is not None else 0
            
            # 6. Construct synchronized sample row
            row_data = [
                ts,
                *bus_voltages,
                *line_loads,
                *breaker_states,
                self.latest_anomaly_score,
                self.latest_threat_score,
                attack_active,
                self.encode_flisr_state(self.latest_flisr_state)
            ]
            
            # 7. Append sample row to CSV
            with open(CSV_PATH, mode="a", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(row_data)
                
            # 8. Append feature vector (excluding timestamp) to rolling buffer
            # Feature size: 9 buses + 9 line loads + 9 breaker states + 1 anomaly + 1 threat + 1 attack + 1 flisr = 31 features
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
            # Record the latest threat scoring index
            collector.latest_threat_score = int(payload.get("threat_score", 0))

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
