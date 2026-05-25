import os
import time
import json
import logging
import paho.mqtt.client as mqtt

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("threat_engine.scorer")

MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))

class ThreatScoringEngine:
    def __init__(self):
        self.flisr_state = "NORMAL"
        self.flisr_auto = True
        self.recent_alerts = []  # List of tuples: (timestamp, alert_dict)
        self.alert_expiry_seconds = 30.0
        
        # Recommendations state
        self.recommendations = []
        # Cooldown tracking for autonomous actions: (action, target) -> timestamp
        self.action_cooldowns = {}
        self.cooldown_period = 30.0  # seconds
        
        # Auto-defense enablement switch (can be toggled via control messages)
        self.auto_defense_enabled = False

    def add_alert(self, alert):
        now = time.time()
        self.recent_alerts.append((now, alert))
        # Keep list pruned
        self.prune_alerts()

    def prune_alerts(self):
        now = time.time()
        self.recent_alerts = [a for a in self.recent_alerts if now - a[0] < self.alert_expiry_seconds]

    def update_flisr_config(self, payload):
        if "flisr_state" in payload:
            self.flisr_state = payload["flisr_state"]
        if "flisr_auto" in payload:
            self.flisr_auto = payload["flisr_auto"]

    def calculate_threat(self, telemetry):
        self.prune_alerts()
        now = time.time()

        # 1. Extract physical grid state
        buses = telemetry.get("state", {}).get("buses", {})
        lines = telemetry.get("state", {}).get("lines", {})
        breakers = telemetry.get("state", {}).get("breakers", {})
        attack_status = telemetry.get("attack_status", {})

        # Calculate voltage deviations
        max_voltage_dev = 0.0
        worst_bus = None
        for bus_name, bus_data in buses.items():
            V = bus_data.get("voltage_pu", 1.0)
            dev = abs(V - 1.0)
            if dev > max_voltage_dev:
                max_voltage_dev = dev
                worst_bus = bus_name

        # Calculate line capacities and overloads
        max_capacity_pct = 0.0
        num_overloaded_lines = 0
        worst_line = None
        for line_id, line_data in lines.items():
            cap = line_data.get("capacity_pct", 0.0)
            if cap > max_capacity_pct:
                max_capacity_pct = cap
                worst_line = line_id
            if cap > 100.0:
                num_overloaded_lines += 1

        # Count tripped/open breakers (excluding L7_8 Normally Open tie-line)
        num_open_breakers = 0
        for breaker_id, status in breakers.items():
            if breaker_id != "L7_8" and status == "OPEN":
                num_open_breakers += 1

        # 2. Extract cyber attack state
        active_attack = attack_status.get("active_attack")
        compromised_nodes = attack_status.get("compromised_nodes", {})
        num_compromised = len(compromised_nodes)

        # Find highest severity recent AI alert
        max_alert_severity = None
        for ts, alert in self.recent_alerts:
            sev = alert.get("severity")
            if sev == "CRITICAL":
                max_alert_severity = "CRITICAL"
            elif sev == "HIGH" and max_alert_severity != "CRITICAL":
                max_alert_severity = "HIGH"
            elif sev == "WARNING" and max_alert_severity not in ["CRITICAL", "HIGH"]:
                max_alert_severity = "WARNING"

        # 3. Calculate Threat Score (0 - 100)
        score = 0
        
        # Cyber components
        if active_attack:
            score += 35
        score += min(45, 15 * num_compromised)
        
        if max_alert_severity == "CRITICAL":
            score += 15
        elif max_alert_severity == "HIGH":
            score += 10
        elif max_alert_severity == "WARNING":
            score += 5

        # Physical components
        score += min(30, 10 * num_open_breakers)

        if max_voltage_dev > 0.15:
            score += 30
        elif max_voltage_dev > 0.10:
            score += 20
        elif max_voltage_dev > 0.05:
            score += 10

        if max_capacity_pct > 120.0:
            score += 30
        elif max_capacity_pct > 100.0:
            score += 20
        elif max_capacity_pct > 80.0:
            score += 10

        # Remediation offset (reducing threat level when FLISR is actively correcting)
        if self.flisr_state == "RESTORED":
            score -= 15
        elif self.flisr_state in ["RESTORATION", "ISOLATION"]:
            score -= 10

        threat_score = max(0, min(100, score))

        # 4. Severity Level
        if threat_score >= 76:
            severity = "CRITICAL"
        elif threat_score >= 51:
            severity = "HIGH"
        elif threat_score >= 26:
            severity = "MODERATE"
        else:
            severity = "LOW"

        # 5. Confidence Score (0.0 to 1.0)
        confidence = 0.50
        if active_attack:
            confidence += 0.20
        if self.recent_alerts:
            confidence += 0.15
        if max_voltage_dev > 0.05 or max_capacity_pct > 90.0:
            confidence += 0.15
            
        # Nominal default
        if not active_attack and not self.recent_alerts and max_voltage_dev <= 0.02 and max_capacity_pct <= 70.0:
            confidence = 0.99
            
        confidence = round(max(0.0, min(1.0, confidence)), 2)

        # 6. Cascade Probability (0.0 to 1.0)
        if num_overloaded_lines > 0:
            cascade_probability = 0.2 + 0.3 * num_overloaded_lines + 0.4 * max_voltage_dev
        else:
            cascade_probability = 1.5 * max_voltage_dev
            
        if num_open_breakers > 0 and num_overloaded_lines > 0:
            cascade_probability += 0.15
            
        cascade_probability = round(max(0.0, min(1.0, cascade_probability)), 2)

        # 7. Propagation Risk (LOW, MEDIUM, HIGH)
        if threat_score >= 70 or num_overloaded_lines > 0:
            propagation_risk = "HIGH"
        elif threat_score >= 40 or max_capacity_pct > 80.0:
            propagation_risk = "MEDIUM"
        else:
            propagation_risk = "LOW"

        # 8. Compile Affected Nodes list
        affected = set()
        for node in compromised_nodes.keys():
            affected.add(node)
        for b_id, status in breakers.items():
            if status == "OPEN":
                affected.add(b_id)
        for line_id, line_data in lines.items():
            if line_data.get("capacity_pct", 0.0) > 100.0:
                affected.add(line_id)
        for bus_name, bus_data in buses.items():
            if abs(bus_data.get("voltage_pu", 1.0) - 1.0) > 0.08:
                affected.add(bus_name)
        affected_nodes = sorted(list(affected))

        # 9. Generate recommendations
        recommendations = []
        
        # Recommendation A: Reject Telemetry due to cyber anomaly
        for ts, alert in self.recent_alerts:
            suspect = alert.get("suspect_node")
            alert_type = alert.get("type")
            if suspect and alert_type in ["TARGETED_FDIA", "SENSOR_ANOMALY"]:
                recommendations.append({
                    "action": "REJECT_TELEMETRY",
                    "target": suspect,
                    "priority": "HIGH",
                    "msg": f"Reject telemetry feed from {suspect} due to suspect cyber {alert_type} signature."
                })
                break # suggest one target at a time

        # Recommendation B: Isolate Line due to critical thermal overload
        for line_id, line_data in lines.items():
            cap = line_data.get("capacity_pct", 0.0)
            if cap > 105.0 and breakers.get(line_id) == "CLOSED":
                recommendations.append({
                    "action": "ISOLATE_LINE",
                    "target": line_id,
                    "priority": "CRITICAL" if cap > 120.0 else "HIGH",
                    "msg": f"Open breaker on {line_id} to isolate line and halt thermal cascade propagation."
                })

        # Recommendation C: Activate Islanding
        if active_attack == "SCENARIO" and max_voltage_dev > 0.12 and worst_bus:
            recommendations.append({
                "action": "ACTIVATE_ISLANDING",
                "target": worst_bus,
                "priority": "CRITICAL",
                "msg": f"De-couple sector via islanding at {worst_bus} to contain voltage instability cascade."
            })

        # Recommendation D: Engage FLISR
        if num_open_breakers > 0 and self.flisr_state == "NORMAL" and not self.flisr_auto:
            recommendations.append({
                "action": "ENGAGE_FLISR",
                "target": "SYSTEM",
                "priority": "MEDIUM",
                "msg": "Enable FLISR auto-healing algorithms to execute grid reconfiguration sequence."
            })

        # Filter out duplicate recommendations to prevent UI flickering or command flooding
        # Deduplicate based on action and target
        deduped_recs = []
        seen_recs = set()
        for rec in recommendations:
            key = (rec["action"], rec["target"])
            if key not in seen_recs:
                seen_recs.add(key)
                deduped_recs.append(rec)
        
        self.recommendations = deduped_recs

        return {
            "timestamp": int(now * 1000),
            "threat_score": int(threat_score),
            "severity": severity,
            "confidence": confidence,
            "cascade_probability": cascade_probability,
            "affected_node_count": len(affected_nodes),
            "affected_nodes": affected_nodes,
            "propagation_risk": propagation_risk,
            "recommendations": self.recommendations,
            "auto_defense_active": self.auto_defense_enabled
        }

    def execute_autonomous_defense(self, threat_data, client):
        """
        If auto-defense mode is active, automatically publish control actions to grid/control.
        Includes a 30s cooldown guard to avoid redundant/oscillatory commands.
        """
        if not self.auto_defense_enabled:
            return

        now = time.time()
        for rec in threat_data.get("recommendations", []):
            action = rec["action"]
            target = rec["target"]
            key = (action, target)

            # Check cooldown
            last_triggered = self.action_cooldowns.get(key, 0.0)
            if now - last_triggered < self.cooldown_period:
                continue

            # Execute action
            logger.info(f"[AUTONOMOUS ACTION] Executing {action} on {target}")
            self.action_cooldowns[key] = now

            if action == "ISOLATE_LINE":
                payload = {"command": "OPEN", "target": target}
                client.publish("grid/control", json.dumps(payload))
                
                # Log event
                event = {
                    "timestamp": int(now * 1000),
                    "source": "AUTO_DEFENSE",
                    "event": f"Autonomous Action: Tripped breaker on overloaded line {target} to stop cascade.",
                    "severity": "CRITICAL"
                }
                client.publish("grid/events", json.dumps(event))

            elif action == "ENGAGE_FLISR":
                payload = {"flisr_auto": True}
                client.publish("grid/config", json.dumps(payload))
                
                event = {
                    "timestamp": int(now * 1000),
                    "source": "AUTO_DEFENSE",
                    "event": "Autonomous Action: Re-enabled FLISR automatic healing mode.",
                    "severity": "INFO"
                }
                client.publish("grid/events", json.dumps(event))

            elif action == "REJECT_TELEMETRY":
                # Simulated mitigation: publish event representing telemetry rejection
                event = {
                    "timestamp": int(now * 1000),
                    "source": "AUTO_DEFENSE",
                    "event": f"Autonomous Action: Terminated untrusted telemetry channel from {target}.",
                    "severity": "WARNING"
                }
                client.publish("grid/events", json.dumps(event))

            elif action == "ACTIVATE_ISLANDING":
                # Isolate target bus by opening connected lines
                payload = {"command": "OPEN", "target": target}
                client.publish("grid/control", json.dumps(payload))
                
                event = {
                    "timestamp": int(now * 1000),
                    "source": "AUTO_DEFENSE",
                    "event": f"Autonomous Action: Isolated unstable sector at {target} (islanding).",
                    "severity": "CRITICAL"
                }
                client.publish("grid/events", json.dumps(event))

