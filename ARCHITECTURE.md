# PYPY Runtime Architecture

This document describes the verified default Docker Compose runtime. PYPY is an event-driven research system: services exchange state and commands through the MQTT broker rather than invoking one another directly.

## Verified Runtime Flow

```text
IEEE-39 Digital Twin --pypy/grid/telemetry--> shared feature adapters
  +--> LSTM temporal detector ---------+
  +--> GNN topology detector ----------+--> AI Fusion --+
  +--> ST-GNN propagation detector ----+              |
  +--> PINN + physics validation ------+              +--> TRUST / Threat Scorer
                                                        --> PPO + DQN proposals
                                                        --> AC restoration sandbox
                                                        --> Orchestrator approval/veto
                                                        --> grid/control
                                                        --> ordered Digital Twin state proof
                                                        --> Gateway / Dashboard / JSON reports
```

The Digital Twin is the authoritative physics runtime. Its default model is IEEE 39-Bus with 39 buses, 46 lines, 10 generators, and 21 loads.

## Telemetry Views

- `pypy/grid/telemetry` is the full IEEE-39 telemetry stream and the authoritative input for the defense chain.
- `grid/telemetry` is a legacy/gateway-translated view retained for compatibility and presentation consumers. It is not the primary IEEE-39 defense input.

## Runtime Services

### Digital Twin

The Digital Twin solves the IEEE-39 grid state, publishes `pypy/grid/telemetry` and relevant `grid/events`, and consumes approved commands from `grid/control`. A published command is not considered successful until the resulting Digital Twin state change is observed.

### AI Detection and parallel model services

- Input: `pypy/grid/telemetry` (plus attack/control context used for calibration and reset handling)
- Output: `grid/alerts`

The NumPy detector uses all 39 bus voltages, worst-bus reconstruction error for targeted FDIA, and an inference heartbeat. LSTM, GNN, ST-GNN, and PINN services independently consume the same full IEEE-39 frame and publish model evidence plus readiness status. Non-finite solver frames are represented explicitly and never emitted as NaN detection loss. Detection output is context, not direct actuator authority.

### Fusion, Physics, and TRUST

`ai_fusion` combines fresh LSTM, GNN, ST-GNN, and PINN outputs on explicit subscriptions. `physics_validation` evaluates IEEE-39 KCL/KVL/solver evidence and publishes dynamic trust for 39 buses and 46 branches. Threat scoring consumes alert, fusion, physics, and trust evidence; status and decisions are exposed to the Gateway and Dashboard.

### Threat Scorer

- Input: `grid/alerts`
- Output: `grid/threat`

The scorer correlates alerts into a threat assessment consumed by downstream safety logic.

### Recovery Policy and Self-Healing

- Input: cyber-physical context including `pypy/grid/telemetry`, `grid/events`, `grid/control`, and `grid/threat`
- Output: `grid/l6_recovery` and `grid/control/proposed`

The `recovery_policy` service loads both PPO and DQN checkpoints, encodes all 39 buses/46 branches into their retained 72-dimensional input, and publishes each decision. Only actuator-intent consensus proceeds to the IEEE-39 AC restoration sandbox. Safe proposals wait for the five-second breaker cooldown and are deduplicated by target and topology. Self-Healing/FLISR remains an independent recovery layer.

### AI Orchestrator

- Input: proposed recovery/control on `grid/control/proposed` plus the supporting telemetry, threat, and recovery context
- Output: approved commands on `grid/control` and decisions on `grid/orchestrator/events`

The orchestrator is the final software approval gate. PPO/DQN recovery must carry a passing sandbox result, fresh threat evidence, an open target, and physical outage evidence. Hardware quarantine, emergency stop, active veto, cooldown, and sandbox violations remain rejection conditions. Approval is not counted as successful until newer Digital Twin telemetry shows the requested breaker state.

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
| AI Detection | `grid/alerts`, `grid/ai/status/ai_detection` | Threat Scorer, Gateway |
| LSTM/GNN/ST-GNN/PINN | `grid/ai/*`, `grid/ai/status/*` | Fusion, Orchestrator, Gateway |
| Fusion / Physics / TRUST | `grid/ai/fusion`, `grid/physics_validation`, `grid/trust_scores` | Threat Scorer, Recovery, Gateway |
| Threat Scorer | `grid/threat` | Self-Healing, AI Orchestrator, Gateway |
| Self-Healing | `grid/l6_recovery` | AI Orchestrator, Gateway |
| PPO/DQN Recovery | `grid/ai/recovery/*`, `grid/ai/recovery_policy`, `grid/control/proposed` | AI Orchestrator, Gateway |
| AI Orchestrator | `grid/orchestrator/events` | Gateway/Dashboard and audit consumers |
| AI Orchestrator | `grid/control` | Digital Twin, Gateway, defense context consumers |
| Digital Twin | `grid/events` | Self-Healing, Gateway/Dashboard |

Additional research and HIL compatibility topics exist, but they are not required to describe the verified default defense chain.

## Default Compose Boundary

The verified default stack contains 19 healthy services: PostgreSQL, Redis, MQTT, Gateway, Dashboard, Digital Twin, Celery worker/beat, AI Detection, LSTM, GNN, ST-GNN, PINN, AI Fusion, Physics Validation/TRUST, Threat Scorer, PPO/DQN Recovery Policy, Self-Healing, and AI Orchestrator. Pathogen–immune co-evolution has a justified offline training/evaluation role and produces versioned CSV/JSON artefacts rather than running continuously against the control bus.

## Verification Boundary

The current integration regression baseline is 868 passed, 0 failed, and 0 errors. Runtime verification additionally demonstrates:

```text
Attack -> Detection -> Threat Assessment -> Cyber-Physical Validation
       -> Recovery -> Grid Stabilization
```

`evaluation/end_to_end/verified_report.json` records ordered detection, threat, physical isolation, PPO/DQN proposal, sandbox/orchestrator approval, newer breaker-state telemetry, and post-experiment finite AC recovery. `evaluation/coevolution/verified/` records the separate three-seed pathogen–immune evaluation. PYPY remains research software and this verified baseline is not a production-readiness claim.
