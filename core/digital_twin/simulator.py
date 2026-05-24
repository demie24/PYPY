import os
import time
import json
import random
import logging
import threading
import numpy as np
import paho.mqtt.client as mqtt

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("digital_twin")

MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))

class IEEE9BusSimulator:
    def __init__(self):
        # 1. Grid Configuration
        self.num_buses = 9
        
        # Generator Bus Indices (1-indexed in docs, 0-indexed in code: Bus 1, 2, 3 -> index 0, 1, 2)
        self.gen_indices = [0, 1, 2]
        self.load_indices = [4, 5, 7] # Bus 5, 6, 8 -> index 4, 5, 7
        
        # Nominal generator voltages (complex values)
        # Gen 1 (Slack): 1.04 angle 0
        # Gen 2: 1.025 angle 9.16 deg (0.16 rad)
        # Gen 3: 1.025 angle 4.58 deg (0.08 rad)
        self.V_G = np.array([
            1.04 * np.exp(1j * 0.0),
            1.025 * np.exp(1j * 0.16),
            1.025 * np.exp(1j * 0.08)
        ], dtype=complex)
        
        # Nominal load powers (P, Q in per-unit)
        self.nominal_loads = {
            4: {"P": 1.25, "Q": 0.50},  # Bus 5
            5: {"P": 0.90, "Q": 0.30},  # Bus 6
            7: {"P": 1.00, "Q": 0.35}   # Bus 8
        }
        self.active_loads = {k: dict(v) for k, v in self.nominal_loads.items()}
        
        # Line definitions (from_bus, to_bus, R, X, line_id)
        # Standard IEEE 9-bus parameters
        self.lines = [
            {"from": 0, "to": 3, "R": 0.0,    "X": 0.0576, "id": "L1_4", "name": "Gen 1 Transformer"},
            {"from": 1, "to": 6, "R": 0.0,    "X": 0.0625, "id": "L2_7", "name": "Gen 2 Transformer"},
            {"from": 2, "to": 8, "R": 0.0,    "X": 0.0586, "id": "L3_9", "name": "Gen 3 Transformer"},
            {"from": 3, "to": 4, "R": 0.010,  "X": 0.085,  "id": "L4_5", "name": "Line 4-5"},
            {"from": 3, "to": 8, "R": 0.017,  "X": 0.092,  "id": "L4_9", "name": "Line 4-9"},
            {"from": 4, "to": 5, "R": 0.032,  "X": 0.161,  "id": "L5_6", "name": "Line 5-6"},
            {"from": 5, "to": 6, "R": 0.0085, "X": 0.072,  "id": "L6_7", "name": "Line 6-7"},
            {"from": 6, "to": 7, "R": 0.032,  "X": 0.161,  "id": "L7_8", "name": "Line 7-8"},
            {"from": 7, "to": 8, "R": 0.0119, "X": 0.1008, "id": "L8_9", "name": "Line 8-9"}
        ]
        
        # Breaker status (CLOSED = 1, OPEN = 0)
        self.breakers = {line["id"]: "CLOSED" for line in self.lines}
        # L7_8 is a normally-open tie-breaker for self-healing restoration
        self.breakers["L7_8"] = "OPEN"
        
        # Shunt admittances to prevent singularity when islands form
        self.shunt_admittance = 1e-5 + 1e-5j
        
        # Attack parameters
        self.active_attack = None
        self.attack_config = {}
        
        # Replay recording buffer
        self.replay_buffer = []
        self.replay_index = 0
        self.recording = False
        
        # Thread lock for state updates
        self.lock = threading.Lock()

    def build_admittance_matrices(self):
        """
        Builds the complex bus admittance matrix Y_bus based on breaker states
        and partitions it into Generator (G) and Load (L) components.
        """
        Y_bus = np.zeros((self.num_buses, self.num_buses), dtype=complex)
        
        # Add line admittances
        for line in self.lines:
            f, t, lid = line["from"], line["to"], line["id"]
            if self.breakers[lid] == "CLOSED":
                y = 1.0 / (line["R"] + 1j * line["X"])
                Y_bus[f, f] += y
                Y_bus[t, t] += y
                Y_bus[f, t] -= y
                Y_bus[t, f] -= y
        
        # Add load admittances as shunts (constant impedance model)
        # Y_load = (P - jQ) / |V|^2. Assuming nominal |V| = 1.0
        for bus_idx, load in self.active_loads.items():
            # Constant impedance equivalent: Y = (P - jQ)
            y_load = load["P"] - 1j * load["Q"]
            Y_bus[bus_idx, bus_idx] += y_load
            
        # Add minor shunt to all diagonal terms to guarantee invertibility (numerical stability)
        for i in range(self.num_buses):
            Y_bus[i, i] += self.shunt_admittance
            
        # Partition Y_bus
        # G (0, 1, 2) and L (3, 4, 5, 6, 7, 8)
        # Y_bus = [[Y_GG, Y_GL],
        #          [Y_LG, Y_LL]]
        Y_GG = Y_bus[0:3, 0:3]
        Y_GL = Y_bus[0:3, 3:9]
        Y_LG = Y_bus[3:9, 0:3]
        Y_LL = Y_bus[3:9, 3:9]
        
        return Y_GG, Y_GL, Y_LG, Y_LL

    def solve_power_flow(self):
        """
        Solves network node equations: V_L = - Y_LL^-1 * Y_LG * V_G
        """
        with self.lock:
            # Add dynamic load noise
            for bus_idx in self.load_indices:
                noise_p = random.uniform(-0.02, 0.02)
                noise_q = random.uniform(-0.01, 0.01)
                self.active_loads[bus_idx]["P"] = max(0.0, self.nominal_loads[bus_idx]["P"] + noise_p)
                self.active_loads[bus_idx]["Q"] = max(0.0, self.nominal_loads[bus_idx]["Q"] + noise_q)

            # Build and solve
            Y_GG, Y_GL, Y_LG, Y_LL = self.build_admittance_matrices()
            try:
                # Solve V_L
                V_L = np.linalg.solve(Y_LL, -Y_LG.dot(self.V_G))
            except np.linalg.LinAlgError:
                # Fallback if singular matrix occurs
                V_L = np.zeros(6, dtype=complex)
                logger.error("Singular matrix in power flow! Grid may be fully de-energized.")

            # Combine generator and load voltages
            V = np.zeros(self.num_buses, dtype=complex)
            V[0:3] = self.V_G
            V[3:9] = V_L
            
            # Compute line currents and power flows
            telemetry = {
                "buses": {},
                "lines": {},
                "breakers": self.breakers.copy()
            }
            
            # Bus Telemetry (convert to polar and p.u.)
            for i in range(self.num_buses):
                v_mag = float(np.abs(V[i]))
                v_ang = float(np.angle(V[i]))
                
                # Check for voltage collapse (disconnected buses)
                if v_mag < 0.1:
                    v_mag = 0.0
                    v_ang = 0.0
                    
                telemetry["buses"][f"Bus_{i+1}"] = {
                    "voltage_pu": round(v_mag, 4),
                    "angle_rad": round(v_ang, 4),
                    "is_load": i in self.load_indices,
                    "is_gen": i in self.gen_indices,
                    "P_mw": round(self.active_loads[i]["P"] * 100, 2) if i in self.load_indices else 0.0,
                    "Q_mvar": round(self.active_loads[i]["Q"] * 100, 2) if i in self.load_indices else 0.0
                }
                
            # Line Telemetry
            for line in self.lines:
                f, t, lid = line["from"], line["to"], line["id"]
                if self.breakers[lid] == "CLOSED":
                    # I = (V_i - V_j) * y
                    y = 1.0 / (line["R"] + 1j * line["X"])
                    I_line = (V[f] - V[t]) * y
                    I_mag = float(np.abs(I_line))
                    
                    # S_from = V_i * I_line*
                    S_from = V[f] * np.conj(I_line)
                    P_flow = float(np.real(S_from))
                    Q_flow = float(np.imag(S_from))
                else:
                    I_mag = 0.0
                    P_flow = 0.0
                    Q_flow = 0.0
                
                # Overcurrent flag (> 3.5 p.u. load current or line capacity limits)
                capacity = 3.0
                load_pct = (I_mag / capacity) * 100
                
                telemetry["lines"][lid] = {
                    "current_pu": round(I_mag, 4),
                    "current_amp": round(I_mag * 500, 2), # Scaling factor to Amps
                    "P_mw": round(P_flow * 100, 2),
                    "Q_mvar": round(Q_flow * 100, 2),
                    "capacity_pct": round(load_pct, 1),
                    "overcurrent": I_mag > capacity
                }
                
            return telemetry

    def execute_breaker_command(self, line_id, state):
        with self.lock:
            if line_id in self.breakers:
                self.breakers[line_id] = state
                logger.info(f"Breaker '{line_id}' status set to: {state}")
            else:
                logger.warning(f"Attempted to control invalid breaker id: {line_id}")

    def apply_attack(self, telemetry):
        """
        Applies cyber security attacks to the solved telemetry payload.
        """
        if not self.active_attack:
            # Default state: record normal telemetry if requested
            if self.recording:
                self.replay_buffer.append(json.loads(json.dumps(telemetry)))
                if len(self.replay_buffer) > 60: # Limit buffer to 60 seconds
                    self.replay_buffer.pop(0)
            return telemetry

        attack_type = self.active_attack
        target = self.attack_config.get("target")
        
        # 1. False Data Injection Attack (FDIA)
        if attack_type == "FDIA":
            # Scale or offset sensor measurements
            bias = self.attack_config.get("bias", 0.0)
            scale = self.attack_config.get("scale", 1.0)
            
            if target in telemetry["buses"]:
                orig = telemetry["buses"][target]["voltage_pu"]
                telemetry["buses"][target]["voltage_pu"] = round(orig * scale + bias, 4)
            elif target in telemetry["lines"]:
                orig = telemetry["lines"][target]["current_amp"]
                telemetry["lines"][target]["current_amp"] = round(orig * scale + bias * 500, 2)
                telemetry["lines"][target]["current_pu"] = round((orig * scale + bias * 500) / 500, 4)
                
        # 2. Replay Attack
        elif attack_type == "REPLAY":
            if self.replay_buffer:
                replay_payload = self.replay_buffer[self.replay_index % len(self.replay_buffer)]
                self.replay_index += 1
                logger.info(f"Replaying historical telemetry index {self.replay_index}")
                
                # Keep real timestamps but use historical sensor readings
                replay_payload["timestamp"] = telemetry["timestamp"]
                return replay_payload
            else:
                logger.warning("Replay attack active but replay buffer is empty!")
                
        # 3. Denial of Service (DoS) is handled by dropping gateway forwarding
        return telemetry

