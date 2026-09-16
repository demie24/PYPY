#!/usr/bin/env python3
"""Separated, correlation-aware FDIA and physical-recovery verification."""

from __future__ import annotations
import argparse, json, math, threading, time, uuid
from pathlib import Path
from core.mqtt_compat import create_client

TOPICS = ("pypy/grid/telemetry", "grid/alerts", "grid/ai/lstm", "grid/ai/gnn", "grid/ai/stgnn", "grid/ai/pinn",
          "grid/ai/fusion", "grid/physics_validation", "grid/trust_scores", "grid/threat", "grid/ai/recovery/ppo",
          "grid/ai/recovery/dqn", "grid/ai/recovery_policy", "grid/control/proposed", "grid/orchestrator/events", "grid/control")


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--broker", default="localhost"); parser.add_argument("--port", type=int, default=1884)
    parser.add_argument("--output", type=Path, default=Path("evaluation/methodology_hardening/correlation_trace.json")); parser.add_argument("--timeout", type=float, default=35)
    args = parser.parse_args(); messages=[]; lock=threading.Lock()
    def connect(c,*a):
        for topic in TOPICS: c.subscribe(topic)
    def receive(c,u,m):
        try: value=json.loads(m.payload.decode())
        except Exception: return
        with lock: messages.append({"received_ns":time.time_ns(),"topic":m.topic,"payload":value})
    def wait(topic,predicate,timeout=None):
        end=time.monotonic()+(timeout or args.timeout)
        while time.monotonic()<end:
            with lock: found=next((row for row in reversed(messages) if row["topic"]==topic and predicate(row["payload"])),None)
            if found:return found
            time.sleep(.1)
        raise TimeoutError(topic)
    def publish(topic,payload): client.publish(topic,json.dumps(payload)); return payload
    client=create_client("pypy_methodology_hardening_trace");client.on_connect=connect;client.on_message=receive;client.connect(args.broker,args.port,60);client.loop_start()
    report={"schema_version":"pypy.methodology-e2e.v1","defence_mode":"blind","experiments":{}}
    try:
        time.sleep(22)
        publish("grid/attack",{"action":"STOP"});publish("grid/control",{"command":"RESET_ALARMS"})
        wait("pypy/grid/telemetry",lambda p:p.get("solver_status",{}).get("converged") is True and all(x=="CLOSED" for x in p.get("state",{}).get("breakers",{}).values()))

        # A: telemetry-only FDIA evidence. No breaker manipulation is part of this claim.
        exp_a="fdia-blind-"+uuid.uuid4().hex[:10]; corr_a="corr-"+uuid.uuid4().hex[:12]
        publish("grid/attack",{"action":"START","type":"FDIA","config":{"target":"Bus_5","bias":-.35,"scale":.7},"experiment_id":exp_a,"scenario_id":"FDIA_ONLY","correlation_id":corr_a})
        attacked=wait("pypy/grid/telemetry",lambda p:p.get("experiment_id")==exp_a and p.get("attack_status",{}).get("active_attack")=="FDIA")
        time.sleep(12)
        with lock: arows=[row for row in messages if row["payload"].get("experiment_id")==exp_a]
        source_id=attacked["payload"].get("telemetry_id")
        report["experiments"]["fdia_only"]={"experiment_id":exp_a,"correlation_id":corr_a,"result":"OBSERVED",
            "attack_telemetry_id":source_id,"breaker_outage_injected":False,
            "events_by_topic":{topic:sum(row["topic"]==topic for row in arows) for topic in TOPICS},
            "blind_alert_observed":any(row["topic"]=="grid/alerts" for row in arows),
            "maximum_blind_threat_score":max([row["payload"].get("threat_score",0) for row in arows if row["topic"]=="grid/threat"] or [0]),
            "model_source_references":sorted({row["payload"].get("source_telemetry_id") for row in arows if row["topic"].startswith("grid/ai/") and row["payload"].get("source_telemetry_id")}),
            "qualification":"Detection evidence only; no causal recovery claim."}
        publish("grid/attack",{"action":"STOP","experiment_id":exp_a,"correlation_id":corr_a});publish("grid/control",{"command":"RESET_ALARMS","experiment_id":exp_a,"correlation_id":corr_a});time.sleep(3)

        # B: independent physical outage and safety-gated recovery.
        exp_b="breaker-recovery-"+uuid.uuid4().hex[:10];corr_b="corr-"+uuid.uuid4().hex[:12]
        for target in ("L_line_0","L_line_1"):
            publish("grid/attack",{"action":"START","type":"BREAKER_MANIPULATION","config":{"target":target,"command":"OPEN"},"experiment_id":exp_b,"scenario_id":"BREAKER_RECOVERY","correlation_id":corr_b});time.sleep(1.2)
        outage=wait("pypy/grid/telemetry",lambda p:p.get("experiment_id")==exp_b and all(p.get("state",{}).get("breakers",{}).get(x)=="OPEN" for x in ("L_line_0","L_line_1")))
        publish("grid/attack",{"action":"STOP","experiment_id":exp_b,"correlation_id":corr_b})
        proposal=wait("grid/control/proposed",lambda p:p.get("experiment_id")==exp_b and p.get("source")=="AI_RL_PPO_DQN_CONSENSUS")
        sandbox=proposal["payload"].get("sandbox") or {}
        decision=wait("grid/orchestrator/events",lambda p:p.get("experiment_id")==exp_b and p.get("target")==proposal["payload"].get("target"))
        control=wait("grid/control",lambda p:p.get("experiment_id")==exp_b and p.get("target")==proposal["payload"].get("target"))
        restored=wait("pypy/grid/telemetry",lambda p:p.get("experiment_id")==exp_b and p.get("state",{}).get("breakers",{}).get(proposal["payload"].get("target"))=="CLOSED" and p.get("timestamp",0)>decision["payload"].get("timestamp",0))
        report["experiments"]["breaker_recovery"]={"experiment_id":exp_b,"correlation_id":corr_b,"outage_telemetry_id":outage["payload"].get("telemetry_id"),
            "proposal":proposal["payload"],"orchestrator":decision["payload"],"control":control["payload"],
            "post_command_telemetry_id":restored["payload"].get("telemetry_id"),"post_command_solver_status":restored["payload"].get("solver_status"),
            "sandbox_explicit_gate":all(sandbox.get(k) is True for k in ("solver_converged","finite_state","voltage_safe","thermal_safe","cascade_safe","topology_valid","overall_safe")),
            "causal_reference_preserved":all(x["payload"].get("correlation_id")==corr_b for x in (proposal,decision,control,restored)),
            "strict_approval_before_state":restored["payload"].get("timestamp",0)>decision["payload"].get("timestamp",0)}
        report["result"]="PASS" if report["experiments"]["breaker_recovery"]["sandbox_explicit_gate"] and report["experiments"]["breaker_recovery"]["causal_reference_preserved"] else "FAIL"
    finally:
        publish("grid/attack",{"action":"STOP"});time.sleep(1)
        for target in ("L_line_0","L_line_1"):publish("grid/control",{"command":"CLOSE","target":target,"source":"METHODOLOGY_CLEANUP"})
        publish("grid/control",{"command":"RESET_ALARMS"});time.sleep(2);client.loop_stop();client.disconnect()
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,indent=2,allow_nan=False)+"\n");print(json.dumps(report,allow_nan=False));return 0 if report.get("result")=="PASS" else 1


if __name__=="__main__":raise SystemExit(main())
