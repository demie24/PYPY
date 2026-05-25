import os
import csv
import time
import json
import logging
from collections import deque
import numpy as np
import torch
import paho.mqtt.client as mqtt

from multi_bus_model import ThreatAwarePredictorLSTM

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ai_prediction.threat_aware_inference")

MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))

AI_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.abspath(os.path.join(AI_DIR, "..", "data_collector", "data", "telemetry_dataset.csv"))
CHECKPOINT_PATH = os.path.join(AI_DIR, "models", "lstm_threat_aware_predictor.pt")

class ThreatAwareInferenceEngine:
    def __init__(self):
        self.window_size = 10
        self.history = deque(maxlen=self.window_size)
        
        # State caches
        self.latest_anomaly_score = 0.0
        self.latest_threat_score = 0.0
        self.latest_cascade_probability = 0.0
        self.latest_propagation_risk = 0
        self.latest_flisr_state = "NORMAL"
        
        # Model config
        self.feature_dim = 32
        self.model = None
        
        # Scaler variables
        self.min_vals = None
        self.max_vals = None
        
        # Targets: Bus_1, Bus_3, Bus_5, Bus_7, Bus_9 (indices 1, 3, 5, 7, 9)
        self.target_indices = [1, 3, 5, 7, 9]
        self.target_names = ["Bus_1", "Bus_3", "Bus_5", "Bus_7", "Bus_9"]
        
        # Smoothing cache
        self.prev_predictions = {}
        self.prev_cyber_prob = 0.0
        
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
            raise FileNotFoundError(f"Threat-aware model checkpoint not found at: {CHECKPOINT_PATH}. Please run training first!")
            
        logger.info(f"Loading Threat-Aware Predictor model from: {CHECKPOINT_PATH}")
        self.model = ThreatAwarePredictorLSTM(input_dim=self.feature_dim, output_dim=5, hidden_dim=64, num_layers=2, dropout=0.2)
        self.model.load_state_dict(torch.load(CHECKPOINT_PATH, map_location="cpu"))
        self.model.eval()
        logger.info("Model loaded successfully.")

    def fit_scaler(self):
        """
        Determines Min-Max scaler values from the telemetry dataset CSV.
        """
        expected_headers = [
            "timestamp",
            "bus_1_v", "bus_2_v", "bus_3_v", "bus_4_v", "bus_5_v", "bus_6_v", "bus_7_v", "bus_8_v", "bus_9_v",
            "line_L1_4_load", "line_L2_7_load", "line_L3_9_load", "line_L4_5_load", "line_L4_9_load", "line_L5_6_load", "line_L6_7_load", "line_L7_8_load", "line_L8_9_load",
            "breaker_L1_4", "breaker_L2_7", "breaker_L3_9", "breaker_L4_5", "breaker_L4_9", "breaker_L5_6", "breaker_L6_7", "breaker_L7_8", "breaker_L8_9",
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
        
        if os.path.exists(CSV_PATH):
            try:
                data_matrix = []
                with open(CSV_PATH, mode="r", newline="") as f:
                    reader = csv.reader(f)
                    header = [h.strip() for h in next(reader)]
                    header_to_idx = {name: i for i, name in enumerate(header)}
                    
                    for row in reader:
                        if row:
                            new_row = []
                            for col_name in expected_headers:
                                if col_name in header_to_idx:
                                    try:
                                        new_row.append(float(row[header_to_idx[col_name]]))
                                    except ValueError:
                                        new_row.append(0.0)
                                else:
                                    new_row.append(0.0)
                            data_matrix.append(new_row)
                            
                data = np.array(data_matrix, dtype=np.float32)
                if len(data) >= 5:
                    feature_indices = [i for i in range(1, len(expected_headers)) if i not in self.target_indices]
                    X_raw = data[:, feature_indices]
                    self.min_vals = X_raw.min(axis=0)
                    self.max_vals = X_raw.max(axis=0)
                    logger.info(f"Scaler fit successful on {len(data)} CSV dataset rows.")
                    return
            except Exception as e:
                logger.error(f"Failed to fit scaler: {e}. Falling back to default ranges.")
                
        # Nominal fallback ranges (D = 32 features)
        v_min, v_max = [0.5] * 4, [1.2] * 4
        l_min, l_max = [0.0] * 9, [150.0] * 9
        b_min, b_max = [0.0] * 9, [1.0] * 9
        a_min, a_max = [0.0], [0.05]
        t_min, t_max = [0.0], [100.0]
        atk_min, atk_max = [0.0], [1.0]
        f_min, f_max = [0.0], [4.0]
        at_min, at_max = [0.0], [5.0]
        fdia_min, fdia_max = [0.0], [1.0]
        rep_min, rep_max = [0.0], [1.0]
        ba_min, ba_max = [0.0], [1.0]
        cp_min, cp_max = [0.0], [1.0]
        pr_min, pr_max = [0.0], [2.0]
        
        self.min_vals = np.array(
            v_min + l_min + b_min + a_min + t_min + atk_min + f_min +
            at_min + fdia_min + rep_min + ba_min + cp_min + pr_min,
            dtype=np.float32
        )
        self.max_vals = np.array(
            v_max + l_max + b_max + a_max + t_max + atk_max + f_max +
            at_max + fdia_max + rep_max + ba_max + cp_max + pr_max,
            dtype=np.float32
        )

    def process_telemetry(self, telemetry, client):
        try:
            # 1. Parse physical state features (split targets/inputs)
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
                
            # 2. Extract active attack status flag and parse specific type
            attack_status = telemetry.get("attack_status", {})
            active_attack = attack_status.get("active_attack")
            attack_active = 1 if active_attack is not None else 0
            
            fdia_active = 0
            replay_active = 0
            breaker_attack_active = 0
            attack_type = 0
            
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
                        
            flisr_val = self.encode_flisr_state(self.latest_flisr_state)
            
            # 3. Compile Raw Feature Vector (D = 32)
            raw_features = np.array(
                bus_voltages + 
                line_loads + 
                breaker_states + 
                [self.latest_anomaly_score, self.latest_threat_score, attack_active, flisr_val,
                 attack_type, fdia_active, replay_active, breaker_attack_active,
                 self.latest_cascade_probability, self.latest_propagation_risk], 
                dtype=np.float32
            )
            
            # 4. Normalize using fitted limits
            range_vals = self.max_vals - self.min_vals
            range_vals[range_vals == 0.0] = 1.0
            scaled_features = (raw_features - self.min_vals) / range_vals
            
            # 5. Append to sliding history buffer
            self.history.append(scaled_features)
            
            # 6. Run prediction if buffer is full
            if len(self.history) == self.window_size:
                seq = np.array(self.history, dtype=np.float32)
                tensor_input = torch.tensor(seq).unsqueeze(0)
                
                # Execute inference
                start_time = time.time()
                with torch.no_grad():
                    pred_volts_tensor, pred_cyber_tensor = self.model.predict(tensor_input)
                    pred_volts = pred_volts_tensor.squeeze(0).numpy()
                    pred_cyber = float(pred_cyber_tensor.squeeze(0).numpy()[0])
                latency_ms = (time.time() - start_time) * 1000
                
                # Apply smoothing to cyber probability
                alpha_cyber = 0.35
                pred_cyber = self.prev_cyber_prob + alpha_cyber * (pred_cyber - self.prev_cyber_prob)
                self.prev_cyber_prob = pred_cyber
                
                forecasts = {}
                volt_deltas = []
                
                for idx, bus_name in enumerate(self.target_names):
                    predicted_val = float(pred_volts[idx])
                    actual_val = float(actual_voltages[bus_name])
                    
                    # NaN / Inf protection
                    if np.isnan(predicted_val) or np.isinf(predicted_val):
                        predicted_val = actual_val
                        
                    # Prediction smoothing (EMA)
                    if bus_name not in self.prev_predictions:
                        self.prev_predictions[bus_name] = predicted_val
                    else:
                        alpha = 0.40
                        predicted_val = self.prev_predictions[bus_name] + alpha * (predicted_val - self.prev_predictions[bus_name])
                        self.prev_predictions[bus_name] = predicted_val
                        
                    pred_delta = predicted_val - actual_val
                    volt_deltas.append(abs(pred_delta))
                    
                    forecasts[bus_name] = {
                        "predicted": round(predicted_val, 4),
                        "actual": round(actual_val, 4),
                        "delta": round(pred_delta, 4)
                    }
                    
                # Determine overall cyber-instability status
                if pred_cyber >= 0.70:
                    overall_status = "CYBER-CRITICAL"
                elif pred_cyber >= 0.30:
                    overall_status = "SUSPICIOUS"
                else:
                    overall_status = "NORMAL"
                    
                # Calculate threat-aware confidence score
                # Drops based on voltage forecasting errors and cyber instability classification
                mean_delta = float(np.mean(volt_deltas))
                base_conf = 0.98 - 2.0 * mean_delta
                confidence_factor = 1.0 - pred_cyber
                conf = max(0.40, min(0.99, base_conf * (0.3 + 0.7 * confidence_factor)))
                
                # 7. Publish threat-aware forecast
                payload_out = {
                    "timestamp": int(time.time() * 1000),
                    "forecasts": forecasts,
                    "cyber_instability_probability": round(pred_cyber, 4),
                    "status": overall_status,
                    "confidence": round(conf, 2),
                    "forecast_horizon_seconds": 10
                }
                
                client.publish("grid/ai_threat_forecast", json.dumps(payload_out))
                logger.info(
                    f"Published Threat-Aware Forecast | Status: {overall_status} | "
                    f"Cyber Prob: {pred_cyber:.2f} | Conf: {conf:.2f} | Latency: {latency_ms:.2f}ms"
                )
            else:
                logger.info(f"Threat-Aware buffer warming up: {len(self.history)}/{self.window_size} frames.")
                
        except Exception as e:
            logger.error(f"Threat-Aware Inference processing failure: {e}")

engine = ThreatAwareInferenceEngine()

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info("AI Threat-Aware Inference Engine connected to MQTT!")
        client.subscribe("grid/telemetry")
        client.subscribe("grid/alerts")
        client.subscribe("grid/threat")
        client.subscribe("grid/config")
        client.subscribe("grid/control")
    else:
        logger.error(f"AI Threat-Aware Inference connection failed: rc {rc}")

def on_message(client, userdata, msg):
    try:
        topic = msg.topic
        payload = json.loads(msg.payload.decode("utf-8"))
        
        if topic == "grid/alerts":
            engine.latest_anomaly_score = float(payload.get("loss", 0.0))
            
        elif topic == "grid/threat":
            engine.latest_threat_score = float(payload.get("threat_score", 0.0))
            engine.latest_cascade_probability = float(payload.get("cascade_probability", 0.0))
            risk_str = payload.get("propagation_risk", "LOW").upper()
            risk_mapping = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}
            engine.latest_propagation_risk = risk_mapping.get(risk_str, 0)
            
        elif topic == "grid/config":
            if "flisr_state" in payload:
                engine.latest_flisr_state = payload["flisr_state"]
                
        elif topic == "grid/control":
            cmd = payload.get("command")
            if cmd == "RESET_ALARMS":
                engine.latest_anomaly_score = 0.0
                engine.latest_threat_score = 0.0
                engine.latest_cascade_probability = 0.0
                engine.latest_propagation_risk = 0
                engine.latest_flisr_state = "NORMAL"
                engine.history.clear()
                engine.prev_predictions.clear()
                engine.prev_cyber_prob = 0.0
                logger.info("AI Threat-Aware Inference history and cache reset.")
                
        elif topic == "grid/telemetry":
            engine.process_telemetry(payload, client)
            
    except Exception as e:
        logger.error(f"Error handling message on {msg.topic}: {e}")

if __name__ == "__main__":
    # Wait for the model weights to be saved by training
    time.sleep(2)
    try:
        engine.load_model()
        engine.fit_scaler()
    except Exception as e:
        logger.error(f"Inference Engine startup configuration failure: {e}")
        os._exit(1)
        
    client = mqtt.Client(client_id="ai_threat_aware_inference_engine")
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
        client.loop_forever()
    except KeyboardInterrupt:
        logger.info("Stopping AI Threat-Aware Inference Engine...")
    except Exception as e:
        logger.error(f"MQTT Loop Error: {e}")
        os._exit(1)
