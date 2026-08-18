# PYPY: Smart Grid Cybersecurity Research Platform

PYPY is an event-driven cyber-physical research platform for smart-grid simulation, attack detection, threat assessment, and safety-gated recovery. The default Docker Compose runtime uses the IEEE 39-Bus model.

> Research software: do not connect this stack to live grid infrastructure without an independent security and safety assessment.

## Current Runtime Architecture

The verified runtime flow is:

```text
Digital Twin
  -> AI Detection
  -> Threat Scorer
  -> Self-Healing
  -> AI Orchestrator
  -> Digital Twin
  -> Gateway / WebSocket / Dashboard
```

Services communicate through MQTT. The principal topic contract is:

| Topic | Purpose |
|---|---|
| `pypy/grid/telemetry` | Full IEEE-39 telemetry published by the Digital Twin |
| `grid/alerts` | Anomalies published by AI Detection |
| `grid/threat` | Threat assessments published by the Threat Scorer |
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

An AI alert does not directly open a breaker. Automated recovery requires correlated threat context and physical outage evidence, acceptable stability measurements, restoration sandbox validation, and explicit safety constraints. Self-Healing publishes a proposed action only after those checks; the AI Orchestrator is the approval gate that publishes an executable `grid/control` command.

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

The verified baseline is **835 passed, 0 failed, 0 errors**:

```bash
PYTHONDONTWRITEBYTECODE=1 python -m pytest -q
```

The stateful runtime path has also been verified end to end:

```text
Attack -> Detection -> Threat Assessment -> Cyber-Physical Validation
       -> Recovery -> Grid Stabilization
```

Success means more than MQTT publication: the approved command was consumed by the Digital Twin and produced a measurable state change, followed by cleanup to a nominal grid state.

## Repository Layout

```text
core/digital_twin/   IEEE-39 simulator and MQTT control endpoint
core/ai_detection/   telemetry anomaly and FDIA detection
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
