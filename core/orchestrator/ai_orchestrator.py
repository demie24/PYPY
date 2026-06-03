import os
import time
import json
import logging
import sys
import paho.mqtt.client as mqtt
from typing import Dict, Any, Tuple

# Ensure current directory is in path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(CURRENT_DIR)
sys.path.append(os.path.abspath(os.path.join(CURRENT_DIR, "..", "self_healing", "rl")))
sys.path.append(os.path.abspath(os.path.join(CURRENT_DIR, "..", "self_healing")))

try:
    import core.self_healing.rl.rl_metrics as rl_metrics
except ImportError:
    pass

from core.orchestrator.decision_engine import OrchestrationDecisionEngine
from core.orchestrator.action_recommender import ActionRecommender
from core.self_healing.orchestrator_agent import OrchestratorAgent

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("orchestrator.main")

MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))

class OrchestratorMemory:
    def __init__(self):
        self.recent_attacks = {}      # target -> timestamp
        self.unstable_nodes = set()   # nodes with persistent deviations
        self.failed_recoveries = {}   # breaker_id -> timestamp
        self.repeated_attacks = {}    # node -> list of timestamps
        self.unstable_node_counters = {} # node -> consecutive ticks with deviation
        
    def record_attack(self, target: str):
        now = time.time()
        self.recent_attacks[target] = now
        if target not in self.repeated_attacks:
            self.repeated_attacks[target] = []
        self.repeated_attacks[target].append(now)
        # Clean up old timestamps > 300 seconds
        self.repeated_attacks[target] = [t for t in self.repeated_attacks[target] if now - t < 300.0]
        
    def record_deviation(self, node: str, has_deviation: bool):
        if has_deviation:
            self.unstable_node_counters[node] = self.unstable_node_counters.get(node, 0) + 1
            if self.unstable_node_counters[node] >= 3:
                self.unstable_nodes.add(node)
        else:
            self.unstable_node_counters[node] = 0
            if node in self.unstable_nodes:
                self.unstable_nodes.remove(node)
                
    def record_failed_recovery(self, breaker: str):
        self.failed_recoveries[breaker] = time.time()
        
    def is_persistently_targeted(self, node: str) -> bool:
        # If node was attacked >= 3 times in the last 5 minutes
        now = time.time()
        if node in self.repeated_attacks:
            recent = [t for t in self.repeated_attacks[node] if now - t < 300.0]
            return len(recent) >= 3
        return False
        
    def is_recovery_blocked(self, breaker: str) -> bool:
        now = time.time()
        if breaker in self.failed_recoveries:
            if now - self.failed_recoveries[breaker] < 60.0:
                return True
            else:
                del self.failed_recoveries[breaker]
        return False
        
    def clean_expired(self):
        now = time.time()
        # recent attacks expire after 60s
        self.recent_attacks = {k: v for k, v in self.recent_attacks.items() if now - v < 60.0}
        # failed recoveries expire after 60s
        self.failed_recoveries = {k: v for k, v in self.failed_recoveries.items() if now - v < 60.0}

class ThreatResponseSequencer:
    def __init__(self):
        self.state = "MONITORING" # default nominal monitoring
        self.target = None
        self.step = 7
        self.state_timer = time.time()
        
    def transition_to(self, new_state: str, target: str = None):
        logger.info(f"[SEQUENCER] Transitioning state: {self.state} -> {new_state} for target: {target}")
        self.state = new_state
        self.target = target
        self.step = self._get_step_num(new_state)
        self.state_timer = time.time()
        
    def _get_step_num(self, state: str) -> int:
        steps = {
            "DETECTION": 1,
            "VALIDATION": 2,
            "CORRELATION": 3,
            "ISOLATION": 4,
            "REROUTING": 5,
            "RECOVERY": 6,
            "MONITORING": 7
        }
        return steps.get(state, 7)
        
    def update(self, grid_state: dict, decision_report: dict, memory: OrchestratorMemory) -> dict:
        """
        Advances FSM based on decision report and current grid state.
        """
        global_state = decision_report.get("global_state", "NORMAL")
        stability = decision_report.get("stability_score", 100.0)
        
        # If there is no active threat/attack/anomaly, and we are not recovering, keep MONITORING
        if global_state == "NORMAL" and self.state not in ["REROUTING", "RECOVERY", "MONITORING"]:
            self.transition_to("MONITORING")
            return self.get_pipeline_data()
            
        now = time.time()
        
        # FSM Transition Rules
        if self.state == "MONITORING":
            # Check if any deviation is detected (Detection trigger)
            if global_state in ["CYBER_ATTACK", "CASCADING_INSTABILITY", "EMERGENCY_STABILIZATION"]:
                # Identify the target. Find line or bus with deviation/anomaly
                target_node = None
                telemetry = grid_state.get("telemetry")
                if telemetry:
                    attack_status = telemetry.get("attack_status", {})
                    compromised = list(attack_status.get("compromised_nodes", {}).keys())
                    if compromised:
                        target_node = compromised[0]
                        
                if not target_node:
                    # Find first overloaded line
                    lines = telemetry.get("state", {}).get("lines", {}) if telemetry else {}
                    for line_id, l_data in lines.items():
                        if l_data.get("capacity_pct", 0.0) > 100.0:
                            target_node = line_id
                            break
                            
                if not target_node:
                    # Find first voltage deviant bus
                    buses = telemetry.get("state", {}).get("buses", {}) if telemetry else {}
                    for bus_id, b_data in buses.items():
                        v = b_data.get("voltage_pu", 1.0)
                        if abs(v - 1.0) > 0.05:
                            target_node = bus_id
                            break
                            
                self.transition_to("DETECTION", target_node)
                
        elif self.state == "DETECTION":
            if self.target:
                memory.record_attack(self.target)
            self.transition_to("VALIDATION", self.target)
            
        elif self.state == "VALIDATION":
            self.transition_to("CORRELATION", self.target)
            
        elif self.state == "CORRELATION":
            self.transition_to("ISOLATION", self.target)
            
        elif self.state == "ISOLATION":
            self.transition_to("REROUTING", self.target)
            
        elif self.state == "REROUTING":
            self.transition_to("RECOVERY", self.target)
            
        elif self.state == "RECOVERY":
            self.transition_to("MONITORING", self.target)
            
        return self.get_pipeline_data()
        
    def get_pipeline_data(self) -> dict:
        return {
            "state": self.state,
            "step": self.step,
            "target": self.target or "None",
            "timestamp": int(time.time() * 1000)
        }

