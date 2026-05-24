# Smart Grid Cybersecurity Platform

A modular, cyber-physical platform simulating a power distribution grid with real-time digital twin monitoring, hardware-in-the-loop (HIL) ESP32 edge control, intelligent electronic device (relay) protection, AI intrusion detection, and automatic self-healing logic.

## System Architecture

The platform consists of several decoupled services that communicate via a central WebSocket and MQTT Gateway:

1. **Gateway (`core/gateway/`)**: A WebSocket and MQTT communication hub.
2. **Digital Twin (`core/digital_twin/`)**: A Python-based real-time power grid simulator modeling buses, branches, generators, loads, and breakers.
3. **AI Anomaly Detection (`core/ai_detection/`)**: Machine learning models detecting False Data Injection Attacks (FDIA) and unauthorized commands.
4. **Relay Protection (`core/relay_protection/`)**: Emulator of Intelligent Electronic Devices (IEDs) providing overcurrent/overvoltage protection logic.
5. **Self-Healing Grid (`core/self_healing/`)**: Automates Fault Location, Isolation, and Service Restoration (FLISR).
6. **Attack Simulator (`core/attack_simulator/`)**: Injects faults, DoS, and telemetry manipulation (FDIA).
7. **Dashboard (`dashboard/`)**: A dynamic Vite + React single-line diagram and security operations center.
8. **Hardware (`hardware/`)**: ESP32 microcontroller firmware implementing physical substation sensors and breakers.

---

## Directory Layout

```text
smart-grid-cybersecurity/
├── core/
│   ├── gateway/           # Real-time WebSocket & MQTT message router
│   ├── digital_twin/      # Power grid simulator (IEEE 9-Bus model)
│   ├── ai_detection/      # Anomaly detection models & inference pipeline
│   ├── relay_protection/  # Overcurrent / undervoltage trip logic (IEDs)
│   ├── self_healing/      # FLISR (Fault Location, Isolation, and Service Restoration)
│   └── attack_simulator/  # Cyber-attack orchestrator (FDIA, DoS)
├── dashboard/             # React visualizer and control center
└── hardware/              # ESP32 firmware for hardware-in-the-loop RTU
```

## Getting Started

Refer to individual service READMEs for configuration and setup details. Use Docker Compose to launch the environment locally:
```bash
docker-compose up --build
```
