import os
import json
import time
import logging
import paho.mqtt.client as mqtt
from relay import ProtectiveRelay
from flisr import FLISREngine

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("self_healing.main")

MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))

# Instantiate modules
relay = ProtectiveRelay()
flisr = FLISREngine()

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info("Self-Healing Subsystem connected to MQTT!")
        client.subscribe("grid/telemetry")
        client.subscribe("grid/events")
        client.subscribe("grid/control")
        client.subscribe("grid/config")
    else:
        logger.error(f"MQTT Connection failed with code {rc}")

def on_message(client, userdata, msg):
    try:
        topic = msg.topic
        payload = json.loads(msg.payload.decode("utf-8"))

        if topic == "grid/telemetry":
            # 1. Evaluate protective relay tripping rules (ANSI 50/51, 27)
            relay_commands = relay.evaluate_telemetry(payload)
            for cmd in relay_commands:
                # Send breaker trip command to grid/control
                control_payload = {
                    "command": cmd["command"],
                    "target": cmd["target"]
                }
                client.publish("grid/control", json.dumps(control_payload))
                
                # Publish trip alert event log
                client.publish("grid/events", json.dumps(cmd["event_log"]))
                
                # Publish cyber alarm warning if security threat is suspected
                alarm_payload = {
                    "timestamp": int(time.time() * 1000),
                    "type": "BREAKER_TRIP",
                    "severity": "CRITICAL",
                    "suspect_node": cmd["target"],
                    "msg": f"Breaker {cmd['target']} was tripped by Relay Protection due to threshold breach."
                }
                client.publish("grid/alerts", json.dumps(alarm_payload))

            # Track FLISR state before executing healing cycle
            prev_state = flisr.state
            prev_isolated = list(flisr.isolated_faults)
            prev_reconfigured = list(flisr.reconfigured_breakers)

            # 2. Run FLISR Self-Healing calculation loop
            flisr_commands = flisr.execute_healing_cycle(payload)
            for cmd in flisr_commands:
                # Send reconfiguration action (e.g. closing tie-breaker)
                control_payload = {
                    "command": cmd["command"],
                    "target": cmd["target"]
                }
                client.publish("grid/control", json.dumps(control_payload))
                
                # Publish restoration event log
                client.publish("grid/events", json.dumps(cmd["event_log"]))

            # Broadcast FLISR state if any changes occurred
            if (flisr.state != prev_state or 
                flisr.isolated_faults != prev_isolated or 
                flisr.reconfigured_breakers != prev_reconfigured):
                config_update = {
                    "flisr_state": flisr.state,
                    "flisr_isolated_faults": flisr.isolated_faults,
                    "flisr_reconfigured_breakers": flisr.reconfigured_breakers,
                    "flisr_tripped_by_relay": flisr.tripped_by_relay
                }
                client.publish("grid/config", json.dumps(config_update))

        elif topic == "grid/events":
            prev_state = flisr.state
            # Pass events into FLISR to track breaker trips and start healing state machine
            flisr.process_event(payload)
            if flisr.state != prev_state:
                config_update = {
                    "flisr_state": flisr.state,
                    "flisr_isolated_faults": flisr.isolated_faults,
                    "flisr_reconfigured_breakers": flisr.reconfigured_breakers,
                    "flisr_tripped_by_relay": flisr.tripped_by_relay
                }
                client.publish("grid/config", json.dumps(config_update))

        elif topic == "grid/control":
            # Handle operator reset actions
            cmd = payload.get("command")
            if cmd == "RESET_ALARMS":
                logger.info("Operator triggered system alarm reset.")
                relay.reset_trips()
                flisr.reset()
                
                # Also command simulator to restore normally open L7_8 configuration
                restore_payload = {
                    "command": "OPEN",
                    "target": "L7_8"
                }
                client.publish("grid/control", json.dumps(restore_payload))

                # Publish reset FLISR state to grid/config
                config_update = {
                    "flisr_state": flisr.state,
                    "flisr_isolated_faults": flisr.isolated_faults,
                    "flisr_reconfigured_breakers": flisr.reconfigured_breakers,
                    "flisr_tripped_by_relay": flisr.tripped_by_relay
                }
                client.publish("grid/config", json.dumps(config_update))

        elif topic == "grid/config":
            # Update auto/manual configuration for self-healing
            if "flisr_auto" in payload:
                flisr.set_mode(payload["flisr_auto"])
                # Broadcast back state status to sync frontends
                config_update = {
                    "flisr_state": flisr.state,
                    "flisr_isolated_faults": flisr.isolated_faults,
                    "flisr_reconfigured_breakers": flisr.reconfigured_breakers,
                    "flisr_tripped_by_relay": flisr.tripped_by_relay,
                    "flisr_auto": flisr.auto_mode
                }
                client.publish("grid/config", json.dumps(config_update))

    except Exception as e:
        logger.error(f"Error handling message on {msg.topic}: {e}")

if __name__ == "__main__":
    client = mqtt.Client(client_id="self_healing_subsystem")
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
        logger.info("Starting Self-Healing / Protection Relay daemon...")
        client.loop_forever()
    except KeyboardInterrupt:
        logger.info("Daemon interrupted. Shutting down...")
    except Exception as e:
        logger.error(f"MQTT Loop Error: {e}")
        os._exit(1)
