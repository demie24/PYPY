# PYPY — Demo Failure Recovery Plan

**Version 1.0 · 10 September 2026 · For the next live supervisor demonstration**

The objective during a failure is to preserve a truthful explanation and usable evidence. Start by stopping any active simulated attack. Allow one short diagnosis attempt; after 30–60 seconds, continue with the prepared fallback rather than consuming the presentation with repeated restarts.

Use the actual repository: `/home/demie/.gemini/antigravity/scratch/smart-grid-cybersecurity`. The initial audit outage was repaired by starting MQTT, Redis and PostgreSQL. After recovery, all 19 services were healthy and two controlled scenarios succeeded. That history is a useful fallback, not a promise that tomorrow's runtime cannot fail.

## Universal first step

If MQTT is available:

```bash
docker exec smart_grid_mqtt mosquitto_pub -t grid/attack -m '{"action":"STOP"}'
```

Do not clear alerts, remove containers, delete volumes or reset the grid before preserving evidence. If you later need a clean preparation baseline, `RESET_ALARMS` with target SYSTEM is a broad operator reset, not autonomous recovery. Explain it that way.

## Level 1 — One UI page fails

**Recognise:** One hash route is blank, a card says unavailable, or data is missing on a single page while MQTT/API continue working.

**Diagnose:** Reload the correct `http://localhost:3001/#/...` route. Check another page and browser console. Compare `#/health` with actual service state. Remember that “PPO unavailable” or “Safety gate awaiting evidence” may be the documented mapping gap rather than service failure.

**Commands:**

```bash
curl --max-time 10 -fsS http://localhost:8000/api/health
docker exec smart_grid_mqtt mosquitto_sub -t grid/ai/recovery_policy -C 1 -W 10
```

**Continue showing:** Live Grid, raw policy/decision messages, API histories and existing screenshots. The terminal can show the exact sandbox flags and control source even when a UI card cannot.

**Say:** “The backend is publishing the evidence, but this page has a display issue. I will show the actual message and its timestamp.”

**Avoid:** Inventing a page, navigating the unreachable old UI, or rebuilding every service to fix one frontend route.

**Rejoin:** Continue at detection/decision evidence; skip the broken panel.

## Level 2 — Attack simulation fails

**Recognise:** No changed voltage, no active scenario, or no alert after the planned observation window.

**Diagnose in order:** Is the broker connected? Is the target valid? Does the payload include a non-zero FDIA magnitude? Has detector calibration completed? Is an earlier attack/cooldown still active? The current default FDIA form has zero numerical effect; replay requires a buffer.

**Use the rehearsed trigger once:**

```bash
docker exec smart_grid_mqtt mosquitto_pub -t grid/attack -m '{"action":"START","type":"FDIA","config":{"target":"Bus_5","bias":0.15,"scale":1.0}}'
```

Observe for about 20–25 seconds, then STOP. Do not escalate to a complex cascade just because the simple case failed.

**Continue showing:** Normal live telemetry plus recorded `fdia_summary.json` and `fdia_rehearsal.jsonl`. Explain baseline voltage, injected ramp, Bus_5 alert, threat increase, rejected proposals and post-STOP return.

**Say:** “The live trigger has not produced the expected observation, so I will use the saved rehearsal trace. It records the exact parameters and outputs; I am not presenting it as a live result.”

**Rejoin:** Explain detection and validation, then show the separate recorded recovery chain if another live experiment would be uncertain.

## Level 3 — AI inference fails

**Recognise:** Model service restarts, checkpoint errors, invalid feature messages, stale status, or fusion never completes calibration.

**Diagnose:**

```bash
docker compose ps
docker compose logs --since 5m --tail 60 ai_lstm ai_gnn ai_stgnn ai_pinn ai_fusion
docker exec smart_grid_mqtt mosquitto_sub -t grid/ai/status/fusion -C 1 -W 10
```

Check IEEE39, valid counts, finite state and solver convergence. Do not change weights, retrain or relax safety thresholds during the presentation. A healthy process with stale output is not functioning inference.

**Continue showing:** If still available, live twin telemetry, NumPy detector and deterministic physics evidence. Otherwise use fresh saved baseline/model output and the successful test logs. Explain which model is unavailable rather than calling partial analysis a fully operational ensemble.

**Say:** “This model is not producing valid fresh inference in the current session. The remaining evidence is shown separately. The saved rehearsal demonstrates the intended integrated path, and the test report covers its specific software checks.”

**Important:** A missing PPO/DQN UI card is not enough to declare inference failed. Read `grid/ai/recovery_policy` first.

