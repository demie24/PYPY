# Exhibition success verification — final frontend correction

Verified on 2026-09-13 against **http://localhost:3001/#/exhibition**.

**Result: PASS.** The real breaker rehearsal displayed **GRID SECURED** and the existing **Autonomous recovery completed · approved restoration confirmed in telemetry** presentation after a real, later canonical CLOSED frame. No UI redesign or backend modification was required.

## 1. Confirmed root causes

- The exhibition predicate imposed 0.95–1.05 p.u. across every bus. Healthy IEEE39 operation includes Bus_36 at 1.0636 and Bus_25 around 1.056. The established restoration validator instead uses 0.90–1.10 p.u. (`core/self_healing/restoration_validator.py`, Layer 6).
- Forwarded `grid/control` has no top-level timestamp. The reducer repeatedly evaluated a `Date.now()` fallback, moving the actuation boundary forward; the exhibition predicate also demanded the absent payload timestamp.
- The real trace exposed two related compatibility details: PPO/DQN proposals also omit a top-level timestamp but contain a real `sandbox.timestamp`; early policy assessments reference an older source telemetry ID than the eventual proposal. Comparing proposal receipt time to an earlier source-time approval, or retaining that older input ID, incorrectly withheld verification.

The intermediate rehearsal `breaker-1789277169974` genuinely restored the branch but remained VERIFYING while these last compatibility details were identified. It is not presented as the final successful UI test.

## 2. Exact files changed

| File | Purpose |
| --- | --- |
| `dashboard/src/recoveryEvidence.ts` | Freeze dispatch evidence time; use existing proposal safety-decision time; retain canonical telemetry and an actually observed OPEN; bind source telemetry identity to the actual proposal. |
| `dashboard/src/exhibitionState.ts` | Replace the incorrect voltage band with the established restoration envelope; require the full correlated physical-response evidence chain for success. |
| `dashboard/tests/exhibitionState.test.ts` | Realistic 39-bus/46-branch fixtures and positive/negative certification tests. |
| `dashboard/tests/recoveryEvidence.test.ts` | Receipt-time, source-frame-time and out-of-order telemetry regressions. |
| `dashboard/tests/exhibition.browser.mjs` | Strengthen the isolated success fixture with a safe PPO/DQN proposal, timestamp-less control and legitimate 1.0636 p.u. telemetry. |
| `EXHIBITION_STARTUP.md` | Change the operator's final acceptance check from “banner withheld” to waiting for verified success; explain refresh evidence limits. Startup commands and attack procedure are unchanged. |
| `EXHIBITION_SUCCESS_VERIFICATION_FIX.md` | This report. |

Only **two production source files** changed. Components, CSS, typography, layout, topology appearance, audio, animations, routing and command handling were untouched. The deployed CSS asset remains `index-u53EYPoq.css`; the final JS asset is `index-B0BRI8OM.js`.

These exhibition sources/tests were already untracked at the task boundary. No additional tracked source file was modified by this task. Existing tracked backend/configuration changes in the dirty worktree belong to the pre-existing baseline and were preserved, not reverted or claimed as this patch.

Generated evidence is separate under `docs/audit_evidence/2026-09-13-exhibition-success-fix/`. The existing unmodified live recorder wrote uniquely named raw recordings and screenshots under `docs/audit_evidence/2026-09-13-exhibition/`.

## 3. Logic and evidence safety

The existing reducer/state architecture is retained. A dispatch evidence item stores the actual control timestamp if supplied, otherwise the existing gateway `_evidence_timestamp`, otherwise frontend receipt time captured once. **The original control payload is unchanged.** `source_telemetry_timestamp` is an input-frame time, not an actuation timestamp, and cannot substitute for dispatch time.

Proposal ordering uses its real top-level timestamp when available, otherwise its real sandbox decision timestamp, then existing evidence/receipt fallback. Correlation and experiment IDs remain unchanged; the proposal's actual source telemetry ID replaces an earlier policy input ID for matching actuation evidence.

Success requires all of the following:

