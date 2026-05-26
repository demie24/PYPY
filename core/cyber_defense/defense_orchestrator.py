import os
import sys
import json
import time
import logging
import threading
import paho.mqtt.client as mqtt

# Add directory to sys.path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(CURRENT_DIR)

from autonomous_defense_coordinator import AutonomousDefenseCoordinator
from adaptive_defense_engine import AdaptiveDefenseEngine
from campaign_response_engine import CampaignResponseEngine
from defense_escalation import DefenseEscalator
from defense_memory import DefenseMemory
from containment_engine import ContainmentEngine
from campaign_timeline import CampaignTimeline

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("cyber_defense.orchestrator")

MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))

class DefenseOrchestrator:
    def __init__(self):
        self.coordinator = AutonomousDefenseCoordinator()
        self.adaptive = AdaptiveDefenseEngine()
        self.campaign = CampaignResponseEngine()
        self.escalator = DefenseEscalator()
        self.memory = DefenseMemory()
        self.containment = ContainmentEngine()
        self.timeline = CampaignTimeline()

        # Shared data caches (MQTT inputs)
        self.latest_telemetry = {}
        self.latest_threat = {}
        self.latest_pinn = {}
        self.latest_physics_val = {}
        self.latest_trust = {}
        
        self.pending_alerts = []
        self.pending_events = []
        self.lock = threading.Lock()
        
        # Initialize timeline startup event
        self.timeline.record(
            "SYSTEM_STARTUP", 
            "Autonomous Cyber Defense Orchestrator daemon initialized. Listening to SCADA layers..."
        )

    def cache_alert(self, alert: dict):
        with self.lock:
            self.pending_alerts.append(alert)
            # Record in memory
            target = alert.get("suspect_node") or alert.get("target") or "SYSTEM"
            atk_type = alert.get("type", "UNKNOWN")
            severity = 50.0
            if alert.get("severity") == "CRITICAL":
                severity = 90.0
            elif alert.get("severity") == "HIGH":
                severity = 70.0
            self.memory.record_attack(target, atk_type, severity)
            
            # Record in timeline
            self.timeline.record(
                "ATTACK_DETECTED",
                f"Intrusion alert: [{atk_type}] targeting {target} (Severity: {alert.get('severity', 'LOW')})",
                details=alert
            )

    def cache_event(self, event: dict):
        with self.lock:
            self.pending_events.append(event)
            event_str = event.get("event", "")
            source = event.get("source", "SYSTEM")
            
            # Pattern match to extract security actions in memory and timeline
            if "rollback" in event_str.lower():
                self.memory.record_rollback(event, reason=event_str)
                self.timeline.record("ROLLBACK_TRIGGERED", f"State rollback detected: {event_str}", details=event)
            elif "failed" in event_str.lower() and ("restor" in event_str.lower() or "heal" in event_str.lower()):
                self.memory.record_failed_restoration(source, reason=event_str)
                self.timeline.record("RESTORATION_FAILED", f"Restoration failure: {event_str}", details=event)
            elif "compromise" in event_str.lower() or "compromised" in event_str.lower():
                self.memory.record_attack(source, "COMPROMISE", 80.0)
                self.timeline.record("COMPROMISE_EVENT", f"Node compromised: {event_str}", details=event)
            elif "restored" in event_str.lower():
                self.timeline.record("RESTORATION_SUCCESS", f"Node restoration successful: {event_str}", details=event)

    def run_tick(self, mqtt_client):
        """
        Executes one loop of the 1.0 Hz orchestrator lifecycle.
        """
        with self.lock:
            # Capture inputs
            telemetry = self.latest_telemetry.copy()
            threat_data = self.latest_threat.copy()
            trust_scores = self.latest_trust.copy()
            pinn_forecast = self.latest_pinn.copy()
            physics_val = self.latest_physics_val.copy()
            
            alerts = self.pending_alerts.copy()
            events = self.pending_events.copy()
            self.pending_alerts.clear()
            self.pending_events.clear()

        # Check for system reset controls
        # (Already listened to on grid/control via reset, but we can do a local check too)
        
        # 1. Update Adaptive Defense Engine
        adaptive_report = self.adaptive.update_and_adapt(telemetry, alerts, trust_scores)
        
        # 2. Analyze Campaigns
        campaign_report = self.campaign.analyze_campaigns(alerts, events)
        
        # 3. Evaluate Escalation Mode
        threat_score = threat_data.get("threat_score", 0)
        campaign_severity = campaign_report["campaign_severity_score"]
        physics_anomaly = physics_val.get("physics_anomaly_score", 0.0)
        pinn_confidence = pinn_forecast.get("global_physics_confidence", 100.0) / 100.0
        
        # Extract islanding state
        islanding = False
        if telemetry and "state" in telemetry and "buses" in telemetry["state"]:
            islanding = any(float(b.get("voltage_pu", 1.0)) < 0.20 for b in telemetry["state"]["buses"].values())
            
        stability_score = 100.0 - physics_anomaly
        
        escalator_report = self.escalator.evaluate_escalation(
            threat_score=threat_score,
            campaign_severity=campaign_severity,
            physics_anomaly=physics_anomaly,
            pinn_confidence=pinn_confidence,
            islanding_active=islanding,
            stability_score=stability_score
        )
        
        # Update timeline for escalation transitions
        prev_level = self.escalator.current_level
        
        # 4. Coordinate Defense Actions
        coordinator_report = self.coordinator.coordinate(
            telemetry=telemetry,
            threat_data=threat_data,
            trust_scores=trust_scores,
            pinn_forecast=pinn_forecast,
            physics_val=physics_val,
            escalation_level=escalator_report["escalation_level"]
        )
        
        # 5. Dispatch Containment Actions
        dispatched_logs = self.containment.dispatch_containment(coordinator_report, mqtt_client)
        for log in dispatched_logs:
            self.memory.record_containment(
                action=log["action"], 
                target=log["target"], 
                success=True, 
                reason=log["reason"]
            )
            self.timeline.record(
                "CONTAINMENT_DISPATCHED",
                f"Dispatched {log['action']} containment on {log['target']}: {log['message']}",
                details=log
            )

        # 6. Retrieve Memory Summary
        memory_report = self.memory.get_summary()
        
        # 7. Package and Publish Unified State Array
        payload = {
            "timestamp": int(time.time() * 1000),
            
            # Escalation level details
            "escalation_level": escalator_report["escalation_level"],
            "operator_authority": escalator_report["operator_authority"],
            "rl_permissions": escalator_report["rl_permissions"],
            "restoration_permissions": escalator_report["restoration_permissions"],
            "containment_aggressiveness": escalator_report["containment_aggressiveness"],
            "telemetry_trust_threshold": escalator_report["telemetry_trust_threshold"],
            "rollback_restrictions": escalator_report["rollback_restrictions"],
            
            # Coordination strategies
            "strategies": coordinator_report["strategies"],
            "recommended_defense_actions": coordinator_report["recommended_defense_actions"],
            "restoration_lockdown_active": coordinator_report["restoration_lockdown_active"],
            "breaker_lockdown_targets": coordinator_report["breaker_lockdown_targets"],
            
            # Campaign tracks
            "campaign_detected": campaign_report["campaign_detected"],
            "campaign_severity_score": campaign_report["campaign_severity_score"],
            "containment_strategy": campaign_report["containment_strategy"],
            "trusted_operational_mode": campaign_report["trusted_operational_mode"],
            "active_campaigns": campaign_report["active_campaigns"],
            "active_campaign_types": campaign_report["active_campaign_types"],
            
            # Adaptive thresholds
            "adaptive_trust_threshold": adaptive_report["adaptive_trust_threshold"],
            "trust_penalty_multiplier": adaptive_report["trust_penalty_multiplier"],
            "filtering_smoothing_alpha": adaptive_report["filtering_smoothing_alpha"],
            "containment_severity_multiplier": adaptive_report["containment_severity_multiplier"],
            "next_attack_window_prediction_seconds": adaptive_report["next_attack_window_prediction_seconds"],
            "repeated_attack_detected": adaptive_report["repeated_attack_detected"],
            
            # Memory state
            "defense_confidence_score": memory_report["defense_confidence_score"],
            "repeated_attacker_detected": memory_report["repeated_attacker_detected"],
            "total_attacks_recorded": memory_report["total_attacks_recorded"],
            "total_containments_recorded": memory_report["total_containments_recorded"],
            "total_rollbacks_recorded": memory_report["total_rollbacks_recorded"],
            "total_failed_restorations": memory_report["total_failed_restorations"],
            
            # Chronological timeline and containment status lists
            "timeline_events": self.timeline.get_events()[-30:],  # Limit to 30 for MQTT size
            "containment_status": self.containment.get_status()
        }
        
        # Publish
        mqtt_client.publish("grid/defense", json.dumps(payload))
        logger.info(f"Published Defense Orchestration update. Escalation: {payload['escalation_level']} | Active Containments: {len(payload['containment_status']['active_containments'])}")

    def handle_reset(self, mqtt_client):
        self.containment.reset(mqtt_client)
        self.memory = DefenseMemory()
        self.timeline.clear()
        self.adaptive = AdaptiveDefenseEngine()
        self.campaign = CampaignResponseEngine()
        self.escalator = DefenseEscalator()
        
        self.timeline.record(
            "SYSTEM_RESET", 
            "Autonomous Cyber Defense states reset by operator command."
        )
        logger.info("Defense Orchestrator state fully reset.")