class AIOrchestrator:
    def __init__(self):
        self.decision_engine = OrchestrationDecisionEngine()
        self.action_recommender = ActionRecommender()
        self.defense_mode = "ADVISORY"
        self.orchestrator_agent = OrchestratorAgent()
        
        # Stateful helper components
        self.memory = OrchestratorMemory()
        self.sequencer = ThreatResponseSequencer()
        
        # Resilience & Throttling tracking
        self.last_cycle_time = 0.0
        self.last_telemetry_timestamp = 0
        self.subsystem_last_update = {
            "LSTM": time.time(),
            "PINN": time.time(),
            "TRUST": time.time()
        }
        
        # Rollback tracking
        self.monitoring_recovery_breaker = None
        self.monitoring_recovery_ticks = 0
        self.monitoring_recovery_start_stability = 100.0
        
        # Unified grid state cache
        self.state_cache = {
            "telemetry": None,
            "ai_forecast": None,
            "multi_bus_forecast": None,
            "threat_aware_forecast": None,
            "physics_validation": None,
            "trust_scores": None,
            "threat": None,
            "flisr_state": "NORMAL",
            "flisr_auto": True,
            "defense": None,
            "l6_recovery": None,
            "l6_adaptive_recovery": None,
            "l6_containment": None,
            "l6_degraded_mode": None,
            "l6_survival": None,
            "l6_islanding": None,
            "l6_blackstart": None,
            "l6_balancing": None,
            "l6_predictive_stability": None,
            "l6_survival_forecast": None,
            "l6_proactive_actions": None,
            "l6_self_preservation": None,
            "l6_agents": None,
            "l6_agent_consensus": None,
            "l6_agent_conflicts": None,
            "l6_distributed_state": None,
            "l6_agent_confidence": None,
            "hardware_attack_state": None,
            "hardware_attack_propagation": None,
            "hardware_orchestration": None,
            "hardware_edge_devices": None,
            "hardware_relay_execution": None,
            "hardware_distributed_bus": None,
            "hardware_synchronization": None,
            "hardware_orchestration_conflicts": None,
            "hardware_telemetry_validation": None,
            "hardware_resilience": None,
            "hardware_disaster_recovery": None,
            "hardware_redundancy": None,
            "hardware_deployment_hardening": None,
            "hardware_large_scale_sync": None
        }

        # Operator overrides and control states
        self.override_state = {
            "pause_autonomous": False,
            "emergency_stop_active": False
        }
        
        # Protection guard tracking
        self.last_breaker_operation_time = 0.0

    def update_state(self, topic, payload):
        """
        Updates the cache based on received topic.
        """
        if topic == "grid/telemetry":
            self.state_cache["telemetry"] = payload
        elif topic == "grid/ai_prediction":
            self.state_cache["ai_forecast"] = payload
            self.subsystem_last_update["LSTM"] = time.time()
        elif topic == "grid/ai_forecast_multi_bus":
            self.state_cache["multi_bus_forecast"] = payload
            self.subsystem_last_update["LSTM"] = time.time()
        elif topic == "grid/ai_threat_forecast":
            self.state_cache["threat_aware_forecast"] = payload
            self.subsystem_last_update["LSTM"] = time.time()
        elif topic == "grid/physics_validation":
            self.state_cache["physics_validation"] = payload
            self.subsystem_last_update["PINN"] = time.time()
        elif topic == "grid/trust_scores":
            self.state_cache["trust_scores"] = payload
            self.subsystem_last_update["TRUST"] = time.time()
        elif topic == "grid/threat":
            self.state_cache["threat"] = payload
        elif topic == "grid/defense":
            self.state_cache["defense"] = payload
        elif topic == "grid/l6_recovery":
            self.state_cache["l6_recovery"] = payload
        elif topic == "grid/l6_adaptive_recovery":
            self.state_cache["l6_adaptive_recovery"] = payload
        elif topic == "grid/l6_containment":
            self.state_cache["l6_containment"] = payload
        elif topic == "grid/l6_degraded_mode":
            self.state_cache["l6_degraded_mode"] = payload
        elif topic == "grid/l6_survival":
            self.state_cache["l6_survival"] = payload
        elif topic == "grid/l6_islanding":
            self.state_cache["l6_islanding"] = payload
        elif topic == "grid/l6_blackstart":
            self.state_cache["l6_blackstart"] = payload
        elif topic == "grid/l6_balancing":
            self.state_cache["l6_balancing"] = payload
        elif topic == "grid/l6_predictive_stability":
            self.state_cache["l6_predictive_stability"] = payload
        elif topic == "grid/l6_survival_forecast":
            self.state_cache["l6_survival_forecast"] = payload
        elif topic == "grid/l6_proactive_actions":
            self.state_cache["l6_proactive_actions"] = payload
        elif topic == "grid/l6_self_preservation":
            self.state_cache["l6_self_preservation"] = payload
        elif topic == "grid/l6_agents":
            self.state_cache["l6_agents"] = payload
            # Synchronize trust and weights statefully
            for agent_info in payload.get("agents", []):
                name = agent_info.get("agent_name")
                if name in self.orchestrator_agent.agents:
                    self.orchestrator_agent.agent_trust[name] = agent_info.get("trust", 1.0)
                    self.orchestrator_agent.agent_weights[name] = agent_info.get("weight", 1.0)
        elif topic == "grid/l6_agent_consensus":
            self.state_cache["l6_agent_consensus"] = payload
        elif topic == "grid/l6_agent_conflicts":
            self.state_cache["l6_agent_conflicts"] = payload
        elif topic == "grid/l6_distributed_state":
            self.state_cache["l6_distributed_state"] = payload
        elif topic == "grid/l6_agent_confidence":
            self.state_cache["l6_agent_confidence"] = payload
        elif topic == "hardware/device_health":
            self.state_cache["hardware_device_health"] = payload
        elif topic == "hardware/faults":
            self.state_cache["hardware_faults"] = payload
        elif topic == "hardware/relay_faults":
            self.state_cache["hardware_relay_faults"] = payload
        elif topic == "hardware/anomalies":
            self.state_cache["hardware_anomalies"] = payload
        elif topic == "hardware/attack_state":
            self.state_cache["hardware_attack_state"] = payload
        elif topic == "grid/pre_rl":
            op_override = payload.get("operator_override", {})
            self.override_state["pause_autonomous"] = op_override.get("pause_autonomous", False)
            self.override_state["emergency_stop_active"] = op_override.get("emergency_stop_active", False)
        elif topic == "grid/config":
            if "flisr_state" in payload:
                self.state_cache["flisr_state"] = payload["flisr_state"]
            if "flisr_auto" in payload:
                self.state_cache["flisr_auto"] = payload["flisr_auto"]
            if "defense_mode" in payload:
                self.defense_mode = payload["defense_mode"]
        elif topic == "hardware/attack_propagation":
            self.state_cache["hardware_attack_propagation"] = payload
        elif topic == "hardware/orchestration":
            self.state_cache["hardware_orchestration"] = payload
        elif topic == "hardware/edge_devices":
            self.state_cache["hardware_edge_devices"] = payload
        elif topic == "hardware/relay_execution":
            self.state_cache["hardware_relay_execution"] = payload
        elif topic == "hardware/distributed_bus":
            self.state_cache["hardware_distributed_bus"] = payload
        elif topic == "hardware/synchronization":
            self.state_cache["hardware_synchronization"] = payload
        elif topic == "hardware/orchestration_conflicts":
            self.state_cache["hardware_orchestration_conflicts"] = payload
        elif topic == "hardware/reliability":
            self.state_cache["hardware_reliability"] = payload
        elif topic == "hardware/telemetry_validation":
            self.state_cache["hardware_telemetry_validation"] = payload
        elif topic == "hardware/resilience":
            self.state_cache["hardware_resilience"] = payload
        elif topic == "hardware/disaster_recovery":
            self.state_cache["hardware_disaster_recovery"] = payload
        elif topic == "hardware/redundancy":
            self.state_cache["hardware_redundancy"] = payload
        elif topic == "hardware/deployment_hardening":
            self.state_cache["hardware_deployment_hardening"] = payload
        elif topic == "hardware/large_scale_sync":
            self.state_cache["hardware_large_scale_sync"] = payload


    def process_quarantine_containment(self, client):
        """
        When a hardware quarantine is detected in the propagation chain,
        automatically isolate the dependent power lines/breakers.
        """
        hardware_prop = self.state_cache.get("hardware_attack_propagation") or {}
        nodes = hardware_prop.get("nodes", [])
        quarantined_nodes = [node["id"] for node in nodes if node.get("status") == "QUARANTINED"]
        
        hardware_attack = self.state_cache.get("hardware_attack_state")
        if hardware_attack:
            quarantined_ports = hardware_attack.get("quarantined_ports", [])
            for port in quarantined_ports:
                port_id = port
                if port == "Port 7":
                    port_id = "USB_Port_7"
                elif port == "ESP32":
                    port_id = "ESP32_Bridge"
                elif port == "PLC":
                    port_id = "PLC_Modbus_Gateway"
                
                if port_id not in quarantined_nodes:
                    quarantined_nodes.append(port_id)
                    
        if not quarantined_nodes:
            return
            
        device_dependency = {
            "USB_Port_7": ["L1_4", "L2_7", "L3_9", "L4_5", "L4_9", "L5_6"],
            "ESP32_Bridge": ["L1_4", "L2_7", "L3_9", "L4_5", "L4_9", "L5_6"],
            "PLC_Modbus_Gateway": ["L6_7", "L7_8", "L8_9"],
            "Breaker_Relays": ["L6_7", "L7_8", "L8_9"]
        }
        
        telemetry = self.state_cache.get("telemetry")
        breakers_state = telemetry.get("state", {}).get("breakers", {}) if telemetry else {}
        
        for qnode in quarantined_nodes:
            dependent_breakers = device_dependency.get(qnode, [])
            for breaker in dependent_breakers:
                current_state = breakers_state.get(breaker, "CLOSED")
                if current_state in ["CLOSED", "CLOSE"]:
                    logger.warning(f"[DEFENSIVE COORDINATION] Quarantined interface {qnode} detected. Automatically isolating dependent breaker {breaker}.")
                    isolate_payload = {
                        "command": "OPEN",
                        "target": breaker,
                        "source": "AI_ORCHESTRATOR"
                    }
                    client.publish("grid/control", json.dumps(isolate_payload))

    def evaluate_proposed_command(self, cmd: str, target: str, source: str) -> Tuple[bool, str]:
        """
        Intercepts proposed commands and evaluates them using safety constraints, trust metrics,
        and simultaneous action protections.
        """
        if self.override_state.get("emergency_stop_active", False):
            return False, "Emergency stop active."
            
        if self.override_state.get("pause_autonomous", False):
            return False, "Autonomous execution paused by operator override."

        # Cooldown check for failed recovery breakers
        if cmd in ["CLOSE", "CLOSED"] and self.memory.is_recovery_blocked(target):
            if source != "SCADA_OPERATOR":
                return False, f"Blocked proposed command on {target}: Breaker is cooling down after a failed recovery attempt."

        # Hardware Attack Layer / Quarantine & Compromise Checks
        hardware_attack = self.state_cache.get("hardware_attack_state") or {}
        quarantined_ports = hardware_attack.get("quarantined_ports", [])
        
        # Map quarantined ports/interfaces to dependent breakers
        device_dependency = {
            "ESP32": ["L1_4", "L2_7", "L3_9", "L4_5", "L4_9", "L5_6"],
            "Port 7": ["L1_4", "L2_7", "L3_9", "L4_5", "L4_9", "L5_6"],
            "USB_Port_7": ["L1_4", "L2_7", "L3_9", "L4_5", "L4_9", "L5_6"],
            "ESP32_Bridge": ["L1_4", "L2_7", "L3_9", "L4_5", "L4_9", "L5_6"],
            "PLC": ["L6_7", "L7_8", "L8_9"],
            "PLC_Modbus_Gateway": ["L6_7", "L7_8", "L8_9"],
            "Breaker_Relays": ["L6_7", "L7_8", "L8_9"]
        }

        for port in quarantined_ports:
            if str(port) in target or target in str(port):
                return False, f"Blocked proposed command on {target}: Target interface/port {port} is quarantined."
            dependent_breakers = device_dependency.get(port, [])
            if target in dependent_breakers:
                return False, f"Blocked proposed command on {target}: Dependent interface/port {port} is quarantined."

        hardware_prop = self.state_cache.get("hardware_attack_propagation") or {}
        nodes = hardware_prop.get("nodes", [])
        for node in nodes:
            if node.get("status") == "QUARANTINED":
                dependent_breakers = device_dependency.get(node["id"], [])
                if target in dependent_breakers:
                    return False, f"Blocked proposed command on {target}: Dependent interface {node['id']} is quarantined."

        escalation = hardware_attack.get("attack_escalation_state", "NOMINAL")
        if escalation == "COMPROMISED":
            # Decay agent trust statefully
            for agent_name in self.orchestrator_agent.agent_trust:
                self.orchestrator_agent.agent_trust[agent_name] = max(0.1, self.orchestrator_agent.agent_trust[agent_name] - 0.05)
            logger.warning("Decayed AI agent trust levels due to COMPROMISED hardware attack state.")
            # Quarantine proposed commands
            if source != "SCADA_OPERATOR":
                return False, f"Blocked proposed command on {target}: Hardware layer is COMPROMISED. Proposed action quarantined."

        # Stuck/Welded/Desynced Relays Check
        relay_faults = self.state_cache.get("hardware_relay_faults") or {}
        stuck_breakers = relay_faults.get("stuck", [])
        welded_breakers = relay_faults.get("welded", [])
        desynced_breakers = relay_faults.get("desynced", [])
        
        if target in stuck_breakers:
            return False, f"Blocked proposed command on {target}: Relay is stuck at hardware layer."
        if target in welded_breakers:
            return False, f"Blocked proposed command on {target}: Relay contacts welded CLOSED."
        if target in desynced_breakers:
            return False, f"Blocked proposed command on {target}: Relay desynchronized."

        # Evaluate current grid decision report
        report = self.decision_engine.evaluate(self.state_cache)
        stability = report.get("stability_score", 100.0)
        global_state = report.get("global_state", "NORMAL")

        is_restoration = cmd in ["CLOSE", "CLOSED"] or source in ["FLISR", "AI_RL_PPO_CONTROL", "BLACKSTART_ENGINE"] or cmd in ["RECONNECT_LINE", "REROUTE_FLOW"]

        # 1. Topology Survival: Reject restoration if stability is poor
        if is_restoration and stability < 70.0:
            return False, f"Blocked restoration under low stability: stability score {stability:.1f}% is below 70% threshold."

        # 2. Containment Checks: Reject restoration on locked down components
        lockdown_targets = []
        if self.state_cache.get("defense"):
            lockdown_targets = self.state_cache["defense"].get("breaker_lockdown_targets", [])
        if is_restoration and target in lockdown_targets:
            return False, f"Target {target} is locked down by active cyber defense containment."

        # 3. Simultaneous Action Protections: Enforce a 3-second guard delay between breaker commands
        is_breaker_cmd = cmd in ["OPEN", "CLOSE", "CLOSED"]
        if is_breaker_cmd:
            now = time.time()
            if now - self.last_breaker_operation_time < 3.0:
                if is_restoration:
                    return False, "Unsafe simultaneous recovery: recovery command rejected due to 3-second guard delay."
            self.last_breaker_operation_time = now

        # 4. Multi-Agent Agent Consensus voting
        # Build context for agent voting
        telemetry = self.state_cache.get("telemetry") or {}
        state_data = telemetry.get("state", {})
        buses = state_data.get("buses", {})
        
        avg_freq = 60.0
        v_dev_sum = 0.0
        v_count = 0
        for b_data in buses.values():
            if "frequency_hz" in b_data:
                avg_freq = min(avg_freq, b_data["frequency_hz"])
            v = b_data.get("voltage_pu", 1.0)
            if v > 0.0:
                v_dev_sum += abs(1.0 - v)
                v_count += 1
        avg_v_dev = v_dev_sum / v_count if v_count > 0 else 0.0
        
        stability_score = stability
        
        collapse_probability = 0.0
        predicted_overloads = []
        if self.state_cache.get("l6_predictive_stability"):
            collapse_probability = self.state_cache["l6_predictive_stability"].get("collapse_probability", 0.0)
            predicted_overloads = self.state_cache["l6_predictive_stability"].get("predicted_overloads", [])
        
        success_probability = 100.0
        if self.state_cache.get("l6_survival_forecast"):
            success_probability = self.state_cache["l6_survival_forecast"].get("recovery_success_prob", 100.0)

        context = {
            "telemetry": telemetry,
            "active_attack": telemetry.get("attack_status", {}).get("active_attack"),
            "collapsed": self.state_cache.get("flisr_state") != "NORMAL",
            "avg_freq": avg_freq,
            "avg_v_dev": avg_v_dev,
            "stability_score": stability_score,
            "predicted_overloads": predicted_overloads,
            "collapse_probability": collapse_probability,
            "success_probability": success_probability
        }
        
        # Update dynamic weights statefully based on context
        self.orchestrator_agent.update_dynamic_weights(context)

        # Run voting
        proposal = {"command": cmd, "target": target, "source": source}
        vote_res = self.orchestrator_agent.vote_on_proposal(proposal, context)
        
        # Check active cyber lockdown conflict before execution approval
        if target in self.orchestrator_agent.active_lockdowns and cmd in ["CLOSE", "RECONNECT_LINE", "REROUTE_FLOW"]:
            return False, f"Blocked by active cyber lockdown: CyberDefenseAgent vetoed proposed action {cmd} targeting compromised {target}."
            
        consensus_score = vote_res["consensus_score"]
        has_veto = vote_res.get("has_veto", False)

        # Gated Consensus Threshold Rules for autonomous execution
        is_nominal = (context.get("active_attack") is None) and (stability >= 90.0)
        if source != "SCADA_OPERATOR" and not is_nominal:
            if has_veto or consensus_score < 0.40 or stability < 30.0:
                # Operator approval required
                return False, f"Blocked: Action requires OPERATOR_APPROVAL_REQUIRED (consensus_score={consensus_score:.2f}, stability={stability:.1f}%, veto={has_veto})."
            elif consensus_score < 0.70 or stability < 50.0:
                # Semi-automatic (propose, but do not auto-execute)
                return False, f"Blocked: Action is SEMI-AUTOMATIC and requires operator approval (consensus_score={consensus_score:.2f}, stability={stability:.1f}%)."

        if not vote_res["approved"]:
            veto_reason = ""
            if vote_res.get("has_veto"):
                veto_reason = f" Vetoed by {', '.join(vote_res['vetoed_by'])}."
            return False, f"Agent consensus rejected proposal (score={consensus_score:.2f}).{veto_reason}"

        # Initialize rollback tracking on close command approval
        if cmd in ["CLOSE", "CLOSED"]:
            self.monitoring_recovery_breaker = target
            self.monitoring_recovery_ticks = 0
            self.monitoring_recovery_start_stability = stability

        return True, f"Passed all AI orchestrator and agent consensus checks (consensus score={consensus_score:.2f})."

    def run_cycle(self, client):
        """
        Runs a decision-making and action recommendations cycle.
        """
        if not self.state_cache["telemetry"]:
            return
            
        try:
            # Clean expired memory entries
            self.memory.clean_expired()

            # 1. Run Decision Engine
            report = self.decision_engine.evaluate(self.state_cache)
            
            # Check for stale subsystems
            now = time.time()
            stale_subsystems = []
            for subsystem, last_time in self.subsystem_last_update.items():
                if now - last_time > 10.0:
                    stale_subsystems.append(subsystem)
                    
            if stale_subsystems:
                logger.warning(f"[STALE SUBSYSTEMS] Subsystems offline: {stale_subsystems}")
                report["restoration_confidence"] = max(0.0, report["restoration_confidence"] - 20.0 * len(stale_subsystems))
                if "stale_subsystems" not in report["active_subsystems_reasoning"]:
                    report["active_subsystems_reasoning"]["stale_subsystems"] = f"Warning: {', '.join(stale_subsystems)} telemetry feed is stale (>10s)."

            # Rollback Safety Check
            if self.monitoring_recovery_breaker:
                self.monitoring_recovery_ticks += 1
                if report["stability_score"] < self.monitoring_recovery_start_stability - 15.0 or report["stability_score"] < 40.0:
                    logger.warning(f"[ROLLBACK SAFETY] Collapse detected after restoring {self.monitoring_recovery_breaker}. Initiating ROLLBACK!")
                    rollback_payload = {
                        "command": "OPEN",
                        "target": self.monitoring_recovery_breaker,
                        "source": "ROLLBACK_SAFETY"
                    }
                    client.publish("grid/control", json.dumps(rollback_payload))
                    
                    # Record failed recovery in memory
                    self.memory.record_failed_recovery(self.monitoring_recovery_breaker)
                    
                    # Log event
                    timestamp_ms = int(time.time() * 1000)
                    client.publish("grid/orchestrator/events", json.dumps({
                        "timestamp": timestamp_ms,
                        "event": "ROLLBACK",
                        "command": "OPEN",
                        "target": self.monitoring_recovery_breaker,
                        "source": "ROLLBACK_SAFETY",
                        "reason": "Stability collapse after restoration attempt"
                    }))
                    
                    self.monitoring_recovery_breaker = None
                elif self.monitoring_recovery_ticks >= 3:
                    logger.info(f"[ROLLBACK SAFETY] Breaker {self.monitoring_recovery_breaker} restoration stabilized successfully.")
                    self.monitoring_recovery_breaker = None

            # 2. Run Action Recommender
            self.state_cache["failed_recoveries"] = list(self.memory.failed_recoveries.keys())
            self.state_cache["sequencer_state"] = self.sequencer.state
            actions = self.action_recommender.recommend(self.state_cache, report)
            
            # 3. Determine active AI modules
            active_modules = []
            if self.state_cache["ai_forecast"] or self.state_cache["multi_bus_forecast"] or self.state_cache["threat_aware_forecast"]:
                active_modules.append("LSTM")
            if self.state_cache["physics_validation"]:
                active_modules.append("PINN")
            active_modules.append("PPO")
            if self.state_cache["flisr_state"] != "NORMAL":
                active_modules.append("FLISR")
            if self.state_cache["threat"]:
                active_modules.append("THREAT")
            if self.state_cache["defense"]:
                active_modules.append("DEFENSE")
                
            # 4. Determine dominant decision source
            dominant_source = "LSTM"
            global_state = report["global_state"]
            if self.state_cache["defense"] and self.state_cache["defense"].get("escalation_level") in ["EMERGENCY_CONTAINMENT", "GRID_PRESERVATION"]:
                dominant_source = "DEFENSE"
            elif global_state == "CYBER_ATTACK":
                dominant_source = "DEFENSE"
            elif global_state == "EMERGENCY_MODE":
                dominant_source = "PINN"
            elif global_state == "CASCADE_RISK":
                dominant_source = "THREAT"
            elif global_state == "AUTONOMOUS_RECOVERY":
                dominant_source = "FLISR"
            elif self.state_cache.get("flisr_state") != "NORMAL":
                dominant_source = "FLISR"
                
            # 5. Determine adaptive escalation mode
            escalation_mode = "NORMAL"
            stability_score = report["stability_score"]
            
            has_single_attack = False
            has_coordinated_attack = False
            if self.state_cache["threat"]:
                rec_actions = self.state_cache["threat"].get("recommendations", [])
                targets = [rec.get("target") for rec in rec_actions if rec.get("action") == "REJECT_TELEMETRY"]
                if len(targets) == 1:
                    has_single_attack = True
                elif len(targets) > 1:
                    has_coordinated_attack = True
            
            if self.state_cache["defense"]:
                esc_level = self.state_cache["defense"].get("escalation_level", "ADVISORY")
                if esc_level == "LOCAL_CONTAINMENT":
                    has_single_attack = True
                elif esc_level in ["EMERGENCY_CONTAINMENT", "GRID_PRESERVATION"]:
                    has_coordinated_attack = True
                    
            overloads_exist = False
            telemetry = self.state_cache["telemetry"]
            if telemetry:
                lines = telemetry.get("state", {}).get("lines", {})
                if any(l.get("capacity_pct", 0.0) > 100.0 for l in lines.values()):
                    overloads_exist = True
                    
            if stability_score < 50.0 or global_state == "EMERGENCY_MODE":
                escalation_mode = "EMERGENCY_STABILIZATION"
            elif overloads_exist and stability_score < 75.0:
                escalation_mode = "CASCADING_INSTABILITY"
            elif has_coordinated_attack or global_state == "CYBER_ATTACK":
                escalation_mode = "COORDINATED_ATTACK"
            elif has_single_attack:
                escalation_mode = "LOCAL_ATTACK"
                
            # 6. Coordinated recovery state
            coordinated_recovery_state = "STANDBY"
            if escalation_mode in ["COORDINATED_ATTACK", "LOCAL_ATTACK"]:
                coordinated_recovery_state = "CONTAINMENT_ENGAGED"
            elif escalation_mode == "CASCADING_INSTABILITY":
                coordinated_recovery_state = "STABILIZING"
            elif global_state == "AUTONOMOUS_RECOVERY":
                coordinated_recovery_state = "RECOVERING"
            elif stability_score > 90.0:
                coordinated_recovery_state = "STABLE"
                
            # Run Threat-Response Sequencer
            pipeline_data = self.sequencer.update(self.state_cache, report, self.memory)
            client.publish("grid/orchestrator/pipeline", json.dumps(pipeline_data))

            # 7. Publish AI Orchestrator Summary
            timestamp_ms = int(time.time() * 1000)
            orchestrator_payload = {
                "timestamp": timestamp_ms,
                "global_state": report["global_state"],
                "global_risk_level": report["global_risk_level"],
                "stability_score": stability_score,
                "restoration_confidence": report["restoration_confidence"],
                "active_subsystems_reasoning": report["active_subsystems_reasoning"],
                "defense_mode": self.defense_mode,
                "active_modules": active_modules,
                "dominant_decision_source": dominant_source,
                "ai_coordination_confidence": report["restoration_confidence"],
                "emergency_override_state": self.override_state.get("emergency_stop_active", False) or self.override_state.get("pause_autonomous", False),
                "coordinated_recovery_state": coordinated_recovery_state,
                "escalation_mode": escalation_mode
            }
            client.publish("grid/ai_orchestrator", json.dumps(orchestrator_payload))
            
            # 8. Publish Recommended Actions
            recommended_actions_payload = {
                "timestamp": timestamp_ms,
                "recommendations": actions
            }
            client.publish("grid/recommended_actions", json.dumps(recommended_actions_payload))
 
            # 9. Autonomous Emergency Defense Execution (when in EMERGENCY_DEFENSE mode)
            if self.defense_mode == "EMERGENCY_DEFENSE" and report["global_state"] == "EMERGENCY_MODE" and report["stability_score"] < 30.0:
                for act in actions:
                    if act["priority"] in ["CRITICAL", "HIGH"] and act["action"] in ["TELEMETRY_DISTRUST", "BREAKER_LOCKOUT", "ISOLATE_LINE"]:
                        cmd = None
                        if act["action"] == "TELEMETRY_DISTRUST":
                            cmd = "REJECT_TELEMETRY"
                        elif act["action"] in ["BREAKER_LOCKOUT", "ISOLATE_LINE"]:
                            cmd = "OPEN"
                        
                        if cmd:
                            logger.warning(f"[AUTONOMOUS DEFENSE] Automatically executing action {act['action']} targeting {act['target']}")
                            control_payload = {
                                "command": cmd,
                                "target": act["target"],
                                "source": "ORCHESTRATOR"
                            }
                            # Send via proposed topic for self-evaluation or directly if bypass is required
                            client.publish("grid/control/proposed", json.dumps(control_payload))
            
            logger.info(
                f"AI Orchestration cycle | Global State: {report['global_state']} | "
                f"Stability: {report['stability_score']}% | Mode: {escalation_mode} | Recovery: {coordinated_recovery_state} | Sequencer: {pipeline_data['state']}"
            )
            
        except Exception as e:
            logger.error(f"Failed to run AI Orchestrator cycle: {e}", exc_info=True)

    def reset(self):
        """
        Resets cache and engines.
        """
        self.state_cache = {
            "telemetry": None,
            "ai_forecast": None,
            "multi_bus_forecast": None,
            "threat_aware_forecast": None,
            "physics_validation": None,
            "trust_scores": None,
            "threat": None,
            "flisr_state": "NORMAL",
            "flisr_auto": True,
            "defense": None,
            "l6_recovery": None,
            "l6_adaptive_recovery": None,
            "l6_containment": None,
            "l6_degraded_mode": None,
            "l6_survival": None,
            "l6_islanding": None,
            "l6_blackstart": None,
            "l6_balancing": None,
            "l6_predictive_stability": None,
            "l6_survival_forecast": None,
            "l6_proactive_actions": None,
            "l6_self_preservation": None,
            "l6_agents": None,
            "l6_agent_consensus": None,
            "l6_agent_conflicts": None,
            "l6_distributed_state": None,
            "l6_agent_confidence": None,
            "hardware_attack_state": None,
            "hardware_attack_propagation": None
        }
        self.decision_engine = OrchestrationDecisionEngine()
        self.action_recommender = ActionRecommender()
        self.defense_mode = "ADVISORY"
        self.last_breaker_operation_time = 0.0
        self.orchestrator_agent = OrchestratorAgent()
        logger.info("AI Orchestrator cache and engines reset.")

