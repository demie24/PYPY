import { useEffect, useMemo, useState, type ReactNode } from "react";
import {
  Activity, AlertTriangle, ArrowRight, BarChart3, Bell, BrainCircuit,
  Check, CheckCircle2, ChevronRight, CircleOff, Clock3, Cpu, FileSearch,
  Gauge, HeartPulse, HelpCircle, Home, Menu, Network, Play, Radio, RefreshCw,
  Search, Settings, Shield, ShieldAlert, ShieldCheck, Sparkles,
  Square, Target, TerminalSquare, TowerControl, User, Workflow,
  Wrench, X, Zap,
} from "lucide-react";
import type { RecoveryEvidenceState } from "../recoveryEvidence.ts";
import { ExhibitionMode } from './ExhibitionMode.tsx';

export type ControlPage =
  | "overview" | "grid" | "detection" | "decision" | "recovery"
  | "simulation" | "forensics" | "health" | "reports" | "settings";

export type ControlCenterProps = {
  connected: boolean;
  telemetry: any;
  totalLoadMw: number | null;
  threat: any;
  alerts: any[];
  events: any[];
  activeAttack: string | null;
  recovery: any;
  proposal: any;
  orchestratorEvent: any;
  lastControl: any;
  recoveryEvidence: RecoveryEvidenceState;
  aiStatuses: Record<string, any>;
  aiFusion: any;
  physicsValidation: any;
  trustScores: any;
  recommendedActions: any;
  preRl: any;
  flisrState: string;
  flisrAuto: boolean;
  lastUpdate: string;
  messageRate: number;
  wsLatency: number;
  selectedGrid: string;
  topology: ReactNode;
  onToggleBreaker: (lineId: string) => void;
  onSendControl: (payload: any) => void;
  onSendMessage: (message: { topic: string; payload: any }) => void;
  onSelectGrid: (grid: string) => void;
  onLogout?: () => void;
};
type Props = ControlCenterProps;

type Tone = "safe" | "info" | "warning" | "danger" | "ai" | "muted";

const nav: Array<{ id: ControlPage; label: string; short: string; icon: typeof Home }> = [
  { id: "overview", label: "Overview", short: "System at a glance", icon: Home },
  { id: "grid", label: "Live Grid", short: "Digital Twin", icon: TowerControl },
  { id: "detection", label: "Cyber Detection", short: "Threat evidence", icon: ShieldAlert },
  { id: "decision", label: "AI Decision", short: "Governed reasoning", icon: BrainCircuit },
  { id: "recovery", label: "Self-Healing", short: "FLISR recovery", icon: RefreshCw },
  { id: "simulation", label: "Attack Simulation", short: "Cyber range", icon: Target },
  { id: "forensics", label: "Logs & Forensics", short: "Incident records", icon: FileSearch },
  { id: "health", label: "System Health", short: "Services & models", icon: HeartPulse },
  { id: "reports", label: "Reports", short: "Operational summary", icon: BarChart3 },
  { id: "settings", label: "Settings", short: "Workspace controls", icon: Settings },
];

const modelInfo = [
  ["lstm", "LSTM", "Temporal anomaly detection"],
  ["gnn", "GNN", "Topology analysis"],
  ["stgnn", "ST-GNN", "Spatio-temporal analysis"],
  ["pinn", "PINN", "Physics diagnostic validation"],
  ["ppo", "PPO", "Recovery proposal generation"],
  ["dqn", "DQN", "Recovery proposal comparison"],
] as const;

const pageCopy: Record<ControlPage, { eyebrow: string; title: string; description: string }> = {
  overview: { eyebrow: "Command centre", title: "Grid security overview", description: "See the grid, threat evidence, AI decision, and recovery state in one place." },
  grid: { eyebrow: "Digital Twin", title: "Live grid", description: "Inspect real bus, branch, breaker, and power-flow telemetry." },
  detection: { eyebrow: "Cyber defence", title: "Cyber detection", description: "Understand active threats, affected assets, and detector evidence without digging through raw logs." },
  decision: { eyebrow: "Governed intelligence", title: "AI decision", description: "Follow evidence fusion, learning-agent proposals, safety validation, and the final orchestrator decision." },
  recovery: { eyebrow: "Safety-gated control", title: "Self-healing (FLISR)", description: "Review isolation, reconfiguration, validation, and restoration status before acting." },
  simulation: { eyebrow: "Isolated cyber range", title: "Attack simulation", description: "Run supported attack scenarios and observe detection and recovery without confusing them with live actions." },
  forensics: { eyebrow: "Audit trail", title: "Logs & forensics", description: "Search and filter the live event and alert record." },
  health: { eyebrow: "Operational readiness", title: "System health", description: "Check the connection, Digital Twin, AI models, and safety services from real signals." },
  reports: { eyebrow: "Situation reporting", title: "Reports", description: "Review a concise live operational summary and current evidence availability." },
  settings: { eyebrow: "Workspace", title: "Settings", description: "Configure frontend display preferences without changing backend contracts." },
};

const asNumber = (value: unknown): number | null => {
  if (value === null || value === undefined || value === "" || typeof value === "boolean") return null;
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
};

const formatTime = (value: unknown) => {
  if (!value) return "Time unavailable";
  const raw = Number(value);
  const date = new Date(Number.isFinite(raw) ? raw : String(value));
  return Number.isNaN(date.getTime()) ? "Time unavailable" : date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
};

const severityTone = (severity: unknown): Tone => {
  const value = String(severity || "").toUpperCase();
  if (["CRITICAL", "SEVERE"].includes(value)) return "danger";
  if (["HIGH", "WARNING", "WARN", "MEDIUM"].includes(value)) return "warning";
  if (["NORMAL", "NOMINAL", "RESOLVED", "HEALTHY", "SAFE"].includes(value)) return "safe";
  return "info";
};

function StatusBadge({ tone = "muted", children }: { tone?: Tone; children: ReactNode }) {
  return <span className={`pypy-badge tone-${tone}`}><span aria-hidden="true" />{children}</span>;
}

function SectionCard({ title, description, icon, action, className = "", children }: {
  title: string; description?: string; icon?: ReactNode; action?: ReactNode; className?: string; children: ReactNode;
}) {
  return (
    <section className={`pypy-card ${className}`}>
      <header className="pypy-card-head">
        <div className="pypy-card-title-wrap">{icon && <span className="pypy-card-icon">{icon}</span>}<div><h2>{title}</h2>{description && <p>{description}</p>}</div></div>
        {action}
      </header>
      {children}
    </section>
  );
}

