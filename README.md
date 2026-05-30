# Smart Grid Cybersecurity Platform (PYPY)

A modular, cyber-physical platform for simulating power distribution grids with real-time digital twin monitoring, AI-driven anomaly detection, self-healing logic, and hardware-in-the-loop (HIL) control via ESP32 edge devices.

**Project Status**: 🔄 **In Active Development**

---

## 📋 Project Status

| Component | Status | Notes |
|-----------|--------|-------|
| **Gateway** | ✅ Active | WebSocket + MQTT communication hub |
| **Digital Twin Simulator** | ✅ Active | Real-time power grid simulation (IEEE 9-Bus) |
| **AI Anomaly Detection** | ✅ Active | FDIA and unauthorized command detection |
| **Self-Healing Grid** | ✅ Active | Automated FLISR (Fault Location, Isolation, Service Restoration) |
| **Dashboard (React)** | ✅ Active | Real-time visualization & control interface |
| **Relay Protection** | ⏳ Partial | Overcurrent/overvoltage logic (in progress) |
| **Hardware ESP32** | ⏳ Pending | Waiting for hardware to arrive |
| **Advanced AI Services** | ⏳ Paused | Threat engine, data collector, PINN prediction (to be enabled) |

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    SMART GRID PLATFORM                       │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ Gateway  │  │ Digital  │  │    AI    │  │  Self-   │   │
│  │ (WS/MQTT)│  │  Twin    │  │Detection │  │ Healing  │   │
│  └──────┬───┘  └────┬─────┘  └────┬─────┘  └────┬─────┘   │
│         │           │             │             │           │
│         └───────────┼─────────────┼─────────────┘           │
│                     │             │                          │
│              ┌──────▼─────────────▼──────┐                  │
│              │   MQTT Broker (Eclipse)    │                 │
│              └──────────────────────────┘                   │
│                     ▲           │                            │
│                     │           ▼                            │
│              ┌──────────────────────────┐                   │
│              │   React Dashboard        │                   │
│              │  (Visualization & Control)│                  │
│              └──────────────────────────┘                   │
│                                                               │
│  [Hardware Layer - ESP32 (pending)]                          │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## 📁 Directory Structure

```
smart-grid-cybersecurity/
├── core/                          # All backend Python packages
│   ├── requirements.txt           # Base Python dependencies
│   ├── requirements-ai.txt        # AI/ML packages (torch, sklearn, etc.)
│   ├── gateway/                   # FastAPI WebSocket + MQTT bridge
│   ├── digital_twin/              # IEEE 9-Bus power flow simulator
│   ├── ai_detection/              # FDIA/UCIA anomaly detection
│   ├── ai_prediction/             # PINN/LSTM inference engine
│   ├── self_healing/              # FLISR + RL restoration engine
│   │   └── rl/                    # PPO / DQN agents
│   ├── cyber_defense/             # Adaptive defense orchestration
│   ├── physics_validation/        # KCL/KVL telemetry validation
│   ├── orchestrator/              # Multi-agent AI orchestrator
│   ├── relay_protection/          # IED protection logic
│   ├── attack_simulator/          # Cyber-attack injector (red-team)
│   ├── hardware/                  # ESP32 HIL control layer
│   └── assistant/                 # Voice/NLP operator assistant
│
├── dashboard/                     # React/Vite frontend
│   └── Dockerfile
│
├── hardware/                      # ESP32 firmware (pending hardware)
│   └── README.md
│
├── tests/                         # 379-test suite (355 unit + integration)
│   ├── conftest.py                # Shared fixtures (MQTT, grid state, etc.)
│   ├── unit/                      # Unit tests — no external services needed
│   ├── integration/               # Integration tests (requires MQTT broker)
│   ├── cyber/                     # Cyber defense scenario tests
│   ├── physics/                   # PINN / physics validation tests
│   └── self_healing/              # RL self-healing tests
│
├── docs/                          # Reference documentation
│   ├── API_REFERENCE.md           # Gateway API endpoints
│   └── MQTT_TOPICS.md             # MQTT message specification
│
├── logs/                          # Service log output (gitignored)
├── checkpoints/                   # RL model checkpoints (gitignored)
├── analytics/                     # Training run analytics (gitignored)
│
├── ARCHITECTURE.md                # Detailed system design
├── CONTRIBUTING.md                # Development guide
├── docker-compose.yml             # Service orchestration
├── mosquitto.conf                 # MQTT broker config
├── pyproject.toml                 # Python package config + pytest settings
└── .gitignore

```

