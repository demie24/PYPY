import os
import time
import json
import logging
import threading
import paho.mqtt.client as mqtt
from hardware_state_manager import HardwareStateManager
from virtual_esp32 import VirtualESP32
from virtual_relay_faults import VirtualRelayFaults
from virtual_plc import VirtualPLC
from virtual_sensor_faults import VirtualSensorFaults
from hardware_command_router import HardwareCommandRouter
from hardware_fault_orchestrator import HardwareFaultOrchestrator

# Import Cyber-Physical Attack Layer Skeletons
from digispark_attack_engine import DigisparkAttackEngine
from badusb_payload_manager import BadUSBPayloadManager
from rogue_device_monitor import RogueDeviceMonitor
from hardware_intrusion_detector import HardwareIntrusionDetector
from cyber_physical_attack_orchestrator import CyberPhysicalAttackOrchestrator


# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("hardware.main")

MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))

# Initialize HAL instances
state_manager = HardwareStateManager()
relay_controller = VirtualRelayFaults(state_manager)
esp32_bridge = VirtualESP32(state_manager, relay_controller)
plc_interface = VirtualPLC(state_manager, relay_controller)
sensor_interface = VirtualSensorFaults(state_manager)
command_router = HardwareCommandRouter(state_manager, esp32_bridge, plc_interface, relay_controller)
fault_orchestrator = HardwareFaultOrchestrator(state_manager, esp32_bridge, plc_interface, sensor_interface, relay_controller)

