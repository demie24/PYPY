import React, { useState } from "react";
import { 
  ShieldAlert, Split, RefreshCw, Zap, Sliders, Heart, Info, CheckCircle2, AlertTriangle
} from "lucide-react";

interface Strategy {
  strategy: string;
  score: number;
  reason: string;
}

interface IslandInfo {
  island_id: string;
  buses: string[];
  generators: string[];
  loads: string[];
  has_generation: boolean;
  is_unstable: boolean;
  reasons: string[];
  stability_rating?: number;
}

interface L6SurvivalData {
  timestamp: number;
  survivability_score: number;
  load_retention_pct: number;
  strategy_ranking: Strategy[];
}

interface L6IslandingData {
  timestamp: number;
  active_islands: IslandInfo[];
  unstable_zones: IslandInfo[];
  healthy_zones: IslandInfo[];
  splitting_commands: any[];
}

interface L6BlackstartData {
  timestamp: number;
  active_blackstart: boolean;
  blackstart_state: string;
  step_description: string;
  progress_percentage: number;
}

interface L6BalancingData {
  timestamp: number;
  frequencies: Record<string, number>;
  mismatches: Record<string, number>;
  balancing_commands: any[];
}

interface AutonomousSurvivalPanelProps {
  survivalData: L6SurvivalData | null;
  islandingData: L6IslandingData | null;
  blackstartData: L6BlackstartData | null;
  balancingData: L6BalancingData | null;
  onSendControl: (command: string, target: string, payload?: any) => void;
}

type TabType = "overview" | "islands" | "blackstart";