function EmptyState({ icon = <Radio />, title, text }: { icon?: ReactNode; title: string; text: string }) {
  return <div className="pypy-empty">{icon}<strong>{title}</strong><p>{text}</p></div>;
}

function MetricCard({ label, value, detail, icon, tone = "info", progress }: {
  label: string; value: ReactNode; detail: string; icon: ReactNode; tone?: Tone; progress?: number | null;
}) {
  return (
    <article className={`pypy-metric tone-${tone}`}>
      <span className="pypy-metric-icon">{icon}</span><div className="pypy-metric-copy"><p>{label}</p><strong>{value}</strong><small>{detail}</small>
      {progress !== undefined && progress !== null && <div className="pypy-progress" aria-label={`${label}: ${progress.toFixed(0)} percent`}><span style={{ width: `${Math.max(0, Math.min(100, progress))}%` }} /></div>}</div>
    </article>
  );
}

function ConnectionNotice({ connected }: { connected: boolean }) {
  if (connected) return null;
  return <div className="pypy-notice tone-warning" role="status"><CircleOff /><div><strong>Live telemetry temporarily unavailable</strong><p>PYPY is reconnecting to the existing WebSocket. Values are shown as unavailable rather than estimated.</p></div></div>;
}

function ThreatMeter({ threat, activeAttack }: { threat: any; activeAttack: string | null }) {
  const score = asNumber(threat?.threat_score);
  const bounded = Math.max(0, Math.min(100, score ?? 0));
  const severity = threat?.severity || (score === null ? "Unavailable" : bounded >= 76 ? "Critical" : bounded >= 51 ? "High" : bounded >= 26 ? "Medium" : "Low");
  return (
    <div className="pypy-threat-meter">
      <div className="pypy-gauge" style={{ "--risk": `${bounded * 3.6}deg` } as React.CSSProperties}><div><strong>{score === null ? "—" : Math.round(score)}</strong><span>/100</span></div></div>
      <div className="pypy-threat-copy"><StatusBadge tone={score === null ? "muted" : severityTone(severity)}>{String(severity)}</StatusBadge><h3>{activeAttack ? String(activeAttack).replaceAll("_", " ") : "No attack reported"}</h3><dl><div><dt>Source</dt><dd>{threat?.source || "Threat engine"}</dd></div><div><dt>Confidence</dt><dd>{asNumber(threat?.confidence) === null ? "Unavailable" : `${((asNumber(threat?.confidence) || 0) * 100).toFixed(0)}%`}</dd></div><div><dt>Latest detection</dt><dd>{formatTime(threat?.timestamp)}</dd></div></dl></div>
    </div>
  );
}

function IncidentFeed({ alerts, events, limit = 6 }: { alerts: any[]; events: any[]; limit?: number }) {
  const incidents = useMemo(() => [
    ...(alerts || []).map((item) => ({ ...item, title: item.type || item.event || "Anomaly detected", asset: item.suspect_node || item.affected_asset || item.source || "Grid", kind: "alert" })),
    ...(events || []).map((item) => ({ ...item, title: item.event || item.type || "Grid event", asset: item.target || item.affected_asset || item.source || "Digital Twin", kind: "event" })),
  ].sort((a, b) => Number(b.timestamp || 0) - Number(a.timestamp || 0)).slice(0, limit), [alerts, events, limit]);
  if (!incidents.length) return <EmptyState icon={<CheckCircle2 />} title="No incidents received" text="New live alerts and grid events will appear here." />;
  return <div className="pypy-incident-list">{incidents.map((item, index) => { const tone = severityTone(item.severity || (item.kind === "alert" ? "WARNING" : "INFO")); return <article className="pypy-incident" key={`${item.timestamp}-${index}`}><span className={`pypy-incident-symbol tone-${tone}`}>{tone === "danger" ? <ShieldAlert /> : tone === "warning" ? <AlertTriangle /> : tone === "safe" ? <CheckCircle2 /> : <Activity />}</span><div><strong>{item.title}</strong><p>{item.asset}</p></div><div className="pypy-incident-meta"><StatusBadge tone={tone}>{item.status || item.severity || (item.kind === "alert" ? "Alert" : "Info")}</StatusBadge><time>{formatTime(item.timestamp)}</time></div></article>; })}</div>;
}

function ModelGrid({ statuses, preRl }: { statuses: Record<string, any>; preRl: any }) {
  const rlStatus = preRl?.model_status || preRl?.status;
  return <div className="pypy-model-grid">{modelInfo.map(([id, name, label]) => {
    const payload = statuses?.[id] || ((id === "ppo" || id === "dqn") ? (rlStatus ? { status: rlStatus } : null) : null);
    const ready = payload?.ready === true || ["online", "active", "ready", "healthy", "loaded"].includes(String(payload?.status || "").toLowerCase());
    const status = payload ? (ready ? "Active" : payload?.status || "Awaiting signal") : "Unavailable";
    const metricEntry = Object.entries(payload || {}).find(([key, value]) => !["ready", "status", "timestamp", "model"].includes(key) && ["number", "string"].includes(typeof value));
    return <article className="pypy-model" key={id}><span><BrainCircuit /></span><div><div><strong>{name}</strong><StatusBadge tone={ready ? "safe" : payload ? "warning" : "muted"}>{String(status)}</StatusBadge></div><p>{label}</p><small>{metricEntry ? `${metricEntry[0].replaceAll("_", " ")}: ${String(metricEntry[1])}` : "No live metric supplied"}</small></div></article>;
  })}</div>;
}

function LiveEventConsole({ props }: { props: Props }) {
  const filters = ["All","Attack","Detection","AI","Sandbox","Orchestrator","Control","Telemetry"];
  const [filter,setFilter]=useState("All");
  const rows=useMemo(()=>[
    ...props.alerts.map(payload=>({category:"Detection",timestamp:payload.timestamp,summary:`${payload.type || "Detection"} · ${payload.suspect_node || "grid"}`,payload})),
    ...props.events.map(payload=>({category:/attack/i.test(`${payload.source} ${payload.event}`)?"Attack":"Telemetry",timestamp:payload.timestamp,summary:payload.event || "Grid event",payload})),
    ...props.recoveryEvidence.attempts.flatMap(a=>a.evidence.map(e=>({category:e.stage==="SAFETY CHECKED"?"Sandbox":e.stage==="APPROVED"||e.stage==="REJECTED"||e.stage==="DUPLICATE SUPPRESSED"?"Orchestrator":e.stage==="CONTROL DISPATCHED"?"Control":e.stage==="TELEMETRY VERIFIED"?"Telemetry":"AI",timestamp:e.timestamp,summary:e.summary,payload:e.payload})))
  ].sort((a,b)=>Number(b.timestamp)-Number(a.timestamp)).filter(r=>filter==="All"||r.category===filter).slice(0,20),[props.alerts,props.events,props.recoveryEvidence,filter]);
  return <SectionCard title="Live event console" description="Human-readable evidence with expandable raw JSON." icon={<TerminalSquare />} action={<div className="pypy-console-filters">{filters.map(f=><button className={filter===f?"active":""} onClick={()=>setFilter(f)} key={f}>{f}</button>)}</div>}><div className="pypy-console">{rows.map((r,i)=><details key={`${r.timestamp}-${i}`}><summary><StatusBadge tone={r.category==="Attack"?"danger":r.category==="Sandbox"||r.category==="Orchestrator"?"ai":"info"}>{r.category}</StatusBadge><time>{formatTime(r.timestamp)}</time><span>{r.summary}</span></summary><pre>{JSON.stringify(r.payload,null,2)}</pre></details>)}</div></SectionCard>;
}

