# Final PYPY source release preparation

Prepared 2026-09-16 from the authoritative `ui-ux-redesign` working tree for the
existing `demie24/PYPY` repository and its primary `main` branch. Existing history
is preserved. The intended annotated release is `v11.9.1`, following `v11.9` and
project metadata 11.9.0; no existing tag is replaced.

## Scope

Includes the final backend, Overview, Control Center, Exhibition Mode, canonical
load calculations, recovery evidence predicates, tests, operator guides, diagrams,
and selected dated research evidence. Local source functionality is preserved.
Release preparation adds portable browser-script imports, credential placeholders,
ignore rules, model manifests, and documentation. CI uses Node 22 and runs frontend
tests. Historical registry/Kubernetes deployment is manual (`workflow_dispatch`)
so source synchronization does not deploy infrastructure.

## Validation on 2026-09-16

| Check | Result |
|---|---|
| `PYTHONDONTWRITEBYTECODE=1 python -m pytest -q` | 876 passed, 0 failed; 97 warnings; 116.31 s |
| `npm test` in dashboard | 2 test files passed, 0 failed |
| `npm run build` in dashboard | TypeScript and Vite production build passed |
| `docker compose config --quiet` | Passed |
| `dashboard/tests/exhibition.browser.mjs` | Passed against final production preview |
| `dashboard/tests/overview.browser.mjs` | Passed; authoritative load and readiness checks |
| `dashboard/tests/scroll.browser.mjs` | Passed; no page errors or control commands |
| `scripts/verification/verify_closed_loop.py` | PASS against existing local Docker runtime |
| `git diff --check` | Passed before staging |
| Existing CI flake8 command | 7 pre-existing findings, listed below |

The three browser scripts used an installed Playwright module via
`PLAYWRIGHT_MODULE` and the newly built preview via `EXHIBITION_URL`.
PostgreSQL, Redis and MQTT were initially stopped; starting the existing containers
restored all 19 services to healthy and the gateway to MQTT-connected. The live
verifier observed detection, threat assessment, approved autonomous CLOSE and
newer CLOSED telemetry. Subsequent full AC convergence followed the verifier's
controlled experiment reset; it is not evidence of fully autonomous two-line
restoration. See [recorded release verification](release-closed-loop.json).
The live check used existing Docker images, not a newly rebuilt image set.

### Known pre-existing CI lint findings

`python -m flake8 core --count --select=E9,F63,F7,F82 --show-source --statistics`
reports undefined `timedelta` in `core/gateway/routes/billing.py:109`, undefined
`logger` at four sites in `core/gateway/routes/saas_auth.py`, an unresolved
`CriticalityAwareEncoder` type annotation in
`core/transfer/self_supervised_pretrain.py:310`, and an unused `global` declaration
in `core/workers/health/worker_monitor.py:30`. These four files are identical to
remote main at preparation time. They are outside the final implementation changes
and have not been modified to force CI success. The Python CI job will need these
resolved separately; passing tests do not imply a clean lint result.

## Sensitive-file audit

Candidate tracked and untracked text was scanned for API keys, secrets, tokens,
passwords, private-key headers, Bearer credentials and credential assignments.
No live API token or private-key material was found in publication candidates.
Literal matches were placeholders, synthetic test fixtures, variable names or
package metadata. The eight outgoing historical commits were also scanned for
recognizable provider tokens and private-key headers with no matches.
This was a pattern-based audit, not a guarantee against every secret format.

A hard-coded development database password was replaced in Compose files with
`${POSTGRES_PASSWORD:-CHANGE_ME}` and in the Kubernetes example with `CHANGE_ME`.
The existing local value is preserved only in an ignored, mode-0600 `.env` to keep
existing volumes usable. Public `.env.example` and `.env.production.template`
contain placeholders. Older Git history is not rewritten: rotate any credentials
that were ever used outside this isolated demo. GitHub Actions secret references
remain references, not credential values.

## Artifacts and reproduction

[Model manifest](release-model-manifest.json) records sizes and SHA-256 checksums
for the six active inference checkpoints plus the two checkpoints used by the
reference co-evolution evaluator. These small artifacts are included explicitly;
other training checkpoints remain ignored and untouched locally. PPO/DQN retain
the documented legacy compatibility encoding; inclusion is not retraining.

The largest tracked source-release files are the existing IEEE-39 telemetry CSV
(16,168,635 bytes) and legacy telemetry CSV (7,493,276 bytes). They are retained as
training/reproduction inputs. No release candidate exceeds 50 MiB or requires Git
LFS. Inference itself does not need training CSVs. For new synthetic IEEE-39 data:

```bash
python -m core.dataset_generator.dataset_generator \
  --seed 2026 --output-path /tmp/ieee39-release.csv \
  --valid-target 1300 --start-timestamp 0
```

Use trainers in `core/lstm`, `core/gnn`, `core/pinn`, `core/self_healing` and
`core/adversarial` for new experiments; inspect their path/default settings before
running to avoid overwriting release models. Training is not guaranteed to
reproduce historical weights bit for bit. Methodology reports describe corrected
experimental checkpoints that remain local, distinct from the active release
models. The distributed manifest provides the authoritative release hashes.

## Deliberately local-only material

- `.env` and any real environment/credential files.
- Thesis DOCX/PDF/Markdown, chapter drafts, correction reports, extracted thesis
  assets and appendix renders; the local thesis assembly utility.
- Downloaded `bin/arduino-cli` (36,931,908 bytes); install Arduino CLI separately
  for optional hardware development. PlatformIO dependencies are installed from
  `hardware/esp32_proximity_lab/platformio.ini`.
- `node_modules`, virtual environments, Python/pytest caches, PlatformIO `.pio`,
  build output, logs, runtime databases and Docker volumes.
- Redundant league/epoch checkpoints (the local checkpoint tree is about 184 MiB),
  corrected experimental checkpoints and training logs. None were deleted.

Dated curated screenshots, small experiment summaries and evidence streams are
included as project documentation; they are historical records, not fresh claims.
The separate older checkout rooted at `/home/demie` was not modified.
