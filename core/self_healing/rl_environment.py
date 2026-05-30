import os
import sys
import json
import time
import copy
import logging
from typing import Dict, Any, List, Tuple
import numpy as np
import paho.mqtt.client as mqtt

# Add current dir and digital_twin dir to sys.path to enable topology/physics imports
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(CURRENT_DIR)
sys.path.append(os.path.abspath(os.path.join(CURRENT_DIR, "..", "digital_twin")))
sys.path.append(os.path.abspath(os.path.join(CURRENT_DIR, "rl")))

import core.self_healing.rl.rl_metrics as rl_metrics

from core.self_healing.state_encoder import StateEncoder
from core.self_healing.action_registry import ActionRegistry
from core.self_healing.safety_constraints import SafetyConstraintEngine
from core.self_healing.trusted_action_filter import TrustedActionFilter
from core.self_healing.reward_engine import RewardEngine
from core.self_healing.restoration_policy_engine import RestorationPolicyEngine
from core.self_healing.operator_override import OperatorOverrideEngine

# Import new Pre-RL foundation engines
from core.self_healing.restoration_sandbox import RestorationSandbox
from core.self_healing.action_rollback import ActionRollbackManager
from core.self_healing.state_vector_debugger import StateVectorDebugger
from core.self_healing.action_explainer import ActionExplainer
from core.self_healing.restoration_timeline import RestorationTimeline

# Dynamic imports from digital twin if available
try:
    from grid_topology import GridTopology
    from physics import GridPhysicsEngine
except ImportError:
    # Safe mock fallback classes for isolation/standalone environments
    class GridTopology:
        def __init__(self):
            self.num_buses = 9
            self.slack_bus = 0
            self.lines = [
                {"id": "L1_4", "from": 0, "to": 3, "X": 0.0576},
                {"id": "L2_7", "from": 1, "to": 6, "X": 0.0625},
                {"id": "L3_9", "from": 2, "to": 8, "X": 0.0586},
                {"id": "L4_5", "from": 3, "to": 4, "X": 0.085},
                {"id": "L4_9", "from": 3, "to": 8, "X": 0.092},
                {"id": "L5_6", "from": 4, "to": 5, "X": 0.161},
                {"id": "L6_7", "from": 5, "to": 6, "X": 0.072},
                {"id": "L7_8", "from": 6, "to": 7, "X": 0.161},
                {"id": "L8_9", "from": 7, "to": 8, "X": 0.1008}
            ]
            self.generators = {0: {"P_nom": 72.0, "Q_nom": 27.0}, 1: {"P_nom": 163.0, "Q_nom": 6.0}, 2: {"P_nom": 85.0, "Q_nom": -10.0}}
            self.loads = {4: {"P_nom": 125.0, "Q_nom": 50.0}, 5: {"P_nom": 90.0, "Q_nom": 30.0}, 7: {"P_nom": 100.0, "Q_nom": 35.0}}
            
    class GridPhysicsEngine:
        def __init__(self, topology):
            self.topo = topology
        def solve(self, breakers, active_loads, generator_P, generator_Q):
            V = np.ones(9)
            theta = np.zeros(9)
            P = np.zeros(9)
            Q = np.zeros(9)
            line_flows = {line["id"]: {"P_flow": 0.1, "Q_flow": 0.02, "current": 0.1} for line in self.topo.lines}
            return V, theta, P, Q, line_flows

# Fallback Gymnasium Env import
try:
    import gymnasium as gym
    from gymnasium import spaces
    EnvClass = gym.Env
except ImportError:
    class EnvClass:
        pass
    spaces = None

logger = logging.getLogger("self_healing.rl_environment")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

