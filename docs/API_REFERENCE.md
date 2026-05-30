# API Reference — Smart Grid Gateway

> **Status**: Work in progress. This document describes the planned API surface.
> See `core/gateway/routes/` for current implementations.

---

## Base URL

```
http://localhost:8000
```

---

## Health Check

```http
GET /health
```

**Response**
```json
{ "status": "ok", "timestamp": 1609459200 }
```

---

## WebSocket Endpoint

```
ws://localhost:8000/ws
```

Clients connect here to receive real-time grid state updates and send control commands.

### Incoming message format (server → client)
```json
{
  "type": "grid_state",
  "payload": { ... },
  "timestamp": 1609459200
}
```

### Outgoing message format (client → server)
```json
{
  "type": "control",
  "command": "open_breaker",
  "payload": { "breaker_id": "BR_1_2" },
  "timestamp": 1609459200
}
```

---

## REST Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Service health check |
| GET | `/grid/state` | Current grid state snapshot |
| POST | `/grid/breaker` | Send breaker control command |

---

*Last updated: May 2026*
