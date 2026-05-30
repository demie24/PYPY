import os
import time
import json
import logging
import threading
import paho.mqtt.client as mqtt
from core.hardware.hardware_state_manager import HardwareStateManager
from core.hardware.virtual_esp32 import VirtualESP32
from core.hardware.virtual_relay_faults import VirtualRelayFaults
from core.hardware.virtual_plc import VirtualPLC
from core.hardware.virtual_sensor_faults import VirtualSensorFaults
from core.hardware.hardware_command_router import HardwareCommandRouter
from core.hardware.hardware_fault_orchestrator import HardwareFaultOrchestrator

# Import Cyber-Physical Attack Layer Skeletons
from core.hardware.digispark_attack_engine import DigisparkAttackEngine
from core.hardware.badusb_payload_manager import BadUSBPayloadManager
from core.hardware.rogue_device_monitor import RogueDeviceMonitor
from core.hardware.hardware_intrusion_detector import HardwareIntrusionDetector
from core.hardware.cyber_physical_attack_orchestrator import CyberPhysicalAttackOrchestrator
from core.hardware.hardware_orchestrator import HardwareOrchestrator

# Import Physical Execution & Edge Reliability Layer
from core.hardware.deployment_profiles import DeploymentProfiles
from core.hardware.physical_telemetry_validator import PhysicalTelemetryValidator
from core.hardware.edge_reliability_monitor import EdgeReliabilityMonitor
from core.hardware.safe_relay_guard import SafeRelayGuard
from core.hardware.hardware_execution_gateway import HardwareExecutionGateway

# Import Distributed Resilience & Deployment Hardening Layer
from core.hardware.distributed_resilience_manager import DistributedResilienceManager
from core.hardware.disaster_recovery_engine import DisasterRecoveryEngine
from core.hardware.redundancy_coordinator import RedundancyCoordinator
from core.hardware.deployment_hardening_engine import DeploymentHardeningEngine
from core.hardware.large_scale_synchronization_manager import LargeScaleSynchronizationManager



# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("hardware.main")

MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))

client = None

# Callback for bus command execution
def on_bus_execution(cmd_payload, success, reason):
    global client
    if not client:
        return
    if success:
        logger.info(f"Command routed successfully: {cmd_payload.get('command')} on {cmd_payload.get('target')}. Confirming execution.")
        control_payload = {
            "command": cmd_payload.get("command"),
            "target": cmd_payload.get("target"),
            "source": "AGENT_CONSENSUS"
        }
        client.publish("grid/control", json.dumps(control_payload))
    else:
        logger.warning(f"Command execution failed on bus: {reason}")
        
    log_payload = {
        "timestamp": int(time.time() * 1000),
        "command": cmd_payload.get("command"),
        "target": cmd_payload.get("target"),
        "source": cmd_payload.get("source"),
        "status": "SUCCESS" if success else "BLOCKED",
        "details": reason
    }
    client.publish("hardware/command_log", json.dumps(log_payload))

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

# Initialize Hardware Orchestrator
orchestrator = HardwareOrchestrator(state_manager, command_router)

# Initialize Physical Execution & Edge Reliability Layer
profiles = DeploymentProfiles()
telemetry_validator = PhysicalTelemetryValidator()
reliability_monitor = EdgeReliabilityMonitor()
safety_guard = SafeRelayGuard()
execution_gateway = HardwareExecutionGateway(
    device_manager=orchestrator.device_manager,
    profiles=profiles,
    safety_guard=safety_guard,
    reliability_monitor=reliability_monitor,
    command_router=command_router
)

# Proxy orchestrator's router calls to execution gateway
orchestrator.command_router = execution_gateway