threat_engine = ThreatScoringEngine()

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info("Threat Scoring Engine connected to MQTT!")
        client.subscribe("grid/telemetry")
        client.subscribe("grid/alerts")
        client.subscribe("grid/config")
        client.subscribe("grid/control")
    else:
        logger.error(f"Threat Engine connection failed: rc {rc}")

def on_message(client, userdata, msg):
    try:
        topic = msg.topic
        payload = json.loads(msg.payload.decode("utf-8"))

        if topic == "grid/alerts":
            threat_engine.add_alert(payload)

        elif topic == "grid/config":
            threat_engine.update_flisr_config(payload)

        elif topic == "grid/control":
            cmd = payload.get("command")
            target = payload.get("target")
            if cmd == "RESET_ALARMS":
                threat_engine.recent_alerts.clear()
                threat_engine.action_cooldowns.clear()
                logger.info("Threat Engine alerts and cooldown history cleared.")
            elif cmd == "TOGGLE_AUTO_DEFENSE":
                threat_engine.auto_defense_enabled = bool(payload.get("enabled", False))
                logger.info(f"Threat Engine Auto-Defense Mode set to: {threat_engine.auto_defense_enabled}")
                # Log event
                event = {
                    "timestamp": int(time.time() * 1000),
                    "source": "AUTO_DEFENSE",
                    "event": f"Operator set Auto-Defense System Mode to: {'ENABLED' if threat_engine.auto_defense_enabled else 'DISABLED'}",
                    "severity": "INFO"
                }
                client.publish("grid/events", json.dumps(event))

        elif topic == "grid/telemetry":
            threat_data = threat_engine.calculate_threat(payload)
            
            # Publish calculated threat telemetry
            client.publish("grid/threat", json.dumps(threat_data))
            
            # Evaluate autonomous defense actions
            threat_engine.execute_autonomous_defense(threat_data, client)

    except Exception as e:
        logger.error(f"Error processing message in Threat Scorer on {msg.topic}: {e}")

if __name__ == "__main__":
    client = mqtt.Client(client_id="threat_scoring_engine")
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
        client.loop_forever()
    except KeyboardInterrupt:
        logger.info("Stopping Threat Scoring Engine...")
    except Exception as e:
        logger.error(f"MQTT Loop Error: {e}")
        os._exit(1)
