import React, { useState } from "react";
import { 
  Shield, AlertTriangle, RefreshCw, CheckCircle, XCircle
} from "lucide-react";

interface AdaptiveRecoveryData {
  timestamp: number;
  optimization_score: number;
  voltage_stability_score: number;
  thermal_loading_score: number;
  restoration_speed_score: number;
  switching_operations_score: number;
  cascading_risk_score: number;
  rollback_probability_score: number;
  isolated_load_count_score: number;
  instability_risk_score: number;
  historical_confidence: number;
  total_successful_runs: number;
  total_failed_runs: number;
}

interface ContainmentData {
  timestamp: number;
  propagation_zones: string[];
  instability_spread_risk: number;
  isolation_boundary: string[];
}

interface DegradedModeData {
  timestamp: number;
  active_degraded_mode: boolean;
  critical_buses_secured: string[];
  load_shedding_active: boolean;
  load_shed_summary: Record<string, number>;
  survival_commands: Array<{
    command: string;
    target: string;
    percentage: number;
    source: string;
  }>;
}

interface AdaptiveRecoveryPanelProps {
  adaptiveRecoveryData: AdaptiveRecoveryData | null;
  containmentData: ContainmentData | null;
  degradedModeData: DegradedModeData | null;
  onSendControl: (command: string, target: string, payload?: any) => void;
}

type TabType = "metrics" | "containment" | "degraded" | "memory";

