import os
import time
import json
import random
import logging
import copy
from typing import Dict, Any, List

from grid_topology import GridTopology
from physics import GridPhysicsEngine
from publisher import TelemetryPublisher

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("digital_twin.main")

class SmartGridDigitalTwin:
    def __init__(self):
        self.topo = GridTopology()
        self.physics = GridPhysicsEngine(self.topo)
        
        # Initialize dynamic breaker states from topology
        self.breakers = {line["id"]: "CLOSED" for line in self.topo.lines}
        # L7_8 starts as normally open tie line
        self.breakers["L7_8"] = "OPEN"
        
        # Initialize dynamic loads
        self.active_loads = {}
        for bus_idx, load in self.topo.loads.items():
            self.active_loads[bus_idx] = {
                "P": load["P_nom"],
                "Q": load["Q_nom"]
            }
            
        # Generator setpoints
        self.generator_P = {k: v["P_nom"] for k, v in self.topo.generators.items()}
        self.generator_Q = {k: v["Q_nom"] for k, v in self.topo.generators.items()}
        self.generators_online = {0: True, 1: True, 2: True}
        
        # Island frequency states
        self.island_frequencies = {}
        self.island_freq_violations = {}
        
        # Configuration
        self.simulation_interval = 1.0 # seconds
        self.load_shed_factors = {bus_idx: 1.0 for bus_idx in self.topo.loads.keys()}
        
        # Attack states
        self.active_attack = None
        self.attack_config = {}
        self.recording = False
        self.replay_buffer = []
        self.replay_index = 0
        
        # Scenario engine states
        self.active_scenario = None
        self.scenario_elapsed_time = 0.0
        self.active_compromises = {}
        self.sensor_drifts = {}
        
        # Predefined Attack Scenarios
        self.predefined_scenarios = {
            "coordinated_cascade": [
                {"time": 0, "type": "SENSOR_SPOOFING", "target": "Bus_5", "config": {"noise": 0.04, "drift": -0.015}, "desc": "Phase 1: Substation 5 PT Sensor Drift"},
                {"time": 5, "type": "BREAKER_MANIPULATION", "target": "L4_5", "config": {"command": "OPEN"}, "desc": "Phase 2: Unauthorized Trip of Line 4-5"},
                {"time": 10, "type": "DOS", "target": "Bus_6", "config": {}, "desc": "Phase 3: DoS Attack on Bus 6 Comm Link"},
                {"time": 15, "type": "FDIA", "target": "Bus_9", "config": {"bias": 0.18, "scale": 1.05}, "desc": "Phase 4: Coordinated FDIA on Bus 9"},
                {"time": 20, "type": "BREAKER_MANIPULATION", "target": "L1_4", "config": {"command": "OPEN"}, "desc": "Phase 5: Coordinated Outage Cascade"}
            ],
            "stealthy_fdia": [
                {"time": 0, "type": "FDIA", "target": "Bus_5", "config": {"bias": 0.03, "scale": 1.0}, "desc": "Phase 1: Stealthy Injection on Bus 5 (+0.03 pu)"},
                {"time": 6, "type": "FDIA", "target": "Bus_6", "config": {"bias": 0.06, "scale": 1.0}, "desc": "Phase 2: Stealthy Injection on Bus 6 (+0.06 pu)"},
                {"time": 12, "type": "FDIA", "target": "Bus_8", "config": {"bias": 0.12, "scale": 1.05}, "desc": "Phase 3: Cumulative Spoofing on Bus 8 (+0.12 pu)"}
            ],
            "coordinated_cyber_physical": [
                {"time": 0, "type": "DOS", "target": "L7_8", "config": {}, "desc": "Phase 1: DoS Jamming on restoration line L7_8"},
                {"time": 5, "type": "BREAKER_MANIPULATION", "target": "L4_9", "config": {"command": "OPEN"}, "desc": "Phase 2: Intrusion on Line 4-9 Breaker"},
                {"time": 10, "type": "SENSOR_SPOOFING", "target": "Bus_4", "config": {"noise": 0.06}, "desc": "Phase 3: High-Noise Spoofing on Bus 4"}
            ]
        }
        
        # Setup publisher
        mqtt_broker = os.getenv("MQTT_BROKER", "localhost")
        mqtt_port = int(os.getenv("MQTT_PORT", 1883))
        
        # PYPY Stabilization Arc States
        self.attack_steps = {}
        self.breaker_lockouts = {}
        self.scheduled_actions = []
        self.attacker_retrips = {}
        
        self.publisher = TelemetryPublisher(
            broker=mqtt_broker,
            port=mqtt_port,
            on_control_cmd=self.handle_control_cmd,
            on_attack_cmd=self.handle_attack_cmd,
            on_config_cmd=self.handle_config_cmd
        )

    def _is_safe_topology_after_action(self, target: str, action: str) -> bool:
        # Simulate breakers state after action
        temp_breakers = self.breakers.copy()
        new_status = "CLOSED" if action == "CLOSE" else "OPEN"
        temp_breakers[target] = new_status
        
        # Build adjacency list of buses (0-indexed)
        adj = {i: [] for i in range(self.topo.num_buses)}
        for line in self.topo.lines:
            lid = line["id"]
            if temp_breakers.get(lid, "CLOSED") == "CLOSED":
                adj[line["from"]].append(line["to"])
                adj[line["to"]].append(line["from"])
                
        # Find connected components
        visited = [False] * self.topo.num_buses
        components = []
        for i in range(self.topo.num_buses):
            if not visited[i]:
                comp = []
                queue = [i]
                visited[i] = True
                while queue:
                    curr = queue.pop(0)
                    comp.append(curr)
                    for neighbor in adj[curr]:
                        if not visited[neighbor]:
                            visited[neighbor] = True
                            queue.append(neighbor)
                components.append(comp)
                
        # Check if any component has loads but NO generator
        for comp in components:
            has_load = any(idx in self.topo.loads for idx in comp)
            has_gen = any(idx in self.topo.generators for idx in comp)
            if has_load and not has_gen:
                return False
        return True

    def handle_control_cmd(self, target: str, command: str, payload: Dict[str, Any] = None):
        """
        Callback for remote control command: sets breaker status.
        Bypassed if breaker communication is blocked by active DoS.
        """
        if target == "SYSTEM" and command == "RESET_ALARMS":
            logger.info("Resetting digital twin simulator transient and thermal state, breakers, and active attacks.")
            self.prev_telemetry = None
            self.physics.prev_currents = {}
            self.breakers = {line["id"]: "CLOSED" for line in self.topo.lines}
            self.breakers["L7_8"] = "OPEN"
            self.breaker_lockouts.clear()
            self.scheduled_actions.clear()
            self.attacker_retrips.clear()
            self.attack_steps.clear()
            self.active_attack = None
            self.attack_config = {}
            self.active_scenario = None
            self.active_compromises = {}
            self.sensor_drifts = {}
            self.load_shed_factors = {bus_idx: 1.0 for bus_idx in self.topo.loads.keys()}
            self.generators_online = {0: True, 1: True, 2: True}
            self.generator_P = {k: v["P_nom"] for k, v in self.topo.generators.items()}
            self.generator_Q = {k: v["Q_nom"] for k, v in self.topo.generators.items()}
            self.island_frequencies.clear()
            self.island_freq_violations.clear()
            return

        if command == "REJECT_TELEMETRY":
            logger.info(f"Operator distrusted sensor {target}. Triggering attacker adaptive escalation loop.")
            if self.active_attack:
                neighbors = {
                    "Bus_5": ["Bus_4", "Bus_6"],
                    "Bus_4": ["Bus_1", "Bus_5", "Bus_9"],
                    "Bus_6": ["Bus_5", "Bus_7"],
                    "Bus_9": ["Bus_3", "Bus_4", "Bus_8"],
                    "Bus_8": ["Bus_7", "Bus_9"],
                    "Bus_7": ["Bus_2", "Bus_6", "Bus_8"],
                    "L4_5": ["L1_4", "L5_6"],
                    "L5_6": ["L4_5", "L6_7"],
                    "L7_8": ["L6_7", "L8_9"]
                }
                candidates = neighbors.get(target, ["Bus_5"])
                for cand in candidates:
                    if cand not in self.active_compromises:
                        self.active_compromises[cand] = {
                            "type": "FDIA" if "Bus" in cand else "SENSOR_SPOOFING",
                            "config": {"bias": 0.12, "scale": 1.05, "noise": 0.04}
                        }
                        logger.warning(f"[ATTACK ESCALATION] Attacker retaliated by compromising neighbor {cand}!")
                        self.publisher.publish_event(
                            source="ATTACK_ORCHESTRATOR",
                            event_desc=f"Attacker Escalation: retaliated against distrust on '{target}' by compromising neighbor '{cand}'",
                            severity="CRITICAL"
                        )
                        break
            return

        if command == "SHED_LOAD":
            try:
                bus_idx = int(target.replace("Bus_", "")) - 1
                pct = payload.get("percentage", 0.0) if payload else 0.0
                self.load_shed_factors[bus_idx] = max(0.0, min(1.0, 1.0 - (pct / 100.0)))
                logger.info(f"Load shedding of {pct}% applied to bus '{target}' (factor={self.load_shed_factors[bus_idx]})")
                self.publisher.publish_event(
                    source="SCADA_GATEWAY",
                    event_desc=f"Load shedding of {pct}% applied to bus '{target}'",
                    severity="WARNING"
                )
            except Exception as e:
                logger.error(f"Failed to process SHED_LOAD command for target {target}: {e}")
            return

        if command == "START_GEN":
            try:
                gen_idx = None
                if "1" in target:
                    gen_idx = 0
                elif "2" in target:
                    gen_idx = 1
                elif "3" in target:
                    gen_idx = 2
                
                if gen_idx is not None:
                    self.generators_online[gen_idx] = True
                    self.generator_P[gen_idx] = self.topo.generators[gen_idx]["P_nom"]
                    self.generator_Q[gen_idx] = self.topo.generators[gen_idx]["Q_nom"]
                    logger.info(f"Generator {target} (index {gen_idx}) started online.")
                    self.publisher.publish_event(
                        source="SCADA_GATEWAY",
                        event_desc=f"Generator '{target}' started online",
                        severity="INFO"
                    )
            except Exception as e:
                logger.error(f"Failed to start generator {target}: {e}")
            return

        if command == "STOP_GEN":
            try:
                gen_idx = None
                if "1" in target:
                    gen_idx = 0
                elif "2" in target:
                    gen_idx = 1
                elif "3" in target:
                    gen_idx = 2
                
                if gen_idx is not None:
                    self.generators_online[gen_idx] = False
                    logger.info(f"Generator {target} (index {gen_idx}) stopped offline.")
                    self.publisher.publish_event(
                        source="SCADA_GATEWAY",
                        event_desc=f"Generator '{target}' stopped offline",
                        severity="WARNING"
                    )
            except Exception as e:
                logger.error(f"Failed to stop generator {target}: {e}")
            return

        if command == "ADJUST_GEN":
            try:
                gen_idx = None
                if "1" in target:
                    gen_idx = 0
                elif "2" in target:
                    gen_idx = 1
                elif "3" in target:
                    gen_idx = 2
                
                if gen_idx is not None:
                    p_mw = payload.get("P_mw") if payload else None
                    if p_mw is not None:
                        p_pu = float(p_mw) / 100.0
                        self.generator_P[gen_idx] = p_pu
                        logger.info(f"Adjusted generator {target} (index {gen_idx}) P to {p_mw} MW ({p_pu:.3f} pu)")
                        self.publisher.publish_event(
                            source="SCADA_GATEWAY",
                            event_desc=f"Generator '{target}' output adjusted to {p_mw:.1f} MW",
                            severity="INFO"
                        )
            except Exception as e:
                logger.error(f"Failed to adjust generator {target}: {e}")
            return

        # 1. Check if the target breaker is jammed by DoS
        if target in self.active_compromises:
            comp = self.active_compromises[target]
            if comp.get("type") == "DOS":
                logger.warning(f"Control command BLOCKED: Breaker {target} is under DoS jamming!")
                self.publisher.publish_event(
                    source="SCADA_GATEWAY",
                    event_desc=f"Control command BLOCKED: Breaker {target} communication link jammed by DoS",
                    severity="WARNING"
                )
                return

        # 2. Extract sender source from payload
        source = payload.get("source", "OPERATOR") if payload else "OPERATOR"

        # 3. Check Lockout state
        if command == "CLOSE" and self.breaker_lockouts.get(target, False):
            logger.warning(f"Control command BLOCKED: Breaker {target} is locked out by relay protection. Reset alarms first.")
            self.publisher.publish_event(
                source="SCADA_GATEWAY",
                event_desc=f"Control command BLOCKED: Breaker {target} is locked out by relay protection.",
                severity="WARNING"
            )
            return

        # 4. Check safe topology for manual operator trip
        if command == "OPEN" and source == "OPERATOR" and target in self.breakers:
            if not self._is_safe_topology_after_action(target, "OPEN"):
                logger.warning(f"Control command BLOCKED: Opening breaker {target} would isolate critical loads.")
                self.publisher.publish_event(
                    source="SCADA_GATEWAY",
                    event_desc=f"Control command BLOCKED: Manual trip of '{target}' would isolate load components with no generator.",
                    severity="WARNING"
                )
                return

        # 5. Execute control action if allowed
        if target in self.breakers:
            new_status = "CLOSED" if command == "CLOSE" else "OPEN"
            if self.breakers[target] != new_status:
                # If command is OPEN and comes from RELAY, lock it out statefully
                if new_status == "OPEN" and source == "RELAY":
                    self.breaker_lockouts[target] = True
                    logger.warning(f"Breaker {target} tripped by protective relay and LOCKED OUT statefully.")
                
                self.breakers[target] = new_status
                logger.info(f"Breaker control executed: {target} set to {new_status} (Source: {source})")
                self.publisher.publish_event(
                    source="SCADA_GATEWAY",
                    event_desc=f"Breaker switch '{target}' commanded to {command} by {source}",
                    severity="INFO"
                )

                # Attacker Persistence logic for BREAKER_MANIPULATION cyberattacks
                if command == "CLOSE" and target in self.active_compromises:
                    comp = self.active_compromises[target]
                    if comp.get("type") == "BREAKER_MANIPULATION":
                        retrips = self.attacker_retrips.get(target, 0)
                        if retrips < 3:
                            self.attacker_retrips[target] = retrips + 1
                            # Schedule re-trip command in 3 sweeps
                            re_trip_time = time.time() + 3.0
                            self.scheduled_actions.append((re_trip_time, target, "OPEN"))
                            logger.warning(f"[ATTACK PERSISTENCE] Operator closed compromised breaker {target}. Re-trip scheduled in 3s (attempt {retrips+1}/3).")
                            self.publisher.publish_event(
                                source="ATTACK_ORCHESTRATOR",
                                event_desc=f"Attacker Persistence: detected closure of compromised breaker '{target}'. Scheduling re-trip.",
                                severity="WARNING"
                            )
        else:
            logger.warning(f"Control command received for invalid breaker target: {target}")

    def handle_attack_cmd(self, payload: Dict[str, Any]):
        """
        Callback for cyber attack configurations.
        """
        action = payload.get("action")
        
        if action == "START":
            self.active_attack = payload.get("type")
            self.attack_config = payload.get("config", {})
            self.active_compromises = {
                self.attack_config.get("target"): {
                    "type": self.active_attack,
                    "config": self.attack_config
                }
            }
            logger.info(f"Initiated single-node cyber attack simulation: {self.active_attack}")
            self.publisher.publish_event(
                source="ATTACK_ORCHESTRATOR",
                event_desc=f"Cyber Attack activated: {self.active_attack} targeting {self.attack_config.get('target')}",
                severity="CRITICAL"
            )
            
            if self.active_attack == "BREAKER_MANIPULATION":
                target = self.attack_config.get("target")
                cmd = self.attack_config.get("command", "OPEN")
                if target in self.breakers:
                    self.breakers[target] = cmd
                    logger.info(f"[ATTACK EVENT] Forced single-node breaker manipulation on {target} -> {cmd}")
            
        elif action == "START_SCENARIO":
            scen_name = payload.get("scenario_name", "coordinated_cascade")
            custom_stages = payload.get("stages")
            
            if custom_stages:
                stages = custom_stages
                scen_name = "custom_scenario"
            else:
                stages = self.predefined_scenarios.get(scen_name, self.predefined_scenarios["coordinated_cascade"])
            
            self.active_attack = "SCENARIO"
            self.active_scenario = {
                "name": scen_name,
                "stages": copy.deepcopy(stages)
            }
            self.scenario_elapsed_time = 0.0
            self.active_compromises = {}
            self.sensor_drifts = {}
            
            logger.info(f"Initiated Advanced Scenario: {scen_name}")
            self.publisher.publish_event(
                source="ATTACK_ORCHESTRATOR",
                event_desc=f"Cyber Attack Scenario activated: {scen_name}",
                severity="CRITICAL"
            )
            
        elif action == "STOP":
            logger.info(f"Terminated cyber attack simulation: {self.active_attack}")
            self.publisher.publish_event(
                source="ATTACK_ORCHESTRATOR",
                event_desc=f"Cyber Attack simulation disabled. Sensors nominal.",
                severity="INFO"
            )
            self.active_attack = None
            self.attack_config = {}
            self.active_scenario = None
            self.active_compromises = {}
            self.sensor_drifts = {}
            self.prev_telemetry = None
            self.physics.prev_currents = {}
            
        elif action == "RECORD_START":
            self.recording = True
            self.replay_buffer = []
            logger.info("Recording nominal state telemetry for Replay Attack buffer...")
            
        elif action == "RECORD_STOP":
            self.recording = False
            logger.info(f"Replay recording finalized. Recorded {len(self.replay_buffer)} telemetry frames.")

    def handle_config_cmd(self, payload: Dict[str, Any]):
        """
        Callback for runtime grid simulator settings.
        """
        interval = payload.get("simulation_interval")
        if interval:
            self.simulation_interval = float(interval)
            logger.info(f"Simulation sweep interval set to {self.simulation_interval}s")

    def run_simulation_sweep(self):
        """
        Calculates power flow, creates JSON telemetry payload, and applies cyber tampering.
        """
        # 0. Process Scheduled Re-trip Actions
        now = time.time()
        for act in list(self.scheduled_actions):
            exec_time, tgt, cmd = act
            if now >= exec_time:
                self.scheduled_actions.remove(act)
                if cmd == "OPEN" and self.breakers.get(tgt) == "CLOSED":
                    self.breakers[tgt] = "OPEN"
                    logger.warning(f"[ATTACK PERSISTENCE] Attacker re-tripped breaker {tgt}!")
                    self.publisher.publish_event(
                        source="ATTACK_ORCHESTRATOR",
                        event_desc=f"Attacker Persistence: compromised breaker '{tgt}' re-tripped automatically.",
                        severity="CRITICAL"
                    )

        # Increment attack steps for active compromises
        for tgt in self.active_compromises:
            self.attack_steps[tgt] = self.attack_steps.get(tgt, 0) + 1

        # 1. Update Scenario Timeline Scheduler
        if self.active_attack == "SCENARIO" and self.active_scenario:
            stages = self.active_scenario["stages"]
            for stage in stages:
                if self.scenario_elapsed_time >= stage["time"] and not stage.get("activated", False):
                    stage["activated"] = True
                    target = stage["target"]
                    stype = stage["type"]
                    desc = stage["desc"]
                    
                    # Force breaker trip immediately if breaker manipulation
                    if stype == "BREAKER_MANIPULATION":
                        cmd = stage["config"].get("command", "OPEN")
                        if target in self.breakers:
                            self.breakers[target] = cmd
                            logger.info(f"[SCENARIO EVENT] Forced breaker manipulation on {target} -> {cmd}")
                            self.publisher.publish_event(
                                source="ATTACK_ORCHESTRATOR",
                                event_desc=f"Breaker manipulation: forced {target} to {cmd} ({desc})",
                                severity="CRITICAL"
                            )
                    else:
                        logger.info(f"[SCENARIO EVENT] Activated {stype} compromise on {target} ({desc})")
                        self.publisher.publish_event(
                            source="ATTACK_ORCHESTRATOR",
                            event_desc=f"Compromised node status: {target} under {stype} ({desc})",
                            severity="CRITICAL"
                        )
                        
                    # Cache under active compromises
                    self.active_compromises[target] = stage

        # 2. Simulate small load fluctuations (representing standard grid demand profile variance)
        for bus_idx in self.topo.loads.keys():
            nominal_p = self.topo.loads[bus_idx]["P_nom"]
            nominal_q = self.topo.loads[bus_idx]["Q_nom"]
            factor = self.load_shed_factors.get(bus_idx, 1.0)
            
            # Fluctuations within +/- 3%
            self.active_loads[bus_idx]["P"] = max(0.0, (nominal_p + random.uniform(-0.03, 0.03)) * factor)
            self.active_loads[bus_idx]["Q"] = max(0.0, (nominal_q + random.uniform(-0.015, 0.015)) * factor)
            
        # 3. Run DC power flow & voltage drop solver
        V, theta, P, Q, line_flows = self.physics.solve(
            self.breakers, 
            self.active_loads, 
            self.generator_P, 
            self.generator_Q,
            self.generators_online
        )
        
        # Calculate dynamic frequency per island and execute frequency trips
        components = self.physics._get_components(self.breakers)
        new_frequencies = {}
        tripped_something = False
        
        for comp in components:
            comp_key = ",".join(map(str, sorted(comp)))
            
            # Check online generators in this component
            online_gens = [b for b in comp if b in self.topo.generators and self.generators_online.get(b, True)]
            if not online_gens:
                new_frequencies[comp_key] = 0.0
                self.island_freq_violations[comp_key] = 0
                continue
                
            # Mismatch in MW
            comp_gen_p_mw = sum(self.generator_P[b] for b in online_gens) * 100.0
            comp_load_p_mw = sum(self.active_loads[b]["P"] for b in comp if b in self.topo.loads) * 100.0
            mismatch_mw = comp_gen_p_mw - comp_load_p_mw
            
            prev_freq = self.island_frequencies.get(comp_key, 60.0)
            target_freq = 60.0 + mismatch_mw * 0.02
            alpha = 0.30
            freq = prev_freq + alpha * (target_freq - prev_freq)
            freq = max(55.0, min(65.0, freq))
            new_frequencies[comp_key] = freq
            
            # Check frequency breach limits
            if freq < 57.5 or freq > 62.5:
                v_count = self.island_freq_violations.get(comp_key, 0) + 1
                self.island_freq_violations[comp_key] = v_count
                if v_count >= 2:
                    logger.warning(f"FREQUENCY BREACH: Island {comp_key} at {freq:.2f} Hz for 2 sweeps. Tripping.")
                    self.publisher.publish_event( source="PROTECTION_RELAY",
                        event_desc=f"Frequency protection trip: island {comp_key} frequency {freq:.2f} Hz breached threshold",
                        severity="CRITICAL"
                    )
                    # Turn off generators in this component
                    for b in comp:
                        if b in self.topo.generators:
                            self.generators_online[b] = False
                    # Open line breakers in this component
                    for line in self.topo.lines:
                        if line["from"] in comp and line["to"] in comp:
                            self.breakers[line["id"]] = "OPEN"
                    tripped_something = True
                    self.island_freq_violations[comp_key] = 0
            else:
                self.island_freq_violations[comp_key] = 0
                
        self.island_frequencies = new_frequencies
        
        # If any frequency breach tripped generators or lines, resolve physics so telemetry shows zeroed voltages
        if tripped_something:
            V, theta, P, Q, line_flows = self.physics.solve(
                self.breakers, 
                self.active_loads, 
                self.generator_P, 
                self.generator_Q,
                self.generators_online
            )
            # Re-evaluate frequencies (they will now be 0 because generators are tripped)
            components = self.physics._get_components(self.breakers)
            for comp in components:
                comp_key = ",".join(map(str, sorted(comp)))
                online_gens = [b for b in comp if b in self.topo.generators and self.generators_online.get(b, True)]
                if not online_gens:
                    self.island_frequencies[comp_key] = 0.0

        # Build bus frequencies mapping for telemetry bus representation
        bus_frequencies = {}
        for comp in components:
            comp_key = ",".join(map(str, sorted(comp)))
            freq = self.island_frequencies.get(comp_key, 60.0)
            for b in comp:
                bus_name = f"Bus_{b+1}"
                bus_frequencies[bus_name] = round(freq, 2)

        # 4. Format telemetry payload
        telemetry = {
            "timestamp": int(time.time() * 1000),
            "state": {
                "buses": {},
                "lines": {},
                "breakers": self.breakers.copy(),
                "generators_online": {f"Bus_{k+1}": v for k, v in self.generators_online.items()}
            }
        }
        
        # Map Bus properties
        for i in range(self.topo.num_buses):
            bus_name = f"Bus_{i+1}"
            is_load = i in self.topo.loads
            is_gen = i in self.topo.generators
            
            telemetry["state"]["buses"][bus_name] = {
                "voltage_pu": round(float(V[i]), 4),
                "angle_rad": round(float(theta[i]), 4),
                "is_load": is_load,
                "is_gen": is_gen,
                "frequency_hz": bus_frequencies.get(bus_name, 60.0),
                "P_mw": round(float(self.active_loads[i]["P"] * 100) if is_load else float(P[i] * 100), 2),
                "Q_mvar": round(float(self.active_loads[i]["Q"] * 100) if is_load else float(Q[i] * 100), 2)
            }
            
        # Map Line flows
        for line in self.topo.lines:
            lid = line["id"]
            flow = line_flows[lid]
            
            capacity_limit = 3.0
            capacity_pct = (flow["current"] / capacity_limit) * 100
            
            telemetry["state"]["lines"][lid] = {
                "current_pu": round(flow["current"], 4),
                "current_amp": round(flow["current"] * 500, 2),
                "P_mw": round(flow["P_flow"] * 100, 2),
                "Q_mvar": round(flow["Q_flow"] * 100, 2),
                "capacity_pct": round(capacity_pct, 1),
                "overcurrent": flow["current"] > capacity_limit
            }
            
        # 4.5. Smooth telemetry transitions (grid transient emulation)
        if not hasattr(self, "prev_telemetry") or self.prev_telemetry is None:
            self.prev_telemetry = copy.deepcopy(telemetry)
        else:
            alpha = 0.40  # 40% update rate per step for smooth transient decay
            
            # Smooth buses
            for bus_name, bus_data in telemetry["state"]["buses"].items():
                prev_bus = self.prev_telemetry["state"]["buses"].get(bus_name)
                if prev_bus:
                    bus_data["voltage_pu"] = round(prev_bus["voltage_pu"] + alpha * (bus_data["voltage_pu"] - prev_bus["voltage_pu"]), 4)
                    bus_data["angle_rad"] = round(prev_bus["angle_rad"] + alpha * (bus_data["angle_rad"] - prev_bus["angle_rad"]), 4)
                    bus_data["P_mw"] = round(prev_bus["P_mw"] + alpha * (bus_data["P_mw"] - prev_bus["P_mw"]), 2)
                    bus_data["Q_mvar"] = round(prev_bus["Q_mvar"] + alpha * (bus_data["Q_mvar"] - prev_bus["Q_mvar"]), 2)
            
            # Smooth lines
            for line_id, line_data in telemetry["state"]["lines"].items():
                prev_line = self.prev_telemetry["state"]["lines"].get(line_id)
                if prev_line:
                    line_data["current_pu"] = round(prev_line["current_pu"] + alpha * (line_data["current_pu"] - prev_line["current_pu"]), 4)
                    line_data["current_amp"] = round(prev_line["current_amp"] + alpha * (line_data["current_amp"] - prev_line["current_amp"]), 2)
                    line_data["P_mw"] = round(prev_line["P_mw"] + alpha * (line_data["P_mw"] - prev_line["P_mw"]), 2)
                    line_data["Q_mvar"] = round(prev_line["Q_mvar"] + alpha * (line_data["Q_mvar"] - prev_line["Q_mvar"]), 2)
                    line_data["capacity_pct"] = round(prev_line["capacity_pct"] + alpha * (line_data["capacity_pct"] - prev_line["capacity_pct"]), 1)
                    
            self.prev_telemetry = copy.deepcopy(telemetry)

        # 5. Record normal telemetry buffer for Replay Attacks
        if self.recording and not self.active_attack:
            self.replay_buffer.append(copy.deepcopy(telemetry))
            if len(self.replay_buffer) > 100: # Max buffer depth
                self.replay_buffer.pop(0)
                
        # 6. Apply Cyber Tampering (Attack Vector)
        telemetry = self.apply_attack_tampering(telemetry)
        
        # 7. Add Attack timeline and compromise status to telemetry
        telemetry["attack_status"] = {
            "active_attack": self.active_attack,
            "active_scenario_name": self.active_scenario["name"] if self.active_scenario else None,
            "scenario_time": self.scenario_elapsed_time if self.active_attack == "SCENARIO" else 0.0,
            "compromised_nodes": {
                k: {"type": v["type"], "severity": "CRITICAL" if v["type"] in ["BREAKER_MANIPULATION", "DOS"] else "HIGH"}
                for k, v in self.active_compromises.items()
            },
            "stages": [
                {
                    "time": s["time"],
                    "type": s["type"],
                    "target": s["target"],
                    "desc": s["desc"],
                    "status": "active" if self.scenario_elapsed_time >= s["time"] else "pending"
                }
                for s in (self.active_scenario["stages"] if self.active_scenario else [])
            ]
        }
        
        # 8. Check Scenario termination duration
        if self.active_attack == "SCENARIO" and self.active_scenario:
            max_time = max(s["time"] for s in self.active_scenario["stages"])
            if self.scenario_elapsed_time > max_time + 15.0:
                logger.info(f"Advanced Scenario timeline completed: {self.active_scenario['name']}")
                self.publisher.publish_event(
                    source="ATTACK_ORCHESTRATOR",
                    event_desc=f"Cyber Attack Scenario '{self.active_scenario['name']}' timeline completed.",
                    severity="INFO"
                )
                self.active_attack = None
                self.active_scenario = None
                self.active_compromises = {}
                self.sensor_drifts = {}
            else:
                self.scenario_elapsed_time += self.simulation_interval

        # 9. Publish telemetry broadcast
        self.publisher.publish_telemetry(telemetry)

    def apply_attack_tampering(self, telemetry: Dict[str, Any]) -> Dict[str, Any]:
        if not self.active_attack:
            return telemetry
            
        # Replay Attack overrides the entire frame directly
        if self.active_attack == "REPLAY":
            if self.replay_buffer:
                replay_frame = self.replay_buffer[self.replay_index % len(self.replay_buffer)]
                self.replay_index += 1
                spoofed_frame = copy.deepcopy(replay_frame)
                spoofed_frame["timestamp"] = telemetry["timestamp"]
                return spoofed_frame
            else:
                logger.warning("Replay attack is enabled but replay buffer is empty!")
                return telemetry

        # Apply multi-node compromises (supports scenario attacks as well as single attacks)
        for target, comp in self.active_compromises.items():
            stype = comp["type"]
            config = comp.get("config", {})
            
            # 1. False Data Injection Attack (FDIA)
            if stype == "FDIA":
                ramp = min(1.0, self.attack_steps.get(target, 1) / 5.0)
                bias = config.get("bias", 0.0) * ramp
                scale = 1.0 + (config.get("scale", 1.0) - 1.0) * ramp
                
                if target in telemetry["state"]["buses"]:
                    orig_val = telemetry["state"]["buses"][target]["voltage_pu"]
                    telemetry["state"]["buses"][target]["voltage_pu"] = round(orig_val * scale + bias, 4)
                    
                elif target in telemetry["state"]["lines"]:
                    orig_amp = telemetry["state"]["lines"][target]["current_amp"]
                    new_amp = orig_amp * scale + bias * 500
                    telemetry["state"]["lines"][target]["current_amp"] = round(new_amp, 2)
                    telemetry["state"]["lines"][target]["current_pu"] = round(new_amp / 500, 4)
            
            # 2. Denial of Service (DoS)
            elif stype == "DOS":
                if self.attack_steps.get(target, 1) <= 2:
                    continue  # Delay DoS impact by 2 sweeps
                if target in telemetry["state"]["buses"]:
                    telemetry["state"]["buses"][target]["voltage_pu"] = 0.0
                    telemetry["state"]["buses"][target]["P_mw"] = 0.0
                    telemetry["state"]["buses"][target]["Q_mvar"] = 0.0
                    telemetry["state"]["buses"][target]["angle_rad"] = 0.0
                    telemetry["state"]["buses"][target]["status"] = "COMM_LOSS"
                    
                elif target in telemetry["state"]["lines"]:
                    telemetry["state"]["lines"][target]["current_pu"] = 0.0
                    telemetry["state"]["lines"][target]["current_amp"] = 0.0
                    telemetry["state"]["lines"][target]["P_mw"] = 0.0
                    telemetry["state"]["lines"][target]["Q_mvar"] = 0.0
                    telemetry["state"]["lines"][target]["capacity_pct"] = 0.0
                    telemetry["state"]["lines"][target]["status"] = "COMM_LOSS"
                    
                elif target in telemetry["state"]["breakers"]:
                    telemetry["state"]["breakers"][target] = "OPEN"
            
            # 3. Sensor Spoofing (Drifts & White Noise)
            elif stype == "SENSOR_SPOOFING":
                ramp = min(1.0, self.attack_steps.get(target, 1) / 5.0)
                noise_lvl = config.get("noise", 0.02) * ramp
                drift_rate = config.get("drift", 0.0) * ramp
                
                # Accumulate drift over time
                self.sensor_drifts[target] = self.sensor_drifts.get(target, 0.0) + drift_rate
                noise = random.uniform(-noise_lvl, noise_lvl)
                
                if target in telemetry["state"]["buses"]:
                    orig_val = telemetry["state"]["buses"][target]["voltage_pu"]
                    telemetry["state"]["buses"][target]["voltage_pu"] = round(orig_val + self.sensor_drifts[target] + noise, 4)
                    
                elif target in telemetry["state"]["lines"]:
                    orig_amp = telemetry["state"]["lines"][target]["current_amp"]
                    new_amp = orig_amp + (self.sensor_drifts[target] + noise) * 500
                    telemetry["state"]["lines"][target]["current_amp"] = round(new_amp, 2)
                    telemetry["state"]["lines"][target]["current_pu"] = round(new_amp / 500, 4)
                    
        return telemetry

    def start(self):
        self.publisher.start()
        logger.info("Grid Digital Twin Simulator started. Running main sweep loops...")
        
        try:
            while True:
                start_time = time.time()
                self.run_simulation_sweep()
                
                elapsed = time.time() - start_time
                sleep_time = max(0.01, self.simulation_interval - elapsed)
                time.sleep(sleep_time)
                
        except KeyboardInterrupt:
            logger.info("Grid Simulator shutting down...")
        finally:
            self.publisher.stop()

if __name__ == "__main__":
    twin = SmartGridDigitalTwin()
    twin.start()
