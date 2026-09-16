# PYPY exhibition runtime verification — 13 September 2026

**Runtime restored and deployed; real attack/detection and branch restoration verified. Full-grid success-banner presentation remains limited by the accepted frontend's evidence rules. No visual redesign or application-source changes were made.**

Booth URL: **http://localhost:3001/#/exhibition**. Startup instructions: [EXHIBITION_STARTUP.md](EXHIBITION_STARTUP.md).

## Root cause and deployment

The missing telemetry was an unavailable MQTT dependency, not an Exhibition Mode routing failure. Initial inspection captured repeated `Temporary failure in name resolution` errors resolving `mqtt` in both the twin publisher and gateway. The twin's main sweep loops did not start until its publisher connected. The dependency containers' inspected previous exit was 11 September; MQTT, Redis and PostgreSQL subsequently started together at approximately **2026-09-12 19:08:08 UTC**. Gateway reconnected at 19:08:17 and the twin at 19:08:26 using their existing retry paths. Those dependency starts had already occurred before this verification's first inspection; this task does not claim to have issued them. The original reason those dependencies were stopped is not established by the retained evidence.

The working repair is the documented existing dependency startup (`docker compose up -d mqtt redis postgres`), followed by verifying actual freshness. Process/API liveness alone was insufficient: containers could appear healthy while the transport was unavailable. No DNS, networking, MQTT configuration or application code was changed.

Executed deployment: `docker compose up -d --build --no-deps dashboard`. The accepted Exhibition Mode is now served by the existing Nginx dashboard container on port 3001. Configuration, networks, volumes and published ports were preserved. The deployed JavaScript checksum matches the locally built production bundle: `c8baa06fe3e576f4299d6f3dd16b850c9eb326cc09a4447b8d015b6c2402c84f`.

The running gateway's `mqtt_manager.py` and `store.py` checksums match the existing repository, so it was not rebuilt unnecessarily. During fault checks the same gateway was stopped/started, and the twin paused/unpaused. One recovery-policy restart cleared a stalled transient proposal signature, as described below.

## Actual data path verified

`digital_twin → pypy/grid/telemetry → existing MQTT broker → gateway /ws → deployed Exhibition Mode`

- Real topology API: 39 buses and 46 branches; generator/load roles and connections render.
- Canonical telemetry: advancing timestamps, 39 buses, 46 branches, live voltages and breaker changes, converged solver.
- A legacy nine-bus `grid/telemetry` compatibility stream also exists. The first recorder result (`baseline-1789241050827`) sampled that stream last; it is not the canonical baseline. The recorder was corrected to select `pypy/grid/telemetry`, without changing either stream or the application. Subsequent results record the full canonical state.
- Browser: `MONITORING LIVE`, enabled attack launch, received threat/trust/fusion/policy signals, real event/alert timeline updates. No page errors or request failures and zero WebSocket closes during the successful attack rehearsals.
- Gateway health: `healthy`, `mqtt_connected:true`. Redis PONG and PostgreSQL accepting connections were verified. `/api/telemetry/latest` responds with its existing per-asset schema; the canonical broker frames are used for the 39/46 and solver checks.
- Attack control is the existing WebSocket `grid/attack` forwarding path, not a separate invented REST API. START and STOP were exercised through actual UI buttons, with gateway forwarding logs and twin telemetry/events confirming execution.

## Real rehearsals and honest outcomes

### FDIA detection

Evidence: `fdia-1789275353614-summary.json`, matching `.jsonl`, and `-attack.png` / `-after-stop.png`.

The browser sent FDIA on Bus_5, bias +0.15, scale 1, experiment `ui-1789275361543`. Telemetry showed **1.1515 p.u.** under attack. At source timestamp **1789275367405**, the detector emitted critical **GRID_DEVIATION** for Bus_5, reconstruction loss 0.02228 versus threshold 0.001, with matching experiment/correlation evidence. The screenshot confirms ATTACK and DETECT activation, TRUST assessment, a proposal, critical threat, compromised Bus_5 and the live timeline.

