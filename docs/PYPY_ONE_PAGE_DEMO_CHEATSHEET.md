# PYPY — Emergency Demo Cheat Sheet

**10 September 2026 · Keep beside the browser · Core demo verified; UI caveats remain**

**PROJECT IN ONE SENTENCE:** A simulated smart-grid cybersecurity platform that detects abnormal data, checks physical evidence and evaluates recovery actions.

**PROBLEM:** False measurements can lead to unsafe electrical decisions.

**SOLUTION:** Analyse patterns, validate physics/trust, gate proposals and verify the resulting state.

**ARCHITECTURE:** IEEE-39 twin → MQTT → detector + LSTM/GNN/ST-GNN/PINN → fusion/physics/trust → threat/recovery → orchestrator → simulated control; gateway → React. SQLite = telemetry; PostgreSQL = application records; Redis = jobs/state.

**NORMAL FLOW:** Fresh converged telemetry, calibrated models, no active attack; policies may choose NO_ACTION. Nominal threat was around 30, not necessarily zero.

**ATTACK FLOW:** Bus_5 FDIA +0.15 p.u. → critical GRID_DEVIATION → score rises → isolation proposals may be rejected → STOP restores untampered report.

**DETECTION:** Maximum bus reconstruction error plus confirmation window; four learned-model streams supply additional evidence. Default scorer is experiment-aware.

**DECISION:** Proposal ≠ approval ≠ control ≠ observed outcome. Read the rejection/approval reason.

**RESPONSE:** Separate L_line_0 outage → STOP attacker → PPO/DQN close intent → sandbox → approval → later CLOSED state. This is distinct from FDIA detection.

## Five main things to show

1. `#/overview` / `#/grid`: fresh IEEE39 state and solver convergence.
2. `#/simulation` / `#/detection`: explicit FDIA and Bus_5 alert.
3. `#/decision`: physics/trust and rejection reason.
4. Terminal + grid: separate L_line_0 approved restoration chain.
5. `#/forensics`: timestamped evidence and honest limitations.

## Important commands

```bash
cd /home/demie/.gemini/antigravity/scratch/smart-grid-cybersecurity
docker compose up -d
docker compose ps
curl --max-time 10 -fsS http://localhost:8000/api/health
```

**FDIA — use terminal; current form omits magnitude:**

```bash
docker exec smart_grid_mqtt mosquitto_pub -t grid/attack -m '{"action":"START","type":"FDIA","config":{"target":"Bus_5","bias":0.15,"scale":1.0}}'
```

**STOP — keep ready:**

```bash
docker exec smart_grid_mqtt mosquitto_pub -t grid/attack -m '{"action":"STOP"}'
```

**Separate breaker example — observe OPEN, then STOP above:**

```bash
docker exec smart_grid_mqtt mosquitto_pub -t grid/attack -m '{"action":"START","type":"BREAKER_MANIPULATION","config":{"target":"L_line_0","command":"OPEN"}}'
```

**Evidence / dependency rescue / shutdown:**

```bash
docker exec smart_grid_mqtt mosquitto_sub -v -t grid/control/proposed -t grid/orchestrator/events -t grid/control
docker exec smart_grid_mqtt mosquitto_sub -t pypy/grid/telemetry -C 1 -W 10
docker compose up -d postgres redis mqtt
docker compose stop
```

The first subscription runs until Ctrl+C. Allow calibration before attacks and up to 30 seconds for recovery. Do not manually CLOSE and call it autonomous.

**URLS/PORTS:** UI `http://localhost:3001`; API `http://localhost:8000`; WebSocket `ws://localhost:8000/ws`; host MQTT 1884, container MQTT 1883; PostgreSQL 5432; Redis 6379. No active InfluxDB/Grafana URL.

## Top ten questions

| Question | One-line answer |
|---|---|
| Real grid? | Simulated IEEE-39; actual running software pipeline. |
| Why AI? | Temporal/topological evidence supplements deterministic checks. |
| Why physics? | Suspicious data alone does not justify safe switching. |
| What attack? | Parameterised Bus_5 FDIA; breaker restoration is separate. |
| What if AI is wrong? | Selected proposals face sandbox/orchestrator checks; guarantees are limited. |
| PPO/DQN trained on IEEE39? | No verified native retraining; a 72-input compatibility adapter is used. |
| What is autonomous? | Analysis and observed approved branch restoration; attack STOP is manual. |
| InfluxDB? | Not active; telemetry uses SQLite. |
| Tests? | 609 unit tests passed; 874 collected, not all run. |
| Main limits? | Simulation, experiment-aware scoring, model provenance and UI/control-security gaps. |

**UI WARNINGS:** FDIA default form has zero effect; PPO/DQN cards can miss live policy messages; safety card field mapping is incomplete. Show raw evidence. A post-STOP near-zero-loss warning was observed.

**FAILURE BACKUP:** STOP first. Spend at most 30–60 seconds diagnosing. Use `docs/audit_evidence/2026-09-10/fdia_summary.json`, `breaker_summary.json`, screenshots and test logs. Say: “This is recorded rehearsal evidence; the live component is unavailable.” Never present a reset, mock job or screenshot as autonomous live recovery.
