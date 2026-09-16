# PYPY — Supervisor Demonstration Script

**Target: 8–9 minutes · Version 1.0 · 10 September 2026**

This script follows two fresh, successful rehearsals: [FDIA](audit_evidence/2026-09-10/fdia_summary.json) and [single-breaker recovery](audit_evidence/2026-09-10/breaker_summary.json). They are separate experiments. Overall readiness is **PARTIALLY READY**: the core path works, but documented UI gaps require terminal evidence.

## Pre-demo checklist

- [ ] Run commands from `/home/demie/.gemini/antigravity/scratch/smart-grid-cybersecurity`.
- [ ] Start with `docker compose up -d`; verify all 19 services with `docker compose ps`.
- [ ] `curl --max-time 10 -fsS http://localhost:8000/api/health` shows `mqtt_connected: true`.
- [ ] Wait for fresh IEEE39 telemetry, converged solver, all intended breakers closed and no active attack.
- [ ] Four model services and fusion are ready; allow calibration time.
- [ ] Open browser tabs at `http://localhost:3001/#/overview`, `#/grid`, `#/detection`, `#/decision`, `#/forensics`.
- [ ] Prepare terminal A for commands and terminal B for decision evidence.
- [ ] Keep STOP command and [failure plan](PYPY_DEMO_FAILURE_RECOVERY.md) visible.
- [ ] Keep saved FDIA/breaker summaries available offline.
- [ ] Do not change topology, retrain, clear logs or rebuild during the presentation.

Terminal B: start observation before the experiments:

```bash
docker exec smart_grid_mqtt mosquitto_sub -v \
  -t grid/control/proposed -t grid/orchestrator/events -t grid/control
```

This runs until Ctrl+C. It subscribes only; it does not operate breakers. Large sandbox arrays may appear. Point to `target`, `source`, `is_safe`, `solver_converged`, `overall_safe`, `event` and `reason` rather than reading the entire payload aloud.

## 00:00–00:45 — Introduce the problem

**Open:** `http://localhost:3001/#/overview`.

**Click:** No control buttons.

**Point at:** IEEE39 label, grid topology and incoming operational information.

**Say:** “PYPY studies a problem at the boundary between cybersecurity and electrical engineering. If a measurement is changed, a controller may make the wrong decision about the grid. This platform lets me demonstrate detection, physical checking and controlled response using a simulated IEEE-39 network.”

**Expected:** Connected browser and changing information. If there is no fresh telemetry, say so and use the failure plan; do not call cached numbers live.

## 00:45–01:30 — Explain the architecture

**Open:** Manual Chapter 5 in a prepared tab, then return to Overview.

**Click:** None.

**Point at:** Twin, MQTT, analysis, validation, proposal and orchestrator.

**Say:** “The simulator publishes telemetry through MQTT. The gateway brings it to the browser. Detection models and physics checks analyse it. Recovery modules can propose an action, and the orchestrator decides whether that proposal is allowed.”

**Add:** “SQLite stores per-asset telemetry. PostgreSQL and Redis support application and job workflows. They are different parts of the architecture.”

**Expected:** A source-based diagram, not an animation claiming every research module is active.

## 01:30–02:15 — Show normal operation

**Open:** `#/grid`.

**Click:** Use topology zoom/fit or inspect an asset if useful; do not toggle a breaker yet.

**Run in terminal A:**

```bash
docker exec smart_grid_mqtt mosquitto_sub -t pypy/grid/telemetry -C 1 -W 10
```

Wait for asynchronous topology loading; branch percentage labels have a field mismatch, so use raw canonical `capacity_pct` for loading claims.

**Point at:** `grid_name`, `solver_status.converged`, `attack_status.active_attack`, and `state.breakers`.

**Say:** “These values come from a running power-flow simulation. At the baseline the solver converges and the breakers are closed. The policies can legitimately choose no action. The threat score does not have to be zero; I compare it with this baseline and with the physics evidence.”

**Expected:** Fresh IEEE39 frame; no active attack. Nominal threat around 30 was observed, not guaranteed exactly 30.

## 02:15–03:00 — Start controlled FDIA

**Open:** `#/simulation`.

**Click:** Do not use the default FDIA Start simulation button: it does not include magnitude parameters.

**Run:**

```bash
docker exec smart_grid_mqtt mosquitto_pub -t grid/attack -m '{"action":"START","type":"FDIA","config":{"target":"Bus_5","bias":0.15,"scale":1.0}}'
```

**Point at:** Active FDIA scenario and Bus_5 when viewing the grid.

**Say:** “I am adding 0.15 per unit to one reported voltage. It ramps over five samples. This is measurement tampering inside the simulator, not a real attack on an external network or a physical generator adjustment.”

**Expected:** FDIA becomes active; Bus_5 report approaches roughly 1.15 p.u. The exact baseline varies.

## 03:00–03:45 — Show detection

**Open:** `#/detection`, then `#/forensics` if needed.

**Click:** In Forensics select ALERT or search `Bus_5`.

**Point at:** Critical alert, suspect bus, timestamp and threat change.

**Say:** “The detector reconstructs the expected voltage pattern and checks repeated error. In rehearsal it produced a critical GRID_DEVIATION on Bus_5. The scenario label says FDIA because we selected the experiment; the detector's own label is separate.”

