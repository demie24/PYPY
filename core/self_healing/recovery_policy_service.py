"""IEEE-39 runtime adapter for the trained PPO and DQN recovery policies."""

from __future__ import annotations

import json
import logging
import math
import os
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch

from core.ai_runtime.readiness import ModelReadiness
from core.mqtt_compat import create_client
from core.self_healing.action_registry import ActionRegistry
from core.self_healing.restoration_validator import RestorationValidator
from core.self_healing.rl.dqn_agent import DQNAgent
from core.self_healing.rl.ppo_agent import PPOAgent


LOGGER = logging.getLogger("self_healing.recovery_policy")
MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
TELEMETRY_TOPIC = os.getenv("TELEMETRY_TOPIC", "pypy/grid/telemetry")


class IEEE39RecoveryEncoder:
    """Pool every IEEE-39 bus/branch into the legacy policy's 72 inputs.

    The neural checkpoints retain their trained tensor dimensions. Nine
    deterministic topology bins replace the old nine literal devices, so no
    IEEE-39 bus or branch is silently omitted. This is a runtime compatibility
    adapter, not evidence that the legacy policies were retrained on IEEE-39.
    """

    state_dim = 72

    @staticmethod
    def _finite(value: Any, default: float) -> float:
        parsed = float(value)
        return parsed if math.isfinite(parsed) else default

    @staticmethod
    def _pool(values: list[float], bins: int = 9, default: float = 0.0) -> np.ndarray:
        chunks = np.array_split(np.asarray(values, dtype=np.float32), bins)
        return np.asarray([float(np.mean(chunk)) if len(chunk) else default for chunk in chunks], dtype=np.float32)

    def encode(self, telemetry: dict[str, Any], threat=None, trust=None, fusion=None, physics=None) -> np.ndarray:
        state = telemetry.get("state", {})
        buses = state.get("buses", {})
        lines = state.get("lines", {})
        breakers = state.get("breakers", {})
        if len(buses) != 39 or len(lines) != 46 or len(breakers) != 46:
            raise ValueError("recovery policy requires IEEE-39 telemetry with 39 buses and 46 branches")
        bus_ids = [f"Bus_{index}" for index in range(1, 40)]
        branch_ids = [f"L_line_{index}" for index in range(35)] + [f"L_trafo_{index}" for index in range(11)]
        vector = np.zeros(72, dtype=np.float32)
        vector[0:9] = self._pool([self._finite(buses[key]["voltage_pu"], 0.0) for key in bus_ids], default=1.0)
        vector[9:18] = self._pool([self._finite(buses[key]["angle_rad"], 0.0) for key in bus_ids])
        vector[18:27] = self._pool([self._finite(lines[key].get("P_mw", 0.0), 0.0) / 100.0 for key in branch_ids])
        vector[27:36] = self._pool([self._finite(lines[key].get("Q_mvar", 0.0), 0.0) / 100.0 for key in branch_ids])
        vector[36:45] = self._pool([1.0 if breakers[key] == "CLOSED" else 0.0 for key in branch_ids], default=1.0)
        bus_trust = (trust or {}).get("bus_trust", {})
        line_trust = (trust or {}).get("line_trust", {})
        vector[45:54] = self._pool([float(bus_trust.get(key, 100.0)) / 100.0 for key in bus_ids], default=1.0)
        vector[54:63] = self._pool([float(line_trust.get(key, 100.0)) / 100.0 for key in branch_ids], default=1.0)
        vector[63] = float((physics or {}).get("physics_anomaly_score", 0.0)) / 100.0
        vector[64] = 1.0 - float((fusion or {}).get("fused_risk", 0.0))
        vector[65] = float((threat or {}).get("cascade_probability", 0.0))
        vector[66] = float(sum(status == "OPEN" for status in breakers.values())) / 46.0
        vector[67] = 0.0 if (physics or {}).get("degraded_observability", False) else 1.0
        vector[68] = float((fusion or {}).get("fused_risk", 0.0))
        vector[69] = {"LOW": 0.0, "MEDIUM": 0.33, "HIGH": 0.66, "CRITICAL": 1.0}.get(str((threat or {}).get("severity", "LOW")), 0.0)
        solver_failed = (telemetry.get("solver_status") or {}).get("converged") is False
        vector[70] = 1.0 if solver_failed or any(self._finite(buses[key]["voltage_pu"], 0.0) < 0.20 for key in bus_ids) else 0.0
        vector[71] = 0.0
        if not np.isfinite(vector).all():
            raise ValueError("non-finite IEEE-39 recovery state")
        return vector