**Rejoin:** Demonstrate the decision boundary using source and recorded proposal/sandbox/approval. Do not issue a manual CLOSE and label it AI recovery.

## Level 4 — Database or MQTT fails

**Recognise:** `mqtt_connected` false, no new canonical messages, name-resolution errors, Celery disconnects, or database route failures.

**Diagnose and repair foundation:**

```bash
docker compose ps
docker compose up -d postgres redis mqtt
docker exec smart_grid_redis redis-cli ping
docker exec smart_grid_postgres pg_isready -U pypy_admin -d pypy_saas
curl --max-time 10 -fsS http://localhost:8000/api/health
```

This dependency start was executed successfully in the audit. Recheck model freshness/calibration after recovery; the UI may contain old state. If PostgreSQL alone fails, MQTT-based core grid analysis may still operate, while SaaS jobs/application records fail. If SQLite fails, per-asset history can be affected even though live canonical data flows. If MQTT fails, the integrated live cyber-physical chain is not operational.

**Continue showing:** Local evidence files, source architecture, tests, screenshots and model manifests. For a PostgreSQL-only issue, show the remaining live MQTT path with an explicit scope statement.

**Say:** “The transport/storage dependency is unavailable, so the live path is incomplete. I can still explain the implemented architecture and show timestamped rehearsal evidence.”

**Avoid:** `down -v`, deleting database files, changing credentials without understanding the initialized volume, or claiming InfluxDB recovery is required for this stack.

**Rejoin:** Only return to live narration after fresh messages and appropriate health checks succeed.

## Level 5 — Docker or the runtime completely fails

**Recognise:** Daemon inaccessible, laptop/VM resource failure, all services unavailable or insufficient time for recovery.

**Single check:** `docker info`. If host access cannot be restored promptly, stop attempting live execution and move to offline explanation. Do not reinstall Docker or rebuild PyTorch images while the supervisor waits.

**Offline sequence:**

1. Show the manual architecture and data-flow diagrams.
2. Open the saved Overview and System Health screenshots, labelled as recordings.
3. Read the FDIA summary: Bus_5 baseline→tampered values, critical alert and rejections.
4. Read the breaker summary: OPEN, safe CLOSE proposal, APPROVAL, forwarded control, CLOSED/converged outcome.
5. Show `unit_tests.txt` and `dashboard_build.txt` with dates and scope.
6. Explain limitations and what would be checked before the next live run.

**Say:** “The live environment is unavailable. These are recorded results from the audited rehearsal, not live measurements. I will use them to explain the implementation and the evidence chain, and I can repeat the live run once the host is restored.”

**What this still proves:** Source architecture, checkpoint identity, recorded test execution and recorded scenario observations. It does not prove present runtime readiness.

## Prepared evidence pack

| File | What it supports |
|---|---|
| `docs/audit_evidence/2026-09-10/grid_final.png` | Recorded full topology after asynchronous loading |
| `docs/audit_evidence/2026-09-10/overview.png` | Recorded current control-centre appearance |
| `docs/audit_evidence/2026-09-10/health.png` | Recorded UI signal/model display, including missing policy cards |
| `docs/audit_evidence/2026-09-10/decision.png` | Recorded decision page layout |
| `docs/audit_evidence/2026-09-10/simulation.png` | Actual scenario form |
| `docs/audit_evidence/2026-09-10/runtime_baseline.json` | Recorded canonical state and model/physics messages |
| `docs/audit_evidence/2026-09-10/fdia_summary.json` | Recorded FDIA outcome and post-STOP edge case |
| `docs/audit_evidence/2026-09-10/breaker_summary.json` | Recorded policy/sandbox/orchestrator recovery |
| `docs/audit_evidence/2026-09-10/*_rehearsal.jsonl` | Detailed raw scenario traces |
| `docs/audit_evidence/2026-09-10/unit_tests.txt` | 609 unit tests passed |
| `docs/audit_evidence/2026-09-10/test_collection.txt` | 874 collected tests; not all executed |
| `docs/audit_evidence/2026-09-10/dashboard_build.txt` | Successful TypeScript/Vite build |
| `docs/audit_evidence/2026-09-10/checkpoint_manifest.json` | Six active checkpoint hashes |

A backup video is recommended if the presenter can record one, but no video was generated in this audit. Do not promise an unavailable recording.

## After the meeting

Preserve the failure time, command and error before changing anything. Compare fresh dependency state, feature contract and image/source versions. Apply a narrow fix in a separate implementation task, repeat the same acceptance checks, and document whether the failure affected UI only, analysis, decision, or actual simulated control. Update the readiness verdict after retesting.
