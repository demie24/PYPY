# PYPY — Documentation and Technical Audit Report

**Version 1.0 · 10 September 2026 · Repository-first implementation audit**

## Verdict

**DEMO READINESS: PARTIALLY READY.**

The core local demonstration is operational and was rehearsed successfully. All 19 default Compose services were healthy after restoring stopped dependencies. The dashboard built successfully, all ten active routes rendered without page JavaScript errors, 609 unit tests passed, and separate FDIA and single-breaker recovery experiments produced usable evidence.

The qualification is necessary: the default FDIA UI payload has no numerical effect, policy/sandbox evidence is incompletely mapped into UI cards, default scoring uses attack context, and several broader reporting/SaaS/research features must not be presented as fully verified. A supervisor demo using the documented terminal commands and honest scope is supportable. A fully polished UI-only demonstration or production-readiness claim is not.

## 1. Repository identity and structure inspected

The environment started in `/home/demie`, which contains an older Compose layout and several PYPY copies. The active stack's gateway Compose label identifies:

`/home/demie/.gemini/antigravity/scratch/smart-grid-cybersecurity`

Audited HEAD: `5f00008a8ece9a13aaaa37d1ce5c91668b7e7b9e`, “feat: verify complete IEEE-39 AI recovery pipeline.” Package version is 11.9.0. The working tree already contained 27 modified tracked files plus untracked implementation/research/UI material. No core source refactor or behaviour change was applied for this documentation task.

The inventory covers 2,125 non-cache files and structural parsing of 646 Python files, with no AST parse errors. Git internals, dependency trees, bytecode, PlatformIO environments and newly generated audit evidence were excluded. Important source paths were followed in depth from Compose entrypoints through telemetry, inference, scoring, validation, response and UI. Remaining research modules were inventoried and classified; not every research algorithm, physical device or external integration was independently executed.

Inspected families include:

- Root/default, production and SaaS Compose definitions; service Dockerfiles; dependency manifests; environment templates; broker and nginx configuration.
- Digital twin topology/loaders, physics/solver, telemetry serializer, attack/control handlers and compatibility simulator files.
- NumPy detection, active model feature conversion/loaders/readiness/fusion, model definitions, trainers/evaluators and checkpoints.
- Physics/KCL/KVL/trust/filtering; threat scoring; recovery-policy adapter; sandbox/validator; relay/FLISR/recovery; orchestration.
- Gateway HTTP/WebSocket/MQTT/store/database; application models; Celery jobs and scheduled tasks.
- Active React control centre, all ten routes, legacy unreachable layout and UI field mappings.
- Unit/integration/physics/cyber/research tests; methodology outputs, datasets, generated figures, logs, hardware/assistant/adversarial/transfer/analytics material.

Three source-to-image checks matched SHA-256 for the twin entrypoint, model runtime and feature converter. This supports provenance for those paths; it is not a claim that every container file was byte-compared. The six active checkpoint hashes are recorded separately.

## 2. Actual architecture and implemented components

The default Compose stack has 19 services:

`postgres`, `redis`, `mqtt`, `gateway`, `celery_worker`, `celery_beat`, `digital_twin`, `ai_detection`, `ai_lstm`, `ai_gnn`, `ai_stgnn`, `ai_pinn`, `ai_fusion`, `physics_validation`, `recovery_policy`, `threat_scorer`, `self_healing`, `ai_orchestrator`, `dashboard`.

The core flow is:

**IEEE-39/Pandapower twin → canonical MQTT telemetry → NumPy detector and four learned-model services → calibrated fusion / physics / trust / threat → recovery proposals → orchestrator decision → simulated control → later telemetry.**

The gateway forwards MQTT state through WebSocket and exposes FastAPI routes. React is served by nginx on host port 3001; gateway is on 8000; host MQTT is 1884 mapped to broker 1883. PostgreSQL and Redis are on 5432 and 6379. Broker WebSocket port 9001 is configured, but the active browser connects directly to `ws://<hostname>:8000/ws`; topology requests also use port 8000 directly. Nginx proxy definitions do not remove this direct-port dependency.