function DecisionFlow({ threat, proposal, orchestratorEvent: orchestrator, lastControl, recovery, activeAttack }: Pick<Props, "threat" | "proposal" | "orchestratorEvent" | "lastControl" | "recovery" | "activeAttack">) {
  const approved = orchestrator?.event === "APPROVAL" || orchestrator?.decision === "APPROVED" || orchestrator?.approved === true;
  const steps = [
    ["Threat", activeAttack || (threat ? `Score ${threat.threat_score ?? "received"}` : "Monitoring"), !!activeAttack || !!threat, ShieldAlert],
    ["AI evaluation", proposal ? "Proposal received" : "Awaiting evidence", !!proposal, BrainCircuit],
    ["Recommendation", proposal ? `${proposal.command || proposal.action || "Action"} ${proposal.target || ""}` : "No proposal", !!proposal, Sparkles],
    ["Safety validation", recovery ? "Sandbox evidence received" : "Awaiting evidence", !!recovery, ShieldCheck],
    ["Orchestrator", orchestrator?.event || orchestrator?.decision || "Awaiting decision", approved, Workflow],
    ["Latest control", lastControl?.command ? `${lastControl.command} ${lastControl.target || ""}` : "No execution", !!lastControl, RefreshCw],
  ] as const;
  return <div className="pypy-decision-flow">{steps.map(([label, detail, done, Icon], index) => <div className="pypy-decision-wrap" key={label}><article className={done ? "is-done" : ""}><span>{done ? <Check /> : <Icon />}</span><strong>{label}</strong><small>{detail}</small></article>{index < steps.length - 1 && <ChevronRight />}</div>)}</div>;
}

function OverviewPage(props: Props) {
  const buses = props.telemetry?.state?.buses || {};
  const breakers = props.telemetry?.state?.breakers || {};
  const voltages = Object.values(buses).map((bus: any) => asNumber(bus.voltage_pu)).filter((value): value is number => value !== null);
  const load = asNumber(props.totalLoadMw);
  const openBreakers = Object.values(breakers).filter((value) => value === "OPEN").length;
  const criticalAlerts = props.alerts.filter((alert) => String(alert.severity).toUpperCase() === "CRITICAL").length;
  const readyModels = modelInfo.filter(([id]) => props.aiStatuses?.[id]?.ready === true).length;
  const minimumVoltage = voltages.length ? Math.min(...voltages) : null;
  const gridTone: Tone = props.activeAttack ? "danger" : openBreakers || (minimumVoltage !== null && minimumVoltage < .95) ? "warning" : props.telemetry ? "safe" : "muted";
  return <>
    <ConnectionNotice connected={props.connected} />
    <div className="pypy-metric-grid five">
      <MetricCard label="Grid status" value={props.telemetry ? (props.activeAttack ? "Critical" : openBreakers || (minimumVoltage !== null && minimumVoltage < .95) ? "Degraded" : minimumVoltage !== null ? "Stable" : "Unavailable") : "Unavailable"} detail={minimumVoltage === null ? "Waiting for bus telemetry" : `Minimum voltage ${minimumVoltage.toFixed(3)} p.u.`} icon={<ShieldCheck />} tone={gridTone} progress={minimumVoltage === null ? null : Math.min(100, minimumVoltage * 100)} />
      <MetricCard label="Active power load" value={load !== null ? `${load.toFixed(1)} MW` : "Unavailable"} detail={`${Object.keys(buses).length || "No"} buses reporting`} icon={<Zap />} tone="info" />
      <MetricCard label="Threat level" value={props.threat?.severity || "Unavailable"} detail={props.threat?.threat_score == null ? "No current threat evidence" : `Threat score ${props.threat.threat_score} / 100`} icon={<Shield />} tone={severityTone(props.threat?.severity)} />
      <MetricCard label="Active alerts" value={props.connected ? props.alerts.length : "Unavailable"} detail={`${criticalAlerts} critical records received`} icon={<Bell />} tone={criticalAlerts ? "danger" : props.alerts.length ? "warning" : "safe"} />
      <MetricCard label="AI live readiness" value={Object.keys(props.aiStatuses).length ? `${readyModels}/${modelInfo.length}` : "Unavailable"} detail="Models confirmed ready by live signals" icon={<BrainCircuit />} tone={readyModels ? "ai" : "muted"} />
    </div>
    <div className="pypy-overview-grid">
      <SectionCard className="pypy-topology-card" title="Grid Topology — Digital Twin" description="Live topology semantics, breaker state, attack context, and recovery paths." icon={<Network />} action={<div className="pypy-legend"><span><i className="safe" />Normal</span><span><i className="warning" />Warning</span><span><i className="danger" />Critical</span><span><i className="offline" />Isolated</span></div>}><div className="pypy-topology">{Object.keys(buses).length && Object.keys(props.telemetry?.state?.lines || {}).length ? props.topology : <EmptyState title="Waiting for Digital Twin" text="Waiting for bus and line telemetry from the Digital Twin. No asset state is inferred." />}</div></SectionCard>
      <SectionCard title="Recent incidents" description="Latest alerts and grid events." icon={<Clock3 />}><IncidentFeed alerts={props.alerts} events={props.events} limit={6} /></SectionCard>
    </div>
    <div className="pypy-bottom-grid">
      <SectionCard title="Self-healing recommendation" description="Review the proposed action and safety evidence." icon={<RefreshCw />}>
        <div className="pypy-recommendation"><span><ShieldCheck /></span><div><StatusBadge tone={props.proposal ? "ai" : "muted"}>{props.proposal ? "Proposal available" : "No proposal received"}</StatusBadge><h3>{props.proposal ? "Review the recommended grid control" : "Waiting for a recommendation"}</h3><p>{props.proposal ? `${props.proposal.command || props.proposal.action || "Action"} ${props.proposal.target || ""}` : "No current action evidence has been supplied."}</p><p>{props.orchestratorEvent?.reason || "Validation and orchestrator approval remain required."}</p></div></div>
        <a className="pypy-text-link" href="#/recovery">Review recovery evidence <ArrowRight size={16} /></a>
      </SectionCard>
      <SectionCard className="pypy-overview-flow" title="AI decision flow" description="Follow the evidence from detection to control." icon={<Workflow />}><DecisionFlow {...props} /></SectionCard>
    </div>
    <SectionCard title="System signals" description="Evidence availability; receipt alone does not establish service health." icon={<HeartPulse />}><div className="pypy-service-grid">{[["Browser connection", props.connected], ["Digital Twin telemetry", !!props.telemetry], ["AI fusion evidence", !!props.aiFusion], ["Recovery evidence", !!props.recovery]].map(([label, available]) => <article key={String(label)}><span className={available ? "live" : "waiting"}>{available ? <Check /> : <Radio />}</span><div><strong>{String(label)}</strong><p>{available ? "Signal received" : "Unavailable"}</p></div></article>)}</div></SectionCard>
    <LiveEventConsole props={props} />

  </>;
}

