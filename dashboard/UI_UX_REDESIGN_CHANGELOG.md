# PYPY UI/UX Redesign Changelog

## Scope

Frontend-only production redesign on branch `ui-ux-redesign`. Backend services, AI logic, MQTT topics, WebSocket payloads, Digital Twin behaviour, FLISR logic, and evidence artifacts were not modified.

## Changed

- Added a responsive PYPY control-centre shell with persistent desktop navigation and mobile drawer navigation.
- Added ten operator-focused views: Overview, Live Grid, Cyber Detection, AI Decision, Self-Healing, Attack Simulation, Logs & Forensics, System Health, Reports, and Settings.
- Added reusable presentation primitives for metric cards, section cards, status badges, incident rows, empty states, threat visualisation, model status, evidence lists, and decision-flow stages.
- Redesigned the overview around the sequence Summary → Situation → Detection → AI Decision → Safety Validation → Recovery.
- Preserved the real topology renderer and its zoom, pan, hover, breaker, attack, and FLISR semantics.
- Added explicit loading, disconnected, unavailable, and empty states. Missing backend metrics are never replaced with invented values.
- Exposed LSTM, GNN, ST-GNN, PINN, PPO, and DQN status only when supported by received live signals.
- Made PPO/DQN proposal status visually non-authoritative and kept the existing sandbox/orchestrator gate explicit.
- Added a visually distinct Simulation Mode that uses the existing `grid/attack` START/STOP payload contract.
- Added searchable and filterable live forensic records.
- Added responsive layouts for desktop, laptop, tablet, and narrow mobile screens.
- Added keyboard focus styles, text labels alongside colour states, semantic landmarks, reduced-motion support, and browser-local density/motion preferences.
- Corrected frontend transport selection so HTTPS deployments use `wss://` and HTTPS topology requests.
- Set the redesigned operations overview as the application entry view.

## Dependencies

No frontend dependency was added. The redesign uses the existing React, TypeScript, Lucide, Tailwind, and Vite toolchain.

## Verification

- `npm run build`: passed (`tsc` and Vite production build).
- `git diff --check -- dashboard`: passed.
- Desktop headless-Chromium visual audit: passed at 1600 × 1200.
- Mobile headless-Chromium visual audit: passed at 390 × 844.
- `npm run lint`: unavailable because the repository declares an ESLint script but does not install ESLint in `dashboard/node_modules` or `devDependencies`.
- Build retains the existing bundle-size warning for the legacy monolithic application chunk.

## Screenshots

- `docs/screenshots/ui-redesign/overview-desktop.png`
- `docs/screenshots/ui-redesign/overview-mobile.png`

## Known limitations

- Full live-data visual verification requires the backend stack to be running; the captured audit verifies the deliberate disconnected state.
- The existing `App.tsx` integration layer remains large. It was intentionally preserved to avoid changing validated data and command contracts.
- Bundle code-splitting and a formal browser-test suite remain future frontend engineering work.

## Navigation integration repair

- Removed the legacy dark operational wrapper as the default runtime fallback.
- Fixed a route mismatch where authenticated navigation emitted `copilot` and `marketplace` while the new-shell whitelist expected `ai_copilot` and `scenario_marketplace`.
- All non-public/authentication application states now return `PypyControlCenter`; unknown legacy state strings can no longer expose the old presentation.
- Added hash-backed routes for all ten operational pages so refresh and browser Back preserve the selected page inside the new shell.
- Verified every sidebar action in a real Chromium session and captured ten page-specific desktop screenshots.