class GridRLEnvironment(EnvClass):
    """
    IEEE 9-bus Grid RL Environment for cybersecurity and self-healing.
    Compatible with Gymnasium/Gym interface for training.
    """
    def __init__(self, is_live_mode=True):
        super(GridRLEnvironment, self).__init__()
        
        # Instantiate Pre-RL engines
        self.encoder = StateEncoder()
        self.registry = ActionRegistry()
        self.safety = SafetyConstraintEngine()
        self.filter = TrustedActionFilter()
        self.reward_engine = RewardEngine()
        self.policy = RestorationPolicyEngine()
        self.override = OperatorOverrideEngine()
        
        # Complete foundation engines
        self.sandbox = RestorationSandbox()
        self.rollback = ActionRollbackManager()
        self.debugger = StateVectorDebugger()
        self.explainer = ActionExplainer()
        self.timeline = RestorationTimeline()
        
        self.topo = GridTopology()
        self.physics = GridPhysicsEngine(self.topo)
        
        # RL Gym spaces definition
        if spaces:
            # 72-dimensional state observations
            self.observation_space = spaces.Box(
                low=-10.0, high=10.0, shape=(72,), dtype=np.float32
            )
            # 10 discrete actions
            self.action_space = spaces.Discrete(10)
            
        # Standalone sandbox properties
        self.sandbox_active = False
        self.sandbox_breakers = {}
        self.sandbox_loads = {}
        self.sandbox_gen_P = {}
        self.sandbox_gen_Q = {}
        
        # Live caches of MQTT inputs
        self.latest_telemetry = None
        self.latest_threat_data = None
        self.latest_ai_prediction = None
        self.latest_multi_bus = None
        self.latest_threat_aware = None
        self.latest_pinn_forecast = None
        self.latest_physics_val = None
        self.latest_trust_scores = None
        self.latest_adaptive_filter = None
        self.latest_ai_orchestrator = None
        self.latest_recommended_actions = None
        self.latest_rl_status = None
        self.latest_defense = None
        
        self.is_live_mode = is_live_mode
        self.current_live_state_vec = np.zeros(72, dtype=np.float32)
        self.bus_names = [f"Bus_{i}" for i in range(1, 10)]
        
        self.step_count = 0
        self.episode_failed_actions = set()
        self.episode_rollbacks = 0
        self.episode_switches = 0
        self.episode_start_time = time.time()
        
        # Add rl folder to sys.path and initialize PPOAgent
        rl_path = os.path.abspath(os.path.join(CURRENT_DIR, "rl"))
        if rl_path not in sys.path:
            sys.path.append(rl_path)
            
        self.ppo_agent = None
        try:
            from core.self_healing.rl.ppo_agent import PPOAgent
            self.ppo_agent = PPOAgent(state_dim=72, action_dim=10)
            models_dir = os.path.abspath(os.path.join(CURRENT_DIR, "models"))
            checkpoint_path = os.path.join(models_dir, "ppo_self_healing.pt")
            if os.path.exists(checkpoint_path):
                self.ppo_agent.load_checkpoint(checkpoint_path)
                logger.info("[RL ENVIRONMENT] Successfully loaded trained PPO checkpoint for live inference.")
            else:
                logger.warning(f"[RL ENVIRONMENT] PPO Checkpoint not found at {checkpoint_path}. Using untrained agent.")
        except Exception as e:
            logger.error(f"[RL ENVIRONMENT] Failed to initialize PPOAgent: {e}")

    def get_target_for_action(self, action_id: int, state: np.ndarray) -> str:
        """
        Selects the most appropriate target string for the given action category
        based on the current grid state vector.
        """
        action_meta = self.registry.get_action(action_id)
        target_type = action_meta.get("target")
        
        if target_type == "SYSTEM" or target_type == "FLISR":
            return "SYSTEM"
        elif target_type == "ORCHESTRATOR":
            return "EMERGENCY_DEFENSE"
        elif target_type == "ZONE":
            return "ZONE_1"
            
        voltages = state[0:9]
        breakers = state[36:45]
        bus_trust = state[45:54]
        line_trust = state[54:63]
        
        line_names = ["L1_4", "L2_7", "L3_9", "L4_5", "L4_9", "L5_6", "L6_7", "L7_8", "L8_9"]
        bus_names = [f"Bus_{i}" for i in range(1, 10)]
        
        if target_type == "LINE":
            if action_meta["name"] in ["ISOLATE_LINE", "OPEN_BREAKER"]:
                closed_lines = [i for i, b in enumerate(breakers) if b > 0.5]
                if not closed_lines:
                    return "L1_4"
                closed_lines.sort(key=lambda idx: line_trust[idx])
                return line_names[closed_lines[0]]
            else:
                open_lines = [i for i, b in enumerate(breakers) if b < 0.5]
                if not open_lines:
                    return "L7_8"
                open_lines.sort(key=lambda idx: line_trust[idx], reverse=True)
                return line_names[open_lines[0]]
                
        elif target_type == "NODE" or target_type == "BUS":
            if action_meta["name"] in ["REJECT_TELEMETRY", "ISOLATE_BUS"]:
                lowest_trust_idx = int(np.argmin(bus_trust))
                return bus_names[lowest_trust_idx]
            else:
                distrusted_buses = [i for i, t in enumerate(bus_trust) if t < 0.8]
                if not distrusted_buses:
                    return "Bus_1"
                distrusted_buses.sort(key=lambda idx: bus_trust[idx], reverse=True)
                return bus_names[distrusted_buses[0]]
                
        return "SYSTEM"
        
    def reset(self, seed=None, options=None):
        """
        Resets environment to nominal state (Gymnasium interface).
        """
        if seed is not None and hasattr(self, "np_random"):
            self.np_random, seed = gym.utils.seeding.np_random(seed)
            
        self.step_count = 0
        self.episode_failed_actions = set()
        self.episode_rollbacks = 0
        self.episode_switches = 0
        self.episode_start_time = time.time()
        
        # Reset local sandbox parameters
        self.sandbox_breakers = {line["id"]: "CLOSED" for line in self.topo.lines}
        self.sandbox_breakers["L7_8"] = "OPEN"
        
        self.sandbox_loads = {}
        for bus_idx, load in self.topo.loads.items():
            self.sandbox_loads[bus_idx] = {"P": load["P_nom"], "Q": load["Q_nom"]}
            
        self.sandbox_gen_P = {k: v["P_nom"] for k, v in self.topo.generators.items()}
        self.sandbox_gen_Q = {k: v["Q_nom"] for k, v in self.topo.generators.items()}
        
        # Build initial state representation
        V, theta, P, Q, line_flows = self.physics.solve(
            self.sandbox_breakers, self.sandbox_loads, self.sandbox_gen_P, self.sandbox_gen_Q
        )
        
        dummy_telemetry = {
            "state": {
                "buses": {f"Bus_{i+1}": {"voltage_pu": float(V[i]), "angle_rad": float(theta[i])} for i in range(9)},
                "lines": {lid: {"P_mw": float(f["P_flow"]*100.0), "Q_mvar": float(f["Q_flow"]*100.0), "current_pu": float(f["current"])} for lid, f in line_flows.items()},
                "breakers": self.sandbox_breakers.copy()
            }
        }
        
        obs = self.encoder.encode_state(telemetry=dummy_telemetry)
        info = {"status": "Nominal reset", "sandbox_active": self.sandbox_active}
        return obs, info
        
    def step(self, action_id: int, target: str = "SYSTEM"):
        """
        Executes step transition on sandbox grid simulation model (Gymnasium interface).
        """
        action = self.registry.get_action(action_id)
        action_name = action["name"]
        
        self.step_count += 1
        repeated_failed_action = (action_name, target) in self.episode_failed_actions
        
        prev_obs = self.encoder.encode_state(
            telemetry=self._get_sandbox_telemetry_snapshot(),
            threat_data=self.latest_threat_data,
            ai_prediction=self.latest_ai_prediction,
            multi_bus=self.latest_multi_bus,
            threat_aware=self.latest_threat_aware,
            pinn_forecast=self.latest_pinn_forecast,
            physics_val=self.latest_physics_val,
            trust_scores=self.latest_trust_scores,
            adaptive_filter=self.latest_adaptive_filter,
            orchestrator_data=self.latest_ai_orchestrator
        )
        
        # Apply the sandbox action
        action_allowed = True
        violation_reason = ""
        
        if repeated_failed_action:
            action_allowed = False
            violation_reason = f"Action {action_name}({target}) blocked by adaptive policy protection (repeated failed action)."
            
        # 1. Cyber defense containment check (Priority override)
        if self.latest_defense:
            esc_level = self.latest_defense.get("escalation_level", "ADVISORY")
            is_restoration = action_name in ["RECONNECT_LINE", "REROUTE_FLOW", "ENABLE_RESTORATION"]
            restoration_locked = self.latest_defense.get("restoration_lockdown_active", False)
            if esc_level in ["EMERGENCY_CONTAINMENT", "GRID_PRESERVATION"]:
                restoration_locked = True
                
            if restoration_locked and is_restoration:
                action_allowed = False
                violation_reason = f"Restoration blocked by active cyber defense containment (mode: {esc_level})."
            elif target in self.latest_defense.get("breaker_lockdown_targets", []):
                action_allowed = False
                violation_reason = f"Breaker target {target} is locked down by cyber defense containment."
                
        # 2. Safety and Policy checks (only if not blocked by cyber defense)
        if action_allowed:
            # Safety constraint validation check
            allowed, violations, score = self.safety.evaluate_constraints(
                self._get_sandbox_telemetry_snapshot(), action_name, target
            )
            
            if not allowed:
                action_allowed = False
                violation_reason = "Blocked by Safety Constraints: " + ", ".join(violations)
            else:
                # Policy rules check
                policy_allowed, policy_reason = self.policy.evaluate_policy(
                    action_name, target, self._get_sandbox_telemetry_snapshot(), self.latest_pinn_forecast
                )
                if not policy_allowed:
                    action_allowed = False
                    violation_reason = policy_reason
                
        if action_allowed:
            # Apply changes statefully inside sandbox breakers
            if action_name in ["ISOLATE_LINE", "OPEN_BREAKER"] and target in self.sandbox_breakers:
                if self.sandbox_breakers[target] != "OPEN":
                    self.episode_switches += 1
                self.sandbox_breakers[target] = "OPEN"
            elif action_name in ["RECONNECT_LINE", "REROUTE_FLOW"] and target in self.sandbox_breakers:
                if self.sandbox_breakers[target] != "CLOSED":
                    self.episode_switches += 1
                self.sandbox_breakers[target] = "CLOSED"
            elif action_name == "ISOLATE_BUS":
                bus_idx = self.bus_names.index(target) if target in self.bus_names else 0
                for line in self.topo.lines:
                    if line["from"] == bus_idx or line["to"] == bus_idx:
                        if self.sandbox_breakers[line["id"]] != "OPEN":
                            self.episode_switches += 1
                        self.sandbox_breakers[line["id"]] = "OPEN"
            elif action_name == "ENABLE_ISLANDING":
                for line_id in ["L7_8", "L4_5", "L8_9"]:
                    if line_id in self.sandbox_breakers:
                        if self.sandbox_breakers[line_id] != "OPEN":
                            self.episode_switches += 1
                        self.sandbox_breakers[line_id] = "OPEN"
                        
            # Execute sandbox physics calculation loop
            V, theta, P, Q, line_flows = self.physics.solve(
                self.sandbox_breakers, self.sandbox_loads, self.sandbox_gen_P, self.sandbox_gen_Q
            )
            self.policy.record_action_execution(target)
            self.override.record_execution(action_name, target)
        else:
            self.episode_failed_actions.add((action_name, target))
            logger.warning(f"[SANDBOX STEP BLOCKED] Action {action_name}({target}) blocked. Reason: {violation_reason}")
            
        curr_obs = self.encoder.encode_state(
            telemetry=self._get_sandbox_telemetry_snapshot(),
            threat_data=self.latest_threat_data,
            ai_prediction=self.latest_ai_prediction,
            multi_bus=self.latest_multi_bus,
            threat_aware=self.latest_threat_aware,
            pinn_forecast=self.latest_pinn_forecast,
            physics_val=self.latest_physics_val,
            trust_scores=self.latest_trust_scores,
            adaptive_filter=self.latest_adaptive_filter,
            orchestrator_data=self.latest_ai_orchestrator
        )
        
        reward, reward_details = self.reward_engine.compute_reward(
            prev_obs, curr_obs, action_id,
            repeated_failed_action=repeated_failed_action,
            step_count=self.step_count,
            defense_status=self.latest_defense
        )
        
        terminated = False
        truncated = False
        info = {
            "action_allowed": action_allowed,
            "rejection_reason": violation_reason,
            "reward_details": reward_details,
            "sandbox_active": self.sandbox_active
        }
        
        return curr_obs, reward, terminated, truncated, info
 
    def _get_sandbox_telemetry_snapshot(self) -> Dict[str, Any]:
        """
        Runs local physics calculations and returns a mock telemetry payload matching sandbox breaker states.
        """
        V, theta, P, Q, line_flows = self.physics.solve(
            self.sandbox_breakers, self.sandbox_loads, self.sandbox_gen_P, self.sandbox_gen_Q
        )
        return {
            "timestamp": int(time.time() * 1000),
            "state": {
                "buses": {f"Bus_{i+1}": {
                    "voltage_pu": float(V[i]), 
                    "angle_rad": float(theta[i]),
                    "P_mw": float(P[i]*100.0),
                    "Q_mvar": float(Q[i]*100.0)
                } for i in range(9)},
                "lines": {lid: {
                    "P_mw": float(f["P_flow"]*100.0), 
                    "Q_mvar": float(f["Q_flow"]*100.0), 
                    "current_pu": float(f["current"])
                } for lid, f in line_flows.items()},
                "breakers": self.sandbox_breakers.copy()
            }
        }

    def process_live_telemetry(self) -> Dict[str, Any]:
        """
        Evaluates the current live grid state and compiles the Pre-RL status payload.
        """
        # Encode current state
        self.current_live_state_vec = self.encoder.encode_state(
            telemetry=self.latest_telemetry,
            threat_data=self.latest_threat_data,
            ai_prediction=self.latest_ai_prediction,
            multi_bus=self.latest_multi_bus,
            threat_aware=self.latest_threat_aware,
            pinn_forecast=self.latest_pinn_forecast,
            physics_val=self.latest_physics_val,
            trust_scores=self.latest_trust_scores,
            adaptive_filter=self.latest_adaptive_filter,
            orchestrator_data=self.latest_ai_orchestrator,
            override_active=1.0 if self.override.pause_autonomous else 0.0
        )
        
        # Parse vector with debugger
        debugger_data = self.debugger.deconstruct(self.current_live_state_vec)
        
        # Calculate PPO probabilities if PPO agent is available
        ppo_probs = None
        if self.ppo_agent is not None:
            try:
                import torch
                state_t = torch.FloatTensor(self.current_live_state_vec).to(self.ppo_agent.device)
                with torch.no_grad():
                    logits = self.ppo_agent.actor(state_t)
                    ppo_probs = torch.softmax(logits, dim=-1).cpu().numpy().squeeze(0)
            except Exception as e:
                logger.warning(f"Failed to calculate PPO probabilities for explanation: {e}")

        # Keep sandbox synchronized with live state when entering sandbox mode
        if self.sandbox_active and self.latest_telemetry:
            self.sandbox.reset_to_state(self.latest_telemetry)
            
        # Build Trusted Action Queue based on AI recommendations
        trusted_queue = []
        ai_recs = []
        if self.latest_recommended_actions and "recommendations" in self.latest_recommended_actions:
            ai_recs = self.latest_recommended_actions["recommendations"]
            
        for i, rec in enumerate(ai_recs):
            rec_action = rec.get("action")
            rec_target = rec.get("target")
            
            # Map recommendation string to discrete action ID
            mapped_action_id = 0
            for aid, act in self.registry.ACTIONS.items():
                if act["name"] == rec_action:
                    mapped_action_id = aid
                    break
                    
            if mapped_action_id == 0:
                continue
                
            action_meta = self.registry.get_action(mapped_action_id)
            
            # Evaluate constraints and trust scores via TrustedActionFilter
            allowed, reason, filter_metrics = self.filter.filter_action(
                action=action_meta,
                target=rec_target,
                telemetry=self.latest_telemetry,
                trust_scores=self.latest_trust_scores,
                pinn_forecast=self.latest_pinn_forecast,
                physics_validation=self.latest_physics_val
            )
            
            # Cyber defense containment override
            if allowed and self.latest_defense:
                esc_level = self.latest_defense.get("escalation_level", "ADVISORY")
                is_restoration = rec_action in ["RECONNECT_LINE", "REROUTE_FLOW", "ENABLE_RESTORATION"]
                restoration_locked = self.latest_defense.get("restoration_lockdown_active", False)
                if esc_level in ["EMERGENCY_CONTAINMENT", "GRID_PRESERVATION"]:
                    restoration_locked = True
                    
                if restoration_locked and is_restoration:
                    allowed = False
                    reason = f"Restoration locked down by active cyber defense containment ({esc_level})."
                elif rec_target in self.latest_defense.get("breaker_lockdown_targets", []):
                    allowed = False
                    reason = f"Target {rec_target} is locked down by cyber defense containment."
            
            # Run dry run rehearsal in sandbox
            sandbox_res = None
            if self.latest_telemetry:
                self.sandbox.reset_to_state(self.latest_telemetry)
                sandbox_res = self.sandbox.dry_run_action(rec_action, rec_target)

            # Generate explainer logs with PPO probabilities passed
            explain_record = self.explainer.explain_action(
                action_id=mapped_action_id,
                target=rec_target,
                state_vector=self.current_live_state_vec,
                sandbox_results=sandbox_res,
                ppo_probs=ppo_probs
            )
            
            trusted_queue.append({
                "queue_index": i,
                "action_id": mapped_action_id,
                "action": rec_action,
                "target": rec_target,
                "allowed": allowed,
                "reason": reason,
                "safety_score": float(filter_metrics["safety_score"]),
                "operational_risk": float(action_meta["operational_risk"]),
                "restoration_confidence": float(action_meta["restoration_confidence"]),
                "explainability": explain_record
            })
            
        # Formulate Safety Constraints status details
        safety_allowed, safety_violations, safety_score = self.safety.evaluate_constraints(
            self.latest_telemetry or {"state": {}}, "NO_ACTION", "SYSTEM"
        )
        
        # Calculate restoration readiness (percentage 0-100)
        restoration_readiness = 100.0
        if len(safety_violations) > 0:
            restoration_readiness -= 30.0
        if self.latest_pinn_forecast and self.latest_pinn_forecast.get("degraded_observability", False):
            restoration_readiness -= 25.0
        if self.latest_trust_scores:
            mean_trust = np.mean(list(self.latest_trust_scores.get("bus_trust", {}).values()))
            if mean_trust < 80.0:
                restoration_readiness -= (80.0 - mean_trust)
        restoration_readiness = max(0.0, min(100.0, restoration_readiness))
        
        # Compile timeline payload
        timeline_payload = self.timeline.get_timeline_payload()
        
        # Compile rollback status
        rollback_status = self.rollback.get_readiness_status()
        
        # Output Pre-RL Environment Status Payload
        payload = {
            "timestamp": int(time.time() * 1000),
            "sandbox_active": self.sandbox_active,
            "observation_vector": [round(float(x), 4) for x in self.current_live_state_vec],
            "observation_debug": debugger_data,
            "action_queue": trusted_queue,
            "safety_status": {
                "overall_score": round(safety_score, 2),
                "allowed": safety_allowed,
                "violations": safety_violations
            },
            "restoration_readiness": round(restoration_readiness, 1),
            "rollback_status": rollback_status,
            "timeline": timeline_payload,
            "operator_override": {
                "pause_autonomous": self.override.pause_autonomous,
                "emergency_stop_active": self.override.emergency_stop_active,
                "restoration_mode": self.override.restoration_mode,
                "execution_delay": self.override.execution_delay,
                "locked_breakers": self.override.locked_breakers,
                "audit_logs": self.override.get_audit_logs()
            },
            "rl_status": self.latest_rl_status
        }
        return payload

    def compile_live_rl_telemetry(self, ppo_probs=None) -> Dict[str, Any]:
        telemetry = self.latest_telemetry or {"state": {}}
        survivability = rl_metrics.calculate_grid_survivability(telemetry)
        
        cascade_prob = 0.0
        if self.latest_threat_data:
            cascade_prob = float(self.latest_threat_data.get("cascade_probability", 0.0))
        blackout_prob = rl_metrics.calculate_blackout_risk(telemetry, cascade_prob)
        
        # PPO confidence
        ppo_conf = 100.0
        if ppo_probs is not None:
            ppo_conf = float(np.max(ppo_probs)) * 100.0
            
        # Determine current RL objective
        objective = "NORMAL"
        buses = telemetry.get("state", {}).get("buses", {})
        breakers = telemetry.get("state", {}).get("breakers", {})
        
        voltage_deviation = False
        if buses:
            voltages = [b.get("voltage_pu", 1.0) for b in buses.values()]
            if any(v < 0.92 or v > 1.08 for v in voltages):
                voltage_deviation = True
                
        open_restorable = False
        if breakers:
            if breakers.get("L7_8") == "OPEN" and any(b.get("voltage_pu", 1.0) < 0.90 for b in buses.values()):
                open_restorable = True
                
        if self.latest_defense and self.latest_defense.get("escalation_level") in ["EMERGENCY_CONTAINMENT", "GRID_PRESERVATION"]:
            objective = "ISOLATE_FAULT"
        elif open_restorable:
            objective = "RECONNECT_LOAD"
        elif voltage_deviation:
            objective = "STABILIZE_VOLTAGE"
        elif any(stat == "OPEN" for lid, stat in breakers.items() if lid != "L7_8"):
            objective = "ISOLATE_FAULT"
            
        # Restoration Phase
        phase = "STABLE"
        flisr_state = telemetry.get("flisr_state", "NORMAL")
        if flisr_state == "FAULT_DETECTED":
            phase = "FAULT_ISOLATION"
        elif flisr_state in ["ISOLATED", "RECONFIGURING"]:
            phase = "POWER_RECONSTRUCT"
        elif any(stat == "OPEN" for lid, stat in breakers.items() if lid != "L7_8"):
            phase = "DEGRADED"
            
        # Recovery progress %
        load_bus_indices = ["Bus_5", "Bus_6", "Bus_8"]
        serviced_loads = 0
        for bid in load_bus_indices:
            if buses and bid in buses:
                if buses[bid].get("voltage_pu", 0.0) > 0.90:
                    serviced_loads += 1
        progress = (serviced_loads / len(load_bus_indices)) * 100.0 if load_bus_indices else 100.0
        
        return {
            "timestamp": int(time.time() * 1000),
            "current_rl_objective": objective,
            "restoration_phase": phase,
            "topology_health": round(survivability, 2),
            "blackout_probability": round(blackout_prob, 2),
            "ppo_confidence": round(ppo_conf, 2),
            "recovery_progress": round(progress, 2)
        }

