import time
import logging
import math
from typing import Dict, Any, List, Optional
from core.hardware.hardware_state_manager import HardwareStateManager
from core.hardware.virtual_esp32 import VirtualESP32
from core.hardware.virtual_plc import VirtualPLC
from core.hardware.virtual_sensor_faults import VirtualSensorFaults
from core.hardware.virtual_relay_faults import VirtualRelayFaults

logger = logging.getLogger("hardware.fault_orchestrator")

class HardwareFaultOrchestrator:
    def __init__(self, 
                 state_manager: HardwareStateManager, 
                 esp32_bridge: VirtualESP32, 
                 plc_interface: VirtualPLC, 
                 sensor_interface: VirtualSensorFaults, 
                 relay_controller: VirtualRelayFaults):
        
        self.state_manager = state_manager
        self.esp = esp32_bridge
        self.plc = plc_interface
        self.sensor = sensor_interface
        self.relay = relay_controller
        
        self.active_scenario: Optional[str] = None
        self.scenario_start_time: float = 0.0
        self.scenario_step = 0
        
        self.anomalies_log: List[Dict[str, Any]] = []
        self.severity_score = 0.0  # 0.0 (nominal) to 100.0 (catastrophic)
        
    def inject_fault(self, device: str, fault_type: str, target: str, state: Any):
        """
        Routes fault injection request to the appropriate virtual device.
        """
        timestamp = int(time.time() * 1000)
        logger.info(f"Injecting fault: device={device}, type={fault_type}, target={target}, state={state}")
        
        # 1. ESP32 Controller Faults
        if device == "esp32":
            if fault_type == "comms_failure":
                self.esp.set_comms_failure(bool(state))
            elif fault_type == "latency_spike":
                self.esp.set_latency_spike(bool(state))
            elif fault_type == "packet_drop_rate":
                self.esp.set_packet_drop_rate(float(state))
            elif fault_type == "heartbeat_failure":
                self.esp.set_heartbeat_failure(bool(state))
                
        # 2. PLC Modbus Faults
        elif device == "plc":
            if fault_type == "comms_failure":
                self.plc.set_comms_failure(bool(state))
            elif fault_type == "latency_spike":
                self.plc.set_latency_spike(bool(state))
            elif fault_type == "write_delay":
                self.plc.set_write_delay(float(state))
            elif fault_type == "modbus_exception_rate":
                self.plc.set_modbus_exception_rate(float(state))
                
        # 3. Sensor Faults (PTs, CTs, feedback)
        elif device == "sensor":
            if fault_type == "noise":
                self.sensor.noise_enabled = bool(state)
            elif fault_type == "drift":
                self.sensor.drift_enabled = bool(state)
            elif fault_type == "packet_loss_rate":
                self.sensor.packet_loss_rate = float(state)
            elif fault_type == "spoofing_bias":
                # target represents sensor_id (e.g. "bus_5_v")
                self.sensor.set_spoofing_bias(target, float(state))
            elif fault_type == "corruption":
                # state is corr_type ("NaN", "OOB", "STUCK")
                # optional value for STUCK passed as third param or parsed
                val = 1.0
                if isinstance(state, dict):
                    corr_type = state.get("type", "NONE")
                    val = state.get("value", 1.0)
                else:
                    corr_type = str(state)
                self.sensor.set_corruption(target, corr_type, val)
            elif fault_type == "fake_breaker_feedback":
                self.sensor.set_fake_breaker_feedback(target, state)
                
        # 4. Relay controller faults (stickiness, welding, oscillation)
        elif device == "relay":
            if fault_type == "stuck_relay":
                self.relay.set_stuck_relay(target, state)
            elif fault_type == "switching_delay":
                self.relay.set_switching_delay(target, float(state))
            elif fault_type == "oscillation":
                self.relay.set_relay_oscillation(target, float(state))
            elif fault_type == "welded_contact":
                self.relay.set_contact_welding(target, bool(state))
            elif fault_type == "desync":
                self.relay.set_relay_desync(target, bool(state))
            elif fault_type == "corruption":
                # state is Dict with {"coil": val, "feedback": val}
                c_val = state.get("coil") if isinstance(state, dict) else None
                f_val = state.get("feedback") if isinstance(state, dict) else None
                self.relay.set_relay_corruption(target, c_val, f_val)

        # Log anomaly event
        self._add_anomaly(
            source="FAULT_INJECTOR",
            event_type="FAULT_INJECTED",
            details=f"Injected {fault_type} on {device} ({target})",
            severity="WARNING" if state else "INFO"
        )
        
    def clear_all_faults(self):
        """
        Resets and clears all active virtual device and fault states.
        """
        self.active_scenario = None
        self.scenario_step = 0
        self.scenario_start_time = 0.0
        
        self.esp.set_comms_failure(False)
        self.esp.set_latency_spike(False)
        self.esp.set_packet_drop_rate(0.0)
        self.esp.set_heartbeat_failure(False)
        
        self.plc.set_comms_failure(False)
        self.plc.set_latency_spike(False)
        self.plc.set_write_delay(0.0)
        self.plc.set_modbus_exception_rate(0.0)
        self.plc.write_queue.clear()
        
        self.sensor.clear_sensor_faults()
        self.sensor.packet_loss_rate = 0.0
        self.sensor.noise_enabled = True
        self.sensor.drift_enabled = False
        for sid in self.sensor.drifts.keys():
            self.sensor.drifts[sid] = 0.0
            
        self.relay.clear_relay_faults()
        
        for dev_id in self.state_manager.devices.keys():
            self.state_manager.devices[dev_id]["trust"] = 1.0
            self.state_manager.devices[dev_id]["status"] = "ONLINE"
            
        self.anomalies_log.clear()
        self.severity_score = 0.0
        
        logger.info("All virtual hardware twin faults and devices reset to nominal.")
        
        self._add_anomaly(
            source="FAULT_INJECTOR",
            event_type="RESET_ALL",
            details="All hardware faults and device states reset to nominal.",
            severity="INFO"
        )
        
    def launch_scenario(self, scenario_name: str):
        """
        Launches a pre-defined hardware fault sequence.
        """
        self.clear_all_faults()
        self.active_scenario = scenario_name
        self.scenario_start_time = time.time()
        self.scenario_step = 0
        logger.warning(f"Launched Hardware fault scenario: {scenario_name}")
        
    def tick_scenario(self):
        """
        Steps through the active scenario sequence. Should be ticked at 1Hz in the main daemon.
        """
        if not self.active_scenario:
            return
            
        elapsed = time.time() - self.scenario_start_time
        
        # 1. Scenario: DoS Propagation
        # Gradually disconnects ESP32 nodes, representing a spreading local WiFi jamming attack
        if self.active_scenario == "dos_propagation":
            if self.scenario_step == 0 and elapsed >= 1.0:
                self.esp.set_comms_failure(True)
                self._add_anomaly("SCENARIO", "ATTACK_PROPAGATION", "DoS Attack active on Substation substations (ESP32 disconnected)", "HIGH")
                self.scenario_step = 1
            elif self.scenario_step == 1 and elapsed >= 5.0:
                self.esp.set_packet_drop_rate(0.8)
                self._add_anomaly("SCENARIO", "ATTACK_PROPAGATION", "Jamming spreads: Packet drops on substation relays escalated to 80%", "HIGH")
                self.scenario_step = 2
            elif self.scenario_step == 2 and elapsed >= 10.0:
                self.sensor.packet_loss_rate = 0.90
                self._add_anomaly("SCENARIO", "ATTACK_PROPAGATION", "WiFi noise isolates sensor telemetry (90% packet loss)", "CRITICAL")
                self.scenario_step = 3
                
        # 2. Scenario: PLC Modbus Hijack
        # Targets substation 7-9 PLC Modbus channel
        elif self.active_scenario == "plc_modbus_hijack":
            if self.scenario_step == 0 and elapsed >= 1.0:
                self.plc.set_modbus_exception_rate(0.60)
                self.plc.set_write_delay(4.0)
                self._add_anomaly("SCENARIO", "PLC_COMPROMISED", "PLC Modbus interface hijacked: Exception rate 60%, command execution delayed by 4s", "HIGH")
                self.scenario_step = 1
            elif self.scenario_step == 1 and elapsed >= 5.0:
                self.relay.set_contact_welding("L7_8", True)
                self._add_anomaly("SCENARIO", "RELAY_DAMAGE", "Contacts welded CLOSED on tie-breaker L7_8", "CRITICAL")
                self.scenario_step = 2
            elif self.scenario_step == 2 and elapsed >= 10.0:
                self.plc.set_comms_failure(True)
                self._add_anomaly("SCENARIO", "PLC_COLLAPSE", "PLC communications fully collapsed (offline DoS)", "CRITICAL")
                self.scenario_step = 3
                
        # 3. Scenario: Sensor Corruption Storm
        # Corrupts physical voltage & current feeds, causing AI predictor and physics checks to flap
        elif self.active_scenario == "sensor_corruption_storm":
            if self.scenario_step == 0 and elapsed >= 1.0:
                self.sensor.set_spoofing_bias("bus_5_v", -0.18)
                self.sensor.set_spoofing_bias("bus_6_v", 0.12)
                self._add_anomaly("SCENARIO", "SENSOR_SPOOFING", "PT voltage spoofing active on Bus_5 (-0.18 p.u.) and Bus_6 (+0.12 p.u.)", "HIGH")
                self.scenario_step = 1
            elif self.scenario_step == 1 and elapsed >= 5.0:
                self.sensor.set_corruption("bus_7_v", "NaN")
                self._add_anomaly("SCENARIO", "TELEMETRY_CORRUPTION", "Bus_7 voltage transmitter failed (broadcasting NaNs)", "HIGH")
                self.scenario_step = 2
            elif self.scenario_step == 2 and elapsed >= 10.0:
                self.sensor.set_corruption("line_L1_4_i", "OOB")
                self._add_anomaly("SCENARIO", "SENSORS_CORRUPTED", "CT Current transmitter L1_4 corrupted (broadcasting extreme out-of-bounds 5.0 p.u.)", "CRITICAL")
                self.scenario_step = 3
                
        # 4. Scenario: Relay Welding Lockout
        # Locks grid breakers state and welded contacts to cause restoration locks
        elif self.active_scenario == "relay_welding_lockout":
            if self.scenario_step == 0 and elapsed >= 1.0:
                self.relay.set_contact_welding("L4_5", True)
                self._add_anomaly("SCENARIO", "RELAY_WELDER", "Relay L4_5 welded CLOSED (aux feedback welded)", "HIGH")
                self.scenario_step = 1
            elif self.scenario_step == 1 and elapsed >= 5.0:
                self.relay.set_stuck_relay("L7_8", "OPEN")
                self._add_anomaly("SCENARIO", "RELAY_LOCKOUT", "Tie-breaker L7_8 stuck OPEN (actuator mechanical lockout)", "CRITICAL")
                self.scenario_step = 2

    def check_anomalies(self) -> List[Dict[str, Any]]:
        """
        Scans physical state manager for active conflicts, mismatches, or timeout failures.
        """
        now = time.time()
        
        # 1. Check Breaker Mismatches
        for rid, val in self.state_manager.relays.items():
            if val["coil"] != val["feedback"]:
                # alignment anomaly
                msg = f"Relay alignment mismatch on {rid}: coil={val['coil']}, feedback={val['feedback']}"
                self._add_anomaly("STATE_MONITOR", "RELAY_ALIGNMENT_MISMATCH", msg, "HIGH", rid)
                
            if rid in self.relay.welded_contacts:
                self._add_anomaly("STATE_MONITOR", "CONTACT_WELDED", f"Relay contact {rid} welded CLOSED", "HIGH", rid)
                
            if rid in self.relay.stuck_relays:
                self._add_anomaly("STATE_MONITOR", "RELAY_STUCK", f"Relay actuator {rid} STUCK {self.relay.stuck_relays[rid]}", "CRITICAL", rid)
                
            if rid in self.relay.oscillating_relays:
                self._add_anomaly("STATE_MONITOR", "RELAY_OSCILLATING", f"Relay {rid} chattering rapidly ({self.relay.oscillating_relays[rid]}Hz)", "HIGH", rid)

        # 2. Check Device Offline timeouts and low trust
        for dev_id, dev in self.state_manager.devices.items():
            if dev["status"] == "OFFLINE":
                self._add_anomaly("DEVICE_HEALTH", "DEVICE_OFFLINE", f"{dev['name']} heartbeat missing (OFFLINE)", "HIGH", dev_id)
            if dev["trust"] < 0.60:
                self._add_anomaly("DEVICE_HEALTH", "LOW_TRUST", f"{dev['name']} trust degraded to {(dev['trust']*100):.0f}%", "WARNING", dev_id)
            if dev["latency_ms"] > 200.0:
                self._add_anomaly("DEVICE_HEALTH", "LATENCY_SPIKE", f"{dev['name']} ping latency high: {dev['latency_ms']:.1f}ms", "WARNING", dev_id)

        # 3. Check Sensor NaNs and extreme values
        for sid, val in self.state_manager.sensors.items():
            if math.isnan(val):
                self._add_anomaly("SENSOR_MONITOR", "TELEMETRY_NAN", f"Telemetry feed {sid} is broadcasting NaN values", "HIGH", sid)
            elif "_v" in sid and (val < 0.85 or val > 1.15) and val != 0.0:
                self._add_anomaly("SENSOR_MONITOR", "VOLTAGE_OUT_OF_BOUNDS", f"Telemetry voltage {sid} out of bounds: {val:.3f} p.u.", "WARNING", sid)

        # 4. Limit log size
        if len(self.anomalies_log) > 50:
            self.anomalies_log = self.anomalies_log[-50:]
            
        # Calculate dynamic severity score based on active anomalies
        self._calculate_severity()
        
        return self.anomalies_log

    def _add_anomaly(self, source: str, event_type: str, details: str, severity: str, target: str = "all"):
        timestamp = int(time.time() * 1000)
        
        # Check duplicate logs within last 5 seconds
        for item in reversed(self.anomalies_log):
            if (timestamp - item["timestamp"] < 5000 and 
                item["event_type"] == event_type and 
                item["details"] == details):
                return
                
        self.anomalies_log.append({
            "timestamp": timestamp,
            "source": source,
            "event_type": event_type,
            "details": details,
            "severity": severity,
            "target": target
        })

    def _calculate_severity(self):
        """
        Determines dynamic severity score: 0.0 (nominal) to 100.0 (catastrophic)
        """
        base = 0.0
        
        # Add weights for anomalies
        esp_online = self.state_manager.devices["esp32"]["status"] == "ONLINE"
        plc_online = self.state_manager.devices["plc"]["status"] == "ONLINE"
        
        if not esp_online: base += 25.0
        if not plc_online: base += 25.0
        
        # Check relay faults
        base += len(self.relay.stuck_relays) * 15.0
        base += len(self.relay.welded_contacts) * 15.0
        base += len(self.relay.oscillating_relays) * 10.0
        
        # Check sensor faults
        base += len(self.sensor.spoofing_biases) * 8.0
        base += len(self.sensor.corruption_types) * 10.0
        base += len(self.sensor.fake_breaker_feedback) * 12.0
        
        self.severity_score = min(100.0, base)

    def get_fault_propagation_status(self) -> Dict[str, Any]:
        """
        Analyzes virtual cyber-physical attack propagation pathways across grid nodes.
        Maps how virtual compromise transitions trigger relay and physical line anomalies.
        """
        propagation_paths = []
        
        # 1. ESP32 Compromise Pathway
        if not self.esp.is_connected or self.esp.packet_drop_rate > 0.5:
            propagation_paths.append({
                "source": "esp32",
                "compromised": True,
                "vector": "Jamming / DoS",
                "affected_nodes": ["L1_4", "L2_7", "L3_9", "L4_5", "L4_9", "L5_6"],
                "propagation_stage": "DEVICE_ISOLATED"
            })
            
        # Stuck or welded ESP32 relays
        for rid in ["L1_4", "L2_7", "L3_9", "L4_5", "L4_9", "L5_6"]:
            if rid in self.relay.welded_contacts or rid in self.relay.stuck_relays:
                propagation_paths.append({
                    "source": "esp32",
                    "compromised": True,
                    "vector": "Relay Welding/Stuck actuator",
                    "affected_nodes": [rid, rid.split('_')[1]],  # affects breaker and bus
                    "propagation_stage": "PHYSICAL_LOCKOUT"
                })

        # 2. PLC Compromise Pathway
        if not self.plc.is_connected or self.plc.modbus_exception_rate > 0.5:
            propagation_paths.append({
                "source": "plc",
                "compromised": True,
                "vector": "Modbus hijacking / Comm loss",
                "affected_nodes": ["L6_7", "L7_8", "L8_9"],
                "propagation_stage": "COMMUNICATION_COLLAPSE"
            })
            
        for rid in ["L6_7", "L7_8", "L8_9"]:
            if rid in self.relay.welded_contacts or rid in self.relay.stuck_relays:
                propagation_paths.append({
                    "source": "plc",
                    "compromised": True,
                    "vector": "PLC Relay degradation",
                    "affected_nodes": [rid, "Bus_7", "Bus_8"],
                    "propagation_stage": "PHYSICAL_LOCKOUT"
                })

        # 3. Sensor Spoofing Pathway
        for sid in self.sensor.spoofing_biases.keys():
            bus_name = sid.replace("bus_", "").replace("_v", "").upper()
            propagation_paths.append({
                "source": "sensor_interface",
                "compromised": True,
                "vector": "Calibration bias injection (FDIA)",
                "affected_nodes": [f"Bus_{bus_name}"],
                "propagation_stage": "TELEMETRY_CORRUPTED"
            })
            
        return {
            "timestamp": int(time.time() * 1000),
            "severity_score": round(self.severity_score, 1),
            "propagation_paths": propagation_paths,
            "scenario": self.active_scenario or "NONE"
        }

    def get_faults_payload(self) -> Dict[str, Any]:
        """
        Compiles the active faults list.
        """
        return {
            "timestamp": int(time.time() * 1000),
            "esp32": {
                "comms_failure": self.esp.comms_failure,
                "latency_spike": self.esp.latency_spike,
                "packet_drop_rate": self.esp.packet_drop_rate,
                "heartbeat_failure": self.esp.heartbeat_failure
            },
            "plc": {
                "comms_failure": self.plc.comms_failure,
                "latency_spike": self.plc.latency_spike,
                "write_delay": self.plc.write_delay_duration,
                "modbus_exception_rate": self.plc.modbus_exception_rate
            },
            "sensors": {
                "noise_enabled": self.sensor.noise_enabled,
                "drift_enabled": self.sensor.drift_enabled,
                "packet_loss_rate": self.sensor.packet_loss_rate,
                "spoofed_sensors": list(self.sensor.spoofing_biases.keys()),
                "corrupted_sensors": list(self.sensor.corruption_types.keys()),
                "fake_feedbacks": list(self.sensor.fake_breaker_feedback.keys())
            },
            "relays": {
                "stuck_relays": list(self.stuck_relays.keys()),
                "switching_delays": list(self.relay.switching_delays.keys()),
                "oscillating_relays": list(self.relay.oscillating_relays.keys()),
                "welded_contacts": list(self.relay.welded_contacts),
                "desynced_relays": list(self.relay.desynced_relays),
                "corrupted_relays": list(self.relay.corrupted_states.keys())
            }
        }
