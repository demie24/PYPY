import React, { useState } from "react";
import { Brain, Zap, FileText, ListChecks, Sparkles, Clock } from "lucide-react";

interface SubsystemsReasoning {
  forecast: string;
  physics: string;
  trust: string;
  flisr: string;
}

interface AIOrchestratorData {
  timestamp: number;
  global_state: "NORMAL" | "DEGRADED" | "CYBER_ATTACK" | "CASCADE_RISK" | "AUTONOMOUS_RECOVERY" | "EMERGENCY_MODE";
  global_risk_level: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  stability_score: number;
  restoration_confidence: number;
  active_subsystems_reasoning: SubsystemsReasoning;
}

interface RecommendationAction {
  action: "ISOLATE_LINE" | "REROUTE_LOAD" | "BREAKER_LOCKOUT" | "TELEMETRY_DISTRUST" | "FLISR_SUPPRESSION" | "OPERATOR_ESCALATION" | string;
  target: string;
  priority: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL" | string;
  description: string;
  reasoning: string;
}

interface RecommendedActionsData {
  timestamp: number;
  recommendations: RecommendationAction[];
}

interface OrchestratorPanelProps {
  orchestratorData: AIOrchestratorData | null;
  actionsData: RecommendedActionsData | null;
  onExecuteAction: (action: string, target: string) => void;
}

