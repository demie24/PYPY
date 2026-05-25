import os
import csv
import time
import json
import logging
from collections import deque
import numpy as np
import torch
import paho.mqtt.client as mqtt

from model import TelemetryPredictorLSTM

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ai_prediction.inference")

MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))

AI_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.abspath(os.path.join(AI_DIR, "..", "data_collector", "data", "telemetry_dataset.csv"))
CHECKPOINT_PATH = os.path.join(AI_DIR, "models", "lstm_bus5_predictor.pt")

class LiveInferenceEngine:
    def __init__(self):
        self.window_size = 10
        self.history = deque(maxlen=self.window_size)
        
        # State caches
        self.latest_anomaly_score = 0.0
        self.latest_threat_score = 0.0
        self.latest_flisr_state = "NORMAL"
        
        # Model details
        self.feature_dim = 30
        self.model = None
        
        # Scaler variables
        self.min_vals = None
        self.max_vals = None
        
        # Target index is Bus_5 voltage magnitude (index 5)
        self.target_index = 5
        
        # Prediction smoothing variable
        self.prev_predicted_voltage = None
        
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
        Loads the trained model weights and verifies directory configuration.
        """
        if not os.path.exists(CHECKPOINT_PATH):
            raise FileNotFoundError(f"Trained model checkpoint not found at: {CHECKPOINT_PATH}. Please run training first!")
            
        logger.info(f"Loading Threat Predictor model from: {CHECKPOINT_PATH}")
        self.model = TelemetryPredictorLSTM(input_dim=self.feature_dim, hidden_dim=64, num_layers=2, dropout=0.2)
        self.model.load_state_dict(torch.load(CHECKPOINT_PATH, map_location="cpu"))
        self.model.eval()
        logger.info("Model loaded successfully.")

    def fit_scaler(self):
        """
        Determines Min-Max scaler values from the telemetry dataset CSV.
        If CSV is missing, falls back to nominal physical ranges.
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
                    # Exclude timestamp (index 0) and target_index (index 5)
                    feature_indices = [i for i in range(1, len(header)) if i != self.target_index]
                    X_raw = data[:, feature_indices]
                    self.min_vals = X_raw.min(axis=0)
                    self.max_vals = X_raw.max(axis=0)
                    logger.info(f"Min-Max Scaler fit successful from {len(data)} CSV dataset rows.")
                    return
            except Exception as e:
                logger.error(f"Failed to fit scaler from CSV: {e}. Falling back to default ranges.")
                
        # Nominal fallback ranges (D = 30 features)
        logger.info("Dataset CSV absent or small. Initializing nominal scaling fallback ranges.")
        # Voltages: nominal 1.0 (range 0.5 to 1.2) - excluding Bus_5 voltage which is target
        v_min, v_max = [0.5] * 8, [1.2] * 8
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
            actual_voltage = 1.0
            for i in range(1, 10):
                bus_key = f"Bus_{i}"
                v_val = telemetry["state"]["buses"][bus_key]["voltage_pu"]
                if i == self.target_index:
                    actual_voltage = v_val
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
            
            # 2. Compile Raw Feature Vector (D = 30)
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
                # Prepare PyTorch input: shape (1, window_size, feature_dim)
                tensor_input = torch.tensor(seq).unsqueeze(0)
                
                # Execute non-blocking inference
                start_time = time.time()
                with torch.no_grad():
                    pred_val = self.model(tensor_input).item()
                latency_ms = (time.time() - start_time) * 1000
                
                predicted_voltage = float(pred_val)
                
                # NaN / Inf protection
                if np.isnan(predicted_voltage) or np.isinf(predicted_voltage):
                    predicted_voltage = actual_voltage
                    logger.warning("Prediction produced NaN/Inf. Reverting to actual voltage fallback.")
                
                # Prediction smoothing (Exponential Moving Average)
                if self.prev_predicted_voltage is None:
                    self.prev_predicted_voltage = predicted_voltage
                else:
                    alpha = 0.40
                    predicted_voltage = self.prev_predicted_voltage + alpha * (predicted_voltage - self.prev_predicted_voltage)
                    self.prev_predicted_voltage = predicted_voltage
                
                # Calculate delta metrics
                pred_delta = predicted_voltage - actual_voltage
                
                # Voltage Instability Risk categories
                # LOW: [0.95, 1.05] p.u.
                # MEDIUM: [0.90, 0.95) or (1.05, 1.10] p.u.
                # HIGH: [0.85, 0.90) or (1.10, 1.15] p.u.
                # CRITICAL: < 0.85 or > 1.15 p.u.
                if predicted_voltage < 0.85 or predicted_voltage > 1.15:
                    risk = "CRITICAL"
                elif (0.85 <= predicted_voltage < 0.90) or (1.10 < predicted_voltage <= 1.15):
                    risk = "HIGH"
                elif (0.90 <= predicted_voltage < 0.95) or (1.05 < predicted_voltage <= 1.10):
                    risk = "MEDIUM"
                else:
                    risk = "LOW"
                    
                # Calculate confidence score
                confidence = max(0.40, min(0.99, 0.98 - 2.0 * abs(pred_delta)))
                
                # 6. Publish forecast results
                pred_payload = {
                    "timestamp": int(time.time() * 1000),
                    "predicted_bus5_voltage": round(float(predicted_voltage), 4),
                    "actual_bus5_voltage": round(float(actual_voltage), 4),
                    "prediction_delta": round(float(pred_delta), 4),
                    "instability_risk": risk,
                    "confidence": round(float(confidence), 2),
                    "forecast_horizon_seconds": 10
                }
                
                client.publish("grid/ai_prediction", json.dumps(pred_payload))
                logger.info(
                    f"AI Voltage Forecast Bus_5: {predicted_voltage:.4f} p.u. (Risk: {risk}) | "
                    f"Confidence: {confidence:.2f} | Latency: {latency_ms:.2f}ms"
                )
            else:
                logger.info(f"Telemetry buffer warming up: {len(self.history)}/{self.window_size} frames.")
                
        except Exception as e:
            logger.error(f"Inference processing failure: {e}")

engine = LiveInferenceEngine()

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info("AI Inference Engine connected to MQTT!")
        client.subscribe("grid/telemetry")
        client.subscribe("grid/alerts")
        client.subscribe("grid/threat")
        client.subscribe("grid/config")
        client.subscribe("grid/control")
    else:
        logger.error(f"AI Inference connection failed: rc {rc}")

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
                engine.prev_predicted_voltage = None
                logger.info("AI Inference history and cache reset.")
                
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
        
    client = mqtt.Client(client_id="ai_voltage_inference_engine")
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
        client.loop_forever()
    except KeyboardInterrupt:
        logger.info("Stopping AI Inference Engine...")
    except Exception as e:
        logger.error(f"MQTT Loop Error: {e}")
        os._exit(1)