function GridPage(props: Props) {
  const buses = props.telemetry?.state?.buses || {}; const lines = props.telemetry?.state?.lines || {}; const breakers = props.telemetry?.state?.breakers || {};
  const values = Object.values(buses) as any[];
  const voltages = values.map((bus) => asNumber(bus.voltage_pu)).filter((v): v is number => v !== null);
  const frequencies = values.map((bus) => asNumber(bus.frequency_hz)).filter((v): v is number => v !== null);
  const currents = Object.values(lines).map((line: any) => asNumber(line.current_pu ?? line.current)).filter((v): v is number => v !== null);
  return <><ConnectionNotice connected={props.connected} /><div className="pypy-metric-grid four"><MetricCard label="Bus voltage range" value={voltages.length ? `${Math.min(...voltages).toFixed(3)}–${Math.max(...voltages).toFixed(3)} p.u.` : "Unavailable"} detail={`${voltages.length} buses reporting voltage`} icon={<Activity />} tone="info" /><MetricCard label="System frequency" value={frequencies.length ? `${(frequencies.reduce((a,b)=>a+b,0)/frequencies.length).toFixed(2)} Hz` : "Unavailable"} detail="Average of received bus fields" icon={<Gauge />} tone="safe" /><MetricCard label="Maximum branch current" value={currents.length ? `${Math.max(...currents).toFixed(3)} p.u.` : "Unavailable"} detail={`${currents.length} branch measurements`} icon={<Zap />} tone="warning" /><MetricCard label="Breaker position" value={Object.keys(breakers).length ? `${Object.values(breakers).filter((v)=>v === "OPEN").length} open` : "Unavailable"} detail={`${Object.keys(breakers).length} states received`} icon={<Network />} tone={Object.values(breakers).some((v)=>v === "OPEN") ? "warning" : "safe"} /></div><SectionCard className="pypy-grid-full" title={`${props.selectedGrid.toUpperCase()} live topology`} description="Use the topology controls to zoom, pan, fit, inspect assets, and operate supported breakers." icon={<TowerControl />} action={<StatusBadge tone={props.connected ? "safe" : "warning"}>{props.connected ? props.telemetry ? "Telemetry received" : "Waiting for telemetry" : "Disconnected"}</StatusBadge>}><div className="pypy-topology">{Object.keys(buses).length && Object.keys(lines).length ? props.topology : <EmptyState title="Waiting for Digital Twin" text="Bus and line telemetry is unavailable. The topology will appear when measurements arrive." />}</div></SectionCard></>;
}

function DetectionPage(props: Props) {
  const affected = props.threat?.affected_nodes || props.threat?.affected_assets || props.telemetry?.attack_status?.compromised_nodes;
  return <><ConnectionNotice connected={props.connected} /><div className="pypy-split"><SectionCard title="Current threat" description="Severity is shown in text as well as colour." icon={<ShieldAlert />}><ThreatMeter threat={props.threat} activeAttack={props.activeAttack} /></SectionCard><SectionCard title="Affected components" description="Assets reported by live threat or attack telemetry." icon={<Target />}>{affected && Object.keys(affected).length ? <div className="pypy-chip-list">{(Array.isArray(affected) ? affected : Object.keys(affected)).map((id)=><span key={id}><Target />{id}</span>)}</div> : <EmptyState title="No affected asset reported" text="The current live payload contains no affected-component list." />}</SectionCard></div><SectionCard title="Detector status" description="PYPY models that contribute detection and diagnostic evidence." icon={<BrainCircuit />}><ModelGrid statuses={props.aiStatuses} preRl={props.preRl} /></SectionCard><SectionCard title="Detection timeline" description="Latest alerts and grid events, ordered by timestamp." icon={<Clock3 />}><IncidentFeed alerts={props.alerts} events={props.events} limit={12} /></SectionCard></>;
}

function DecisionPage(props: Props) {
  const consensus = props.preRl?.consensus ?? props.proposal?.consensus;
  const d = props.orchestratorEvent || {};
  const isDuplicate = /duplicate proposal suppressed/i.test(String(d.reason || ""));
  return <><SectionCard title="Governed decision path" description="Detection never automatically authorizes control." icon={<Workflow />}><DecisionFlow {...props} /><div className="pypy-notice tone-info"><ShieldCheck /><div><strong>DETECTION DOES NOT AUTOMATICALLY AUTHORIZE CONTROL</strong><p>A proposal requires sandbox validation and an explicit orchestrator decision before dispatch.</p></div></div></SectionCard><div className="pypy-three"><MetricCard label="Threat evidence" value={props.threat ? `Score ${props.threat.threat_score ?? "received"}` : "Unavailable"} detail={props.threat?.severity || "Awaiting threat scorer"} icon={<ShieldAlert />} tone={severityTone(props.threat?.severity)} /><MetricCard label="PPO / DQN consensus" value={consensus == null ? "Unavailable" : consensus ? "Consensus" : "No consensus"} detail="Learning-agent proposal only" icon={<BrainCircuit />} tone={consensus ? "ai" : "muted"} /><MetricCard label="Final decision" value={isDuplicate ? "DUPLICATE SUPPRESSED" : d.event || d.decision || "Unavailable"} detail={isDuplicate ? "Repeated recovery proposal was not resent." : d.reason || "Awaiting orchestrator event"} icon={<ShieldCheck />} tone={isDuplicate ? "info" : severityTone(d.event === "APPROVAL" ? "SAFE" : d.event)} /></div><SectionCard title="Orchestrator decision evidence" description="Fields published by the decision service." icon={<Workflow />}><dl className="pypy-evidence">{[["Command",d.command],["Target",d.target],["Source",d.source],["Decision",isDuplicate ? "DUPLICATE SUPPRESSED" : d.decision || d.event],["Reason",isDuplicate ? "Repeated recovery proposal was not resent." : d.reason],["Consensus score",d.consensus_score],["Stability",d.stability],["Veto",d.veto],["Operator approval required",d.operator_approval_required]].map(([k,v])=><div key={String(k)}><dt>{k}</dt><dd>{v === undefined || v === null ? "Not supplied" : typeof v === "boolean" ? (v ? "Yes" : "No") : String(v)}</dd></div>)}</dl></SectionCard><div className="pypy-split"><SectionCard title="Evidence fusion" description="Live fusion and trust payloads." icon={<Sparkles />}><EvidenceList data={props.aiFusion} empty="No fusion evidence received" /></SectionCard><SectionCard title="Physics & trust validation" description="Diagnostic evidence exposed by the backend." icon={<Gauge />}><EvidenceList data={props.physicsValidation} empty="No physics evidence received" /><EvidenceList data={props.trustScores} empty="No trust evidence received" /></SectionCard></div></>;
}