- A canonical OPEN observation for the target in the same experiment, before dispatch and within the existing recent-evidence window. Declaring `initial_state: OPEN` alone is insufficient.
- A matching CLOSE proposal from `AI_RL_PPO_DQN_CONSENSUS`, with authoritative sandbox overall, convergence, finite-state, voltage, thermal, topology and cascade safety flags true.
- A corresponding approval after proposal evidence and before dispatch; no subsequent rejection.
- An actually received orchestrator-approved CLOSE with matching correlation, experiment, target, command and available source telemetry identity.
- A **later `pypy/grid/telemetry` frame**, also matching the currently displayed canonical frame. Legacy `grid/telemetry` cannot certify exhibition success. Older canonical frames cannot overwrite newer canonical evidence.
- 39 buses, 46 branches, every required branch CLOSED, no other OPEN breaker, converged solver, finite voltages within the established restoration safety envelope, and an explicitly inactive attacker.
- Connected WebSocket, fresh telemetry under the existing 30-second threshold and recent dispatch under the existing 60-second threshold.

STOP, a proposal, approval, CLOSE dispatch or an elapsed timeout cannot independently satisfy these conditions. No backend timestamp, acknowledgement, telemetry or success event was manufactured.

## 4. Real runtime procedure and positive result

Only the dashboard was rebuilt/redeployed:

```sh
cd /home/demie/.gemini/antigravity/scratch/smart-grid-cybersecurity
docker compose up -d --build --no-deps dashboard
node scripts/exhibition_runtime_verify.mjs breaker
```

The recorder opens the actual Exhibition Mode, checks fresh baseline telemetry, uses the real launch selector for Breaker manipulation / `L_line_0`, observes OPEN, promptly clicks STOP, and waits for the existing autonomous CLOSE and later telemetry. It does not intercept the live WebSocket or manufacture runtime events.

Successful final run: **`breaker-1789277545201`**. Correlation: **`ui-1789277553116:L_line_0`**. Source telemetry ID: **`ui-1789277553116:1789277560068`**.

| Evidence | Actual timestamp, milliseconds since epoch |
| --- | --- |
| Canonical OPEN observed | 1789277554065 |
| Browser STOP sent, recorder receipt | 1789277555481 |
| Safe PPO/DQN sandbox decision, source time | 1789277560136 |
| Orchestrator APPROVAL, source time | 1789277560140 |
| Timestamp-less CLOSE, actual receipt time | 1789277560345 |
| First subsequent converged, attack-free CLOSED frame, source time | 1789277561077 |
| That frame received | 1789277561095 |

STOP followed the first OPEN frame by approximately 1.4 seconds. The confirming frame was generated 732 ms after CLOSE receipt, not reused from before actuation. All 46 breakers were CLOSED. Baseline maximum voltage was 1.0636 p.u.

The actual screenshot visibly shows **GRID SECURED**, **Autonomous recovery completed**, **Recovery: Verified**, live topology, and timeline entries for orchestrator CLOSE and subsequent CLOSED telemetry. No manual CLOSE or recovery-policy restart was used. Browser errors: **0**; failed requests: **0**; WebSocket closes: **0**.

Evidence:

- [Asserted positive proof](docs/audit_evidence/2026-09-13-exhibition-success-fix/positive-proof.json)
- [Real runtime summary](docs/audit_evidence/2026-09-13-exhibition/breaker-1789277545201-summary.json)
- [Raw real WebSocket/event recording](docs/audit_evidence/2026-09-13-exhibition/breaker-1789277545201.jsonl)
- [Actual successful screen](docs/audit_evidence/2026-09-13-exhibition/breaker-1789277545201-after-stop.png)

## 5. Negative tests and regression results

Negative cases below were tested with isolated frontend fixtures, never injected into production:

| Case | Result |
| --- | --- |
| CLOSE dispatched, later telemetry OPEN | PASS — VERIFYING, no success |
| CLOSED but stale telemetry | PASS — no success / TELEMETRY UNAVAILABLE |
| CLOSED while attacker active | PASS — no success |
| CLOSED but solver unconverged | PASS — no success |
| Gateway/WebSocket disconnected | PASS — CONNECTION LOST, no success |
| Healthy IEEE39 voltage above 1.05 | PASS — does not block evidenced restoration |
| FDIA STOP restores normal telemetry | PASS — not autonomous recovery |
| Missing approval, unsafe/non-PPO proposal, missing OPEN observation | PASS — no success |
| Wrong experiment/correlation/source evidence, expired dispatch | PASS — no success |
| Missing/open required breaker, absent attack status, unsafe voltage | PASS — no success |
| Legacy or missing canonical confirmation | PASS — no success |
| Refresh without original OPEN evidence | PASS — no restored success |
| Source input time before actuation, or older canonical frame | PASS — cannot advance verification incorrectly |

