import React from "react";
import { ShieldCheck, Clock } from "lucide-react";

interface TrustDetails {
  trust_score: number;
  stability_score: number;
  physics_consistency_score: number;
  cyber_suspicion_score: number;
  anomaly_frequency: number;
}

interface TrustScoresData {
  timestamp: number;
  bus_trust: Record<string, number>;
  line_trust: Record<string, number>;
  details: Record<string, TrustDetails>;
}

interface FilterAction {
  action: "PASSED" | "SMOOTHED" | "REJECTED";
  trust_score: number;
  raw_voltage?: number;
  filtered_voltage?: number;
  raw_flow_mw?: number;
  filtered_flow_mw?: number;
}

interface AdaptiveFilterData {
  timestamp: number;
  global_grid_confidence: number;
  trusted_state: boolean;
  degraded_observability: boolean;
  filter_actions: Record<string, FilterAction>;
}

interface TrustAnalysisPanelProps {
  trustScores: TrustScoresData | null;
  filterData: AdaptiveFilterData | null;
}

export const TrustAnalysisPanel: React.FC<TrustAnalysisPanelProps> = ({ trustScores, filterData }) => {
  const hasData = trustScores !== null && trustScores !== undefined && filterData !== null && filterData !== undefined;
  
  const confidence = hasData ? (filterData.global_grid_confidence ?? 100.0) : 100.0;
  const degraded = hasData ? filterData.degraded_observability : false;
  const trusted = hasData ? filterData.trusted_state : true;
  
  const getTrustColor = (score?: number) => {
    const s = score ?? 100;
    if (s >= 90) return "text-emerald-400";
    if (s >= 70) return "text-yellow-400";
    return "text-red-400 font-extrabold animate-pulse";
  };

  const getActionBadge = (action: string) => {
    switch (action) {
      case "REJECTED":
        return "bg-red-500/15 border-red-500 text-red-400 font-bold scada-glow-red animate-pulse";
      case "SMOOTHED":
        return "bg-amber-500/15 border-amber-500 text-amber-400 font-medium";
      default:
        return "bg-emerald-500/10 border-emerald-500/30 text-scada-nominal font-medium";
    }
  };

  return (
    <div className="bg-scada-panel border border-scada-border rounded-lg p-4 h-[300px] flex flex-col justify-between overflow-hidden">
      {/* Header */}
      <div className="flex justify-between items-center mb-2 border-b border-scada-border/40 pb-1.5 shrink-0">
        <h2 className="text-sm font-semibold tracking-wider text-scada-dimText uppercase flex items-center gap-1.5">
          <ShieldCheck size={16} className={degraded ? "text-red-500 animate-pulse" : "text-emerald-400"} />
          Telemetry Trust & Filtering
        </h2>
        <div className="flex items-center gap-1.5 font-mono text-[9px] text-scada-dimText">
          <Clock size={10} />
          <span>FSE Engine</span>
        </div>
      </div>

      {/* Main Panel Content */}
      {!hasData ? (
        <div className="flex-1 flex flex-col items-center justify-center gap-2 font-mono text-xs text-scada-dimText italic">
          <div className="animate-spin w-4 h-4 border-2 border-emerald-400 border-t-transparent rounded-full"></div>
          <span>Trust scoring engine booting... Awaiting data stream...</span>
        </div>
      ) : (
        <div className="flex-1 flex flex-col justify-between overflow-hidden">
          
          {/* Fused Confidence & Degraded Alerts */}
          <div className="grid grid-cols-2 gap-3 mb-2 shrink-0">
            <div className="bg-scada-bg/60 border border-scada-border/50 rounded p-2 flex flex-col justify-between h-[65px]">
              <span className="text-[8px] text-scada-dimText uppercase font-mono font-semibold">Grid Confidence Index</span>
              <div className="flex items-baseline gap-1 mt-1">
                <span className={`text-base font-bold font-scada-nums ${
                  confidence >= 80 ? "text-emerald-400 scada-text-glow-green" :
                  confidence >= 60 ? "text-yellow-400" : "text-red-500 font-extrabold scada-text-glow-red"
                }`}>
                  {(confidence ?? 100).toFixed(1)}%
                </span>
              </div>
            </div>
            
            <div className="bg-scada-bg/60 border border-scada-border/50 rounded p-2 flex flex-col justify-between h-[65px]">
              <span className="text-[8px] text-scada-dimText uppercase font-mono font-semibold">Observability Status</span>
              {degraded ? (
                <span className="px-2 py-0.5 border border-red-500 bg-red-500/15 text-red-400 rounded-[3px] text-[8px] tracking-wider uppercase font-semibold text-center font-mono mt-1 animate-pulse scada-glow-red">
                  DEGRADED OBS (FILTER ACTIVE)
                </span>
              ) : (
                <span className="px-2 py-0.5 border border-emerald-500/30 bg-emerald-500/10 text-scada-nominal rounded-[3px] text-[8px] tracking-wider uppercase font-semibold text-center font-mono mt-1">
                  FULL OBSERVABILITY (TRUSTED)
                </span>
              )}
            </div>
          </div>

          {/* Grid Layout of Bus Trust and Active Filters */}
          <div className="flex-1 flex gap-3 overflow-hidden">
            {/* Bus Trust Grid (Left half) */}
            <div className="w-[45%] flex flex-col justify-between border border-scada-border/30 rounded p-1.5 bg-scada-bg/25">
              <span className="text-[7.5px] font-bold font-mono tracking-wider uppercase text-scada-dimText border-b border-scada-border/20 pb-1 mb-1 text-center">
                Bus Trust Scores
              </span>
              <div className="grid grid-cols-3 gap-x-1 gap-y-1.5 font-mono text-[8px] flex-1 items-center">
                {Object.entries(trustScores?.bus_trust || {}).map(([busName, score]) => (
                  <div key={busName} className="flex flex-col items-center">
                    <span className="text-[7px] text-white/50">{busName.replace("Bus_", "B")}</span>
                    <span className={`font-bold ${getTrustColor(score)}`}>{(score ?? 100.0).toFixed(0)}%</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Active Filter actions log (Right half) */}
            <div className="w-[55%] flex flex-col justify-between border border-scada-border/30 rounded p-1.5 bg-scada-bg/25 overflow-hidden">
              <span className="text-[7.5px] font-bold font-mono tracking-wider uppercase text-scada-dimText border-b border-scada-border/20 pb-1 mb-1 shrink-0">
                Active Filter Actions
              </span>
              <div className="flex-1 overflow-y-auto space-y-1 pr-0.5">
                {Object.entries(filterData?.filter_actions || {})
                  .filter(([_, act]) => act?.action !== "PASSED")
                  .map(([node, act]) => (
                    <div key={node} className="flex justify-between items-center text-[7.5px] font-mono border-b border-scada-border/10 pb-0.5">
                      <span className="text-white font-semibold uppercase">{node.replace("_", " ")}</span>
                      <span className={`px-1 rounded-[2px] border text-[6px] scale-90 ${getActionBadge(act?.action ?? "")}`}>
                        {act?.action}
                      </span>
                    </div>
                  ))}
                {Object.values(filterData?.filter_actions || {}).every((act) => act?.action === "PASSED") && (
                  <p className="text-scada-dimText italic text-[7.5px] text-center mt-4">
                    Telemetry healthy. Filters bypassed.
                  </p>
                )}
              </div>
            </div>
          </div>

          {/* Footer Info */}
          <div className="flex justify-between items-center border-t border-scada-border/20 pt-2 shrink-0 font-mono text-[8px] text-scada-dimText mt-1.5">
            <div className="flex items-center gap-1.5">
              <span>STATE ESTIMATE:</span>
              <span className={`font-bold ${trusted ? "text-scada-nominal" : "text-scada-trip font-extrabold animate-pulse"}`}>
                {trusted ? "SECURE & VERIFIED" : "UNTRUSTED MEASUREMENTS"}
              </span>
            </div>
            <div className="flex items-center gap-1">
              <span>UPDATED:</span>
              <span className="text-white font-scada-nums">
                {new Date(filterData?.timestamp ?? Date.now()).toLocaleTimeString([], { hour12: false })}
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