# MQTT Event handlers for Simulator
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info("Simulator connected to MQTT!")
        client.subscribe("grid/control")
        client.subscribe("grid/attack")
    else:
        logger.error(f"Simulator failed to connect, rc {rc}")

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode("utf-8"))
        if msg.topic == "grid/control":
            cmd = payload.get("command")
            target = payload.get("target")
            if cmd in ["OPEN", "CLOSE"] and target:
                sim.execute_breaker_command(target, "CLOSED" if cmd == "CLOSE" else "OPEN")
                # Publish event log
                event_log = {
                    "timestamp": int(time.time() * 1000),
                    "source": "SCADA_OPERATOR",
                    "event": f"Breaker '{target}' commanded {cmd}",
                    "severity": "INFO"
                }
                client.publish("grid/events", json.dumps(event_log))
                
        elif msg.topic == "grid/attack":
            action = payload.get("action")
            if action == "START":
                sim.active_attack = payload.get("type")
                sim.attack_config = payload.get("config", {})
                logger.info(f"Cyber Attack activated: {sim.active_attack} on {sim.attack_config.get('target')}")
                
                # Log attack start event
                event_log = {
                    "timestamp": int(time.time() * 1000),
                    "source": "CYBER_ATTACK_ENGINE",
                    "event": f"Active Cyber Attack initiated: {sim.active_attack} targeting {sim.attack_config.get('target')}",
                    "severity": "CRITICAL"
                }
                client.publish("grid/events", json.dumps(event_log))
                
            elif action == "STOP":
                logger.info(f"Cyber Attack stopped: {sim.active_attack}")
                event_log = {
                    "timestamp": int(time.time() * 1000),
                    "source": "CYBER_ATTACK_ENGINE",
                    "event": f"Cyber Attack {sim.active_attack} terminated. Grid restoring nominal sensors.",
                    "severity": "INFO"
                }
                client.publish("grid/events", json.dumps(event_log))
                sim.active_attack = None
                sim.attack_config = {}
                
            elif action == "RECORD_START":
                sim.recording = True
                sim.replay_buffer = []
                logger.info("Recording normal telemetry for future replay attack...")
                
            elif action == "RECORD_STOP":
                sim.recording = False
                logger.info(f"Recording stopped. Buffered {len(sim.replay_buffer)} telemetry frames.")
                
    except Exception as e:
        logger.error(f"Error handling message on simulator: {e}")

if __name__ == "__main__":
    # Create simulator instance
    sim = IEEE9BusSimulator()
    
    # Initialize MQTT client
    client = mqtt.Client(client_id="digital_twin_simulator")
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
        client.loop_start()
    except Exception as e:
        logger.error(f"Failed to connect simulator to MQTT broker: {e}")
        time.sleep(5)
        # Exit to allow docker-compose reboot restart
        os._exit(1)
        
    logger.info("Digital Twin Grid Simulator successfully started. Spinning simulation loops...")
    
    # Main simulation loop
    while True:
        try:
            # Solve physical power flow
            telemetry = sim.solve_power_flow()
            telemetry["timestamp"] = int(time.time() * 1000)
            
            # Apply cyber tampering if active
            telemetry = sim.apply_attack(telemetry)
            
            # Publish to broker
            client.publish("grid/telemetry", json.dumps(telemetry))
            
            time.sleep(1.0)
        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.error(f"Error in simulation step loop: {e}")
            time.sleep(1.0)
            
    client.loop_stop()
    client.disconnect()