The orchestrator rejected isolation proposals with `OPERATOR_APPROVAL_REQUIRED`; they were not executed. STOP was confirmed in telemetry and Bus_5 returned to **1.0014 p.u.**, all breakers closed and solver converged. The UI continued to show the recently received anomaly rather than claiming autonomous recovery. This is a detection/safety-gate demonstration, not an autonomous-healing claim.

### Long breaker attack: failure and assisted recovery

Evidence: `breaker-1789241113735-summary.json` and `resume-1789241279564-summary.json`, with raw traces and screenshots.

The first L_line_0 attack was deliberately observed for 12 seconds. PPO/DQN proposed CLOSE and the orchestrator approved it. The twin executed that CLOSE, but the still-active attacker re-tripped the breaker. After STOP, the next proposal was suppressed inside the orchestrator's 30-second duplicate window. The policy's unchanged-topology proposal signature prevented further retries. After 90 seconds, telemetry still showed OPEN; Exhibition Mode showed **VERIFYING GRID RESPONSE**, not success.

After the duplicate window had expired, restarting **only `recovery_policy`** cleared its in-memory signature. Its unchanged policy/sandbox produced a new approved CLOSE, and later canonical telemetry confirmed CLOSED/converged. No manual CLOSE, reset, model change or relaxed guard was used. Because an operator restarted the service, this recovery is explicitly **operator-assisted**.

### Booth breaker procedure: successful autonomous actuation

Evidence: `breaker-1789275483211-summary.json`, matching raw trace, `-attack.png` and `-after-stop.png`.

The browser launched L_line_0 manipulation and stopped the attacker promptly once OPEN was observed, before the first recovery close/re-trip cycle. The existing policy then produced a safe sandbox and PPO/DQN consensus. At **1789275496544**, the orchestrator emitted APPROVAL with correlation `ui-1789275490410:L_line_0`. It dispatched `ORCHESTRATOR_APPROVED` CLOSE. Canonical telemetry **1789275497514** subsequently showed L_line_0 CLOSED, no active attack and solver convergence. The recorder received that confirming frame 809 ms after receiving the control message; this is an observed local interval, not a new backend metric.

This clean rehearsal required **no manual CLOSE and no service restart**. It verifies autonomous branch restoration after the operator stops the attacker. No detector alert was produced by this brief breaker scenario; the separate FDIA rehearsal supplies real detection evidence. These two experiments must not be narrated as one correlated incident.

## Success presentation limitations — left unchanged

The backend's branch restoration is proven, but Exhibition Mode still says **VERIFYING GRID RESPONSE**. Inspection identified these existing presentation/evidence mismatches:

1. Normal IEEE39 telemetry includes Bus_36 at **1.0636 p.u.** (and Bus_25 around 1.056), outside the frontend's whole-grid 0.95–1.05 rule. Thus normal operation can show GRID REQUIRES ATTENTION and full-grid success remains withheld even when the backend sandbox marks a branch restoration safe.
2. Existing forwarded `grid/control` messages carry correlation/source-telemetry identifiers but no `timestamp`. The Exhibition Mode success predicate requires a fresh dispatch timestamp. The existing evidence reducer has receipt-time fallbacks, but the presentation checks the unmodified dispatch payload directly.
3. Canonical line power uses `P_mw`; ExhibitionTopology's decorative flow layer reads `active_power_flow`. Connections and real states render, but that layer does not animate from the canonical line power field. No runtime telemetry field was renamed to make it animate.
4. Proposal/rejection correlation is incomplete for some FDIA isolation messages. The raw event/decision evidence and existing Forensics page are the authoritative explanation; not every pipeline label resolves the latest rejection.

