# PYPY — Supervisor Q&A Cheat Sheet

**Version 1.0 · 10 September 2026 · 50 evidence-grounded questions**

Answers refer to the audited working tree, not every thesis claim. Use [manual](PYPY_COMPLETE_USER_AND_TECHNICAL_MANUAL.md) chapters for sources and [audit evidence](audit_evidence/2026-09-10/) for fresh results. Personal motivation and contribution answers must be adapted to your true experience.

## 1. Why did you choose this project?

**Short answer:** It connects cybersecurity decisions with electrical consequences.

**Detailed answer:** A possible answer, if it reflects your motivation, is: “I wanted to examine how false information can affect a grid controller and how a response can be checked before it changes the system.” The repository supports that project objective, but it cannot establish your personal reasons. Add your actual engineering interest or project experience.

## 2. Why focus on smart grids?

**Short answer:** Grid operation depends on trusted measurements and control information.

**Detailed answer:** Voltage, power flow and breaker information guide operational decisions. A measurement anomaly may indicate either an electrical disturbance or information manipulation. PYPY uses a simulated grid to investigate that connection without connecting the experiment to an operating utility.

## 3. What is PYPY in one sentence?

**Short answer:** A simulated smart-grid cybersecurity platform integrating detection, validation and controlled recovery.

**Detailed answer:** The default deployment combines an IEEE-39 digital twin, MQTT, a gateway/browser, anomaly and learned-model services, physics/trust validation, threat scoring, recovery proposals and orchestration. The live audit demonstrated a detected FDIA and a separate validated breaker restoration.

## 4. Why use the immune-system analogy?

**Short answer:** It explains surveillance, diagnosis, decision and response in a memorable order.

**Detailed answer:** Telemetry resembles vital signs; detection resembles surveillance; validation resembles diagnosis; control resembles intervention. The analogy is explanatory. It does not mean the software has biological immunity or that ordinary logs automatically improve the models.

## 5. Why not just use a firewall?

**Short answer:** Access control alone does not check electrical consistency.

**Detailed answer:** A firewall remains useful, but a permitted message may contain an implausible measurement. PYPY adds model-based analysis of reported grid state and candidate actions. It is not a substitute for secure networking, and its current local WebSocket/MQTT control path still needs production hardening.

## 6. Where does the data come from?

**Short answer:** The live demonstration uses the Pandapower-based digital twin.

**Detailed answer:** The twin calculates repeated grid states and publishes them. Stored CSVs support research/training, but they are not required to serve the existing checkpoints. The audit did not establish utility field-data provenance for these datasets.

## 7. Is this real grid data?

**Short answer:** It is simulated benchmark-grid telemetry.

**Detailed answer:** The electrical network is simulated; the messaging, APIs, model inference and browser are actually running software. Do not describe the measurements as live utility sensor readings or imply a physical substation was connected.

## 8. What is the digital twin here?

**Short answer:** A stateful electrical model that produces telemetry and responds to simulated commands.

**Detailed answer:** It holds breaker, load and generator state, solves AC power flow, produces bus/branch data and applies attack effects. It also provides the model family used by restoration validation. It is more than a diagram, but less than a validated full utility replica.

## 9. Why IEEE-39?

**Short answer:** It is the default topology used by the active model contracts and demo stack.

**Detailed answer:** The runtime expects 39 buses and 46 branches, with 35 lines and 11 transformers. Other grid loaders exist, but the current feature conversion and model inference reject unsupported topology. Keep IEEE-39 selected during the AI demo.

## 10. Can it run IEEE14, IEEE57 or IEEE118?

**Short answer:** The simulator has loaders; the current AI pipeline is not interchangeable across them.

**Detailed answer:** The Settings page can request those topologies. That capability does not prove compatible learned detection or recovery. A separate multi-grid validation is required before presenting the same full pipeline on another grid.

## 11. What is MQTT used for?

**Short answer:** It distributes telemetry, evidence and commands between services.

**Detailed answer:** The canonical topic is `pypy/grid/telemetry`. Other topics carry alerts, model outputs, trust, proposals and control. The host connects on port 1884, while containers use `mqtt:1883`. A stopped broker initially prevented the AI services from operating during this audit.

## 12. What is the gateway's role?

**Short answer:** It connects MQTT to HTTP/WebSocket clients and telemetry storage.

**Detailed answer:** FastAPI exposes the APIs and `/ws`. The MQTT manager updates caches, stores per-asset telemetry in SQLite, translates compatibility data and forwards messages to browsers. A reachable HTTP process does not guarantee fresh grid data.

## 13. What is InfluxDB used for?

