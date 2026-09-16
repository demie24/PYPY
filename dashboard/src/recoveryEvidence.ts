export type EvidenceTopic =
  | "grid/alerts" | "grid/control/proposed" | "grid/ai/recovery_policy"
  | "grid/orchestrator/events" | "grid/control" | "pypy/grid/telemetry" | "grid/telemetry";

export type RecoveryStage = "DETECTED" | "PROPOSED" | "SAFETY CHECKED" | "APPROVED" | "REJECTED" | "DUPLICATE SUPPRESSED" | "CONTROL DISPATCHED" | "TELEMETRY VERIFIED";
export type RecoveryOutcome = "MONITORING" | "ACTIVE ATTACK — STATE CONTESTED" | "REJECTED" | "DUPLICATE SUPPRESSED" | "CONTROL DISPATCHED" | "ACTUATION NOT VERIFIED" | "RECOVERY SUCCESS";

export interface RecoveryEvidenceItem { topic: EvidenceTopic; stage: RecoveryStage; timestamp: number; payload: any; summary: string; }
export interface RecoveryAttempt {
  key: string; correlationId: string; sourceTelemetryId?: string; experimentId?: string; scenarioId?: string;
  target: string; command: string; initialState?: string; finalState?: string; source?: string;
  outcome: RecoveryOutcome; sandbox?: any; decision?: any; proposal?: any; dispatched?: any;
  evidence: RecoveryEvidenceItem[];
  observedOpen?: any;
}
export interface RecoveryEvidenceState { attempts: RecoveryAttempt[]; activeAttack: any | null; canonicalTelemetry?: any; }

export const emptyRecoveryEvidence = (): RecoveryEvidenceState => ({ attempts: [], activeAttack: null });
const ts = (p: any) => Number(p?.timestamp || p?._evidence_timestamp || p?.source_telemetry_timestamp || Date.now());
const id = (p: any) => String(p?.correlation_id || p?.source_telemetry_id || p?.telemetry_id || "");
const duplicate = (p: any) => /duplicate proposal suppressed/i.test(String(p?.reason || p?.event || ""));
const isApprovedControl = (p: any) => String(p?.source || "").toUpperCase() === "ORCHESTRATOR_APPROVED" || p?.orchestrator_approved === true;
const desiredState = (command: string) => command.toUpperCase() === "CLOSE" ? "CLOSED" : command.toUpperCase() === "OPEN" ? "OPEN" : command.toUpperCase();

function findAttempt(state: RecoveryEvidenceState, payload: any, allowTargetFallback = true) {
  const correlation = id(payload);
  if (correlation) {
    const exact = state.attempts.findIndex((a) => a.correlationId === correlation);
    if (exact >= 0) return exact;
    return -1;
  }
  if (allowTargetFallback && payload?.target) return state.attempts.findIndex((a) => a.target === payload.target && !["RECOVERY SUCCESS", "REJECTED"].includes(a.outcome));
  return -1;
}

function append(attempt: RecoveryAttempt, item: RecoveryEvidenceItem): RecoveryAttempt {
  if (attempt.evidence.some((e) => e.topic === item.topic && e.timestamp === item.timestamp && e.stage === item.stage)) return attempt;
  return { ...attempt, evidence: [...attempt.evidence, item].sort((a, b) => a.timestamp - b.timestamp) };
}

