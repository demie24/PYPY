import os
import time
import json
import logging
import numpy as np
import paho.mqtt.client as mqtt

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ai_detector")

MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))

class NumPyAutoencoderDetector:
    def __init__(self, input_dim=9, hidden_dim=4, lr=0.02):
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.lr = lr
        
        # Initialize weights randomly
        np.random.seed(42)
        self.W1 = np.random.randn(input_dim, hidden_dim) * 0.1
        self.b1 = np.zeros(hidden_dim)
        self.W2 = np.random.randn(hidden_dim, input_dim) * 0.1
        self.b2 = np.zeros(input_dim)
        
        # Adaptive thresholding
        self.threshold = 0.003
        self.loss_history = []
        self.under_attack = False

        # Alert throttling & sliding window variables
        # Window/confirm counts are relaxed during known attacks to reduce flood
        self.anomaly_window = []   # sliding window of boolean flags
        self.window_size = 3       # normal mode window
        self.confirm_count = 2     # number of anomalous flags in window to confirm
        self.last_alerts = {}      # maps suspect_node to {"timestamp": float, "severity": str}
        self.cooldown_period = 12.0   # seconds before duplicate alert for same node (Phase 5B: raised from 8s)

        # Phase 5B: Attack-mode window inflation
        # During a known active attack, inflate the sliding window requirement
        # to avoid flooding with expected anomalies
        self.attack_window_size = 6
        self.attack_confirm_count = 5
        self.attack_cooldown_period = 20.0  # longer suppression during active attacks

    def forward(self, x):
        # Hidden layer with tanh activation
        h = np.tanh(np.dot(x, self.W1) + self.b1)
        # Output layer with linear activation (voltages are bounded around 1.0 p.u.)
        x_hat = np.dot(h, self.W2) + self.b2
        return h, x_hat

    def train_step(self, x):
        h, x_hat = self.forward(x)
        loss = np.mean((x - x_hat) ** 2)
        
        # Backpropagation
        dx_hat = 2.0 * (x_hat - x) / self.input_dim # Shape: (9,)
        
        dW2 = np.outer(h, dx_hat) # Shape: (4, 9)
        db2 = dx_hat             # Shape: (9,)
        
        dh = np.dot(self.W2, dx_hat) # Shape: (4,)
        da = dh * (1.0 - h ** 2)    # Activation derivative for tanh
        
        dW1 = np.outer(x, da)   # Shape: (9, 4)
        db1 = da                # Shape: (4,)
        
        # Gradient update
        self.W1 -= self.lr * dW1
        self.b1 -= self.lr * db1
        self.W2 -= self.lr * dW2
        self.b2 -= self.lr * db2
        
        return loss

    def process_telemetry(self, telemetry_data):
        # Extract voltage magnitudes from Buses 1 to 9
        try:
            x = []
            for i in range(1, 10):
                bus_key = f"Bus_{i}"
                val = telemetry_data["state"]["buses"][bus_key]["voltage_pu"]
                x.append(val)
            
            x = np.array(x)
            
            # Forward pass to get reconstruction
            h, x_hat = self.forward(x)
            loss = np.mean((x - x_hat) ** 2)
            
            is_anomaly = loss > self.threshold
            
            # If not under attack and loss is normal, train the autoencoder to adapt to normal load changes
            if not is_anomaly:
                trained_loss = self.train_step(x)
                # Keep tracking moving average of losses
                self.loss_history.append(trained_loss)
                if len(self.loss_history) > 100:
                    self.loss_history.pop(0)
                    self.threshold = max(0.001, np.mean(self.loss_history) * 4.0)
            
            return {
                "loss": float(loss),
                "threshold": float(self.threshold),
                "is_anomaly": bool(is_anomaly),
                "voltages": x.tolist(),
                "reconstruction": x_hat.tolist()
            }
        except KeyError as e:
            logger.error(f"Missing expected bus keys in telemetry payload: {e}")
            return None