# Global handler functions
orchestrator = DefenseOrchestrator()

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info("Defense Orchestrator connected to MQTT broker successfully!")
        client.subscribe("grid/telemetry")
        client.subscribe("grid/alerts")
        client.subscribe("grid/events")
        client.subscribe("grid/threat")
        client.subscribe("grid/pinn_forecast")
        client.subscribe("grid/physics_validation")
        client.subscribe("grid/trust_scores")
        client.subscribe("grid/control")
    else:
        logger.error(f"MQTT connection failed with code {rc}")

def on_message(client, userdata, msg):
    try:
        topic = msg.topic
        payload = json.loads(msg.payload.decode("utf-8"))
        
        if topic == "grid/telemetry":
            with orchestrator.lock:
                orchestrator.latest_telemetry = payload
        elif topic == "grid/alerts":
            orchestrator.cache_alert(payload)
        elif topic == "grid/events":
            orchestrator.cache_event(payload)
        elif topic == "grid/threat":
            with orchestrator.lock:
                orchestrator.latest_threat = payload
        elif topic == "grid/pinn_forecast":
            with orchestrator.lock:
                orchestrator.latest_pinn = payload
        elif topic == "grid/physics_validation":
            with orchestrator.lock:
                orchestrator.latest_physics_val = payload
        elif topic == "grid/trust_scores":
            with orchestrator.lock:
                orchestrator.latest_trust = payload
        elif topic == "grid/control":
            cmd = payload.get("command")
            if cmd == "RESET_ALARMS":
                orchestrator.handle_reset(client)
    except Exception as e:
        logger.error(f"Error handling message on {msg.topic}: {e}")

def main():
    client = mqtt.Client(client_id="smart_grid_cyber_defense_orchestrator")
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
        client.loop_start()
    except Exception as e:
        logger.error(f"Failed to connect to MQTT broker: {e}")
        time.sleep(5)
        sys.exit(1)
        
    logger.info("Autonomous Cyber Defense Orchestrator started. Running at 1.0Hz loop rate...")
    
    # 1.0 Hz Execution Loop
    while True:
        try:
            start_time = time.time()
            orchestrator.run_tick(client)
            elapsed = time.time() - start_time
            sleep_time = max(0.1, 1.0 - elapsed)
            time.sleep(sleep_time)
        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.error(f"Error in orchestrator tick: {e}", exc_info=True)
            time.sleep(1.0)
            
    client.loop_stop()
    client.disconnect()

if __name__ == "__main__":
    main()