Commands and results:

```sh
cd dashboard
npm test
node --experimental-strip-types tests/exhibitionState.test.ts
node --experimental-strip-types tests/recoveryEvidence.test.ts
npm run build
PLAYWRIGHT_MODULE=/home/demie/.npm/_npx/e41f203b7505f1fb/node_modules/playwright/index.mjs EXHIBITION_URL=http://localhost:3001 node tests/exhibition.browser.mjs
cd ..
PYTHONDONTWRITEBYTECODE=1 python -m pytest -q
git diff --check
```

- Frontend: **12 named tests passed** across two test files. [Named results](docs/audit_evidence/2026-09-13-exhibition-success-fix/frontend-unit-results.txt).
- TypeScript and Vite production build: **PASS**, both locally and inside the dashboard image.
- Final deployed browser regression: **PASS** — 1920×1080, 1366×768, 1440×900, 390×844; navigation/refresh, START/STOP payloads, rejection/recovery, stale/offline, command timeout, topology retry, audio, fullscreen, dialog focus, attract entry/return/no commands, reduced motion. [Results](docs/audit_evidence/2026-09-13-exhibition-success-fix/browser-results.txt).
- Repository: **876 passed, 97 warnings in 93.66 seconds**. Existing tests modify ignored `core/assistant/routine_memory.json`; it was restored byte-for-byte to its pre-test contents and verified by checksum.
- `git diff --check`: **PASS**.

The previous real FDIA detection demonstration remains separate and authoritative in `EXHIBITION_RUNTIME_VERIFICATION.md`. It was not relabelled or rerun as autonomous healing. The short breaker rehearsal produced policy/trust/fusion evidence but no new IDS alert; no detection event was invented.

## 6. Final runtime state and limitations

- **19 services healthy**; gateway `mqtt_connected: true`.
- Final canonical timestamps **1789277722226 → 1789277723224**, age approximately zero at receipt; **39 buses / 46 branches**, solver converged, no active attack, all breakers CLOSED. [Final MQTT check](docs/audit_evidence/2026-09-13-exhibition-success-fix/final-mqtt.txt).
- URL: **http://localhost:3001/#/exhibition**. Exact booth commands remain in [EXHIBITION_STARTUP.md](EXHIBITION_STARTUP.md).
- Prompt STOP remains essential: an active attacker may re-trip the line and encounter existing duplicate-suppression behavior. This backend behavior was not altered.
- Success remains a recent, live verification, not a persisted certificate. After the existing evidence window expires, or refresh loses the original OPEN observation, the UI may withhold the success banner. Saved real evidence remains available.
- Existing topology nominal-voltage warning colours and threat indicators remain visible even when the restoration safety envelope is satisfied. They were not hidden to obtain success.
- One image build hit a Docker Hub TLS timeout; retry succeeded. Two browser navigation attempts timed out before launching an attack; retry succeeded without production changes. The exact cause of those page-load timeouts was not established. The accepted dashboard still references external Google Fonts. Start and load the booth page ahead of visitors; no typography or network configuration was changed.

## 7. Source audit / protected areas

Before/after SHA-256 manifests cover **822 existing files** across `core`, `services`, `workers`, `dashboard/src`, repository tests, Compose files, Mosquitto configuration and dashboard dependency manifests. **820 matched exactly; the only two differences were the intended production frontend files.** No protected-area change was found. The three frontend test edits are explicitly listed separately because `dashboard/tests` was outside that manifest.

See [source audit](docs/audit_evidence/2026-09-13-exhibition-success-fix/source-audit.json), [before](docs/audit_evidence/2026-09-13-exhibition-success-fix/before.sha256) and [after](docs/audit_evidence/2026-09-13-exhibition-success-fix/after.sha256).

Backend logic changed: **NO**. AI/model code or weights changed: **NO**. Simulation logic changed: **NO**. MQTT contract changed: **NO**. Database schema changed: **NO**. API/WebSocket backend contract changed: **NO**. Docker architecture/configuration changed: **NO**. Accepted UI design changed: **NO**. Only the dashboard container was redeployed.
