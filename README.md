# PYPY: Smart Grid Cybersecurity Research Platform

PYPY is an event-driven cyber-physical research platform for smart-grid simulation, attack detection, threat assessment, and safety-gated recovery. The default Docker Compose runtime uses the IEEE 39-Bus model.

> Research software: do not connect this stack to live grid infrastructure without an independent security and safety assessment.

## Current Runtime Architecture

The verified runtime flow is:

```text
IEEE-39 Digital Twin
  -> shared full-grid telemetry
  -> LSTM + GNN + ST-GNN + PINN/physics validation (parallel)
  -> calibrated AI fusion + TRUST + threat scoring
  -> PPO/DQN recovery consensus
  -> AC restoration sandbox + safety constraints
  -> AI Orchestrator approval/veto
  -> ordered Digital Twin state verification
  -> Gateway / WebSocket / Dashboard
```

Services communicate through MQTT. The principal topic contract is:

| Topic | Purpose |
|---|---|
| `pypy/grid/telemetry` | Full IEEE-39 telemetry published by the Digital Twin |
| `grid/alerts` | Anomalies published by AI Detection |
| `grid/ai/{lstm,gnn,stgnn,pinn}` | Per-model IEEE-39 decisions |
| `grid/ai/fusion` | Calibrated multi-model fused risk and evidence |
| `grid/physics_validation` / `grid/trust_scores` | Physics and full-grid trust evidence |
| `grid/threat` | Threat assessments published by the Threat Scorer |
| `grid/ai/recovery/{ppo,dqn}` | Separate recovery-policy decisions |
| `grid/ai/recovery_policy` | PPO/DQN consensus, coverage, and sandbox result |
| `grid/l6_recovery` | Recovery state and evidence events |
| `grid/control/proposed` | Safety-validated recovery proposals from Self-Healing |
| `grid/orchestrator/events` | Orchestrator decisions and approval events |
| `grid/control` | Approved commands consumed by the Digital Twin |
| `grid/events` | Grid and control execution events exposed through the Gateway |

`grid/telemetry` remains a legacy/gateway-translated view. Defense services use `pypy/grid/telemetry` as their full-fidelity input.

## Grid Model

The default runtime is the IEEE 39-Bus system:

- 39 buses
- 46 lines
- 10 generators
- 21 loads

## Cyber-Physical Safety

An AI alert does not directly open a breaker. Automated recovery requires correlated threat context, physical outage evidence, PPO/DQN actuator consensus, an AC restoration-sandbox pass, explicit safety constraints, and orchestrator approval without veto. A five-second settling guard matches the simulated breaker cooldown, while topology-aware deduplication prevents repeated commands.

The PPO/DQN checkpoints retain a legacy 72-feature tensor shape. Runtime coverage includes all 39 buses and 46 branches through a deterministic nine-bin compatibility encoder; this is **not** evidence that those checkpoints were retrained on IEEE-39. Runtime output therefore states `compatibility_adapter: true` and `retrained_on_ieee39: false`.

## Quick Start

Prerequisites are Docker with Compose support. Start the complete verified runtime with:

```bash
docker compose up -d --build --remove-orphans
docker compose ps
```

Useful local endpoints:

| Service | Address |
|---|---|
| Dashboard | `http://localhost:3001` |
| Gateway API | `http://localhost:8000` |
| Gateway health | `http://localhost:8000/api/health` |
| MQTT | `localhost:1884` |

Inspect service logs with `docker compose logs --tail=200 SERVICE`.

## Verification

The current integration baseline is **868 passed, 0 failed, 0 errors**. The
`verified-baseline-2026-08-18` tag preserves the preceding 835-test runtime baseline.

```bash
PYTHONDONTWRITEBYTECODE=1 python -m pytest -q
```

The stateful runtime path has also been verified end to end:

```text
Attack -> Detection -> Threat Assessment -> Cyber-Physical Validation
       -> Recovery -> Grid Stabilization
```

Success means more than MQTT publication: the approved command was consumed by the Digital Twin and produced a measurable state change, followed by cleanup to a nominal grid state.

Run the repository verifier after the Compose stack is healthy:

```bash
PYTHONDONTWRITEBYTECODE=1 python scripts/verification/verify_closed_loop.py \
  --output evaluation/end_to_end/verified_report.json
```

The report enforces event order: observed breaker-state telemetry must be newer than orchestrator approval. The coordinated two-line experiment reaches an explicit non-convergent intermediate state; after verified autonomous actuation, controlled experiment reset is separately verified to return all breakers and AC power flow to a finite nominal state.

Pathogen–immune evaluation selects the existing co-evolved checkpoints and writes strict CSV/JSON artefacts:

```bash
PYTHONDONTWRITEBYTECODE=1 python -m core.adversarial.coevolution_evaluator \
  --seeds 42 123 999 --episodes 5 \
  --output-dir evaluation/coevolution/verified
```

This is checkpoint selection and evaluation, not retraining. The committed 15-episode run reports a 13.33% blackout rate, 13.33% detection rate, and zero non-finite output values. These results must not be generalized beyond the recorded experiment.

The machine-readable payload contract for the verified topics is in
[`docs/mqtt-contract.schema.json`](docs/mqtt-contract.schema.json).

## Repository Layout

```text
core/digital_twin/   IEEE-39 simulator and MQTT control endpoint
core/ai_detection/   telemetry anomaly and FDIA detection
core/ai_runtime/     LSTM/GNN/ST-GNN/PINN serving and fusion
core/physics/        IEEE-39 physics validation and dynamic TRUST scoring
core/adversarial/    pathogen–immune co-evolution and evaluation
core/threat_engine/  alert correlation and threat scoring
core/self_healing/   safety-gated recovery planning
core/orchestrator/   recovery proposal approval gate
core/gateway/        REST, WebSocket, and MQTT bridge
dashboard/           React/Vite operator interface
tests/               unit, integration, cyber, and physics regression tests
```

## Security

The local stack uses development defaults, unencrypted MQTT, and simulated controls. Do not commit real credentials or `.env` files. Review deployment-specific authentication, encryption, secret management, and hardware interlocks before any environment beyond isolated research use.

## License

This project is licensed under the [MIT License](LICENSE).
