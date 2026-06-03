import React from "react";
import { 
  Shield, Skull, Zap, Lock, Unlock, EyeOff, RefreshCw, HelpCircle, Clock
} from "lucide-react";

interface TimelineEvent {
  timestamp: number;
  event_type: string;
  message: string;
  details: any;
}

interface ActiveCampaign {
  campaign_id: number;
  start_time: number;
  last_updated: number;
  targets: string[];
  attack_types: string[];
  severity: number;
  stage: string;
  classification: string;
}

interface ContainmentStatus {
  isolated_telemetry_sources: string[];
  locked_breakers: string[];
  active_containments: Array<{ target: string; type: string }>;
}

interface DefenseData {
  timestamp: number;
  escalation_level: string;
  operator_authority: string;
  rl_permissions: string;
  restoration_permissions: string;
  containment_aggressiveness: string;
  telemetry_trust_threshold: number;
  rollback_restrictions: string;
  strategies: string[];
  recommended_defense_actions: Array<{ action: string; target: string; priority: string; reason: string }>;
  restoration_lockdown_active: boolean;
  breaker_lockdown_targets: string[];
  campaign_detected: boolean;
  campaign_severity_score: number;
  containment_strategy: string;
  trusted_operational_mode: string;
  active_campaigns: ActiveCampaign[];
  active_campaign_types: string[];
  adaptive_trust_threshold: number;
  trust_penalty_multiplier: number;
  filtering_smoothing_alpha: number;
  containment_severity_multiplier: number;
  next_attack_window_prediction_seconds: number | null;
  repeated_attack_detected: boolean;
  defense_confidence_score: number;
  repeated_attacker_detected: boolean;
  total_attacks_recorded: number;
  total_containments_recorded: number;
  total_rollbacks_recorded: number;
  total_failed_restorations: number;
  timeline_events: TimelineEvent[];
  containment_status: ContainmentStatus;
}

interface CyberDefensePanelProps {
  defenseData: DefenseData | null;
  onSendControl: (command: string, target: string, payload?: any) => void;
}