detector = NumPyAutoencoderDetector()

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info("AI Detector connected to MQTT!")
        client.subscribe("grid/telemetry")
        client.subscribe("grid/attack")
        client.subscribe("grid/control")
    else:
        logger.error(f"AI Detector connection failed: rc {rc}")

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode("utf-8"))
        
        if msg.topic == "grid/attack":
            action = payload.get("action")
            if action == "START":
                detector.under_attack = True
            elif action == "STOP":
                detector.under_attack = False
                
        elif msg.topic == "grid/control":
            command = payload.get("command")
            if command == "RESET_ALARMS":
                detector.last_alerts.clear()
                detector.anomaly_window.clear()
                logger.info("AI Detector alerts history and anomaly window reset.")
                
        elif msg.topic == "grid/telemetry":
            res = detector.process_telemetry(payload)
            if res:
                # Phase 5B: Use attack-mode window parameters when under known active attack
                # to avoid flooding on expected grid deviations
                if detector.under_attack:
                    w_size = detector.attack_window_size
                    w_confirm = detector.attack_confirm_count
                    cooldown = detector.attack_cooldown_period
                else:
                    w_size = detector.window_size
                    w_confirm = detector.confirm_count
                    cooldown = detector.cooldown_period

                # 1. Update sliding window
                detector.anomaly_window.append(res["is_anomaly"])
                if len(detector.anomaly_window) > w_size:
                    detector.anomaly_window.pop(0)
                
                # 2. Confirm anomaly over window size
                confirmed_anomaly = sum(1 for x in detector.anomaly_window if x) >= w_confirm
                
                if confirmed_anomaly:
                    # Pinpoint target of anomaly by checking which bus has the highest reconstruction error
                    errors = (np.array(res["voltages"]) - np.array(res["reconstruction"])) ** 2
                    suspect_bus_idx = int(np.argmax(errors)) + 1
                    suspect_bus = f"Bus_{suspect_bus_idx}"
                    
                    # Calculate dynamic severity
                    ratio = res["loss"] / res["threshold"] if res["threshold"] > 0 else 1.0
                    if ratio >= 8.0:
                        severity = "CRITICAL"
                    elif ratio >= 3.0:
                        severity = "HIGH"
                    else:
                        severity = "WARNING"

                    # Phase 5B: Classify anomaly type from error pattern
                    max_err = float(np.max(errors))
                    mean_err = float(np.mean(errors))
                    spread = float(np.std(errors))
                    if spread > 0.02:       # Errors concentrated on 1-2 buses
                        anomaly_class = "TARGETED_FDIA"
                    elif mean_err > 0.05:   # Broad voltage collapse
                        anomaly_class = "PHYSICAL_FAULT"
                    elif max_err > 0.1:     # Large single-bus deviation
                        anomaly_class = "SENSOR_ANOMALY"
                    else:
                        anomaly_class = "GRID_DEVIATION"
                        
                    # Check throttling / suppression
                    now = time.time()
                    last_alert = detector.last_alerts.get(suspect_bus)
                    
                    should_send = True
                    if last_alert:
                        time_since_last = now - last_alert["timestamp"]
                        # Suppress if within cooldown period and severity is not higher
                        if time_since_last < cooldown and severity == last_alert["severity"]:
                            should_send = False
                            
                    if should_send:
                        detector.last_alerts[suspect_bus] = {
                            "timestamp": now,
                            "severity": severity
                        }
                        
                        alert = {
                            "timestamp": int(now * 1000),
                            "type": anomaly_class,
                            "severity": severity,
                            "loss": round(res["loss"], 6),
                            "threshold": round(res["threshold"], 6),
                            "suspect_node": suspect_bus,
                            "msg": f"[{anomaly_class}] Anomalous grid state on {suspect_bus} (reconstruction Δ={round(res['loss'], 5)}, ratio={ratio:.1f}x threshold)."
                        }
                        client.publish("grid/alerts", json.dumps(alert))
                        logger.warning(f"AI Anomaly Alert [{anomaly_class}]! Node: {suspect_bus}, Severity: {severity}, Loss: {res['loss']:.5f}")
    except Exception as e:
        logger.error(f"Error handling telemetry in detector: {e}")

if __name__ == "__main__":
    client = mqtt.Client(client_id="ai_anomaly_detector")
    client.on_connect = on_connect
    client.on_message = on_message
    
    connected = False
    retry_delay = 1.0
    while not connected:
        try:
            client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
            connected = True
            logger.info("AI Detector connected to MQTT successfully!")
        except Exception as e:
            logger.warning(f"AI Detector MQTT connection failed: {e}. Retrying in {retry_delay}s...")
            time.sleep(retry_delay)
            retry_delay = min(15.0, retry_delay * 1.5)
            
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        logger.info("Stopping AI Detector...")
    except Exception as e:
        logger.error(f"MQTT Loop Error: {e}")
        os._exit(1)