function EvidenceList({ data, empty }: { data: any; empty: string }) {
  const entries = Object.entries(data || {}).filter(([, value]) => value !== null && value !== undefined && typeof value !== "object").slice(0, 10);
  if (!entries.length) return <EmptyState title={empty} text="This panel will update when the existing backend publishes evidence." />;
  return <dl className="pypy-evidence">{entries.map(([key,value])=><div key={key}><dt>{key.replaceAll("_", " ")}</dt><dd>{typeof value === "boolean" ? (value ? "Yes" : "No") : String(value)}</dd></div>)}</dl>;
}

function RecoveryPage(props: Props) {
  const attempt = props.recoveryEvidence.attempts[0]; const sandbox = attempt?.sandbox || props.recovery?.sandbox || props.proposal?.sandbox;
  const safe = sandbox?.overall_safe ?? sandbox?.is_safe ?? props.recovery?.safety_passed;
  const outcomeTone: Tone = attempt?.outcome === "RECOVERY SUCCESS" ? "safe" : attempt?.outcome === "REJECTED" || attempt?.outcome === "ACTUATION NOT VERIFIED" ? "danger" : attempt?.outcome === "ACTIVE ATTACK — STATE CONTESTED" ? "warning" : "info";
  const safetyFields = ["is_safe","solver_converged","finite_state","voltage_safe","thermal_safe","cascade_safe","topology_valid","overall_safe","safety_score","cascade_risk","confidence","violations","rejection_reason"];
  return <><div className="pypy-recovery-hero"><div><StatusBadge tone={outcomeTone}>{attempt?.outcome || "MONITORING"}</StatusBadge><h2>{attempt ? `${attempt.target}: ${attempt.initialState || "OPEN"} → ${attempt.finalState || "pending"}` : "No active recovery attempt"}</h2><p>Success is shown only after a later telemetry frame verifies the commanded breaker state.</p></div><RefreshCw /></div>{props.activeAttack === "BREAKER_MANIPULATION" && <div className="pypy-notice tone-warning"><ShieldAlert /><div><strong>ACTIVE ATTACK — STATE CONTESTED</strong><p>The attacker is forcing breaker state while autonomous recovery is attempting restoration. Operator STOP is recorded as an operator action.</p></div></div>}<div className="pypy-three"><MetricCard label="Recovery outcome" value={attempt?.outcome || "Monitoring"} detail={attempt?.outcome === "ACTUATION NOT VERIFIED" ? "Command dispatched; later telemetry still disagrees" : "Telemetry remains authoritative"} icon={<RefreshCw />} tone={outcomeTone} /><MetricCard label="Target state" value={attempt ? `${attempt.initialState || "OPEN"} → ${attempt.finalState || "Pending"}` : "Unavailable"} detail={attempt?.target || "No target correlated"} icon={<Network />} tone={attempt?.finalState === "CLOSED" ? "safe" : "warning"} /><MetricCard label="Safety gate" value={safe == null ? "No correlated evidence" : safe ? "SAFE" : "REJECTED"} detail={sandbox?.rejection_reason || "RestorationSandbox result"} icon={<ShieldCheck />} tone={safe == null ? "muted" : safe ? "safe" : "danger"} /></div><SectionCard title="Recovery evidence chain" description="Chronological evidence correlated by session and target." icon={<Workflow />}>{attempt ? <div className="pypy-recovery-chain">{attempt.evidence.map((e,i)=><article className={`tone-${e.stage === "REJECTED" ? "danger" : e.stage === "DUPLICATE SUPPRESSED" ? "info" : e.stage === "TELEMETRY VERIFIED" && attempt.outcome === "RECOVERY SUCCESS" ? "safe" : "ai"}`} key={`${e.timestamp}-${i}`}><span>{i+1}</span><div><strong>{e.stage}</strong><p>{e.summary}</p><time>{formatTime(e.timestamp)}</time></div></article>)}</div> : <EmptyState title="No correlated recovery evidence" text="A recovery attempt begins when the backend publishes a control proposal." />}</SectionCard><div className="pypy-split"><SectionCard title="Sandbox / safety mapping" description="Exact backend RestorationSandbox fields." icon={<ShieldCheck />}>{sandbox ? <dl className="pypy-evidence">{safetyFields.map(k=><div key={k}><dt>{k.replaceAll("_"," ")}</dt><dd>{sandbox[k] == null ? "Not supplied" : Array.isArray(sandbox[k]) ? (sandbox[k].length ? sandbox[k].join(", ") : "None") : typeof sandbox[k] === "boolean" ? (sandbox[k] ? "Yes" : "No") : String(sandbox[k])}</dd></div>)}</dl> : <EmptyState title="No sandbox payload correlated" text="Safety values appear when grid/ai/recovery_policy publishes a sandbox result." />}</SectionCard><SectionCard title="Verified recovery summary" description="Generated only from correlated evidence." icon={<CheckCircle2 />}>{attempt ? <dl className="pypy-evidence">{[["Target",attempt.target],["Initial state",attempt.initialState],["Final verified state",attempt.outcome === "RECOVERY SUCCESS" ? attempt.finalState : "Not verified"],["AI / recovery source",attempt.source],["Sandbox",safe == null ? "Not supplied" : safe ? "SAFE" : "REJECTED"],["Orchestrator",attempt.decision?.event || attempt.decision?.decision],["Solver state",sandbox?.solver_converged ? "CONVERGED" : sandbox?.solver_converged === false ? "NOT CONVERGED" : "Not supplied"],["Recovery duration",attempt.evidence.length > 1 ? `${Math.max(0,(attempt.evidence.at(-1)!.timestamp-attempt.evidence[0].timestamp)/1000).toFixed(2)} s` : "In progress"],["Correlation ID",attempt.correlationId]].map(([k,v])=><div key={String(k)}><dt>{k}</dt><dd>{v ?? "Not supplied"}</dd></div>)}</dl> : <EmptyState title="No recovery summary" text="No recovery sequence is active." />}</SectionCard></div><SectionCard title="Manual Operator Override" description="Manual dispatch is explicitly separate from autonomous recovery." icon={<Wrench />}><div className="pypy-action-panel"><div><StatusBadge tone="warning">Manual action</StatusBadge><h3>{props.proposal ? `${props.proposal.command} ${props.proposal.target}` : "No proposal selected"}</h3><p>This creates an operator command and does not claim autonomous recovery.</p></div><button className="pypy-button primary" disabled={!props.proposal || safe !== true} onClick={()=>props.onSendControl({ command: props.proposal.command, target: props.proposal.target, source:"OPERATOR_OVERRIDE" })}><Zap />Manual Operator Override</button></div></SectionCard></>;
}