**Short answer:** It is not part of the audited active stack.

**Detailed answer:** No default Compose service or active runtime storage integration was found. Telemetry history uses SQLite, while application data uses PostgreSQL. Any presentation mentioning active InfluxDB storage should be corrected unless another separately verified deployment is being discussed.

## 14. What is PostgreSQL used for?

**Short answer:** Application records such as users, tenants, jobs, experiments and audits.

**Detailed answer:** Compose configures database `pypy_saas`. SQLAlchemy models define these tables and gateway startup initializes them. This does not mean canonical live telemetry is stored there as its primary time-series path; that role is separate.

## 15. What is Redis used for?

**Short answer:** Celery transport and shared operational state.

**Detailed answer:** The worker connects using `REDIS_URL`, and service helpers use Redis for queue/health or related state. Redis is not the power-flow simulator and is not the learned detector. Its availability matters to background application jobs.

## 16. What is SQLite used for?

**Short answer:** Per-bus, per-line and per-generator telemetry history.

**Detailed answer:** The gateway writes three telemetry tables at `/app/data/telemetry.db` in Docker. The default deployment does not mount that directory persistently, so container recreation can lose history. The canonical FDIA frame can differ from per-asset solver data written to this database.

## 17. What does Celery do?

**Short answer:** It runs background simulation jobs and scheduled application tasks.

**Detailed answer:** Worker/beat processes were healthy after restoring dependencies. However, the simulation worker attempts a twin constructor with a `grid_name` argument that the current twin does not accept, then has a mock fallback. Therefore queued SaaS jobs are not the recommended live power-flow demonstration.

## 18. Is Grafana the dashboard?

**Short answer:** The live dashboard is React; a Grafana configuration artifact also exists.

**Detailed answer:** The default stack serves React through nginx on port 3001. A Grafana dashboard JSON and a Prometheus-format metrics endpoint exist, but no Grafana service is configured in the selected Compose deployment. Do not promise a Grafana URL for this demo.

## 19. Which attack are you showing?

**Short answer:** A +0.15 p.u. Bus_5 false-data injection, followed by a separate breaker experiment.

**Detailed answer:** The first changes a reported voltage through the twin's tampering handler. The second opens `L_line_0` and stops the attacker before observing recovery. Separating them prevents the false claim that the telemetry-only FDIA caused and repaired a physical outage.

## 20. Why not click the FDIA button?

**Short answer:** The current form omits magnitude parameters.

**Detailed answer:** Its payload contains the target only. The backend defaults to zero bias and unit scale, producing no numeric FDIA effect. The documented terminal command includes explicit bias/scale and was rehearsed successfully. This is an acknowledged UI gap.

## 21. What attack types are implemented?

**Short answer:** FDIA, replay, DoS effects, sensor spoofing and breaker manipulation, plus composed scenarios.

**Detailed answer:** These are implemented in the active twin. Replay requires recorded frames; DoS is a simulated telemetry-loss effect, not network flooding. Adversarial and hardware attack research code also exists, but it is not automatically active in the default demo.

## 22. How does the main detector work?

**Short answer:** It reconstructs the 39-bus voltage vector and checks persistent reconstruction error.

**Detailed answer:** The NumPy autoencoder calibrates for 20 frames, then compares the maximum squared bus error with an adaptive threshold. A confirmation window and cooldown reduce repeated alerts. The suspect node is selected by maximum error, and the alert type is a heuristic description of the error pattern.

## 23. Why did the alert say GRID_DEVIATION instead of FDIA?

**Short answer:** The detector label comes from error-pattern rules, not the selected scenario name.

**Detailed answer:** The rehearsed injection produced a critical GRID_DEVIATION on Bus_5. The attack generator knows it launched FDIA, but that is different evidence. Use the actual alert wording rather than claiming the model independently attributed the exact attack type.

## 24. Which AI models are active?

**Short answer:** NumPy autoencoder, LSTM, GNN, ST-GNN, PINN, PPO and DQN.

**Detailed answer:** Four PyTorch analysis services serve checkpoint files; the recovery service runs both policy checkpoints through an adapter. The autoencoder calibrates online. Legacy forecasts, pathogen/immune models and other research checkpoints exist but are not all separate active services.

## 25. What does the LSTM receive?

**Short answer:** Twenty frames of 156 ordered features.

**Detailed answer:** The feature vector consists of 39 P values, 39 Q values, 39 voltages and 39 angles. Runtime emits eight-class probabilities and an anomaly score derived from non-normal probability. Correct ordering and units are as important as loading the weights.

## 26. What does the GNN add?

