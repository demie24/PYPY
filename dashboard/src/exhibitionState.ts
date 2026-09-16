import type { RecoveryEvidenceState } from './recoveryEvidence.ts';

export const evidenceTime = (value: unknown): number => {
  if (value == null || value === '') return 0;
  const number = Number(value);
  const time = Number.isFinite(number) ? number : Date.parse(String(value));
  return Number.isFinite(time) ? time : 0;
};
export const fresh = (payload: any, now: number, age = 30000) => {
  const time = evidenceTime(payload?.timestamp);
  return time > 0 && now - time >= -5000 && now - time < age;
};
export function exhibitionState(p: { connected: boolean; telemetry: any; alerts: any[]; threat: any; trustScores: any; aiFusion: any; recoveryEvidence: RecoveryEvidenceState }, now: number) {
  const live = p.connected && fresh(p.telemetry, now);
  const attack = live ? p.telemetry?.attack_status?.active_attack : null;
  const buses = Object.values(p.telemetry?.state?.buses || {}) as any[];
  const voltages = buses.map(b => b.voltage_pu).filter(v => typeof v === 'number' && Number.isFinite(v));
  const open = Object.values(p.telemetry?.state?.breakers || {}).filter(s => s === 'OPEN').length;
  // Match the established restoration safety envelope, not a nominal-voltage band:
  // core/self_healing/restoration_validator.py, Layer 6 voltage_safe (0.90–1.10).
  const stable = live && buses.length > 0 && voltages.length === buses.length && voltages.every(v => v >= .90 && v <= 1.10) && !open && p.telemetry?.solver_status?.converged === true;
  const detection = live ? p.alerts.find(a => fresh(a, now)) : null;
  // Only a recent, explicitly approved CLOSE followed by matching live telemetry
  // can produce the success presentation. STOP and OPEN are never recovery.
  const attempt = p.recoveryEvidence.attempts.find(a => a.evidence.some(e => now - evidenceTime(e.timestamp) < 60000 && evidenceTime(e.timestamp) <= now + 5000));
  const approved = !!attempt?.evidence.some(e => e.stage === 'APPROVED');
  const dispatched = approved && !!attempt?.dispatched;
  const dispatch = attempt?.evidence.filter(e => e.stage === 'CONTROL DISPATCHED').at(-1);
  const matches = (payload: any) => !!attempt?.correlationId && payload?.correlation_id === attempt.correlationId && payload?.target === attempt.target && payload?.command === 'CLOSE' && !!attempt.experimentId && payload?.experiment_id === attempt.experimentId && (!attempt.sourceTelemetryId || payload?.source_telemetry_id === attempt.sourceTelemetryId);
  const approval = attempt?.evidence.find(e => e.stage === 'APPROVED' && matches(e.payload) && e.timestamp <= (dispatch?.timestamp || 0));
  const sandbox = attempt?.proposal?.sandbox;
  const proposedBeforeApproval = attempt?.evidence.some(e => e.stage === 'PROPOSED' && e.payload === attempt.proposal && e.timestamp <= (approval?.timestamp || 0));
  const safeDecision = attempt?.proposal?.source === 'AI_RL_PPO_DQN_CONSENSUS' && matches(attempt?.proposal) && sandbox?.overall_safe === true && sandbox?.solver_converged === true && sandbox?.voltage_safe === true && sandbox?.thermal_safe === true && sandbox?.topology_valid === true && sandbox?.cascade_safe === true && sandbox?.finite_state === true;
  const canonical = p.recoveryEvidence.canonicalTelemetry;
  const lines = Object.keys(p.telemetry?.state?.lines || {});
  const complete = buses.length === 39 && lines.length === 46 && lines.every(line => p.telemetry?.state?.breakers?.[line] === 'CLOSED');
  const sameExperiment = !!attempt?.experimentId && attempt.experimentId === p.telemetry?.experiment_id;
  const observedOpen = attempt?.observedOpen;
  const openConfirmed = observedOpen?.state?.breakers?.[attempt?.target || ''] === 'OPEN' && observedOpen?.experiment_id === attempt?.experimentId && evidenceTime(observedOpen?.timestamp) < (dispatch?.timestamp || 0) && fresh(observedOpen, dispatch?.timestamp || 0, 60000);
  const laterCanonical = canonical === p.telemetry || (canonical?.timestamp === p.telemetry?.timestamp && canonical?.telemetry_id === p.telemetry?.telemetry_id && canonical?.experiment_id === p.telemetry?.experiment_id);
  const confirmed = attempt?.evidence.some(e => e.topic === 'pypy/grid/telemetry' && e.stage === 'TELEMETRY VERIFIED' && e.timestamp === evidenceTime(p.telemetry?.timestamp) && e.timestamp > (dispatch?.timestamp || 0) && e.payload?.state?.breakers?.[attempt.target] === 'CLOSED');
  const subsequentlyRejected = attempt?.evidence.some(e => e.stage === 'REJECTED' && e.timestamp >= (approval?.timestamp || 0));
  const verified = !!(live && stable && complete && p.telemetry?.attack_status?.active_attack === null && sameExperiment && attempt?.command === 'CLOSE' && openConfirmed && safeDecision && proposedBeforeApproval && approval && !subsequentlyRejected && dispatch && matches(dispatch.payload) && fresh(dispatch, now, 60000) && attempt.outcome === 'RECOVERY SUCCESS' && laterCanonical && confirmed);
  const rejected = attempt?.outcome === 'REJECTED';
  const headline = !p.connected ? 'CONNECTION LOST' : !live ? 'TELEMETRY UNAVAILABLE' : attack ? 'CYBER ATTACK IN PROGRESS' : verified ? 'GRID SECURED' : rejected ? 'UNSAFE RESPONSE BLOCKED' : dispatched && !verified ? 'VERIFYING GRID RESPONSE' : detection ? 'ANOMALY DETECTED' : stable ? 'GRID STABLE · MONITORING' : 'GRID REQUIRES ATTENTION';
  const stages = [
    { name: 'ATTACK', detail: !live ? 'State unavailable' : attack ? String(attack).replaceAll('_', ' ') : 'No active attack', state: attack ? 'danger' : 'idle' },
    { name: 'DETECT', detail: !live ? 'State unavailable' : detection ? detection.type || 'Anomaly received' : 'Watching telemetry', state: detection ? 'warning' : 'idle' },
    { name: 'TRUST', detail: live && fresh(p.trustScores, now) ? 'Assessment received' : 'Awaiting evidence', state: live && fresh(p.trustScores, now) ? 'info' : 'idle' },
    { name: 'DECIDE', detail: live && attempt ? rejected ? 'Response rejected' : approved ? 'Response approved' : 'Proposal received' : 'Awaiting proposal', state: live && attempt ? rejected ? 'warning' : 'info' : 'idle' },
    { name: 'HEAL', detail: live && dispatched ? 'Control dispatched' : 'Awaiting approved control', state: live && dispatched ? 'info' : 'idle' },
    { name: 'RECOVER', detail: verified ? 'Telemetry verified' : 'Awaiting verification', state: verified ? 'safe' : 'idle' },
  ];
  return { live, attack, stable, open, detection, attempt, verified, headline, stages, tone: !live ? 'idle' : attack ? 'danger' : verified || stable ? 'safe' : 'warning' };
}
