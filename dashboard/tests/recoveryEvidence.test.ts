import assert from "node:assert/strict";
import test from "node:test";
import { emptyRecoveryEvidence, reduceRecoveryEvidence } from "../src/recoveryEvidence.ts";

const proposal = (correlation_id: string, timestamp: number) => ({ command: "CLOSE", target: "L_line_0", correlation_id, source_telemetry_id: `${correlation_id}:frame`, timestamp, source: "AI_RL_PPO_DQN_CONSENSUS" });
const ingest = (items: Array<[any, any]>) => items.reduce((state, [topic, payload]) => reduceRecoveryEvidence(state, topic, payload), emptyRecoveryEvidence());

test("success requires a later matching telemetry frame", () => {
  const p = proposal("exp-1", 1000);
  const beforeTelemetry = { timestamp: 900, state: { breakers: { L_line_0: "CLOSED" } } };
  const dispatched = { ...p, timestamp: 1200, source: "ORCHESTRATOR_APPROVED" };
  let state = ingest([["grid/control/proposed", p], ["grid/control", dispatched], ["pypy/grid/telemetry", beforeTelemetry]]);
  assert.equal(state.attempts[0].outcome, "CONTROL DISPATCHED");
  state = reduceRecoveryEvidence(state, "pypy/grid/telemetry", { timestamp: 1300, state: { breakers: { L_line_0: "CLOSED" } } });
  assert.equal(state.attempts[0].outcome, "RECOVERY SUCCESS");
});

test("a later disagreeing frame is actuation not verified", () => {
  const p = proposal("exp-2", 2000);
  const state = ingest([["grid/control/proposed", p], ["grid/control", { ...p, timestamp: 2100, source: "ORCHESTRATOR_APPROVED" }], ["pypy/grid/telemetry", { timestamp: 2200, state: { breakers: { L_line_0: "OPEN" } } }]]);
  assert.equal(state.attempts[0].outcome, "ACTUATION NOT VERIFIED");
});

test("consecutive experiments retain independent correlation", () => {
  let state = reduceRecoveryEvidence(emptyRecoveryEvidence(), "grid/control/proposed", proposal("exp-a", 1000));
  state = reduceRecoveryEvidence(state, "grid/control/proposed", proposal("exp-b", 2000));
  assert.deepEqual(state.attempts.map((a) => a.correlationId), ["exp-b", "exp-a"]);
  state = reduceRecoveryEvidence(state, "grid/control", { ...proposal("exp-b", 2000), timestamp: 2100, source: "ORCHESTRATOR_APPROVED" });
  assert.equal(state.attempts[0].outcome, "CONTROL DISPATCHED");
  assert.equal(state.attempts[1].outcome, "MONITORING");
});

test("duplicate suppression is informational", () => {
  const p = proposal("exp-3", 3000);
  const state = ingest([["grid/control/proposed", p], ["grid/orchestrator/events", { ...p, timestamp: 3100, event: "REJECTION", reason: "Duplicate proposal suppressed; breaker state has not changed." }]]);
  assert.equal(state.attempts[0].outcome, "DUPLICATE SUPPRESSED");
  assert.equal(state.attempts[0].evidence.at(-1)?.summary, "Repeated recovery proposal was not resent.");
});

test("receipt time is fixed once; source telemetry time cannot stand in for dispatch", t => {
  t.mock.method(Date, "now", () => 2000);
  const p = proposal("receipt", 1000);
  const control = {command:"CLOSE",target:"L_line_0",correlation_id:"receipt",source:"ORCHESTRATOR_APPROVED",source_telemetry_timestamp:900};
  let state = ingest([["grid/control/proposed",p],["grid/control",control]]);
  assert.equal(state.attempts[0].evidence.at(-1)?.timestamp,2000);
  t.mock.method(Date,"now",()=>3000);
  state=reduceRecoveryEvidence(state,"pypy/grid/telemetry",{timestamp:1900,state:{breakers:{L_line_0:"CLOSED"}}});
  assert.equal(state.attempts[0].outcome,"CONTROL DISPATCHED");
  state=reduceRecoveryEvidence(state,"pypy/grid/telemetry",{timestamp:2100,state:{breakers:{L_line_0:"CLOSED"}}});
  assert.equal(state.attempts[0].outcome,"RECOVERY SUCCESS");
  assert.equal(Object.hasOwn(control,"timestamp"),false);
  state=reduceRecoveryEvidence(state,"pypy/grid/telemetry",{timestamp:2050,state:{breakers:{L_line_0:"OPEN"}}});
  assert.equal(state.canonicalTelemetry.timestamp,2100);
});
