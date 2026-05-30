# MQTT Topics Reference — Smart Grid Platform

All inter-service communication uses the MQTT broker at `localhost:1884` (external) / `mqtt:1883` (internal Docker network).

---

## Topic Hierarchy

```
grid/
├── digital_twin/
│   └── state              # Full grid state snapshot (published by digital_twin)
├── detection/
│   └── alerts             # Anomaly detection alerts (published by ai_detection)
├── self_healing/
│   └── actions            # FLISR restoration actions (published by self_healing)
├── breaker/
│   └── status             # Breaker open/close events
└── command/
    └── control            # Operator control commands (sent by gateway)

hardware/
└── sensor/
    └── readings           # ESP32 physical sensor data (pending hardware)
```

---

## Topic Details

### `grid/digital_twin/state`
Published every simulation step by the **digital_twin** service.

```json
{
  "timestamp": 1609459200,
  "buses": [{"id": 1, "voltage": 1.04, "angle": 0.0}],
  "breakers": {"L1_4": "CLOSED", "L2_7": "CLOSED"},
  "generation": {"Bus_1": 2.32},
  "loads": {"Bus_5": 1.25}
}
```

### `grid/detection/alerts`
Published by **ai_detection** when an anomaly is found.

```json
{
  "timestamp": 1609459205,
  "alert_type": "FDIA",
  "confidence": 0.97,
  "affected_buses": [1, 2],
  "description": "False data injection detected on voltage sensors"
}
```

### `grid/self_healing/actions`
Published by **self_healing** when a restoration action is taken.

```json
{
  "timestamp": 1609459212,
  "action": "ISOLATE_LINE",
  "target": "L1_4",
  "reason": "branch_fault",
  "confidence": 0.95
}
```

---

## QoS Levels

| Topic | QoS | Reason |
|-------|-----|--------|
| `grid/digital_twin/state` | 0 | High-frequency, loss tolerable |
| `grid/detection/alerts` | 1 | At-least-once delivery required |
| `grid/self_healing/actions` | 2 | Exactly-once for control actions |
| `grid/command/control` | 2 | Critical operator commands |

---

*Last updated: May 2026*