function SimulationPage(props: Props) {
  const [attack, setAttack] = useState("FDIA"); const [target, setTarget] = useState("Bus_5"); const [bias,setBias]=useState(.15); const [scale,setScale]=useState(1); const [breakerCommand,setBreakerCommand]=useState("OPEN"); const [busy, setBusy] = useState(false);
  const start = () => { setBusy(true); const experimentId=`ui-${Date.now()}`; props.onSendMessage({ topic: "grid/attack", payload: { action: "START", type: attack, experiment_id:experimentId, correlation_id:`${experimentId}:${target}`, config: { target, ...(attack === "FDIA" ? {bias,scale} : {}), ...(attack === "BREAKER_MANIPULATION" ? {command:breakerCommand} : {}) } } }); window.setTimeout(()=>setBusy(false), 600); };
  const stop = () => { setBusy(true); props.onSendMessage({ topic: "grid/attack", payload: { action: "STOP", source:"OPERATOR_STOP" } }); window.setTimeout(()=>setBusy(false), 600); };
  return <><div className="pypy-simulation-banner"><Target /><div><strong>SIMULATION MODE</strong><p>Commands use the live backend cyber-range path.</p></div><StatusBadge tone={props.activeAttack ? "warning" : "info"}>{props.activeAttack ? "Scenario running" : props.connected ? "Ready" : "Disconnected"}</StatusBadge></div><div className="pypy-split simulation"><SectionCard title="Attack configuration" description="Configure the exact MQTT-equivalent payload." icon={<Target />}><div className="pypy-form"><label>Attack type<select value={attack} onChange={(e)=>{setAttack(e.target.value);setTarget(e.target.value==="BREAKER_MANIPULATION"?"L_line_0":"Bus_5")}}><option value="FDIA">False Data Injection (FDIA)</option><option value="BREAKER_MANIPULATION">Breaker manipulation</option></select></label><label>{attack==="FDIA"?"Target bus":"Target branch / breaker"}<input value={target} onChange={(e)=>setTarget(e.target.value)} /></label>{attack==="FDIA"?<><label>Bias<input type="number" step="0.01" value={bias} onChange={(e)=>setBias(Number(e.target.value))}/></label><label>Scale<input type="number" step="0.1" value={scale} onChange={(e)=>setScale(Number(e.target.value))}/></label></>:<label>Command<select value={breakerCommand} onChange={(e)=>setBreakerCommand(e.target.value)}><option>OPEN</option><option>CLOSE</option></select></label>}<div className="pypy-button-row"><button className="pypy-button secondary" disabled={!props.connected || !props.activeAttack || busy} onClick={stop}><Square />STOP</button><button className="pypy-button simulation" disabled={!props.connected || !!props.activeAttack || !target.trim() || busy} onClick={start}><Play />START</button></div></div></SectionCard><SectionCard title="Action provenance" description="Attacker, operator, and recovery actions remain distinct." icon={<Activity />}><dl className="pypy-evidence"><div><dt>Attacker action</dt><dd>{props.activeAttack ? `${props.activeAttack} forcing ${target}` : "Inactive"}</dd></div><div><dt>Operator action</dt><dd>STOP terminates the attack only</dd></div><div><dt>Autonomous recovery</dt><dd>{props.proposal ? `${props.proposal.command} ${props.proposal.target}` : "No proposal"}</dd></div></dl></SectionCard></div><SectionCard title="Simulation event feed" description="Real backend evidence in timestamp order." icon={<Clock3 />}><IncidentFeed alerts={props.alerts} events={props.events} limit={10} /></SectionCard></>;
}

function ForensicsPage(props: Props) {
  const [query, setQuery] = useState(""); const [filter, setFilter] = useState("ALL");
  const rows = useMemo(()=>[
    ...props.alerts.map((item)=>({...item, category:"ALERT", message:item.type || item.event || "Alert", source:item.source || item.suspect_node || "AI Detection"})),
    ...props.events.map((item)=>({...item, category:"EVENT", message:item.event || item.type || "Event", source:item.source || "Digital Twin"})),
  ].sort((a,b)=>Number(b.timestamp||0)-Number(a.timestamp||0)).filter((item)=>filter === "ALL" || item.category === filter).filter((item)=>JSON.stringify(item).toLowerCase().includes(query.toLowerCase())),[props.alerts,props.events,query,filter]);
  return <SectionCard title="Forensic event record" description={`${rows.length} matching live records`} icon={<TerminalSquare />} action={<div className="pypy-table-tools"><label><Search /><input value={query} onChange={(e)=>setQuery(e.target.value)} placeholder="Search records" aria-label="Search forensic records" /></label><select value={filter} onChange={(e)=>setFilter(e.target.value)} aria-label="Filter record type"><option>ALL</option><option>ALERT</option><option>EVENT</option></select></div>}><div className="pypy-table-wrap">{rows.length ? <table className="pypy-table"><thead><tr><th>Time</th><th>Severity</th><th>Type</th><th>Source / asset</th><th>Event</th></tr></thead><tbody>{rows.map((row,index)=><tr key={`${row.timestamp}-${index}`}><td>{formatTime(row.timestamp)}</td><td><StatusBadge tone={severityTone(row.severity)}>{row.severity || "Info"}</StatusBadge></td><td>{row.category}</td><td>{row.source}</td><td>{row.message}</td></tr>)}</tbody></table> : <EmptyState title="No matching records" text="Adjust the search or wait for new live events." />}</div></SectionCard>;
}

