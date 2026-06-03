import React, { useState } from "react";
import { Activity, ShieldCheck, ShieldAlert, AlertTriangle, Cpu, TrendingUp } from "lucide-react";
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid } from "recharts";

interface HorizonForecast {
  voltages: number[];
  angles?: number[];
  line_flows_p: number[];
  line_flows_q: number[];
  cyber_instability_probability: number;
  confidence: number;
  uncertainty_std?: number;
  kcl_error: number;
  kvl_error: number;
  dc_flow_error?: number;
  topology_valid: boolean;
  stability_valid: boolean;
  adversarial_anomaly?: boolean;
  explainability_log?: string;
}

interface PinnForecastData {
  timestamp: number;
  horizons: {
    "10s": HorizonForecast;
    "30s": HorizonForecast;
    "60s": HorizonForecast;
  };
  latency_ms: number;
  concept_drift_score?: number;
  concept_drift_alert?: boolean;
  trusted_grid_state?: number[];
  degraded_observability?: boolean;
  global_physics_confidence?: number;
}

interface PinnForecastPanelProps {
  pinnForecastData: PinnForecastData | null;
}

type TabType = "heatmap" | "threat" | "physics";

export const PinnForecastPanel: React.FC<PinnForecastPanelProps> = ({ pinnForecastData }) => {
  const [selectedHorizon, setSelectedHorizon] = useState<"10s" | "30s" | "60s">("10s");
  const [viewTab, setViewTab] = useState<TabType>("heatmap");

  const hasData = pinnForecastData !== null && pinnForecastData !== undefined && pinnForecastData.horizons !== undefined;
  const currentForecast = hasData ? pinnForecastData.horizons[selectedHorizon] : null;

  const getVoltageColorClass = (v: number) => {
    if (v < 0.90 || v > 1.10) return "text-red-400 font-extrabold scada-text-glow-red bg-red-950/20";
    if (v < 0.95 || v > 1.05) return "text-yellow-400 font-bold bg-yellow-950/10";
    return "text-emerald-400 bg-emerald-950/5";
  };

  const getVoltageBgClass = (v: number) => {
    if (v < 0.90 || v > 1.10) return "bg-red-500/25 border-red-500/50";
    if (v < 0.95 || v > 1.05) return "bg-yellow-500/25 border-yellow-500/50";
    return "bg-emerald-500/15 border-emerald-500/20";
  };

  // Format data for Recharts area plot (cyber probability over horizons)
  const getTimelineData = () => {
    if (!hasData) return [];
    return [
      { name: "Now", prob: 0 },
      { name: "10s", prob: Math.round((pinnForecastData.horizons?.["10s"]?.cyber_instability_probability ?? 0) * 100) },
      { name: "30s", prob: Math.round((pinnForecastData.horizons?.["30s"]?.cyber_instability_probability ?? 0) * 100) },
      { name: "60s", prob: Math.round((pinnForecastData.horizons?.["60s"]?.cyber_instability_probability ?? 0) * 100) },
    ];
  };

  return (
    <div className="bg-scada-panel border border-scada-border rounded-lg p-4 h-[300px] flex flex-col justify-between overflow-hidden relative">
      {/* Header */}
      <div className="flex justify-between items-center mb-1.5 border-b border-scada-border/40 pb-1.5 shrink-0">
        <h2 className="text-sm font-semibold tracking-wider text-scada-dimText uppercase flex items-center gap-1.5">
          <Activity size={16} className="text-cyan-400 animate-pulse" />
          True Physics-Informed Forecasting Engine (PINN)
        </h2>

        {/* View Tabs */}
        <div className="flex gap-1.5 mr-auto ml-4">
          {(["heatmap", "threat", "physics"] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setViewTab(tab)}
              className={`px-2 py-0.5 rounded text-[8px] font-mono font-bold tracking-wider uppercase transition-all ${
                viewTab === tab
                  ? "bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 scada-text-glow"
                  : "text-scada-dimText hover:text-white border border-transparent"
              }`}
            >
              {tab === "heatmap" ? "Forecast Heatmap" : tab === "threat" ? "Threat Timeline" : "Physical Physics"}
            </button>
          ))}
        </div>
        
        {/* Horizon Tabs */}
        <div className="flex gap-1 bg-scada-bg/60 border border-scada-border/40 rounded p-0.5">
          {(["10s", "30s", "60s"] as const).map((h) => (
            <button
              key={h}
              onClick={() => setSelectedHorizon(h)}
              className={`px-2 py-0.5 rounded-[3px] text-[9px] font-mono font-bold transition-all ${
                selectedHorizon === h
                  ? "bg-cyan-500/20 text-cyan-400 border border-cyan-500/30"
                  : "text-scada-dimText hover:text-white border border-transparent"
              }`}
            >
              {h}
            </button>
          ))}
        </div>
      </div>

      {!hasData ? (
        <div className="flex-1 flex flex-col items-center justify-center gap-2 font-mono text-xs text-scada-dimText italic">
          <div className="animate-spin w-4 h-4 border-2 border-cyan-500 border-t-transparent rounded-full"></div>
          <span>PINN forecasting solver warming up...</span>
        </div>
      ) : (
        <div className="flex-1 flex flex-col justify-between overflow-hidden mt-1">
          
          {/* TAB 1: Heatmap View */}
          {viewTab === "heatmap" && (
            <div className="grid grid-cols-12 gap-3 flex-1 overflow-hidden min-h-0 pb-1">
              {/* Heatmap cells: Columns 0 to 6 */}
              <div className="col-span-6 flex flex-col overflow-hidden h-full">
                <div className="flex justify-between items-center mb-1 block">
                  <span className="text-[8px] text-scada-dimText uppercase font-mono font-semibold">
                    {selectedHorizon} Voltage Horizon (V ± σ uncertainty):
                  </span>
                  {pinnForecastData.degraded_observability && (
                    <span className="text-[7px] text-yellow-400 font-mono font-bold animate-pulse">
                      [RECONSTRUCTED STATE ACTIVE]
                    </span>
                  )}
                </div>
                
                {/* Heatmap cells */}
                <div className="grid grid-cols-3 gap-1.5 flex-1 items-center justify-center">
                  {currentForecast?.voltages?.map((v, idx) => {
                    const std = currentForecast?.uncertainty_std ?? 0.025;
                    return (
                      <div
                        key={idx}
                        className={`border rounded p-1 flex flex-col items-center justify-center transition-all ${getVoltageBgClass(v)} h-[42px]`}
                      >
                        <span className="text-[7px] text-scada-dimText font-mono uppercase font-bold leading-none">Bus {idx + 1}</span>
                        <span className={`text-[9px] font-bold font-scada-nums mt-0.5 leading-none ${getVoltageColorClass(v)}`}>
                          {(v ?? 0).toFixed(3)}
                        </span>
                        <span className="text-[6.5px] text-scada-dimText/80 font-mono leading-none mt-0.5">
                          ±{(std ?? 0.025).toFixed(3)}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Metrics & Physics Diagnostics: Columns 7 to 12 */}
              <div className="col-span-6 flex flex-col justify-between h-full border-l border-scada-border/20 pl-3">
                <div className="space-y-2">
                  {/* Confidence Decay */}
                  <div>
                    <div className="flex justify-between text-[8px] font-mono font-semibold text-scada-dimText">
                      <span>LEARNED PINN CONFIDENCE:</span>
                      <span className="text-white font-bold font-mono">{((currentForecast?.confidence ?? 0.90) * 100).toFixed(0)}%</span>
                    </div>
                    <div className="w-full h-1.5 bg-scada-bg rounded overflow-hidden border border-scada-border/40 mt-0.5">
                      <div
                        className="h-full bg-cyan-500 transition-all duration-500"
                        style={{ width: `${(currentForecast?.confidence ?? 0.90) * 100}%` }}
                      ></div>
                    </div>
                  </div>

                  {/* KCL Power Balance */}
                  <div>
                    <div className="flex justify-between text-[8px] font-mono font-semibold text-scada-dimText">
                      <span>KCL CONSERVATION BIAS:</span>
                      <span className={`font-mono ${(currentForecast?.kcl_error ?? 0) > 0.01 ? "text-yellow-400" : "text-emerald-400"}`}>
                        {(currentForecast?.kcl_error ?? 0).toFixed(5)} MW
                      </span>
                    </div>
                    <div className="w-full h-1.5 bg-scada-bg rounded overflow-hidden border border-scada-border/40 mt-0.5">
                      <div
                        className={`h-full transition-all duration-500 ${
                          (currentForecast?.kcl_error ?? 0) > 0.05 ? "bg-red-500" :
                          (currentForecast?.kcl_error ?? 0) > 0.01 ? "bg-yellow-500" : "bg-emerald-500"
                        }`}
                        style={{ width: `${Math.min(100, (currentForecast?.kcl_error ?? 0) * 2000)}%` }}
                      ></div>
                    </div>
                  </div>

                  {/* Concept Drift Score */}
                  <div>
                    <div className="flex justify-between text-[8px] font-mono font-semibold text-scada-dimText">
                      <span>STREAMING CONCEPT DRIFT:</span>
                      <span className={`font-mono ${pinnForecastData.concept_drift_alert ? "text-red-400 animate-pulse font-bold" : "text-cyan-400"}`}>
                        {pinnForecastData.concept_drift_score ? pinnForecastData.concept_drift_score.toFixed(3) : "0.000"} Z
                      </span>
                    </div>
                    <div className="w-full h-1.5 bg-scada-bg rounded overflow-hidden border border-scada-border/40 mt-0.5">
                      <div
                        className={`h-full transition-all duration-500 ${
                          pinnForecastData.concept_drift_alert ? "bg-red-500 animate-pulse" : "bg-cyan-500/80"
                        }`}
                        style={{ width: `${Math.min(100, (pinnForecastData.concept_drift_score || 0) * 25)}%` }}
                      ></div>
                    </div>
                  </div>
                </div>

                {/* Status Badges Row */}
                <div className="flex gap-2 my-1">
                  <div className="flex-1 bg-scada-bg/50 border border-scada-border/40 rounded p-1 flex items-center justify-between">
                    <span className="text-[7px] text-scada-dimText font-mono font-semibold uppercase">Topology</span>
                    <span className={`px-1 rounded-[2px] text-[7px] font-mono font-bold ${
                      currentForecast!.topology_valid 
                        ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                        : "bg-red-500/10 text-red-400 border border-red-500/20 animate-pulse"
                    }`}>
                      {currentForecast!.topology_valid ? "VALID" : "INVALID"}
                    </span>
                  </div>
                  
                  <div className="flex-1 bg-scada-bg/50 border border-scada-border/40 rounded p-1 flex items-center justify-between">
                    <span className="text-[7px] text-scada-dimText font-mono font-semibold uppercase">Drift Status</span>
                    <span className={`px-1 rounded-[2px] text-[7px] font-mono font-bold ${
                      !pinnForecastData.concept_drift_alert 
                        ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                        : "bg-red-500/10 text-red-400 border border-red-500/20 animate-pulse"
                    }`}>
                      {pinnForecastData.concept_drift_alert ? "DRIFT ALERT" : "STABLE"}
                    </span>
                  </div>
                </div>

                {/* Micro-diagnostic */}
                <div className="p-1 bg-scada-bg border border-scada-border/30 rounded flex items-center gap-1.5 text-[7px] font-mono text-scada-dimText">
                  <Cpu size={10} className="text-cyan-400" />
                  <span>State Reconstruction: {pinnForecastData.degraded_observability ? "ACTIVE (Reconstructing Bus telemetry)" : "INACTIVE (All telemetry healthy)"}</span>
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: Threat & Cascading Risk Timeline */}
          {viewTab === "threat" && (
            <div className="grid grid-cols-12 gap-3 flex-1 overflow-hidden min-h-0 pb-1">
              {/* Timeline chart: Columns 0 to 7 */}
              <div className="col-span-8 flex flex-col h-full overflow-hidden">
                <span className="text-[8px] text-scada-dimText uppercase font-mono font-semibold mb-1 block">
                  Cyber Instability Probability Curve:
                </span>
                
                <div className="flex-1 min-h-0">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={getTimelineData()} margin={{ top: 5, right: 10, left: -25, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#22D3EE/10" vertical={false} />
                      <XAxis dataKey="name" stroke="#64748B" style={{ fontSize: "8px", fontFamily: "monospace" }} />
                      <YAxis domain={[0, 100]} stroke="#64748B" style={{ fontSize: "8px", fontFamily: "monospace" }} />
                      <Tooltip 
                        contentStyle={{ backgroundColor: "#0F172A", borderColor: "#22D3EE/30", fontSize: "9px", fontFamily: "monospace" }} 
                        labelStyle={{ color: "#22D3EE", fontWeight: "bold" }}
                      />
                      <Line 
                        type="monotone" 
                        dataKey="prob" 
                        name="Cyber Risk" 
                        stroke="#F59E0B" 
                        strokeWidth={2} 
                        dot={{ r: 3, stroke: "#F59E0B", strokeWidth: 1, fill: "#0F172A" }}
                        activeDot={{ r: 5 }}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Cascade Timeline Log: Columns 8 to 12 */}
              <div className="col-span-4 flex flex-col justify-between h-full border-l border-scada-border/20 pl-3 overflow-hidden">
                <span className="text-[8px] text-scada-dimText uppercase font-mono font-semibold mb-1 block">
                  Cascading Risk Progression:
                </span>

                <div className="flex-1 overflow-y-auto space-y-1.5 pr-1 font-mono text-[7px] scrollbar-thin">
                  <div className="flex items-start gap-1 p-1 bg-scada-bg rounded border border-scada-border/20">
                    <span className="text-cyan-400 font-bold">[10s]</span>
                    <span className="text-white leading-none">
                      Risk: {Math.round((pinnForecastData.horizons?.["10s"]?.cyber_instability_probability ?? 0) * 100)}%
                    </span>
                  </div>
                  <div className="flex items-start gap-1 p-1 bg-scada-bg rounded border border-scada-border/20">
                    <span className="text-yellow-400 font-bold">[30s]</span>
                    <span className="text-white leading-none">
                      Risk: {Math.round((pinnForecastData.horizons?.["30s"]?.cyber_instability_probability ?? 0) * 100)}%
                    </span>
                  </div>
                  <div className="flex items-start gap-1 p-1 bg-scada-bg rounded border border-scada-border/20">
                    <span className="text-red-400 font-bold animate-pulse">[60s]</span>
                    <span className="text-white leading-none">
                      Risk: {Math.round((pinnForecastData.horizons?.["60s"]?.cyber_instability_probability ?? 0) * 100)}%
                    </span>
                  </div>
                </div>

                <div className="mt-2 p-1.5 bg-scada-bg border border-scada-border/40 rounded">
                  <span className="text-[7.5px] font-bold font-mono text-scada-dimText uppercase flex items-center gap-1">
                    <TrendingUp size={10} className="text-yellow-400" />
                    Cascading Severity
                  </span>
                  <p className="text-[7px] font-mono text-scada-dimText mt-0.5 leading-tight">
                    {(pinnForecastData.horizons?.["60s"]?.cyber_instability_probability ?? 0) > 0.5
                      ? "High cascade propagation warning. Cyber attack is spreading across lines, leading to potential islanding."
                      : "Unstable loops suppressed. Cascading risk propagation under nominal safety limits."}
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* TAB 3: Physics & Explainability */}
          {viewTab === "physics" && (
            <div className="grid grid-cols-12 gap-3 flex-1 overflow-hidden min-h-0 pb-1">
              {/* Physics Consistency Details: Columns 0 to 5 */}
              <div className="col-span-5 flex flex-col justify-between h-full overflow-hidden">
                <span className="text-[8px] text-scada-dimText uppercase font-mono font-semibold mb-1 block">
                  Electrical Physics Consistency (t+{selectedHorizon}):
                </span>
                
                <div className="space-y-1.5 flex-1 flex flex-col justify-center">
                  <div className="flex justify-between items-center text-[7.5px] font-mono p-1 bg-scada-bg rounded border border-scada-border/20">
                    <span className="text-scada-dimText">KCL Power mismatch:</span>
                    <span className="text-white font-bold">{(currentForecast?.kcl_error ?? 0).toFixed(6)} p.u.</span>
                  </div>
                  <div className="flex justify-between items-center text-[7.5px] font-mono p-1 bg-scada-bg rounded border border-scada-border/20">
                    <span className="text-scada-dimText">KVL Voltage drop mismatch:</span>
                    <span className="text-white font-bold">{(currentForecast?.kvl_error ?? 0).toFixed(6)} p.u.</span>
                  </div>
                  <div className="flex justify-between items-center text-[7.5px] font-mono p-1 bg-scada-bg rounded border border-scada-border/20">
                    <span className="text-scada-dimText">DC flow angle consistency:</span>
                    <span className="text-white font-bold">
                      {currentForecast?.dc_flow_error ? currentForecast.dc_flow_error.toFixed(6) : "0.000000"} p.u.
                    </span>
                  </div>
                </div>
              </div>

              {/* Explainability Report: Columns 6 to 12 */}
              <div className="col-span-7 flex flex-col justify-between h-full border-l border-scada-border/20 pl-3">
                <div className="flex justify-between items-center mb-1">
                  <span className="text-[8px] text-scada-dimText uppercase font-mono font-semibold">
                    Anomaly Explainability Report:
                  </span>
                  {currentForecast?.adversarial_anomaly && (
                    <div className="flex items-center gap-0.5 text-red-400 font-mono font-bold animate-pulse text-[7px] bg-red-950/20 border border-red-500/30 px-1 rounded">
                      <AlertTriangle size={8} />
                      <span>ADVERSARIAL ATTACK</span>
                    </div>
                  )}
                </div>

                <div className="p-2 bg-scada-bg border border-scada-border/50 rounded flex-1 flex flex-col justify-center min-h-[60px]">
                  <div className="flex items-center gap-1 mb-1">
                    {!currentForecast?.topology_valid || (currentForecast?.kcl_error ?? 0) > 0.03 || currentForecast?.adversarial_anomaly ? (
                      <>
                        <ShieldAlert size={11} className="text-red-400 animate-bounce" />
                        <span className="text-[7.5px] font-bold font-mono text-red-400 uppercase">Tampering Detected</span>
                      </>
                    ) : (
                      <>
                        <ShieldCheck size={11} className="text-emerald-400" />
                        <span className="text-[7.5px] font-bold font-mono text-emerald-400 uppercase">Physics Gradients Valid</span>
                      </>
                    )}
                  </div>
                  <p className="text-[8px] font-mono text-scada-dimText leading-tight">
                    {currentForecast?.explainability_log || 
                      "Forecasted profiles satisfy KCL, KVL, and breaker topology constraints. No active anomalies detected."}
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Footer Info */}
          <div className="flex justify-between items-center border-t border-scada-border/20 pt-1.5 shrink-0 font-mono text-[8px] text-scada-dimText">
            <div className="flex items-center gap-1">
              <span>SOLVER STATUS:</span>
              <span className="text-cyan-400 font-bold">PINN CONVERGED</span>
            </div>
            <div className="flex items-center gap-1">
              <span>LATENCY:</span>
              <span className="text-white font-scada-nums">{(pinnForecastData.latency_ms ?? 0).toFixed(1)}ms</span>
            </div>
            <div className="flex items-center gap-1">
              <span>UPDATED:</span>
              <span className="text-white font-scada-nums">
                {new Date(pinnForecastData.timestamp ?? Date.now()).toLocaleTimeString([], { hour12: false })}
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