export const AdaptiveRecoveryPanel: React.FC<AdaptiveRecoveryPanelProps> = ({
  adaptiveRecoveryData,
  containmentData,
  degradedModeData,
  onSendControl
}) => {
  const [activeTab, setActiveTab] = useState<TabType>("metrics");

  const hasRecoveryData = adaptiveRecoveryData !== null && adaptiveRecoveryData !== undefined;
  const hasContainmentData = containmentData !== null && containmentData !== undefined;
  const hasDegradedData = degradedModeData !== null && degradedModeData !== undefined;

  // Defaults
  const optScore = hasRecoveryData ? (adaptiveRecoveryData.optimization_score ?? 100.0) : 100.0;
  const histConfidence = hasRecoveryData ? (adaptiveRecoveryData.historical_confidence ?? 1.0) : 1.0;
  const successRuns = hasRecoveryData ? (adaptiveRecoveryData.total_successful_runs ?? 0) : 0;
  const failedRuns = hasRecoveryData ? (adaptiveRecoveryData.total_failed_runs ?? 0) : 0;

  const spreadRisk = hasContainmentData ? (containmentData.instability_spread_risk ?? 0.0) : 0.0;
  const propZones = hasContainmentData ? containmentData.propagation_zones : [];
  const isoBoundary = hasContainmentData ? containmentData.isolation_boundary : [];

  const isDegraded = hasDegradedData ? degradedModeData.active_degraded_mode : false;
  const isLoadShedding = hasDegradedData ? degradedModeData.load_shedding_active : false;
  const securedBuses = hasDegradedData ? degradedModeData.critical_buses_secured : ["Bus_5", "Bus_8", "Bus_6"];
  const loadShedSummary = hasDegradedData ? degradedModeData.load_shed_summary : {};
  const survivalCmds = hasDegradedData ? degradedModeData.survival_commands : [];

  const getOptScoreColor = (score: number) => {
    if (score >= 85) return "text-emerald-400";
    if (score >= 70) return "text-yellow-400";
    return "text-red-400";
  };

  const getRiskBadgeColor = (risk: number) => {
    if (risk >= 0.75) return "bg-red-500/20 text-red-400 border-red-500/40 animate-pulse";
    if (risk >= 0.40) return "bg-yellow-500/20 text-yellow-400 border-yellow-500/40";
    return "bg-emerald-500/20 text-emerald-400 border-emerald-500/40";
  };

  const getRiskText = (risk: number) => {
    if (risk >= 0.75) return "CRITICAL CASCADE RISK";
    if (risk >= 0.40) return "MEDIUM RISK";
    return "STABLE / LOW RISK";
  };

  const executeContainment = (breakerId: string) => {
    onSendControl("OPEN", breakerId, { source: "HMI_CONTAINMENT" });
  };

  const executeAllContainment = () => {
    isoBoundary.forEach(bId => {
      onSendControl("OPEN", bId, { source: "HMI_CONTAINMENT" });
    });
  };

  return (
    <div className="bg-scada-panel border border-scada-border rounded-lg p-4 h-[300px] flex flex-col justify-between overflow-hidden relative">
      {/* Header */}
      <div className="flex justify-between items-center mb-1.5 border-b border-scada-border/40 pb-1.5 shrink-0">
        <h2 className="text-sm font-semibold tracking-wider text-scada-dimText uppercase flex items-center gap-1.5">
          <Shield size={16} className="text-emerald-400" />
          Layer 6 Adaptive Recovery Intelligence
        </h2>
        
        {/* Navigation Tabs */}
        <div className="flex gap-1.5 mr-auto ml-4">
          {(["metrics", "containment", "degraded", "memory"] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-2 py-0.5 rounded text-[8px] font-mono font-bold tracking-wider uppercase transition-all ${
                activeTab === tab
                  ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 scada-text-glow"
                  : "text-scada-dimText hover:text-white border border-transparent"
              }`}
            >
              {tab === "metrics" ? "Optimization Score" : tab === "containment" ? "Containment" : tab === "degraded" ? "Degraded Ops" : "Recovery Memory"}
            </button>
          ))}
        </div>

        {/* Global Degraded Status Badge */}
        <div className={`px-2 py-0.5 rounded text-[8px] font-mono font-bold border ${
          isDegraded ? "bg-red-500/20 text-red-400 border-red-500/40 animate-pulse" : "bg-emerald-500/20 text-emerald-400 border-emerald-500/40"
        }`}>
          GRID MODE: {isDegraded ? "DEGRADED" : "NOMINAL"}
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col justify-between overflow-hidden mt-1">
        
        {/* TAB 1: Metrics */}
        {activeTab === "metrics" && (
          <div className="grid grid-cols-12 gap-3 flex-1 overflow-hidden min-h-0 pb-1">
            {/* Optimization Score gauge */}
            <div className="col-span-4 flex flex-col items-center justify-center border-r border-scada-border/20 pr-3">
              <span className="text-[8px] text-scada-dimText uppercase font-mono font-bold text-center mb-1">
                Optimization Score
              </span>
              <div className="relative flex items-center justify-center h-20 w-20">
                <svg className="w-full h-full transform -rotate-90">
                  <circle
                    cx="40"
                    cy="40"
                    r="32"
                    className="stroke-scada-bg fill-none"
                    strokeWidth="6"
                  />
                  <circle
                    cx="40"
                    cy="40"
                    r="32"
                    className="stroke-emerald-500/20 fill-none"
                    strokeWidth="6"
                  />
                  <circle
                    cx="40"
                    cy="40"
                    r="32"
                    className="stroke-emerald-500 fill-none transition-all duration-500"
                    strokeWidth="6"
                    strokeDasharray={2 * Math.PI * 32}
                    strokeDashoffset={2 * Math.PI * 32 * (1 - optScore / 100)}
                    strokeLinecap="round"
                  />
                </svg>
                <div className="absolute flex flex-col items-center justify-center">
                  <span className={`text-xl font-bold font-mono ${getOptScoreColor(optScore)} scada-text-glow`}>
                    {optScore.toFixed(0)}
                  </span>
                  <span className="text-[6.5px] text-scada-dimText font-mono uppercase">points</span>
                </div>
              </div>
              <div className="text-[6.5px] font-mono text-center text-scada-dimText mt-1.5 max-w-[90px] leading-tight">
                Calculated stability, loading, speed & rollback risk vector.
              </div>
            </div>

            {/* Score Grid details */}
            <div className="col-span-8 flex flex-col justify-between overflow-hidden h-full">
              <span className="text-[8px] text-scada-dimText uppercase font-mono font-semibold mb-1">
                Restoration Parameter Scoring Matrix:
              </span>
              <div className="flex-1 overflow-y-auto grid grid-cols-2 gap-1.5 p-1.5 bg-scada-bg/25 border border-scada-border/20 rounded font-mono text-[7.5px] text-scada-dimText">
                <div className="flex justify-between border-b border-scada-border/10 pb-0.5">
                  <span>Voltage Stability:</span>
                  <strong className="text-white">{hasRecoveryData ? (adaptiveRecoveryData.voltage_stability_score ?? 100.0).toFixed(1) : "100.0"}</strong>
                </div>
                <div className="flex justify-between border-b border-scada-border/10 pb-0.5">
                  <span>Thermal Loading:</span>
                  <strong className="text-white">{hasRecoveryData ? (adaptiveRecoveryData.thermal_loading_score ?? 100.0).toFixed(1) : "100.0"}</strong>
                </div>
                <div className="flex justify-between border-b border-scada-border/10 pb-0.5">
                  <span>Restoration Speed:</span>
                  <strong className="text-white">{hasRecoveryData ? (adaptiveRecoveryData.restoration_speed_score ?? 100.0).toFixed(1) : "100.0"}</strong>
                </div>
                <div className="flex justify-between border-b border-scada-border/10 pb-0.5">
                  <span>Switch Operations:</span>
                  <strong className="text-white">{hasRecoveryData ? (adaptiveRecoveryData.switching_operations_score ?? 100.0).toFixed(1) : "100.0"}</strong>
                </div>
                <div className="flex justify-between border-b border-scada-border/10 pb-0.5">
                  <span>Cascading Risk:</span>
                  <strong className="text-white">{hasRecoveryData ? (adaptiveRecoveryData.cascading_risk_score ?? 100.0).toFixed(1) : "100.0"}</strong>
                </div>
                <div className="flex justify-between border-b border-scada-border/10 pb-0.5">
                  <span>Rollback Guard:</span>
                  <strong className="text-white">{hasRecoveryData ? (adaptiveRecoveryData.rollback_probability_score ?? 100.0).toFixed(1) : "100.0"}</strong>
                </div>
                <div className="flex justify-between border-b border-scada-border/10 pb-0.5">
                  <span>Isolated Load:</span>
                  <strong className="text-white">{hasRecoveryData ? (adaptiveRecoveryData.isolated_load_count_score ?? 100.0).toFixed(1) : "100.0"}</strong>
                </div>
                <div className="flex justify-between border-b border-scada-border/10 pb-0.5">
                  <span>Instability Risk (ML):</span>
                  <strong className="text-white">{hasRecoveryData ? (adaptiveRecoveryData.instability_risk_score ?? 100.0).toFixed(1) : "100.0"}</strong>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* TAB 2: Containment */}
        {activeTab === "containment" && (
          <div className="grid grid-cols-12 gap-3 flex-1 overflow-hidden min-h-0 pb-1">
            <div className="col-span-8 flex flex-col overflow-hidden h-full">
              <span className="text-[8px] text-scada-dimText uppercase font-mono font-semibold mb-1">
                Active Cascading Risk Propagation Map:
              </span>
              
              <div className="flex-1 overflow-y-auto space-y-1.5 p-2 bg-scada-bg/20 border border-scada-border/20 rounded font-mono text-[7.5px] text-scada-dimText">
                <div className="flex justify-between items-center">
                  <span>Cascade Threat Propagation Risk:</span>
                  <span className={`px-1.5 py-0.5 rounded text-[7px] font-bold border ${getRiskBadgeColor(spreadRisk)}`}>
                    {getRiskText(spreadRisk)} ({(spreadRisk * 100).toFixed(0)}%)
                  </span>
                </div>

                <div className="border-t border-scada-border/10 pt-1.5">
                  <span className="text-gray-300 font-bold block mb-1">Traced Propagation Zones (Alternate Lines):</span>
                  {propZones.length > 0 ? (
                    <div className="flex flex-wrap gap-1">
                      {propZones.map((lid) => (
                        <span key={lid} className="bg-red-500/10 px-1 border border-red-500/30 rounded text-[7px] text-red-400">
                          {lid}
                        </span>
                      ))}
                    </div>
                  ) : (
                    <p className="text-emerald-400 italic text-[7px]">No cascading overload propagation path traced.</p>
                  )}
                </div>

                <div className="border-t border-scada-border/10 pt-1.5">
                  <span className="text-gray-300 font-bold block mb-1">Recommended Containment Boundary:</span>
                  {isoBoundary.length > 0 ? (
                    <div className="flex flex-wrap items-center gap-1.5">
                      {isoBoundary.map((lid) => (
                        <div key={lid} className="flex items-center gap-1 bg-yellow-500/10 px-1.5 py-0.5 border border-yellow-500/30 rounded text-[7px] text-yellow-400">
                          <span>Open {lid}</span>
                          <button
                            onClick={() => executeContainment(lid)}
                            className="ml-1 text-[6.5px] bg-yellow-500/20 hover:bg-yellow-500/40 text-yellow-300 px-1 rounded font-bold"
                          >
                            ISOLATE
                          </button>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-emerald-400 italic text-[7px]">Grid containment boundary is clear. Isolation not required.</p>
                  )}
                </div>
              </div>
            </div>

            <div className="col-span-4 flex flex-col justify-center gap-2 border-l border-scada-border/20 pl-3">
              <span className="text-[8px] text-scada-dimText uppercase font-mono font-bold text-center block">
                Containment Action
              </span>
              <button
                disabled={isoBoundary.length === 0}
                onClick={executeAllContainment}
                className={`w-full py-2 text-[8px] font-mono font-bold tracking-wider rounded transition-all uppercase flex items-center justify-center gap-1 ${
                  isoBoundary.length > 0
                    ? "bg-yellow-500/10 hover:bg-yellow-500/20 text-yellow-400 border border-yellow-500/30 cursor-pointer"
                    : "bg-gray-500/5 text-gray-500 border border-gray-500/10 cursor-not-allowed"
                }`}
              >
                <AlertTriangle size={10} />
                ENGAGE ALL CONTAINMENT
              </button>
              <p className="text-[6.5px] font-mono text-center text-scada-dimText mt-1 leading-normal italic">
                Will command SCADA to open all boundary switches to quarantine compromised components.
              </p>
            </div>
          </div>
        )}

        {/* TAB 3: Degraded Ops */}
        {activeTab === "degraded" && (
          <div className="grid grid-cols-12 gap-3 flex-1 overflow-hidden min-h-0 pb-1">
            {/* Critical Bus Grid status */}
            <div className="col-span-6 flex flex-col overflow-hidden h-full">
              <span className="text-[8px] text-scada-dimText uppercase font-mono font-semibold mb-1">
                Critical Customer Load Status:
              </span>
              <div className="flex-1 overflow-y-auto space-y-1.5 p-1.5 bg-scada-bg/25 border border-scada-border/20 rounded font-mono text-[7px] text-scada-dimText">
                <div className="flex justify-between items-center border-b border-scada-border/10 pb-0.5">
                  <span className="font-bold text-gray-300">Bus_5 (High Priority):</span>
                  {securedBuses.includes("Bus_5") ? (
                    <span className="text-emerald-400 font-bold flex items-center gap-0.5"><CheckCircle size={8} /> SECURED</span>
                  ) : (
                    <span className="text-red-400 font-bold flex items-center gap-0.5"><XCircle size={8} /> SHED/OFFLINE</span>
                  )}
                </div>
                <div className="flex justify-between items-center border-b border-scada-border/10 pb-0.5">
                  <span className="font-bold text-gray-300">Bus_8 (Medium Priority):</span>
                  {securedBuses.includes("Bus_8") ? (
                    <span className="text-emerald-400 font-bold flex items-center gap-0.5"><CheckCircle size={8} /> SECURED</span>
                  ) : (
                    <span className="text-red-400 font-bold flex items-center gap-0.5"><XCircle size={8} /> SHED/OFFLINE</span>
                  )}
                </div>
                <div className="flex justify-between items-center border-b border-scada-border/10 pb-0.5">
                  <span className="font-bold text-gray-300">Bus_6 (Low Priority):</span>
                  {securedBuses.includes("Bus_6") ? (
                    <span className="text-emerald-400 font-bold flex items-center gap-0.5"><CheckCircle size={8} /> SECURED</span>
                  ) : (
                    <span className="text-red-400 font-bold flex items-center gap-0.5"><XCircle size={8} /> SHED/OFFLINE</span>
                  )}
                </div>
                
                <div className="pt-1.5 text-[6.5px] italic text-scada-dimText">
                  * Load shedding logic prioritizes Bus_6 first, then Bus_8, conserving Bus_5.
                </div>
              </div>
            </div>

            {/* Load Shed summary table */}
            <div className="col-span-6 flex flex-col overflow-hidden h-full">
              <span className="text-[8px] text-scada-dimText uppercase font-mono font-semibold mb-1">
                Active Curtailments & Commands:
              </span>
              <div className="flex-1 overflow-y-auto space-y-1.5 p-1.5 bg-scada-bg/20 border border-scada-border/20 rounded font-mono text-[7px] text-scada-dimText">
                <span className="text-gray-300 font-bold block mb-1">Shed Factors:</span>
                {isLoadShedding && Object.keys(loadShedSummary).length > 0 ? (
                  <div className="space-y-1">
                    {Object.entries(loadShedSummary).map(([busName, pct]) => (
                      <div key={busName} className="flex justify-between text-yellow-400 font-bold">
                        <span>{busName}:</span>
                        <span>-{pct}% load</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-emerald-400 italic mb-2 text-[6.5px]">No active load curtailments.</p>
                )}

                <div className="border-t border-scada-border/10 pt-1.5">
                  <span className="text-gray-300 font-bold block mb-0.5">Survival Logs:</span>
                  <div className="space-y-1 overflow-y-auto max-h-[50px] pr-0.5">
                    {survivalCmds.map((cmd, idx) => (
                      <div key={idx} className="border-b border-scada-border/5 pb-0.5">
                        <span className="text-white">SHED {cmd.target} to {100 - cmd.percentage}%</span>
                      </div>
                    ))}
                    {survivalCmds.length === 0 && (
                      <p className="text-gray-500 italic text-[6.5px]">No recent survival logs.</p>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* TAB 4: Recovery Memory */}
        {activeTab === "memory" && (
          <div className="grid grid-cols-12 gap-3 flex-1 overflow-hidden min-h-0 pb-1">
            {/* Historical Stats */}
            <div className="col-span-5 flex flex-col justify-between h-full border-r border-scada-border/20 pr-3">
              <div>
                <span className="text-[8px] text-scada-dimText uppercase font-mono font-bold text-center block mb-1">
                  Memory Confidence
                </span>
                <div className="flex justify-between items-center text-[8px] font-mono text-scada-dimText">
                  <span>Laplace Confidence:</span>
                  <strong className="text-white">{(histConfidence * 100).toFixed(0)}%</strong>
                </div>
                <div className="w-full h-1.5 bg-scada-bg rounded overflow-hidden border border-scada-border/40 mt-1">
                  <div
                    className={`h-full transition-all duration-500 ${
                      histConfidence > 0.8 ? "bg-emerald-500" : histConfidence > 0.5 ? "bg-yellow-500" : "bg-red-500"
                    }`}
                    style={{ width: `${histConfidence * 100}%` }}
                  ></div>
                </div>
              </div>

              <div className="bg-scada-bg/40 p-2 rounded border border-scada-border/25 font-mono text-[7px] text-scada-dimText space-y-1">
                <span className="font-bold text-gray-300 block border-b border-scada-border/20 pb-0.5">Memory Counters:</span>
                <p>Successful Runs: <strong className="text-emerald-400">{successRuns}</strong></p>
                <p>Failed / Rollbacks: <strong className="text-red-400">{failedRuns}</strong></p>
              </div>

              <button
                onClick={() => onSendControl("RESET_L6_RECOVERY", "SYSTEM")}
                className="w-full py-1 text-[7.5px] font-mono font-bold tracking-wider rounded bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/30 transition-all uppercase flex items-center justify-center gap-0.5"
              >
                <RefreshCw size={8} /> CLEAR MEMORY CACHE
              </button>
            </div>

            {/* Breaker details */}
            <div className="col-span-7 flex flex-col overflow-hidden h-full">
              <span className="text-[8px] text-scada-dimText uppercase font-mono font-semibold mb-1">
                Learned Breaker Success Probabilities:
              </span>
              <div className="flex-1 overflow-y-auto space-y-1 bg-scada-bg/20 border border-scada-border/20 rounded p-1.5 font-mono text-[7.5px] text-scada-dimText">
                <div className="flex justify-between border-b border-scada-border/5">
                  <span>Tie-Link L7_8:</span>
                  <span className="text-emerald-400 font-bold">100% success</span>
                </div>
                <div className="flex justify-between border-b border-scada-border/5">
                  <span>Sectionalizer L4_5:</span>
                  <span className="text-emerald-400 font-bold">100% success</span>
                </div>
                <div className="flex justify-between border-b border-scada-border/5">
                  <span>Grid Feeders (L1_4, L2_5):</span>
                  <span className="text-cyan-400 font-bold">92% expected</span>
                </div>
                <div className="flex justify-between border-b border-scada-border/5">
                  <span>Cyber-Hacked Breaker:</span>
                  <span className="text-red-400 font-bold">Rollback history detected</span>
                </div>
                <p className="text-[6px] text-gray-500 italic mt-2">
                  * Computes success probability using Laplace smoothing. Helps the path ranker select highly stable components.
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
