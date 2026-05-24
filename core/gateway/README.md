# Core Gateway Service

The Gateway service is the communication backbone of the Smart Grid Cybersecurity project. It handles:
- Routing real-time telemetry from the **Digital Twin** and **ESP32** to the **Dashboard** and **AI Detection** engines.
- Handling control signals (e.g. manual breaker commands, self-healing routing adjustments) and delivering them to their respective targets.
- Providing MQTT and WebSocket integration.

## Installation & Setup

1. Install dependencies:
   ```bash
   npm install
   ```
2. Start server:
   ```bash
   npm run dev
   ```

## Protocol Specifications
Communication is standard JSON over WebSockets/MQTT.

### Telemetry Payload Format
```json
{
  "timestamp": 1700000000000,
  "device_id": "substation_01",
  "data": {
    "voltage": 119.8,
    "current": 4.2,
    "frequency": 60.01,
    "breaker_status": "CLOSED"
  }
}
```