# Live Daemon Service Execution Loop
def run_live_daemon():
    MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
    MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
    
    env = GridRLEnvironment(is_live_mode=True)
    env.reset()
    
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            logger.info("Pre-RL Foundation Daemon connected to MQTT!")
            client.subscribe("grid/telemetry")
            client.subscribe("grid/events")
            client.subscribe("grid/alerts")
            client.subscribe("grid/control")
            client.subscribe("grid/attack")
            client.subscribe("grid/threat")
            client.subscribe("grid/ai_prediction")
            client.subscribe("grid/ai_forecast_multi_bus")
            client.subscribe("grid/ai_threat_forecast")
            client.subscribe("grid/pinn_forecast")
            client.subscribe("grid/physics_validation")
            client.subscribe("grid/trust_scores")
            client.subscribe("grid/adaptive_filter")
            client.subscribe("grid/ai_orchestrator")
            client.subscribe("grid/recommended_actions")
            client.subscribe("grid/pre_rl/control")
            client.subscribe("grid/rl/status")
            client.subscribe("grid/defense")
        else:
            logger.error(f"MQTT connection failed with code {rc}")
            
    def on_message(client, userdata, msg):
        try:
            topic = msg.topic
            payload = json.loads(msg.payload.decode("utf-8"))
            
            if topic == "grid/telemetry":
                env.latest_telemetry = payload
                # Compile and publish Pre-RL states
                compiled = env.process_live_telemetry()
                client.publish("grid/pre_rl", json.dumps(compiled))
                
                # Publish live RL metrics
                ppo_probs = None
                if env.ppo_agent is not None:
                    try:
                        import torch
                        state_t = torch.FloatTensor(env.current_live_state_vec).to(env.ppo_agent.device)
                        with torch.no_grad():
                            logits = env.ppo_agent.actor(state_t)
                            ppo_probs = torch.softmax(logits, dim=-1).cpu().numpy().squeeze(0)
                    except Exception as e:
                        pass
                rl_telemetry = env.compile_live_rl_telemetry(ppo_probs=ppo_probs)
                client.publish("grid/rl/telemetry", json.dumps(rl_telemetry))
                
                # Check for automatic action execution if in AUTO mode
                if env.override.restoration_mode == "AUTO" and not env.override.pause_autonomous and not env.override.emergency_stop_active:
                    # Perform live PPO model inference if available
                    if env.ppo_agent is not None:
                        action_id, _, _ = env.ppo_agent.select_action(env.current_live_state_vec, evaluation=True)
                        action_meta = env.registry.get_action(action_id)
                        act_name = action_meta["name"]
                        
                        if action_id == 0:
                            logger.info("[PPO LIVE INFERENCE] PPO selected NO_ACTION. Grid is stable.")
                        else:
                            act_target = env.get_target_for_action(action_id, env.current_live_state_vec)
                            
                            # Adaptive behavior: check if this action was already attempted and failed
                            if (act_name, act_target) in env.episode_failed_actions:
                                logger.warning(f"[PPO LIVE ADAPTIVE] PPO proposed repeated failed action {act_name} targeting {act_target}. Blocking to avoid unsafe loop.")
                                allowed = False
                                reason = f"Repeated failed action {act_name} on {act_target} blocked by orchestrator."
                            else:
                                # Validate the selected action via TrustedActionFilter
                                allowed = False
                                reason = ""
                                if env.latest_telemetry:
                                    allowed, reason, _ = env.filter.filter_action(
                                        action=action_meta,
                                        target=act_target,
                                        telemetry=env.latest_telemetry,
                                        trust_scores=env.latest_trust_scores,
                                        pinn_forecast=env.latest_pinn_forecast,
                                        physics_validation=env.latest_physics_val
                                    )
                                
                            # Check cyber defense restrictions
                            if allowed and env.latest_defense:
                                esc_level = env.latest_defense.get("escalation_level", "ADVISORY")
                                is_restoration = act_name in ["RECONNECT_LINE", "REROUTE_FLOW", "ENABLE_RESTORATION"]
                                restoration_locked = env.latest_defense.get("restoration_lockdown_active", False)
                                if esc_level in ["EMERGENCY_CONTAINMENT", "GRID_PRESERVATION"]:
                                    restoration_locked = True
                                    
                                if restoration_locked and is_restoration:
                                    allowed = False
                                    reason = f"Restoration locked down by active cyber defense containment ({esc_level})."
                                elif act_target in env.latest_defense.get("breaker_lockdown_targets", []):
                                    allowed = False
                                    reason = f"Target {act_target} is locked down by cyber defense containment."
                                
                            if allowed:
                                is_override_allowed, override_reason = env.override.is_action_allowed(act_name, act_target)
                                if is_override_allowed:
                                    if env.override.execution_delay > 0:
                                        logger.info(f"Simulating operator execution delay: sleeping {env.override.execution_delay}s")
                                        time.sleep(env.override.execution_delay)
                                        
                                    if env.latest_telemetry:
                                        env.rollback.push_checkpoint(
                                            env.latest_telemetry.get("state", {}).get("breakers", {}),
                                            env.latest_trust_scores
                                        )
                                    cmd_str = "OPEN" if act_name in ["ISOLATE_LINE", "OPEN_BREAKER", "ISOLATE_BUS", "ENABLE_ISLANDING"] else "CLOSED"
                                    control_payload = {
                                        "command": cmd_str,
                                        "target": act_target,
                                        "source": "AI_RL_PPO_CONTROL"
                                    }
                                    client.publish("grid/control/proposed", json.dumps(control_payload))
                                    env.override.record_execution(act_name, act_target)
                                    env.timeline.record_event("ACTION_SELECTED", f"PPO LIVE: executed [{act_name}] targeting {act_target}.")
                                else:
                                    logger.warning(f"[PPO CONTROL BLOCKED] Action blocked by operator override: {override_reason}")
                            else:
                                logger.warning(f"[PPO CONTROL BLOCKED] Action rejected by safety filters: {reason}")
                                
                                # Safety fallback: execute first allowed rule-based action if PPO proposed an unsafe one
                                for action_item in compiled.get("action_queue", []):
                                    if action_item.get("allowed"):
                                        fb_name = action_item["action"]
                                        fb_target = action_item["target"]
                                        is_fb_allowed, _ = env.override.is_action_allowed(fb_name, fb_target)
                                        if is_fb_allowed:
                                            if env.override.execution_delay > 0:
                                                time.sleep(env.override.execution_delay)
                                            if env.latest_telemetry:
                                                env.rollback.push_checkpoint(
                                                    env.latest_telemetry.get("state", {}).get("breakers", {}),
                                                    env.latest_trust_scores
                                                )
                                            cmd_str = "OPEN" if fb_name in ["ISOLATE_LINE", "OPEN_BREAKER", "ISOLATE_BUS", "ENABLE_ISLANDING"] else "CLOSED"
                                            control_payload = {
                                                "command": cmd_str,
                                                "target": fb_target,
                                                "source": "AI_AUTONOMOUS_CONTROL_FALLBACK"
                                            }
                                            client.publish("grid/control/proposed", json.dumps(control_payload))
                                            env.override.record_execution(fb_name, fb_target)
                                            env.timeline.record_event("ACTION_SELECTED", f"PPO GATED FALLBACK: executed [{fb_name}] targeting {fb_target}.")
                                            break
                    else:
                        # Fallback to default heuristic if agent is not loaded
                        for action_item in compiled.get("action_queue", []):
                            if action_item.get("allowed"):
                                act_name = action_item["action"]
                                act_target = action_item["target"]
                                is_allowed, reason = env.override.is_action_allowed(act_name, act_target)
                                if is_allowed:
                                    if env.override.execution_delay > 0:
                                        time.sleep(env.override.execution_delay)
                                    if env.latest_telemetry:
                                        env.rollback.push_checkpoint(
                                            env.latest_telemetry.get("state", {}).get("breakers", {}),
                                            env.latest_trust_scores
                                        )
                                    cmd_str = "OPEN" if act_name in ["ISOLATE_LINE", "OPEN_BREAKER", "ISOLATE_BUS", "ENABLE_ISLANDING"] else "CLOSED"
                                    control_payload = {
                                        "command": cmd_str,
                                        "target": act_target,
                                        "source": "AI_AUTONOMOUS_CONTROL"
                                    }
                                    client.publish("grid/control/proposed", json.dumps(control_payload))
                                    env.override.record_execution(act_name, act_target)
                                    env.timeline.record_event("ACTION_SELECTED", f"AI AUTO: executed [{act_name}] targeting {act_target}.")
                                    break
                                
            elif topic == "grid/threat":
                env.latest_threat_data = payload
            elif topic == "grid/ai_prediction":
                env.latest_ai_prediction = payload
            elif topic == "grid/ai_forecast_multi_bus":
                env.latest_multi_bus = payload
            elif topic == "grid/ai_threat_forecast":
                env.latest_threat_aware = payload
            elif topic == "grid/pinn_forecast":
                env.latest_pinn_forecast = payload
            elif topic == "grid/physics_validation":
                env.latest_physics_val = payload
            elif topic == "grid/trust_scores":
                env.latest_trust_scores = payload
            elif topic == "grid/adaptive_filter":
                env.latest_adaptive_filter = payload
            elif topic == "grid/ai_orchestrator":
                env.latest_ai_orchestrator = payload
            elif topic == "grid/recommended_actions":
                env.latest_recommended_actions = payload
            elif topic == "grid/rl/status":
                env.latest_rl_status = payload
            elif topic == "grid/defense":
                env.latest_defense = payload
                
            elif topic == "grid/attack":
                atk_type = payload.get("attack_type", "UNKNOWN")
                atk_target = payload.get("target", "SYSTEM")
                env.timeline.record_event("ATTACK_DETECTED", f"Attack injection: type {atk_type} targeting {atk_target}.")
                
            elif topic == "grid/events":
                event_str = payload.get("event", "")
                source_str = payload.get("source", "")
                if "compromise" in event_str.lower() or "compromised" in event_str.lower():
                    env.timeline.record_event("ATTACK_DETECTED", f"[{source_str}] Cyber compromise: {event_str}")
                elif "trip" in event_str.lower() or "tripped" in event_str.lower():
                    env.timeline.record_event("TOPOLOGY_INSTABILITY", f"[{source_str}] Breaker trip: {event_str}")
                elif "restored" in event_str.lower():
                    env.timeline.record_event("RESTORATION_SUCCESS", f"[{source_str}] Grid restoration: {event_str}")
                    
            elif topic == "grid/pre_rl/control":
                cmd = payload.get("command")
                target = payload.get("target", "SYSTEM")
                
                logger.info(f"Operator control command received on grid/pre_rl/control: {cmd} targeting {target}")
                
                if cmd == "PAUSE_AUTONOMOUS":
                    env.override.set_pause(True)
                    env.timeline.record_event("STATUS_UPDATE", "Operator paused autonomous execution.")
                elif cmd == "RESUME_AUTONOMOUS":
                    env.override.set_pause(False)
                    env.timeline.record_event("STATUS_UPDATE", "Operator resumed autonomous execution.")
                elif cmd == "EMERGENCY_STOP":
                    env.override.trigger_emergency_stop()
                    env.timeline.record_event("STATUS_UPDATE", "CRITICAL: Operator engaged EMERGENCY STOP.")
                elif cmd == "CLEAR_EMERGENCY_STOP":
                    env.override.clear_emergency_stop()
                    env.timeline.record_event("STATUS_UPDATE", "Operator disengaged emergency stop.")
                elif cmd == "LOCK_ACTION":
                    env.override.lock_breaker(target)
                elif cmd == "UNLOCK_ACTION":
                    env.override.unlock_breaker(target)
                elif cmd == "SET_DELAY":
                    env.override.set_execution_delay(float(payload.get("delay", 0.0)))
                elif cmd == "LOCK_RESTORATION":
                    env.override.set_restoration_mode(payload.get("mode", "SEMI_AUTONOMOUS"))
                elif cmd == "ENTER_SANDBOX":
                    env.sandbox_active = True
                    if env.latest_telemetry:
                        env.sandbox_breakers = env.latest_telemetry.get("state", {}).get("breakers", {}).copy()
                        env.sandbox.reset_to_state(env.latest_telemetry)
                    env.timeline.record_event("RESTORATION_INITIATED", "Operator activated Sandbox Rehearsal Mode.")
                elif cmd == "EXIT_SANDBOX":
                    env.sandbox_active = False
                    env.timeline.record_event("STATUS_UPDATE", "Operator deactivated Sandbox Rehearsal Mode.")
                elif cmd == "FORCE_ROLLBACK":
                    brk, trust = env.rollback.rollback_to_last()
                    if brk:
                        for lid, state in brk.items():
                            control_payload = {
                                "command": state,
                                "target": lid,
                                "source": "OPERATOR_FORCE_ROLLBACK"
                            }
                            client.publish("grid/control", json.dumps(control_payload))
                        env.timeline.record_event("ROLLBACK_TRIGGERED", "Operator triggered manual rollback checkpoint.")
                    else:
                        logger.warning("Operator force rollback triggered, but no checkpoints exist.")
                elif cmd == "REVERT_ACTION":
                    # Rollback the last executed action from live history
                    act_name, act_target = env.override.get_last_executed_action()
                    if act_name:
                        opposite_cmd = "CLOSED" if act_name in ["ISOLATE_LINE", "OPEN_BREAKER", "ISOLATE_BUS", "ENABLE_ISLANDING"] else "OPEN"
                        control_payload = {
                            "command": opposite_cmd,
                            "target": act_target,
                            "source": "OPERATOR_OVERRIDE_ROLLBACK"
                        }
                        client.publish("grid/control", json.dumps(control_payload))
                        env.override.pop_last_executed_action()
                        env.override._log_override(act_target, "ROLLBACK_ACTION", f"Reverted last action {act_name} -> command {opposite_cmd}")
                        env.timeline.record_event("ROLLBACK_TRIGGERED", f"Operator reverted action [{act_name}] on {act_target}.")
                    else:
                        logger.warning("Operator revert requested but no actions exist in historical rollback cache.")
                elif cmd == "APPROVE_ACTION":
                    action_id = payload.get("action_id", 0)
                    action_meta = env.registry.get_action(action_id)
                    act_name = action_meta["name"]
                    
                    env.override.approve_action(act_name, target)
                    allowed, reason = env.override.is_action_allowed(act_name, target)
                    if allowed:
                        if env.latest_telemetry:
                            env.rollback.push_checkpoint(
                                env.latest_telemetry.get("state", {}).get("breakers", {}),
                                env.latest_trust_scores
                            )
                        cmd_str = "OPEN" if act_name in ["ISOLATE_LINE", "OPEN_BREAKER", "ISOLATE_BUS", "ENABLE_ISLANDING"] else "CLOSED"
                        control_payload = {
                            "command": cmd_str,
                            "target": target,
                            "source": "OPERATOR_OVERRIDE_APPROVAL"
                        }
                        client.publish("grid/control", json.dumps(control_payload))
                        env.override.record_execution(act_name, target)
                        env.timeline.record_event("RESTORATION_INITIATED", f"Operator manually approved [{act_name}] command targeting {target}.")
                    else:
                        logger.warning(f"Operator override blocked manual execution of action: {reason}")
                        
        except Exception as e:
            logger.error(f"Error handling message on {msg.topic}: {e}", exc_info=True)
            
    client = mqtt.Client(client_id="ai_pre_rl_foundation_service")
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
        client.loop_forever()
    except KeyboardInterrupt:
        logger.info("Stopping Pre-RL Foundation Service...")
    except Exception as e:
        logger.error(f"MQTT loop failed: {e}")
        os._exit(1)

if __name__ == "__main__":
    run_live_daemon()
