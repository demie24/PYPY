# System Architecture — Smart Grid Cybersecurity Platform

This document describes the internal architecture of the PYPY platform: how services are structured, how they communicate, and how data flows through the system.

---

## Overview

The platform is a **modular, event-driven cyber-physical system** built around an MQTT message bus. Each service is an independent Python process that publishes and subscribes to topics — no service calls another directly.

```
                     ┌──────────────────────────────────────────────┐
                     │              SMART GRID PLATFORM              │
                     └──────────────────────────────────────────────┘

  [Hardware Layer]          [Simulation Layer]          [Intelligence Layer]
  ┌─────────────┐           ┌──────────────┐           ┌──────────────────┐
  │  ESP32 RTU  │           │ Digital Twin │           │  AI Detection    │
  │ (pending)   │           │  Simulator   │           │  (FDIA / UCIA)   │
  └──────┬──────┘           └──────┬───────┘           └────────┬─────────┘
         │                         │                            │
         └─────────────────────────┼────────────────────────────┘
                                   │
                         ┌─────────▼─────────┐
                         │   MQTT Broker      │
                         │  (Eclipse Mosquitto)│
                         └─────────┬─────────┘
                                   │
              ┌────────────────────┼─────────────────────┐
              │                    │                     │
   ┌──────────▼──────┐   ┌─────────▼──────┐   ┌────────▼───────┐
   │    Gateway      │   │  Cyber Defense │   │  Self-Healing  │
   │  (WS / REST)    │   │  Orchestrator  │   │  (FLISR + RL)  │
   └──────────┬──────┘   └────────────────┘   └────────┬───────┘
              │                                         │
   ┌──────────▼──────┐                        ┌────────▼───────┐
   │    Dashboard    │                        │ Relay Protection│
   │  (React / Vite) │                        └────────────────┘
   └─────────────────┘
```

---

## Service Descriptions

### Gateway (`core/gateway/`)
- **Role**: Central communication hub between the dashboard and all backend services
- **Exposes**: WebSocket endpoint (`ws://localhost:8000/ws`), REST health endpoint
- **MQTT**: Bridges WebSocket messages to/from the broker
- **Tech**: FastAPI + uvicorn + paho-mqtt

### Digital Twin (`core/digital_twin/`)
- **Role**: Physics-accurate simulation of an IEEE 9-Bus power distribution network
- **Publishes**: `grid/digital_twin/state` — full grid snapshot every simulation step
- **Tech**: Custom numpy/scipy power flow solver

### AI Detection (`core/ai_detection/`)
- **Role**: Real-time anomaly detection for False Data Injection Attacks (FDIA) and Unauthorized Command Injection Attacks (UCIA)
- **Subscribes**: `grid/digital_twin/state`
- **Publishes**: `grid/detection/alerts`
- **Tech**: LSTM / Physics-Informed Neural Network (PINN)

### Self-Healing (`core/self_healing/`)
- **Role**: Automated Fault Location, Isolation, and Service Restoration (FLISR) with Reinforcement Learning-based optimization
- **Subscribes**: `grid/digital_twin/state`, `grid/detection/alerts`
- **Publishes**: `grid/self_healing/actions`
- **Sub-modules**: `rl/` (PPO/DQN agents), `cyber_defense/` (integrated), `orchestrator/` (multi-agent)
- **Tech**: PyTorch RL, multi-agent consensus

### Cyber Defense (`core/cyber_defense/`)
- **Role**: Adaptive defense coordination in response to detected attacks
- **Integrated into**: `self_healing` service orchestrator

### Physics Validation (`core/physics_validation/`)
- **Role**: KCL/KVL validator — validates telemetry against physical laws before it reaches the AI
- **Used by**: `ai_detection` (trust filter)

### Relay Protection (`core/relay_protection/`)
- **Role**: IED overcurrent/overvoltage protection logic (in progress)

### Dashboard (`dashboard/`)
- **Role**: React/Vite single-line diagram, real-time alerts, self-healing action viewer
- **Connects to**: Gateway WebSocket

---

## Data Flow

```
[Digital Twin] ──publishes──► grid/digital_twin/state
                                      │
                         ┌────────────┼────────────┐
                         ▼            ▼            ▼
               [AI Detection]  [Self-Healing]  [Gateway]
                         │            │            │
                         ▼            ▼            ▼
               grid/detection  grid/self_healing  WebSocket
                  /alerts        /actions          ──► [Dashboard]
```

---

## `core/` Package Structure

```
core/
├── __init__.py
├── requirements.txt         # Base Python dependencies
├── requirements-ai.txt      # ML/AI-specific dependencies (torch, sklearn, etc.)
│
├── gateway/                 # FastAPI WebSocket + MQTT bridge
├── digital_twin/            # IEEE 9-Bus power flow simulator
├── ai_detection/            # FDIA/UCIA anomaly detection
├── ai_prediction/           # PINN inference (LSTM physics-informed model)
├── self_healing/            # FLISR + RL restoration engine
│   └── rl/                  # PPO / DQN agents
├── cyber_defense/           # Adaptive defense orchestration
├── physics_validation/      # KCL/KVL telemetry validation
├── orchestrator/            # Multi-agent AI orchestration layer
├── relay_protection/        # IED protection logic
├── attack_simulator/        # Cyber-attack injection for red-team testing
├── hardware/                # ESP32 HIL control layer
├── assistant/               # Voice/NLP operator assistant
├── data_collector/          # Training data collection daemon
└── threat_engine/           # Threat scoring and prioritization
```

---

## Test Architecture

```
tests/
├── conftest.py              # Shared fixtures (MQTT mocks, grid state, telemetry)
├── unit/                    # 355 unit tests — no external services required
├── integration/             # Integration tests (requires MQTT broker)
├── cyber/                   # Cyber defense scenario tests
├── physics/                 # PINN / physics validation tests
├── self_healing/            # RL self-healing tests
├── relay/                   # Relay protection tests
├── ai/                      # AI detection / prediction tests
├── hardware/                # Hardware abstraction layer tests
└── fixtures/                # Shared test data
```

Test command: `pytest tests/ -m "not integration" -q`

---

## Security Considerations

> ⚠️ **Research Platform** — Not production-ready. Do not deploy on live infrastructure.

- All inter-service communication is unencrypted MQTT (no TLS)
- No authentication on the gateway WebSocket
- Attack simulator is for red-team research only
- Hardware layer assumes trusted local network

---

*Last updated: May 2026*