SQLite stores per-asset telemetry. PostgreSQL supports application records and SaaS workflows. Redis supports Celery and operational state. InfluxDB is not an active integration in the selected deployment. A Grafana dashboard artifact and Prometheus-format endpoint exist, but no default Grafana service is running.

Implemented active model roles include the online NumPy autoencoder, LSTM, GNN, ST-GNN, PINN diagnostics and adapted PPO/DQN recovery. The PPO/DQN payload explicitly states `compatibility_adapter: true` and `retrained_on_ieee39: false`.

## 3. Experimental components found

Adversarial/pathogen/immune learning, partial observation, reconnaissance, stealth optimisation, coevolution, arena/self-play, transfer learning, PTDF/betweenness/SOM analytics and hierarchical research consensus have source and artifacts. They are not separate services in the default Compose runtime. Their historical reports are evidence of recorded outputs, not independently repeated results from this audit.

Hardware includes virtual devices, relay/sensor/PLC/ESP32 abstractions, execution/safety helpers and firmware projects. Assistant includes cognition, memory, voice and workflow modules. Unit coverage exists for many helpers. No physical actuation or external assistant/email/payment service was exercised by this documentation audit.

## 4. Legacy, inactive and incomplete components

| Finding | Evidence | Classification |
|---|---|---|
| Simplified old simulator and detector under `src/` | Three-bus state and threshold/placeholder logic | Legacy, not active entrypoints |
| Old standalone attack helper | Uses `voltage`, old breaker payload keys | Legacy; differs from canonical twin handler |
| Old forecast models | `core/ai_prediction/models/` and optional Dockerfile | Not a default active service |
| Old dashboard presentation | Code below unconditional control-centre return | Unreachable runtime layout; retained source |
| Legacy FLISR tie and scenario branches | `L7_8`, `L4_5`, other nine-bus identifiers | Partially topology-specific; do not assume IEEE-39 compatibility |
| Root `services/` and `workers/` copies | Default gateway build copies `core/` | Alternate/legacy layout, not selected image copies |
| SaaS Compose | References absent `core/Dockerfile` | Not a verified deployment alternative |
| Experiment PDF export | Writes header/text mock payload | Incomplete, not a valid report generator |
| Celery physical simulation path | Calls twin with unsupported constructor argument; mock fallback | Workflow exists but physics path is not reliable as written |

“No default service” does not mean globally dead code. Tests or research scripts may import these modules. The audit made no deletions.

## 5. Dependencies and missing prerequisites

The existing host environment successfully collected tests and ran the unit suite. Runtime containers loaded their model checkpoints. No missing checkpoint blocked the active rehearsal.

Important reproducibility limits:

- Docker uses Python 3.10; host tests used Python 3.13.14 with preinstalled dependencies. Fresh installation of older pinned NumPy/SciPy on a newer interpreter was not verified.
- Core runtime manifests do not include every testing/research dependency, such as pytest or scikit-learn. A clean environment may need extra provisioning.
- Full clean Docker rebuild/dependency download was not repeated. Existing images were reused; the frontend TypeScript/Vite production build was executed.
- System Python Playwright was installed but its expected `/usr/share/nodejs/playwright/cli.js` driver was missing. Browser validation succeeded through the already installed Node Playwright package and Chromium. No dependency installation was performed for this workaround.
- Checkpoint training seeds/episode counts cannot be inferred merely from checkpoint filenames. Historical RL provenance also marks native IEEE-39 training unverified.

## 6. Initial runtime blockers and resolution

Initially MQTT, Redis and PostgreSQL were exited. Several model/validation/recovery services were restarting, and the twin/detector/Celery worker were unhealthy. Model logs showed MQTT hostname resolution failures. The following existing operation restored dependencies:

```bash
docker compose up -d postgres redis mqtt
```

Consumers recovered without source changes. Later full `docker compose up -d` completed successfully and all 19 services were healthy. Full shutdown was dry-run verified, not actually performed; the platform was left running.

This outage exposes a maintenance issue: infrastructure restart behaviour differs from application restart policies, and a host/session restart can leave application processes running without their foundation. Pre-demo checks must cover all dependencies, not only the browser.

## 7. Fresh validation results