export const OrchestratorPanel: React.FC<OrchestratorPanelProps> = ({
  orchestratorData,
  actionsData,
  onExecuteAction
}) => {
  const [activeTab, setActiveTab] = useState<"actions" | "reasoning">("actions");

  const hasData = orchestratorData !== null;
  const globalState = orchestratorData?.global_state ?? "NORMAL";
  const riskLevel = orchestratorData?.global_risk_level ?? "LOW";
  const stability = orchestratorData?.stability_score ?? 100.0;
  const confidence = orchestratorData?.restoration_confidence ?? 100.0;
  const reasoning = orchestratorData?.active_subsystems_reasoning ?? {
    forecast: "Awaiting telemetry data...",
    physics: "Awaiting physical law validation...",
    trust: "Awaiting sensor trust evaluations...",
    flisr: "Awaiting recovery grid mapping..."
  };
  const recommendations = actionsData?.recommendations ?? [];

  const getGlobalStateStyle = (state: string) => {
    switch (state) {
      case "EMERGENCY_MODE":
        return "bg-red-950/20 border-red-500 text-red-500 font-extrabold animate-pulse scada-glow-red";
      case "CYBER_ATTACK":
        return "bg-red-500/15 border-red-500 text-red-400 font-extrabold animate-pulse scada-glow-red";
      case "CASCADE_RISK":
        return "bg-orange-500/15 border-orange-500 text-orange-400 font-bold";
      case "DEGRADED":
        return "bg-yellow-500/15 border-yellow-500 text-yellow-400 font-semibold";
      case "AUTONOMOUS_RECOVERY":
        return "bg-blue-500/15 border-blue-500 text-blue-400 font-bold";
      default:
        return "bg-emerald-500/10 border-emerald-500/30 text-scada-nominal font-medium";
    }
  };

  const getRiskStyle = (risk: string) => {
    switch (risk) {
      case "CRITICAL":
        return "text-red-500 font-extrabold animate-pulse scada-text-glow-red";
      case "HIGH":
        return "text-orange-500 font-bold";
      case "MEDIUM":
        return "text-yellow-500";
      default:
        return "text-scada-nominal";
    }
  };

  const getPriorityStyle = (priority: string) => {
    switch (priority) {
      case "CRITICAL":
        return "bg-red-500/25 border-red-500/50 text-red-300";
      case "HIGH":
        return "bg-orange-500/25 border-orange-500/50 text-orange-300";
      case "MEDIUM":
        return "bg-yellow-500/20 border-yellow-500/40 text-yellow-400";
      default:
        return "bg-emerald-500/10 border-emerald-500/30 text-scada-nominal";
    }
  };

  return (
    <div className="bg-scada-panel border border-scada-border rounded-lg p-3 h-[300px] flex flex-col justify-between overflow-hidden">
      {/* Header */}
      <div className="flex justify-between items-center mb-1.5 border-b border-scada-border/40 pb-1 shrink-0">
        <h2 className="text-xs font-bold tracking-wider text-scada-dimText uppercase flex items-center gap-1">
          <Brain size={14} className={globalState !== "NORMAL" ? "text-red-500 animate-pulse" : "text-emerald-400"} />
          AI Orchestration
        </h2>
        <div className="flex items-center gap-1 font-mono text-[8px] text-scada-dimText">
          <Clock size={8} />
          <span>Decision Hub</span>
        </div>
      </div>

      {!hasData ? (
        <div className="flex-1 flex flex-col items-center justify-center gap-1.5 font-mono text-[10px] text-scada-dimText italic">
          <div className="animate-spin w-3.5 h-3.5 border-2 border-emerald-500 border-t-transparent rounded-full"></div>
          <span>Orchestrator sync...</span>
        </div>
      ) : (
        <div className="flex-1 flex flex-col justify-between overflow-hidden">
          {/* Top Panel: Global State & Risk */}
          <div className="grid grid-cols-2 gap-2 mb-1.5 shrink-0 font-mono text-[9px]">
            <div className={`border rounded p-1 flex flex-col justify-between h-[48px] ${getGlobalStateStyle(globalState)}`}>
              <span className="text-[7px] text-white/50 uppercase font-semibold">GRID STATE</span>
              <span className="font-bold text-[9px] uppercase tracking-tight truncate leading-none mb-0.5">
                {globalState.replace("_", " ")}
              </span>
            </div>
            <div className="bg-scada-bg/60 border border-scada-border/40 rounded p-1 flex flex-col justify-between h-[48px]">
              <span className="text-[7px] text-scada-dimText uppercase font-semibold">Risk & stability</span>
              <div className="flex justify-between items-center leading-none mb-0.5">
                <span className={`font-extrabold ${getRiskStyle(riskLevel)}`}>{riskLevel} RISK</span>
                <span className="text-[9px] font-bold text-white font-scada-nums">{stability.toFixed(0)}% STB</span>
              </div>
            </div>
          </div>

          {/* Core Metrics: Confidence bar */}
          <div className="mb-2 shrink-0 font-mono text-[8.5px] bg-scada-bg/40 border border-scada-border/20 rounded p-1">
            <div className="flex justify-between text-scada-dimText mb-0.5">
              <span>RESTORATION CONFIDENCE</span>
              <span className="text-white font-bold font-scada-nums">{confidence.toFixed(1)}%</span>
            </div>
            <div className="w-full bg-scada-bg h-1 rounded-full overflow-hidden border border-scada-border/40">
              <div
                className={`h-full transition-all duration-500 ${
                  confidence >= 80 ? "bg-emerald-500" : confidence >= 50 ? "bg-yellow-500" : "bg-red-500"
                }`}
                style={{ width: `${confidence}%` }}
              ></div>
            </div>
          </div>

          {/* Tab Navigation */}
          <div className="flex border-b border-scada-border/30 mb-1.5 shrink-0">
            <button
              onClick={() => setActiveTab("actions")}
              className={`flex-1 pb-1 text-[8px] font-mono uppercase font-bold tracking-wider flex items-center justify-center gap-1 border-b-2 transition-all ${
                activeTab === "actions"
                  ? "border-emerald-500 text-white"
                  : "border-transparent text-scada-dimText hover:text-white"
              }`}
            >
              <ListChecks size={10} />
              Actions ({recommendations.length})
            </button>
            <button
              onClick={() => setActiveTab("reasoning")}
              className={`flex-1 pb-1 text-[8px] font-mono uppercase font-bold tracking-wider flex items-center justify-center gap-1 border-b-2 transition-all ${
                activeTab === "reasoning"
                  ? "border-emerald-500 text-white"
                  : "border-transparent text-scada-dimText hover:text-white"
              }`}
            >
              <FileText size={10} />
              Reasoning
            </button>
          </div>

          {/* Dynamic Tab Body */}
          <div className="flex-1 overflow-y-auto bg-black/15 border border-scada-border/30 rounded p-1 max-h-[110px]">
            {activeTab === "actions" ? (
              <div className="space-y-1">
                {recommendations.map((rec, idx) => (
                  <div
                    key={idx}
                    className="bg-scada-bg/60 border border-scada-border/40 rounded p-1 flex flex-col justify-between gap-0.5 text-[8px] font-mono leading-tight"
                  >
                    <div className="flex justify-between items-center font-bold">
                      <span className={`px-1 py-0.2 rounded border scale-90 ${getPriorityStyle(rec.priority)}`}>
                        {rec.priority}
                      </span>
                      <span className="text-white/70 uppercase text-[7px] truncate max-w-[80px]">
                        {rec.action.replace("_", " ")}
                      </span>
                    </div>
                    <p className="text-white/90 font-medium text-[7.5px] leading-snug">{rec.description}</p>
                    <p className="text-scada-dimText text-[7px] italic border-t border-scada-border/10 pt-0.5 mt-0.5 leading-snug">
                      {rec.reasoning}
                    </p>
                    <div className="flex justify-between items-center mt-1 border-t border-scada-border/20 pt-1 shrink-0">
                      <span className="text-[6.5px] text-gray-500 uppercase truncate max-w-[90px]">Target: {rec.target}</span>
                      <button
                        onClick={() => onExecuteAction(rec.action, rec.target)}
                        className="bg-scada-nominal/10 border border-scada-nominal/30 hover:bg-scada-nominal/20 text-scada-nominal px-1 py-0.2 rounded text-[7px] font-bold flex items-center gap-0.5 transition-all scale-95"
                      >
                        <Zap size={6} /> Execute
                      </button>
                    </div>
                  </div>
                ))}
                {recommendations.length === 0 && (
                  <div className="text-[8.5px] text-scada-dimText font-mono italic text-center py-6 flex flex-col items-center justify-center gap-1">
                    <Sparkles size={12} className="text-scada-nominal" />
                    <span>No recommendations (Nominal Grid)</span>
                  </div>
                )}
              </div>
            ) : (
              <div className="font-mono text-[7px] space-y-1 pr-0.5">
                <div>
                  <span className="text-emerald-400 font-bold uppercase block border-b border-scada-border/10 pb-0.2 mb-0.5">
                    [ML Forecast]
                  </span>
                  <span className="text-scada-text leading-tight">{reasoning.forecast}</span>
                </div>
                <div className="mt-1">
                  <span className="text-emerald-400 font-bold uppercase block border-b border-scada-border/10 pb-0.2 mb-0.5">
                    [Physics Check]
                  </span>
                  <span className="text-scada-text leading-tight">{reasoning.physics}</span>
                </div>
                <div className="mt-1">
                  <span className="text-emerald-400 font-bold uppercase block border-b border-scada-border/10 pb-0.2 mb-0.5">
                    [Sensor Trust]
                  </span>
                  <span className="text-scada-text leading-tight">{reasoning.trust}</span>
                </div>
                <div className="mt-1">
                  <span className="text-emerald-400 font-bold uppercase block border-b border-scada-border/10 pb-0.2 mb-0.5">
                    [FLISR Status]
                  </span>
                  <span className="text-scada-text leading-tight">{reasoning.flisr}</span>
                </div>
              </div>
            )}
          </div>

          {/* Footer Info */}
          <div className="flex justify-between items-center border-t border-scada-border/20 pt-1 shrink-0 font-mono text-[7.5px] text-scada-dimText mt-1">
            <span className="uppercase text-[6px]">AI Orchestration Engine</span>
            <span>
              {new Date(orchestratorData.timestamp).toLocaleTimeString([], { hour12: false })}
            </span>
          </div>
        </div>
      )}
    </div>
  );
};