export function reduceRecoveryEvidence(state: RecoveryEvidenceState, topic: EvidenceTopic, payload: any): RecoveryEvidenceState {
  const next: RecoveryEvidenceState = { ...state, attempts: [...state.attempts] };
  if (topic === "pypy/grid/telemetry" || topic === "grid/telemetry") {
    if (topic === "pypy/grid/telemetry") {
      if (Number(payload?.timestamp) <= Number(state.canonicalTelemetry?.timestamp)) return state;
      next.canonicalTelemetry = payload;
    }
    next.activeAttack = payload?.attack_status?.active_attack ? payload.attack_status : null;
    const frameTime = ts(payload);
    next.attempts = next.attempts.map((attempt) => {
      if (topic === "pypy/grid/telemetry" && !attempt.dispatched && payload?.state?.breakers?.[attempt.target] === "OPEN") attempt = { ...attempt, observedOpen: payload };
      // The evidence item freezes the real source/receipt time once at ingestion.
      // Re-evaluating ts(dispatched) would move a timestamp-less command forever.
      const dispatchTime = attempt.evidence.filter(e => e.stage === "CONTROL DISPATCHED").at(-1)?.timestamp;
      if (!attempt.dispatched || !dispatchTime || frameTime <= dispatchTime) return next.activeAttack && attempt.target in (next.activeAttack.compromised_nodes || {}) ? { ...attempt, outcome: "ACTIVE ATTACK — STATE CONTESTED" } : attempt;
      const observed = payload?.state?.breakers?.[attempt.target];
      if (!observed) return attempt;
      const verified = observed === desiredState(attempt.command);
      const evidence = append(attempt, { topic, stage: "TELEMETRY VERIFIED", timestamp: frameTime, payload, summary: `${attempt.target} telemetry ${observed}` });
      return { ...evidence, finalState: observed, outcome: verified ? "RECOVERY SUCCESS" : "ACTUATION NOT VERIFIED" };
    });
    return next;
  }

  if (topic === "grid/control/proposed") {
    const target = String(payload?.target || "SYSTEM"); const command = String(payload?.command || payload?.action || "ACTION");
    const correlationId = id(payload) || `uncorrelated:${target}:${ts(payload)}`;
    const key = `${correlationId}:${target}:${command}`;
    const correlated = findAttempt(next, payload);
    const prior = correlated >= 0 ? correlated : next.attempts.findIndex((a) => a.key === key);
    const base: RecoveryAttempt = prior >= 0 ? next.attempts[prior] : { key, correlationId, sourceTelemetryId: payload?.source_telemetry_id, experimentId: payload?.experiment_id, scenarioId: payload?.scenario_id, target, command, initialState: payload?.initial_state || "OPEN", source: payload?.source, outcome: "MONITORING", evidence: [] };
    const observedOpen = base.observedOpen || (next.canonicalTelemetry?.state?.breakers?.[target] === "OPEN" ? next.canonicalTelemetry : undefined);
    // PPO/DQN proposals also omit a top-level timestamp; their sandbox carries
    // the real safety-decision time. Keep it ahead of the subsequent approval.
    const proposalTime = Number(payload?.timestamp || payload?.sandbox?.timestamp || ts(payload));
    // Policy assessments precede the actual proposal and can reference older
    // input frames. Bind actuation verification to the proposal's real frame ID.
    const updated = append({ ...base, observedOpen, sourceTelemetryId: payload?.source_telemetry_id || base.sourceTelemetryId, proposal: payload }, { topic, stage: "PROPOSED", timestamp: proposalTime, payload, summary: `${command} ${target} proposed` });
    if (prior >= 0) next.attempts[prior] = updated; else next.attempts.unshift(updated);
    return { ...next, attempts: next.attempts.slice(0, 12) };
  }

  let index = findAttempt(next, payload);
  if (index < 0 && topic === "grid/ai/recovery_policy" && payload?.target && payload?.sandbox) {
    const correlationId = id(payload) || `unproposed:${payload.target}:${ts(payload)}`;
    next.attempts.unshift({ key: `${correlationId}:${payload.target}:CLOSE`, correlationId, sourceTelemetryId: payload.source_telemetry_id, experimentId: payload.experiment_id, scenarioId: payload.scenario_id, target: String(payload.target), command: "CLOSE", initialState: "OPEN", source: "AI_RL_PPO_DQN_CONSENSUS", outcome: "MONITORING", evidence: [] });
    index = 0;
  }
  if (index < 0) return next;
  let attempt = next.attempts[index];
  if (topic === "grid/ai/recovery_policy") {
    const sandbox = payload?.sandbox || payload?.recovery?.sandbox;
    if (sandbox) attempt = append({ ...attempt, sandbox, source: payload?.source || "AI_RL_PPO_DQN_CONSENSUS" }, { topic, stage: "SAFETY CHECKED", timestamp: Number(sandbox.timestamp || ts(payload)), payload: sandbox, summary: sandbox.overall_safe ?? sandbox.is_safe ? "Sandbox SAFE" : `Sandbox REJECTED: ${sandbox.rejection_reason || "safety condition failed"}` });
  } else if (topic === "grid/orchestrator/events") {
    const isDup = duplicate(payload); const approved = payload?.event === "APPROVAL" || payload?.decision === "APPROVED" || payload?.approved === true;
    attempt = append({ ...attempt, decision: payload, outcome: isDup ? "DUPLICATE SUPPRESSED" : approved ? attempt.outcome : "REJECTED" }, { topic, stage: isDup ? "DUPLICATE SUPPRESSED" : approved ? "APPROVED" : "REJECTED", timestamp: ts(payload), payload, summary: isDup ? "Repeated recovery proposal was not resent." : `${approved ? "Approved" : "Rejected"}: ${payload?.reason || "decision recorded"}` });
  } else if (topic === "grid/control" && isApprovedControl(payload)) {
    // source_telemetry_timestamp identifies the input frame, not actuation time.
    const dispatchTime = Number(payload?.timestamp || payload?._evidence_timestamp || Date.now());
    attempt = append({ ...attempt, dispatched: payload, outcome: "CONTROL DISPATCHED" }, { topic, stage: "CONTROL DISPATCHED", timestamp: dispatchTime, payload, summary: `${attempt.command} ${attempt.target} dispatched by orchestrator` });
  } else if (topic === "grid/alerts") {
    attempt = append(attempt, { topic, stage: "DETECTED", timestamp: ts(payload), payload, summary: `${payload?.type || "Anomaly"} detected at ${payload?.suspect_node || attempt.target}` });
  }
  next.attempts[index] = attempt;
  return next;
}
