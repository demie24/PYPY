import React from "react";
import { ShieldCheck, Zap, Shield, Cpu, Activity } from "lucide-react";

interface Recommendation {
  action: string;
  target: string;
  priority: string;
  msg: string;
}

interface ThreatData {
  timestamp: number;
  threat_score: number;
  severity: string;
  confidence: number;
  cascade_probability: number;
  affected_node_count: number;
  affected_nodes: string[];
  propagation_risk: string;
  recommendations: Recommendation[];
  auto_defense_active: boolean;
}

interface ThreatScorePanelProps {
  threatData: ThreatData | null;
  onExecuteAction: (action: string, target: string) => void;
  onToggleAutoDefense: (enabled: boolean) => void;
}

export const ThreatScorePanel: React.FC<ThreatScorePanelProps> = ({
  threatData,
  onExecuteAction,
  onToggleAutoDefense,
}) => {
  // Safe fallback states if threatData is not initialized yet
  const score = threatData?.threat_score ?? 0;
  const severity = threatData?.severity ?? "LOW";
  const confidence = threatData?.confidence ?? 1.0;
  const cascadeProb = threatData?.cascade_probability ?? 0.0;
  const propagationRisk = threatData?.propagation_risk ?? "LOW";
  const affectedNodes = threatData?.affected_nodes ?? [];
  const recommendations = threatData?.recommendations ?? [];
  const autoDefenseActive = threatData?.auto_defense_active ?? false;

  // Custom styling depending on severity level
  const getSeverityStyle = (sev: string) => {
    switch (sev) {
      case "CRITICAL":
        return "bg-red-500/15 border-red-500 text-red-400 animate-pulse font-extrabold";
      case "HIGH":
        return "bg-orange-500/15 border-orange-500 text-orange-400 font-bold";
      case "MODERATE":
        return "bg-yellow-500/15 border-yellow-500 text-yellow-400 font-semibold";
      default:
        return "bg-emerald-500/10 border-emerald-500/35 text-scada-nominal font-medium";
    }
  };

  const getScoreColorClass = (val: number) => {
    if (val >= 76) return "text-red-500 scada-text-glow-red";
    if (val >= 51) return "text-orange-500";
    if (val >= 26) return "text-yellow-500 scada-text-glow-warning";
    return "text-scada-nominal scada-text-glow-green";
  };

  const getBarColorClass = (val: number) => {
    if (val >= 0.75) return "bg-red-500";
    if (val >= 0.50) return "bg-orange-500";
    if (val >= 0.25) return "bg-yellow-500";
    return "bg-emerald-500";
  };

  const getPriorityStyle = (priority: string) => {
    switch (priority) {
      case "CRITICAL":
        return "bg-red-500/25 text-red-300";
      case "HIGH":
        return "bg-orange-500/25 text-orange-300";
      default:
        return "bg-yellow-500/20 text-yellow-400";
    }
  };

  return (
    <div className="bg-scada-panel border border-scada-border rounded-lg p-4 flex flex-col justify-between overflow-hidden h-[300px]">
      {/* Header with Title and Auto-Defense toggle */}
      <div className="flex justify-between items-center mb-2 shrink-0 border-b border-scada-border pb-1.5">
        <h2 className="text-sm font-semibold tracking-wider text-scada-dimText uppercase flex items-center gap-1.5">
          <Shield size={16} className={score > 50 ? "text-red-500 animate-pulse" : "text-scada-nominal"} />
          Threat Scoring Engine
        </h2>
        
        <button
          onClick={() => onToggleAutoDefense(!autoDefenseActive)}
          className={`px-2 py-0.5 rounded text-[9px] font-mono tracking-widest border transition-all duration-300 flex items-center gap-1 ${
            autoDefenseActive
              ? "bg-red-500/15 border-red-500/50 text-red-400 animate-pulse"
              : "bg-scada-bg border-scada-border text-scada-dimText hover:text-white"
          }`}
          title="Toggle autonomous mitigation trigger on threat engine recommendations"
        >
          <Cpu size={10} />
          {autoDefenseActive ? "AUTO-DEFENSE ACTIVE" : "DEFENSE MANUAL"}
        </button>
      </div>

      <div className="flex-1 grid grid-cols-1 lg:grid-cols-3 gap-3 overflow-hidden">
        {/* Metric gauge & Severity Column */}
        <div className="flex flex-col justify-center items-center bg-black/20 border border-scada-border/30 rounded p-2.5">
          <div className="text-[10px] text-scada-dimText uppercase tracking-widest font-mono mb-1">Threat Index</div>
          <div className={`text-4xl font-scada-nums tracking-tighter ${getScoreColorClass(score)}`}>
            {score}
          </div>
          <div className={`mt-2 px-2.5 py-0.5 border rounded text-[9px] uppercase tracking-wider text-center ${getSeverityStyle(severity)}`}>
            {severity}
          </div>
        </div>

        {/* Confidence & Cascade Risk Bar Graph Column */}
        <div className="flex flex-col justify-between bg-black/20 border border-scada-border/30 rounded p-3 font-mono text-[9px] space-y-2">
          {/* Confidence Indicator */}
          <div>
            <div className="flex justify-between text-scada-dimText uppercase mb-1">
              <span>Confidence</span>
              <span className="text-white font-bold">{Math.round(confidence * 100)}%</span>
            </div>
            <div className="w-full bg-scada-bg h-1.5 rounded-full overflow-hidden border border-scada-border/40">
              <div 
                className="h-full bg-scada-nominal transition-all duration-500" 
                style={{ width: `${confidence * 100}%` }}
              ></div>
            </div>
          </div>

          {/* Cascade Probability */}
          <div>
            <div className="flex justify-between text-scada-dimText uppercase mb-1">
              <span>Cascade Probability</span>
              <span className="text-white font-bold">{Math.round(cascadeProb * 100)}%</span>
            </div>
            <div className="w-full bg-scada-bg h-1.5 rounded-full overflow-hidden border border-scada-border/40">
              <div 
                className={`h-full transition-all duration-500 ${getBarColorClass(cascadeProb)}`}
                style={{ width: `${cascadeProb * 100}%` }}
              ></div>
            </div>
          </div>

          {/* Propagation Risk */}
          <div className="flex justify-between items-center text-[10px] border-t border-scada-border/20 pt-1.5">
            <span className="text-scada-dimText uppercase">Propagation Risk:</span>
            <span className={`px-1.5 py-0.5 rounded text-[8px] font-extrabold border ${
              propagationRisk === "HIGH" ? "bg-red-500/10 border-red-500/35 text-red-400 animate-pulse" :
              propagationRisk === "MEDIUM" ? "bg-orange-500/10 border-orange-500/35 text-orange-400" :
              "bg-emerald-500/10 border-emerald-500/35 text-scada-nominal"
            }`}>
              {propagationRisk}
            </span>
          </div>
        </div>

        {/* Recommendations / Affected Nodes column */}
        <div className="flex flex-col justify-between overflow-hidden">
          {/* Affected Nodes strip */}
          <div className="mb-2 shrink-0">
            <div className="text-[8px] text-scada-dimText uppercase font-mono tracking-wider mb-1 flex items-center gap-1">
              <Activity size={10} /> Affected Nodes ({affectedNodes.length})
            </div>
            <div className="flex flex-wrap gap-1 max-h-[36px] overflow-y-auto pr-1">
              {affectedNodes.map((node, i) => (
                <span 
                  key={i} 
                  className={`px-1.5 py-0.5 rounded text-[8px] font-mono uppercase font-bold border ${
                    node.startsWith("Bus") ? "bg-blue-500/10 border-blue-500/30 text-blue-300" : "bg-orange-500/10 border-orange-500/30 text-orange-300"
                  }`}
                >
                  {node}
                </span>
              ))}
              {affectedNodes.length === 0 && (
                <span className="text-[8px] text-scada-dimText italic">None</span>
              )}
            </div>
          </div>

          {/* Active Mitigation Recommendations */}
          <div className="flex-1 overflow-y-auto border border-scada-border/50 bg-black/20 rounded p-1.5 max-h-[140px] space-y-1.5">
            <div className="text-[8px] text-scada-dimText uppercase font-mono tracking-wider mb-1">Defense Recommendations</div>
            {recommendations.map((rec, i) => (
              <div 
                key={i} 
                className="bg-scada-bg border border-scada-border/60 rounded p-1.5 flex flex-col justify-between gap-1 text-[9px] font-mono leading-tight"
              >
                <div className="flex justify-between items-center font-bold text-[8px]">
                  <span className={`px-1 py-0.2 rounded ${getPriorityStyle(rec.priority)}`}>
                    {rec.priority}
                  </span>
                  <span className="text-white/60 uppercase">{rec.action.replace("_", " ")}</span>
                </div>
                <p className="text-scada-text leading-tight">{rec.msg}</p>
                <div className="flex justify-between items-center mt-1 border-t border-scada-border/20 pt-1 shrink-0">
                  <span className="text-[8px] text-gray-500 uppercase">Target: {rec.target}</span>
                  <button
                    onClick={() => onExecuteAction(rec.action, rec.target)}
                    className="bg-scada-nominal/15 border border-scada-nominal/40 hover:bg-scada-nominal/30 text-scada-nominal px-1.5 py-0.5 rounded text-[8px] font-semibold flex items-center gap-0.5 transition-all"
                  >
                    <Zap size={8} /> Execute Action
                  </button>
                </div>
              </div>
            ))}
            {recommendations.length === 0 && (
              <div className="text-[10px] text-scada-dimText font-mono italic text-center py-6 flex flex-col items-center justify-center gap-1.5">
                <ShieldCheck size={16} className="text-scada-nominal" />
                No recommendation (Grid secure)
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
