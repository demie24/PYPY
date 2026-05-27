import React, { useState } from "react";
import { 
  ShieldAlert, Activity, Sliders, CheckCircle2, TrendingUp
} from "lucide-react";

interface ProactiveAction {
  command: string;
  target: string;
  reason: string;
}

interface L6PredictiveStabilityData {
  timestamp: number;
  collapse_probability: number;
  survivability_horizon: number;
  predicted_overloads: any[];
  propagation_trajectory: string[];
}

interface L6SurvivalForecastData {
  timestamp: number;
  do_nothing_curve: number[];
  mitigated_curve: number[];
  recovery_success_prob: number;
  degraded_operation_duration: number;
}

interface L6ProactiveActionsData {
  timestamp: number;
  proactive_rerouting_active: boolean;
  preemptive_isolation_active: boolean;
  proactive_actions: ProactiveAction[];
  side_effects: Record<string, any>;
}

interface L6SelfPreservationData {
  timestamp: number;
  active_policy: string;
  preservation_rules: string[];
  proactive_commands: ProactiveAction[];
}

interface PredictiveStabilizationPanelProps {
  predictiveStability: L6PredictiveStabilityData | null;
  survivalForecast: L6SurvivalForecastData | null;
  proactiveActions: L6ProactiveActionsData | null;
  selfPreservation: L6SelfPreservationData | null;
  proactiveAutoMode: boolean;
  onSendControl: (command: string, target: string, payload?: any) => void;
}

type TabType = "overview" | "trajectories" | "policy";