export const CyberDefensePanel: React.FC<CyberDefensePanelProps> = ({
  defenseData,
  onSendControl
}) => {
  if (!defenseData) {
    return (
      <div className="bg-scada-panel border border-scada-border rounded-lg p-4 h-[580px] flex flex-col justify-center items-center font-mono">
        <Shield size={36} className="text-gray-500 animate-pulse mb-2" />
        <span className="text-xs text-scada-dimText uppercase tracking-widest">
          Awaiting Cyber Defense Telemetry...
        </span>
      </div>
    );
  }

  const {
    escalation_level = "ADVISORY",
    operator_authority = "READ_ONLY",
    rl_permissions = "RESTRICTED",
    telemetry_trust_threshold = 100,
    rollback_restrictions = "NONE",
    strategies = [],
    restoration_lockdown_active = false,
    campaign_detected = false,
    active_campaigns = [],
    adaptive_trust_threshold = 100,
    trust_penalty_multiplier = 1.0,
    filtering_smoothing_alpha = 1.0,
    next_attack_window_prediction_seconds = null,
    defense_confidence_score = 100.0,
    repeated_attacker_detected = false,
    total_attacks_recorded = 0,
    total_containments_recorded = 0,
    total_rollbacks_recorded = 0,
    total_failed_restorations = 0,
    timeline_events = [],
    containment_status = { isolated_telemetry_sources: [], locked_breakers: [], active_containments: [] }
  } = defenseData;

  // Escalation level specs
  const levels = [
    { name: "ADVISORY", desc: "Normal monitoring", color: "text-emerald-400 border-emerald-500/30 bg-emerald-500/5" },
    { name: "ASSISTED_DEFENSE", desc: "Anomalous triggers detected", color: "text-blue-400 border-blue-500/30 bg-blue-500/5" },
    { name: "AUTONOMOUS_DEFENSE", desc: "Active coordinated attacks", color: "text-amber-400 border-amber-500/30 bg-amber-500/5" },
    { name: "EMERGENCY_CONTAINMENT", desc: "Severe state discrepancies", color: "text-orange-400 border-orange-500/30 bg-orange-500/5" },
    { name: "GRID_PRESERVATION", desc: "Critical grid breakdown imminent", color: "text-red-500 border-red-500/30 bg-red-500/5 animate-pulse" }
  ];

  // Campaign Stages
  const campaignStages = [
    { id: "RECONNAISSANCE", label: "Recon" },
    { id: "INITIAL_COMPROMISE", label: "Compromise" },
    { id: "LATERAL_PROPAGATION", label: "Propagation" },
    { id: "COORDINATED_STRIKE", label: "Strike" },
    { id: "CASCADE_TRIGGERED", label: "Cascade" }
  ];

  const currentCampaign = active_campaigns.length > 0 ? active_campaigns[0] : null;
  const currentStage = currentCampaign ? currentCampaign.stage : "RECONNAISSANCE";

  const getStageIndex = (stageId: string) => {
    return campaignStages.findIndex(s => s.id === stageId);
  };

  const currentStageIdx = currentCampaign ? getStageIndex(currentStage) : -1;

  const getConfidenceColor = (score: number) => {
    if (score < 40) return "text-red-500 shadow-[0_0_8px_rgba(239,68,68,0.4)]";
    if (score < 75) return "text-amber-400 shadow-[0_0_8px_rgba(245,158,11,0.4)]";
    return "text-emerald-400 shadow-[0_0_8px_rgba(16,185,129,0.4)]";
  };

  return (
    <div className="bg-scada-panel border border-scada-border rounded-lg p-3 h-[580px] flex flex-col justify-between overflow-hidden">
      {/* Header */}
      <div className="flex justify-between items-center mb-2 border-b border-scada-border/40 pb-1.5 shrink-0">
        <div className="flex items-center gap-2">
          <Shield className="text-blue-400 animate-pulse" size={16} />
          <h2 className="text-xs font-bold tracking-wider text-white uppercase">
            Autonomous Cyber Defense Hub
          </h2>
        </div>
        <div className="flex items-center gap-2 font-mono text-[9px]">
          <span className="text-scada-dimText">CONFIDENCE INDEX:</span>
          <span className={`font-scada-nums ${getConfidenceColor(defense_confidence_score)}`}>
            {(defense_confidence_score ?? 100.0).toFixed(1)}%
          </span>
          <button 
            onClick={() => onSendControl("RESET_ALARMS", "SYSTEM")}
            className="ml-2 bg-red-950/60 hover:bg-red-900 border border-red-700/50 text-red-400 px-2 py-0.5 rounded text-[8px] flex items-center gap-1 font-sans transition-colors active:scale-95"
            title="Reset active containment blocks and alarms"
          >
            <RefreshCw size={8} /> RESET ALARMS
          </button>
        </div>
      </div>

      {/* Grid Content */}
      <div className="flex-1 grid grid-cols-12 gap-3 min-h-0 mb-2">
        {/* Left Column - Escalation Levels (span 4) */}
        <div className="col-span-4 flex flex-col justify-between min-h-0 bg-black/10 border border-scada-border/20 rounded p-2.5">
          <div className="shrink-0 mb-2 border-b border-scada-border/20 pb-1.5 flex justify-between items-center">
            <span className="text-[10px] font-bold text-scada-dimText uppercase tracking-wider">
              Defense Escalation Levels
            </span>
            <span title="Governance levels mapping network security threat thresholds.">
              <HelpCircle size={10} className="text-gray-500" />
            </span>
          </div>

          {/* List of levels */}
          <div className="flex-1 overflow-y-auto space-y-1.5 pr-0.5 scrollbar-thin">
            {levels.map((lvl) => {
              const isActive = escalation_level === lvl.name;
              return (
                <div
                  key={lvl.name}
                  className={`border rounded p-1.5 transition-all text-left ${
                    isActive 
                      ? `${lvl.color} border-current scale-[1.01] shadow-[inset_0_0_8px_rgba(255,255,255,0.02)]`
                      : "border-scada-border/30 opacity-40 hover:opacity-60"
                  }`}
                >
                  <div className="flex justify-between items-center">
                    <span className="text-[8px] font-bold tracking-wider font-mono">{lvl.name.replace("_", " ")}</span>
                    {isActive && <Zap size={10} className="fill-current animate-bounce" />}
                  </div>
                  <p className="text-[7.5px] text-scada-dimText font-mono leading-tight mt-0.5">{lvl.desc}</p>
                </div>
              );
            })}
          </div>

          {/* Dynamic Governance Info Card */}
          <div className="mt-2 bg-scada-bg/60 border border-scada-border/40 rounded p-2 font-mono text-[8px] shrink-0 text-left">
            <span className="text-[7.5px] font-semibold text-white/80 uppercase block border-b border-scada-border/30 pb-0.5 mb-1.5">
              Active Mode Governance
            </span>
            <div className="space-y-1 text-scada-dimText">
              <div className="flex justify-between">
                <span>OPERATOR AUTHORITY:</span>
                <span className="text-white font-medium">{operator_authority}</span>
              </div>
              <div className="flex justify-between">
                <span>RL POLICY PERMISSION:</span>
                <span className={`font-bold ${rl_permissions === "ALLOWED" ? "text-emerald-400" : rl_permissions === "RESTRICTED" ? "text-amber-400" : "text-red-400"}`}>
                  {rl_permissions}
                </span>
              </div>
              <div className="flex justify-between">
                <span>RESTORATION LOCKDOWN:</span>
                <span className={`font-bold ${restoration_lockdown_active ? "text-red-500" : "text-emerald-400"}`}>
                  {restoration_lockdown_active ? "ENGAGED" : "NOMINAL"}
                </span>
              </div>
              <div className="flex justify-between border-t border-scada-border/20 pt-1 mt-1">
                <span>TRUST THRESHOLD:</span>
                <span className="text-white font-scada-nums">{telemetry_trust_threshold}%</span>
              </div>
              <div className="flex justify-between">
                <span>ROLLBACK ENFORCEMENT:</span>
                <span className="text-white font-medium">{rollback_restrictions}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Center Column - Active Campaigns & Timelines (span 5) */}
        <div className="col-span-5 flex flex-col justify-between min-h-0 bg-black/10 border border-scada-border/20 rounded p-2.5 text-left">
          {/* Campaign Stage Tracking */}
          <div className="shrink-0 mb-2 border-b border-scada-border/20 pb-1.5">
            <div className="flex justify-between items-center">
              <span className="text-[10px] font-bold text-scada-dimText uppercase tracking-wider">
                Coordinated Campaign Tracker
              </span>
              <span className={`text-[8.5px] px-1.5 py-0.5 rounded border uppercase font-mono font-bold ${
                campaign_detected ? "bg-red-950/40 text-red-400 border-red-500/30 animate-pulse" : "bg-emerald-950/20 text-emerald-400 border-emerald-500/20"
              }`}>
                {campaign_detected ? "ALERT: Campaign Active" : "No Active Campaigns"}
              </span>
            </div>
          </div>

          {/* Sequence Timeline representation */}
          <div className="shrink-0 bg-scada-bg/60 border border-scada-border/40 rounded p-2 mb-2">
            <div className="grid grid-cols-5 gap-1 mb-2">
              {campaignStages.map((stage, idx) => {
                const isPassed = currentStageIdx >= idx;
                const isCurrent = currentStageIdx === idx;
                return (
                  <div key={stage.id} className="flex flex-col items-center">
                    <div className={`w-3.5 h-3.5 rounded-full flex items-center justify-center font-mono text-[7px] font-bold border transition-all ${
                      isCurrent 
                        ? "bg-red-500 border-red-400 text-white shadow-[0_0_8px_rgba(239,68,68,0.8)] animate-pulse" 
                        : isPassed 
                          ? "bg-red-950/80 border-red-800 text-red-400" 
                          : "bg-scada-bg border-scada-border/40 text-gray-500"
                    }`}>
                      {idx + 1}
                    </div>
                    <span className={`text-[6.5px] mt-1 truncate max-w-full scale-90 ${
                      isCurrent ? "text-red-400 font-bold" : isPassed ? "text-red-500/70" : "text-gray-600"
                    }`}>
                      {stage.label}
                    </span>
                  </div>
                );
              })}
            </div>
            {/* Timeline connector lines overlay logic */}
            <div className="relative h-1 w-full bg-scada-border/20 rounded-full -mt-[17px] mb-2 z-0 max-w-[85%] mx-auto">
              <div 
                className="absolute top-0 left-0 h-full bg-red-600 rounded-full transition-all duration-500"
                style={{ width: currentStageIdx >= 0 ? `${(currentStageIdx / 4) * 100}%` : "0%" }}
              />
            </div>

            {currentCampaign ? (
              <div className="font-mono text-[8px] space-y-1 border-t border-scada-border/20 pt-1.5 text-left">
                <div className="flex justify-between">
                  <span className="text-scada-dimText">CLASSIFICATION:</span>
                  <span className="text-red-400 font-bold">{currentCampaign.classification}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-scada-dimText">SEVERITY INDEX:</span>
                  <span className="text-white font-scada-nums font-bold">{(currentCampaign?.severity ?? 0.0).toFixed(0)} / 100</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-scada-dimText">COMPROMISED TARGETS:</span>
                  <span className="text-white font-medium truncate max-w-[120px]" title={currentCampaign.targets.join(", ")}>
                    {currentCampaign.targets.join(", ") || "None"}
                  </span>
                </div>
              </div>
            ) : (
              <div className="font-mono text-[7.5px] text-scada-dimText text-center py-2 italic uppercase">
                SCADA Security Monitoring Grid is Quiet
              </div>
            )}
          </div>

          {/* Live Adaptive Filter Parameters Card */}
          <div className="shrink-0 bg-scada-bg/60 border border-scada-border/40 rounded p-2 mb-2 font-mono text-[8px] text-left">
            <span className="text-[7.5px] font-semibold text-white/80 uppercase block border-b border-scada-border/30 pb-0.5 mb-1.5">
              Live Adaptive Controls
            </span>
            <div className="grid grid-cols-2 gap-2">
              <div className="space-y-1">
                <div className="flex justify-between">
                  <span className="text-scada-dimText">ADAPTIVE THR:</span>
                  <span className="text-white font-scada-nums">{(adaptive_trust_threshold ?? 100.0).toFixed(0)}%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-scada-dimText">FILTER SMOOTH ALPHA:</span>
                  <span className="text-white font-scada-nums">{(filtering_smoothing_alpha ?? 1.0).toFixed(2)}</span>
                </div>
              </div>
              <div className="space-y-1 border-l border-scada-border/20 pl-2">
                <div className="flex justify-between">
                  <span className="text-scada-dimText">DECAY MULTIPLIER:</span>
                  <span className="text-white font-scada-nums">x{(trust_penalty_multiplier ?? 1.0).toFixed(1)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-scada-dimText">ATTACK PREDICT WINDOW:</span>
                  <span className="text-amber-400 font-bold">
                    {next_attack_window_prediction_seconds !== null && next_attack_window_prediction_seconds !== undefined 
                      ? `${(next_attack_window_prediction_seconds ?? 0).toFixed(0)}s` 
                      : "ESTIMATING"}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Forensic Logs (Timeline Events) */}
          <div className="flex-1 overflow-hidden flex flex-col">
            <span className="text-[8px] font-bold text-scada-dimText uppercase tracking-wider mb-1 block">
              Forensic Incident Timeline
            </span>
            <div className="flex-1 overflow-y-auto bg-black/20 border border-scada-border/30 rounded p-1.5 font-mono text-[7.5px] space-y-1.5 scrollbar-thin">
              {timeline_events.length > 0 ? (
                timeline_events.slice().reverse().map((evt, idx) => {
                  const timestamp = new Date(evt.timestamp).toLocaleTimeString();
                  let color = "text-gray-400";
                  if (evt.event_type === "ATTACK_DETECTED") color = "text-red-400 font-bold";
                  if (evt.event_type === "CONTAINMENT_DISPATCHED") color = "text-amber-400";
                  if (evt.event_type === "ROLLBACK_TRIGGERED") color = "text-blue-400";
                  if (evt.event_type === "RESTORATION_SUCCESS") color = "text-emerald-400";
                  if (evt.event_type === "RESTORATION_FAILED") color = "text-red-500 font-bold";
                  
                  return (
                    <div key={idx} className="border-b border-scada-border/10 pb-1 last:border-b-0 leading-tight">
                      <div className="flex justify-between text-[7px] text-scada-dimText/65 mb-0.5">
                        <span>{timestamp}</span>
                        <span className={color}>{evt.event_type}</span>
                      </div>
                      <p className="text-white/90">{evt.message}</p>
                    </div>
                  );
                })
              ) : (
                <div className="text-center py-6 text-scada-dimText italic uppercase">No incident reports recorded</div>
              )}
            </div>
          </div>
        </div>

        {/* Right Column - Containments & Memory Records (span 3) */}
        <div className="col-span-3 flex flex-col justify-between min-h-0 bg-black/10 border border-scada-border/20 rounded p-2.5 text-left">
          {/* Active Containments */}
          <div className="flex-1 flex flex-col min-h-0">
            <div className="shrink-0 mb-1.5 border-b border-scada-border/20 pb-1">
              <span className="text-[10px] font-bold text-scada-dimText uppercase tracking-wider">
                Active Containment Status
              </span>
            </div>
            
            <div className="flex-1 overflow-y-auto bg-black/25 border border-scada-border/30 rounded p-1.5 space-y-1.5 scrollbar-thin text-left">
              {containment_status.active_containments.length > 0 ? (
                containment_status.active_containments.map((c, idx) => (
                  <div 
                    key={idx} 
                    className="bg-scada-bg/60 border border-scada-border/40 rounded p-1 flex items-center justify-between text-[7.5px] font-mono leading-none"
                  >
                    <div className="flex items-center gap-1.5 truncate">
                      {c.type === "TELEMETRY_ISOLATION" ? (
                        <EyeOff size={10} className="text-orange-400 shrink-0" />
                      ) : (
                        <Lock size={10} className="text-red-500 shrink-0 animate-pulse" />
                      )}
                      <span className="text-white font-medium truncate">{c.target}</span>
                    </div>
                    <span className={`text-[6.5px] font-semibold px-1 rounded ${
                      c.type === "TELEMETRY_ISOLATION" ? "bg-orange-500/10 text-orange-400" : "bg-red-500/10 text-red-400"
                    }`}>
                      {c.type === "TELEMETRY_ISOLATION" ? "ISOLATED" : "LOCKED"}
                    </span>
                  </div>
                ))
              ) : (
                <div className="h-full flex flex-col justify-center items-center text-center text-scada-dimText font-mono text-[7.5px] uppercase italic py-4">
                  <Unlock size={12} className="text-emerald-400 mb-1" />
                  No Active Containments
                </div>
              )}
            </div>
          </div>

          {/* Defense Memory stats */}
          <div className="mt-3 shrink-0 bg-scada-bg/60 border border-scada-border/40 rounded p-2.5 text-left">
            <span className="text-[7.5px] font-semibold text-white/80 uppercase block border-b border-scada-border/30 pb-0.5 mb-1.5">
              Historical Threat Memory
            </span>
            <div className="font-mono text-[8px] space-y-1.5 text-scada-dimText">
              <div className="flex justify-between items-center">
                <span>ATTACKS DETECTED:</span>
                <span className="text-white font-scada-nums font-bold">{total_attacks_recorded}</span>
              </div>
              <div className="flex justify-between items-center">
                <span>ROLLBACKS TRIGGERED:</span>
                <span className="text-blue-400 font-scada-nums font-bold">{total_rollbacks_recorded}</span>
              </div>
              <div className="flex justify-between items-center">
                <span>CONTAINMENTS APPLIED:</span>
                <span className="text-amber-400 font-scada-nums font-bold">{total_containments_recorded}</span>
              </div>
              <div className="flex justify-between items-center">
                <span>FAILED RESTORATIONS:</span>
                <span className={`font-scada-nums font-bold ${total_failed_restorations > 0 ? "text-red-500 animate-pulse" : "text-white"}`}>
                  {total_failed_restorations}
                </span>
              </div>
              
              {repeated_attacker_detected && (
                <div className="border border-red-500/30 bg-red-950/20 text-red-400 p-1 rounded text-[7.5px] font-bold text-center mt-2 flex items-center justify-center gap-1 animate-pulse uppercase">
                  <Skull size={10} /> Repeated Attacker Flagged
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Footer / Strategies */}
      <div className="border-t border-scada-border/30 pt-1.5 shrink-0 flex justify-between items-center font-mono text-[7.5px] text-scada-dimText text-left">
        <div className="flex items-center gap-1.5 truncate max-w-[70%]">
          <span className="font-bold text-white uppercase">Active Cyber Defense Strategies:</span>
          <span className="text-amber-400 truncate font-semibold">
            {strategies.length > 0 ? strategies.join(" | ") : "MONITORING_ONLY"}
          </span>
        </div>
        <div className="flex items-center gap-1 text-[7px] opacity-75">
          <Clock size={8} /> Cyber-Defense 1.0Hz Daemon Running
        </div>
      </div>
    </div>
  );
};
