import { useEffect, useMemo, useState, type ReactNode } from "react";
import {
  Activity, AlertTriangle, ArrowRight, Bot, Check, CheckCircle2,
  CircuitBoard, Clock3, Cpu, Gauge, HeartPulse, Info, Radio,
  ShieldCheck, Sparkles, Workflow, Zap,
} from "lucide-react";

type Props = {
  connected: boolean;
  telemetry: any;
  threat: any;
  alerts: any[];
  events: any[];
  activeAttack: string | null;
  recovery: any;
  proposal: any;
  orchestratorEvent: any;
  lastControl: any;
  lastUpdate: string;
  aiStatuses: Record<string, any>;
  aiFusion: any;
  physicsValidation: any;
  trustScores: any;
  topology: ReactNode;
};

type Tone = "safe" | "info" | "warning" | "danger" | "purple";

const toneClass: Record<Tone, string> = {
  safe: "ops-tone-safe", info: "ops-tone-info", warning: "ops-tone-warning",
  danger: "ops-tone-danger", purple: "ops-tone-purple",
};

function KpiCard({ label, value, detail, tone, icon }: {
  label: string; value: string | number; detail: string; tone: Tone; icon: ReactNode;
}) {
  return (
    <article className={`ops-card ops-kpi ${toneClass[tone]}`}>
      <div className="ops-kpi-icon" aria-hidden="true">{icon}</div>
      <div>
        <p className="ops-eyebrow">{label}</p>
        <p className="ops-kpi-value">{value}</p>
        <p className="ops-muted">{detail}</p>
      </div>
    </article>
  );
}

function SectionTitle({ icon, title, description, aside }: {
  icon: ReactNode; title: string; description: string; aside?: ReactNode;
}) {
  return (
    <div className="ops-section-title">
      <div className="ops-section-heading">
        <span className="ops-section-icon">{icon}</span>
        <div><h2>{title}</h2><p>{description}</p></div>
      </div>
      {aside}
    </div>
  );
}