# Initialize Distributed Resilience & Deployment Hardening Layer
resilience_manager = DistributedResilienceManager()
disaster_recovery = DisasterRecoveryEngine()
redundancy_coordinator = RedundancyCoordinator()
deployment_hardening = DeploymentHardeningEngine()
large_scale_sync = LargeScaleSynchronizationManager()


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
            
            success, reason = orchestrator.submit_command(payload)
            
            # If the command fails arbitration, reject and log immediately.
            # Otherwise it is submitted on the bus and will be acknowledged asynchronously.
            if not success:
                logger.warning(f"Command rejected by Orchestrator arbitration: {reason}")
                log_payload = {
                    "timestamp": int(time.time() * 1000),
                    "command": payload.get("command"),
                    "target": payload.get("target"),
                    "source": payload.get("source"),
                    "status": "BLOCKED",
                    "details": reason
                }
                client.publish("hardware/command_log", json.dumps(log_payload))
            else:
                logger.info(f"Command successfully submitted to Orchestrator: {reason}")
            
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
                if port == "esp32":
                    for d in ["esp32_zone1", "esp32_zone2", "esp32_zone3"]:
                        orchestrator.device_manager.set_device_quarantine(d, True)
                    execution_gateway.set_zone_compromised("zone_1", True)
                    execution_gateway.set_zone_compromised("zone_2", True)
                    execution_gateway.set_zone_compromised("zone_3", True)
                elif port == "plc":
                    orchestrator.device_manager.set_device_quarantine("plc_primary", True)
                    execution_gateway.set_zone_compromised("plc_zone", True)
                else:
                    orchestrator.device_manager.set_device_quarantine(port, True)
                    zone = execution_gateway.breaker_to_zone.get(port) or port
                    execution_gateway.set_zone_compromised(zone, True)
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
                if port == "esp32":
                    for d in ["esp32_zone1", "esp32_zone2", "esp32_zone3"]:
                        orchestrator.device_manager.set_device_quarantine(d, False)
                    execution_gateway.set_zone_compromised("zone_1", False)
                    execution_gateway.set_zone_compromised("zone_2", False)
                    execution_gateway.set_zone_compromised("zone_3", False)
                elif port == "plc":
                    orchestrator.device_manager.set_device_quarantine("plc_primary", False)
                    execution_gateway.set_zone_compromised("plc_zone", False)
                else:
                    orchestrator.device_manager.set_device_quarantine(port, False)
                    zone = execution_gateway.breaker_to_zone.get(port) or port
                    execution_gateway.set_zone_compromised(zone, False)
                event_log = {
                    "timestamp": int(time.time() * 1000),
                    "source": "SCADA_OPERATOR",
                    "event": f"Released Quarantine on Port: {port}",
                    "severity": "INFO"
                }
                client.publish("grid/events", json.dumps(event_log))
                
            elif cmd == "TRIGGER_EMERGENCY_STOP":
                commands = safety_guard.trigger_emergency_stop()
                for safe_cmd in commands:
                    execution_gateway.execute_command(safe_cmd)
                event_log = {
                    "timestamp": int(time.time() * 1000),
                    "source": "SCADA_OPERATOR",
                    "event": "Triggered Emergency Stop! Forced all relays to safe states.",
                    "severity": "CRITICAL"
                }
                client.publish("grid/events", json.dumps(event_log))
                
            elif cmd == "RESET_EMERGENCY_STOP":
                safety_guard.reset_emergency_stop()
                event_log = {
                    "timestamp": int(time.time() * 1000),
                    "source": "SCADA_OPERATOR",
                    "event": "Emergency Stop Reset. Command execution re-enabled.",
                    "severity": "INFO"
                }
                client.publish("grid/events", json.dumps(event_log))
                
            elif cmd == "TRIGGER_DISASTER_RECOVERY":
                workflow = payload.get("workflow", "BLACKSTART_RESTORATION")
                current_breaker_states = {k: v.get("feedback", "OPEN") for k, v in state_manager.relays.items()}
                success, msg = disaster_recovery.start_recovery_workflow(workflow, current_breaker_states)
                event_log = {
                    "timestamp": int(time.time() * 1000),
                    "source": "SCADA_OPERATOR",
                    "event": f"Triggered Disaster Recovery Workflow: {workflow}. Result: {msg}",
                    "severity": "WARNING" if success else "ERROR"
                }
                client.publish("grid/events", json.dumps(event_log))
                
            elif cmd == "TOGGLE_REDUNDANT_EXECUTION":
                enabled = payload.get("enabled", False)
                redundancy_coordinator.redundant_execution_active = enabled
                event_log = {
                    "timestamp": int(time.time() * 1000),
                    "source": "SCADA_OPERATOR",
                    "event": f"Redundant Execution Routing toggled to: {enabled}",
                    "severity": "INFO"
                }
                client.publish("grid/events", json.dumps(event_log))
                
            elif cmd == "SET_HARDENING_CHECK":
                check_name = payload.get("check")
                state = payload.get("state", False)
                deployment_hardening.set_check_state(check_name, state)
                event_log = {
                    "timestamp": int(time.time() * 1000),
                    "source": "SCADA_OPERATOR",
                    "event": f"Hardening Compliance check {check_name} set to {state}",
                    "severity": "INFO"
                }
                client.publish("grid/events", json.dumps(event_log))

            elif cmd == "TERMINATE_HARDWARE_SCENARIO" or cmd == "RESET_ALARMS":
                fault_orchestrator.clear_all_faults()
                attack_orchestrator.reset()
                safety_guard.reset_emergency_stop()
                execution_gateway.compromised_zones.clear()
                
                # Reset new resilience states
                disaster_recovery.active_workflow = None
                disaster_recovery.workflow_status = "IDLE"
                disaster_recovery.restoration_stage = 0
                disaster_recovery.rollback_active = False
                redundancy_coordinator.redundant_execution_active = False
                deployment_hardening.compliance_checks = {
                    "SECURE_BOOT_ENABLED": True,
                    "ENCRYPTED_COMMS_ONLY": True,
                    "DEFAULT_CREDENTIALS_CHANGED": True,
                    "PORT_SECTOR_SEGMENTATION": True,
                    "ACCESS_CONTROL_ENFORCED": True
                }
                deployment_hardening.evaluate_compliance()
                large_scale_sync.recovery_attempts = 0
                
                event_log = {
                    "timestamp": int(time.time() * 1000),
                    "source": "SCADA_OPERATOR",
                    "event": "Cleared all hardware faults, emergency stops, scenarios, and resilience states.",
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
    global client
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
            
            # Tick the hardware orchestrator
            orchestrator.tick(on_bus_execution)
            
            # Get latest telemetry and relays from state_manager
            current_state = state_manager.get_all_states()
            
            # Validate telemetry integrity
            telemetry_validator.validate_telemetry_integrity(current_state, state_manager.relays)
            
            # Get fleet telemetry representation and relay telemetry
            fleet_payload = orchestrator.device_manager.get_telemetry_payload()
            relay_telemetry = relay_controller.get_relay_telemetry()
            
            # Tick reliability monitor
            reliability_monitor.tick(fleet_payload, relay_telemetry)
            
            # Tick synchronization manager and evaluate timings
            large_scale_sync.monitor_and_stabilize(orchestrator.sync_engine.device_drifts)
            
            # Evaluate redundancy and primary-backup health
            redundancy_coordinator.evaluate_redundancy_health(fleet_payload, large_scale_sync.timing_deviations)
            
            # Evaluate global distributed resilience state
            resilience_manager.evaluate_resilience(
                current_state,
                fleet_payload,
                telemetry_validator.alerts,
                not large_scale_sync.sync_stabilized,
                large_scale_sync.congestion_detected
            )
            
            # Evaluate deployment hardening compliance
            deployment_hardening.evaluate_compliance()
            
            # Execute automated disaster recovery workflow step
            if disaster_recovery.active_workflow and disaster_recovery.workflow_status == "IN_PROGRESS":
                current_breaker_states = {k: v.get("feedback", "OPEN") for k, v in state_manager.relays.items()}
                cmd_payload = disaster_recovery.execute_next_step(current_breaker_states)
                if cmd_payload:
                    success, reason = execution_gateway.execute_command(cmd_payload)
                    if success:
                        disaster_recovery.restoration_stage += 1
                        logger.info(f"Disaster Recovery executed step successfully. Advancing to stage {disaster_recovery.restoration_stage}")
                    else:
                        rollback_cmds = disaster_recovery.handle_step_failure(cmd_payload["target"], current_breaker_states)
                        for r_cmd in rollback_cmds:
                            execution_gateway.execute_command(r_cmd)
            
            # 1. Heartbeats
            esp32_hb = esp32_bridge.run_heartbeat_cycle()
            plc_hb = plc_interface.run_heartbeat_cycle()
            
            # Feed heartbeats into fleet devices
            if esp32_bridge.status == "ONLINE":
                orchestrator.device_manager.update_device_heartbeat("esp32_zone1", esp32_bridge.latency_ms)
                orchestrator.device_manager.update_device_heartbeat("esp32_zone2", esp32_bridge.latency_ms + 2.0)
                orchestrator.device_manager.update_device_heartbeat("esp32_zone3", esp32_bridge.latency_ms + 4.0)
                orchestrator.device_manager.update_device_heartbeat("esp32_backup", esp32_bridge.latency_ms + 3.0)
            if plc_interface.status == "ONLINE":
                orchestrator.device_manager.update_device_heartbeat("plc_primary", plc_interface.latency_ms)
                orchestrator.device_manager.update_device_heartbeat("plc_backup", plc_interface.latency_ms + 5.0)
            
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
            
            # 6. Publish Hardware Orchestration Telemetry
            client.publish("hardware/orchestration", json.dumps(orchestrator.get_orchestration_telemetry()))
            client.publish("hardware/edge_devices", json.dumps(orchestrator.device_manager.get_telemetry_payload()))
            client.publish("hardware/relay_execution", json.dumps(orchestrator.relay_planner.get_telemetry_payload()))
            client.publish("hardware/distributed_bus", json.dumps(orchestrator.command_bus.get_telemetry_payload()))
            client.publish("hardware/synchronization", json.dumps(orchestrator.sync_engine.get_telemetry_payload()))
            client.publish("hardware/orchestration_conflicts", json.dumps(orchestrator.get_conflicts_telemetry()))
            
            # 7. Publish Physical Execution & Edge Reliability Telemetry
            client.publish("hardware/execution_gateway", json.dumps(execution_gateway.get_telemetry_payload()))
            client.publish("hardware/reliability", json.dumps(reliability_monitor.get_telemetry_payload()))
            client.publish("hardware/safety_guard", json.dumps(safety_guard.get_telemetry_payload()))
            client.publish("hardware/deployment_profiles", json.dumps(profiles.get_telemetry_payload()))
            client.publish("hardware/telemetry_validation", json.dumps(telemetry_validator.get_telemetry_payload()))
            
            # 8. Publish Distributed Resilience & Deployment Hardening Telemetry
            client.publish("hardware/resilience", json.dumps(resilience_manager.get_telemetry_payload()))
            client.publish("hardware/disaster_recovery", json.dumps(disaster_recovery.get_telemetry_payload()))
            client.publish("hardware/redundancy", json.dumps(redundancy_coordinator.get_telemetry_payload()))
            client.publish("hardware/deployment_hardening", json.dumps(deployment_hardening.get_telemetry_payload()))
            client.publish("hardware/large_scale_sync", json.dumps(large_scale_sync.get_telemetry_payload()))

            
            time.sleep(1.0)
        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.error(f"Error in HAL main thread loop: {e}")
            time.sleep(1.0)
            
    client.loop_stop()
    client.disconnect()
