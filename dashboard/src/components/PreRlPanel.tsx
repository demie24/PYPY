import React, { useState } from "react";
import { 
  ShieldCheck, RotateCcw, AlertOctagon, ListChecks, Zap
} from "lucide-react";

interface ActionExplainRecord {
  action_id: number;
  action_name: string;
  target: string;
  reason: string;
  safety_justification: string;
  safety_score: number;
  topology_reasoning: string;
  expected_reward_gain: number;
  expected_cascade_reduction: number;
  restoration_probability: number;
  trusted_telemetry_basis: string;
  reasoning_chain: string[];
}

interface ActionQueueItem {
  queue_index: number;
  action_id: number;
  action: string;
  target: string;
  allowed: boolean;
  reason: string;
  safety_score: number;
  operational_risk: number;
  restoration_confidence: number;
  explainability: ActionExplainRecord;
}

interface TimelineEvent {
  timestamp: number;
  category: string;
  description: string;
  state_change: any;
}

interface ObservationDebug {
  voltages: Record<string, number>;
  angles: Record<string, number>;
  loadings: Record<string, number>;
  breakers: Record<string, string>;
  bus_trust: Record<string, number>;
  line_trust: Record<string, number>;
  anomaly_score: number;
  pinn_confidence: number;
  cascade_risk: number;
  flisr_state: string;
  observability: string;
  cyber_instability_probability: number;
  threat_severity: string;
  islanding_active: boolean;
  override_active: boolean;
  trusted_state_quality: number;
  warnings: string[];
}

interface PreRlData {
  timestamp: number;
  sandbox_active: boolean;
  observation_vector: number[];
  observation_debug?: ObservationDebug;
  action_queue: ActionQueueItem[];
  safety_status: {
    overall_score: number;
    allowed: boolean;
    violations: string[];
  };
  restoration_readiness: number;
  rollback_status?: {
    checkpoints_count: number;
    rollback_available: boolean;
    last_checkpoint_time: number;
  };
  timeline?: TimelineEvent[];
  operator_override: {
    pause_autonomous: boolean;
    emergency_stop_active?: boolean;
    restoration_mode?: string;
    execution_delay?: number;
    locked_breakers: string[];
    audit_logs: Array<{
      timestamp: number;
      target: string;
      action: string;
      details: string;
    }>;
  };
  rl_status?: any;
}

interface PreRlPanelProps {
  preRlData: PreRlData | null;
  onSendControl: (command: string, target: string, payload?: any) => void;
}

type PreRlTab = "queue" | "state" | "timeline" | "override" | "rl_agent";