# Initialize Attack Layer Skeletons
digispark_engine = DigisparkAttackEngine()
badusb_manager = BadUSBPayloadManager()
rogue_monitor = RogueDeviceMonitor()
intrusion_detector = HardwareIntrusionDetector()
attack_orchestrator = CyberPhysicalAttackOrchestrator(digispark_engine, badusb_manager, rogue_monitor, intrusion_detector)

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
                # Scaffolding intrusion telemetry analysis
                for bid, bus in (payload.get("state", {}).get("buses", {})).items():
                    sensor_id = f"{bid.lower()}_v"
                    if sensor_id in state_manager.sensors:
                        raw_v = bus.get("voltage_pu", 1.0)
                        filtered_v = state_manager.sensors[sensor_id]
                        intrusion_detector.analyze_telemetry(sensor_id, raw_v, filtered_v)
                
        # 2. Intercept proposed commands
        elif topic == "hardware/control/execute":
            logger.info(f"Proposed control command intercepted: {payload}")
            # Intrusion command checks
            cmd = payload.get("command")
            target = payload.get("target")
            source = payload.get("source")
            intrusion_detector.analyze_command(cmd, target, source)
            
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
                target = payload.get("target", "all")
                state = payload.get("state", False)
                
                # Delegate to orchestrator
                fault_orchestrator.inject_fault(device, fault_type, target, state)
                
                # Publish event log
                event_log = {
                    "timestamp": int(time.time() * 1000),
                    "source": "SCADA_OPERATOR",
                    "event": f"Hardware Fault Injection: device={device}, type={fault_type}, target={target}, state={state}",
                    "severity": "WARNING" if state else "INFO"
                }
                client.publish("grid/events", json.dumps(event_log))
                
            elif cmd == "LAUNCH_HARDWARE_SCENARIO":
                scenario = payload.get("scenario")
                campaigns = ["coordinated_blackout", "stealthy_calibration_drift", "reconnect_flood_dos"]
                if scenario in campaigns:
                    attack_orchestrator.start_campaign(scenario)
                else:
                    fault_orchestrator.launch_scenario(scenario)
                event_log = {
                    "timestamp": int(time.time() * 1000),
                    "source": "SCADA_OPERATOR",
                    "event": f"Launched Hardware Scenario/Campaign: {scenario}",
                    "severity": "WARNING"
                }
                client.publish("grid/events", json.dumps(event_log))
                
            elif cmd == "INJECT_USB_DEVICE":
                vid = payload.get("vendor_id")
                pid = payload.get("product_id")
                name = payload.get("name")
                rogue_monitor.simulate_device_insertion(vid, pid, name)
                event_log = {
                    "timestamp": int(time.time() * 1000),
                    "source": "SCADA_OPERATOR",
                    "event": f"USB Device Connected: {name} ({vid}:{pid})",
                    "severity": "WARNING"
                }
                client.publish("grid/events", json.dumps(event_log))
                
            elif cmd == "REMOVE_USB_DEVICE":
                vid = payload.get("vendor_id")
                pid = payload.get("product_id")
                rogue_monitor.simulate_device_removal(vid, pid)
                event_log = {
                    "timestamp": int(time.time() * 1000),
                    "source": "SCADA_OPERATOR",
                    "event": f"USB Device Disconnected: {vid}:{pid}",
                    "severity": "INFO"
                }
                client.publish("grid/events", json.dumps(event_log))
                
            elif cmd == "TRIGGER_BADUSB_ATTACK":
                payload_id = payload.get("payload_id")
                delay = payload.get("delay_ticks", 0)
                origin_ip = payload.get("origin_ip", "192.168.1.50")
                
                # Fetch payload scripts and metadata
                script_steps = badusb_manager.get_payload_script(payload_id)
                meta = badusb_manager.get_payload_metadata(payload_id)
                
                # Run security intrusion evaluations
                intrusion_detector.analyze_ip_origin(origin_ip, f"TRIGGER_BADUSB:{payload_id}")
                intrusion_detector.analyze_typing_speed(2) # 2ms mechanical speed triggers alert
                
                # Trigger staged attack execution
                digispark_engine.trigger_attack(payload_id, delay_ticks=delay, steps=script_steps)
                
                # Decay trust statefully based on badusb metadata
                impact = meta.get("trust_impact", 0.0)
                if impact > 0:
                    rogue_monitor.hardware_trust_score = max(0.0, rogue_monitor.hardware_trust_score - impact)
                
                # Dynamically execute simulated physical commands described in the DuckyScript
                for step in script_steps:
                    parts = step.split(" ", 1)
                    step_cmd = parts[0]
                    step_arg = parts[1] if len(parts) > 1 else ""
                    
                    if step_cmd == "WRITE_MODBUS_COIL":
                        # Format: WRITE_MODBUS_COIL address value
                        try:
                            addr_val = step_arg.split(" ")
                            addr = int(addr_val[0])
                            val = int(addr_val[1])
                            # Execute coil write
                            plc_interface.write_single_coil(addr, val)
                        except Exception as e:
                            logger.error(f"Error executing MODBUS payload step: {e}")
                    elif step_cmd == "SPOOF_BIAS":
                        try:
                            sensor_val = step_arg.split(" ")
                            sensor = sensor_val[0]
                            bias = float(sensor_val[1])
                            sensor_interface.set_calibration_drift(sensor, bias)
                        except Exception as e:
                            logger.error(f"Error executing SPOOF payload step: {e}")
                    elif step_cmd == "CORRUPT_SENSOR":
                        try:
                            sensor_type = step_arg.split(" ")
                            sensor = sensor_type[0]
                            ctype = sensor_type[1]
                            sensor_interface.set_sensor_corruption(sensor, ctype)
                        except Exception as e:
                            logger.error(f"Error executing CORRUPT payload step: {e}")
                
                event_log = {
                    "timestamp": int(time.time() * 1000),
                    "source": "SCADA_OPERATOR",
                    "event": f"Triggered Digispark BadUSB Attack: {payload_id} (trust penalty applied: -{impact})",
                    "severity": "HIGH"
                }
                client.publish("grid/events", json.dumps(event_log))
                
            elif cmd == "QUARANTINE_PORT":
                port = payload.get("port")
                attack_orchestrator.execute_quarantine(port)
                event_log = {
                    "timestamp": int(time.time() * 1000),
                    "source": "SCADA_OPERATOR",
                    "event": f"Quarantined Hardware Interface Port: {port}",
                    "severity": "WARNING"
                }
                client.publish("grid/events", json.dumps(event_log))
                
            elif cmd == "RELEASE_PORT":
                port = payload.get("port")
                attack_orchestrator.remove_quarantine(port)
                event_log = {
                    "timestamp": int(time.time() * 1000),
                    "source": "SCADA_OPERATOR",
                    "event": f"Released Quarantine on Port: {port}",
                    "severity": "INFO"
                }
                client.publish("grid/events", json.dumps(event_log))
                
            elif cmd == "TERMINATE_HARDWARE_SCENARIO" or cmd == "RESET_ALARMS":
                fault_orchestrator.clear_all_faults()
                attack_orchestrator.reset()
                event_log = {
                    "timestamp": int(time.time() * 1000),
                    "source": "SCADA_OPERATOR",
                    "event": "Cleared all hardware faults and scenario states.",
                    "severity": "INFO"
                }
                client.publish("grid/events", json.dumps(event_log))
                
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
            # 0. Tick orchestrator and deferred queue components
            plc_interface.process_write_queue()
            fault_orchestrator.tick_scenario()
            anomalies = fault_orchestrator.check_anomalies()
            
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
            
            # 4. Virtual Twin Telemetry topics
            client.publish("hardware/faults", json.dumps(fault_orchestrator.get_faults_payload()))
            
            relay_faults_payload = {
                "timestamp": int(time.time() * 1000),
                "stuck": list(relay_controller.stuck_relays.keys()),
                "welded": list(relay_controller.welded_contacts),
                "desynced": list(relay_controller.desynced_relays),
                "oscillating": list(relay_controller.oscillating_relays.keys()),
                "corrupted": list(relay_controller.corrupted_states.keys())
            }
            client.publish("hardware/relay_faults", json.dumps(relay_faults_payload))
            
            client.publish("hardware/anomalies", json.dumps(anomalies))
            
            virtual_devices_payload = {
                "timestamp": int(time.time() * 1000),
                "esp32": esp32_bridge.get_telemetry_payload(),
                "plc": plc_interface.get_telemetry_payload()
            }
            client.publish("hardware/virtual_devices", json.dumps(virtual_devices_payload))
            
            spoofed_telemetry_payload = {
                "timestamp": int(time.time() * 1000),
                "spoofed_sensors": {k: v for k, v in sensor_interface.spoofing_biases.items()},
                "corrupted_sensors": {k: v for k, v in sensor_interface.corruption_types.items()},
                "fake_feedbacks": {k: v for k, v in sensor_interface.fake_breaker_feedback.items()}
            }
            client.publish("hardware/spoofed_telemetry", json.dumps(spoofed_telemetry_payload))
            
            client.publish("hardware/fault_propagation", json.dumps(fault_orchestrator.get_fault_propagation_status()))
            
            # Tick Cyber-Physical Attack layer
            rogue_monitor.tick()
            attack_orchestrator.tick_campaign()
            badusb_payload = digispark_engine.tick()
            attack_state_payload = attack_orchestrator.get_orchestration_payload()
            
            client.publish("hardware/usb_events", json.dumps({"timestamp": int(time.time() * 1000), "events": digispark_engine.usb_events}))
            client.publish("hardware/rogue_devices", json.dumps({"timestamp": int(time.time() * 1000), "devices": rogue_monitor.get_devices_status()}))
            client.publish("hardware/badusb", json.dumps(badusb_payload))
            client.publish("hardware/intrusion_alerts", json.dumps({"timestamp": int(time.time() * 1000), "alerts": intrusion_detector.alerts}))
            client.publish("hardware/device_trust", json.dumps(rogue_monitor.get_trust_payload()))
            client.publish("hardware/attack_state", json.dumps(attack_state_payload))
            client.publish("hardware/attack_propagation", json.dumps(attack_orchestrator.get_propagation_chain()))
            
            time.sleep(1.0)
        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.error(f"Error in HAL main thread loop: {e}")
            time.sleep(1.0)
            
    client.loop_stop()
    client.disconnect()
