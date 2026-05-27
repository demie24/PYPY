import os
import time
import json
import logging
import threading
import paho.mqtt.client as mqtt
from hardware_state_manager import HardwareStateManager
from esp32_bridge import ESP32Bridge
from relay_controller import RelayController
from plc_interface import PLCInterface
from sensor_interface import SensorInterface
from hardware_command_router import HardwareCommandRouter

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("hardware.main")

MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))

# Initialize HAL instances
state_manager = HardwareStateManager()
relay_controller = RelayController(state_manager)
esp32_bridge = ESP32Bridge(state_manager, relay_controller)
plc_interface = PLCInterface(state_manager, relay_controller)
sensor_interface = SensorInterface(state_manager)
command_router = HardwareCommandRouter(state_manager, esp32_bridge, plc_interface, relay_controller)

# MQTT Callbacks
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info("Hardware Abstraction Layer Daemon connected to MQTT!")
        client.subscribe("grid/telemetry")
        client.subscribe("hardware/control/execute")
        client.subscribe("grid/control")  # Operator commands for fault injection
    else:
        logger.error(f"HAL Daemon failed to connect, rc {rc}")

def on_message(client, userdata, msg):
    try:
        topic = msg.topic
        payload = json.loads(msg.payload.decode("utf-8"))
        
        # 1. Mirror digital twin telemetry into physical sensors
        if topic == "grid/telemetry":
            sensor_data = sensor_interface.simulate_sensor_sweep(payload)
            if sensor_data:
                client.publish("hardware/sensor", json.dumps(sensor_data))
                
        # 2. Intercept proposed commands
        elif topic == "hardware/control/execute":
            logger.info(f"Proposed control command intercepted: {payload}")
            success, reason = command_router.route_command(payload)
            
            # If successfully routed, we publish the command execution to grid/control
            # so that the Digital Twin updates its state.
            if success:
                logger.info(f"Command routed successfully: {payload.get('command')} on {payload.get('target')}. Confirming execution.")
                control_payload = {
                    "command": payload.get("command"),
                    "target": payload.get("target"),
                    "source": "AGENT_CONSENSUS"  # Mark as consensus execution
                }
                client.publish("grid/control", json.dumps(control_payload))
            else:
                logger.warning(f"Command rejected by Hardware abstraction: {reason}")
                
            # Always publish router log
            log_payload = {
                "timestamp": int(time.time() * 1000),
                "command": payload.get("command"),
                "target": payload.get("target"),
                "source": payload.get("source"),
                "status": "SUCCESS" if success else "BLOCKED",
                "details": reason
            }
            client.publish("hardware/command_log", json.dumps(log_payload))
            
        # 3. Handle operator commands (e.g. reset alarms or fault injections)
        elif topic == "grid/control":
            cmd = payload.get("command")
            if cmd == "INJECT_HARDWARE_FAULT":
                device = payload.get("device")
                fault_type = payload.get("type")
                state = payload.get("state", False)
                
                # Apply fault injection
                if device == "esp32":
                    if fault_type == "comms_failure":
                        esp32_bridge.set_comms_failure(state)
                    elif fault_type == "latency_spike":
                        esp32_bridge.set_latency_spike(state)
                elif device == "plc":
                    if fault_type == "comms_failure":
                        plc_interface.set_comms_failure(state)
                    elif fault_type == "latency_spike":
                        plc_interface.set_latency_spike(state)
                elif device == "sensor":
                    if fault_type == "noise":
                        sensor_interface.noise_enabled = state
                    elif fault_type == "drift":
                        sensor_interface.drift_enabled = state
                        # If drift is enabled, set some random offsets
                        if state:
                            for sid in sensor_interface.drifts.keys():
                                sensor_interface.set_calibration_drift(sid, round(random.uniform(-0.04, 0.04), 4))
                
                # Publish event log
                event_log = {
                    "timestamp": int(time.time() * 1000),
                    "source": "SCADA_OPERATOR",
                    "event": f"Hardware Fault Injection: device={device}, type={fault_type}, state={state}",
                    "severity": "WARNING" if state else "INFO"
                }
                client.publish("grid/events", json.dumps(event_log))
                
            elif cmd == "RESET_ALARMS":
                # Reset hardware trust and statuses
                for dev_id in state_manager.devices.keys():
                    state_manager.devices[dev_id]["trust"] = 1.0
                    state_manager.devices[dev_id]["status"] = "ONLINE"
                esp32_bridge.set_comms_failure(False)
                esp32_bridge.set_latency_spike(False)
                plc_interface.set_comms_failure(False)
                plc_interface.set_latency_spike(False)
                sensor_interface.noise_enabled = True
                sensor_interface.drift_enabled = False
                sensor_interface.packet_loss_rate = 0.0
                logger.info("HAL Daemon metrics and injected faults reset.")
                
    except Exception as e:
        logger.error(f"Error handling message in HAL Daemon: {e}")

# High-resolution transition ticks thread
# Mechanical contact bouncing runs at 100Hz/10ms or similar resolution
def run_relay_transition_loop():
    while True:
        try:
            relay_controller.update_transitions()
            time.sleep(0.02)  # 20ms ticks
        except Exception as e:
            logger.error(f"Error in relay transition update thread: {e}")
            time.sleep(0.1)

if __name__ == "__main__":
    # Initialize MQTT Client
    client = mqtt.Client(client_id="smart_grid_hardware_abstraction_layer")
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
        client.loop_start()
    except Exception as e:
        logger.error(f"Failed to connect HAL Daemon to MQTT broker: {e}")
        time.sleep(5)
        os._exit(1)
        
    # Start high-res transition updates thread
    transition_thread = threading.Thread(target=run_relay_transition_loop, daemon=True)
    transition_thread.start()
    
    logger.info("HAL Daemon successfully started. Spinning 1.0Hz telemetry loops...")
    
    # 1.0Hz main telemetry publishing loop
    while True:
        try:
            # 1. Heartbeats
            esp32_hb = esp32_bridge.run_heartbeat_cycle()
            plc_hb = plc_interface.run_heartbeat_cycle()
            
            # 2. Publish health payload
            health_payload = state_manager.get_device_health()
            client.publish("hardware/device_health", json.dumps(health_payload))
            
            # 3. Publish relay and GPIO statuses
            relay_payload = relay_controller.get_relay_telemetry()
            client.publish("hardware/relay", json.dumps(relay_payload))
            
            gpio_payload = {
                "timestamp": int(time.time() * 1000),
                "gpio": state_manager.gpio.copy()
            }
            client.publish("hardware/gpio", json.dumps(gpio_payload))
            
            time.sleep(1.0)
        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.error(f"Error in HAL main thread loop: {e}")
            time.sleep(1.0)
            
    client.loop_stop()
    client.disconnect()