export const PredictiveStabilizationPanel: React.FC<PredictiveStabilizationPanelProps> = ({ 
  predictiveStability, 
  survivalForecast, 
  proactiveActions, 
  selfPreservation,
  proactiveAutoMode,
  onSendControl 
}) => {
  const [activeTab, setActiveTab] = useState<TabType>("overview");

  const hasStability = predictiveStability !== null && predictiveStability !== undefined;
  const hasForecast = survivalForecast !== null && survivalForecast !== undefined;
  const hasActions = proactiveActions !== null && proactiveActions !== undefined;
  const hasPreservation = selfPreservation !== null && selfPreservation !== undefined;

  const collapseProb = hasStability ? predictiveStability.collapse_probability : 0.0;
  const horizon = hasStability ? predictiveStability.survivability_horizon : 999.0;

  const doNothingCurve = hasForecast ? survivalForecast.do_nothing_curve : Array(10).fill(100.0);
  const mitigatedCurve = hasForecast ? survivalForecast.mitigated_curve : Array(10).fill(100.0);
  const successProb = hasForecast ? survivalForecast.recovery_success_prob : 100.0;

  const actions = hasActions ? proactiveActions.proactive_actions : [];
  const sideEffects = hasActions ? proactiveActions.side_effects : {};

  const activePolicy = hasPreservation ? selfPreservation.active_policy : "NOMINAL";
  const rules = hasPreservation ? selfPreservation.preservation_rules : ["Grid operations nominal."];

  const getPolicyBadge = (policy: string) => {
    switch (policy) {
      case "NOMINAL": return "bg-emerald-500/10 text-emerald-400 border-emerald-500/20";
      case "PREVENTATIVE": return "bg-cyan-500/10 text-cyan-400 border-cyan-500/20";
      case "SELF_PRESERVATION": return "bg-amber-500/10 text-amber-400 border-amber-500/20";
      case "EMERGENCY_DEGRADATION": return "bg-red-500/10 text-red-400 border-red-500/20 animate-pulse";
      default: return "bg-gray-500/10 text-gray-400 border-gray-500/20";
    }
  };

  return (
    <div className="bg-scada-panel border border-scada-border rounded-lg p-4 h-[300px] flex flex-col justify-between overflow-hidden relative">
      {/* Header */}
      <div className="flex justify-between items-center mb-1.5 border-b border-scada-border/40 pb-1.5 shrink-0">
        <h2 className="text-sm font-semibold tracking-wider text-scada-dimText uppercase flex items-center gap-1.5">
          <Activity size={16} className={collapseProb > 40 ? "text-red-500 animate-pulse" : "text-emerald-400"} />
          Layer 6 Predictive Stabilization
        </h2>
        
        {/* Navigation Tabs */}
        <div className="flex gap-1.5 mr-auto ml-4">
          {(["overview", "trajectories", "policy"] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-2.5 py-0.5 rounded text-[8px] font-mono font-bold tracking-wider uppercase transition-all ${
                activeTab === tab
                  ? "bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 scada-text-glow"
                  : "text-scada-dimText hover:text-white border border-transparent"
              }`}
            >
              {tab === "overview" ? "Overview" : tab === "trajectories" ? "Stabilization Futures" : "Preservation Policy"}
            </button>
          ))}
        </div>

        {/* Proactive Mode Control */}
        <button
          onClick={() => onSendControl("TOGGLE_PROACTIVE_AUTO", "SYSTEM", { proactive_auto: !proactiveAutoMode })}
          className={`px-2 py-0.5 rounded text-[8px] font-mono font-bold border transition-all ${
            proactiveAutoMode
              ? "bg-cyan-500/20 text-cyan-400 border-cyan-500/40 scada-text-glow"
              : "bg-gray-500/10 text-gray-400 border-gray-500/20"
          }`}
        >
          {proactiveAutoMode ? "PROACTIVE: AUTO" : "PROACTIVE: ADVISORY"}
        </button>
      </div>

      <div className="flex-1 flex flex-col justify-between overflow-hidden mt-1">
        
        {/* TAB 1: Overview */}
        {activeTab === "overview" && (
          <div className="grid grid-cols-12 gap-3 flex-1 overflow-hidden min-h-0 pb-1">
            
            {/* Collapse Probability Radial Gauge */}
            <div className="col-span-4 flex flex-col items-center justify-center bg-scada-bg/25 border border-scada-border/20 rounded p-2 text-center h-full">
              <span className="text-[7.5px] font-mono text-scada-dimText uppercase mb-1">Collapse Probability</span>
              
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
                      collapseProb > 75 ? "stroke-red-500" : collapseProb > 40 ? "stroke-yellow-500" : "stroke-emerald-500"
                    }`}
                    strokeWidth="4"
                    strokeDasharray={2 * Math.PI * 30}
                    strokeDashoffset={2 * Math.PI * 30 * (1 - collapseProb / 100)}
                    strokeLinecap="round"
                  />
                </svg>
                <div className="absolute flex flex-col items-center">
                  <span className="text-sm font-bold text-white tracking-tight">{Math.round(collapseProb)}%</span>
                  <span className="text-[6.5px] text-scada-dimText font-mono -mt-1">COLLAPSE</span>
                </div>
              </div>
              
              {/* Survival Horizon indicator */}
              <div className="mt-2 text-center w-full">
                <span className="text-[6.5px] text-scada-dimText font-mono block">SURVIVAL HORIZON</span>
                <span className={`text-[10px] font-mono font-bold ${
                  horizon < 15.0 ? "text-red-500 animate-pulse" : horizon < 60.0 ? "text-yellow-500" : "text-emerald-400"
                }`}>
                  {horizon === 999.0 ? "NOMINAL (STABLE)" : `${horizon} SEC`}
                </span>
              </div>
            </div>

            {/* Proactive Actions / Side Effects list */}
            <div className="col-span-8 flex flex-col overflow-hidden h-full">
              <span className="text-[8px] text-scada-dimText uppercase font-mono font-semibold mb-1 flex items-center gap-1">
                <Sliders size={10} className="text-cyan-400" />
                Pre-Failure Proactive Recommendations:
              </span>
              
              <div className="flex-1 overflow-y-auto space-y-1.5 bg-scada-bg/25 border border-scada-border/20 rounded p-2 font-mono text-[8px] text-scada-dimText">
                {actions.map((act, i) => {
                  const s_effect = sideEffects[act.target];
                  return (
                    <div key={i} className="p-1.5 rounded bg-cyan-500/5 border border-cyan-500/10 flex justify-between items-center gap-2">
                      <div className="flex-1 min-w-0">
                        <div className="flex justify-between font-bold text-white mb-0.5">
                          <span>{act.command}</span>
                          <span className="text-cyan-400">{act.target}</span>
                        </div>
                        <p className="text-[7.5px] text-gray-400 leading-tight truncate">{act.reason}</p>
                        {s_effect && (
                          <p className="text-[7.5px] text-yellow-400 leading-tight mt-0.5">
                            Side effect: Isolates {s_effect.isolated_loads.join(", ")}
                          </p>
                        )}
                      </div>
                      
                      {!proactiveAutoMode && (
                        <button
                          onClick={() => onSendControl(act.command, act.target, { source: "PROACTIVE_ENGINE", reason: act.reason })}
                          className="px-2 py-0.5 rounded bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-400 border border-cyan-500/30 text-[7px] font-bold uppercase transition-all shrink-0"
                        >
                          Execute
                        </button>
                      )}
                    </div>
                  );
                })}
                
                {actions.length === 0 && (
                  <div className="flex flex-col items-center justify-center h-full text-center text-scada-dimText py-6 space-y-1">
                    <CheckCircle2 size={16} className="text-emerald-400" />
                    <p className="font-semibold text-white">No Impending Overloads</p>
                    <p className="italic text-[7.5px]">Proactive rerouting/isolation models standby.</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* TAB 2: Stabilization Futures */}
        {activeTab === "trajectories" && (
          <div className="flex flex-col justify-between flex-1 overflow-hidden h-full pb-1">
            <span className="text-[8px] text-scada-dimText uppercase font-mono font-semibold mb-1 flex items-center gap-1 shrink-0">
              <TrendingUp size={10} className="text-cyan-400" />
              10-Second Lookahead Survivability Forecast Curves (Do Nothing vs. Mitigated):
            </span>
            
            {/* SVG Line Chart */}
            <div className="flex-1 min-h-0 bg-scada-bg/40 border border-scada-border/25 rounded relative p-2">
              <div className="absolute top-2 right-2 flex gap-3 text-[7px] font-mono">
                <span className="flex items-center gap-1 text-red-500 font-bold">
                  <span className="w-2 h-0.5 bg-red-500 inline-block"></span> DO NOTHING
                </span>
                <span className="flex items-center gap-1 text-emerald-400 font-bold">
                  <span className="w-2 h-0.5 bg-emerald-400 inline-block"></span> MITIGATED
                </span>
              </div>

              <div className="w-full h-full pt-4 flex items-end justify-between font-mono text-[7px] relative">
                {/* Horizontal gridlines */}
                {[0, 25, 50, 75, 100].map((gl) => (
                  <div key={gl} className="absolute left-0 right-0 border-t border-scada-border/5 text-scada-dimText/40 flex justify-between" style={{ bottom: `${gl}%` }}>
                    <span>{gl}</span>
                  </div>
                ))}
                
                {/* SVG path rendering */}
                <svg className="absolute inset-0 w-full h-full pt-4 px-3" viewBox="0 0 100 100" preserveAspectRatio="none">
                  {/* Do Nothing Line */}
                  <path 
                    d={`M 0,${100 - doNothingCurve[0]} ${doNothingCurve.map((val, idx) => `L ${idx * 11.1},${100 - val}`).join(" ")}`}
                    fill="none"
                    stroke="#EF4444"
                    strokeWidth="2"
                  />
                  {/* Mitigated Line */}
                  <path 
                    d={`M 0,${100 - mitigatedCurve[0]} ${mitigatedCurve.map((val, idx) => `L ${idx * 11.1},${100 - val}`).join(" ")}`}
                    fill="none"
                    stroke="#10B981"
                    strokeWidth="2"
                  />
                </svg>

                {/* Timeline axis */}
                <div className="absolute bottom-0 left-0 right-0 flex justify-between text-scada-dimText px-1.5">
                  <span>t</span>
                  <span>t+2s</span>
                  <span>t+4s</span>
                  <span>t+6s</span>
                  <span>t+8s</span>
                  <span>t+10s</span>
                </div>
              </div>
            </div>

            {/* Success rates / diagnostic summary footer */}
            <div className="grid grid-cols-2 gap-2 mt-2 pt-2 border-t border-scada-border/20 shrink-0 font-mono text-[8px] text-scada-dimText">
              <div>
                STABILIZATION SUCCESS PROBABILITY: <span className="text-white font-bold">{successProb}%</span>
              </div>
              <div className="text-right">
                DEGRADED GRID LIFE EXPECTANCY: <span className="text-white font-bold">{horizon === 999.0 ? "INFINITE" : `${horizon}s`}</span>
              </div>
            </div>
          </div>
        )}

        {/* TAB 3: Preservation Policy */}
        {activeTab === "policy" && (
          <div className="grid grid-cols-12 gap-3 flex-1 overflow-hidden min-h-0 pb-1">
            
            {/* Left Column: Active Policy Status */}
            <div className="col-span-5 flex flex-col justify-between h-full bg-scada-bg/25 border border-scada-border/20 rounded p-2.5">
              <div>
                <span className="text-[8.5px] text-scada-dimText font-mono uppercase block mb-1">Preservation Policy Mode</span>
                <span className={`px-2 py-0.5 rounded text-[10px] border font-bold font-mono tracking-wider block text-center ${getPolicyBadge(activePolicy)}`}>
                  {activePolicy}
                </span>
              </div>

              {/* Proactive Shed test button */}
              <div className="mt-2 space-y-1">
                <button
                  onClick={() => onSendControl("SHED_LOAD", "Bus_6", { percentage: 25.0, source: "PRESERVATION_POLICY" })}
                  className="w-full py-1 text-[7.5px] font-mono font-bold tracking-wider rounded bg-yellow-500/10 hover:bg-yellow-500/20 text-yellow-400 border border-yellow-500/20 transition-all flex items-center justify-center gap-1"
                >
                  <ShieldAlert size={10} />
                  PROACTIVE SHED BUS_6
                </button>
              </div>
            </div>

            {/* Right Column: Rules Checklist */}
            <div className="col-span-7 flex flex-col overflow-hidden h-full">
              <span className="text-[8px] text-scada-dimText uppercase font-mono font-semibold mb-1 flex items-center gap-1">
                <Sliders size={10} className="text-cyan-400" />
                Active Preservation Rules:
              </span>
              
              <div className="flex-1 overflow-y-auto space-y-1.5 bg-scada-bg/25 border border-scada-border/20 rounded p-2 font-mono text-[7.5px] text-scada-dimText">
                {rules.map((rule, idx) => (
                  <div key={idx} className="flex items-start gap-1.5 leading-tight text-white border-b border-scada-border/10 pb-1 mb-1 last:border-0 last:pb-0 last:mb-0">
                    <span className="text-cyan-400 font-bold shrink-0">▶</span>
                    <span>{rule}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

      </div>
    </div>
  );
};