function HealthPage(props: Props) {
  const services = [
    ["WebSocket", props.connected, "Live browser connection"], ["Digital Twin", !!props.telemetry, "Telemetry payload"], ["Threat engine", !!props.threat, "Threat payload"], ["AI fusion", !!props.aiFusion, "Fusion payload"], ["Physics validation", !!props.physicsValidation, "Diagnostic payload"], ["Trust engine", !!props.trustScores, "Trust payload"], ["Recovery policy", !!props.preRl || !!props.proposal, "Policy / proposal payload"], ["Orchestrator", !!props.orchestratorEvent, "Decision event"],
  ] as const;
  return <><div className="pypy-three"><MetricCard label="WebSocket" value={props.connected ? "Connected" : "Offline"} detail={props.wsLatency ? `${props.wsLatency} ms last ping` : "Latency unavailable"} icon={<Radio />} tone={props.connected ? "safe" : "danger"} /><MetricCard label="Message rate" value={props.connected ? `${props.messageRate.toFixed(1)} Hz` : "Unavailable"} detail="Observed in the frontend" icon={<Activity />} tone="info" /><MetricCard label="Last interface update" value={props.lastUpdate || "Unavailable"} detail="Local display clock" icon={<Clock3 />} tone="muted" /></div><SectionCard title="Service signals" description="A service is marked live only when a corresponding real signal has been received." icon={<Cpu />}><div className="pypy-service-grid">{services.map(([name,live,detail])=><article key={name}><span className={live ? "live" : "waiting"}>{live ? <Check /> : <Radio />}</span><div><strong>{name}</strong><p>{live ? "Live signal received" : "Awaiting signal"}</p><small>{detail}</small></div></article>)}</div></SectionCard><SectionCard title="AI model availability" description="No model metric is fabricated when a status is missing." icon={<BrainCircuit />}><ModelGrid statuses={props.aiStatuses} preRl={props.preRl} /></SectionCard></>;
}

function ReportsPage(props: Props) {
  const reportCards = [
    { title: "Current situation", detail: props.telemetry ? "Telemetry summary available" : "Waiting for telemetry", icon: Activity, tone: props.connected ? "safe" : "warning" as Tone },
    { title: "Incident record", detail: `${props.alerts.length + props.events.length} browser-visible records`, icon: FileSearch, tone: props.alerts.length ? "warning" : "info" as Tone },
    { title: "AI evidence readiness", detail: props.aiFusion ? "Fusion evidence available" : "Fusion evidence not received", icon: BrainCircuit, tone: props.aiFusion ? "ai" : "muted" as Tone },
  ];
  return <><div className="pypy-report-hero"><BarChart3 /><div><h2>Live situation summary</h2><p>Current telemetry, incident records, and available decision evidence.</p></div><StatusBadge tone={props.connected ? "safe" : "warning"}>{props.connected ? "Current" : "Connection unavailable"}</StatusBadge></div><div className="pypy-report-cards">{reportCards.map(({title,detail,icon:Icon,tone})=><article className={`tone-${tone}`} key={title}><span><Icon /></span><div><strong>{title}</strong><p>{detail}</p></div></article>)}</div><div className="pypy-split"><SectionCard title="Operational summary" icon={<FileSearch />}><dl className="pypy-evidence"><div><dt>Grid</dt><dd>{props.telemetry?.grid_name?.toUpperCase() || props.selectedGrid.toUpperCase()}</dd></div><div><dt>Connection</dt><dd>{props.connected ? "Connected" : "Offline"}</dd></div><div><dt>Active attack</dt><dd>{props.activeAttack || "None reported"}</dd></div><div><dt>Threat severity</dt><dd>{props.threat?.severity || "Unavailable"}</dd></div><div><dt>FLISR state</dt><dd>{props.telemetry || props.recovery ? props.flisrState || "Unavailable" : "Unavailable"}</dd></div><div><dt>Last decision</dt><dd>{props.orchestratorEvent?.event || "Unavailable"}</dd></div></dl></SectionCard><SectionCard title="Evidence availability" icon={<CheckCircle2 />}><div className="pypy-check-list">{[["Telemetry",props.telemetry],["Threat score",props.threat],["AI fusion",props.aiFusion],["Physics validation",props.physicsValidation],["Trust scores",props.trustScores],["Recovery proposal",props.proposal],["Orchestrator decision",props.orchestratorEvent]].map(([label,value])=><div key={String(label)}><span className={value ? "yes" : "no"}>{value ? <Check /> : <CircleOff />}</span><strong>{String(label)}</strong><small>{value ? "Available" : "Not received"}</small></div>)}</div></SectionCard></div></>;
}

function SettingsPage(props: Props) {
  const [compact, setCompact] = useState(()=>localStorage.getItem("pypy_compact") === "true"); const [motion, setMotion] = useState(()=>localStorage.getItem("pypy_motion") !== "false");
  useEffect(()=>{ document.documentElement.dataset.compact=String(compact); localStorage.setItem("pypy_compact",String(compact)); },[compact]);
  useEffect(()=>{ document.documentElement.dataset.motion=String(motion); localStorage.setItem("pypy_motion",String(motion)); },[motion]);
  return <div className="pypy-split"><SectionCard title="Display preferences" description="Stored in this browser only." icon={<Settings />}><div className="pypy-settings-list"><label><div><strong>Compact density</strong><p>Reduce vertical spacing on information-heavy pages.</p></div><input type="checkbox" checked={compact} onChange={(e)=>setCompact(e.target.checked)} /></label><label><div><strong>Interface motion</strong><p>Enable subtle live-state and hover animation.</p></div><input type="checkbox" checked={motion} onChange={(e)=>setMotion(e.target.checked)} /></label></div></SectionCard><SectionCard title="Grid workspace" description="Choose the supported grid model for this workspace." icon={<TowerControl />}><div className="pypy-form"><label>Selected topology<select value={props.selectedGrid.toUpperCase()} onChange={(e)=>props.onSelectGrid(e.target.value.toLowerCase())}><option>IEEE14</option><option>IEEE39</option><option>IEEE57</option><option>IEEE118</option></select></label><div className="pypy-notice tone-info"><HelpCircle /><div><strong>Shared grid configuration</strong><p>Changing the topology sends a configuration request to the connected Digital Twin.</p></div></div></div></SectionCard></div>;
}