| Validation | Result | Evidence |
|---|---|---|
| Compose configuration | Valid; 19 services | `compose_services.txt`, health snapshots |
| Redis / PostgreSQL | PONG / accepting connections | Executed CLI health checks |
| Gateway | HTTP health, broker connected | `api_health.json` |
| Canonical telemetry | IEEE39, converged, no baseline attack/open breakers | `runtime_baseline.json`, final frame |
| Test collection | 874 collected, no collection errors | `test_collection.txt` |
| Unit suite | 609 passed, 3 warnings, 32.95 s | `unit_tests.txt` |
| Focused runtime/safety subset | 20 passed, 9.56 s; subset of 609 | `focused_tests.txt` |
| Frontend build | TypeScript/Vite successful | `dashboard_build.txt` |
| Browser routes | Ten rendered, no page-level JavaScript errors | `browser_pages.json`, four screenshots |
| FDIA | Changed Bus_5, critical alert, threat increase, proposal rejection, STOP recovery of report | `fdia_summary.json`, raw JSONL |
| Breaker restoration | OPEN→safe proposal→APPROVAL→control→CLOSED/converged | `breaker_summary.json`, raw JSONL |

The 874-test full suite was not run. Current tests are not all IEEE-39 tests; several deliberately use legacy topology. Browser rendering does not validate every button. Two scenario successes do not establish a statistical detection or restoration success rate.

### FDIA observations

The command used Bus_5, bias +0.15 and scale 1.0. Baseline voltage was approximately 1.0015–1.0017 p.u.; tampered voltage reached approximately 1.1513–1.1517. The detector emitted a CRITICAL `GRID_DEVIATION` on Bus_5 with loss 0.02236 and threshold 0.001. Threat reached 100. Isolation proposals were rejected, and no breaker opened. STOP returned voltage close to baseline.

A post-STOP warning named Bus_10 with rounded loss zero, consistent with the confirmation window retaining earlier anomalous entries. This is documented as a limitation, not counted as a successful new detection.

### Breaker observations

A separate `BREAKER_MANIPULATION` opened `L_line_0`, followed by STOP. A CLOSE proposal from `AI_RL_PPO_DQN_CONSENSUS` carried safe/converged/finite/voltage/thermal/cascade/topology/overall flags all true, with no violations. The orchestrator approved, forwarded `ORCHESTRATOR_APPROVED` control and preserved the source reference. Later telemetry showed CLOSED and converged power flow. Observed OPEN-to-CLOSED spacing was about seven seconds in this one trace; this is not a latency guarantee.

## 8. Best demo path and attack

Use the current local React control centre plus a prepared terminal subscribed to proposal/decision/control topics. Keep IEEE-39 selected. Start from a calibrated, converged baseline.

The safest primary attack is **parameterised Bus_5 FDIA (+0.15 p.u.)**. It is simple and reversible through STOP, and the rehearsal did not open breakers. Do not use the default FDIA form as the trigger: it sends only the target and defaults to no numerical tampering.

For the self-healing claim, use the separate rehearsed **L_line_0 breaker manipulation**, stop the attacker after observing OPEN, and wait for the policy/sandbox/orchestrator chain. Do not claim that FDIA caused this outage or that manual STOP is autonomous repair.

Best pages: Overview and Live Grid for baseline; Cyber Detection for alerts; AI Decision for interpretation; Logs & Forensics for records; Self-Healing for summary, supplemented with raw messages. Reports is a situation summary, and System Health is a signal-presence view.

## 9. Critical issues before the demonstration

| Priority | Issue | Required preparation / future fix |
|---|---|---|
| Immediate | Correct repository must be selected | Use the audited absolute path; do not use home-directory Compose |
| Immediate | Dependencies may be stopped after restart | Run full Compose startup and verify all 19 services |
| Immediate | Default FDIA UI is numerically ineffective | Use rehearsed explicit bias/scale command |
| Immediate | PPO/DQN, sandbox and active-load UI mappings incomplete | Prepare raw policy/proposal/decision evidence; do not invent unavailable demand values |
| Immediate | Startup calibration required | Wait for fresh model/fusion status before attack |
| Immediate | Experiment-aware score can be misrepresented | Disclose mode; distinguish scenario metadata from detector output |
| Immediate | Reset can be mistaken for recovery | Explain STOP/reset/operator control separately |
| Before production claims | Anonymous MQTT and unprotected direct WebSocket controls | Keep demo local; require a dedicated authorization/security task |
| Before stronger evaluation claims | RL provenance and historical model limitations | Do not claim native IEEE39 retraining or broad accuracy |
| Before SaaS/reporting demo | Mock job fallback and PDF handler | Exclude those workflows from the live script |
| Maintenance | SQLite persistence, restart policy and detector window edge case | Documented; no core refactor made |