These are not safely corrected by restarts. The task explicitly preserves the accepted UI and backend contracts, so they were documented rather than changing thresholds, inserting timestamps or altering payloads. Do not promise the **GRID SECURED / AUTONOMOUS RECOVERY COMPLETED** banner on exhibition day. Show the real approval, control and later CLOSED telemetry instead. A separately authorized frontend compatibility correction would be needed for that final presentation behavior.

## Runtime fault checks

Final passing trace: **`failures-1789275667742-summary.json`**, matching `.jsonl` and screenshots.

| Actual interruption | Observed UI/result |
|---|---|
| Gateway stopped | CONNECTION LOST, launch disabled, no false success |
| Same gateway started | WebSocket reconnected, fresh canonical telemetry and launch restored |
| Twin paused; real START sent through gateway | Command unconfirmed after 15 seconds; no invented backend acknowledgement |
| Twin remains paused | TELEMETRY UNAVAILABLE after source freshness expires, launch disabled |
| STOP queued, twin unpaused, STOP repeated | Fresh data resumes, no active attack, all breakers closed |
| Fullscreen and reload after recovery | Passed; fresh data returns |

The temporary faults were always cleaned up in `finally`. Earlier harness runs failed on an ambiguous hidden-dialog button locator and an asynchronous fullscreen assertion; both were test-runner issues, corrected without application changes. Their traces are retained, and the final complete run passes. A timed-out START may still be queued: the operator card therefore requires emergency STOP and checking actual state before retrying.

Gateway restart resets its in-memory event cache. This task archived the real traces/screenshots before fault testing; it did not delete volumes, databases or persisted logs.

## Tests, final state and scope

- Existing repository suite: **876 passed**, 97 warnings, 92.74 seconds.
- Existing frontend/unit command: **both test files passed**.
- Existing isolated frontend browser suite against the deployed port-3001 build: **passed** (desktop/laptop/mobile layouts, both attacks, STOP, rejection/recovery presentation, stale/offline, command timeout, audio, fullscreen, dialog focus, attract mode, reduced motion, refresh and topology retry). These isolated tests remain separate from the real rehearsals above.
- TypeScript + Vite production build: **passed**, locally and in the existing dashboard Dockerfile.
- Real runtime checks: canonical data path, FDIA detection, clean approved breaker restoration, unsuccessful/assisted long attack, real transport/freeze/unconfirmed-command behavior, fullscreen and refresh all recorded.
- Final service snapshot: **19 running, healthy services**.
- Final canonical frames: **1789275788722 → 1789275789725**, age approximately 0.0 seconds at capture, 39 buses / 46 branches, converged, no active attack, no open breakers.
- Final gateway reports `mqtt_connected:true`; deployed dashboard bundle matches the built artifact.
- `git diff --check` passes. The repository already contained backend/frontend changes before this task; they were preserved.
- Source/configuration checksums were compared against the start of this runtime task. Backend logic: **NO change**. AI code/models: **NO change**. Simulation logic: **NO change**. MQTT contract: **NO change**. Database schema: **NO change**. API contract: **NO change**. Docker architecture/configuration: **NO change**. Accepted dashboard source: **NO change**.
- The existing Python suite again wrote its ignored assistant runtime-memory fixture. Its captured original content and exact original checksum were restored after testing; no guessed data or persistent test side effect remains there.
- Final checksum audit: **822 protected files checked, zero changed and zero missing**; see `source-audit.json`.

Added files are only this report, the operator card, opt-in diagnostic scripts `scripts/exhibition_runtime_verify.mjs` / `scripts/exhibition_failure_verify.mjs`, and generated evidence. These scripts use the existing local Playwright installation; they are not part of any running PYPY service. Failure rehearsal is disruptive and is not part of normal booth startup.

All evidence lives in [docs/audit_evidence/2026-09-13-exhibition](docs/audit_evidence/2026-09-13-exhibition/). `root-cause.txt` records outage/reconnect excerpts; `final-runtime.txt` records final service, API, canonical-data and bundle checks. Screenshots here are **real runtime captures**, unlike the isolated test screenshots from the earlier UI implementation.
