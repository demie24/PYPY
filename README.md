# ⚡ PYPY: Smart Grid Cybersecurity & Cyber-Physical Research Platform

[![CI Pipeline](https://github.com/demie24/PYPY/actions/workflows/ci.yml/badge.svg)](https://github.com/demie24/PYPY/actions/workflows/ci.yml)
[![Tests Passing](https://img.shields.io/badge/tests-833%20passed-success)](https://github.com/demie24/PYPY)
[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**PYPY** is an enterprise-grade cyber-physical power grid research and SaaS platform. It combines real-time digital twin grid monitoring (IEEE 9-Bus standard), AI-driven anomaly and False Data Injection Attack (FDIA) detection, self-healing Fault Location, Isolation, and Service Restoration (FLISR) logic, and Hardware-in-the-Loop (HIL) relay controls.

---

## 📋 System Capability Overview

| Module / Component | Functional Capabilities | Status |
|---|---|---|
| **API Gateway** | FastAPI WebSocket + MQTT communication bridge & JWT authentication | ✅ Active |
| **Digital Twin Simulator** | Real-time IEEE 9-Bus power flow solver (voltage, phase angle, active/reactive power) | ✅ Active |
| **AI Anomaly Detection** | Real-time FDIA, unauthorized command, and telemetry anomaly detection | ✅ Active |
| **Self-Healing Engine** | Automated FLISR restoration planner and Deep RL (PPO/DQN) recovery policies | ✅ Active |
| **Operator Dashboard** | React + Vite single-line diagram visualization, alert timeline & control console | ✅ Active |
| **Relay Protection** | Intelligent Electronic Device (IED) overcurrent and distance relay trip simulation | ✅ Active |
| **Hardware HIL Bridge** | ESP32 edge microcontroller integration & physical relay control bridge | ⏳ HIL Ready |
| **Deep RL / Coevolution** | Red/Blue agent competitive self-play and physics-informed neural network (PINN) inference | ✅ Integrated |

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                 PYPY SMART GRID PLATFORM                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ │
│  │ Gateway  │  │ Digital  │  │    AI    │  │  Self-   │ │
│  │ (WS/REST)│  │  Twin    │  │Detection │  │ Healing  │ │
│  └──────┬───┘  └────┬─────┘  └────┬─────┘  └────┬─────┘ │
│         │           │             │             │         │
│         └───────────┼─────────────┼─────────────┘         │
│                     │             │                        │
│              ┌──────▼─────────────▼──────┐                │
│              │   MQTT Broker (Mosquitto) │                │
│              └──────────────┬────────────┘                │
│                             │                             │
│                      ┌──────▼──────┐                      │
│                      │ React / Vite│                      │
│                      │ Dashboard   │                      │
│                      └─────────────┘                      │
│                                                             │
│  [ Hardware Layer — ESP32 Microcontrollers / Relay HIL ]     │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start Guide

### Prerequisites

- **Python 3.10+**
- **Docker & Docker Compose** (v20.10+)
- **Node.js 18+** & **npm**

---

### 1. Clone & Environment Configuration

```bash
git clone https://github.com/demie24/PYPY.git
cd PYPY

# Create local environment configuration
cp .env.example .env
```

---

### 2. Run with Docker Compose

Spin up PostgreSQL, Redis, MQTT Broker, Gateway API, Celery Workers, Digital Twin, and Dashboard:

```bash
# Build and launch services
docker compose up -d --build

# View real-time container logs
docker compose logs -f
```

Access the interfaces once services report healthy status:

| Service | Access URL | Description |
|---|---|---|
| **Dashboard Console** | `http://localhost:3001` | Single-line diagram & alert dashboard |
| **Gateway API Docs** | `http://localhost:8000/docs` | OpenAPI / Swagger interactive documentation |
| **Health Endpoint** | `http://localhost:8000/api/health` | Service health status JSON |
| **MQTT Broker** | `localhost:1884` | Telemetry & control topic bus |

---

### 3. Local Development (Without Docker)

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install all backend requirements
pip install -r requirements.txt
pip install -e .

# Start local MQTT broker container
docker run -d -p 1883:1883 eclipse-mosquitto:latest

# Run Gateway API service
python core/gateway/main.py

# In another terminal, run Dashboard frontend
cd dashboard
npm install
npm run dev
```

---

## 🧪 Testing & Validation

The platform features an extensive test suite of **833 unit, integration, physics, and cybersecurity tests**.

```bash
# Install editable package for local imports
pip install -e .

# Run the full 833-test regression suite
pytest

# Run non-integration unit tests only
pytest -m "not integration"

# Run tests with code coverage report
pytest --cov=core --cov-report=term-missing
```

---

## 📁 Repository Structure

```
PYPY/
├── core/                          # Core Python backend engine
│   ├── gateway/                   # FastAPI REST API & WebSocket server
│   ├── digital_twin/              # IEEE 9-Bus power flow simulator
│   ├── ai_detection/              # Anomaly detection & FDIA classifiers
│   ├── ai_prediction/             # PINN prediction & LSTM engines
│   ├── self_healing/              # FLISR restoration & RL agents
│   ├── cyber_defense/             # Adaptive defense orchestrator
│   ├── relay_protection/          # Intelligent relay protection logic
│   ├── hardware/                  # ESP32 HIL bridge & relay interface
│   ├── requirements.txt           # Core Python dependencies
│   └── requirements-ai.txt        # Deep learning / PyTorch packages
│
├── dashboard/                     # React + Vite frontend application
│   ├── src/                       # UI components, single-line diagrams, hooks
│   └── Dockerfile                 # Production nginx container build
│
├── tests/                         # Comprehensive 833-test regression suite
│   ├── unit/                      # Isolated unit tests
│   ├── integration/               # Multi-service integration tests
│   ├── cyber/                     # Cyber-attack simulation tests
│   ├── physics/                   # Physics/KCL validation tests
│   └── self_healing/              # RL self-healing tests
│
├── docs/                          # Platform documentation
│   ├── API_REFERENCE.md           # REST & WebSocket endpoint documentation
│   ├── MQTT_TOPICS.md             # MQTT message bus topics specification
│   ├── DEPLOYMENT_GUIDE.md        # Production deployment instructions
│   └── reports/                   # Historical architecture & audit research reports
│
├── k8s/                           # Kubernetes deployment manifests
├── scripts/                       # Deployment and verification utility scripts
├── docker-compose.yml             # Local docker development stack
├── docker-compose.prod.yml        # Production stack with Nginx proxy
├── pyproject.toml                 # Package configuration & pytest settings
├── LICENSE                        # MIT Open Source License
└── README.md                      # Project documentation
```

---

## 🔒 Security & Disclosure

- All sample API keys and secret definitions are strictly scoped to mock/development values.
- Never commit active production credentials or real `.env.production` files.
- Refer to `k8s/secrets.yaml.template` and `.env.production.template` for secure configuration management.

---

## 📖 Citation

If you use PYPY in academic research or smart grid security publications, please cite:

```bibtex
@software{pypy_2026,
  author = {demie24},
  title = {PYPY: Smart Grid Cybersecurity & Cyber-Physical Research Platform},
  year = {2026},
  url = {https://github.com/demie24/PYPY}
}
```

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
