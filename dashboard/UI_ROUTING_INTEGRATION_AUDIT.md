# PYPY UI Routing Integration Audit

## Root cause

The redesigned shell was protected by a whitelist of legacy `currentPage` values. Any value outside that list fell through to the old dark operational JSX at the end of `App.tsx`. The authenticated dashboard emitted `copilot` and `marketplace`, while the whitelist expected `ai_copilot` and `scenario_marketplace`. Returning authentication and setup completion also routed directly to the old dark `UserDashboard`.

## Repair

- All non-public/authentication states now return `PypyControlCenter` unconditionally.
- Returning authentication and setup completion now route to `overview`.
- The old `UserDashboard` render branch was removed from `App.tsx`.
- Ten operational pages now use hash-backed state (`#/overview` through `#/settings`) for refresh and Back support.
- The old SCADA presentation remains only as unreachable source reference below the unconditional production-shell return and is eliminated from the production bundle.

## Routing map

| User action | Handler | Resulting route | Rendered component |
|---|---|---|---|
| Overview | `go("overview")` | `#/overview` | `OverviewPage` in `PypyControlCenter` |
| Live Grid | `go("grid")` | `#/grid` | `GridPage` in `PypyControlCenter` |
| Cyber Detection | `go("detection")` | `#/detection` | `DetectionPage` in `PypyControlCenter` |
| AI Decision | `go("decision")` | `#/decision` | `DecisionPage` in `PypyControlCenter` |
| Self-Healing | `go("recovery")` | `#/recovery` | `RecoveryPage` in `PypyControlCenter` |
| Attack Simulation | `go("simulation")` | `#/simulation` | `SimulationPage` in `PypyControlCenter` |
| Logs & Forensics | `go("forensics")` | `#/forensics` | `ForensicsPage` in `PypyControlCenter` |
| System Health | `go("health")` | `#/health` | `HealthPage` in `PypyControlCenter` |
| Reports | `go("reports")` | `#/reports` | `ReportsPage` in `PypyControlCenter` |
| Settings | `go("settings")` | `#/settings` | `SettingsPage` in `PypyControlCenter` |

## Legacy reachability after repair

| Legacy UI component | Still reachable? | Former entry path | Action taken |
|---|---:|---|---|
| Dark SCADA operational wrapper in `App.tsx` | No | Unknown/non-whitelisted `currentPage` | Replaced whitelist with unconditional production-shell return |
| Legacy analytics/report/settings presentation | No | Old operational sidebar | Old sidebar is below unconditional return and absent from production bundle |
| `MainOperationsDashboard` legacy composition | No | Old `overview` conditional | New `OverviewPage` is the only operational overview route |
| Dark authenticated `UserDashboard` | No | Successful returning login or setup completion | Authentication/setup now route to new `overview`; branch and import removed |
| Public landing page | Yes, intentionally | Sign-out/public entry | Public, non-operational page; Watch Demo enters new shell |
| Authentication and first-time setup pages | Yes, intentionally | Sign-in/register/onboarding | Non-operational entry pages; completion enters new shell |

## Browser evidence

A real Chromium session clicked all ten sidebar buttons. Each assertion verified the expected heading and hash, `.pypy-sidebar`, `.pypy-topbar`, light application background, absence of the old `.bg-scada-bg.text-scada-text` wrapper, and absence of the old Command Center title. Back navigation and refresh both preserved `#/reports` in the new shell. Sign-out reached the public landing page, and landing → Watch Demo returned to the new Overview.
