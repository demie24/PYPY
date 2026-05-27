import os
import json
import time
import logging
import paho.mqtt.client as mqtt
from relay import ProtectiveRelay
from flisr import FLISREngine

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("self_healing.main")

MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))

# Instantiate modules
relay = ProtectiveRelay()
flisr = FLISREngine()
from recovery_state_machine import RecoveryStateMachine
l6_fsm = RecoveryStateMachine()

from recovery_scoring_engine import RecoveryScoringEngine
from cascading_containment_engine import CascadingContainmentEngine
from adaptive_recovery_memory import AdaptiveRecoveryMemory
from degraded_operation_manager import DegradedOperationManager

l6_scorer = RecoveryScoringEngine()
l6_containment = CascadingContainmentEngine(l6_fsm.topo_engine)
l6_memory = AdaptiveRecoveryMemory()
l6_degraded = DegradedOperationManager()


# Phase 5B: Rate limiting state
# Only run the full relay+FLISR evaluation every N telemetry frames.
# This prevents excessive cycling under 1Hz telemetry + physics transients.
_telemetry_frame_count = 0
_relay_eval_every_n_frames = 2  # evaluate every 2nd frame

# Post-trip settle counter: number of frames to skip FLISR after a relay trip
_post_trip_settle_remaining = 0
_post_trip_settle_frames = 3

# Alert deduplication cooldown: suppress repeated BREAKER_TRIP alerts for the
# same node within this window. Prevents flooding during coordinated_cascade
# where FLISR restoration transients keep relay counters non-zero for several
# cycles after the breaker has already been isolated.
_alert_cooldown: dict = {}   # node -> last published timestamp (float)
_alert_cooldown_seconds = 20.0

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info("Self-Healing Subsystem connected to MQTT!")
        client.subscribe("grid/telemetry")
        client.subscribe("grid/events")
        client.subscribe("grid/control")
        client.subscribe("grid/config")
    else:
        logger.error(f"MQTT Connection failed with code {rc}")

