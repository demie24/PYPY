import os
import sys
import json
import time
import random
import logging
import copy
import numpy as np
import torch
import paho.mqtt.client as mqtt

# Setup paths to import core files
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(CURRENT_DIR)
sys.path.append(os.path.abspath(os.path.join(CURRENT_DIR, "..")))
sys.path.append(os.path.abspath(os.path.join(CURRENT_DIR, "..", "..", "digital_twin")))

from ppo_agent import PPOAgent
from dqn_agent import DQNAgent
from replay_buffer import ReplayBuffer, PPOMemory
from rl_environment import GridRLEnvironment

# Set up project root and directories
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", "..", ".."))
CHECKPOINTS_DIR = os.path.join(PROJECT_ROOT, "checkpoints")
LOGS_DIR = os.path.join(PROJECT_ROOT, "training_logs")
ANALYTICS_DIR = os.path.join(PROJECT_ROOT, "analytics")

os.makedirs(CHECKPOINTS_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)
os.makedirs(ANALYTICS_DIR, exist_ok=True)

# Configure file logging
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

# Avoid adding multiple duplicate handlers
handler_exists = any(isinstance(h, logging.FileHandler) and h.baseFilename == os.path.abspath(os.path.join(LOGS_DIR, "rl_training_run.log")) for h in root_logger.handlers)

if not handler_exists:
    file_handler = logging.FileHandler(os.path.join(LOGS_DIR, "rl_training_run.log"))
    file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    root_logger.addHandler(file_handler)

# Ensure stream handler exists for stdout
if not any(isinstance(h, logging.StreamHandler) for h in root_logger.handlers):
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    root_logger.addHandler(stream_handler)

logger = logging.getLogger("self_healing.rl.rl_trainer")

def get_target_for_action(action_id: int, state: np.ndarray, env: GridRLEnvironment) -> str:
    """
    Selects the most appropriate target string for the given action category
    based on the current grid state vector.
    """
    action_meta = env.registry.get_action(action_id)
    target_type = action_meta.get("target")
    
    if target_type == "SYSTEM" or target_type == "FLISR":
        return "SYSTEM"
    elif target_type == "ORCHESTRATOR":
        return "EMERGENCY_DEFENSE"
    elif target_type == "ZONE":
        return "ZONE_1"
        
    # Extract states from state vector
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
        else: # RECONNECT_LINE or REROUTE_FLOW
            open_lines = [i for i, b in enumerate(breakers) if b < 0.5]
            if not open_lines:
                return "L7_8"
            open_lines.sort(key=lambda idx: line_trust[idx], reverse=True)
            return line_names[open_lines[0]]
            
    elif target_type == "NODE" or target_type == "BUS":
        if action_meta["name"] in ["REJECT_TELEMETRY", "ISOLATE_BUS"]:
            lowest_trust_idx = int(np.argmin(bus_trust))
            return bus_names[lowest_trust_idx]
        else: # RESTORE_TELEMETRY_TRUST
            distrusted_buses = [i for i, t in enumerate(bus_trust) if t < 0.8]
            if not distrusted_buses:
                return "Bus_1"
            distrusted_buses.sort(key=lambda idx: bus_trust[idx], reverse=True)
            return bus_names[distrusted_buses[0]]
            
    return "SYSTEM"

