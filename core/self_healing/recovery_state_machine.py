import os
import sys
import time
import json
import logging
from typing import Dict, List, Any

# Setup import paths
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(CURRENT_DIR)

from core.self_healing.topology_recovery_engine import TopologyRecoveryEngine
from core.self_healing.restoration_planner import RestorationPlanner
from core.self_healing.restoration_validator import RestorationValidator
from core.self_healing.rollback_guard import RollbackGuard
from core.self_healing.operator_override import OperatorOverrideEngine

logger = logging.getLogger("self_healing.recovery_state_machine")

class RecoveryStateMachine:
    """
    Manages Layer 6 Autonomous Restoration states statefully.
    Transitions: NORMAL -> DETECTION -> ISOLATE -> STABILIZE -> REROUTE -> RESTORE -> VERIFY -> ROLLBACK.
    Enforces switching cooldowns, staged restoration sequencing, and operator override interlocks.
    """
    def __init__(self):
        self.state = "NORMAL"
        
        self.topo_engine = TopologyRecoveryEngine()
        self.validator = RestorationValidator()
        self.planner = RestorationPlanner(self.topo_engine, self.validator)
        self.rollback_guard = RollbackGuard()
        self.override = OperatorOverrideEngine()
        self.override.set_restoration_mode("AUTO")
        
        # State tracking buffers
        self.timeline: List[Dict[str, Any]] = []
        self.action_logs: List[Dict[str, Any]] = []
        self.planned_sequence: List[Dict[str, Any]] = []
        self.executed_sequence: List[Dict[str, Any]] = []
        
        # Staged recovery splitting
        self.critical_steps: List[Dict[str, Any]] = []
        self.non_critical_steps: List[Dict[str, Any]] = []
        self.recovery_phase = "NONE" # NONE, PARTIAL, FULL
        
        self.state_timer = 0
        
        # Cooldown tracking: breaker -> last_switched_time (float)
        self.switching_cooldowns: Dict[str, float] = {}
        self.cooldown_duration = 30.0  # 30 seconds switching cooldown
        
        # Cache for live cyber-physical contextual parameters
        self.latest_trust_scores = None
        self.latest_threat_data = None
        
        # Initialize log
        self.log_event("Autonomous Restoration System online. Monitoring grid state...", "INFO")
        
    def log_event(self, msg: str, severity: str = "INFO"):
        event = {
            "timestamp": int(time.time() * 1000),
            "event": msg,
            "severity": severity
        }
        self.timeline.append(event)
        if len(self.timeline) > 50:
            self.timeline.pop(0)
        logger.info(f"[{severity}] {msg}")
        
    def log_action(self, action: str, target: str, status: str):
        log = {
            "timestamp": int(time.time() * 1000),
            "action": action,
            "target": target,
            "status": status
        }
        self.action_logs.append(log)
        if len(self.action_logs) > 50:
            self.action_logs.pop(0)
            
    def transition_to(self, new_state: str):
        self.log_event(f"State transition: {self.state} -> {new_state}", "WARNING")
        self.state = new_state
        self.state_timer = 0
        
    def reset(self):
        self.state = "NORMAL"
        self.timeline.clear()
        self.action_logs.clear()
        self.planned_sequence.clear()
        self.executed_sequence.clear()
        self.critical_steps.clear()
        self.non_critical_steps.clear()
        self.recovery_phase = "NONE"
        self.rollback_guard.reset()
        self.switching_cooldowns.clear()
        self.log_event("Restoration state machine reset by operator.", "INFO")
        
    def update(self, telemetry: Dict[str, Any], client, faulted_breakers: list = None, trust_scores: Dict[str, Any] = None, threat_data: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Executes a state evaluation step based on incoming 1.0 Hz telemetry tick.
        Returns a list of proposed commands to be published.
        """
        if not telemetry:
            return []

        # Store latest contextual variables
        if trust_scores:
            self.latest_trust_scores = trust_scores
        if threat_data:
            self.latest_threat_data = threat_data

        # --- OPERATOR OVERRIDE INTERLOCK ---
        if self.override.pause_autonomous or self.override.emergency_stop_active:
            logger.debug("Autonomous restoration paused/emergency stopped by operator override.")
            return []

        self.state_timer += 1
        state_data = telemetry.get("state", {})
        breakers = state_data.get("breakers", {})
        buses = state_data.get("buses", {})
        
        commands = []
        
        # Analyze grid topology
        topo_analysis = self.topo_engine.analyze_topology(telemetry)
        isolated_segments = topo_analysis["isolated_segments"]
        
        # Run state logic
        if self.state == "NORMAL":
            # Monitor for de-energized load sectors
            has_isolated_loads = False
            for comp in isolated_segments:
                if any(self.topo_engine.topo.loads.get(b) is not None for b in comp):
                    has_isolated_loads = True
                    break
                    
            if has_isolated_loads:
                if faulted_breakers:
                    self.log_event("Faulted breakers reported. Entering ISOLATE state directly.", "WARNING")
                    self.transition_to("ISOLATE")
                else:
                    self.log_event("Isolated load buses detected. Entering DETECTION state.", "WARNING")
                    self.transition_to("DETECTION")
                
        elif self.state == "DETECTION":
            # Verification window to confirm persistent outage (prevent false actions on transient noise)
            if self.state_timer >= 2:
                self.log_event("Persistent outage confirmed. Moving to fault isolation.", "WARNING")
                self.transition_to("ISOLATE")
                
        elif self.state == "ISOLATE":
            # In ISOLATE, wait for protective relays to finish tripping
            if self.state_timer >= 2:
                self.log_event("Fault isolation complete. Proceeding to stabilization settle window.", "INFO")
                self.transition_to("STABILIZE")
                
        elif self.state == "STABILIZE":
            # Wait for physical parameters (voltages/transients) to settle post-trip
            if self.state_timer >= 3:
                self.log_event("Grid parameters stabilized. Moving to alternate route planning.", "INFO")
                self.transition_to("REROUTE")
                
        elif self.state == "REROUTE":
            # Calculate restoration sequences utilizing context-aware planning
            sequence = self.planner.plan_restoration(
                telemetry, faulted_breakers, self.latest_trust_scores, self.latest_threat_data
            )
            if sequence:
                self.planned_sequence = sequence
                self.executed_sequence = []
                self.critical_steps = []
                self.non_critical_steps = []
                
                # Split planned sequence into critical loads (Bus 5 hospital and Bus 8 industrial) vs others
                critical_lines = {"L4_5", "L5_6", "L7_8", "L8_9"}
                for step in sequence:
                    if step["target"] in critical_lines:
                        self.critical_steps.append(step)
                    else:
                        self.non_critical_steps.append(step)
                
                self.log_event(
                    f"Plan generated: {len(self.critical_steps)} critical steps, "
                    f"{len(self.non_critical_steps)} non-critical steps.", "INFO"
                )
                
                if self.critical_steps or self.non_critical_steps:
                    self.recovery_phase = "NONE"
                    self.transition_to("RESTORE")
                else:
                    self.transition_to("NORMAL")
            else:
                self.log_event("No viable restoration sequence discovered. Returning to monitor.", "WARNING")
                self.transition_to("NORMAL")
                
        elif self.state == "RESTORE":
            # Determine sub-phase state dynamically
            if self.recovery_phase == "NONE":
                if self.critical_steps:
                    self.recovery_phase = "PARTIAL"
                elif self.non_critical_steps:
                    self.recovery_phase = "FULL"
                else:
                    self.transition_to("NORMAL")
                    return []

            if self.recovery_phase == "PARTIAL":
                # Progressively close planned critical load breakers
                if len(self.executed_sequence) < len(self.critical_steps):
                    next_step = self.critical_steps[len(self.executed_sequence)]
                    cmd = next_step["command"]
                    target = next_step["target"]
                    
                    # Check lockout
                    if self.rollback_guard.is_locked_out(target):
                        self.log_event(f"Skipped critical step on locked breaker: {target}.", "WARNING")
                        self.log_action(cmd, target, "BLOCKED")
                        self.transition_to("ROLLBACK")
                    # Check switching cooldown to prevent equipment wear
                    elif not self._check_cooldown_and_allowed(cmd, target):
                        logger.warning(f"Cooldown active on breaker {target}. Delaying execution.")
                    else:
                        control_cmd = "CLOSED" if cmd == "CLOSE" else "OPEN"
                        commands.append({
                            "command": control_cmd,
                            "target": target,
                            "source": "L6_RECOVERY_PARTIAL"
                        })
                        self.switching_cooldowns[target] = time.time()
                        self.log_event(f"Progressive critical restoration: {cmd} breaker {target}.", "WARNING")
                        self.log_action(cmd, target, "EXECUTING")
                        self.executed_sequence.append(next_step)
                else:
                    self.log_event("Critical path commands issued. Moving to validation.", "INFO")
                    self.transition_to("VERIFY")

            elif self.recovery_phase == "FULL":
                # Progressively close non-critical breakers
                if len(self.executed_sequence) < len(self.non_critical_steps):
                    next_step = self.non_critical_steps[len(self.executed_sequence)]
                    cmd = next_step["command"]
                    target = next_step["target"]
                    
                    # Check lockout
                    if self.rollback_guard.is_locked_out(target):
                        self.log_event(f"Skipped non-critical step on locked breaker: {target}.", "WARNING")
                        self.log_action(cmd, target, "BLOCKED")
                        self.transition_to("ROLLBACK")
                    # Check switching cooldown
                    elif not self._check_cooldown_and_allowed(cmd, target):
                        logger.warning(f"Cooldown active on breaker {target}. Delaying execution.")
                    else:
                        control_cmd = "CLOSED" if cmd == "CLOSE" else "OPEN"
                        commands.append({
                            "command": control_cmd,
                            "target": target,
                            "source": "L6_RECOVERY_FULL"
                        })
                        self.switching_cooldowns[target] = time.time()
                        self.log_event(f"Progressive non-critical restoration: {cmd} breaker {target}.", "WARNING")
                        self.log_action(cmd, target, "EXECUTING")
                        self.executed_sequence.append(next_step)
                else:
                    self.log_event("All planned commands issued. Moving to final verification.", "INFO")
                    self.transition_to("VERIFY")
                
        elif self.state == "VERIFY":
            # Monitor voltages and loadings for 3 frames to confirm stability
            is_unstable = False
            reasons = []
            
            for bus_idx in self.topo_engine.topo.loads.keys():
                bus_name = f"Bus_{bus_idx + 1}"
                v_pu = buses.get(bus_name, {}).get("voltage_pu", 1.0)
                
                if bus_name == "Bus_5" and v_pu < 0.90:
                    is_unstable = True
                    reasons.append(f"CRITICAL Hospital voltage collapse on Bus_5: {v_pu:.3f} p.u.")
                elif v_pu < 0.88:
                    is_unstable = True
                    reasons.append(f"Voltage collapse on {bus_name}: {v_pu:.3f} p.u.")
                    
            lines = state_data.get("lines", {})
            for lid, l_data in lines.items():
                loading = l_data.get("capacity_pct", 0.0)
                if loading > 110.0:
                    is_unstable = True
                    reasons.append(f"Line overload on {lid}: {loading:.1f}%")
                    
            # Check for switching oscillations
            loop_detected, reason = self.rollback_guard.detect_oscillation(self.action_logs)
            if loop_detected:
                is_unstable = True
                reasons.append(f"Oscillation: {reason}")
                
            if is_unstable:
                self.log_event(f"Verification FAILED: {', '.join(reasons)}. Reverting actions.", "CRITICAL")
                self.transition_to("ROLLBACK")
            elif self.state_timer >= 3:
                self.log_event("Verification PASSED. Local grid stable.", "INFO")
                # Mark executed steps as successful
                for step in self.executed_sequence:
                    self.log_action(step["command"], step["target"], "SUCCESS")
                
                # Check if we should transition to FULL restoration
                if self.recovery_phase == "PARTIAL" and self.non_critical_steps:
                    self.log_event("Critical restoration verified. Moving to non-critical full recovery.", "INFO")
                    self.recovery_phase = "FULL"
                    self.executed_sequence = []
                    self.transition_to("RESTORE")
                else:
                    self.transition_to("NORMAL")
                
        elif self.state == "ROLLBACK":
            # Undo all executed close actions in reverse order
            rollback_commands = []
            for step in reversed(self.executed_sequence):
                if step["command"] == "CLOSE":
                    target = step["target"]
                    rollback_commands.append({
                        "command": "OPEN",
                        "target": target,
                        "source": "ROLLBACK_GUARD"
                    })
                    self.log_event(f"Rolling back closed breaker: {target}.", "CRITICAL")
                    self.log_action("OPEN", target, "ROLLBACK")
                    self.rollback_guard.lockout(target, duration=60.0)
                    
            for r_cmd in rollback_commands:
                client.publish("grid/control", json.dumps(r_cmd))
                
            self.executed_sequence.clear()
            self.transition_to("NORMAL")
            
        # Compute recovery confidence meter (0-100)
        total_voltages = [buses[f"Bus_{i+1}"].get("voltage_pu", 1.0) for i in range(9) if f"Bus_{i+1}" in buses]
        mean_voltage = sum(total_voltages)/len(total_voltages) if total_voltages else 1.0
        confidence = max(0, min(100, int((1.0 - abs(mean_voltage - 1.0) * 4) * 100)))
        if self.state == "ROLLBACK":
            confidence = 10
            
        # Compile and publish Layer 6 telemetry
        payload = {
            "timestamp": int(time.time() * 1000),
            "state": self.state,
            "timeline": self.timeline,
            "action_logs": self.action_logs,
            "confidence": confidence,
            "isolated_segments": [[f"Bus_{b+1}" for b in seg] for seg in isolated_segments],
            "active_sequence": self.planned_sequence,
            "rollback_guard_status": {
                "lockout_breakers": list(self.rollback_guard.lockouts.keys()),
                "rollback_count": self.rollback_guard.rollback_count
            }
        }
        client.publish("grid/l6_recovery", json.dumps(payload))
        
        return commands

    def _check_cooldown_and_allowed(self, action_name: str, target: str) -> bool:
        """
        Enforces physical switching cooldowns and operator overrides.
        """
        # 1. Cooldown check
        last_time = self.switching_cooldowns.get(target, 0.0)
        if time.time() - last_time < self.cooldown_duration:
            return False

        # 2. Operator override check
        allowed, _ = self.override.is_action_allowed(action_name, target)
        return allowed
