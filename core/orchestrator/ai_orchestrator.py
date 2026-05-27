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

try:
    import rl_metrics
except ImportError:
    pass

from decision_engine import OrchestrationDecisionEngine
from action_recommender import ActionRecommender

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("orchestrator.main")

MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))

class AIOrchestrator:
    def __init__(self):
        self.decision_engine = OrchestrationDecisionEngine()
        self.action_recommender = ActionRecommender()
        self.defense_mode = "ADVISORY"
        
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
            "l6_degraded_mode": None
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
        elif topic == "grid/ai_forecast_multi_bus":
            self.state_cache["multi_bus_forecast"] = payload
        elif topic == "grid/ai_threat_forecast":
            self.state_cache["threat_aware_forecast"] = payload
        elif topic == "grid/physics_validation":
            self.state_cache["physics_validation"] = payload
        elif topic == "grid/trust_scores":
            self.state_cache["trust_scores"] = payload
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

    def evaluate_proposed_command(self, cmd: str, target: str, source: str) -> Tuple[bool, str]:
        """
        Intercepts proposed commands and evaluates them using safety constraints, trust metrics,
        and simultaneous action protections.
        """
        if self.override_state.get("emergency_stop_active", False):
            return False, "Emergency stop active."
            
        if self.override_state.get("pause_autonomous", False):
            return False, "Autonomous execution paused by operator override."

        # Evaluate current grid decision report
        report = self.decision_engine.evaluate(self.state_cache)
        stability = report.get("stability_score", 100.0)
        global_state = report.get("global_state", "NORMAL")

        is_restoration = cmd == "CLOSED" or source in ["FLISR", "AI_RL_PPO_CONTROL"] or cmd in ["RECONNECT_LINE", "REROUTE_FLOW"]

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
        is_breaker_cmd = cmd in ["OPEN", "CLOSED"]
        if is_breaker_cmd:
            now = time.time()
            if now - self.last_breaker_operation_time < 3.0:
                if is_restoration:
                    return False, "Unsafe simultaneous recovery: recovery command rejected due to 3-second guard delay."
            self.last_breaker_operation_time = now

        return True, "Passed all AI orchestrator coordination checks."

    def run_cycle(self, client):
        """
        Runs a decision-making and action recommendations cycle.
        """
        if not self.state_cache["telemetry"]:
            return
            
        try:
            # 1. Run Decision Engine
            report = self.decision_engine.evaluate(self.state_cache)
            
            # 2. Run Action Recommender
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
                f"Stability: {report['stability_score']}% | Mode: {escalation_mode} | Recovery: {coordinated_recovery_state}"
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
            "l6_degraded_mode": None
        }
        self.decision_engine = OrchestrationDecisionEngine()
        self.action_recommender = ActionRecommender()
        self.defense_mode = "ADVISORY"
        self.last_breaker_operation_time = 0.0
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
            elif cmd == "TOGGLE_AUTO_DEFENSE":
                enabled = payload.get("enabled", False)
                orchestrator.defense_mode = "EMERGENCY_DEFENSE" if enabled else "ADVISORY"
                logger.info(f"Orchestrator defense mode updated to: {orchestrator.defense_mode}")
            elif cmd == "SET_DEFENSE_MODE":
                orchestrator.defense_mode = payload.get("mode", "ADVISORY")
                logger.info(f"Orchestrator defense mode updated to: {orchestrator.defense_mode}")
        else:
            orchestrator.update_state(topic, payload)
            
            # Trigger cycle execution upon receiving telemetry tick
            if topic == "grid/telemetry":
                orchestrator.run_cycle(client)
                
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
