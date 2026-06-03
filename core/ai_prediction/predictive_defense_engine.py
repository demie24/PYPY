import os
import sys
import time
import json
import logging
from collections import deque
import numpy as np
import paho.mqtt.client as mqtt

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ai_prediction.predictive_defense")

MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))

class PredictiveDefenseEngine:
    def __init__(self, history_len: int = 15):
        self.history_len = history_len
        
        # Stateful Caches for incoming data
        self.telemetry_history = deque(maxlen=history_len)
        self.threat_history = deque(maxlen=history_len)
        self.trust_history = deque(maxlen=history_len)
        self.alert_history = deque(maxlen=30)
        self.event_history = deque(maxlen=50)
        
        # Latest received payloads
        self.latest_telemetry = None
        self.latest_threat = None
        self.latest_trust = None
        self.latest_ai_threat_forecast = None
        self.latest_defense = None
        
        # Resilience & Ordering
        self.last_cycle_time = 0.0
        self.last_telemetry_timestamp = 0
        self.min_cycle_interval = 0.5  # Throttling limit (seconds)
        
        # Incident Memory Patterns
        self.attack_recurrence = {}      # target -> count of recent incidents
        self.failed_restorations = set()  # breaker_id/node -> failure count
        
        # Layout definition
        self.buses = [f"Bus_{i}" for i in range(1, 10)]
        self.lines = ["L1_4", "L2_7", "L3_9", "L4_5", "L4_9", "L5_6", "L6_7", "L7_8", "L8_9"]

    def handle_telemetry(self, payload: dict, client: mqtt.Client):
        """
        Processes incoming telemetry with ordering validation and throttling checks.
        """
        now = time.time()
        
        # 1. Telemetry Flood Throttling
        if now - self.last_cycle_time < self.min_cycle_interval:
            logger.debug("Telemetry frame discarded due to cycle throttling.")
            return

        # 2. Out-of-order Packet Discarding
        pkt_ts = payload.get("timestamp", 0)
        if pkt_ts <= self.last_telemetry_timestamp:
            logger.warning(f"Discarding out-of-order/duplicate telemetry packet (TS: {pkt_ts} <= Last: {self.last_telemetry_timestamp}).")
            return
            
        self.last_telemetry_timestamp = pkt_ts
        self.last_cycle_time = now
        self.latest_telemetry = payload
        
        self.telemetry_history.append(payload)
        
        # Execute centralized predictive fusion and publish results
        self.execute_fusion(client)

    def execute_fusion(self, client: mqtt.Client):
        """
        Core cross-layer intelligence aggregator and predictor.
        """
        if not self.latest_telemetry:
            return

        # 1. Run Memory Recurrence Analysis
        self.analyze_incident_memory()
        
        # 2. Evaluate Threat Escalation
        threat_forecast = self.forecast_threat_escalation()
        
        # 3. Pre-Attack Early Warning Engine
        pre_attack_alert = self.evaluate_pre_attack_patterns()
        
        # 4. Predictive Risk Scoring
        future_risk = self.compute_predictive_risk()
        
        # 5. Node/Line Trust Trend Forecasting
        trust_forecast = self.forecast_trust_degradation()
        
        # 6. Generate Preventive Advisory
        recommended_prevention = self.generate_preventive_advice(pre_attack_alert, future_risk)

        # 7. Publish All Predictive Telemetry Topics
        try:
            client.publish("prediction/threat_forecast", json.dumps(threat_forecast))
            client.publish("prediction/pre_attack_alert", json.dumps(pre_attack_alert))
            client.publish("prediction/future_risk", json.dumps(future_risk))
            client.publish("prediction/trust_forecast", json.dumps(trust_forecast))
            client.publish("prediction/escalation_probability", json.dumps({
                "timestamp": int(time.time() * 1000),
                "escalation_probability": threat_forecast.get("escalation_probability", 0.0),
                "target_severity": threat_forecast.get("projected_severity", "LOW"),
                "horizon_seconds": threat_forecast.get("forecast_horizon_seconds", 30)
            }))
            client.publish("prediction/recommended_prevention", json.dumps(recommended_prevention))
            
            logger.info(f"Published Predictive Intelligence Updates | Threat Escalation Prob: {threat_forecast['escalation_probability']:.2f}")
        except Exception as e:
            logger.error(f"Failed to publish predictive telemetry: {e}")

    def analyze_incident_memory(self):
        """
        Analyzes historical event patterns to learn recurrence indices.
        """
        self.attack_recurrence.clear()
        self.failed_restorations.clear()
        
        # Scan event history for repeated markers
        for ev in self.event_history:
            event_text = ev.get("event", "").upper()
            severity = ev.get("severity", "INFO")
            
            # Recurrent attacks
            if "ATTACK" in event_text or "COMPROMISED" in event_text:
                for node in self.buses + self.lines:
                    if node.upper() in event_text:
                        self.attack_recurrence[node] = self.attack_recurrence.get(node, 0) + 1
            
            # Restoration failures
            if "FAILED" in event_text and ("RESTORE" in event_text or "RECONNECT" in event_text):
                for asset in self.buses + self.lines:
                    if asset.upper() in event_text:
                        self.failed_restorations.add(asset)

    def forecast_threat_escalation(self) -> dict:
        """
        Fits linear trend line to threat scores and projects future escalation severity.
        """
        now_ms = int(time.time() * 1000)
        curr_threat = float(self.latest_threat.get("threat_score", 0.0)) if self.latest_threat else 0.0
        
        # 1. Fallback heuristic or linear regression
        if len(self.threat_history) >= 3:
            times = [t[0] for t in self.threat_history]
            scores = [t[1] for t in self.threat_history]
            
            # Normalize times to prevent overflow in fit
            x = np.array(times) - times[0]
            y = np.array(scores)
            
            # Simple linear regression (slope: change in threat score per second)
            if len(set(x)) > 1:
                slope, intercept = np.polyfit(x, y, 1)
            else:
                slope = 0.0
        else:
            slope = 0.0
            
        horizon = 30  # seconds
        projected_threat = max(0.0, min(100.0, curr_threat + slope * horizon))
        
        # Classify Projected Severity
        if projected_threat >= 76:
            proj_severity = "CRITICAL"
        elif projected_threat >= 51:
            proj_severity = "HIGH"
        elif projected_threat >= 26:
            proj_severity = "MEDIUM"
        else:
            proj_severity = "LOW"
            
        # Determine Escalation Probability
        # If score is rising, probability scales with how fast it reaches the next threshold
        escalation_prob = 0.0
        if slope > 0.01:
            margin = 0.0
            if curr_threat < 26:
                margin = 26 - curr_threat
            elif curr_threat < 51:
                margin = 51 - curr_threat
            elif curr_threat < 76:
                margin = 76 - curr_threat
            else:
                margin = 100 - curr_threat
                
            time_to_next = margin / slope if slope > 0 else 999
            if time_to_next < horizon:
                escalation_prob = float(min(0.99, 0.40 + 0.50 * (1.0 - time_to_next / horizon)))
            else:
                escalation_prob = float(min(0.39, slope * 2.0))
        elif curr_threat > 50:
            # Baseline probability for high threat environments
            escalation_prob = 0.15
            
        confidence = float(min(0.95, 0.50 + 0.03 * len(self.threat_history)))
        
        # Explainability mapping
        explanation_en = f"Threat score is currently {curr_threat:.0f}. "
        explanation_ms = f"Skor ancaman semasa adalah {curr_threat:.0f}. "
        if slope > 0.1:
            explanation_en += f"Rising rapidly at +{slope:.2f}/sec. Escalation is expected within the horizon."
            explanation_ms += f"Meningkat dengan cepat pada kadar +{slope:.2f}/saat. Eskalasi dijangka berlaku dalam masa terdekat."
        elif slope < -0.1:
            explanation_en += f"Declining at {slope:.2f}/sec due to active defense mitigations."
            explanation_ms += f"Menurun pada kadar {slope:.2f}/saat disebabkan oleh mitigasi pertahanan aktif."
        else:
            explanation_en += "Stable telemetry profile indicates low threat evolution rate."
            explanation_ms += "Profil telemetri yang stabil menunjukkan kadar evolusi ancaman yang rendah."

        return {
            "timestamp": now_ms,
            "current_threat_score": int(curr_threat),
            "projected_threat_score": round(projected_threat, 1),
            "projected_severity": proj_severity,
            "escalation_probability": round(escalation_prob, 2),
            "threat_slope": round(float(slope), 3),
            "forecast_horizon_seconds": horizon,
            "confidence": round(confidence, 2),
            "explainability": {
                "en": explanation_en,
                "ms": explanation_ms
            }
        }

    def evaluate_pre_attack_patterns(self) -> dict:
        """
        Early warning pattern recognition scanner.
        """
        now_ms = int(time.time() * 1000)
        likelihood = 0.0
        triggers = []
        
        # 1. Telemetry anomalies (slow voltage drifts or overload trends)
        buses = self.latest_telemetry.get("state", {}).get("buses", {})
        lines = self.latest_telemetry.get("state", {}).get("lines", {})
        
        volts_drift = 0
        for bus_name, bus_data in buses.items():
            v = bus_data.get("voltage_pu", 1.0)
            if v < 0.95 or v > 1.05:
                volts_drift += 1
                
        overload_trend = 0
        for line_id, line_data in lines.items():
            cap = line_data.get("capacity_pct", 0.0)
            if cap > 80.0:
                overload_trend += 1
                
        if volts_drift > 0:
            likelihood += 0.15
            triggers.append("TELEMETRY_VOLTAGE_DRIFT")
        if overload_trend > 0:
            likelihood += 0.15
            triggers.append("LINE_OVERLOAD_INDICATIONS")

        # 2. Repeated trust score degradations
        if self.latest_trust:
            details = self.latest_trust.get("details", {})
            low_trust_count = sum(1 for node, score in details.items() if score.get("trust_score", 100.0) < 70.0)
            if low_trust_count > 0:
                likelihood += min(0.30, 0.10 * low_trust_count)
                triggers.append("TRUST_SCORE_DEGRADATION")

        # 3. Repeated physics validation failures
        alerts_count = len([a for a in self.alert_history if "PHYSICS" in a.get("type", "").upper() or "KCL" in a.get("type", "").upper()])
        if alerts_count > 0:
            likelihood += min(0.25, 0.05 * alerts_count)
            triggers.append("PHYSICS_VALIDATION_FAILURES")

        # 4. Attack preparation indicators (rapid sequential telemetry alerts)
        compromised_nodes = self.latest_telemetry.get("attack_status", {}).get("compromised_nodes", {})
        if len(compromised_nodes) > 0:
            likelihood += 0.20
            triggers.append("COMPROMISED_CYBER_NODES")

        # 5. Suspension / Recurrence indicators
        recurrent_targets = [node for node, count in self.attack_recurrence.items() if count > 1]
        if recurrent_targets:
            likelihood += 0.15
            triggers.append("RECURRENT_TARGET_VULNERABILITY")

        # Cap likelihood
        warning_likelihood = min(0.99, likelihood)
        early_warning_active = warning_likelihood >= 0.40
        
        # Build explainability narratives
        explain_en = "Pre-attack markers detected: " + ", ".join(triggers) if triggers else "No pre-attack preparation patterns observed."
        explain_ms = "Petunjuk pra-serangan dikesan: " + ", ".join(triggers) if triggers else "Tiada corak penyediaan pra-serangan diperhatikan."

        return {
            "timestamp": now_ms,
            "early_warning_active": early_warning_active,
            "pre_attack_likelihood": round(warning_likelihood, 2),
            "active_indicators": triggers,
            "confidence": round(0.70 + 0.20 * (1.0 - abs(0.50 - warning_likelihood)), 2),
            "explainability": {
                "en": explain_en,
                "ms": explain_ms
            }
        }

    def compute_predictive_risk(self) -> dict:
        """
        Evaluates current vs 30s future risk profiles across grid domains.
        """
        now_ms = int(time.time() * 1000)
        
        # Base physical parameters
        buses = self.latest_telemetry.get("state", {}).get("buses", {})
        lines = self.latest_telemetry.get("state", {}).get("lines", {})
        
        # 1. Node Risk Score (Voltage deviations + Cyber anomaly probability)
        node_risk = {}
        for bus_name, bus_data in buses.items():
            v = bus_data.get("voltage_pu", 1.0)
            dev = abs(v - 1.0)
            base_risk = dev * 150.0  # 0.15 pu dev -> 22.5 risk
            
            # Inject cyber probability factor
            if self.latest_ai_threat_forecast:
                cyber_prob = self.latest_ai_threat_forecast.get("cyber_instability_probability", 0.0)
                # Shield hospital Bus_5
                weight = 2.0 if bus_name == "Bus_5" else 1.0
                base_risk += cyber_prob * 30.0 * weight
            node_risk[bus_name] = round(max(0.0, min(100.0, base_risk)), 1)
            
        # 2. Asset Risk Score (Lines)
        asset_risk = {}
        for line_id, line_data in lines.items():
            cap = line_data.get("capacity_pct", 0.0)
            base_risk = 0.0
            if cap > 80.0:
                base_risk = (cap - 80.0) * 3.0  # 110% -> 90 risk
            asset_risk[line_id] = round(max(0.0, min(100.0, base_risk)), 1)
            
        # 3. Topology Risk Score (Open breakers count)
        breakers = self.latest_telemetry.get("state", {}).get("breakers", {})
        open_count = sum(1 for status in breakers.values() if status == "OPEN")
        topology_risk = min(100.0, open_count * 20.0)
        
        # 4. Restoration Risk Score
        # Danger of restorations increases if lines are overloaded or memory indicates recurring failures
        restoration_risk = 10.0
        for asset, count in self.attack_recurrence.items():
            if asset in self.lines:
                restoration_risk += 15.0
        for asset in self.failed_restorations:
            restoration_risk += 30.0
        restoration_risk = min(100.0, restoration_risk)
        
        # 5. Cyber-Physical Instability Risk (PINN anomaly + cyber threat probability)
        phys_score = 0.0
        if self.latest_telemetry:
            # Check if physics validation score is present in nested layers
            phys_validation = self.latest_telemetry.get("physics_validation", {})
            phys_score = phys_validation.get("instability_score", 0.0)
            
        cyber_prob = 0.0
        if self.latest_ai_threat_forecast:
            cyber_prob = self.latest_ai_threat_forecast.get("cyber_instability_probability", 0.0)
            
        cyber_physical_risk = max(phys_score, cyber_prob * 100.0)
        
        # Future Risk Projection
        future_risk_factor = 1.05 if cyber_physical_risk > 40.0 else 0.98
        projected_cyber_physical = max(0.0, min(100.0, cyber_physical_risk * future_risk_factor))

        return {
            "timestamp": now_ms,
            "node_risk_scores": node_risk,
            "asset_risk_scores": asset_risk,
            "topology_risk_score": round(topology_risk, 1),
            "restoration_risk_score": round(restoration_risk, 1),
            "cyber_physical_instability_risk": {
                "current_risk": round(cyber_physical_risk, 1),
                "future_risk": round(projected_cyber_physical, 1),
                "projected_risk_horizon_seconds": 30
            }
        }

    def forecast_trust_degradation(self) -> dict:
        """
        Tracks trend of average node/line trust and forecasts degradation.
        """
        now_ms = int(time.time() * 1000)
        bus_trends = {}
        line_trends = {}
        
        if self.latest_trust:
            details = self.latest_trust.get("details", {})
            for b in self.buses:
                t = details.get(b, {}).get("trust_score", 100.0)
                # Trend analysis (simple derivative fallback based on history)
                slope = 0.0
                if len(self.trust_history) >= 2:
                    prev_t = self.trust_history[-1].get("details", {}).get(b, {}).get("trust_score", 100.0)
                    slope = t - prev_t
                bus_trends[b] = {
                    "current_trust": t,
                    "projected_trust_30s": max(0.0, min(100.0, t + slope * 30.0)),
                    "degradation_slope_per_sec": round(slope, 3)
                }
            for l in self.lines:
                t = details.get(l, {}).get("trust_score", 100.0)
                slope = 0.0
                if len(self.trust_history) >= 2:
                    prev_t = self.trust_history[-1].get("details", {}).get(l, {}).get("trust_score", 100.0)
                    slope = t - prev_t
                line_trends[l] = {
                    "current_trust": t,
                    "projected_trust_30s": max(0.0, min(100.0, t + slope * 30.0)),
                    "degradation_slope_per_sec": round(slope, 3)
                }
        else:
            # Fallback
            for b in self.buses:
                bus_trends[b] = {"current_trust": 100.0, "projected_trust_30s": 100.0, "degradation_slope_per_sec": 0.0}
            for l in self.lines:
                line_trends[l] = {"current_trust": 100.0, "projected_trust_30s": 100.0, "degradation_slope_per_sec": 0.0}

        return {
            "timestamp": now_ms,
            "bus_trust_trends": bus_trends,
            "line_trust_trends": line_trends
        }

    def generate_preventive_advice(self, early_warning: dict, risk: dict) -> list:
        """
        Creates actionable recommendations to prevent escalations before incidents occur.
        """
        recs = []
        cyber_physical = risk.get("cyber_physical_instability_risk", {}).get("current_risk", 0.0)
        warning_likelihood = early_warning.get("pre_attack_likelihood", 0.0)
        
        # 1. Raise trust thresholds / Increase validation frequency
        if warning_likelihood >= 0.30 or "TRUST_SCORE_DEGRADATION" in early_warning.get("active_indicators", []):
            recs.append({
                "action": "INCREASE_TELEMETRY_VALIDATION_FREQUENCY",
                "target": "SYSTEM",
                "rationale": "Trust scores are degrading or showing suspicious fluctuations. Elevating validation checks prevents data injection infiltration.",
                "rationale_ms": "Skor kebolehpercayaan merosot atau menunjukkan turun naik mencurigakan. Meningkatkan semakan pengesahan dapat menghalang penyusupan suntikan data.",
                "expected_benefits": "Rejects spoofed packages at the entry gateway and stabilizes anomaly detection inputs.",
                "confidence_level": 0.85,
                "risk_assessment": "LOW"
            })
            recs.append({
                "action": "RAISE_TRUST_THRESHOLDS",
                "target": "GATEWAY",
                "rationale": "High pre-attack likelihood indicates possible sensor spoofing preparation.",
                "rationale_ms": "Kebarangkalian pra-serangan yang tinggi menunjukkan kemungkinan penyediaan penipuan sensor.",
                "expected_benefits": "Quarantines anomalous SCADA telemetry feeds earlier.",
                "confidence_level": 0.80,
                "risk_assessment": "MEDIUM"
            })

        # 2. Isolate vulnerable nodes
        for bus_name, bus_risk in risk.get("node_risk_scores", {}).items():
            if bus_risk > 75.0:
                recs.append({
                    "action": "ISOLATE_VULNERABLE_NODE",
                    "target": bus_name,
                    "rationale": f"Bus {bus_name} risk index is {bus_risk}% due to voltage decay and/or cyber compromise indications.",
                    "rationale_ms": f"Indeks risiko Bas {bus_name} adalah {bus_risk}% disebabkan oleh kejatuhan voltan dan/atau tanda-tanda serangan siber.",
                    "expected_benefits": "Contains voltage collapse propagation to the adjacent digital twin network.",
                    "confidence_level": 0.90,
                    "risk_assessment": "HIGH"
                })

        # 3. Delay restorations
        rest_risk = risk.get("restoration_risk_score", 0.0)
        if rest_risk > 50.0:
            recs.append({
                "action": "DELAY_RISKY_RESTORATIONS",
                "target": "SYSTEM",
                "rationale": f"High restoration risk ({rest_risk}%) calculated due to recurrent incident history or active network stress.",
                "rationale_ms": f"Risiko pemulihan tinggi ({rest_risk}%) dikesan akibat sejarah insiden berulang atau tekanan grid aktif.",
                "expected_benefits": "Prevents reconnecting breakers onto unresolved physical faults.",
                "confidence_level": 0.95,
                "risk_assessment": "LOW"
            })

        # 4. Default proactive monitoring
        if len(recs) == 0:
            recs.append({
                "action": "INCREASE_MONITORING_INTENSITY",
                "target": "SYSTEM",
                "rationale": "Grid is operating under nominal conditions but proactive observation should remain active.",
                "rationale_ms": "Grid beroperasi dalam keadaan nominal tetapi pengawasan proaktif perlu kekal aktif.",
                "expected_benefits": "Ensures early anomalies are caught immediately at the tick boundary.",
                "confidence_level": 0.99,
                "risk_assessment": "LOW"
            })

        return recs

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info("Predictive Defense Engine connected to MQTT!")
            # Subscriptions
            client.subscribe("grid/telemetry")
            client.subscribe("grid/threat")
            client.subscribe("grid/trust_scores")
            client.subscribe("grid/ai_threat_forecast")
            client.subscribe("grid/defense")
            client.subscribe("grid/events")
            client.subscribe("grid/alerts")
        else:
            logger.error(f"Predictive Engine connection failed: rc {rc}")

    def on_message(self, client, userdata, msg):
        try:
            topic = msg.topic
            payload = json.loads(msg.payload.decode("utf-8"))
            
            if topic == "grid/telemetry":
                self.handle_telemetry(payload, client)
            elif topic == "grid/threat":
                self.latest_threat = payload
                self.threat_history.append((time.time(), float(payload.get("threat_score", 0.0))))
            elif topic == "grid/trust_scores":
                self.latest_trust = payload
                self.trust_history.append(payload)
            elif topic == "grid/ai_threat_forecast":
                self.latest_ai_threat_forecast = payload
            elif topic == "grid/defense":
                self.latest_defense = payload
            elif topic == "grid/events":
                self.event_history.append(payload)
            elif topic == "grid/alerts":
                self.alert_history.append(payload)
                
        except Exception as e:
            logger.error(f"Error handling message on {msg.topic}: {e}")

if __name__ == "__main__":
    engine = PredictiveDefenseEngine()
    
    client = mqtt.Client(client_id="predictive_defense_engine")
    client.on_connect = engine.on_connect
    client.on_message = engine.on_message
    
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
        client.loop_forever()
    except KeyboardInterrupt:
        logger.info("Stopping Predictive Defense Engine...")
    except Exception as e:
        logger.error(f"MQTT Loop Error: {e}")
        sys.exit(1)