orchestrator = AIOrchestrator()

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info("AI Orchestrator connected to MQTT!")
        client.subscribe("grid/telemetry")
        client.subscribe("grid/ai_prediction")
        client.subscribe("grid/ai_forecast_multi_bus")
        client.subscribe("grid/ai_threat_forecast")
        client.subscribe("grid/physics_validation")
        client.subscribe("grid/trust_scores")
        client.subscribe("grid/threat")
        client.subscribe("grid/config")
        client.subscribe("grid/control")
        client.subscribe("grid/control/proposed")
        client.subscribe("grid/pre_rl")
        client.subscribe("grid/defense")
        client.subscribe("grid/l6_recovery")
        client.subscribe("grid/l6_adaptive_recovery")
        client.subscribe("grid/l6_containment")
        client.subscribe("grid/l6_degraded_mode")
        client.subscribe("grid/l6_survival")
        client.subscribe("grid/l6_islanding")
        client.subscribe("grid/l6_blackstart")
        client.subscribe("grid/l6_balancing")
        client.subscribe("grid/l6_predictive_stability")
        client.subscribe("grid/l6_survival_forecast")
        client.subscribe("grid/l6_proactive_actions")
        client.subscribe("grid/l6_self_preservation")
        client.subscribe("grid/l6_agents")
        client.subscribe("grid/l6_agent_consensus")
        client.subscribe("grid/l6_agent_conflicts")
        client.subscribe("grid/l6_distributed_state")
        client.subscribe("grid/l6_agent_confidence")
        client.subscribe("hardware/device_health")
        client.subscribe("hardware/faults")
        client.subscribe("hardware/relay_faults")
        client.subscribe("hardware/anomalies")
        client.subscribe("hardware/attack_state")
        client.subscribe("hardware/attack_propagation")
        client.subscribe("hardware/orchestration")
        client.subscribe("hardware/edge_devices")
        client.subscribe("hardware/relay_execution")
        client.subscribe("hardware/distributed_bus")
        client.subscribe("hardware/synchronization")
        client.subscribe("hardware/orchestration_conflicts")
        client.subscribe("hardware/reliability")
        client.subscribe("hardware/telemetry_validation")
        client.subscribe("hardware/resilience")
        client.subscribe("hardware/disaster_recovery")
        client.subscribe("hardware/redundancy")
        client.subscribe("hardware/deployment_hardening")
        client.subscribe("hardware/large_scale_sync")
    else:
        logger.error(f"MQTT Connection failed: rc {rc}")