The broker binds listeners and Compose publishes host ports broadly; comments suggesting “local only” are not access enforcement. A final browser network check confirmed direct `ws://localhost:8000/ws`, no console errors/failed requests, and branch rendering after a longer wait. Additional UI gaps include an unavailable active-load card and branch labels reading a different loading field, producing 0% labels. Do not use those cards as quantitative electrical evidence.

The UI's “simulation mode” controls the shared simulated twin; it is not a separate preview environment isolated from other viewers. No physical equipment was connected by this audit.

## 10. Changes and actions made

Created the seven requested Markdown documents and supporting audit artifacts under `docs/`. Generated a fresh local frontend build for validation; no UI source was changed. Started the three existing dependencies and ran idempotent full-stack startup. Ran bounded simulated FDIA and single-breaker experiments, each with STOP cleanup. Ran tests, read APIs/topics/logs, inspected browser routes and saved evidence.

No model retraining, code refactor, core behaviour fix, database deletion, volume deletion, administrative account mutation, external message/email, payment or physical hardware action was performed. Existing working-tree implementation changes were preserved. The final canonical state had no active attack and all branches closed; final service health is recorded in the evidence folder.

## 11. Documentation package created

All paths below are relative to the audited repository:

| Document | Purpose |
|---|---|
| [docs/PYPY_COMPLETE_USER_AND_TECHNICAL_MANUAL.md](PYPY_COMPLETE_USER_AND_TECHNICAL_MANUAL.md) | 30-chapter master manual, seven Mermaid diagrams, command/API/source appendices |
| [docs/PYPY_PROJECT_STORY_AND_PRESENTATION_GUIDE.md](PYPY_PROJECT_STORY_AND_PRESENTATION_GUIDE.md) | Twelve-part immune-system story and concise presentation narrative |
| [docs/PYPY_SUPERVISOR_DEMO_SCRIPT.md](PYPY_SUPERVISOR_DEMO_SCRIPT.md) | Timed 8–9-minute demonstration with actual commands/pages/results |
| [docs/PYPY_SUPERVISOR_QA_CHEATSHEET.md](PYPY_SUPERVISOR_QA_CHEATSHEET.md) | 50 questions, each with short and detailed answers |
| [docs/PYPY_ONE_PAGE_DEMO_CHEATSHEET.md](PYPY_ONE_PAGE_DEMO_CHEATSHEET.md) | Approximately 610-word emergency reference |
| [docs/PYPY_DEMO_FAILURE_RECOVERY.md](PYPY_DEMO_FAILURE_RECOVERY.md) | Five fallback levels and recorded-evidence instructions |
| [docs/PYPY_DOCUMENTATION_AUDIT_REPORT.md](PYPY_DOCUMENTATION_AUDIT_REPORT.md) | Findings, verification scope and readiness verdict |

The master manual is approximately 15,400 words before its contents/index additions. At roughly 250–350 words per page, this represents about 44–62 text pages, with diagrams/tables adding layout space. No PDF was generated, so pagination is an estimate rather than a measured claim.

## 12. Evidence and reproducibility index

See [audit_evidence/2026-09-10/](audit_evidence/2026-09-10/). Important files include inventory and source-symbol manifests, checkpoint hashes, live OpenAPI, baseline/final telemetry, service health snapshots, raw rehearsal JSONL and summaries, browser route text/screenshots, current test logs and frontend build output.

Evidence classification used throughout: A source; B configuration; C tests; D current runtime; E historical documented/generated results not repeated; F experimental/legacy/inactive/incomplete. Historical thesis material was not used to infer implementation existence. The repository and actual running services were authoritative.
