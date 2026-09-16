# PYPY — booth operator card

## Start and check

```sh
cd PYPY
docker compose up -d --no-build
docker compose ps
curl --max-time 10 -fsS http://localhost:8000/api/health
docker exec smart_grid_mqtt mosquitto_sub -t pypy/grid/telemetry -C 2 -W 10 | python -c 'import sys,json,time; [print({"timestamp":d["timestamp"],"age_s":round(time.time()-d["timestamp"]/1000,1),"buses":len(d["state"]["buses"]),"branches":len(d["state"]["lines"]),"solver":d.get("solver_status"),"attack":d.get("attack_status",{}).get("active_attack"),"open":[k for k,v in d["state"]["breakers"].items() if v!="CLOSED"]}) for d in map(json.loads,sys.stdin)]'
```

Wait for 19 healthy services, `mqtt_connected:true`, two advancing timestamps, 39 buses, 46 branches, converged solver, no attack and no open breakers. Do not start a scenario while readiness is incomplete.

Open **http://localhost:3001/#/exhibition**. Check **MONITORING LIVE**, changing telemetry time, topology and enabled launch button. Click **Enter fullscreen**; audio is optional. Port 8080 is only the earlier preview.

If the dashboard is stale (already redeployed in this verification):

```sh
docker compose up -d --build --no-deps dashboard
```

## Rehearse / demonstrate

1. **Detection:** Launch → False Data Injection → Bus_5 → bias +0.15, scale 1 → launch. Allow about 20 seconds for critical GRID_DEVIATION and trust/decision evidence, then **STOP ATTACK**. Rejected isolation is a valid safety decision. STOP restoring voltage is not autonomous healing.
2. **Restoration, separately:** With all breakers closed, launch Breaker manipulation → L_line_0. **STOP immediately after OPEN appears, within approximately 2 seconds.** Wait 10–15 seconds for approved CLOSE and later CLOSED telemetry. Leaving the attacker running permits re-trips and can stall duplicate-suppressed proposals.
3. Wait for **GRID SECURED / Autonomous recovery completed**, then read the live timeline and `#/forensics`. This now requires the observed OPEN, safe correlated proposal, approval, CLOSE and later fresh canonical CLOSED telemetry with a converged solver and no attacker. STOP or a proposal alone is not success. Keep the same tab open during the demonstration; a refresh without the original OPEN evidence cannot certify the recovery.

## Stop / return to baseline

Use **STOP ATTACK**, or the emergency terminal command:

```sh
docker exec smart_grid_mqtt mosquitto_pub -t grid/attack -m '{"action":"STOP"}'
```

Repeat the telemetry check above: no active attack, all breakers CLOSED, solver converged. Retained alerts are historical evidence; do not delete them. Normal IEEE39 voltages above 1.05 p.u. no longer block the exhibition recovery predicate; existing topology warning colours remain unchanged.

## Quick recovery

- Missing MQTT / dependencies: `docker compose up -d mqtt redis postgres`; let producers reconnect, then repeat the telemetry check.
- Gateway disconnected: `docker compose restart gateway`; refresh the browser after health returns. In-memory timeline history may reset; saved evidence and container logs remain.
- Frozen telemetry: `docker compose logs --tail 30 digital_twin`; if paused, `docker unpause smart_grid_digital_twin`; otherwise `docker compose restart digital_twin`, then wait for model readiness.
- Command unconfirmed: do **not** keep clicking launch. Send emergency STOP, restore connectivity, and check actual attack state; a queued START may execute later.
- Breaker still OPEN after STOP: wait at least 30 seconds, then `docker compose restart recovery_policy` and recheck. This is an **operator-assisted retry**, not uninterrupted autonomous recovery.
- No verified recovery: say so; show the saved real rehearsal evidence in `docs/audit_evidence/2026-09-13-exhibition/`. Never present recorded evidence as live. Do not clear volumes, retrain models or relax safety checks.