---

## 🚀 Quick Start

### Prerequisites

- **Docker** & **Docker Compose** (v20.10+)
- **Python 3.10+** (for local development)
- **Node.js 18+** (for dashboard development)
- **4GB RAM** minimum, **8GB recommended**
- **Linux/macOS** (Windows may require WSL2)

### 1. Clone & Setup

```bash
git clone https://github.com/demie24/smart-grid-security.git
cd smart-grid-security

# Copy environment template (if exists)
# cp .env.example .env
```

### 2. Run with Docker Compose

```bash
# Build all services
docker-compose build

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### 3. Verify System is Running

```bash
# Check all containers are running
docker-compose ps

# Expected output:
# CONTAINER ID  IMAGE          STATUS          PORTS
# <id>          mqtt           Up              0.0.0.0:1884->1883/tcp
# <id>          gateway        Up              0.0.0.0:8000->8000/tcp
# <id>          digital_twin   Up
# <id>          dashboard      Up              0.0.0.0:3001->80/tcp
```

### 4. Access Interfaces

| Service | URL | Purpose |
|---------|-----|---------|
| **Dashboard** | http://localhost:3001 | Visualization & control |
| **Gateway API** | http://localhost:8000 | WebSocket/REST endpoints |
| **MQTT Broker** | localhost:1884 | Message broker |

---

## 🔧 Configuration

### Environment Variables

Set in `.env` or `docker-compose.yml`:

```bash
# MQTT Configuration
MQTT_BROKER=mqtt              # Hostname of MQTT broker
MQTT_PORT=1883                # MQTT port

# Logging
LOG_LEVEL=INFO                # DEBUG, INFO, WARNING, ERROR

# Digital Twin
GRID_BUS_COUNT=9              # Number of buses (IEEE 9-Bus standard)
SIMULATION_STEP=0.1            # Simulation step (seconds)
```

### MQTT Topics

Key topics the system uses:

```
grid/digital_twin/state        # Current grid state
grid/detection/alerts          # Anomaly alerts
grid/self_healing/actions      # Self-healing commands
grid/breaker/status            # Breaker status updates
hardware/sensor/readings       # Hardware sensor data
```

---

## 📊 Dashboard Guide

### Main Features

1. **Single-Line Diagram**
   - Visual representation of grid topology
   - Real-time voltage/current/power flow
   - Breaker status (open/closed)

2. **Anomaly Alerts**
   - Live threat detection results
   - Alert timeline
   - Confidence scores

3. **Self-Healing Actions**
   - Automated restoration suggestions
   - Manual override controls
   - Action history

4. **Metrics Dashboard**
   - System health indicators
   - Performance graphs
   - Historical trends

---

## 🧪 Testing

```bash
# Install the package (required for `from core.X.Y import Z` imports)
pip install -e .

# Fast check — no external services needed (379 tests)
pytest tests/ -m "not integration" -q

# Full unit suite with verbose output
pytest tests/unit/ -v

# With coverage report
pytest tests/unit/ --cov=core --cov-report=html
open htmlcov/index.html

# Integration tests (requires MQTT broker running)
docker-compose up -d mqtt
pytest tests/integration/ -v
```

---

## 📝 Development Workflow

### Local Development (without Docker)

```bash
# Create virtual environment
python3.10 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r core/requirements.txt
pip install -r core/requirements-ai.txt

# Start MQTT broker (Docker)
docker run -d -p 1883:1883 eclipse-mosquitto:latest

# Run individual services in separate terminals
python core/gateway/main.py
python core/digital_twin/simulator.py
python core/ai_detection/detector.py
python core/self_healing/orchestrator.py

