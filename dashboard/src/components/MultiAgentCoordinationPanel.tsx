import React, { useState } from "react";
import { 
  Users, ShieldAlert, CheckCircle2, Clock, Zap, GitPullRequest, Sliders, ShieldCheck, HeartPulse, Sparkles
} from "lucide-react";

interface AgentInfo {
  agent_name: string;
  confidence: number;
  trust: number;
  weight: number;
}

interface Proposal {
  command: string;
  target: string;
  source: string;
  source_agent?: string;
}

interface VoteInfo {
  vote: number;
  weight: number;
  trust: number;
}

interface ConsensusResult {
  proposal: Proposal;
  votes: Record<string, VoteInfo>;
  consensus_score: number;
  has_veto: boolean;
  vetoed_by: string[];
  approved: boolean;
}

interface ConflictInfo {
  proposal: Proposal;
  type: string;
  arbitration: string;
}

interface L6AgentsData {
  timestamp: number;
  agents: AgentInfo[];
  proposals: Proposal[];
}

interface L6AgentConsensusData {
  timestamp: number;
  consensus_results: ConsensusResult[];
}

interface L6AgentConflictsData {
  timestamp: number;
  conflicts: ConflictInfo[];
}

interface L6DistributedStateData {
  timestamp: number;
  distributed_state: string;
  active_coordination_mode: string;
}

interface L6AgentConfidenceData {
  timestamp: number;
  confidences: Record<string, number>;
}

interface MultiAgentCoordinationPanelProps {
  agentsData: L6AgentsData | null;
  consensusData: L6AgentConsensusData | null;
  conflictsData: L6AgentConflictsData | null;
  distributedStateData: L6DistributedStateData | null;
  confidenceData: L6AgentConfidenceData | null;
}

type TabType = "agents" | "consensus" | "graph" | "conflicts";

const AGENT_DESCRIPTIONS: Record<string, { role: string; desc: string }> = {
  CyberDefenseAgent: {
    role: "Attack Containment",
    desc: "Contains cyber attacks, filters telemetry, and locks down compromised breakers."
  },
  RestorationAgent: {
    role: "Recovery & Blackstart",
    desc: "Sequences line restorations, tie-switch operations, and blackstart routines."
  },
  StabilizationAgent: {
    role: "Frequency & Voltage Balance",
    desc: "Maintains load-gen balancing, adjusts generators, and avoids thermal overloads."
  },
  SurvivalAgent: {
    role: "Degraded Survival & Hospital",
    desc: "Splits unstable zones into islands and protects critical hospital Bus 5 from shed commands."
  },
  PredictionAgent: {
    role: "Stability Forecasting",
    desc: "Forecasts instability propagation, line overload trajectories, and recovery success."
  }
};