def run_training(agent_type: str = "PPO", num_episodes: int = 1000, max_steps: int = 15, checkpoint_interval: int = 50):
    logger.info(f"Starting {agent_type} training loop for {num_episodes} episodes...")
    
    # Setup MQTT publisher
    MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
    MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
    
    mqtt_client = mqtt.Client(client_id=f"rl_trainer_{agent_type.lower()}")
    try:
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
        mqtt_client.loop_start()
        logger.info(f"Connected to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}")
    except Exception as e:
        logger.warning(f"Could not connect to MQTT broker: {e}. Running without MQTT updates.")
        mqtt_client = None

    # Initialize analytics CSV with expanded metrics
    csv_path = os.path.join(ANALYTICS_DIR, "rl_training_analytics.csv")
    if not os.path.exists(csv_path):
        with open(csv_path, "w") as f:
            f.write("episode,curriculum_level,scenario,steps,reward,rolling_avg_reward,loss,success_rate,"
                    "blocked_action_frequency,rollback_count,containment_conflicts,policy_confidence,unsafe_action_count,"
                    "restoration_completion_pct,unsafe_topology_freq,avg_voltage_deviation,containment_count,"
                    "recovery_latency,entropy,explore_ratio,action_diversity\n")

    # Instantiate environment in offline mode
    env = GridRLEnvironment(is_live_mode=False)
    state_dim = 72
    action_dim = 10
    
    # Initialize Agent
    if agent_type == "PPO":
        agent = PPOAgent(state_dim=state_dim, action_dim=action_dim)
        memory = PPOMemory()
    else:
        agent = DQNAgent(state_dim=state_dim, action_dim=action_dim)
        memory = ReplayBuffer(capacity=5000)
        
    recent_rewards = []
    recent_successes = []
    recent_entropies = []
    safety_violations = 0
    rollback_count = 0
    containment_conflicts = 0
    total_steps_taken = 0
    curriculum_level = 1
    
    for episode in range(1, num_episodes + 1):
        # Calculate moving statistics
        avg_reward = np.mean(recent_rewards) if recent_rewards else -50.0
        rolling_success_rate = np.mean(recent_successes) if recent_successes else 0.0

        # --- REDESIGNED CURRICULUM PACING GATING ---
        # Level 1 -> Level 2
        # Requires episode > 150 (or > 50 with early promote), avg_reward >= 5.0, and rolling_success_rate >= 0.70
        if curriculum_level == 1:
            if (episode > 150) or (episode > 50 and avg_reward >= 5.0 and rolling_success_rate >= 0.70):
                if avg_reward >= 5.0 and rolling_success_rate >= 0.70:
                    curriculum_level = 2
                    logger.info(f"Promoted to Curriculum Level 2 | Avg Reward: {avg_reward:.2f}, Success: {rolling_success_rate:.2f}")

        # Level 2 -> Level 3
        # Requires episode > 450 (or > 150 with early promote), avg_reward >= 8.0, and rolling_success_rate >= 0.80
        elif curriculum_level == 2:
            if (episode > 450) or (episode > 150 and avg_reward >= 8.0 and rolling_success_rate >= 0.80):
                if avg_reward >= 8.0 and rolling_success_rate >= 0.80:
                    curriculum_level = 3
                    logger.info(f"Promoted to Curriculum Level 3 | Avg Reward: {avg_reward:.2f}, Success: {rolling_success_rate:.2f}")

        # --- CURRICULUM REGRESSION LOGIC ---
        if curriculum_level == 3:
            if avg_reward < 2.0 or rolling_success_rate < 0.60:
                curriculum_level = 2
                logger.info(f"Regressed to Curriculum Level 2 | Avg Reward: {avg_reward:.2f}, Success: {rolling_success_rate:.2f}")
        elif curriculum_level == 2:
            if avg_reward < 0.0 or rolling_success_rate < 0.50:
                curriculum_level = 1
                logger.info(f"Regressed to Curriculum Level 1 | Avg Reward: {avg_reward:.2f}, Success: {rolling_success_rate:.2f}")

        state, info = env.reset()
        state_init = copy.deepcopy(state)
        init_deenergized = sum(1 for idx in [4, 5, 7] if state_init[idx] <= 0.90)

        # Reset scene-specific variables on env
        env.latest_defense = None
        env.latest_threat_data = None
        env.latest_physics_val = None
        env.latest_trust_scores = {
            "bus_trust": {f"Bus_{i}": 100.0 for i in range(1, 10)},
            "line_trust": {lid: 100.0 for lid in env.sandbox_breakers.keys()}
        }
        
        # Inject scenario based on curriculum level
        if curriculum_level == 1:
            scenario = random.choice(["OVERLOAD", "LINE_FAULT"])
            if scenario == "OVERLOAD":
                env.sandbox_breakers["L7_8"] = "OPEN"
                env.sandbox_loads[4]["P"] = 2.0 * env.topo.loads[4]["P_nom"]
                env.sandbox_loads[5]["P"] = 1.5 * env.topo.loads[5]["P_nom"]
                env.latest_telemetry = env._get_sandbox_telemetry_snapshot()
                state = env.encoder.encode_state(telemetry=env.latest_telemetry)
            else: # LINE_FAULT
                fault_line = random.choice(["L4_5", "L2_7"])
                env.sandbox_breakers[fault_line] = "OPEN"
                env.latest_telemetry = env._get_sandbox_telemetry_snapshot()
                state = env.encoder.encode_state(telemetry=env.latest_telemetry)
                
        elif curriculum_level == 2:
            scenario = random.choice(["FDIA", "REPLAY_ATTACK"])
            if scenario == "FDIA":
                env.latest_trust_scores["bus_trust"]["Bus_5"] = 15.0
                env.latest_threat_data = {
                    "anomaly_score": 0.88,
                    "cyber_attack_probability": 0.90,
                    "threat_level": "HIGH"
                }
                env.latest_physics_val = {
                    "kcl_mismatches": {"Bus_5": 0.35},
                    "overall_validation_score": 0.45
                }
                state = env.encoder.encode_state(
                    telemetry=env._get_sandbox_telemetry_snapshot(),
                    trust_scores=env.latest_trust_scores,
                    threat_data=env.latest_threat_data,
                    physics_val=env.latest_physics_val
                )
            else: # REPLAY_ATTACK
                env.latest_trust_scores["line_trust"]["L4_5"] = 25.0
                env.latest_trust_scores["line_trust"]["L5_6"] = 25.0
                env.latest_threat_data = {
                    "anomaly_score": 0.75,
                    "cyber_attack_probability": 0.80,
                    "threat_level": "MEDIUM"
                }
                state = env.encoder.encode_state(
                    telemetry=env._get_sandbox_telemetry_snapshot(),
                    trust_scores=env.latest_trust_scores,
                    threat_data=env.latest_threat_data
                )
                
        else: # Level 3
            scenario = random.choice(["COORDINATED_ATTACK", "CASCADING_INSTABILITY"])
            if scenario == "COORDINATED_ATTACK":
                env.sandbox_breakers["L4_5"] = "OPEN"
                env.latest_trust_scores["bus_trust"]["Bus_5"] = 10.0
                env.latest_trust_scores["bus_trust"]["Bus_6"] = 10.0
                env.latest_threat_data = {
                    "anomaly_score": 0.98,
                    "cyber_attack_probability": 0.99,
                    "threat_level": "CRITICAL",
                    "coordinated_attack_detected": True
                }
                env.latest_defense = {
                    "escalation_level": "EMERGENCY_CONTAINMENT",
                    "restoration_lockdown_active": True,
                    "breaker_lockdown_targets": ["L4_5", "L5_6"]
                }
                state = env.encoder.encode_state(
                    telemetry=env._get_sandbox_telemetry_snapshot(),
                    trust_scores=env.latest_trust_scores,
                    threat_data=env.latest_threat_data,
                    orchestrator_data={"escalation_level": "EMERGENCY_CONTAINMENT"}
                )
            else: # CASCADING_INSTABILITY
                env.sandbox_breakers["L4_5"] = "OPEN"
                env.sandbox_breakers["L7_8"] = "OPEN"
                env.sandbox_loads[4]["P"] = 1.6 * env.topo.loads[4]["P_nom"]
                env.sandbox_loads[5]["P"] = 1.6 * env.topo.loads[5]["P_nom"]
                env.latest_threat_data = {
                    "cascade_risk_index": 0.95,
                    "threat_level": "HIGH"
                }
                state = env.encoder.encode_state(
                    telemetry=env._get_sandbox_telemetry_snapshot(),
                    threat_data=env.latest_threat_data
                )

        episode_reward = 0.0
        episode_violations = 0
        episode_rollbacks = 0
        episode_containment_conflicts = 0
        loss_val = 0.0
        entropy_val = 0.0
        
        # Stabilization and diagnostics tracking accumulators
        action_history = []
        breaker_action_history = {}
        cooldown_steps_remaining = 0
        episode_confidences = []
        
        unsafe_topology_steps = 0
        total_voltage_dev = 0.0
        successful_containment_count = 0
        first_stable_step = None
        explore_steps = 0
        actions_chosen = []
        
        for step in range(max_steps):
            total_steps_taken += 1
            
            # Select action
            if agent_type == "PPO":
                action_id, prob, val = agent.select_action(state, evaluation=False)
            else:
                action_id, q_val = agent.select_action(state, evaluation=False)
                
            # Determine target and argmax action for exploration metrics
            target = get_target_for_action(action_id, state, env)
            action_meta = env.registry.get_action(action_id)
            action_name = action_meta["name"]
            
            state_t = torch.FloatTensor(state).to(agent.device)
            with torch.no_grad():
                if agent_type == "PPO":
                    logits = agent.actor(state_t)
                    probs = torch.softmax(logits, dim=-1).cpu().numpy().squeeze(0)
                    argmax_action = int(np.argmax(probs))
                else:
                    q_values = agent.q_net(state_t)
                    probs = torch.softmax(q_values, dim=-1).cpu().numpy().squeeze(0)
                    argmax_action = int(torch.argmax(q_values, dim=-1).item())
            
            if action_id != argmax_action:
                explore_steps += 1
            actions_chosen.append(action_id)
            
            # --- STABILIZATION PROTECTION 1: Cooldown check ---
            in_cooldown = False
            cooldown_penalty = 0.0
            if cooldown_steps_remaining > 0:
                cooldown_steps_remaining -= 1
                if action_id != 0:
                    action_id = 0
                    action_meta = env.registry.get_action(0)
                    action_name = action_meta["name"]
                    target = "SYSTEM"
                    in_cooldown = True
                    cooldown_penalty = -1.0
                    
            active_actions_recent = sum(1 for act, _ in action_history[-5:] if act != "NO_ACTION")
            if active_actions_recent >= 3 and cooldown_steps_remaining == 0:
                cooldown_steps_remaining = 2
                
            # --- STABILIZATION PROTECTION 2: Anti-action spam ---
            is_spam = False
            spam_penalty = 0.0
            if action_id != 0:
                if len(action_history) > 0 and action_history[-1] == (action_name, target):
                    is_spam = True
                elif sum(1 for act, trg in action_history[-3:] if act == action_name and trg == target) >= 2:
                    is_spam = True
                    
                if is_spam:
                    action_id = 0
                    action_meta = env.registry.get_action(0)
                    action_name = action_meta["name"]
                    target = "SYSTEM"
                    spam_penalty = -3.0
                    
            # --- STABILIZATION PROTECTION 3: Oscillation prevention ---
            is_oscillation = False
            oscillation_penalty = 0.0
            if action_id != 0 and action_name in ["ISOLATE_LINE", "RECONNECT_LINE", "OPEN_BREAKER"]:
                brk_cmd = "OPEN" if action_name in ["ISOLATE_LINE", "OPEN_BREAKER"] else "CLOSED"
                history_list = breaker_action_history.get(target, [])
                if len(history_list) >= 2:
                    if history_list[-1] != brk_cmd and history_list[-2] == brk_cmd:
                        is_oscillation = True
                        
                if is_oscillation:
                    action_id = 0
                    action_meta = env.registry.get_action(0)
                    action_name = action_meta["name"]
                    target = "SYSTEM"
                    oscillation_penalty = -4.0

            # Calculate policy confidence for logging
            policy_confidence = float(probs[action_id])
            episode_confidences.append(policy_confidence)

            # Record action history
            action_history.append((action_name, target))
            if len(action_history) > 10:
                action_history.pop(0)
                
            if action_id != 0 and action_name in ["ISOLATE_LINE", "RECONNECT_LINE", "OPEN_BREAKER"] and not is_spam and not is_oscillation and not in_cooldown:
                brk_cmd = "OPEN" if action_name in ["ISOLATE_LINE", "OPEN_BREAKER"] else "CLOSED"
                if target not in breaker_action_history:
                    breaker_action_history[target] = []
                breaker_action_history[target].append(brk_cmd)
                if len(breaker_action_history[target]) > 5:
                    breaker_action_history[target].pop(0)

            # Save states for topology rollbacks
            prev_breakers = copy.deepcopy(env.sandbox_breakers)
            prev_trust = copy.deepcopy(env.latest_trust_scores)
            
            # Execute step
            next_state, reward, terminated, truncated, info_step = env.step(action_id, target)
            
            # --- STABILIZATION PROTECTION 4: Unsafe topology rollback & gating ---
            rollback_occurred = False
            is_containment_conflict = False
            
            # Check if step resulted in an unsafe topology state
            is_unsafe_step = False
            if not info_step.get("action_allowed", True):
                is_unsafe_step = True
                episode_violations += 1
                safety_violations += 1
                episode_rollbacks += 1
                rollback_count += 1
                rollback_occurred = True
                
                # Verify containment conflict
                rejection_reason = info_step.get("rejection_reason", "").lower()
                if "containment" in rejection_reason or "defense" in rejection_reason:
                    is_containment_conflict = True
                    episode_containment_conflicts += 1
                    containment_conflicts += 1
                
                action_id = 0
                repeated_failed_action = (action_name, target) in env.episode_failed_actions
                env.episode_failed_actions.add((action_name, target))
                env.episode_rollbacks += 1
                reward, _ = env.reward_engine.compute_reward(
                    state, next_state, action_id, rollback_occurred=True, defense_status=env.latest_defense,
                    repeated_failed_action=repeated_failed_action, step_count=env.step_count
                )
            else:
                # Check for severe voltage violations
                voltages = next_state[0:9]
                severe_violation = np.any(voltages < 0.85) or np.any(voltages > 1.15)
                
                if severe_violation:
                    is_unsafe_step = True
                    # Revert grid topology
                    env.sandbox_breakers = copy.deepcopy(prev_breakers)
                    env.latest_trust_scores = copy.deepcopy(prev_trust)
                    V, theta, P, Q, line_flows = env.physics.solve(
                        env.sandbox_breakers, env.sandbox_loads, env.sandbox_gen_P, env.sandbox_gen_Q
                    )
                    next_state = env.encoder.encode_state(
                        telemetry=env._get_sandbox_telemetry_snapshot(),
                        trust_scores=env.latest_trust_scores,
                        threat_data=env.latest_threat_data,
                        physics_val=env.latest_physics_val,
                        orchestrator_data={"escalation_level": env.latest_defense.get("escalation_level") if env.latest_defense else None}
                    )
                    rollback_occurred = True
                    episode_rollbacks += 1
                    rollback_count += 1
                    
                    repeated_failed_action = (action_name, target) in env.episode_failed_actions
                    env.episode_failed_actions.add((action_name, target))
                    env.episode_rollbacks += 1
                    reward, _ = env.reward_engine.compute_reward(
                        state, next_state, action_id, rollback_occurred=True, defense_status=env.latest_defense,
                        repeated_failed_action=repeated_failed_action, step_count=env.step_count
                    )
            
            if is_unsafe_step:
                unsafe_topology_steps += 1
                
            # Fused metrics updates
            voltages = next_state[0:9]
            total_voltage_dev += np.mean(np.abs(voltages - 1.0))
            
            # Verify containment count
            if action_id in [1, 3, 6] and not rollback_occurred:
                is_degraded = False
                if action_id in [3, 6] and np.min(list(prev_trust.get("bus_trust", {}).values())) < 50.0:
                    is_degraded = True
                elif action_id == 1 and np.min(list(prev_trust.get("line_trust", {}).values())) < 50.0:
                    is_degraded = True
                if is_degraded:
                    successful_containment_count += 1
                    
            # Verify recovery latency
            if np.all(voltages >= 0.90) and np.all(voltages <= 1.10) and first_stable_step is None:
                first_stable_step = step + 1
            
            total_step_reward = reward + cooldown_penalty + spam_penalty + oscillation_penalty
            episode_reward += total_step_reward
            done = terminated or truncated
            
            # Store in memory
            if agent_type == "PPO":
                memory.push(state, action_id, prob, val, total_step_reward, done)
            else:
                memory.push(state, action_id, total_step_reward, next_state, done)
                
            state = next_state
            
            # Perform optimization update
            if agent_type == "DQN" and len(memory) > 32:
                batch = memory.sample(batch_size=32)
                loss_val = agent.update(batch)
                agent.decay_epsilon()
                
            if done:
                break
                
        # PPO policy updates at end of episode trajectory
        if agent_type == "PPO" and len(memory) > 0:
            ppo_data = memory.sample()
            actor_loss, critic_loss, entropy = agent.update(ppo_data, batch_size=8)
            loss_val = float(actor_loss + critic_loss)
            entropy_val = float(entropy)
            memory.clear()
            
        recent_rewards.append(episode_reward)
        if len(recent_rewards) > 10:
            recent_rewards.pop(0)
            
        avg_reward = np.mean(recent_rewards)
        
        # Calculate success metric (nominal grid voltages and loads serviced)
        final_voltages = state[0:9]
        is_success = 1.0 if (np.all(final_voltages > 0.88) and np.all(final_voltages < 1.12)) else 0.0
        recent_successes.append(is_success)
        if len(recent_successes) > 100:
            recent_successes.pop(0)
            
        rolling_success_rate = np.mean(recent_successes)
        
        # Calculate expanded metrics
        end_deenergized = sum(1 for idx in [4, 5, 7] if state[idx] <= 0.90)
        restoration_completion_pct = 100.0 if init_deenergized == 0 else 100.0 * (1.0 - (end_deenergized / init_deenergized))
        
        unsafe_topology_freq = unsafe_topology_steps / (step + 1)
        avg_voltage_deviation = total_voltage_dev / (step + 1)
        recovery_latency = first_stable_step if first_stable_step is not None else (step + 1)
        explore_ratio = explore_steps / (step + 1)
        action_diversity = len(set(actions_chosen)) / (step + 1)
        
        blocked_action_frequency = episode_violations / (step + 1)
        avg_confidence = np.mean(episode_confidences) if episode_confidences else 1.0
        
        recent_entropies.append(entropy_val)
        if len(recent_entropies) > 50:
            recent_entropies.pop(0)
        rolling_entropy = np.mean(recent_entropies)
        
        logger.info(
            f"Episode {episode}/{num_episodes} | Level: {curriculum_level} | Scenario: {scenario} | "
            f"Steps: {step+1} | Reward: {episode_reward:.2f} | Avg (10): {avg_reward:.2f} | "
            f"Rollbacks: {episode_rollbacks} | Violations: {episode_violations} | Loss: {loss_val:.4f}"
        )
        
        # Append to CSV analytics
        with open(csv_path, "a") as f:
            f.write(
                f"{episode},{curriculum_level},{scenario},{step+1},{episode_reward:.2f},{avg_reward:.2f},"
                f"{loss_val:.4f},{is_success:.2f},{blocked_action_frequency:.2f},{episode_rollbacks},"
                f"{episode_containment_conflicts},{avg_confidence:.4f},{episode_violations},"
                f"{restoration_completion_pct:.1f},{unsafe_topology_freq:.2f},{avg_voltage_deviation:.4f},"
                f"{successful_containment_count},{recovery_latency},{entropy_val:.4f},{explore_ratio:.2f},"
                f"{action_diversity:.2f}\n"
            )
            
        # Publish status telemetry to MQTT
        if mqtt_client:
            status_payload = {
                "timestamp": int(time.time() * 1000),
                "agent_type": agent_type,
                "episode": episode,
                "total_episodes": num_episodes,
                "curriculum_level": curriculum_level,
                "reward": float(episode_reward),
                "avg_reward": float(avg_reward),
                "loss": float(loss_val),
                "epsilon": float(agent.epsilon) if agent_type == "DQN" else 0.0,
                "safety_violations": int(safety_violations),
                "success_rate": float(rolling_success_rate),
                "policy_confidence": float(avg_confidence),
                "rollback_count": int(rollback_count),
                "containment_conflicts": int(containment_conflicts),
                # New diagnostics
                "restoration_completion_pct": float(restoration_completion_pct),
                "unsafe_topology_freq": float(unsafe_topology_freq),
                "avg_voltage_deviation": float(avg_voltage_deviation),
                "containment_count": int(successful_containment_count),
                "recovery_latency": int(recovery_latency),
                "entropy": float(rolling_entropy),
                "explore_ratio": float(explore_ratio),
                "action_diversity": float(action_diversity)
            }
            mqtt_client.publish("grid/rl/status", json.dumps(status_payload))
            
        # Save checkpoints periodically
        if episode % checkpoint_interval == 0:
            checkpoint_file = f"ppo_self_healing_ep_{episode}.pt" if agent_type == "PPO" else f"dqn_self_healing_ep_{episode}.pt"
            agent.save_checkpoint(CHECKPOINTS_DIR, checkpoint_file)
            logger.info(f"Periodic checkpoint saved: {checkpoint_file}")
            
    # Save final checkpoint
    final_checkpoint_name = "ppo_self_healing.pt" if agent_type == "PPO" else "dqn_self_healing.pt"
    agent.save_checkpoint(CHECKPOINTS_DIR, final_checkpoint_name)
    logger.info(f"Training completed. Final checkpoint saved to {os.path.join(CHECKPOINTS_DIR, final_checkpoint_name)}")
    
    if mqtt_client:
        mqtt_client.loop_stop()
        mqtt_client.disconnect()

if __name__ == "__main__":
    agent = "PPO"
    if len(sys.argv) > 1:
        agent = sys.argv[1].upper()
        
    episodes = 1000
    if len(sys.argv) > 2:
        episodes = int(sys.argv[2])
    
    run_training(agent_type=agent, num_episodes=episodes, max_steps=12, checkpoint_interval=50)