export function MainOperationsDashboard(props: Props) {
  const [showTechnical, setShowTechnical] = useState(false);
  const [serviceApi, setServiceApi] = useState<Record<string, any>>({});

  useEffect(() => {
    let cancelled = false;
    const refresh = async () => {
      try {
        const token = localStorage.getItem("pypy_token");
        const response = await fetch("/api/operations/metrics/services", {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        });
        if (response.ok && !cancelled) setServiceApi(await response.json());
      } catch { /* Live MQTT indicators remain available without this optional endpoint. */ }
    };
    refresh();
    const timer = window.setInterval(refresh, 10_000);
    return () => { cancelled = true; window.clearInterval(timer); };
  }, []);

  const breakers = props.telemetry?.state?.breakers || {};
  const buses = props.telemetry?.state?.buses || {};
  const lines = props.telemetry?.state?.lines || {};
  const openBreakers = Object.values(breakers).filter((state) => state === "OPEN").length;
  const voltages = Object.values(buses).map((bus: any) => Number(bus.voltage_pu)).filter(Number.isFinite);
  const currents = Object.values(lines).map((line: any) => Number(line.current_pu ?? line.current)).filter(Number.isFinite);
  const minVoltage = voltages.length ? Math.min(...voltages) : null;
  const maxCurrent = currents.length ? Math.max(...currents) : null;
  const threatScore = Number(props.threat?.threat_score || 0);
  const latestAlert = props.alerts?.[0];
  const approval = props.orchestratorEvent?.event === "APPROVAL";
  const recoveryState = props.recovery?.state || props.recovery?.recovery_state || (approval ? "RESTORED" : "MONITORING");
  const isStable = !props.activeAttack && openBreakers === 0 && (minVoltage === null || minVoltage >= 0.9);
  const status = props.activeAttack ? "Critical" : openBreakers ? "Recovering" : isStable ? "Healthy" : "Warning";

  const stages = [
    { label: "Attack", detail: props.activeAttack || "No attack", done: !!props.activeAttack, active: !!props.activeAttack && !latestAlert },
    { label: "Detection", detail: latestAlert?.type || "AI monitoring", done: !!latestAlert, active: !!latestAlert && !props.threat },
    { label: "Threat", detail: props.threat ? `Score ${threatScore}` : "Awaiting assessment", done: !!props.threat, active: !!props.threat && !props.recovery },
    { label: "Validation", detail: props.recovery ? "Physical evidence checked" : "Safety gate ready", done: !!props.recovery, active: !!props.recovery && !props.proposal },
    { label: "Proposal", detail: props.proposal ? `${props.proposal.command} ${props.proposal.target}` : "No action proposed", done: !!props.proposal, active: !!props.proposal && !props.orchestratorEvent },
    { label: "Approval", detail: props.orchestratorEvent?.event || "Awaiting decision", done: approval, active: !!props.orchestratorEvent && !props.lastControl },
    { label: "Execution", detail: props.lastControl?.command ? `${props.lastControl.command} ${props.lastControl.target || ""}` : "No command", done: !!props.lastControl, active: !!props.lastControl && !isStable },
    { label: "Stabilized", detail: isStable ? "Grid is within limits" : "Monitoring recovery", done: isStable && (!!props.lastControl || !props.activeAttack), active: false },
  ];

  const timeline = useMemo(() => {
    const alertItems = (props.alerts || []).slice(0, 5).map((item) => ({
      timestamp: item.timestamp, title: item.type || "AI anomaly detected",
      detail: `${item.suspect_node || "Grid"} · ${item.severity || "Alert"}`, tone: "danger" as Tone,
    }));
    const eventItems = (props.events || []).slice(0, 7).map((item) => ({
      timestamp: item.timestamp, title: item.event || "Grid event",
      detail: item.source || "Digital Twin", tone: (item.severity === "CRITICAL" ? "danger" : item.severity === "WARNING" ? "warning" : "info") as Tone,
    }));
    const synthetic = [
      props.proposal && { timestamp: props.proposal.timestamp || Date.now(), title: "Recovery proposed", detail: `${props.proposal.command} ${props.proposal.target}`, tone: "purple" as Tone },
      props.orchestratorEvent && { timestamp: props.orchestratorEvent.timestamp || Date.now(), title: `Orchestrator ${props.orchestratorEvent.event?.toLowerCase()}`, detail: props.orchestratorEvent.reason || "Safety decision recorded", tone: (approval ? "safe" : "danger") as Tone },
    ].filter(Boolean) as any[];
    return [...synthetic, ...alertItems, ...eventItems]
      .sort((a, b) => Number(b.timestamp || 0) - Number(a.timestamp || 0)).slice(0, 8);
  }, [props.alerts, props.events, props.proposal, props.orchestratorEvent, approval]);

  const apiServices = (serviceApi as any)?.services || serviceApi;
  const services = [
    ["postgres", "PostgreSQL", apiServices?.postgres?.status], ["redis", "Redis", apiServices?.redis?.status],
    ["mqtt", "MQTT", props.connected ? "online" : apiServices?.mqtt?.status], ["gateway", "Gateway", props.connected ? "online" : apiServices?.gateway?.status],
    ["dashboard", "Dashboard", "online"], ["digital_twin", "Digital Twin", props.telemetry ? "online" : "waiting"],
    ["celery_worker", "Celery Worker", apiServices?.celery_worker?.status], ["celery_beat", "Celery Beat", apiServices?.celery_beat?.status],
    ["ai_detection", "AI Detection", latestAlert ? "online" : "ready"], ["threat_scorer", "Threat Scorer", props.threat ? "online" : "ready"],
    ["self_healing", "Self-Healing", props.recovery ? "online" : "ready"], ["ai_orchestrator", "AI Orchestrator", props.orchestratorEvent ? "online" : "ready"],
    ["ai_lstm", "LSTM", props.aiStatuses?.lstm?.ready ? "healthy" : "waiting"],
    ["ai_gnn", "GNN", props.aiStatuses?.gnn?.ready ? "healthy" : "waiting"],
    ["ai_stgnn", "ST-GNN", props.aiStatuses?.stgnn?.ready ? "healthy" : "waiting"],
    ["ai_pinn", "PINN", props.aiStatuses?.pinn?.ready ? "healthy" : "waiting"],
    ["ai_fusion", "AI Fusion", props.aiStatuses?.fusion?.ready ? "healthy" : "waiting"],
    ["physics_validation", "TRUST / Physics", props.aiStatuses?.trust?.ready ? "healthy" : "waiting"],
  ];
  const confirmedServices = services.filter(([, , state]) => ["online", "healthy"].includes(String(state).toLowerCase())).length;

  return (
    <main className="ops-dashboard" aria-label="PYPY main operations dashboard">
      <section className="ops-hero">
        <div>
          <div className="ops-live-label"><span className="ops-live-dot" /> Live cyber-physical overview</div>
          <h1>PYPY Smart Grid Cyber Defense</h1>
          <p>Understand the grid, AI decision, and recovery outcome at a glance.</p>
        </div>
        <div className="ops-hero-status">
          <span className={`ops-status-badge status-${status.toLowerCase()}`}><ShieldCheck size={17} /> {status}</span>
          <div><strong>IEEE 39-Bus</strong><span>39 buses · 46 lines · 10 generators</span></div>
          <div><strong>{props.lastUpdate || "—"}</strong><span>Last live update</span></div>
        </div>
      </section>

      <section className="ops-kpi-grid" aria-label="Key grid indicators">
        <KpiCard label="Active attack" value={props.activeAttack || "None"} detail={props.activeAttack ? "Defense chain is responding" : "No active attack detected"} tone={props.activeAttack ? "danger" : "safe"} icon={<ShieldCheck />} />
        <KpiCard label="Threat score" value={`${threatScore}/100`} detail={props.threat?.severity || "Low risk"} tone={threatScore >= 75 ? "danger" : threatScore >= 40 ? "warning" : "safe"} icon={<Gauge />} />
        <KpiCard label="Recovery state" value={String(recoveryState).replace(/_/g, " ")} detail={approval ? "Orchestrator approval granted" : "Safety-gated monitoring"} tone={approval ? "safe" : "purple"} icon={<HeartPulse />} />
        <KpiCard label="Open breakers" value={openBreakers} detail={`${Object.keys(breakers).length || 46} monitored`} tone={openBreakers ? "warning" : "safe"} icon={<CircuitBoard />} />
        <KpiCard label="Minimum voltage" value={minVoltage === null ? "—" : `${minVoltage.toFixed(3)} pu`} detail="Safe target ≥ 0.90 pu" tone={minVoltage !== null && minVoltage < 0.9 ? "danger" : "info"} icon={<Zap />} />
        <KpiCard label="Maximum current" value={maxCurrent === null ? "—" : `${maxCurrent.toFixed(3)} pu`} detail="Highest observed branch" tone={maxCurrent !== null && maxCurrent > 1.5 ? "warning" : "info"} icon={<Activity />} />
        <KpiCard label="AI alerts" value={props.alerts?.length || 0} detail={latestAlert ? `${latestAlert.type} · ${latestAlert.suspect_node}` : "No current anomaly"} tone={latestAlert ? "danger" : "safe"} icon={<Bot />} />
        <KpiCard label="Service signals" value={`${confirmedServices}/${services.length}`} detail="Confirmed through UI-visible signals" tone={confirmedServices >= services.length - 4 ? "safe" : "info"} icon={<Radio />} />
      </section>

      <section className="ops-card ops-flow-card">
        <SectionTitle icon={<Workflow />} title="Closed-loop defense flow" description="Follow what PYPY knows, validates, and executes—step by step." aside={<span className="ops-demo-pill"><Sparkles size={14} /> Demo guide</span>} />
        <div className="ops-flow" role="list">
          {stages.map((stage, index) => (
            <div className="ops-flow-wrap" key={stage.label}>
              <div className={`ops-flow-step ${stage.done ? "is-done" : ""} ${stage.active ? "is-active" : ""}`} role="listitem">
                <span>{stage.done ? <Check size={16} /> : index + 1}</span><strong>{stage.label}</strong><small>{stage.detail}</small>
              </div>
              {index < stages.length - 1 && <ArrowRight className="ops-flow-arrow" size={18} />}
            </div>
          ))}
        </div>
        <div className="ops-explainer"><Info size={16} /><span><strong>Safety first:</strong> an AI alert never opens a breaker directly. PYPY requires threat context, physical evidence, sandbox validation, and orchestrator approval.</span></div>
      </section>

      <div className="ops-main-grid">
        <section className="ops-card ops-topology-card">
          <SectionTitle icon={<CircuitBoard />} title="Live IEEE-39 topology" description="Breaker and bus conditions from Digital Twin telemetry." aside={<div className="ops-legend"><span><i className="safe" /> Healthy</span><span><i className="warning" /> Open</span><span><i className="danger" /> Threat</span></div>} />
          <div className="ops-topology">{props.topology}</div>
        </section>

        <aside className="ops-side-stack">
          <section className="ops-card ops-insight-card">
            <SectionTitle icon={<Bot />} title="AI & recovery insight" description="Plain-language explanation of the current decision." />
            <div className="ops-insight-summary">
              <span className={`ops-insight-icon ${props.activeAttack ? "danger" : "safe"}`}>{props.activeAttack ? <AlertTriangle /> : <CheckCircle2 />}</span>
              <div><strong>{props.activeAttack ? `${latestAlert?.type || props.activeAttack} detected` : "Grid operating normally"}</strong><p>{props.activeAttack ? `AI is monitoring ${latestAlert?.suspect_node || "the affected area"}. Recovery remains safety-gated.` : "No active cyber attack or unresolved physical isolation is visible."}</p></div>
            </div>
            <dl className="ops-insight-list">
              <div><dt>Suspect node</dt><dd>{latestAlert?.suspect_node || "None"}</dd></div>
              <div><dt>Recommended action</dt><dd>{props.proposal ? `${props.proposal.command} ${props.proposal.target}` : "Continue monitoring"}</dd></div>
              <div><dt>Approval</dt><dd className={approval ? "text-safe" : ""}>{approval ? "Granted" : props.orchestratorEvent?.event || "Not required"}</dd></div>
            </dl>
            <button className="ops-details-button" onClick={() => setShowTechnical((value) => !value)}>{showTechnical ? "Hide" : "Show"} technical evidence</button>
            {showTechnical && <pre className="ops-technical">{JSON.stringify({ alert: latestAlert || null, fusion: props.aiFusion || null, physics: props.physicsValidation || null, trust: props.trustScores || null, model_statuses: props.aiStatuses || {}, threat: props.threat || null, recovery: props.recovery || null, proposal: props.proposal || null, decision: props.orchestratorEvent || null }, null, 2)}</pre>}
          </section>

          <section className="ops-card ops-timeline-card">
            <SectionTitle icon={<Clock3 />} title="Defense timeline" description="Newest verified event first." />
            <div className="ops-timeline">
              {timeline.length ? timeline.map((item, index) => (
                <div className="ops-timeline-item" key={`${item.timestamp}-${index}`}><span className={toneClass[item.tone as Tone]} /><div><strong>{item.title}</strong><p>{item.detail}</p><time>{item.timestamp ? new Date(Number(item.timestamp)).toLocaleTimeString() : "Live"}</time></div></div>
              )) : <div className="ops-empty"><CheckCircle2 /><strong>System is normal</strong><span>Live defense events will appear here.</span></div>}
            </div>
          </section>
        </aside>
      </div>

      <section className="ops-card ops-services-card">
        <SectionTitle icon={<Cpu />} title="Service health" description="Infrastructure, grid, AI-model, fusion, and recovery readiness." aside={<span className="ops-service-count">{confirmedServices} confirmed live</span>} />
        <div className="ops-services-grid">{services.map(([id, label, state]) => {
          const normalized = String(state || "waiting").toLowerCase();
          const healthy = ["online", "healthy"].includes(normalized);
          return <div className="ops-service" key={id}><span className={healthy ? "healthy" : normalized === "ready" ? "ready" : "waiting"}>{healthy ? <Check size={13} /> : <Radio size={13} />}</span><div><strong>{label}</strong><small>{healthy ? "Live" : normalized === "ready" ? "Ready · awaiting event" : "Awaiting health signal"}</small></div></div>;
        })}</div>
      </section>
    </main>
  );
}
