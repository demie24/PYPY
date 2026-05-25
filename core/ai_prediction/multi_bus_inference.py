import os
import csv
import time
import json
import logging
from collections import deque
import numpy as np
import torch
import paho.mqtt.client as mqtt

from multi_bus_model import MultiBusPredictorLSTM

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ai_prediction.multi_bus_inference")

MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))

AI_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.abspath(os.path.join(AI_DIR, "..", "data_collector", "data", "telemetry_dataset.csv"))
CHECKPOINT_PATH = os.path.join(AI_DIR, "models", "lstm_multi_bus_predictor.pt")

class MultiBusInferenceEngine:
    def __init__(self):
        self.window_size = 10
        self.history = deque(maxlen=self.window_size)
        
        # State caches
        self.latest_anomaly_score = 0.0
        self.latest_threat_score = 0.0
        self.latest_flisr_state = "NORMAL"
        
        # Model config
        self.feature_dim = 26
        self.model = None
        
        # Scaler variables
        self.min_vals = None
        self.max_vals = None
        
        # Targets: Bus_1, Bus_3, Bus_5, Bus_7, Bus_9 (indices 1, 3, 5, 7, 9)
        self.target_indices = [1, 3, 5, 7, 9]
        self.target_names = ["Bus_1", "Bus_3", "Bus_5", "Bus_7", "Bus_9"]
        
        # Smoothing cache for the 5 target buses
        self.prev_predictions = {}
        
        # Line layout definitions
        self.line_ids = ["L1_4", "L2_7", "L3_9", "L4_5", "L4_9", "L5_6", "L6_7", "L7_8", "L8_9"]

    def encode_flisr_state(self, state_str):
        mapping = {
            "NORMAL": 0,
            "FAULT_DETECTED": 1,
            "ISOLATION": 2,
            "RESTORATION": 3,
            "RESTORED": 4
        }
        return mapping.get(state_str, 0)

    def load_model(self):
        """
        Loads the trained model weights and verifies checkpoint.
        """
        if not os.path.exists(CHECKPOINT_PATH):
            raise FileNotFoundError(f"Multi-bus model checkpoint not found at: {CHECKPOINT_PATH}. Please run training first!")
            
        logger.info(f"Loading Multi-Bus Predictor model from: {CHECKPOINT_PATH}")
        self.model = MultiBusPredictorLSTM(input_dim=self.feature_dim, output_dim=5, hidden_dim=64, num_layers=2, dropout=0.2)
        self.model.load_state_dict(torch.load(CHECKPOINT_PATH, map_location="cpu"))
        self.model.eval()
        logger.info("Model loaded successfully.")

    def fit_scaler(self):
        """
        Determines Min-Max scaler values from the telemetry dataset CSV.
        """
        if os.path.exists(CSV_PATH):
            try:
                data = []
                with open(CSV_PATH, mode="r", newline="") as f:
                    reader = csv.reader(f)
                    header = next(reader)
                    for row in reader:
                        if row:
                            data.append([float(val) for val in row])
                
                data = np.array(data, dtype=np.float32)
                if len(data) >= 5:
                    feature_indices = [i for i in range(1, len(header)) if i not in self.target_indices]
                    X_raw = data[:, feature_indices]
                    self.min_vals = X_raw.min(axis=0)
                    self.max_vals = X_raw.max(axis=0)
                    logger.info(f"Scaler fit successful on {len(data)} CSV dataset rows.")
                    return
            except Exception as e:
                logger.error(f"Failed to fit scaler: {e}. Falling back to default ranges.")
                
        # Nominal fallback ranges (D = 26 features)
        logger.info("Dataset CSV absent or small. Initializing nominal scaling fallback ranges.")
        # Voltages: nominal 1.0 (excluding target buses: 2, 4, 6, 8)
        v_min, v_max = [0.5] * 4, [1.2] * 4
        # Line capacity: nominal 40% (range 0.0 to 150.0%)
        l_min, l_max = [0.0] * 9, [150.0] * 9
        # Breaker states: binary [0, 1]
        b_min, b_max = [0.0] * 9, [1.0] * 9
        # Anomaly loss: [0.0, 0.05]
        a_min, a_max = [0.0], [0.05]
        # Threat score: [0.0, 100.0]
        t_min, t_max = [0.0], [100.0]
        # Attack active: [0.0, 1.0]
        atk_min, atk_max = [0.0], [1.0]
        # FLISR state: [0.0, 4.0]
        f_min, f_max = [0.0], [4.0]
        
        self.min_vals = np.array(v_min + l_min + b_min + a_min + t_min + atk_min + f_min, dtype=np.float32)
        self.max_vals = np.array(v_max + l_max + b_max + a_max + t_max + atk_max + f_max, dtype=np.float32)

    def process_telemetry(self, telemetry, client):
        try:
            # 1. Parse physical state features
            bus_voltages = []
            actual_voltages = {}
            for i in range(1, 10):
                bus_key = f"Bus_{i}"
                v_val = telemetry["state"]["buses"][bus_key]["voltage_pu"]
                if i in self.target_indices:
                    actual_voltages[bus_key] = v_val
                else:
                    bus_voltages.append(v_val)
                
            line_loads = []
            for lid in self.line_ids:
                line_loads.append(telemetry["state"]["lines"][lid]["capacity_pct"])
                
            breaker_states = []
            for lid in self.line_ids:
                status = telemetry["state"]["breakers"].get(lid, "CLOSED")
                breaker_states.append(1 if status == "CLOSED" else 0)
                
            attack_active = 1 if telemetry.get("attack_status", {}).get("active_attack") is not None else 0
            flisr_val = self.encode_flisr_state(self.latest_flisr_state)
            
            # 2. Compile Raw Feature Vector (D = 26)
            raw_features = np.array(
                bus_voltages + 
                line_loads + 
                breaker_states + 
                [self.latest_anomaly_score, self.latest_threat_score, attack_active, flisr_val], 
                dtype=np.float32
            )
            
            # 3. Normalize using fitted limits
            range_vals = self.max_vals - self.min_vals
            range_vals[range_vals == 0.0] = 1.0
            scaled_features = (raw_features - self.min_vals) / range_vals
            
            # 4. Append to sliding history buffer
            self.history.append(scaled_features)
            
            # 5. Run prediction if buffer is full
            if len(self.history) == self.window_size:
                seq = np.array(self.history, dtype=np.float32)
                tensor_input = torch.tensor(seq).unsqueeze(0)
                
                # Execute inference
                start_time = time.time()
                with torch.no_grad():
                    pred_vals = self.model(tensor_input).squeeze(0).numpy()
                latency_ms = (time.time() - start_time) * 1000
                
                forecasts = {}
                overall_status = "NORMAL"
                confidences = []
                
                for idx, bus_name in enumerate(self.target_names):
                    predicted_val = float(pred_vals[idx])
                    actual_val = float(actual_voltages[bus_name])
                    
                    # NaN / Inf protection
                    if np.isnan(predicted_val) or np.isinf(predicted_val):
                        predicted_val = actual_val
                        
                    # Prediction smoothing (Exponential Moving Average)
                    if bus_name not in self.prev_predictions:
                        self.prev_predictions[bus_name] = predicted_val
                    else:
                        alpha = 0.40
                        predicted_val = self.prev_predictions[bus_name] + alpha * (predicted_val - self.prev_predictions[bus_name])
                        self.prev_predictions[bus_name] = predicted_val
                        
                    # Calculate delta
                    pred_delta = predicted_val - actual_val
                    
                    # Determine status
                    if predicted_val < 0.85 or predicted_val > 1.15:
                        status = "CRITICAL"
                        overall_status = "CRITICAL"
                    elif (0.85 <= predicted_val < 0.95) or (1.05 < predicted_val <= 1.15):
                        status = "WARNING"
                        if overall_status != "CRITICAL":
                            overall_status = "WARNING"
                    else:
                        status = "NORMAL"
                        
                    # Calculate confidence score
                    conf = max(0.40, min(0.99, 0.98 - 2.0 * abs(pred_delta)))
                    confidences.append(conf)
                    
                    forecasts[bus_name] = {
                        "predicted": round(predicted_val, 4),
                        "actual": round(actual_val, 4),
                        "delta": round(pred_delta, 4),
                        "status": status
                    }
                    
                # Compile average confidence
                avg_confidence = float(np.mean(confidences))
                
                # 6. Publish multi-bus forecast
                payload_out = {
                    "timestamp": int(time.time() * 1000),
                    "forecasts": forecasts,
                    "overall_status": overall_status,
                    "confidence": round(avg_confidence, 2),
                    "forecast_horizon_seconds": 10
                }
                
                client.publish("grid/ai_forecast_multi_bus", json.dumps(payload_out))
                logger.info(
                    f"Published Multi-Bus Forecast (Status: {overall_status}) | "
                    f"Avg Confidence: {avg_confidence:.2f} | Latency: {latency_ms:.2f}ms"
                )
            else:
                logger.info(f"Multi-Bus buffer warming up: {len(self.history)}/{self.window_size} frames.")
                
        except Exception as e:
            logger.error(f"Multi-Bus Inference processing failure: {e}")