export const PreRlPanel: React.FC<PreRlPanelProps> = ({ preRlData, onSendControl }) => {
  const [activeTab, setActiveTab] = useState<PreRlTab>("queue");
  const [selectedQueueIndex, setSelectedQueueIndex] = useState<number | null>(null);

  const hasData = preRlData !== null && preRlData !== undefined;
  
  const observation = hasData ? preRlData.observation_vector : [];
  const obsDebug = hasData ? preRlData.observation_debug : null;
  const actionQueue = hasData ? preRlData.action_queue : [];
  const safety = hasData ? preRlData.safety_status : { overall_score: 1.0, allowed: true, violations: [] };
  const readiness = hasData ? preRlData.restoration_readiness : 100.0;
  const rollbackStatus = (hasData && preRlData.rollback_status) ? preRlData.rollback_status : { checkpoints_count: 0, rollback_available: false, last_checkpoint_time: 0 };
  const timeline = hasData ? preRlData.timeline : [];
  const override = hasData ? preRlData.operator_override : { 
    pause_autonomous: false, 
    emergency_stop_active: false, 
    restoration_mode: "SEMI_AUTONOMOUS", 
    execution_delay: 0, 
    locked_breakers: [], 
    audit_logs: [] 
  };

  const handlePauseToggle = () => {
    if (override.pause_autonomous) {
      onSendControl("RESUME_AUTONOMOUS", "SYSTEM");
    } else {
      onSendControl("PAUSE_AUTONOMOUS", "SYSTEM");
    }
  };

  const handleEmergencyStop = () => {
    if (override.emergency_stop_active) {
      onSendControl("CLEAR_EMERGENCY_STOP", "SYSTEM");
    } else {
      onSendControl("EMERGENCY_STOP", "SYSTEM");
    }
  };

  const handleModeChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    onSendControl("LOCK_RESTORATION", "SYSTEM", { mode: e.target.value });
  };

  const handleDelayChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onSendControl("SET_DELAY", "SYSTEM", { delay: parseFloat(e.target.value) });
  };

  const handleRevert = () => {
    onSendControl("REVERT_ACTION", "SYSTEM");
  };

  const handleForceRollback = () => {
    onSendControl("FORCE_ROLLBACK", "SYSTEM");
  };

  const handleToggleLock = (breaker: string) => {
    if (override.locked_breakers.includes(breaker)) {
      onSendControl("UNLOCK_ACTION", breaker);
    } else {
      onSendControl("LOCK_ACTION", breaker);
    }
  };

  const handleApproveAction = (item: ActionQueueItem) => {
    onSendControl("APPROVE_ACTION", item.target, { action_id: item.action_id });
  };

  const handleToggleSandbox = () => {
    if (preRlData?.sandbox_active) {
      onSendControl("EXIT_SANDBOX", "SYSTEM");
    } else {
      onSendControl("ENTER_SANDBOX", "SYSTEM");
    }
  };

  return (
    <div className="bg-scada-panel border border-scada-border rounded-lg p-4 h-[300px] flex flex-col justify-between overflow-hidden relative">
      {/* Header */}
      <div className="flex justify-between items-center mb-1.5 border-b border-scada-border/40 pb-1.5 shrink-0">
        <h2 className="text-sm font-semibold tracking-wider text-scada-dimText uppercase flex items-center gap-1.5">
          <ListChecks size={16} className="text-yellow-500" />
          Autonomous Pre-RL Safety & Control
        </h2>
        
        {/* Navigation Tabs */}
        <div className="flex gap-1.5 mr-auto ml-4">
          {(["queue", "state", "timeline", "override", "rl_agent"] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-2 py-0.5 rounded text-[8px] font-mono font-bold tracking-wider uppercase transition-all ${
                activeTab === tab
                  ? "bg-yellow-500/20 text-yellow-400 border border-yellow-500/30 scada-text-glow"
                  : "text-scada-dimText hover:text-white border border-transparent"
              }`}
            >
              {tab === "queue" 
                ? "Action Queue" 
                : tab === "state" 
                  ? "Debugger" 
                  : tab === "timeline" 
                    ? "Timeline" 
                    : tab === "override"
                      ? "Operator Console"
                      : "RL Agent Status"}
            </button>
          ))}
        </div>

        {/* Sandbox Rehearsal Badge */}
        <button
          onClick={handleToggleSandbox}
          className={`px-2 py-0.5 rounded text-[8px] font-mono font-bold border transition-all ${
            preRlData?.sandbox_active
              ? "bg-amber-500/20 text-amber-400 border-amber-500/30 animate-pulse font-extrabold"
              : "bg-scada-bg border-scada-border/60 text-scada-dimText hover:text-white"
          }`}
        >
          {preRlData?.sandbox_active ? "SANDBOX MODE: ON" : "SANDBOX REHEARSAL"}
        </button>
      </div>

      {!hasData ? (
        <div className="flex-1 flex flex-col items-center justify-center gap-2 font-mono text-xs text-scada-dimText italic">
          <div className="animate-spin w-4 h-4 border-2 border-yellow-500 border-t-transparent rounded-full"></div>
          <span>Synchronizing pre-RL state cache...</span>
        </div>
      ) : (
        <div className="flex-1 flex flex-col justify-between overflow-hidden mt-1">
          
          {/* TAB 1: Action Queue & Explainability */}
          {activeTab === "queue" && (
            <div className="grid grid-cols-12 gap-3 flex-1 overflow-hidden min-h-0 pb-1">
              {/* Left Side: Actions List */}
              <div className="col-span-5 flex flex-col overflow-hidden h-full">
                <span className="text-[8px] text-scada-dimText uppercase font-mono font-semibold mb-1">
                  Queue ({actionQueue.length} proposed):
                </span>
                
                <div className="flex-1 overflow-y-auto space-y-1.5 pr-1 border border-scada-border/20 rounded p-1.5 bg-scada-bg/25">
                  {actionQueue.map((item, idx) => (
                    <div
                      key={idx}
                      onClick={() => setSelectedQueueIndex(idx)}
                      className={`cursor-pointer border rounded p-1.5 font-mono text-[9px] flex flex-col justify-between transition-all ${
                        selectedQueueIndex === idx
                          ? "border-yellow-500 bg-yellow-500/10"
                          : item.allowed 
                            ? "bg-emerald-950/10 border-emerald-500/20 hover:border-emerald-500/40" 
                            : "bg-red-950/10 border-red-500/20 hover:border-red-500/40"
                      }`}
                    >
                      <div className="flex justify-between items-center">
                        <span className="font-bold text-white">
                          [{item.action}] on {item.target}
                        </span>
                        <span className={`px-1 rounded-[2px] text-[6px] font-bold ${
                          item.allowed 
                            ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                            : "bg-red-500/10 text-red-400 border border-red-500/20"
                        }`}>
                          {item.allowed ? "APPROVED" : "BLOCKED"}
                        </span>
                      </div>
                      <div className="flex justify-between text-[7px] text-scada-dimText mt-1">
                        <span>Safety: {((item.safety_score ?? 1.0)*100).toFixed(0)}%</span>
                        <span>Risk: {((item.operational_risk ?? 0.0)*100).toFixed(0)}%</span>
                      </div>
                    </div>
                  ))}
                  {actionQueue.length === 0 && (
                    <p className="text-[9px] text-scada-dimText italic font-mono text-center pt-8">
                      No actions currently pending in grid queue.
                    </p>
                  )}
                </div>
              </div>

              {/* Right Side: AI Decision Explainability Details */}
              <div className="col-span-7 flex flex-col overflow-hidden h-full border-l border-scada-border/20 pl-3">
                <span className="text-[8px] text-scada-dimText uppercase font-mono font-semibold mb-1">
                  AI Decision Reasoning Detail:
                </span>
                
                {selectedQueueIndex !== null && actionQueue[selectedQueueIndex] ? (
                  <div className="flex-1 overflow-y-auto space-y-2 pr-1 border border-scada-border/10 rounded p-2 bg-scada-bg/15 font-mono text-[8px] flex flex-col justify-between">
                    <div>
                      <div className="flex justify-between items-start border-b border-scada-border/20 pb-1">
                        <span className="font-bold text-yellow-400">
                          {actionQueue[selectedQueueIndex].action} ({actionQueue[selectedQueueIndex].target})
                        </span>
                        <span className="text-gray-400">ID: {actionQueue[selectedQueueIndex].action_id}</span>
                      </div>
                      
                      <div className="space-y-1 mt-1 text-scada-dimText">
                        <p className="text-white italic">"{actionQueue[selectedQueueIndex].explainability?.reason}"</p>
                        <p><strong>Safety:</strong> {actionQueue[selectedQueueIndex].explainability?.safety_justification}</p>
                        <p><strong>Topology:</strong> {actionQueue[selectedQueueIndex].explainability?.topology_reasoning}</p>
                        <p><strong>Telemetry:</strong> {actionQueue[selectedQueueIndex].explainability?.trusted_telemetry_basis}</p>
                        
                        <div className="flex justify-between border-t border-scada-border/10 pt-1 mt-1 text-[7px]">
                          <span>Est. Reward: <strong className="text-emerald-400">+{actionQueue[selectedQueueIndex].explainability?.expected_reward_gain ?? 0}</strong></span>
                          <span>Cascade Reduc: <strong className="text-emerald-400">-{((actionQueue[selectedQueueIndex].explainability?.expected_cascade_reduction ?? 0.0) * 100).toFixed(0)}%</strong></span>
                          <span>Success Prob: <strong className="text-emerald-400">{((actionQueue[selectedQueueIndex].explainability?.restoration_probability ?? 1.0) * 100).toFixed(0)}%</strong></span>
                        </div>
                      </div>
                      
                      <div className="mt-1.5 pt-1.5 border-t border-scada-border/10">
                        <span className="text-[7.5px] text-scada-dimText uppercase block mb-0.5">Reasoning Chain:</span>
                        <div className="bg-scada-bg/40 p-1 rounded space-y-0.5 text-[7px] text-yellow-500/80">
                          {actionQueue[selectedQueueIndex].explainability?.reasoning_chain?.map((r, ri) => (
                            <div key={ri}>{r}</div>
                          ))}
                        </div>
                      </div>
                    </div>
                    
                    {actionQueue[selectedQueueIndex].allowed && !override.pause_autonomous && (
                      <button
                        onClick={() => handleApproveAction(actionQueue[selectedQueueIndex])}
                        className="mt-1.5 w-full bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-400 border border-emerald-500/40 rounded py-0.5 text-[8px] font-bold transition-all uppercase tracking-widest text-center"
                      >
                        Execute Approved Action
                      </button>
                    )}
                  </div>
                ) : (
                  <div className="flex-1 flex items-center justify-center border border-scada-border/20 rounded bg-scada-bg/15 font-mono text-[9px] text-scada-dimText italic">
                    Select a proposed action to view AI reasoning logs.
                  </div>
                )}
              </div>
            </div>
          )}

          {/* TAB 2: State Debugger */}
          {activeTab === "state" && (
            <div className="grid grid-cols-12 gap-3 flex-1 overflow-hidden min-h-0 pb-1">
              {/* Left Segment: Vector Grid */}
              <div className="col-span-8 flex flex-col overflow-hidden h-full">
                <div className="flex justify-between items-center mb-1">
                  <span className="text-[8px] text-scada-dimText uppercase font-mono font-semibold">
                    State Vector (72 Dimensions):
                  </span>
                  {obsDebug && (
                    <span className="text-[8px] text-emerald-400 font-mono font-bold">
                      Trust Quality: {obsDebug.trusted_state_quality}%
                    </span>
                  )}
                </div>
                
                <div className="flex-1 overflow-y-auto bg-scada-bg/40 border border-scada-border/20 rounded p-1.5 scrollbar-thin">
                  <div className="grid grid-cols-6 gap-1 text-center">
                    {observation.map((val, idx) => {
                      let label = `IDX ${idx}`;
                      if (idx < 9) label = `V ${idx+1}`;
                      else if (idx < 18) label = `Th ${idx-8}`;
                      else if (idx < 27) label = `P ${idx-17}`;
                      else if (idx < 36) label = `Q ${idx-26}`;
                      else if (idx < 45) label = `B ${idx-35}`;
                      else if (idx < 54) label = `T_B ${idx-44}`;
                      else if (idx < 63) label = `T_L ${idx-53}`;
                      else if (idx === 63) label = "ANOM";
                      else if (idx === 64) label = "CONF";
                      else if (idx === 65) label = "RISK";
                      else if (idx === 66) label = "FLSR";
                      else if (idx === 67) label = "OBS";
                      else if (idx === 68) label = "CYB";
                      else if (idx === 69) label = "SEV";
                      else if (idx === 70) label = "ISLD";
                      else if (idx === 71) label = "OVER";

                      return (
                        <div
                          key={idx}
                          className="border border-scada-border/10 bg-scada-bg/60 p-0.5 rounded flex flex-col items-center"
                          title={label}
                        >
                          <span className="text-[5.5px] text-scada-dimText font-mono leading-none font-semibold">{label}</span>
                          <span className="text-[7.5px] font-mono font-bold text-yellow-400 mt-0.5 leading-none">
                            {(val ?? 0.0).toFixed(2)}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>

              {/* Right Segment: Diagnostics & Safety Warnings */}
              <div className="col-span-4 flex flex-col overflow-hidden h-full border-l border-scada-border/20 pl-3">
                <span className="text-[8px] text-scada-dimText uppercase font-mono font-semibold mb-1">
                  Safety Diagnostics:
                </span>
                
                <div className="flex-1 overflow-y-auto space-y-1 bg-scada-bg/25 border border-scada-border/20 rounded p-1.5 font-mono text-[7px] text-scada-dimText">
                  {obsDebug && obsDebug.warnings && obsDebug.warnings.map((err, i) => (
                    <div key={i} className={`flex gap-1 items-start ${err.startsWith("CRITICAL") ? "text-red-400 font-bold" : "text-amber-400"}`}>
                      <AlertOctagon size={8} className="shrink-0 mt-0.5" />
                      <span>{err}</span>
                    </div>
                  ))}
                  
                  {(!obsDebug || !obsDebug.warnings || obsDebug.warnings.length === 0) && (
                    <div className="flex gap-1 items-center text-emerald-400">
                      <ShieldCheck size={8} />
                      <span>All telemetry parameters healthy.</span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* TAB 3: Timeline & Readiness */}
          {activeTab === "timeline" && (
            <div className="grid grid-cols-12 gap-3 flex-1 overflow-hidden min-h-0 pb-1">
              {/* Left Column: Chronological Flow */}
              <div className="col-span-8 flex flex-col overflow-hidden h-full">
                <span className="text-[8px] text-scada-dimText uppercase font-mono font-semibold mb-1">
                  Chronological Grid Timeline (cyber → physics → AI → defense):
                </span>
                
                <div className="flex-1 overflow-y-auto space-y-1.5 pr-1 bg-scada-bg/20 border border-scada-border/20 rounded p-2 font-mono text-[7.5px] text-scada-dimText">
                  {timeline && timeline.map((ev, i) => {
                    let catColor = "text-gray-400";
                    if (ev.category === "ATTACK_DETECTED") catColor = "text-red-400 font-bold";
                    else if (ev.category === "TELEMETRY_DEGRADED") catColor = "text-orange-400";
                    else if (ev.category === "TOPOLOGY_INSTABILITY") catColor = "text-yellow-400";
                    else if (ev.category === "ACTION_SELECTED") catColor = "text-cyan-400";
                    else if (ev.category === "RESTORATION_INITIATED") catColor = "text-emerald-400 font-bold";
                    else if (ev.category === "ROLLBACK_TRIGGERED") catColor = "text-purple-400";
                    else if (ev.category === "RESTORATION_SUCCESS") catColor = "text-green-400 font-bold";
                    else if (ev.category === "RESTORATION_FAILURE") catColor = "text-red-500 font-bold";

                    return (
                      <div key={i} className="flex gap-1.5 items-start border-b border-scada-border/10 pb-1">
                        <span className="text-gray-500 font-bold min-w-[45px] shrink-0">
                          {new Date(ev.timestamp).toLocaleTimeString([], { hour12: false })}
                        </span>
                        <span className={`${catColor} shrink-0 uppercase font-semibold text-[6.5px]`}>
                          [{ev.category}]
                        </span>
                        <span className="text-white">{ev.description}</span>
                      </div>
                    );
                  })}
                  {(!timeline || timeline.length === 0) && (
                    <p className="italic text-center pt-8">Awaiting grid event timeline synchronization...</p>
                  )}
                </div>
              </div>

              {/* Right Column: Readiness Indicators */}
              <div className="col-span-4 flex flex-col justify-between h-full border-l border-scada-border/20 pl-3">
                <div className="space-y-2.5">
                  {/* Readiness Progress Bar */}
                  <div>
                    <div className="flex justify-between text-[8px] font-mono font-semibold text-scada-dimText">
                      <span>RESTORATION READY:</span>
                      <span className="text-white font-bold">{readiness}%</span>
                    </div>
                    <div className="w-full h-1.5 bg-scada-bg rounded overflow-hidden border border-scada-border/40 mt-0.5">
                      <div
                        className={`h-full transition-all duration-500 ${
                          readiness > 80 ? "bg-emerald-500" : readiness > 50 ? "bg-yellow-500" : "bg-red-500"
                        }`}
                        style={{ width: `${readiness}%` }}
                      ></div>
                    </div>
                  </div>

                  {/* Safety Score Index */}
                  <div>
                    <div className="flex justify-between text-[8px] font-mono font-semibold text-scada-dimText">
                      <span>SAFETY INDEX:</span>
                      <span className="text-white font-bold">{((safety?.overall_score ?? 1.0) * 100).toFixed(0)}%</span>
                    </div>
                    <div className="w-full h-1.5 bg-scada-bg rounded overflow-hidden border border-scada-border/40 mt-0.5">
                      <div
                        className="h-full bg-cyan-500 transition-all duration-500"
                        style={{ width: `${safety.overall_score * 100}%` }}
                      ></div>
                    </div>
                  </div>

                  {/* Rollback status */}
                  <div className="bg-scada-bg/40 p-1.5 rounded border border-scada-border/25 font-mono text-[7px] text-scada-dimText space-y-1">
                    <span className="font-bold text-gray-300 block border-b border-scada-border/20 pb-0.5">Rollback Stack:</span>
                    <p>Stored Checkpoints: <strong className="text-white">{rollbackStatus.checkpoints_count}</strong></p>
                    <p>Last Saved: <strong className="text-white">{rollbackStatus.last_checkpoint_time > 0 ? new Date(rollbackStatus.last_checkpoint_time).toLocaleTimeString([], { hour12: false }) : "None"}</strong></p>
                  </div>
                </div>

                <button
                  onClick={handleForceRollback}
                  disabled={!rollbackStatus.rollback_available}
                  className="w-full py-1 text-[8px] font-mono font-bold tracking-wider rounded bg-purple-500/10 hover:bg-purple-500/20 text-purple-400 border border-purple-500/30 transition-all disabled:opacity-50"
                >
                  FORCE ROLLBACK TO CHECKSUM
                </button>
              </div>
            </div>
          )}

          {/* TAB 4: Operator Overrides Console */}
          {activeTab === "override" && (
            <div className="grid grid-cols-12 gap-3 flex-1 overflow-hidden min-h-0 pb-1">
              {/* Left Column: Interactive Overrides */}
              <div className="col-span-6 flex flex-col justify-between h-full">
                <div className="space-y-1.5">
                  <div className="flex justify-between items-center font-mono text-[8px] text-scada-dimText">
                    <span>Restoration Controls:</span>
                  </div>
                  
                  {/* Emergency Stop Hanger */}
                  <button
                    onClick={handleEmergencyStop}
                    className={`w-full py-1 text-[9px] font-mono font-bold border transition-all rounded flex items-center justify-center gap-1 ${
                      override.emergency_stop_active
                        ? "bg-red-500 text-white border-red-600 animate-pulse font-extrabold"
                        : "bg-red-950/20 text-red-400 border-red-500/40 hover:bg-red-950/40"
                    }`}
                  >
                    <Zap size={10} /> {override.emergency_stop_active ? "EMERGENCY Halted (Release)" : "EMERGENCY STOP"}
                  </button>

                  <div className="grid grid-cols-2 gap-1.5">
                    {/* Pause Switch */}
                    <button
                      onClick={handlePauseToggle}
                      className={`py-0.5 rounded text-[8px] font-mono font-bold transition-all border ${
                        override.pause_autonomous 
                          ? "bg-amber-500/20 text-amber-400 border-amber-500/40" 
                          : "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 hover:bg-emerald-500/20"
                      }`}
                    >
                      {override.pause_autonomous ? "PAUSED" : "RUNNING"}
                    </button>
                    
                    {/* Revert Action */}
                    <button
                      onClick={handleRevert}
                      className="py-0.5 rounded text-[8px] font-mono font-bold bg-purple-500/10 border border-purple-500/30 text-purple-400 hover:bg-purple-500/20 transition-all flex items-center justify-center gap-0.5"
                    >
                      <RotateCcw size={8} /> UNDO ACTION
                    </button>
                  </div>
                  
                  {/* Mode Locking */}
                  <div className="flex justify-between items-center border border-scada-border/20 rounded p-1 bg-scada-bg/10 font-mono text-[8px] text-scada-dimText">
                    <span>Restoration Mode:</span>
                    <select
                      value={override.restoration_mode || "SEMI_AUTONOMOUS"}
                      onChange={handleModeChange}
                      className="bg-scada-bg border border-scada-border/40 text-white rounded p-0.5 text-[8px] outline-none font-bold"
                    >
                      <option value="ADVISORY">ADVISORY</option>
                      <option value="SEMI_AUTONOMOUS">SEMI-AUTO</option>
                      <option value="AUTO">AUTO (RL)</option>
                    </select>
                  </div>

                  {/* Execution Delay Slider */}
                  <div className="border border-scada-border/20 rounded p-1 bg-scada-bg/10 font-mono text-[8px] text-scada-dimText">
                    <div className="flex justify-between mb-0.5">
                      <span>Autonomous delay:</span>
                      <span className="text-white font-bold">{(override.execution_delay || 0.0).toFixed(1)}s</span>
                    </div>
                    <input
                      type="range"
                      min={0}
                      max={10}
                      step={0.5}
                      value={override.execution_delay || 0}
                      onChange={handleDelayChange}
                      className="w-full accent-yellow-500 h-1 bg-scada-border/40 rounded appearance-none cursor-pointer"
                    />
                  </div>
                </div>

                {/* Breaker locking states */}
                <div className="mt-1">
                  <span className="text-[8px] text-scada-dimText uppercase font-mono font-semibold block mb-0.5">
                    Breaker stateful locks:
                  </span>
                  <div className="grid grid-cols-4 gap-1">
                    {["L1_4", "L4_5", "L7_8", "L8_9"].map((b) => {
                      const locked = override.locked_breakers.includes(b);
                      return (
                        <button
                          key={b}
                          onClick={() => handleToggleLock(b)}
                          className={`py-0.5 rounded text-[7.5px] font-mono font-bold transition-all border ${
                            locked 
                              ? "bg-red-500/20 text-red-400 border-red-500/40" 
                              : "bg-scada-bg text-scada-dimText border-scada-border/30 hover:text-white"
                          }`}
                        >
                          {b} {locked ? "LOCK" : "FREE"}
                        </button>
                      );
                    })}
                  </div>
                </div>
              </div>

              {/* Right Column: Audit Logs */}
              <div className="col-span-6 flex flex-col overflow-hidden h-full border-l border-scada-border/20 pl-3">
                <span className="text-[8px] text-scada-dimText uppercase font-mono font-semibold mb-1">
                  Overrides Audit Log:
                </span>
                
                <div className="flex-1 overflow-y-auto space-y-1 pr-1 bg-scada-bg/20 border border-scada-border/20 rounded p-1.5 font-mono text-[7px] text-scada-dimText">
                  {override.audit_logs && override.audit_logs.map((log, idx) => (
                    <div key={idx} className="border-b border-scada-border/10 pb-0.5 mb-0.5">
                      <span className="text-gray-500">
                        {new Date(log.timestamp).toLocaleTimeString([], { hour12: false })}
                      </span>{" "}
                      <span className="text-yellow-400 font-bold">[{log.action}]</span>{" "}
                      <span className="text-white">{log.details}</span>
                    </div>
                  ))}
                  {(!override.audit_logs || override.audit_logs.length === 0) && (
                    <p className="italic text-center pt-8">No operator overrides recorded.</p>
                  )}
                </div>
              </div>
            </div>
          )}
          {/* TAB 5: RL Agent Status */}
          {activeTab === "rl_agent" && (
            <div className="grid grid-cols-12 gap-3 flex-1 overflow-hidden min-h-0 pb-1">
              {/* Left Column: Agent Metadata & Training status */}
              <div className="col-span-5 flex flex-col justify-between h-full font-mono text-[8px] text-scada-dimText">
                <div className="space-y-0.5">
                  <span className="text-[8px] text-scada-dimText uppercase font-semibold">Agent & Policy Diagnostics:</span>
                  <div className="bg-scada-bg/40 border border-scada-border/20 rounded p-1.5 space-y-0.5">
                    <div className="flex justify-between">
                      <span>Active Agent:</span>
                      <strong className="text-yellow-400">{preRlData.rl_status?.agent_type || "PPO (Actor-Critic)"}</strong>
                    </div>
                    <div className="flex justify-between">
                      <span>Curriculum Level:</span>
                      <strong className="text-cyan-400">
                        Level {preRlData.rl_status?.curriculum_level || 1}
                        {preRlData.rl_status?.curriculum_level === 3 ? " (Level 3)" : preRlData.rl_status?.curriculum_level === 2 ? " (Level 2)" : " (Level 1)"}
                      </strong>
                    </div>
                    <div className="flex justify-between">
                      <span>Training Episode:</span>
                      <span className="text-white font-bold">{preRlData.rl_status?.episode || 0} / {preRlData.rl_status?.total_episodes || 1000}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Current loss:</span>
                      <span className="text-red-400 font-bold">{typeof preRlData.rl_status?.loss === "number" ? preRlData.rl_status.loss.toFixed(4) : "0.0000"}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Entropy (PPO):</span>
                      <span className="text-purple-400 font-bold">{typeof preRlData.rl_status?.entropy === "number" ? preRlData.rl_status.entropy.toFixed(4) : "0.0000"}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Explore Ratio:</span>
                      <span className="text-amber-400 font-bold">
                        {typeof preRlData.rl_status?.explore_ratio === "number" ? `${(preRlData.rl_status.explore_ratio * 100).toFixed(0)}%` : "0%"}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span>Action Diversity:</span>
                      <span className="text-cyan-400 font-bold">
                        {typeof preRlData.rl_status?.action_diversity === "number" ? `${(preRlData.rl_status.action_diversity * 100).toFixed(0)}%` : "0%"}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="bg-scada-bg/25 border border-scada-border/10 rounded p-1.5 space-y-0.5">
                  <span className="text-[7.5px] text-scada-dimText uppercase block font-semibold">Exploration Safety & Restoration:</span>
                  <div>
                    <div className="flex justify-between text-[7px]">
                      <span>Restoration Success Rate:</span>
                      <strong className="text-emerald-400">{((preRlData.rl_status?.success_rate ?? 1.0) * 100).toFixed(0)}%</strong>
                    </div>
                    <div className="w-full h-1 bg-scada-bg rounded overflow-hidden mt-0.5">
                      <div 
                        className="h-full bg-emerald-500" 
                        style={{ width: `${((preRlData.rl_status?.success_rate || 1.0) * 100)}%` }}
                      ></div>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-1 mt-1 text-[7px]">
                    <div className="flex justify-between border border-scada-border/10 bg-scada-bg/20 px-1 py-0.5 rounded">
                      <span>Violations:</span>
                      <strong className={preRlData.rl_status?.safety_violations > 0 ? "text-red-400 font-bold" : "text-emerald-400"}>
                        {preRlData.rl_status?.safety_violations || 0}
                      </strong>
                    </div>
                    <div className="flex justify-between border border-scada-border/10 bg-scada-bg/20 px-1 py-0.5 rounded">
                      <span>Rollbacks:</span>
                      <strong className="text-purple-400 font-bold">{preRlData.rl_status?.rollback_count || 0}</strong>
                    </div>
                  </div>
                </div>
              </div>

              {/* Right Column: Reward Trend & Detailed Analytics */}
              <div className="col-span-7 flex flex-col justify-between h-full border-l border-scada-border/20 pl-3 font-mono text-[8px] text-scada-dimText">
                <div className="grid grid-cols-2 gap-2">
                  {/* Reward Trend */}
                  <div className="bg-scada-bg/40 border border-scada-border/20 rounded p-1.5 flex flex-col justify-between h-[80px]">
                    <span className="text-[7.5px] text-scada-dimText uppercase font-semibold block mb-0.5">Reward Trend:</span>
                    <div className="flex justify-between text-[7px]">
                      <span>Latest:</span>
                      <strong className={(preRlData.rl_status?.reward ?? 0.0) >= 0 ? "text-emerald-400" : "text-red-400"}>
                        {(preRlData.rl_status?.reward ?? 0.0).toFixed(2)}
                      </strong>
                    </div>
                    <div className="flex justify-between text-[7px]">
                      <span>10-Ep Avg:</span>
                      <strong className={(preRlData.rl_status?.avg_reward ?? 0.0) >= 0 ? "text-emerald-400" : "text-red-400"}>
                        {(preRlData.rl_status?.avg_reward ?? 0.0).toFixed(2)}
                      </strong>
                    </div>
                    <div className="w-full h-8 bg-scada-bg/60 border border-scada-border/10 rounded overflow-hidden mt-1 relative flex items-center justify-center">
                      <span className="absolute text-[5.5px] text-gray-500 pointer-events-none uppercase">REWARD ENVELOPE</span>
                      <svg className="w-full h-full stroke-yellow-500 fill-none" viewBox="0 0 100 20">
                        <path 
                          d={`M 0,${15 - Math.max(-10, Math.min(30, preRlData.rl_status?.reward ?? 0.0)) / 2} L 20,13 L 40,16 L 60,11 L 80,14 L 100,${10 - Math.max(-10, Math.min(30, preRlData.rl_status?.avg_reward ?? 0.0)) / 2}`} 
                          strokeWidth="1.5"
                        />
                      </svg>
                    </div>
                  </div>

                  {/* Physics & Containment Analytics */}
                  <div className="bg-scada-bg/40 border border-scada-border/20 rounded p-1.5 space-y-1">
                    <span className="text-[7.5px] text-scada-dimText uppercase font-semibold block">Grid Physics Metrics:</span>
                    <div className="flex justify-between text-[7px]">
                      <span>Restored Load:</span>
                      <strong className="text-emerald-400">{typeof preRlData.rl_status?.restoration_completion_pct === "number" ? `${preRlData.rl_status.restoration_completion_pct.toFixed(0)}%` : "0%"}</strong>
                    </div>
                    <div className="flex justify-between text-[7px]">
                      <span>Unsafe Topo Freq:</span>
                      <strong className={(preRlData.rl_status?.unsafe_topology_freq ?? 0.0) > 0.3 ? "text-red-400" : "text-gray-300"}>
                        {typeof preRlData.rl_status?.unsafe_topology_freq === "number" ? `${(preRlData.rl_status.unsafe_topology_freq * 100).toFixed(0)}%` : "0%"}
                      </strong>
                    </div>
                    <div className="flex justify-between text-[7px]">
                      <span>Avg V-Dev:</span>
                      <strong className="text-yellow-400">{typeof preRlData.rl_status?.avg_voltage_deviation === "number" ? `${preRlData.rl_status.avg_voltage_deviation.toFixed(3)} pu` : "0.000 pu"}</strong>
                    </div>
                    <div className="flex justify-between text-[7px]">
                      <span>Recovery Latency:</span>
                      <strong className="text-cyan-400">{preRlData.rl_status?.recovery_latency !== undefined ? `${preRlData.rl_status.recovery_latency} steps` : "0 steps"}</strong>
                    </div>
                  </div>
                </div>

                <div className="space-y-0.5 border-t border-scada-border/20 pt-1 mt-1.5 flex justify-between items-center">
                  <div className="flex gap-2">
                    <div className="text-[7px]">
                      <span>Containment Conflicts: </span>
                      <strong className={preRlData.rl_status?.containment_conflicts > 0 ? "text-orange-400" : "text-emerald-400"}>{preRlData.rl_status?.containment_conflicts || 0}</strong>
                    </div>
                    <div className="text-[7px]">
                      <span>Containments: </span>
                      <strong className="text-emerald-400">{preRlData.rl_status?.containment_count || 0}</strong>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-1 text-[6.5px] text-emerald-400 font-bold font-bold">
                    <div className="flex items-center gap-0.5 text-cyan-400">
                      <ShieldCheck size={7} /> Spam Suppress
                    </div>
                    <div className="flex items-center gap-0.5 text-cyan-400">
                      <ShieldCheck size={7} /> Cooldown Gate
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

        </div>
      )}
    </div>
  );
};
