# PYPY Runtime Architecture

This document describes the verified default Docker Compose runtime. PYPY is an event-driven research system: services exchange state and commands through the MQTT broker rather than invoking one another directly.

## Verified Runtime Flow

```text
Digital Twin --pypy/grid/telemetry--> AI Detection
AI Detection --grid/alerts---------> Threat Scorer
Threat Scorer --grid/threat--------> Self-Healing
Self-Healing --grid/control/proposed--> AI Orchestrator
AI Orchestrator --grid/control-----> Digital Twin
Digital Twin --grid/events---------> Gateway -> WebSocket -> Dashboard
```

The Digital Twin is the authoritative physics runtime. Its default model is IEEE 39-Bus with 39 buses, 46 lines, 10 generators, and 21 loads.

## Telemetry Views

- `pypy/grid/telemetry` is the full IEEE-39 telemetry stream and the authoritative input for the defense chain.
- `grid/telemetry` is a legacy/gateway-translated view retained for compatibility and presentation consumers. It is not the primary IEEE-39 defense input.

## Runtime Services

### Digital Twin

The Digital Twin solves the IEEE-39 grid state, publishes `pypy/grid/telemetry` and relevant `grid/events`, and consumes approved commands from `grid/control`. A published command is not considered successful until the resulting Digital Twin state change is observed.

### AI Detection

- Input: `pypy/grid/telemetry` (plus attack/control context used for calibration and reset handling)
- Output: `grid/alerts`

AI Detection establishes a nominal baseline and publishes anomaly evidence. Its output is context, not direct actuator authority.

### Threat Scorer

- Input: `grid/alerts`
- Output: `grid/threat`

The scorer correlates alerts into a threat assessment consumed by downstream safety logic.

### Self-Healing

- Input: cyber-physical context including `pypy/grid/telemetry`, `grid/events`, `grid/control`, and `grid/threat`
- Output: `grid/l6_recovery` and `grid/control/proposed`

Self-Healing correlates threat context with actual physical outage/isolation evidence and grid stability. Candidate restoration actions pass topology simulation and safety constraints before they can become proposals.

### AI Orchestrator

- Input: proposed recovery/control on `grid/control/proposed` plus the supporting telemetry, threat, and recovery context
- Output: approved commands on `grid/control` and decisions on `grid/orchestrator/events`

The orchestrator is the final software approval gate. It rejects proposals that do not carry the required L6 recovery provenance or do not satisfy current safety conditions.

### Gateway and Dashboard

The Gateway bridges MQTT events and telemetry to REST/WebSocket clients. The Dashboard consumes that live view; it is not in the actuator approval path.

### Supporting Infrastructure

- Mosquitto provides the MQTT event bus.
- PostgreSQL and Redis support the Gateway and task services.
- Celery worker and beat provide background task execution and scheduling.

## Safety Approval Gate

The supported autonomous path is deliberately not `AI alert -> breaker operation`.

```text
Threat context
  + physical fault/outage/isolation evidence
  + acceptable voltage/current/stability state
  + restoration sandbox result
  + topology and safety constraints
  -> recovery proposal
  -> orchestrator approval
  -> executable grid/control command
```

This separation preserves cyber-physical gating: detection informs recovery planning, while observed physical state and validation determine whether an action may proceed.

## Main MQTT Contract

| Publisher | Topic | Principal consumers |
|---|---|---|
| Digital Twin | `pypy/grid/telemetry` | AI Detection, Self-Healing, AI Orchestrator, Gateway |
| AI Detection | `grid/alerts` | Threat Scorer, Gateway |
| Threat Scorer | `grid/threat` | Self-Healing, AI Orchestrator, Gateway |
| Self-Healing | `grid/l6_recovery` | AI Orchestrator, Gateway |
| Self-Healing | `grid/control/proposed` | AI Orchestrator |
| AI Orchestrator | `grid/orchestrator/events` | Gateway/Dashboard and audit consumers |
| AI Orchestrator | `grid/control` | Digital Twin, Gateway, defense context consumers |
| Digital Twin | `grid/events` | Self-Healing, Gateway/Dashboard |

Additional research and HIL compatibility topics exist, but they are not required to describe the verified default defense chain.

## Default Compose Boundary

The verified default stack contains PostgreSQL, Redis, MQTT, Gateway, Dashboard, Digital Twin, Celery worker, Celery beat, AI Detection, Threat Scorer, Self-Healing, and AI Orchestrator. Research modules that are not dependencies of this chain remain outside the default runtime.

## Verification Boundary

The current regression baseline is 835 passed, 0 failed, and 0 errors. Runtime verification additionally demonstrates:

```text
Attack -> Detection -> Threat Assessment -> Cyber-Physical Validation
       -> Recovery -> Grid Stabilization
```

PYPY remains research software and this verified baseline is not a production-readiness claim.