def on_message(client, userdata, msg):
    global _telemetry_frame_count, _post_trip_settle_remaining, _alert_cooldown
    try:
        topic = msg.topic
        payload = json.loads(msg.payload.decode("utf-8"))

        if topic == "grid/telemetry":
            _telemetry_frame_count += 1

            # Phase 5B: Rate limiting - skip odd frames for relay/FLISR evaluation
            # to avoid rapid cycling on back-to-back telemetry messages.
            if _telemetry_frame_count % _relay_eval_every_n_frames != 0:
                return

            # Phase 5B: Post-trip settle - skip FLISR for N frames after any relay trip
            # to allow physics to converge before making restoration decisions.
            skip_flisr = _post_trip_settle_remaining > 0
            if _post_trip_settle_remaining > 0:
                _post_trip_settle_remaining -= 1

            # 1. Evaluate protective relay tripping rules (ANSI 50/51, 27)
            relay_commands = relay.evaluate_telemetry(payload)
            now = time.time()
            for cmd in relay_commands:
                node = cmd["target"]

                # Send breaker trip command to grid/control
                control_payload = {
                    "command": cmd["command"],
                    "target": node,
                    "source": "RELAY"
                }
                client.publish("grid/control", json.dumps(control_payload))

                # Always publish to grid/events (operator log — not the flooding source)
                client.publish("grid/events", json.dumps(cmd["event_log"]))

                # --- Alert deduplication gate ---
                # Suppress grid/alerts for this node if:
                #   (a) same node was published within the cooldown window, OR
                #   (b) FLISR has already reached RESTORED state for this fault
                #       (restoration complete — further trip alerts are post-transient noise)
                last_published = _alert_cooldown.get(node, 0.0)
                flisr_already_restored = (
                    flisr.state in ("RESTORED", "RESTORATION")
                    and node in flisr.isolated_faults
                )
                if (now - last_published) < _alert_cooldown_seconds or flisr_already_restored:
                    logger.debug(
                        f"Suppressed duplicate BREAKER_TRIP alert for {node} "
                        f"(cooldown={now - last_published:.1f}s, flisr={flisr.state})"
                    )
                else:
                    _alert_cooldown[node] = now
                    alarm_payload = {
                        "timestamp": int(now * 1000),
                        "type": "BREAKER_TRIP",
                        "severity": "CRITICAL",
                        "suspect_node": node,
                        "msg": f"Breaker {node} tripped by Relay Protection (threshold breach)."
                     }
                    client.publish("grid/alerts", json.dumps(alarm_payload))

                # Phase 5B: Set settle counter after relay trip so FLISR waits
                _post_trip_settle_remaining = _post_trip_settle_frames
                skip_flisr = True  # Skip FLISR this cycle - just issued trip command

            # Track FLISR state before executing healing cycle
            prev_state = flisr.state
            prev_isolated = list(flisr.isolated_faults)
            prev_reconfigured = list(flisr.reconfigured_breakers)

            # 2. Run FLISR Self-Healing calculation loop (skip if in post-trip settle)
            if not skip_flisr:
                flisr_commands = flisr.execute_healing_cycle(payload)
                for cmd in flisr_commands:
                    # Send reconfiguration action (e.g. closing tie-breaker) to proposed topic
                    control_payload = {
                        "command": cmd["command"],
                        "target": cmd["target"],
                        "source": "FLISR"
                    }
                    client.publish("grid/control/proposed", json.dumps(control_payload))
                    
                    # Publish restoration event log
                    client.publish("grid/events", json.dumps(cmd["event_log"]))
            else:
                logger.debug(f"FLISR execution skipped (post-trip settle: {_post_trip_settle_remaining} frames remaining)")

            # Broadcast FLISR state if any changes occurred
            if (flisr.state != prev_state or 
                flisr.isolated_faults != prev_isolated or 
                flisr.reconfigured_breakers != prev_reconfigured):
                config_update = {
                    "flisr_state": flisr.state,
                    "flisr_isolated_faults": flisr.isolated_faults,
                    "flisr_reconfigured_breakers": flisr.reconfigured_breakers,
                    "flisr_tripped_by_relay": flisr.tripped_by_relay
                }
                client.publish("grid/config", json.dumps(config_update))

            # Run Layer 6 Autonomous Restoration Core state machine
            fsm_state_before = l6_fsm.state
            executed_before = list(l6_fsm.executed_sequence)

            l6_commands = l6_fsm.update(payload, client, faulted_breakers=flisr.tripped_by_relay)
            for cmd in l6_commands:
                logger.info(f"Layer 6 Recovery proposed action: {cmd['command']} on {cmd['target']}")
                client.publish("grid/control/proposed", json.dumps(cmd))

            # Adaptive Recovery Memory transitions
            if fsm_state_before == "VERIFY" and l6_fsm.state == "NORMAL" and executed_before:
                l6_memory.record_success(flisr.tripped_by_relay, executed_before)
            elif fsm_state_before == "ROLLBACK" and l6_fsm.state == "NORMAL" and executed_before:
                l6_memory.record_failure(flisr.tripped_by_relay, executed_before)

            # Cascading Containment Analysis
            containment_data = l6_containment.analyze_cascading_risk(payload, payload.get("attack_status"))
            containment_payload = {
                "timestamp": int(time.time() * 1000),
                "propagation_zones": containment_data.get("propagation_zones", []),
                "instability_spread_risk": containment_data.get("instability_spread_risk", 0.0),
                "isolation_boundary": containment_data.get("isolation_boundary", [])
            }
            client.publish("grid/l6_containment", json.dumps(containment_payload))

            # Degraded Operation Analysis & Load Shedding
            degraded_data = l6_degraded.evaluate_grid_survival(payload)
            degraded_payload = {
                "timestamp": int(time.time() * 1000),
                "active_degraded_mode": degraded_data.get("active_degraded_mode", False),
                "critical_buses_secured": degraded_data.get("critical_buses_secured", []),
                "load_shedding_active": degraded_data.get("load_shedding_active", False),
                "load_shed_summary": degraded_data.get("load_shed_summary", {}),
                "survival_commands": degraded_data.get("survival_commands", [])
            }
            client.publish("grid/l6_degraded_mode", json.dumps(degraded_payload))

            # Execute load shedding commands if any
            for scmd in degraded_data.get("survival_commands", []):
                logger.info(f"Issuing load shedding command: {scmd['command']} on {scmd['target']} ({scmd['percentage']}%)")
                client.publish("grid/control", json.dumps(scmd))

            # Plan Scoring
            state_data = payload.get("state", {})
            buses = state_data.get("buses", {})
            lines = state_data.get("lines", {})
            
            # Formulate simulated sandbox results for the scorer
            sandbox_results = {
                "predicted_voltages": [buses.get(f"Bus_{i+1}", {}).get("voltage_pu", 1.0) for i in range(9)],
                "predicted_loadings": {lid: l_data.get("capacity_pct", 0.0)/100.0 for lid, l_data in lines.items()},
                "cascade_risk": 0.0
            }
            
            if l6_fsm.planned_sequence:
                # Dry run using validator sandbox to evaluate sequence impact
                step = l6_fsm.planned_sequence[0]
                val_res = l6_fsm.validator.validate_action(payload, step["command"], step["target"])
                sandbox_results = {
                    "predicted_voltages": val_res.get("predicted_voltages", []),
                    "predicted_loadings": val_res.get("predicted_loadings", {}),
                    "cascade_risk": val_res.get("cascade_risk", 0.0)
                }

            # Extract instability risk probability from threat or forecast if available
            pred_risk = 0.0
            ai_pred = payload.get("ai_prediction", {})
            if isinstance(ai_pred, dict):
                pred_risk = 1.0 if ai_pred.get("instability_risk") == "CRITICAL" else 0.5 if ai_pred.get("instability_risk") in ["HIGH", "MEDIUM"] else 0.0

            score_data = l6_scorer.score_plan(
                payload,
                l6_fsm.planned_sequence,
                sandbox_results,
                predicted_instability_prob=pred_risk,
                historical_success_rate=l6_memory.get_sequence_confidence(l6_fsm.planned_sequence)
            )

            adaptive_payload = {
                "timestamp": int(time.time() * 1000),
                "optimization_score": score_data.get("optimization_score", 100.0),
                "scores": score_data,
                "historical_confidence": l6_memory.get_sequence_confidence(l6_fsm.planned_sequence),
                "total_successful_runs": sum(len(seqs) for seqs in l6_memory.successful_sequences.values()),
                "total_failed_runs": sum(len(seqs) for seqs in l6_memory.failed_attempts.values())
            }
            client.publish("grid/l6_adaptive_recovery", json.dumps(adaptive_payload))

        elif topic == "grid/events":
            prev_state = flisr.state
            # Pass events into FLISR to track breaker trips and start healing state machine
            flisr.process_event(payload)
            if flisr.state != prev_state:
                config_update = {
                    "flisr_state": flisr.state,
                    "flisr_isolated_faults": flisr.isolated_faults,
                    "flisr_reconfigured_breakers": flisr.reconfigured_breakers,
                    "flisr_tripped_by_relay": flisr.tripped_by_relay
                }
                client.publish("grid/config", json.dumps(config_update))

        elif topic == "grid/control":
            # Handle operator reset actions
            cmd = payload.get("command")
            if cmd == "RESET_ALARMS":
                logger.info("Operator triggered system alarm reset.")
                relay.reset_trips()
                flisr.reset()
                l6_fsm.reset()
                _alert_cooldown.clear()  # Allow fresh alerts for next test run
                
                # Also command simulator to restore normally open L7_8 configuration
                restore_payload = {
                    "command": "OPEN",
                    "target": "L7_8"
                }
                client.publish("grid/control", json.dumps(restore_payload))
            elif cmd == "RESET_L6_RECOVERY":
                logger.info("Operator triggered Layer 6 recovery reset.")
                l6_fsm.reset()
            elif cmd == "TRIGGER_L6_RECOVERY":
                logger.info("Operator manually triggered Layer 6 recovery sequence.")
                l6_fsm.transition_to("ISOLATE")
            elif cmd == "ROLLBACK_L6_RECOVERY":
                logger.info("Operator manually triggered Layer 6 rollback.")
                l6_fsm.transition_to("ROLLBACK")

                # Publish reset FLISR state to grid/config
                config_update = {
                    "flisr_state": flisr.state,
                    "flisr_isolated_faults": flisr.isolated_faults,
                    "flisr_reconfigured_breakers": flisr.reconfigured_breakers,
                    "flisr_tripped_by_relay": flisr.tripped_by_relay
                }
                client.publish("grid/config", json.dumps(config_update))

        elif topic == "grid/config":
            # Update auto/manual configuration for self-healing
            if "flisr_auto" in payload:
                flisr.set_mode(payload["flisr_auto"])
                # Broadcast back state status to sync frontends
                config_update = {
                    "flisr_state": flisr.state,
                    "flisr_isolated_faults": flisr.isolated_faults,
                    "flisr_reconfigured_breakers": flisr.reconfigured_breakers,
                    "flisr_tripped_by_relay": flisr.tripped_by_relay,
                    "flisr_auto": flisr.auto_mode
                }
                client.publish("grid/config", json.dumps(config_update))

    except Exception as e:
        logger.error(f"Error handling message on {msg.topic}: {e}")

if __name__ == "__main__":
    client = mqtt.Client(client_id="self_healing_subsystem")
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
        logger.info("Starting Self-Healing / Protection Relay daemon...")
        client.loop_forever()
    except KeyboardInterrupt:
        logger.info("Daemon interrupted. Shutting down...")
    except Exception as e:
        logger.error(f"MQTT Loop Error: {e}")
        os._exit(1)
