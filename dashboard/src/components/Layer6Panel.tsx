import React, { useState } from "react";
import { 
  RotateCcw, AlertOctagon, Activity, RefreshCw
} from "lucide-react";

interface TimelineEvent {
  timestamp: number;
  event: string;
  severity: string;
}

interface ActionLog {
  timestamp: number;
  action: string;
  target: string;
  status: string;
}

interface L6RecoveryData {
  timestamp: number;
  state: string;
  timeline: TimelineEvent[];
  action_logs: ActionLog[];
  confidence: number;
  isolated_segments: string[][];
  active_sequence: Array<{ command: string; target: string; reason: string }>;
  rollback_guard_status?: {
    lockout_breakers: string[];
    rollback_count: number;
  };
}

interface Layer6PanelProps {
  l6RecoveryData: L6RecoveryData | null;
  onSendControl: (command: string, target: string, payload?: any) => void;
}

type TabType = "timeline" | "actions" | "topology" | "overrides";

export const Layer6Panel: React.FC<Layer6PanelProps> = ({ l6RecoveryData, onSendControl }) => {
  const [activeTab, setActiveTab] = useState<TabType>("timeline");

  const hasData = l6RecoveryData !== null && l6RecoveryData !== undefined;
  
  const state = hasData ? l6RecoveryData.state : "NORMAL";
  const confidence = hasData ? l6RecoveryData.confidence : 100;
  const timeline = hasData ? l6RecoveryData.timeline : [];
  const actionLogs = hasData ? l6RecoveryData.action_logs : [];
  const isolatedSegments = hasData ? l6RecoveryData.isolated_segments : [];
  const activeSequence = hasData ? l6RecoveryData.active_sequence : [];
  const rollbackStatus = hasData && l6RecoveryData.rollback_guard_status 
    ? l6RecoveryData.rollback_guard_status 
    : { lockout_breakers: [], rollback_count: 0 };

  const getStateBadgeColor = (s: string) => {
    switch (s) {
      case "ISOLATE": return "bg-yellow-500/20 text-yellow-400 border-yellow-500/40";
      case "STABILIZE": return "bg-amber-500/20 text-amber-400 border-amber-500/40 animate-pulse";
      case "REROUTE": return "bg-cyan-500/20 text-cyan-400 border-cyan-500/40";
      case "RESTORE": return "bg-blue-500/20 text-blue-400 border-blue-500/40 animate-pulse";
      case "VERIFY": return "bg-indigo-500/20 text-indigo-400 border-indigo-500/40";
      case "ROLLBACK": return "bg-red-500/20 text-red-400 border-red-500/40 animate-bounce";
      case "NORMAL": return "bg-emerald-500/20 text-emerald-400 border-emerald-500/40";
      default: return "bg-gray-500/20 text-gray-400 border-gray-500/40";
    }
  };

  return (
    <div className="bg-scada-panel border border-scada-border rounded-lg p-4 h-[300px] flex flex-col justify-between overflow-hidden relative">
      {/* Header */}
      <div className="flex justify-between items-center mb-1.5 border-b border-scada-border/40 pb-1.5 shrink-0">
        <h2 className="text-sm font-semibold tracking-wider text-scada-dimText uppercase flex items-center gap-1.5">
          <Activity size={16} className="text-cyan-400" />
          Layer 6 Autonomous Restoration Core
        </h2>
        
        {/* Navigation Tabs */}
        <div className="flex gap-1.5 mr-auto ml-4">
          {(["timeline", "actions", "topology", "overrides"] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-2 py-0.5 rounded text-[8px] font-mono font-bold tracking-wider uppercase transition-all ${
                activeTab === tab
                  ? "bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 scada-text-glow"
                  : "text-scada-dimText hover:text-white border border-transparent"
              }`}
            >
              {tab === "timeline" ? "Timeline" : tab === "actions" ? "Action Logs" : tab === "topology" ? "Topology recovery" : "Manual overrides"}
            </button>
          ))}
        </div>

        {/* State Badge */}
        <div className={`px-2 py-0.5 rounded text-[8px] font-mono font-bold border ${getStateBadgeColor(state)}`}>
          RECOVERY STATE: {state}
        </div>
      </div>

      {!hasData ? (
        <div className="flex-1 flex flex-col items-center justify-center gap-2 font-mono text-xs text-scada-dimText italic">
          <div className="animate-spin w-4 h-4 border-2 border-cyan-500 border-t-transparent rounded-full"></div>
          <span>Synchronizing Layer 6 recovery daemon...</span>
        </div>
      ) : (
        <div className="flex-1 flex flex-col justify-between overflow-hidden mt-1">
          
          {/* TAB 1: Timeline */}
          {activeTab === "timeline" && (
            <div className="grid grid-cols-12 gap-3 flex-1 overflow-hidden min-h-0 pb-1">
              <div className="col-span-8 flex flex-col overflow-hidden h-full">
                <span className="text-[8px] text-scada-dimText uppercase font-mono font-semibold mb-1">
                  Self-Healing Event Timeline:
                </span>
                <div className="flex-1 overflow-y-auto space-y-1.5 pr-1 bg-scada-bg/20 border border-scada-border/20 rounded p-2 font-mono text-[7.5px] text-scada-dimText">
                  {timeline.map((ev, i) => {
                    let sevColor = "text-white";
                    if (ev.severity === "CRITICAL") sevColor = "text-red-400 font-bold";
                    else if (ev.severity === "WARNING") sevColor = "text-amber-400";
                    else if (ev.severity === "INFO") sevColor = "text-cyan-400";

                    return (
                      <div key={i} className="flex gap-1.5 items-start border-b border-scada-border/10 pb-1">
                        <span className="text-gray-500 font-bold min-w-[45px] shrink-0">
                          {new Date(ev.timestamp).toLocaleTimeString([], { hour12: false })}
                        </span>
                        <span className="text-gray-400 uppercase font-semibold text-[6.5px]">
                          [{ev.severity}]
                        </span>
                        <span className={sevColor}>{ev.event}</span>
                      </div>
                    );
                  })}
                  {timeline.length === 0 && (
                    <p className="italic text-center pt-8">No recovery events logged.</p>
                  )}
                </div>
              </div>

              {/* Recovery Confidence Meter */}
              <div className="col-span-4 flex flex-col justify-between h-full border-l border-scada-border/20 pl-3">
                <div className="space-y-3">
                  <div>
                    <div className="flex justify-between text-[8px] font-mono font-semibold text-scada-dimText">
                      <span>RECOVERY CONFIDENCE:</span>
                      <span className="text-white font-bold">{confidence}%</span>
                    </div>
                    <div className="w-full h-2 bg-scada-bg rounded overflow-hidden border border-scada-border/40 mt-1">
                      <div
                        className={`h-full transition-all duration-500 ${
                          confidence > 80 ? "bg-emerald-500" : confidence > 50 ? "bg-yellow-500" : "bg-red-500"
                        }`}
                        style={{ width: `${confidence}%` }}
                      ></div>
                    </div>
                  </div>

                  <div className="bg-scada-bg/40 p-2 rounded border border-scada-border/25 font-mono text-[7px] text-scada-dimText space-y-1">
                    <span className="font-bold text-gray-300 block border-b border-scada-border/20 pb-0.5">Rollback Guard Status:</span>
                    <p>Rollbacks Triggered: <strong className="text-red-400">{rollbackStatus.rollback_count}</strong></p>
                    <p>Locked breakers: <strong className="text-yellow-500">{rollbackStatus.lockout_breakers.join(", ") || "None"}</strong></p>
                  </div>
                </div>

                <button
                  onClick={() => onSendControl("ROLLBACK_L6_RECOVERY", "SYSTEM")}
                  className="w-full py-1 text-[8px] font-mono font-bold tracking-wider rounded bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/30 transition-all"
                >
                  MANUAL INITIATE ROLLBACK
                </button>
              </div>
            </div>
          )}

          {/* TAB 2: Action Logs */}
          {activeTab === "actions" && (
            <div className="grid grid-cols-12 gap-3 flex-1 overflow-hidden min-h-0 pb-1">
              <div className="col-span-7 flex flex-col overflow-hidden h-full">
                <span className="text-[8px] text-scada-dimText uppercase font-mono font-semibold mb-1">
                  Restoration Action Log:
                </span>
                <div className="flex-1 overflow-y-auto space-y-1 bg-scada-bg/20 border border-scada-border/20 rounded p-1.5 font-mono text-[8px] text-scada-dimText">
                  {actionLogs.map((log, idx) => {
                    let statusColor = "text-white";
                    if (log.status === "SUCCESS") statusColor = "text-emerald-400 font-bold";
                    else if (log.status === "ROLLBACK") statusColor = "text-red-400 font-bold";
                    else if (log.status === "EXECUTING") statusColor = "text-cyan-400 animate-pulse";
                    else if (log.status === "BLOCKED") statusColor = "text-amber-400";

                    return (
                      <div key={idx} className="flex justify-between items-center border-b border-scada-border/10 pb-0.5 mb-0.5">
                        <span>{new Date(log.timestamp).toLocaleTimeString([], { hour12: false })}</span>
                        <span className="text-white font-bold">{log.action} {log.target}</span>
                        <span className={statusColor}>[{log.status}]</span>
                      </div>
                    );
                  })}
                  {actionLogs.length === 0 && (
                    <p className="italic text-center pt-8">No action logs recorded.</p>
                  )}
                </div>
              </div>

              <div className="col-span-5 flex flex-col overflow-hidden h-full border-l border-scada-border/20 pl-3">
                <span className="text-[8px] text-scada-dimText uppercase font-mono font-semibold mb-1">
                  Planned Restoration Sequence:
                </span>
                <div className="flex-1 overflow-y-auto space-y-1 bg-scada-bg/15 border border-scada-border/10 rounded p-1.5 font-mono text-[7px] text-scada-dimText">
                  {activeSequence.map((step, idx) => (
                    <div key={idx} className="p-1 border border-scada-border/10 rounded bg-scada-bg/30">
                      <div className="flex justify-between font-bold text-cyan-400">
                        <span>Step {idx+1}: {step.command} {step.target}</span>
                      </div>
                      <p className="text-[6.5px] text-scada-dimText italic mt-0.5">"{step.reason}"</p>
                    </div>
                  ))}
                  {activeSequence.length === 0 && (
                    <p className="italic text-center pt-8 text-[8px]">No planned sequences.</p>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* TAB 3: Topology Recovery */}
          {activeTab === "topology" && (
            <div className="grid grid-cols-12 gap-3 flex-1 overflow-hidden min-h-0 pb-1">
              <div className="col-span-12 flex flex-col overflow-hidden h-full font-mono text-[8px] text-scada-dimText">
                <span className="text-[8px] text-scada-dimText uppercase font-semibold mb-1">Topology Status & Isolated Load Segments:</span>
                
                <div className="flex-1 grid grid-cols-2 gap-3 overflow-hidden">
                  <div className="border border-scada-border/20 rounded p-2 bg-scada-bg/20 overflow-y-auto space-y-1">
                    <span className="text-gray-300 font-bold block">De-energized segments:</span>
                    {isolatedSegments.map((seg, idx) => (
                      <div key={idx} className="p-1 bg-red-950/20 border border-red-500/20 rounded text-red-400 flex flex-wrap gap-1">
                        <span className="font-bold shrink-0">Island {idx+1}:</span>
                        {seg.map((bus) => (
                          <span key={bus} className="bg-red-500/10 px-1 border border-red-500/30 rounded text-[7px]">{bus}</span>
                        ))}
                      </div>
                    ))}
                    {isolatedSegments.length === 0 && (
                      <p className="text-[8px] text-emerald-400 italic">No isolated loads or islands detected in grid topology.</p>
                    )}
                  </div>

                  <div className="border border-scada-border/20 rounded p-2 bg-scada-bg/20 overflow-y-auto space-y-1">
                    <span className="text-gray-300 font-bold block">Active Tie-breaker switches:</span>
                    <div className="grid grid-cols-1 gap-1">
                      <div className="flex justify-between items-center p-1 bg-scada-bg/40 border border-scada-border/10 rounded">
                        <span className="font-bold text-white">L7_8 (Normally Open)</span>
                        <span className="text-cyan-400">Restoration tie link</span>
                      </div>
                      <div className="flex justify-between items-center p-1 bg-scada-bg/40 border border-scada-border/10 rounded">
                        <span className="font-bold text-gray-500">L4_5 (Sectionalizer)</span>
                        <span className="text-scada-dimText">Substation 5 line</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 4: Operator Overrides */}
          {activeTab === "overrides" && (
            <div className="grid grid-cols-12 gap-3 flex-1 overflow-hidden min-h-0 pb-1">
              <div className="col-span-12 flex flex-col justify-center gap-3 font-mono text-[9px] text-scada-dimText p-4 border border-scada-border/20 rounded bg-scada-bg/25">
                <span className="font-bold text-yellow-400 uppercase text-center mb-1">Operator Autonomous Restoration overrides Console:</span>
                
                <div className="grid grid-cols-3 gap-3">
                  <button
                    onClick={() => onSendControl("TRIGGER_L6_RECOVERY", "SYSTEM")}
                    className="py-2 text-[8px] font-bold tracking-wider rounded bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 transition-all flex items-center justify-center gap-1 uppercase"
                  >
                    <RefreshCw size={10} /> Manually trigger recovery
                  </button>

                  <button
                    onClick={() => onSendControl("ROLLBACK_L6_RECOVERY", "SYSTEM")}
                    className="py-2 text-[8px] font-bold tracking-wider rounded bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/30 transition-all flex items-center justify-center gap-1 uppercase"
                  >
                    <AlertOctagon size={10} /> Force system rollback
                  </button>

                  <button
                    onClick={() => onSendControl("RESET_L6_RECOVERY", "SYSTEM")}
                    className="py-2 text-[8px] font-bold tracking-wider rounded bg-yellow-500/10 hover:bg-yellow-500/20 text-yellow-400 border border-yellow-500/30 transition-all flex items-center justify-center gap-1 uppercase"
                  >
                    <RotateCcw size={10} /> Reset recovery FSM
                  </button>
                </div>
                
                <p className="text-[7.5px] text-center italic mt-2">
                  Warning: Manual overrides bypass automated coordination checking and execute control actions immediately.
                </p>
              </div>
            </div>
          )}

        </div>
      )}
    </div>
  );
};