export const AutonomousSurvivalPanel: React.FC<AutonomousSurvivalPanelProps> = ({ 
  survivalData, 
  islandingData, 
  blackstartData, 
  balancingData,
  onSendControl 
}) => {
  const [activeTab, setActiveTab] = useState<TabType>("overview");

  // Determine if data is present
  const hasSurvival = survivalData !== null && survivalData !== undefined;
  const hasIslanding = islandingData !== null && islandingData !== undefined;
  const hasBlackstart = blackstartData !== null && blackstartData !== undefined;
  const hasBalancing = balancingData !== null && balancingData !== undefined;

  // Extracted metrics or defaults
  const survivabilityScore = hasSurvival ? survivalData.survivability_score : 100;
  const loadRetention = hasSurvival ? survivalData.load_retention_pct : 100;
  const strategies = hasSurvival ? survivalData.strategy_ranking : [];

  const activeIslands = hasIslanding ? islandingData.active_islands : [];
  const splittingCommands = hasIslanding ? islandingData.splitting_commands : [];

  const activeBlackstart = hasBlackstart ? blackstartData.active_blackstart : false;
  const blackstartState = hasBlackstart ? blackstartData.blackstart_state : "COMPLETE";
  const blackstartDesc = hasBlackstart ? blackstartData.step_description : "System fully synchronized.";
  const blackstartProgress = hasBlackstart ? blackstartData.progress_percentage : 100;

  const frequencies = hasBalancing ? (balancingData.frequencies ?? {}) : {};
  const mismatches = hasBalancing ? (balancingData.mismatches ?? {}) : {};
  const balancingCommands = hasBalancing ? balancingData.balancing_commands : [];

  // Helper to determine strategy priority color
  const getStrategyBadge = (stratName: string) => {
    switch (stratName) {
      case "NOMINAL": return "bg-emerald-500/10 text-emerald-400 border-emerald-500/20";
      case "ISLANDING": return "bg-yellow-500/10 text-yellow-400 border-yellow-500/20";
      case "DEGRADED": return "bg-amber-500/10 text-amber-400 border-amber-500/20";
      case "BLACKSTART": return "bg-purple-500/10 text-purple-400 border-purple-500/20";
      default: return "bg-gray-500/10 text-gray-400 border-gray-500/20";
    }
  };

  return (
    <div className="bg-scada-panel border border-scada-border rounded-lg p-4 h-[300px] flex flex-col justify-between overflow-hidden relative">
      {/* Header */}
      <div className="flex justify-between items-center mb-1.5 border-b border-scada-border/40 pb-1.5 shrink-0">
        <h2 className="text-sm font-semibold tracking-wider text-scada-dimText uppercase flex items-center gap-1.5">
          <Heart size={16} className={survivabilityScore > 75 ? "text-emerald-400" : survivabilityScore > 40 ? "text-yellow-400 animate-pulse" : "text-red-500 animate-pulse"} />
          Layer 6 Autonomous Grid Survival
        </h2>
        
        {/* Navigation Tabs */}
        <div className="flex gap-1.5 mr-auto ml-4">
          {(["overview", "islands", "blackstart"] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-2.5 py-0.5 rounded text-[8px] font-mono font-bold tracking-wider uppercase transition-all ${
                activeTab === tab
                  ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 scada-text-glow"
                  : "text-scada-dimText hover:text-white border border-transparent"
              }`}
            >
              {tab === "overview" ? "Overview" : tab === "islands" ? "Islands & Balancer" : "Blackstart sequencing"}
            </button>
          ))}
        </div>

        {/* Global Survival Status Badge */}
        <div className={`px-2 py-0.5 rounded text-[8px] font-mono font-bold border ${
          activeBlackstart 
            ? "bg-purple-500/20 text-purple-400 border-purple-500/40 animate-pulse"
            : activeIslands.length > 1
            ? "bg-yellow-500/20 text-yellow-400 border-yellow-500/40 animate-pulse"
            : survivabilityScore < 50
            ? "bg-red-500/20 text-red-400 border-red-500/40 animate-bounce"
            : "bg-emerald-500/20 text-emerald-400 border-emerald-500/40"
        }`}>
          {activeBlackstart 
            ? "BLACKSTART ACTIVE" 
            : activeIslands.length > 1 
            ? `GRID ISOLATED: ${activeIslands.length} ISLANDS` 
            : "GRID STABLE"}
        </div>
      </div>

      <div className="flex-1 flex flex-col justify-between overflow-hidden mt-1">
        
        {/* TAB 1: Overview */}
        {activeTab === "overview" && (
          <div className="grid grid-cols-12 gap-3 flex-1 overflow-hidden min-h-0 pb-1">
            
            {/* Survivability Gauge & Load Retention */}
            <div className="col-span-4 flex flex-col items-center justify-center bg-scada-bg/25 border border-scada-border/20 rounded p-2 text-center h-full">
              <span className="text-[7.5px] font-mono text-scada-dimText uppercase mb-1">Grid Survivability</span>
              
              {/* Radial Score Gauge */}
              <div className="relative w-18 h-18 flex items-center justify-center">
                <svg className="w-full h-full transform -rotate-90">
                  <circle
                    cx="36"
                    cy="36"
                    r="30"
                    className="stroke-scada-bg fill-none"
                    strokeWidth="4"
                  />
                  <circle
                    cx="36"
                    cy="36"
                    r="30"
                    className={`fill-none transition-all duration-500 ${
                      survivabilityScore > 75 ? "stroke-emerald-500" : survivabilityScore > 40 ? "stroke-yellow-500" : "stroke-red-500"
                    }`}
                    strokeWidth="4"
                    strokeDasharray={2 * Math.PI * 30}
                    strokeDashoffset={2 * Math.PI * 30 * (1 - survivabilityScore / 100)}
                    strokeLinecap="round"
                  />
                </svg>
                <div className="absolute flex flex-col items-center">
                  <span className="text-sm font-bold text-white tracking-tight">{Math.round(survivabilityScore)}</span>
                  <span className="text-[6.5px] text-scada-dimText font-mono -mt-1">INDEX</span>
                </div>
              </div>

              {/* Load Retention Metric */}
              <div className="mt-2 w-full text-center">
                <div className="flex justify-between text-[7px] font-mono text-scada-dimText px-1.5">
                  <span>LOAD RETAINED:</span>
                  <span className="text-white font-bold">{Math.round(loadRetention)}%</span>
                </div>
                <div className="w-full h-1.5 bg-scada-bg rounded overflow-hidden border border-scada-border/20 mt-0.5">
                  <div
                    className="h-full bg-cyan-500 transition-all duration-500"
                    style={{ width: `${loadRetention}%` }}
                  ></div>
                </div>
              </div>
            </div>

            {/* Survival Strategy Ranking */}
            <div className="col-span-8 flex flex-col overflow-hidden h-full">
              <span className="text-[8px] text-scada-dimText uppercase font-mono font-semibold mb-1 flex items-center gap-1">
                <Sliders size={10} className="text-emerald-400" />
                Adaptive Survival Strategy Rankings:
              </span>
              
              <div className="flex-1 overflow-y-auto space-y-1 bg-scada-bg/25 border border-scada-border/20 rounded p-2 font-mono text-[8px] text-scada-dimText">
                {strategies.map((strat, i) => (
                  <div key={i} className="flex items-center justify-between border-b border-scada-border/10 pb-1 mb-1 last:border-0 last:pb-0 last:mb-0">
                    <div className="flex items-center gap-1.5">
                      <span className={`px-1 py-0.5 rounded text-[7px] border font-bold ${getStrategyBadge(strat.strategy)}`}>
                        {strat.strategy}
                      </span>
                      <span className="text-gray-400 truncate max-w-[190px]">{strat.reason}</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <span className="text-[7px] text-scada-dimText">FIT:</span>
                      <span className={`font-bold ${strat.score > 75 ? "text-emerald-400" : strat.score > 40 ? "text-yellow-400" : "text-red-400"}`}>
                        {Math.round(strat.score)}%
                      </span>
                    </div>
                  </div>
                ))}
                
                {strategies.length === 0 && (
                  <div className="flex flex-col items-center justify-center h-full text-center text-scada-dimText py-6 space-y-1">
                    <Info size={14} className="text-cyan-500" />
                    <p className="italic">Survival optimizer calculating strategy fits...</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* TAB 2: Islands & Balancer */}
        {activeTab === "islands" && (
          <div className="grid grid-cols-12 gap-3 flex-1 overflow-hidden min-h-0 pb-1">
            
            {/* Left Column: Active Islands List */}
            <div className="col-span-7 flex flex-col overflow-hidden h-full">
              <span className="text-[8px] text-scada-dimText uppercase font-mono font-semibold mb-1 flex items-center gap-1">
                <Split size={10} className="text-yellow-400" />
                Active Electrical Islands Map ({activeIslands.length}):
              </span>
              
              <div className="flex-1 overflow-y-auto space-y-2 bg-scada-bg/25 border border-scada-border/20 rounded p-2 font-mono text-[8px] text-scada-dimText">
                {activeIslands.map((island, idx) => {
                  const freq = frequencies[island.island_id] || 60.0;
                  const mismatch = mismatches[island.island_id] || 0.0;
                  const isFreqBreached = freq < 57.5 || freq > 62.5;

                  return (
                    <div key={idx} className={`p-2 rounded border transition-all ${
                      island.is_unstable 
                        ? "bg-red-500/5 border-red-500/20" 
                        : "bg-scada-bg/40 border-scada-border/25"
                    }`}>
                      <div className="flex justify-between items-center border-b border-scada-border/10 pb-1 mb-1">
                        <span className={`font-bold ${island.is_unstable ? "text-red-400 animate-pulse" : "text-emerald-400"}`}>
                          {island.island_id} {island.is_unstable ? "(UNSTABLE)" : "(ACTIVE)"}
                        </span>
                        
                        {/* Frequency Display */}
                        <div className="flex items-center gap-1">
                          <span>FREQ:</span>
                          <span className={`font-bold px-1 rounded ${
                            isFreqBreached 
                              ? "bg-red-500/20 text-red-400 border border-red-500/40 animate-pulse" 
                              : freq < 59.5 || freq > 60.5
                              ? "bg-yellow-500/10 text-yellow-400"
                              : "text-emerald-400"
                          }`}>
                            {(freq ?? 60.0).toFixed(2)} Hz
                          </span>
                        </div>
                      </div>

                      {/* Island details */}
                      <div className="grid grid-cols-2 gap-x-2 gap-y-0.5 text-[7.5px] text-scada-dimText">
                        <div className="truncate">Buses: <strong className="text-white">{island.buses.join(", ")}</strong></div>
                        <div>Generators: <strong className="text-cyan-400">{island.generators.join(", ") || "None"}</strong></div>
                        <div>Mismatch: <strong className={(mismatch ?? 0.0) < 0 ? "text-red-400" : (mismatch ?? 0.0) > 0 ? "text-yellow-400" : "text-emerald-400"}>{(mismatch ?? 0.0) > 0 ? "+" : ""}{(mismatch ?? 0.0).toFixed(1)} MW</strong></div>
                        <div>Stability: <strong className="text-white">{island.stability_rating ?? 100}%</strong></div>
                      </div>

                      {/* Warning reasons */}
                      {island.reasons && island.reasons.length > 0 && (
                        <div className="mt-1 text-[7px] text-red-400 flex items-start gap-1">
                          <AlertTriangle size={8} className="shrink-0 mt-0.5" />
                          <div className="leading-tight">{island.reasons.join(" | ")}</div>
                        </div>
                      )}
                    </div>
                  );
                })}

                {activeIslands.length === 0 && (
                  <div className="flex flex-col items-center justify-center h-full text-center text-scada-dimText py-6">
                    <CheckCircle2 size={16} className="text-emerald-400 mb-1" />
                    <p className="font-semibold text-white">Full Grid Unified</p>
                    <p className="text-[7.5px] italic">No electrical islands currently split.</p>
                  </div>
                )}
              </div>
            </div>

            {/* Right Column: Balancer & Gated Shed Controls */}
            <div className="col-span-5 flex flex-col justify-between h-full border-l border-scada-border/20 pl-3">
              <div className="space-y-2 overflow-hidden flex-1 flex flex-col">
                <span className="text-[8px] text-scada-dimText uppercase font-mono font-semibold shrink-0 flex items-center gap-1">
                  <Zap size={10} className="text-cyan-400" />
                  Gated Balancer Activity:
                </span>

                <div className="flex-1 overflow-y-auto space-y-1.5 bg-scada-bg/25 border border-scada-border/20 rounded p-1.5 font-mono text-[7px] text-scada-dimText">
                  {balancingCommands.map((cmd, idx) => (
                    <div key={idx} className="p-1 rounded bg-yellow-500/5 border border-yellow-500/10 space-y-0.5">
                      <div className="flex justify-between font-bold text-white">
                        <span>{cmd.command}</span>
                        <span className="text-yellow-400">{cmd.target}</span>
                      </div>
                      <p className="text-gray-400 leading-tight">{cmd.reason}</p>
                    </div>
                  ))}

                  {splittingCommands.map((cmd, idx) => (
                    <div key={idx} className="p-1 rounded bg-red-500/5 border border-red-500/10 space-y-0.5">
                      <div className="flex justify-between font-bold text-white">
                        <span>{cmd.command} (SPLIT)</span>
                        <span className="text-red-400">{cmd.target}</span>
                      </div>
                      <p className="text-gray-400 leading-tight">{cmd.reason}</p>
                    </div>
                  ))}

                  {balancingCommands.length === 0 && splittingCommands.length === 0 && (
                    <p className="italic text-center pt-8 text-[7.5px]">No active balancing commands generated.</p>
                  )}
                </div>
              </div>

              {/* Critical Gated Controls */}
              <div className="mt-2 pt-2 border-t border-scada-border/20 shrink-0 space-y-1">
                <button
                  onClick={() => onSendControl("SHED_LOAD", "Bus_5", { percentage: 20.0 })}
                  className="w-full py-1 text-[7.5px] font-mono font-bold tracking-wider rounded bg-yellow-500/10 hover:bg-yellow-500/20 text-yellow-400 border border-yellow-500/20 transition-all flex items-center justify-center gap-1"
                >
                  <ShieldAlert size={10} />
                  TEST SHED CRITICAL BUS_5
                </button>
              </div>
            </div>
          </div>
        )}

        {/* TAB 3: Blackstart Timeline */}
        {activeTab === "blackstart" && (
          <div className="flex flex-col justify-between flex-1 overflow-hidden h-full pb-1">
            
            {/* Header Details */}
            <div className="grid grid-cols-12 gap-3 mb-2">
              <div className="col-span-8 space-y-0.5">
                <span className="text-[8px] text-scada-dimText uppercase font-mono font-semibold block">
                  Blackstart Sequence Controller Status:
                </span>
                <span className={`text-[10px] font-mono font-bold block ${
                  activeBlackstart ? "text-purple-400 animate-pulse" : "text-emerald-400"
                }`}>
                  FSM STATE: {blackstartState}
                </span>
              </div>

              <div className="col-span-4 text-right">
                <span className="text-[8px] text-scada-dimText uppercase font-mono font-semibold block">
                  Blackstart Sync
                </span>
                <span className="text-sm font-bold text-white block">{Math.round(blackstartProgress)}%</span>
              </div>
            </div>

            {/* Progress Timeline Graphic */}
            <div className="relative w-full h-8 bg-scada-bg/50 border border-scada-border/25 rounded p-2 font-mono flex items-center justify-between overflow-hidden my-1">
              {/* Back Bar */}
              <div className="absolute left-4 right-4 h-1.5 bg-scada-bg rounded"></div>
              
              {/* Active Fill Bar */}
              <div 
                className="absolute left-4 h-1.5 bg-purple-500 rounded transition-all duration-500"
                style={{ width: `calc(${blackstartProgress}% - 32px)` }}
              ></div>

              {/* Progress Milestones */}
              {[
                { name: "COLLAPSED", p: 10 },
                { name: "MAIN GEN", p: 25 },
                { name: "PATH 1", p: 40 },
                { name: "GEN 3", p: 55 },
                { name: "PATH 2", p: 75 },
                { name: "GEN 2", p: 90 },
                { name: "RESTORED", p: 100 }
              ].map((m, i) => {
                const isActive = blackstartProgress >= m.p;
                return (
                  <div 
                    key={i} 
                    className="relative flex flex-col items-center z-10"
                    style={{ left: `0%` }}
                  >
                    <div className={`w-3.5 h-3.5 rounded-full border flex items-center justify-center text-[6px] font-bold transition-all ${
                      isActive 
                        ? "bg-purple-500 border-purple-400 text-white" 
                        : "bg-scada-bg border-scada-border text-scada-dimText"
                    }`}>
                      {i + 1}
                    </div>
                    <span className="text-[5.5px] font-mono text-scada-dimText uppercase mt-1 leading-none tracking-tight">
                      {m.name}
                    </span>
                  </div>
                );
              })}
            </div>

            {/* Steps & Descriptions */}
            <div className="bg-scada-bg/25 border border-scada-border/20 rounded p-2.5 font-mono text-[8px] text-scada-dimText space-y-1.5 flex-1 overflow-y-auto mt-2">
              <span className="font-bold text-gray-300 block border-b border-scada-border/20 pb-0.5">
                Current Sequence Step:
              </span>
              <p className="text-white leading-relaxed">{blackstartDesc}</p>
              
              {activeBlackstart && (
                <div className="mt-2 p-1.5 rounded bg-purple-500/5 border border-purple-500/10 text-[7.5px] text-purple-300 animate-pulse flex items-center gap-1.5 leading-tight">
                  <RefreshCw size={10} className="animate-spin shrink-0" />
                  Blackstart Engine is executing automatic recovery step. Stand by for telemetry update.
                </div>
              )}
            </div>

          </div>
        )}

      </div>
    </div>
  );
};