def on_message(client, userdata, msg):
    try:
        topic = msg.topic
        payload = json.loads(msg.payload.decode("utf-8"))
        
        if topic == "grid/control/proposed":
            cmd = payload.get("command")
            target = payload.get("target")
            source = payload.get("source")
            
            approved, reason = orchestrator.evaluate_proposed_command(cmd, target, source)
            timestamp_ms = int(time.time() * 1000)
            
            if approved:
                logger.info(f"[ORCHESTRATOR APPROVAL] Approved proposed action {cmd} on {target} from {source}. Reason: {reason}")
                forwarded_payload = {
                    "command": cmd,
                    "target": target,
                    "source": "ORCHESTRATOR_APPROVED",
                    "original_source": source
                }
                
                # Check if hardware daemon is active and has good trust
                hardware_active = False
                device_health = orchestrator.state_cache.get("hardware_device_health")
                if device_health:
                    devices = device_health.get("devices", {})
                    esp_trust = devices.get("esp32", {}).get("trust", 1.0)
                    plc_trust = devices.get("plc", {}).get("trust", 1.0)
                    if esp_trust >= 0.4 and plc_trust >= 0.4:
                        hardware_active = True
                        
                if hardware_active:
                    logger.info("Routing approved command through Hardware Abstraction Layer.")
                    client.publish("hardware/control/execute", json.dumps(forwarded_payload))
                else:
                    logger.info("HAL offline or degraded. Routing approved command directly to Digital Twin.")
                    client.publish("grid/control", json.dumps(forwarded_payload))
                
                # Log event
                event_payload = {
                    "timestamp": timestamp_ms,
                    "source": "AI_ORCHESTRATOR",
                    "event": f"Approved proposed command {cmd} on {target} from {source}.",
                    "severity": "INFO"
                }
                client.publish("grid/events", json.dumps(event_payload))
                
                # Log specific orchestrator event
                client.publish("grid/orchestrator/events", json.dumps({
                    "timestamp": timestamp_ms,
                    "event": "APPROVAL",
                    "command": cmd,
                    "target": target,
                    "source": source,
                    "reason": reason
                }))
            else:
                logger.warning(f"[ORCHESTRATOR REJECTION] REJECTED proposed action {cmd} on {target} from {source}. Reason: {reason}")
                
                # Log event
                event_payload = {
                    "timestamp": timestamp_ms,
                    "source": "AI_ORCHESTRATOR",
                    "event": f"REJECTED proposed command {cmd} on {target} from {source}. Reason: {reason}",
                    "severity": "WARNING"
                }
                client.publish("grid/events", json.dumps(event_payload))
                
                # Log specific orchestrator event
                client.publish("grid/orchestrator/events", json.dumps({
                    "timestamp": timestamp_ms,
                    "event": "REJECTION",
                    "command": cmd,
                    "target": target,
                    "source": source,
                    "reason": reason
                }))
                
        elif topic == "grid/control":
            cmd = payload.get("command")
            if cmd == "RESET_ALARMS":
                orchestrator.reset()
                orchestrator.override_state["emergency_stop_active"] = False
            elif cmd == "TRIGGER_EMERGENCY_STOP":
                orchestrator.override_state["emergency_stop_active"] = True
                logger.warning("Emergency stop triggered at AI Orchestrator.")
            elif cmd == "RESET_EMERGENCY_STOP":
                orchestrator.override_state["emergency_stop_active"] = False
                logger.info("Emergency stop reset at AI Orchestrator.")
            elif cmd == "TOGGLE_AUTO_DEFENSE":
                enabled = payload.get("enabled", False)
                orchestrator.defense_mode = "EMERGENCY_DEFENSE" if enabled else "ADVISORY"
                logger.info(f"Orchestrator defense mode updated to: {orchestrator.defense_mode}")
            elif cmd == "SET_DEFENSE_MODE":
                orchestrator.defense_mode = payload.get("mode", "ADVISORY")
                logger.info(f"Orchestrator defense mode updated to: {orchestrator.defense_mode}")
        else:
            # Throttling and duplicate timestamp checks for telemetry
            if topic == "grid/telemetry":
                now = time.time()
                if now - orchestrator.last_cycle_time < 0.5:
                    return # Skip telemetry flood
                    
                packet_time = payload.get("timestamp", 0)
                if packet_time <= orchestrator.last_telemetry_timestamp:
                    return # Discard delayed/duplicate telemetry
                    
                orchestrator.last_cycle_time = now
                orchestrator.last_telemetry_timestamp = packet_time

            orchestrator.update_state(topic, payload)
            
            # Trigger cycle execution upon receiving telemetry tick
            if topic == "grid/telemetry":
                orchestrator.run_cycle(client)
            elif topic == "hardware/attack_propagation":
                orchestrator.process_quarantine_containment(client)
                
    except Exception as e:
        logger.error(f"Error handling message on {msg.topic}: {e}", exc_info=True)

if __name__ == "__main__":
    client = mqtt.Client(client_id="ai_orchestration_service")
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
        client.loop_forever()
    except KeyboardInterrupt:
        logger.info("Stopping AI Orchestrator...")
    except Exception as e:
        logger.error(f"MQTT Loop Error: {e}")
        sys.exit(1)