# In another terminal, run dashboard
cd dashboard
npm install
npm start
```

### Adding New Services

1. Create service folder: `core/my_service/`
2. Add `main.py` entry point
3. Create `Dockerfile` in service folder
4. Update `docker-compose.yml`:
   ```yaml
   my_service:
     build:
       context: ./core
       dockerfile: ../my_service/Dockerfile
   ```
5. Add tests in `tests/unit/test_my_service.py`

---

## 🐛 Troubleshooting

### Services Not Starting

```bash
# Check logs
docker-compose logs gateway
docker-compose logs mqtt

# Rebuild images
docker-compose build --no-cache

# Check ports are free
netstat -an | grep -E "1883|8000|3001"
```

### MQTT Connection Issues

```bash
# Verify MQTT broker is running
docker-compose ps mqtt

# Test MQTT connection
mosquitto_sub -h localhost -p 1884 -t "test"

# In another terminal
mosquitto_pub -h localhost -p 1884 -t "test" -m "hello"
```

### Dashboard Not Showing Data

1. Verify Gateway is running: `curl http://localhost:8000/health`
2. Check browser console for WebSocket errors
3. Verify MQTT topics are being published: 
   ```bash
   mosquitto_sub -h localhost -p 1884 -t "grid/#"
   ```

### Out of Memory

```bash
# Increase Docker memory limit
docker-compose down
# Edit docker-compose.yml, add to services:
#   deploy:
#     resources:
#       limits:
#         memory: 2G
docker-compose up -d
```

---

## 📚 Documentation

- **[ARCHITECTURE.md](./ARCHITECTURE.md)** - Detailed system design
- **[API_REFERENCE.md](./docs/API_REFERENCE.md)** - Gateway API endpoints
- **[MQTT_TOPICS.md](./docs/MQTT_TOPICS.md)** - MQTT message specification
- **[HARDWARE.md](./hardware/README.md)** - ESP32 firmware guide (WIP)

---

## 🔄 CI/CD

This project uses **GitHub Actions** (`.github/workflows/test.yml`) for:
- ✅ Running unit + non-integration tests on every push/PR
- ✅ Flake8 lint (syntax errors block; style warnings are advisory)
- ✅ Coverage report uploaded to Codecov
- ✅ Docker image build validation on `main` branch pushes

---

## 🤝 Contributing

See **[CONTRIBUTING.md](./CONTRIBUTING.md)** for the full development guide, including:
- Branch and commit conventions
- Import style requirements (`from core.X.Y import Z`)
- How to add a new service
- Testing guidelines and fixture usage

---

## ⚠️ Known Limitations

- **Hardware**: ESP32 firmware pending hardware arrival
- **Scalability**: Current simulator limited to ~15 buses
- **Real-time**: Simulation runs faster than real-time
- **Security**: For research only, not production-ready

---

## 📈 Roadmap

- [ ] Hardware integration (ESP32 arrives Q2 2026)
- [ ] Advanced PINN-based prediction
- [ ] Reinforcement learning for optimal restoration
- [ ] Multi-agent consensus algorithms
- [ ] Cloud backend integration
- [ ] Enhanced security posture analysis

---

## 📖 Citation

If you use this platform in research, please cite:

```bibtex
@software{pypy_2025,
  author = {demie24},
  title = {Smart Grid Cybersecurity Platform},
  year = {2025},
  url = {https://github.com/demie24/smart-grid-security}
}
```

---

## 📄 License

[Add your license here - MIT, Apache 2.0, etc.]

---

## 👥 Support

- **Issues**: [GitHub Issues](https://github.com/demie24/smart-grid-security/issues)
- **Discussions**: [GitHub Discussions](https://github.com/demie24/smart-grid-security/discussions)
- **Email**: [Add contact email]

---

## 🙏 Acknowledgments

- IEEE 9-Bus test case reference
- Eclipse Mosquitto MQTT broker
- React & Vite community

---

**Last Updated**: May 2026 | **Status**: Actively Maintained