export const MultiAgentCoordinationPanel: React.FC<MultiAgentCoordinationPanelProps> = ({
  agentsData,
  consensusData,
  conflictsData,
  distributedStateData,
  confidenceData
}) => {
  const [activeTab, setActiveTab] = useState<TabType>("agents");

  const hasData = agentsData !== null && agentsData !== undefined;
  const agents = hasData ? agentsData.agents : [];
  const consensusResults = consensusData?.consensus_results ?? [];
  const conflicts = conflictsData?.conflicts ?? [];
  const distributedState = distributedStateData?.distributed_state ?? "STANDBY";
  const coordinationMode = distributedStateData?.active_coordination_mode ?? "NOMINAL";
  const confidences = confidenceData?.confidences ?? {};

  const getDistributedStateStyle = (state: string) => {
    switch (state) {
      case "LOCKDOWN":
        return "bg-red-950/20 border-red-500 text-red-400 font-extrabold animate-pulse scada-glow-red";
      case "CONSENSUS_STABILIZING":
        return "bg-yellow-500/15 border-yellow-500 text-yellow-400 font-bold";
      case "COOPERATIVE_RECOVERY":
        return "bg-cyan-500/15 border-cyan-500 text-cyan-400 font-bold";
      default:
        return "bg-emerald-500/10 border-emerald-500/30 text-scada-nominal font-medium";
    }
  };

  const getVoteBadgeStyle = (vote: number) => {
    if (vote === -1.0) return "bg-red-500/20 text-red-400 border-red-500/35";
    if (vote === 0.0) return "bg-gray-500/10 text-gray-400 border-gray-500/20";
    if (vote > 0.0) return "bg-emerald-500/20 text-emerald-400 border-emerald-500/35";
    return "bg-yellow-500/10 text-yellow-400 border-yellow-500/20";
  };

  const getVoteText = (vote: number) => {
    if (vote === -1.0) return "VETO (-1.0)";
    if (vote === 0.0) return "ABSTAIN (0.0)";
    if (vote > 0.0) return `APPROVE (+${vote.toFixed(1)})`;
    return `DISAGREE (${vote.toFixed(1)})`;
  };

  return (
    <div className="bg-scada-panel border border-scada-border rounded-lg p-3 h-[300px] flex flex-col justify-between overflow-hidden relative">
      
      {/* Header */}
      <div className="flex justify-between items-center mb-1.5 border-b border-scada-border/40 pb-1 shrink-0">
        <h2 className="text-xs font-bold tracking-wider text-scada-dimText uppercase flex items-center gap-1">
          <Users size={14} className={distributedState !== "STANDBY" ? "text-cyan-400 animate-pulse" : "text-emerald-400"} />
          L6 Multi-Agent Grid Intelligence
        </h2>
        <div className="flex items-center gap-1 font-mono text-[8px] text-scada-dimText">
          <Clock size={8} />
          <span>Consensus Bus</span>
        </div>
      </div>

      {!hasData ? (
        <div className="flex-1 flex flex-col items-center justify-center gap-1.5 font-mono text-[10px] text-scada-dimText italic">
          <div className="animate-spin w-3.5 h-3.5 border-2 border-cyan-500 border-t-transparent rounded-full"></div>
          <span>Distributed Agent Bus syncing...</span>
        </div>
      ) : (
        <div className="flex-1 flex flex-col justify-between overflow-hidden">
          
          {/* Top Panel: Distributed State & Coordination Mode */}
          <div className="grid grid-cols-2 gap-2 mb-1.5 shrink-0 font-mono text-[9px]">
            <div className={`border rounded p-1 flex flex-col justify-between h-[48px] ${getDistributedStateStyle(distributedState)}`}>
              <div className="flex justify-between items-center">
                <span className="text-[7px] text-white/50 uppercase font-semibold">DISTRIBUTED STATE</span>
                <span className="text-[6.5px] font-bold bg-white/10 px-1 rounded truncate tracking-tight">{coordinationMode}</span>
              </div>
              <span className="font-bold text-[9px] uppercase tracking-tight truncate leading-none mb-0.5">
                {distributedState.replace("_", " ")}
              </span>
            </div>
            <div className="bg-scada-bg/60 border border-scada-border/40 rounded p-1 flex flex-col justify-between h-[48px]">
              <span className="text-[7px] text-scada-dimText uppercase font-semibold">Consensus Summary</span>
              <div className="flex justify-between items-center leading-none mb-0.5">
                <span className="font-bold text-white text-[8.5px]">ACTIVE PROPOSALS</span>
                <span className="text-[9px] font-bold text-cyan-400 font-scada-nums">{consensusResults.length} GATED</span>
              </div>
            </div>
          </div>

          {/* Tabs */}
          <div className="flex border-b border-scada-border/30 mb-1.5 shrink-0">
            <button
              onClick={() => setActiveTab("agents")}
              className={`flex-1 pb-1 text-[8px] font-mono uppercase font-bold tracking-wider flex items-center justify-center gap-1 border-b-2 transition-all ${
                activeTab === "agents"
                  ? "border-cyan-500 text-white"
                  : "border-transparent text-scada-dimText hover:text-white"
              }`}
            >
              <Sliders size={10} />
              Agents
            </button>
            <button
              onClick={() => setActiveTab("consensus")}
              className={`flex-1 pb-1 text-[8px] font-mono uppercase font-bold tracking-wider flex items-center justify-center gap-1 border-b-2 transition-all ${
                activeTab === "consensus"
                  ? "border-cyan-500 text-white"
                  : "border-transparent text-scada-dimText hover:text-white"
              }`}
            >
              <Zap size={10} />
              Consensus ({consensusResults.length})
            </button>
            <button
              onClick={() => setActiveTab("graph")}
              className={`flex-1 pb-1 text-[8px] font-mono uppercase font-bold tracking-wider flex items-center justify-center gap-1 border-b-2 transition-all ${
                activeTab === "graph"
                  ? "border-cyan-500 text-white"
                  : "border-transparent text-scada-dimText hover:text-white"
              }`}
            >
              <GitPullRequest size={10} />
              Cooperation
            </button>
            <button
              onClick={() => setActiveTab("conflicts")}
              className={`flex-1 pb-1 text-[8px] font-mono uppercase font-bold tracking-wider flex items-center justify-center gap-1 border-b-2 transition-all ${
                activeTab === "conflicts"
                  ? "border-cyan-500 text-white"
                  : "border-transparent text-scada-dimText hover:text-white"
              }`}
            >
              <ShieldAlert size={10} />
              Conflicts ({conflicts.length})
            </button>
          </div>

          {/* Tab Content */}
          <div className="flex-1 overflow-y-auto bg-black/15 border border-scada-border/30 rounded p-1 max-h-[108px] scrollbar-thin">
            
            {/* 1. AGENTS TAB */}
            {activeTab === "agents" && (
              <div className="space-y-1">
                {agents.map((agent, idx) => {
                  const details = AGENT_DESCRIPTIONS[agent.agent_name] || { role: "Subsystem Agent", desc: "Cooperative smart grid stabilizer." };
                  const agentConf = confidences[agent.agent_name] ?? agent.confidence;
                  
                  return (
                    <div
                      key={idx}
                      className="bg-scada-bg/60 border border-scada-border/40 rounded p-1 flex flex-col justify-between gap-0.5 text-[8px] font-mono leading-tight hover:border-cyan-500/40 transition-colors"
                    >
                      <div className="flex justify-between items-center font-bold">
                        <span className="text-cyan-400 uppercase text-[7.5px] truncate">
                          {agent.agent_name.replace("Agent", "")}
                        </span>
                        <div className="flex items-center gap-1.5 text-[6.5px]">
                          <span className="bg-cyan-500/10 px-1 py-0.2 rounded border border-cyan-500/20 text-cyan-300">
                            WT: {agent.weight.toFixed(1)}
                          </span>
                          <span className="bg-emerald-500/10 px-1 py-0.2 rounded border border-emerald-500/20 text-emerald-400">
                            CONF: {Math.round(agentConf * 100)}%
                          </span>
                        </div>
                      </div>
                      <p className="text-white/60 leading-tight text-[6.5px] font-sans">{details.desc}</p>
                      
                      {/* Trust Bar */}
                      <div className="flex items-center gap-2 mt-1 border-t border-scada-border/10 pt-1 shrink-0">
                        <span className="text-[6.5px] text-scada-dimText uppercase shrink-0">Trust Score:</span>
                        <div className="flex-1 bg-scada-bg h-1 rounded-full overflow-hidden border border-scada-border/40">
                          <div
                            className={`h-full transition-all duration-500 ${
                              agent.trust >= 0.8 ? "bg-emerald-500" : agent.trust >= 0.5 ? "bg-yellow-500" : "bg-red-500"
                            }`}
                            style={{ width: `${agent.trust * 100}%` }}
                          ></div>
                        </div>
                        <span className="text-[7px] text-white font-bold shrink-0">{agent.trust.toFixed(2)}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            {/* 2. CONSENSUS TAB */}
            {activeTab === "consensus" && (
              <div className="space-y-1">
                {consensusResults.map((result, idx) => (
                  <div
                    key={idx}
                    className="bg-scada-bg/60 border border-scada-border/40 rounded p-1 flex flex-col justify-between gap-1 text-[8px] font-mono leading-tight"
                  >
                    {/* Header */}
                    <div className="flex justify-between items-center font-bold">
                      <span className="text-white/80 uppercase text-[7.5px] truncate">
                        {result.proposal.command} {result.proposal.target}
                      </span>
                      <span className={`px-1 py-0.2 rounded border text-[6.5px] ${
                        result.approved 
                          ? "bg-emerald-500/25 border-emerald-500/50 text-emerald-300"
                          : "bg-red-500/25 border-red-500/50 text-red-300 animate-pulse"
                      }`}>
                        {result.approved ? "APPROVED" : result.has_veto ? "VETOED" : "REJECTED"}
                      </span>
                    </div>

                    <div className="flex justify-between items-center text-[7px] text-scada-dimText border-b border-scada-border/15 pb-0.5">
                      <span>Source: {result.proposal.source} ({result.proposal.source_agent?.replace("Agent", "") || "External"})</span>
                      <span className="text-white font-semibold">Weighted Score: <span className={result.consensus_score >= 0.15 ? "text-emerald-400" : "text-red-400"}>{result.consensus_score.toFixed(2)}</span> / 0.15</span>
                    </div>

                    {/* Votes breakdown */}
                    <div className="grid grid-cols-2 gap-1 text-[6.5px] mt-0.5 leading-snug">
                      {Object.entries(result.votes).map(([agentName, voteInfo]) => (
                        <div key={agentName} className="flex justify-between items-center border border-scada-border/10 p-0.5 rounded bg-black/10">
                          <span className="text-gray-400 truncate max-w-[70px]">{agentName.replace("Agent", "")}</span>
                          <span className={`px-1 py-0.2 rounded text-[6px] border ${getVoteBadgeStyle(voteInfo.vote)}`}>
                            {getVoteText(voteInfo.vote)}
                          </span>
                        </div>
                      ))}
                    </div>

                    {result.has_veto && (
                      <div className="mt-1 bg-red-950/20 border border-red-900/35 rounded p-1 text-[6.5px] text-red-400 flex items-start gap-1">
                        <ShieldAlert size={10} className="shrink-0 text-red-500" />
                        <span>Vetoed by: {result.vetoed_by.join(", ").replace(/Agent/g, "")}</span>
                      </div>
                    )}
                  </div>
                ))}
                {consensusResults.length === 0 && (
                  <div className="text-[8.5px] text-scada-dimText font-mono italic text-center py-6 flex flex-col items-center justify-center gap-1">
                    <Sparkles size={12} className="text-emerald-400" />
                    <span>No active actions proposed to Consensus Bus</span>
                  </div>
                )}
              </div>
            )}

            {/* 3. COOPERATION GRAPH TAB */}
            {activeTab === "graph" && (
              <div className="font-mono text-[7px] space-y-1.5 pr-0.5">
                <div className="bg-cyan-950/20 border border-cyan-900/35 rounded p-1 mb-1 grid grid-cols-1 gap-1 text-[7px] leading-snug">
                  <span className="text-cyan-400 font-bold uppercase block border-b border-scada-border/10 pb-0.2 mb-0.5">
                    Consensus Rules & Multi-Agent Data Flows:
                  </span>
                  
                  <div className="flex items-start gap-1">
                    <Zap size={10} className="shrink-0 text-yellow-400 mt-0.5" />
                    <p className="text-white/80">
                      <strong>Prediction $\rightarrow$ Stabilization/Survival:</strong> Forecast collapse trajectories feed generation outputs and island triggers.
                    </p>
                  </div>
                  
                  <div className="flex items-start gap-1 mt-0.5">
                    <ShieldCheck size={10} className="shrink-0 text-red-400 mt-0.5" />
                    <p className="text-white/80">
                      <strong>CyberDefense $\dashv$ Restoration:</strong> Containment lockdowns veto close commands on compromised lines and switches.
                    </p>
                  </div>

                  <div className="flex items-start gap-1 mt-0.5">
                    <HeartPulse size={10} className="shrink-0 text-emerald-400 mt-0.5" />
                    <p className="text-white/80">
                      <strong>Survival $\dashv$ Stabilization:</strong> Critical Hospital Bus 5 load protection vetoes load-shedding commands.
                    </p>
                  </div>

                  <div className="flex items-start gap-1 mt-0.5">
                    <Sliders size={10} className="shrink-0 text-purple-400 mt-0.5" />
                    <p className="text-white/80">
                      <strong>Orchestrator:</strong> Aggregates weighted agent consensus, scales cyber weights statefully, and penalizes trust scores on rollback events.
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* 4. CONFLICTS TAB */}
            {activeTab === "conflicts" && (
              <div className="space-y-1">
                {conflicts.map((conflict, idx) => (
                  <div
                    key={idx}
                    className="bg-red-950/10 border border-red-500/25 rounded p-1.5 text-[7.5px] font-mono leading-tight hover:bg-red-950/20 transition-all"
                  >
                    <div className="flex justify-between font-bold text-red-400 mb-0.5">
                      <span>{conflict.type}</span>
                      <span className="text-white uppercase">{conflict.proposal.command} {conflict.proposal.target}</span>
                    </div>
                    <p className="text-gray-400 leading-snug">{conflict.arbitration}</p>
                    <span className="text-[6.5px] text-gray-500 uppercase block mt-1">Gated Source: {conflict.proposal.source}</span>
                  </div>
                ))}
                {conflicts.length === 0 && (
                  <div className="text-[8.5px] text-scada-dimText font-mono italic text-center py-6 flex flex-col items-center justify-center gap-1">
                    <CheckCircle2 size={12} className="text-emerald-400" />
                    <span>No agent conflicts detected. Cooperation nominal.</span>
                  </div>
                )}
              </div>
            )}

          </div>

          {/* Footer Info */}
          <div className="flex justify-between items-center border-t border-scada-border/20 pt-1 shrink-0 font-mono text-[7.5px] text-scada-dimText mt-1">
            <span className="uppercase text-[6px]">Multi-Agent Coordinator</span>
            <span>
              {agentsData ? new Date(agentsData.timestamp).toLocaleTimeString([], { hour12: false }) : "SYNCED"}
            </span>
          </div>
        </div>
      )}
    </div>
  );
};
