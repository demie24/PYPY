# PYPY audit evidence — 10 September 2026

Recorded from the working tree at `5f00008a8ece9a13aaaa37d1ce5c91668b7e7b9e`, with existing source changes. Runtime timestamps are Unix milliseconds or explicitly named receipt times; UTC records can fall on 9 September while the local audit date is 10 September.

- `repository_inventory.json`: non-cache file inventory, captured before writing the package.
- `source_symbols.json`: structural Python inspection; not proof every algorithm was executed.
- `checkpoint_manifest.json`: six active artifact sizes and SHA-256 hashes.
- `source_image_comparison.json`: three selected source/image hash matches.
- `openapi.json`: live HTTP schema; WebSocket is described in source, not this schema.
- `runtime_baseline.json` / `.jsonl`: latest-topic snapshot and short multi-topic baseline capture.
- `telemetry_sample.json`, `telemetry_final.json`: canonical one-frame captures.
- `fdia_rehearsal.jsonl`, `fdia_summary.json`: parameterised +0.15 Bus_5 FDIA, STOP and observed outcome. The post-STOP warning is retained.
- `breaker_rehearsal.jsonl`, `breaker_summary.json`: separate L_line_0 OPEN, STOP, policy proposal, sandbox, approval/control and later CLOSED state.
- `compose_health*.jsonl`, `compose_services.txt`, `api_health.json`: configured/final operational snapshots.
- `history_alerts.json`, `history_events.json`: bounded gateway history captures, not permanent archives.
- `test_collection.txt`: 874 collected; full suite not executed.
- `unit_tests.txt`: 609 passed; `focused_tests.txt`: 20-test subset also passed.
- `dashboard_build.txt`: successful existing-environment TypeScript/Vite build.
- `browser_pages.json`: ten route text snapshots and page-level JavaScript errors (none).
- `overview.png`, `decision.png`, `simulation.png`, `health.png`: early route screenshots; asynchronous fields may still be arriving.
- `grid_final.png`, `browser_network_final.json`: longer grid-page observation, direct WebSocket URL, no failed requests/console errors and loaded branches.
- `documentation_validation.json`: structural checks, link validation, word counts and final state summary.

Screenshots are recorded evidence, not a current live connection. Some UI fields are known to mismatch backend schemas; consult the manual before interpreting their values.

Executed operational verification included `docker compose config --quiet`, `docker compose up -d postgres redis mqtt`, `docker compose up -d`, `docker compose ps`, Redis ping, PostgreSQL readiness, HTTP health/history reads and broker subscriptions. Attack commands were executed through `docker exec smart_grid_mqtt mosquitto_pub` with the JSON reproduced in the demo script. Shutdown was checked through help and `docker compose --dry-run stop`; the stack was not shut down. Fresh dependency installation/full image build was not performed. No video was created.
