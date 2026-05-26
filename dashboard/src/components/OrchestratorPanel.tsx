import React, { useState, useMemo } from "react";
import { Brain, Zap, FileText, ListChecks, Sparkles, Clock, AlertTriangle, CheckSquare, Square } from "lucide-react";

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
  defense_mode?: "ADVISORY" | "SEMI_AUTONOMOUS" | "EMERGENCY_DEFENSE";
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
  const [activeTab, setActiveTab] = useState<"actions" | "reasoning" | "checklist">("actions");
  
  // Confirmation state
  const [confirmOpen, setConfirmOpen] = useState<boolean>(false);
  const [pendingAction, setPendingAction] = useState<RecommendationAction | null>(null);

  // Operator checklist state (completed step IDs)
  const [completedChecklistSteps, setCompletedChecklistSteps] = useState<Record<string, boolean>>({});

  const hasData = orchestratorData !== null;
  const globalState = orchestratorData?.global_state ?? "NORMAL";
  const riskLevel = orchestratorData?.global_risk_level ?? "LOW";
  const stability = orchestratorData?.stability_score ?? 100.0;
  const confidence = orchestratorData?.restoration_confidence ?? 100.0;
  const defenseMode = orchestratorData?.defense_mode ?? "ADVISORY";
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

  const handleExecuteClick = (rec: RecommendationAction) => {
    setPendingAction(rec);
    setConfirmOpen(true);
  };

  const confirmAction = () => {
    if (pendingAction) {
      onExecuteAction(pendingAction.action, pendingAction.target);
      setConfirmOpen(false);
      setPendingAction(null);
    }
  };

  // Build dynamic step-by-step interactive workflow checklist for critical states
  const checklistSteps = useMemo(() => {
    const steps: Array<{ id: string; text: string; actionRec?: RecommendationAction }> = [];
    
    if (globalState === "NORMAL") {
      steps.push({ id: "check_voltage", text: "Monitor voltage levels on critical Bus 5" });
      steps.push({ id: "check_line_loading", text: "Ensure line thermal capacity stays below 80%" });
    } else if (globalState === "DEGRADED" || globalState === "AUTONOMOUS_RECOVERY") {
      steps.push({ id: "check_isolation", text: "Verify faulty grid segments are fully isolated" });
      steps.push({ id: "check_restoration", text: "Review FLISR automated re-configuration logs" });
      recommendations.forEach((rec, idx) => {
        if (rec.action === "REROUTE_LOAD") {
          steps.push({ id: `rec_${idx}`, text: `Execute advisory: Close tie-breaker ${rec.target}`, actionRec: rec });
        }
      });
    } else if (globalState === "CYBER_ATTACK" || globalState === "EMERGENCY_MODE" || globalState === "CASCADE_RISK") {
      steps.push({ id: "raise_alert", text: "Establish emergency communications loop with control room" });
      
      // Auto-populate checklist with recommendations
      recommendations.forEach((rec, idx) => {
        if (rec.action === "TELEMETRY_DISTRUST") {
          steps.push({ id: `rec_${idx}`, text: `Advisory Checklist: Reject measurements from ${rec.target}`, actionRec: rec });
        } else if (rec.action === "BREAKER_LOCKOUT") {
          steps.push({ id: `rec_${idx}`, text: `Advisory Checklist: Lockout breaker ${rec.target} (intrusion)`, actionRec: rec });
        } else if (rec.action === "ISOLATE_LINE") {
          steps.push({ id: `rec_${idx}`, text: `Advisory Checklist: Open line ${rec.target} (overload)`, actionRec: rec });
        } else if (rec.action === "FLISR_SUPPRESSION") {
          steps.push({ id: `rec_${idx}`, text: "Advisory Checklist: Suppress FLISR self-healing FSM", actionRec: rec });
        }
      });

      steps.push({ id: "reset_alarms", text: "Once fault is cleared, perform standard SYSTEM RESET" });
    }
    return steps;
  }, [globalState, recommendations]);

  const toggleChecklistStep = (stepId: string) => {
    setCompletedChecklistSteps(prev => ({
      ...prev,
      [stepId]: !prev[stepId]
    }));
  };

  return (
    <div className="bg-scada-panel border border-scada-border rounded-lg p-3 h-[300px] flex flex-col justify-between overflow-hidden relative">
      
      {/* 4.6. Operator Confirmation Modal Overlay */}
      {confirmOpen && pendingAction && (
        <div className="absolute inset-0 bg-black/85 flex flex-col justify-center items-center p-4 z-50 font-mono text-[10px]">
          <div className="border border-red-500/50 bg-scada-bg p-3 rounded max-w-[200px] flex flex-col gap-2.5 scada-glow-red">
            <h3 className="text-red-400 font-bold flex items-center gap-1">
              <AlertTriangle size={12} />
              Confirm Grid Execution
            </h3>
            <p className="text-white leading-relaxed text-[8.5px]">
              Confirm execution of action: <strong>{pendingAction.action}</strong> on target <strong>{pendingAction.target}</strong>?
            </p>
            <p className="text-scada-dimText italic text-[7.5px] leading-snug">
              {pendingAction.description}
            </p>
            <div className="flex gap-2.5 mt-1 border-t border-scada-border/30 pt-2 shrink-0">
              <button
                onClick={() => setConfirmOpen(false)}
                className="flex-1 bg-scada-border hover:bg-scada-border/70 border border-scada-border text-white p-1 rounded font-bold"
              >
                CANCEL
              </button>
              <button
                onClick={confirmAction}
                className="flex-1 bg-red-900/40 hover:bg-red-950/40 border border-red-500 text-red-300 p-1 rounded font-bold flex items-center justify-center gap-0.5"
              >
                <Zap size={8} /> CONFIRM
              </button>
            </div>
          </div>
        </div>
      )}

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
              <div className="flex justify-between items-center">
                <span className="text-[7px] text-white/50 uppercase font-semibold">GRID STATE</span>
                <span className="text-[6.5px] font-bold bg-white/10 px-1 rounded truncate tracking-tight">{defenseMode}</span>
              </div>
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
            <button
              onClick={() => setActiveTab("checklist")}
              className={`flex-1 pb-1 text-[8px] font-mono uppercase font-bold tracking-wider flex items-center justify-center gap-1 border-b-2 transition-all ${
                activeTab === "checklist"
                  ? "border-emerald-500 text-white"
                  : "border-transparent text-scada-dimText hover:text-white"
              }`}
            >
              <CheckSquare size={10} />
              Checklist
            </button>
          </div>

          {/* Dynamic Tab Body */}
          <div className="flex-1 overflow-y-auto bg-black/15 border border-scada-border/30 rounded p-1 max-h-[100px] scrollbar-thin">
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
                        onClick={() => handleExecuteClick(rec)}
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
            ) : activeTab === "reasoning" ? (
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
            ) : (
              // 4.6. Dynamic Workflow Checklist view
              <div className="space-y-1.5 font-mono text-[8px] leading-tight">
                {globalState !== "NORMAL" && (
                  <div className="bg-red-500/10 border border-red-500/25 text-red-300 rounded p-1 mb-1.5 flex items-center gap-1.5 text-[7.5px]">
                    <AlertTriangle size={10} className="shrink-0 animate-pulse text-red-400" />
                    <span>EMERGENCY WORKFLOW ACTIVE: Complete steps below</span>
                  </div>
                )}
                {checklistSteps.map((step: any) => {
                  const isCompleted = !!completedChecklistSteps[step.id];
                  return (
                    <div
                      key={step.id}
                      className={`flex items-start gap-2 p-1 border rounded transition-colors ${
                        isCompleted
                          ? "bg-emerald-950/10 border-emerald-900/30 text-gray-500"
                          : "bg-scada-bg/40 border-scada-border/30 text-white"
                      }`}
                    >
                      <button
                        onClick={() => toggleChecklistStep(step.id)}
                        className={`mt-0.5 p-0.2 rounded border ${
                          isCompleted ? "border-emerald-500 text-emerald-400 bg-emerald-500/10" : "border-gray-500 text-gray-500"
                        } shrink-0`}
                      >
                        {isCompleted ? <CheckSquare size={9} /> : <Square size={9} />}
                      </button>
                      <div className="flex-1 flex flex-col justify-between">
                        <span className={isCompleted ? "line-through" : ""}>{step.text}</span>
                        {step.actionRec && !isCompleted && (
                          <button
                            onClick={() => handleExecuteClick(step.actionRec!)}
                            className="bg-emerald-500/15 hover:bg-emerald-500/25 border border-emerald-500/35 text-emerald-400 font-bold px-1 py-0.2 rounded mt-1 text-[7px] w-max"
                          >
                            Execute Now
                          </button>
                        )}
                      </div>
                    </div>
                  );
                })}
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