**Short answer:** It analyses relationships between buses and branches.

**Detailed answer:** It receives 39×4 node features and 46×5 edge features in the canonical topology order. It emits class evidence and node/edge risks. This is different from a temporal model, but its predictions still need evaluation and calibration rather than being assumed correct because topology is included.

## 27. What does ST-GNN do?

**Short answer:** It processes sequences of graph state and outputs future risk estimates.

**Detailed answer:** Runtime uses 20 graph frames and reports a five-step horizon. It emits node and branch risk values rather than the same eight-class payload as the LSTM/GNN classifier. It should not be described as a proven predictor of every future blackout.

## 28. What is PINN's role?

**Short answer:** It supplies physics-informed diagnostic evidence.

**Detailed answer:** The model reconstructs a 156-feature input and produces quantities evaluated by a physics-loss module. Its raw loss is used in calibrated fusion. Deterministic physics validation and the restoration sandbox are separate checks; PINN output alone does not approve a breaker close.

## 29. What is evidence fusion?

**Short answer:** It compares each model against its nominal baseline and combines the resulting drift signals.

**Detailed answer:** Median/MAD-based scaling makes unlike raw outputs more comparable. The weights are 0.30 LSTM, 0.25 GNN, 0.20 ST-GNN and 0.25 PINN. Inputs must be fresh and compatible. Fusion confidence is an agreement index, not measured detection accuracy.

## 30. What model did you personally train?

**Short answer:** Answer from your actual training records, not from file presence.

**Detailed answer:** The repository contains trainers and checkpoints, but that does not establish your personal contribution. State the model, training command/configuration, dataset, split, seed and checkpoint you actually produced. If you integrated existing weights, say “integrated and evaluated” rather than “trained.”

## 31. Were PPO/DQN trained on IEEE-39?

**Short answer:** Native IEEE-39 retraining is not verified; runtime explicitly reports false.

**Detailed answer:** Existing policies retain 72 inputs and ten actions. The adapter pools all IEEE-39 buses/branches into nine bins to match the legacy interface. This is a compatibility integration, not evidence of new native training. It can still produce a valid candidate for sandbox evaluation.

## 32. How did you evaluate the AI?

**Short answer:** This audit verified inference and limited scenarios; historical evaluators provide separate recorded metrics.

**Detailed answer:** Current tests and live traces prove selected behaviour, not broad generalisation. Historical methodology reports examine chronological splits, raw/postprocessed scores and normal/replay confusion. Quote a performance number only with its dataset, split, checkpoint and metric definition. No new complete accuracy study was performed here.

## 33. Is 98% confidence the same as 98% accuracy?

**Short answer:** No.

**Detailed answer:** The operational confidence index combines trust, physics score and AI risk. Accuracy is an empirical metric from labelled examples. The formula's percentage is useful for decision logic but cannot replace a confusion matrix or held-out evaluation.

## 34. Is the detector blind to the attack command?

**Short answer:** The default detector/scorer deployment is experiment-aware.

**Detailed answer:** These consumers can use known attack context, affecting windows or scoring. A `blind` mode exists for them, but fusion calibration still uses nominal/attack context. Do not describe the whole pipeline as fully blind without a dedicated, controlled configuration and evaluation.

## 35. What is the trust score?

**Short answer:** A stateful acceptance index for telemetry under the implemented consistency checks.

**Detailed answer:** It combines stability, consistency and suspicion; trust can drop quickly and recover gradually. Published bus/line values are percentages. It is not cryptographic authentication, attacker identification or a proven probability that a device is honest.

## 36. What happens if AI is wrong?

**Short answer:** Selected actions still face rules, consensus, freshness and sandbox checks.

**Detailed answer:** The FDIA rehearsal showed proposals rejected instead of executed. The separate restoration proposal needed explicit safe/finite/converged evidence and approval. These checks reduce certain risks but cannot guarantee correctness when models share assumptions or a direct operator path bypasses the proposal route.

## 37. How is a response validated?

**Short answer:** A copied-state sandbox predicts the result before the relevant restoration proposal proceeds.

**Detailed answer:** It evaluates convergence, finite values, voltage, thermal, cascade and topology conditions, and records violations/reasons. The orchestrator applies additional decision checks. The strongest proof is then a later telemetry frame showing the intended actual simulated state change.

## 38. What is actually autonomous?

**Short answer:** Continuous analysis and the observed policy-approved simulated branch restoration.

**Detailed answer:** The operator starts/stops demonstration attacks. Models and services process telemetry automatically. In the breaker rehearsal, the system generated the close proposal, validated it, approved it and forwarded control without a manual CLOSE. STOP and RESET are operator actions, not autonomous recovery.