**Add:** “The threat scorer is experiment-aware in this demo, so its score is not a blind detection-accuracy measurement.”

**Expected:** Alert usually appears within this observation window; rehearsed score reached 100. Do not repeatedly restart the attack if cooldown delays a second alert.

## 03:45–04:30 — Show validation and decision

**Open:** `#/decision`.

**Click:** None; do not use a direct execution button.

**Point at:** Physics/trust evidence, latest proposal and decision; terminal B for full reasons.

**Say:** “An alarm is not automatic permission to switch. Here the system produced isolation proposals, but the orchestrator rejected them because the required consensus conditions were not met. The breakers stayed closed. That rejection is part of the result.”

**Expected:** REJECTION or duplicate-suppression evidence was observed for this scenario. If current evidence differs, read the actual reason and do not narrate a prerecorded outcome as live fact.

## 04:30–05:00 — End the first experiment

**Open:** `#/simulation`.

**Click:** “Stop scenario” if enabled, or use the verified command below.

```bash
docker exec smart_grid_mqtt mosquitto_pub -t grid/attack -m '{"action":"STOP"}'
```

**Point at:** Attack clears; reported voltage returns toward baseline.

**Say:** “I have stopped the injected report. This restores untampered telemetry. I am not claiming that FDIA caused a physical outage or that an AI removed the attacker. Next I will show the physical restoration path as a separate experiment.”

**Expected:** Voltage near the pre-attack level. Threat/alerts can persist briefly. A post-STOP warning with small or zero rounded loss is a known detector-window edge case.

## 05:00–06:15 — Separate breaker recovery experiment

**Open:** `#/grid`; keep terminal B subscribed.

**Run:**

```bash
docker exec smart_grid_mqtt mosquitto_pub -t grid/attack -m '{"action":"START","type":"BREAKER_MANIPULATION","config":{"target":"L_line_0","command":"OPEN"}}'
```

Observe `L_line_0: OPEN` or the open-breaker count. Stop the attack after approximately two seconds / after the OPEN observation:

```bash
docker exec smart_grid_mqtt mosquitto_pub -t grid/attack -m '{"action":"STOP"}'
```

**Say:** “This time I changed the simulated topology by opening one branch. I stop the attacker so that we can inspect restoration without continued re-tripping. The policies must propose a valid close and the sandbox must predict an acceptable result.”

**Expected:** One branch opens. After the cooldown and policy evaluation, the rehearsed system proposed and executed a close. Allow up to 30 seconds to observe; do not click CLOSE to manufacture an autonomous result.

## 06:15–07:15 — Show the successful control chain

**Open:** `#/decision`, then `#/recovery` and `#/grid`.

**Click:** No “Execute recommended action” click is needed.

**Point at terminal B:**

- Proposal: `source: AI_RL_PPO_DQN_CONSENSUS`, target `L_line_0`, command CLOSE.
- Sandbox: `is_safe`, `solver_converged`, `finite_state`, `overall_safe` true; no violations.
- Decision: APPROVAL and its reason.
- Control: `source: ORCHESTRATOR_APPROVED`.

**Run if needed:**

```bash
docker exec smart_grid_mqtt mosquitto_sub -t pypy/grid/telemetry -C 1 -W 10
```

**Say:** “The important evidence is the complete chain: proposal, safety result, approval, control, then a later state showing CLOSED and a converged solver. This is one verified simulated restoration example. PPO and DQN use an adapter for this grid; I am not claiming they were newly trained on IEEE-39.”

**UI caveat:** If policy/safety cards are unavailable, say: “The backend supplies this evidence, but these cards have a field-mapping gap. Here is the raw message.”

## 07:15–08:00 — Show forensic evidence

**Open:** `#/forensics`.

**Click:** Search `L_line_0` or `Approved`; use ALL/EVENT filters as needed.

**Point at:** Timestamps and event source. Show saved rehearsal JSON only if needed, explicitly labelled recorded.

**Say:** “I keep the attack, detection and recovery evidence separate. This helps me explain what actually happened instead of assuming that nearby messages prove causation. Live history is bounded, so I capture the important messages for research records.”

**Expected:** Recent events; terminal records provide richer sandbox/control details than the summary table.

## 08:00–08:45 — Conclude with scope

**Open:** Overview or Reports.

**Say:** “The demonstrated contribution is an integrated simulated cyber-physical pipeline: telemetry, detection, validation, decision and verified response. The first example detected false data and rejected switching proposals. The second restored a simulated branch through policy consensus and safety checks. The remaining work includes stronger control security, improved UI mapping, persistent evidence storage and more independent model evaluation.”

Then invite questions. Do not claim all attacks are detected, real equipment was operated, or one rehearsal establishes a success rate.

## Five-minute version

Use 30 seconds for the problem, 45 seconds for normal state, 60 seconds for FDIA detection and rejection, 30 seconds to STOP and separate the experiments, 90 seconds for the breaker recovery chain, and 45 seconds for scope/limits. Show raw terminal evidence rather than navigating every page.

## End-of-demo cleanup

Send STOP. Confirm no active attack, intended closed-breaker state and solver convergence. Save terminal output before closing it. Do not clear histories while answering forensic questions. If shutting down after the meeting, use `docker compose stop`; the audit left the stack running.
