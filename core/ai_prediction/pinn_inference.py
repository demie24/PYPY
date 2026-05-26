import os
import time
import json
import logging
from collections import deque
import numpy as np
import torch

from pinn_model import PhysicsInformedPredictorLSTM

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ai_prediction.pinn_inference")

MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))

AI_DIR = os.path.dirname(os.path.abspath(__file__))
CHECKPOINT_PATH = os.path.join(AI_DIR, "models", "lstm_pinn_cyber_physical_predictor.pt")

# Line parameters for KVL consistency (IEEE 9-bus reactances)
X_LINE = [0.0576, 0.0625, 0.0586, 0.085, 0.092, 0.161, 0.072, 0.161, 0.1008]

LINE_CONNECTIONS = [
    (0, 3), # L1_4
    (1, 6), # L2_7
    (2, 8), # L3_9
    (3, 4), # L4_5
    (3, 8), # L4_9
    (4, 5), # L5_6
    (5, 6), # L6_7
    (6, 7), # L7_8
    (7, 8)  # L8_9
]

C_MATRIX = np.zeros((9, 9), dtype=np.float32)
for k, (f, t) in enumerate(LINE_CONNECTIONS):
    C_MATRIX[f, k] = 1.0
    C_MATRIX[t, k] = -1.0

class PinnInferenceEngine:
    def __init__(self, sequence_length=10):
        self.window_size = sequence_length
        self.history = deque(maxlen=sequence_length)
        
        # State caches for inputs compiling
        self.latest_anomaly_score = 0.0
        self.latest_threat_score = 0.0
        self.latest_cascade_probability = 0.0
        self.latest_propagation_risk = 0
        self.latest_flisr_state = "NORMAL"
        
        # Stateful bus and line trust scores (default 100%)
        self.bus_trust = {f"Bus_{i}": 100.0 for i in range(1, 10)}
        self.line_trust = {lid: 100.0 for lid in ["L1_4", "L2_7", "L3_9", "L4_5", "L4_9", "L5_6", "L6_7", "L7_8", "L8_9"]}
        
        # Concept drift tracking parameters (60-sample rolling window)
        self.drift_buffer = deque(maxlen=60)
        self.concept_drift_score = 0.0
        self.concept_drift_alert = False
        
        self.line_ids = ["L1_4", "L2_7", "L3_9", "L4_5", "L4_9", "L5_6", "L6_7", "L7_8", "L8_9"]
        
        self.model = None
        self.min_vals = None
        self.max_vals = None
        self.original_min_vals = None
        self.original_max_vals = None
        
        # Prediction drift tracking: maps target_timestamp -> { "10s": V_pred, "30s": V_pred, "60s": V_pred }
        self.prediction_registry = {}
        
        # Rolling error buffers for confidence adjustments (deques of size 20)
        self.error_buffer_10 = deque(maxlen=20)
        self.error_buffer_30 = deque(maxlen=20)
        self.error_buffer_60 = deque(maxlen=20)
        
        # Smoothing caches for predicted voltages
        self.prev_predictions_10 = {}
        self.prev_predictions_30 = {}
        self.prev_predictions_60 = {}

    def load_model(self):
        if not os.path.exists(CHECKPOINT_PATH):
            raise FileNotFoundError(f"PINN model checkpoint not found at: {CHECKPOINT_PATH}. Please run training first!")
            
        logger.info(f"Loading Physics-Informed Predictor model from: {CHECKPOINT_PATH}")
        checkpoint = torch.load(CHECKPOINT_PATH, map_location="cpu")
        
        self.model = PhysicsInformedPredictorLSTM(input_dim=82, output_dim=38, hidden_dim=128, num_layers=2)
        self.model.load_state_dict(checkpoint["state_dict"])
        self.model.eval()
        
        self.min_vals = np.array(checkpoint["min_vals"], dtype=np.float32)
        self.max_vals = np.array(checkpoint["max_vals"], dtype=np.float32)
        self.original_min_vals = self.min_vals.copy()
        self.original_max_vals = self.max_vals.copy()
        
        logger.info("PINN model loaded successfully. Scaling parameters loaded.")

    def encode_flisr_state(self, state_str):
        mapping = {
            "NORMAL": 0,
            "FAULT_DETECTED": 1,
            "ISOLATION": 2,
            "RESTORATION": 3,
            "RESTORED": 4
        }
        return mapping.get(state_str, 0)

    def calculate_physics_metrics(self, V_pred, angle_pred, P_pred, Q_pred, latest_breakers, latest_inj_P, latest_inj_Q):
        """
        Evaluates physical consistency of predictions against IEEE 9-bus grid equations.
        """
        masked_P = P_pred * latest_breakers
        masked_Q = Q_pred * latest_breakers
        
        flow_leaving_P = np.matmul(C_MATRIX, masked_P)
        flow_leaving_Q = np.matmul(C_MATRIX, masked_Q)
        
        kcl_mismatch_P = latest_inj_P - flow_leaving_P
        kcl_mismatch_Q = latest_inj_Q - flow_leaving_Q
        
        kcl_err = float(np.mean(kcl_mismatch_P**2) + np.mean(kcl_mismatch_Q**2))
        
        # KVL Voltage Drop mismatches
        kvl_errors = []
        for k, (f, t) in enumerate(LINE_CONNECTIONS):
            V_from = V_pred[f]
            V_to = V_pred[t]
            Q_k = Q_pred[k]
            X_k = X_LINE[k]
            breaker_k = latest_breakers[k]
            
            v_drop = V_from - V_to
            kvl_err_val = breaker_k * (v_drop - Q_k * X_k)
            kvl_errors.append(kvl_err_val**2)
            
        kvl_err = float(np.mean(kvl_errors))
        
        # DC Power Flow mismatch
        dc_flow_errors = []
        for k, (f, t) in enumerate(LINE_CONNECTIONS):
            theta_from = angle_pred[f]
            theta_to = angle_pred[t]
            P_k = P_pred[k]
            X_k = X_LINE[k]
            breaker_k = latest_breakers[k]
            
            expected_flow = (theta_from - theta_to) / X_k
            err = breaker_k * (P_k - expected_flow)
            dc_flow_errors.append(err**2)
            
        dc_flow_err = float(np.mean(dc_flow_errors))
        
        # Topology checking (flow on open breakers)
        topo_errors = (1.0 - latest_breakers) * (np.abs(P_pred) + np.abs(Q_pred))
        topology_valid = bool(np.all(topo_errors < 0.05))
        
        # Stability check
        stability_valid = bool(np.all((V_pred >= 0.95) & (V_pred <= 1.05)))
        
        return kcl_err, kvl_err, dc_flow_err, topology_valid, stability_valid

    def reconstruct_voltage(self, bus_idx, current_voltages, current_currents, breakers):
        """
        Reconstructs a bus voltage magnitude from physical KVL neighbors when observability is degraded.
        """
        neighbors = []
        for k, (f, t) in enumerate(LINE_CONNECTIONS):
            if breakers[k] == 0.0:
                continue
            I_val = current_currents[k]
            X_val = X_LINE[k]
            if f == bus_idx:
                neighbors.append(current_voltages[t] + I_val * X_val)
            elif t == bus_idx:
                neighbors.append(current_voltages[f] - I_val * X_val)
        if neighbors:
            return float(np.mean(neighbors))
        else:
            return current_voltages[bus_idx]

    def monitor_concept_drift(self, raw_row):
        """
        Statefully tracks concept drift over incoming telemetry.
        """
        self.drift_buffer.append(raw_row)
        if len(self.drift_buffer) >= 30:
            rolling_data = np.array(self.drift_buffer)
            rolling_means = np.mean(rolling_data, axis=0)
            
            # Baseline parameters
            baseline_centers = 0.5 * (self.original_min_vals + self.original_max_vals)
            baseline_ranges = 0.5 * (self.original_max_vals - self.original_min_vals)
            baseline_ranges[baseline_ranges == 0.0] = 1.0
            
            # Calculate mean Z-score deviation of voltage and active flow features (indices 0 to 45)
            z_scores = np.abs(rolling_means[0:45] - baseline_centers[0:45]) / baseline_ranges[0:45]
            self.concept_drift_score = float(np.mean(z_scores))
            
            self.concept_drift_alert = self.concept_drift_score > 2.0
            
            # Safe online adaptation hook: adapt normalization limits dynamically if drift is severe
            if self.concept_drift_score > 3.5:
                rolling_mins = np.min(rolling_data, axis=0)
                rolling_maxs = np.max(rolling_data, axis=0)
                # Expand limits smoothly
                self.min_vals = 0.95 * self.min_vals + 0.05 * rolling_mins
                self.max_vals = 0.95 * self.max_vals + 0.05 * rolling_maxs
                logger.warning(f"[ONLINE ADAPTATION] Concept drift score high ({self.concept_drift_score:.2f}). Dynamic scaling bounds updated.")

    def process_telemetry(self, telemetry, client):
        try:
            ts = telemetry.get("timestamp", int(time.time() * 1000))
            ts_sec = round(ts / 1000) * 1000
            
            # 1. Collect current actual telemetry values
            bus_voltages = []
            bus_angles = []
            bus_Ps = []
            bus_Qs = []
            for i in range(1, 10):
                bus_key = f"Bus_{i}"
                bus_data = telemetry["state"]["buses"][bus_key]
                bus_voltages.append(bus_data["voltage_pu"])
                bus_angles.append(bus_data["angle_rad"])
                bus_Ps.append(bus_data["P_mw"])
                bus_Qs.append(bus_data["Q_mvar"])
                
            line_Ps = []
            line_Qs = []
            line_Is = []
            for lid in self.line_ids:
                line_data = telemetry["state"]["lines"][lid]
                line_Ps.append(line_data["P_mw"])
                line_Qs.append(line_data["Q_mvar"])
                line_Is.append(line_data["current_pu"])
                
            breaker_states = []
            for lid in self.line_ids:
                status = telemetry["state"]["breakers"].get(lid, "CLOSED")
                breaker_states.append(1.0 if status == "CLOSED" else 0.0)
                
            attack_status = telemetry.get("attack_status", {})
            active_attack = attack_status.get("active_attack")
            attack_active = 1.0 if active_attack is not None else 0.0
            
            # Encode attack type
            fdia_active = 0.0
            replay_active = 0.0
            breaker_attack_active = 0.0
            attack_type = 0.0
            if active_attack:
                compromised = attack_status.get("compromised_nodes", {})
                if active_attack == "FDIA":
                    fdia_active = 1.0
                    attack_type = 1.0
                elif active_attack == "REPLAY":
                    replay_active = 1.0
                    attack_type = 2.0
                elif active_attack == "TRIP":
                    breaker_attack_active = 1.0
                    attack_type = 3.0
                elif active_attack == "SCENARIO":
                    for node, comp in compromised.items():
                        ctype = comp.get("type")
                        if ctype == "FDIA":
                            fdia_active = 1.0
                            attack_type = 1.0
                        elif ctype == "REPLAY":
                            replay_active = 1.0
                            attack_type = 2.0
                        elif ctype in ["BREAKER_MANIPULATION", "TRIP"]:
                            breaker_attack_active = 1.0
                            attack_type = 3.0
                        elif ctype == "DOS":
                            attack_type = 4.0
                        elif ctype == "SENSOR_SPOOFING":
                            attack_type = 5.0
                            
            row_data = [
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
            
            # --- DRIFT MONITORING ---
            self.monitor_concept_drift(row_data)
            
            # --- DRIFT AND ACCURACY CHECKING ---
            actual_voltages = np.array(bus_voltages, dtype=np.float32)
            if ts_sec in self.prediction_registry:
                registry_item = self.prediction_registry[ts_sec]
                if "10s" in registry_item:
                    mae = np.mean(np.abs(registry_item["10s"] - actual_voltages))
                    self.error_buffer_10.append(float(mae))
                if "30s" in registry_item:
                    mae = np.mean(np.abs(registry_item["30s"] - actual_voltages))
                    self.error_buffer_30.append(float(mae))
                if "60s" in registry_item:
                    mae = np.mean(np.abs(registry_item["60s"] - actual_voltages))
                    self.error_buffer_60.append(float(mae))
                    
            # Clean up prediction registry
            for k in list(self.prediction_registry.keys()):
                if k < ts_sec - 120000:
                    self.prediction_registry.pop(k, None)
                    
            # --- DEGRADED OBSERVABILITY / VOLTAGE RECONSTRUCTION ---
            trusted_voltages = list(bus_voltages)
            degraded_observability = False
            for idx in range(9):
                b_name = f"Bus_{idx + 1}"
                t_score = self.bus_trust.get(b_name, 100.0)
                if t_score < 60.0:
                    degraded_observability = True
                    rec_v = self.reconstruct_voltage(idx, trusted_voltages, line_Is, breaker_states)
                    trusted_voltages[idx] = rec_v
                    
            # Update row_data with reconstructed trusted state vector
            for idx in range(9):
                row_data[idx] = trusted_voltages[idx]
                
            self.history.append(row_data)
            
            if len(self.history) >= self.window_size:
                X_seq = np.array(self.history, dtype=np.float32)
                range_vals = self.max_vals - self.min_vals
                range_vals[range_vals == 0.0] = 1.0
                X_scaled = (X_seq - self.min_vals) / range_vals
                
                # Run inference on CPU
                tensor_input = torch.tensor(X_scaled, dtype=torch.float32).unsqueeze(0)
                
                start_time = time.time()
                with torch.no_grad():
                    out_10, out_30, out_60 = self.model(tensor_input)
                latency_ms = (time.time() - start_time) * 1000
                
                pred_10 = out_10.squeeze(0).numpy()
                pred_30 = out_30.squeeze(0).numpy()
                pred_60 = out_60.squeeze(0).numpy()
                
                horizons_data = {}
                np_breakers = np.array(breaker_states, dtype=np.float32)
                np_inj_P = np.array(bus_Ps, dtype=np.float32) / 100.0
                np_inj_Q = np.array(bus_Qs, dtype=np.float32) / 100.0
                
                overall_physics_confidence = []
                
                for h_name, pred_vec, prev_preds, err_buffer, base_conf, h_offset in [
                    ("10s", pred_10, self.prev_predictions_10, self.error_buffer_10, 0.98, 10),
                    ("30s", pred_30, self.prev_predictions_30, self.error_buffer_30, 0.90, 30),
                    ("60s", pred_60, self.prev_predictions_60, self.error_buffer_60, 0.80, 60)
                ]:
                    # Extract 38-dim outputs
                    V = pred_vec[0:9]
                    angles = pred_vec[9:18]
                    P = pred_vec[18:27]
                    Q = pred_vec[27:36]
                    cyber_logit = float(pred_vec[36])
                    uncertainty_logit = float(pred_vec[37])
                    
                    cyber_prob = float(1.0 / (1.0 + np.exp(-cyber_logit)))
                    pred_variance = float(np.exp(uncertainty_logit)) # sigma^2
                    pred_uncertainty_std = float(np.sqrt(pred_variance)) # sigma
                    
                    smoothed_V = []
                    for idx, v_val in enumerate(V):
                        if np.isnan(v_val) or np.isinf(v_val):
                            v_val = float(trusted_voltages[idx])
                        if idx not in prev_preds:
                            prev_preds[idx] = v_val
                        else:
                            v_val = prev_preds[idx] + 0.40 * (v_val - prev_preds[idx])
                            prev_preds[idx] = v_val
                        smoothed_V.append(v_val)
                    smoothed_V = np.array(smoothed_V, dtype=np.float32)
                    
                    # Compute physics metrics
                    kcl, kvl, dc_flow, topo, stab = self.calculate_physics_metrics(
                        smoothed_V, angles, P, Q, np_breakers, np_inj_P, np_inj_Q
                    )
                    
                    # Learned Physics-Informed Confidence Calibration
                    # Fuses historical drift error, predicted uncertainty variance, physics losses, and concept drift
                    mean_drift = float(np.mean(err_buffer)) if err_buffer else 0.0
                    
                    # Formulate penalties
                    drift_penalty = 2.0 * mean_drift
                    uncertainty_penalty = 0.5 * pred_uncertainty_std
                    physics_penalty = 0.8 * float(kcl + kvl + dc_flow)
                    concept_drift_penalty = 0.1 * self.concept_drift_score
                    
                    calibrated_conf = base_conf - drift_penalty - uncertainty_penalty - physics_penalty - concept_drift_penalty
                    calibrated_conf = max(0.30, min(0.99, float(calibrated_conf)))
                    
                    overall_physics_confidence.append(calibrated_conf)
                    
                    target_time = ts_sec + h_offset * 1000
                    if target_time not in self.prediction_registry:
                        self.prediction_registry[target_time] = {}
                    self.prediction_registry[target_time][h_name] = smoothed_V
                    
                    # Flag adversarial perturbations/stealth attacks when prediction variance is high 
                    # but cyber probability and physics mismatches align
                    adversarial_anomaly = bool(pred_uncertainty_std > 0.15 and cyber_prob >= 0.50)
                    
                    # Formulate structured explainability log for the HMI
                    if cyber_prob >= 0.70:
                        explain = f"Critical threat detected. Instability likely induced by active cyber tampering (cyber probability {cyber_prob*100:.1f}%)."
                    elif kcl > 0.02 or kvl > 0.02:
                        explain = f"Physics laws violated (KCL: {kcl:.4f}, KVL: {kvl:.4f}). High likelihood of false data injection (FDIA) sensor spoofing."
                    elif not topo:
                        explain = f"Breaker control conflict: prediction shows line flows crossing open line switches."
                    elif self.concept_drift_alert:
                        explain = f"Concept drift detected (score: {self.concept_drift_score:.2f}). Sensor measurements deviating from historical nominal statistics."
                    else:
                        explain = "Grid operates normally. Voltage and flow profiles satisfy physical conservation laws."
                        
                    horizons_data[h_name] = {
                        "voltages": [round(float(v), 4) for v in smoothed_V],
                        "angles": [round(float(a), 4) for a in angles],
                        "line_flows_p": [round(float(p * 100.0), 2) for p in P],
                        "line_flows_q": [round(float(q * 100.0), 2) for q in Q],
                        "cyber_instability_probability": round(cyber_prob, 4),
                        "confidence": round(calibrated_conf, 2),
                        "uncertainty_std": round(pred_uncertainty_std, 4),
                        "kcl_error": round(kcl, 6),
                        "kvl_error": round(kvl, 6),
                        "dc_flow_error": round(dc_flow, 6),
                        "topology_valid": topo,
                        "stability_valid": stab,
                        "adversarial_anomaly": adversarial_anomaly,
                        "explainability_log": explain
                    }
                    
                # Global physics confidence represents mean calibrated confidence across horizons
                global_phys_conf = float(np.mean(overall_physics_confidence))
                
                # --- PUBLISH COMPREHENSIVE FORWARD PINN PAYLOAD ---
                pinn_payload = {
                    "timestamp": ts,
                    "horizons": horizons_data,
                    "latency_ms": round(latency_ms, 2),
                    "concept_drift_score": round(self.concept_drift_score, 4),
                    "concept_drift_alert": self.concept_drift_alert,
                    "trusted_grid_state": [round(float(v), 4) for v in trusted_voltages],
                    "degraded_observability": degraded_observability,
                    "global_physics_confidence": round(global_phys_conf, 2)
                }
                client.publish("grid/pinn_forecast", json.dumps(pinn_payload))
                
                # --- BACKWARD COMPATIBLE PUBLISHES (10s HORIZON) ---
                h10 = horizons_data["10s"]
                bus5_actual = bus_voltages[4]
                bus5_predicted = h10["voltages"][4]
                pred_delta = bus5_predicted - bus5_actual
                if bus5_predicted < 0.85 or bus5_predicted > 1.15:
                    risk = "CRITICAL"
                elif (0.85 <= bus5_predicted < 0.90) or (1.10 < bus5_predicted <= 1.15):
                    risk = "HIGH"
                elif (0.90 <= bus5_predicted < 0.95) or (1.05 < bus5_predicted <= 1.10):
                    risk = "MEDIUM"
                else:
                    risk = "LOW"
                    
                client.publish("grid/ai_prediction", json.dumps({
                    "timestamp": ts,
                    "predicted_bus5_voltage": round(bus5_predicted, 4),
                    "actual_bus5_voltage": round(bus5_actual, 4),
                    "prediction_delta": round(pred_delta, 4),
                    "instability_risk": risk,
                    "confidence": h10["confidence"],
                    "forecast_horizon_seconds": 10
                }))
                
                target_bus_indices = [0, 2, 4, 6, 8]
                forecasts_multi = {}
                overall_status = "NORMAL"
                for idx_bus in target_bus_indices:
                    b_name = f"Bus_{idx_bus + 1}"
                    b_act = bus_voltages[idx_bus]
                    b_pred = h10["voltages"][idx_bus]
                    b_delta = b_pred - b_act
                    if b_pred < 0.85 or b_pred > 1.15:
                        b_status = "CRITICAL"
                        overall_status = "CRITICAL"
                    elif (0.85 <= b_pred < 0.95) or (1.05 < b_pred <= 1.15):
                        b_status = "WARNING"
                        if overall_status != "CRITICAL":
                            overall_status = "WARNING"
                    else:
                        b_status = "NORMAL"
                        
                    forecasts_multi[b_name] = {
                        "predicted": round(b_pred, 4),
                        "actual": round(b_act, 4),
                        "delta": round(b_delta, 4),
                        "status": b_status
                    }
                    
                client.publish("grid/ai_forecast_multi_bus", json.dumps({
                    "timestamp": ts,
                    "forecasts": forecasts_multi,
                    "overall_status": overall_status,
                    "confidence": h10["confidence"],
                    "forecast_horizon_seconds": 10
                }))
                
                threat_forecasts = {}
                for idx_bus in target_bus_indices:
                    b_name = f"Bus_{idx_bus + 1}"
                    threat_forecasts[b_name] = {
                        "predicted": round(h10["voltages"][idx_bus], 4),
                        "actual": round(bus_voltages[idx_bus], 4),
                        "delta": round(h10["voltages"][idx_bus] - bus_voltages[idx_bus], 4)
                    }
                    
                pred_cyber = h10["cyber_instability_probability"]
                if pred_cyber >= 0.70:
                    threat_status = "CYBER-CRITICAL"
                elif pred_cyber >= 0.30:
                    threat_status = "SUSPICIOUS"
                else:
                    threat_status = "NORMAL"
                    
                client.publish("grid/ai_threat_forecast", json.dumps({
                    "timestamp": ts,
                    "forecasts": threat_forecasts,
                    "cyber_instability_probability": round(pred_cyber, 4),
                    "status": threat_status,
                    "confidence": h10["confidence"],
                    "forecast_horizon_seconds": 10
                }))
                
                logger.info(
                    f"PINN Forecast computed | 10s Cyber Prob: {pred_cyber:.2f} | "
                    f"Drift: {self.concept_drift_score:.2f} | Latency: {latency_ms:.2f}ms"
                )
            else:
                logger.info(f"PINN sequence buffer warming up: {len(self.history)}/{self.window_size} frames.")
                
        except Exception as e:
            logger.error(f"Inference computation failure: {e}", exc_info=True)

engine = PinnInferenceEngine()

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info("PINN Inference Engine connected to MQTT!")
        client.subscribe("grid/telemetry")
        client.subscribe("grid/alerts")
        client.subscribe("grid/threat")
        client.subscribe("grid/config")
        client.subscribe("grid/control")
        client.subscribe("grid/trust_scores")
    else:
        logger.error(f"PINN Inference connection failed: rc {rc}")

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
            
        elif topic == "grid/trust_scores":
            engine.bus_trust = payload.get("bus_trust", engine.bus_trust)
            engine.line_trust = payload.get("line_trust", engine.line_trust)
            
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
                engine.bus_trust = {f"Bus_{i}": 100.0 for i in range(1, 10)}
                engine.line_trust = {lid: 100.0 for lid in engine.line_ids}
                engine.history.clear()
                engine.prediction_registry.clear()
                engine.error_buffer_10.clear()
                engine.error_buffer_30.clear()
                engine.error_buffer_60.clear()
                engine.prev_predictions_10.clear()
                engine.prev_predictions_30.clear()
                engine.prev_predictions_60.clear()
                engine.drift_buffer.clear()
                engine.concept_drift_score = 0.0
                engine.concept_drift_alert = False
                engine.min_vals = engine.original_min_vals.copy() if engine.original_min_vals is not None else None
                engine.max_vals = engine.original_max_vals.copy() if engine.original_max_vals is not None else None
                logger.info("PINN Inference Engine buffers and state caches reset.")
                
        elif topic == "grid/telemetry":
            engine.process_telemetry(payload, client)
            
    except Exception as e:
        logger.error(f"Error handling message on {msg.topic}: {e}")

if __name__ == "__main__":
    time.sleep(1)
    try:
        engine.load_model()
    except Exception as e:
        logger.error(f"Failed to initialize PINN Inference Engine: {e}")
        os._exit(1)
        
    import paho.mqtt.client as mqtt
    client = mqtt.Client(client_id="ai_pinn_inference_engine")
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
        client.loop_forever()
    except KeyboardInterrupt:
        logger.info("Stopping PINN Inference Engine...")
    except Exception as e:
        logger.error(f"MQTT loop failed: {e}")
        os._exit(1)