## 39. Why did PYPY reject a response during FDIA?

**Short answer:** The isolation proposals did not meet decision conditions.

**Detailed answer:** Recorded reasons included `OPERATOR_APPROVAL_REQUIRED` with zero consensus and later duplicate suppression. No breaker opened. This is a valid example of a guarded decision boundary. It does not establish a complete dedicated approval UI for that rejection.

## 40. What is FLISR?

**Short answer:** Fault Location, Isolation and Service Restoration.

**Detailed answer:** The repository includes relay/FLISR and a more elaborate recovery state machine. Some older FLISR assumptions use the nine-bus tie `L7_8`. The fresh IEEE-39 restoration example used the PPO/DQN adapter and sandbox on `L_line_0`, so do not explain it as closing the legacy tie breaker.

## 41. How do you prove the grid recovered?

**Short answer:** Show the proposal, approval, control and a later closed-breaker/converged frame.

**Detailed answer:** A green diagram alone is weak evidence. The recorded breaker experiment contains OPEN state, a safe CLOSE proposal, APPROVAL, forwarded ORCHESTRATOR_APPROVED control and subsequent CLOSED state. It is one successful simulated recovery, not a statistical reliability result.

## 42. Why do PPO/DQN cards say unavailable?

**Short answer:** The current UI does not map all active policy topics/status fields.

**Detailed answer:** Raw `grid/ai/recovery_policy` contains both decisions. The cards expect `ppo`/`dqn` status keys or older pre-RL data, while the service publishes `recovery_policy`. Similarly, the safety card looks for different sandbox fields. Show raw evidence and acknowledge the interface gap.

## 43. What is real and what is simulated?

**Short answer:** The software pipeline is running; the electrical network and attack effects are simulated.

**Detailed answer:** Real Docker processes exchange real MQTT/HTTP/WebSocket data and run actual checkpoint inference. The grid assets are model state. No physical substation, utility connection or verified relay actuation was demonstrated. Optional hardware code is a different scope.

## 44. Are logs permanent forensic evidence?

**Short answer:** Not automatically.

**Detailed answer:** Browser/gateway histories are bounded; the gateway cache is in memory. SQLite is unmounted in the default container, and Docker log retention depends on deployment. The audit saves raw JSONL and summaries explicitly. Live logs are not automatically blockchain-protected or immutable.

## 45. Can it generate a PDF report?

**Short answer:** The current experiment PDF endpoint is a placeholder.

**Detailed answer:** It writes a PDF-looking header and text without building a complete document. The current Reports page is an operational summary, while JSON/CSV export handlers depend on stored results. Use the generated manuals or captured evidence rather than promising that PDF endpoint works.

## 46. How many tests passed?

**Short answer:** 609 unit tests passed; 874 tests were collected across the repository.

**Detailed answer:** A focused subset of 20 also passed and is included in the 609. The complete collected suite was not executed. Some tests use legacy nine-bus fixtures. Frontend build and ten page-render checks also passed, and the two live rehearsals supply separate runtime evidence.

## 47. What failed during the audit?

**Short answer:** Stopped infrastructure initially blocked telemetry and AI services.

**Detailed answer:** MQTT, Redis and PostgreSQL had exited. Consumers were unhealthy or restarting with MQTT resolution errors. Starting those existing dependencies restored all 19 services. The audit also identified UI mappings, mock export/job paths and a detector post-STOP edge case, without changing core code.

## 48. What is the biggest limitation?

**Short answer:** Demonstrated integration is stronger than claims of real-world security or generalisation.

**Detailed answer:** The modelled grid, experiment-aware scoring, adapted RL checkpoints and incomplete production control security constrain the claim. These limits are manageable research boundaries, but they prevent a claim that PYPY is a utility-ready autonomous defence product.

## 49. What would real deployment require?

**Short answer:** Independent validation, hardened control authority, reliable storage and tested physical integration.

**Detailed answer:** Work would include authenticated/authorised commands, secured MQTT, robust fail-safe behaviour, model evaluation on representative unseen data, verified physical modelling, hardware timing/interoperability tests and operational engineering review. These are future tasks; this audit did not establish regulatory or deployment compliance.

## 50. What did you personally develop?

**Short answer:** Name your actual modules, integrations and experiments with evidence.

**Detailed answer:** Prepare a contribution list linking each claim to a design note, commit, source file or experiment you personally performed. Distinguish your work from Pandapower, PyTorch, React, inherited code and assisted development. Repository presence and Git author names alone cannot establish all personal authorship.