engine = MultiBusInferenceEngine()

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info("AI Multi-Bus Inference Engine connected to MQTT!")
        client.subscribe("grid/telemetry")
        client.subscribe("grid/alerts")
        client.subscribe("grid/threat")
        client.subscribe("grid/config")
        client.subscribe("grid/control")
    else:
        logger.error(f"AI Multi-Bus Inference connection failed: rc {rc}")

def on_message(client, userdata, msg):
    try:
        topic = msg.topic
        payload = json.loads(msg.payload.decode("utf-8"))
        
        if topic == "grid/alerts":
            engine.latest_anomaly_score = float(payload.get("loss", 0.0))
            
        elif topic == "grid/threat":
            engine.latest_threat_score = float(payload.get("threat_score", 0.0))
            
        elif topic == "grid/config":
            if "flisr_state" in payload:
                engine.latest_flisr_state = payload["flisr_state"]
                
        elif topic == "grid/control":
            cmd = payload.get("command")
            if cmd == "RESET_ALARMS":
                engine.latest_anomaly_score = 0.0
                engine.latest_threat_score = 0.0
                engine.latest_flisr_state = "NORMAL"
                engine.history.clear()
                engine.prev_predictions.clear()
                logger.info("AI Multi-Bus Inference history and cache reset.")
                
        elif topic == "grid/telemetry":
            engine.process_telemetry(payload, client)
            
    except Exception as e:
        logger.error(f"Error handling message on {msg.topic}: {e}")

if __name__ == "__main__":
    try:
        engine.load_model()
        engine.fit_scaler()
    except Exception as e:
        logger.error(f"Inference Engine startup configuration failure: {e}")
        os._exit(1)
        
    client = mqtt.Client(client_id="ai_multi_bus_inference_engine")
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
        client.loop_forever()
    except KeyboardInterrupt:
        logger.info("Stopping AI Multi-Bus Inference Engine...")
    except Exception as e:
        logger.error(f"MQTT Loop Error: {e}")
        os._exit(1)