class RecoveryPolicyRuntime:
    def __init__(self, ppo_path="/app/checkpoints/ppo_self_healing.pt", dqn_path="/app/checkpoints/dqn_self_healing.pt"):
        self.encoder = IEEE39RecoveryEncoder()
        self.registry = ActionRegistry()
        self.validator = RestorationValidator()
        self.ppo = PPOAgent(state_dim=72, action_dim=10)
        self.dqn = DQNAgent(state_dim=72, action_dim=10)
        if not self.ppo.load_checkpoint(ppo_path) or not self.dqn.load_checkpoint(dqn_path):
            raise RuntimeError("PPO/DQN recovery checkpoints failed to load")

    def infer(self, telemetry, threat=None, trust=None, fusion=None, physics=None):
        vector = self.encoder.encode(telemetry, threat, trust, fusion, physics)
        open_branches = [key for key, value in telemetry["state"]["breakers"].items() if value == "OPEN"]
        allowed_ids = [0, 2, 8, 9] if open_branches else [0]
        state_t = torch.tensor(vector, dtype=torch.float32)
        with torch.no_grad():
            ppo_logits = self.ppo.actor(state_t).squeeze(0)
            dqn_values = self.dqn.q_net(state_t).squeeze(0)
        ppo_id = max(allowed_ids, key=lambda index: float(ppo_logits[index]))
        dqn_id = max(allowed_ids, key=lambda index: float(dqn_values[index]))
        target = self._select_target(telemetry, open_branches) if open_branches else "SYSTEM"
        outputs = {
            "ppo": self._decision("ppo", ppo_id, ppo_logits, target),
            "dqn": self._decision("dqn", dqn_id, dqn_values, target),
        }
        # RECONNECT_LINE, ENABLE_RESTORATION, and REROUTE_FLOW all map to the
        # same physical CLOSE intent. Consensus is over actuator intent/target,
        # not the models' differently named action categories.
        consensus = ppo_id in (2, 8, 9) and dqn_id in (2, 8, 9) and target != "SYSTEM"
        sandbox = None
        if consensus:
            sandbox = self.validator.validate_action(telemetry, "RECONNECT_LINE", target)
            consensus = sandbox["is_safe"] is True
        return {
            "timestamp": int(time.time() * 1000),
            "component": "recovery_policy",
            "grid_name": "ieee39",
            "coverage": {"buses": 39, "branches": 46, "pooling_bins": 9},
            "compatibility_adapter": True,
            "retrained_on_ieee39": False,
            "model_decisions": outputs,
            "consensus": consensus,
            "target": target,
            "sandbox": sandbox,
        }

    def _decision(self, name, action_id, scores, target):
        finite_scores = [float(value) for value in scores]
        return {
            "model": name,
            "action_id": action_id,
            "action": self.registry.get_action(action_id)["name"],
            "target": target,
            "score": finite_scores[action_id],
        }

    @staticmethod
    def _select_target(telemetry, open_branches):
        lines = telemetry["state"]["lines"]
        return min(open_branches, key=lambda key: float(lines.get(key, {}).get("capacity_pct", 0.0)))


class MQTTRecoveryPolicyService:
    def __init__(self):
        self.runtime = RecoveryPolicyRuntime()
        self.readiness = ModelReadiness("recovery_policy", model_loaded=True, checkpoint="ppo+dqn-ieee39-adapter")
        self.cache = {"threat": None, "trust": None, "fusion": None, "physics": None}
        self.last_proposal_signature = None
        self.observed_topology = None
        self.topology_changed_at = 0.0
        self.client = create_client("pypy_recovery_policy")
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

    def on_connect(self, client, userdata, flags, reason_code, properties=None):
        if reason_code == 0:
            for topic in (TELEMETRY_TOPIC, "grid/threat", "grid/trust_scores", "grid/ai/fusion", "grid/physics_validation", "grid/control"):
                client.subscribe(topic)

    def on_message(self, client, userdata, message):
        try:
            payload = json.loads(message.payload.decode("utf-8"))
            if message.topic == "grid/control":
                if payload.get("command") == "RESET_ALARMS":
                    self.last_proposal_signature = None
                    self.observed_topology = None
                    self.topology_changed_at = 0.0
                return
            if message.topic != TELEMETRY_TOPIC:
                key = {"grid/threat": "threat", "grid/trust_scores": "trust", "grid/ai/fusion": "fusion", "grid/physics_validation": "physics"}[message.topic]
                self.cache[key] = payload
                return
            self.readiness.record_telemetry()
            decision = self.runtime.infer(payload, **self.cache)
            topology = tuple(sorted(payload["state"]["breakers"].items()))
            if all(state == "CLOSED" for _, state in topology):
                self.last_proposal_signature = None
            if topology != self.observed_topology:
                self.observed_topology = topology
                self.topology_changed_at = time.monotonic()
            topology_stable_seconds = time.monotonic() - self.topology_changed_at
            decision["topology_stable_seconds"] = topology_stable_seconds
            # Digital-twin breaker motor operators enforce a five-second
            # direction-change cooldown (main.py). Wait beyond that boundary
            # before proposing a close so approval can actually be actuated.
            decision["actuator_guard_satisfied"] = topology_stable_seconds >= 5.2
            client.publish("grid/ai/recovery_policy", json.dumps(decision, allow_nan=False))
            for model in ("ppo", "dqn"):
                client.publish(f"grid/ai/recovery/{model}", json.dumps(decision["model_decisions"][model], allow_nan=False))
            signature = (decision["target"], topology)
            if decision["consensus"] and decision["actuator_guard_satisfied"] and signature != self.last_proposal_signature:
                client.publish("grid/control/proposed", json.dumps({
                    "command": "CLOSE", "target": decision["target"],
                    "source": "AI_RL_PPO_DQN_CONSENSUS", "sandbox": decision["sandbox"],
                }, allow_nan=False))
                self.last_proposal_signature = signature
            self.readiness.record_inference()
        except Exception as exc:
            self.readiness.record_error(exc)
            LOGGER.exception("Recovery policy inference failed")
        finally:
            status = self.readiness.snapshot(stale_after=15.0)
            path = Path("/tmp/pypy_recovery_policy_heartbeat.json")
            path.write_text(json.dumps(status), encoding="utf-8")
            client.publish("grid/ai/status/recovery_policy", json.dumps(status), retain=True)

    def run(self):
        self.client.connect(MQTT_BROKER, MQTT_PORT, 60)
        self.client.loop_forever()


def main():
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(asctime)s [%(levelname)s] %(message)s")
    MQTTRecoveryPolicyService().run()


if __name__ == "__main__":
    main()