export function PypyControlCenter(props: Props) {
  const [exhibition, setExhibition] = useState(() => /^#\/(exhibition|demo)$/.test(window.location.hash));
  useEffect(() => {
    const update = () => setExhibition(/^#\/(exhibition|demo)$/.test(window.location.hash));
    window.addEventListener('hashchange', update);
    window.addEventListener('popstate', update);
    return () => { window.removeEventListener('hashchange', update); window.removeEventListener('popstate', update); };
  }, []);
  const readPageFromLocation = (): ControlPage => {
    const candidate = window.location.hash.replace(/^#\/?/, "") as ControlPage;
    return nav.some((item) => item.id === candidate) ? candidate : "overview";
  };
  const [page, setPage] = useState<ControlPage>(readPageFromLocation); const [mobileOpen, setMobileOpen] = useState(false);
  useEffect(() => {
    if (!mobileOpen) return;
    const sidebar = document.querySelector<HTMLElement>(".pypy-sidebar");
    const controls = () => Array.from(sidebar?.querySelectorAll<HTMLButtonElement>("button") || []).filter(button => button.getClientRects().length > 0);
    controls()[0]?.focus();
    const handleKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") { setMobileOpen(false); document.querySelector<HTMLButtonElement>(".pypy-mobile-menu")?.focus(); }
      if (event.key === "Tab") {
        const items = controls(); const first = items[0]; const last = items[items.length - 1];
        if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
        else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
      }
    };
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [mobileOpen]);
  const copy = pageCopy[page];
  const ActivePageIcon = nav.find((item) => item.id === page)?.icon || Home;
  useEffect(() => {
    if (!window.location.hash) window.history.replaceState(null, "", "#/overview");
    const handleLocationChange = () => setPage(readPageFromLocation());
    window.addEventListener("hashchange", handleLocationChange);
    window.addEventListener("popstate", handleLocationChange);
    return () => {
      window.removeEventListener("hashchange", handleLocationChange);
      window.removeEventListener("popstate", handleLocationChange);
    };
  }, []);
  const go = (next: ControlPage) => {
    if (next !== page) window.history.pushState(null, "", `#/${next}`);
    setPage(next);
    setMobileOpen(false);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };
  const renderPage = () => {
    switch(page) { case "overview": return <OverviewPage {...props} />; case "grid": return <GridPage {...props} />; case "detection": return <DetectionPage {...props} />; case "decision": return <DecisionPage {...props} />; case "recovery": return <RecoveryPage {...props} />; case "simulation": return <SimulationPage {...props} />; case "forensics": return <ForensicsPage {...props} />; case "health": return <HealthPage {...props} />; case "reports": return <ReportsPage {...props} />; case "settings": return <SettingsPage {...props} />; }
  };
  if (exhibition) return <ExhibitionMode {...props} />;
  return <div className={`pypy-app page-${page}`} data-control-page={page}>
    <a className="pypy-skip-link" href="#pypy-main" onClick={(event)=>{event.preventDefault();document.getElementById("pypy-main")?.focus();}}>Skip to content</a>
    <button className="pypy-mobile-menu" onClick={()=>setMobileOpen(true)} aria-label="Open navigation" aria-expanded={mobileOpen} aria-controls="pypy-navigation"><Menu /></button>
    {mobileOpen && <button className="pypy-sidebar-backdrop" aria-label="Close navigation" onClick={()=>setMobileOpen(false)} />}
    <aside className={`pypy-sidebar ${mobileOpen ? "is-open" : ""}`}>
      <div className="pypy-brand"><span><Shield><title>PYPY shield</title></Shield><Zap /></span><div><strong>PYPY</strong><small>Protect Your Power</small></div><button onClick={()=>setMobileOpen(false)} aria-label="Close navigation"><X /></button></div>
      <a className="ex-entry" href="#/exhibition"><Zap size={20}/> Exhibition Mode <ArrowRight size={18}/></a>
      <div className="pypy-side-context"><span className={props.connected ? "is-live" : "is-offline"}><Radio /></span><div><strong>{props.connected ? "Gateway connected" : "Reconnecting"}</strong><small>{props.selectedGrid.toUpperCase()} Digital Twin</small></div></div>
      <nav id="pypy-navigation" aria-label="Primary navigation">{nav.map(({id,label,short,icon:Icon})=><button data-nav={id} key={id} className={page === id ? "active" : ""} onClick={()=>go(id)} aria-current={page === id ? "page" : undefined}><Icon /><span><strong>{label}</strong><small>{short}</small></span>{page === id && <ChevronRight />}</button>)}</nav>
      <div className="pypy-side-footer"><div className="pypy-grid-motif" aria-hidden="true"><Network /><span /><span /><span /></div><div><span><User /></span><div><strong>Grid Operator</strong><small>Safety-gated workspace</small></div></div>{props.onLogout && <button onClick={props.onLogout}>Sign out</button>}</div>
    </aside>
    <div className="pypy-workspace"><header className="pypy-topbar"><div><button onClick={()=>setMobileOpen(true)} aria-label="Open navigation"><Menu /></button><div className="pypy-breadcrumb"><span>Operations</span><ChevronRight /><strong>{nav.find(item=>item.id===page)?.label}</strong></div></div><div><StatusBadge tone={props.connected ? "safe" : "muted"}>{props.connected ? "Connected" : "Offline"}</StatusBadge><span className="pypy-top-stat"><Radio />{props.connected ? `${props.messageRate.toFixed(1)} Hz` : "No stream"}</span><span className="pypy-top-stat"><Clock3 />{props.lastUpdate || "—"}</span></div></header><main id="pypy-main" tabIndex={-1} className="pypy-content"><header className="pypy-page-head"><div className="pypy-page-title"><span className="pypy-page-icon"><ActivePageIcon /></span><div><span>{copy.eyebrow}</span><h1>{copy.title}</h1><p>{copy.description}</p></div></div><div className="pypy-page-status"><span className={props.activeAttack ? "tone-danger" : props.connected ? "tone-safe" : "tone-warning"}>{props.activeAttack ? <ShieldAlert /> : props.connected ? <ShieldCheck /> : <CircleOff />}</span><div><small>Current situation</small><strong>{props.activeAttack ? `${props.activeAttack.replaceAll("_"," ")} detected` : props.connected ? props.telemetry ? "Grid telemetry received" : "Waiting for telemetry" : "Connection unavailable"}</strong></div></div></header>{renderPage()}<footer className="pypy-footer"><span>PYPY — Protect Your Power, Protect Yourself</span><span>AI evidence · physics validation · safety-gated recovery</span></footer></main></div>
  </div>;
}
