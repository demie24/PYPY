import React, { useState, useEffect } from "react";
import { 
  Folder, Play, Square, Pause, ShieldAlert, 
  Search, Tag, Share2, Copy, Trash2, ArrowLeftRight, Download, Clock, AlertTriangle
} from "lucide-react";
import { 
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, 
  AreaChart, Area
} from "recharts";

interface Experiment {
  id: string;
  name: string;
  grid_type: string;
  description?: string;
  verdict?: string;
  resilience_score: number;
  archived: boolean;
  locked: boolean;
  read_only: boolean;
  created_at: string;
  tags?: string[];
}

interface ComparisonData {
  experiment_a: any;
  experiment_b: any;
}

interface ReplayData {
  telemetry_history: any[];
  scada_events: string[];
  attack_events: string[];
  flisr_actions: string[];
}

interface ResearchWorkspaceProps {
  planTier: string;
  onUpgradeClick: () => void;
  token?: string;
}

export const ResearchWorkspace: React.FC<ResearchWorkspaceProps> = ({
  planTier,
  onUpgradeClick,
  token = ""
}) => {
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [search, setSearch] = useState("");
  const [selectedTag, setSelectedTag] = useState<string>("All");
  
  // Actions
  const [compareList, setCompareList] = useState<string[]>([]);
  const [compareResult, setCompareResult] = useState<ComparisonData | null>(null);
  
  // Replay timeline
  const [replayExpId, setReplayExpId] = useState<string | null>(null);
  const [replayData, setReplayData] = useState<ReplayData | null>(null);
  const [replayState, setReplayState] = useState<'idle' | 'playing' | 'paused'>('idle');
  const [replayStep, setReplayStep] = useState(0);

  // Modals
  const [sharingExp, setSharingExp] = useState<Experiment | null>(null);
  const [shareUserId, setShareUserId] = useState("");
  const [shareTenantId, setShareTenantId] = useState("");

  const fetchExperiments = async () => {
    try {
      const headers: HeadersInit = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;
      
      const params = new URLSearchParams();
      if (search) params.append("search", search);
      if (selectedTag !== "All") params.append("tag", selectedTag);
      
      const res = await fetch(`/api/experiments?${params.toString()}`, { headers });
      if (res.ok) {
        const data = await res.json();
        setExperiments(data);
      }
    } catch (err) {
      console.error("Error fetching experiments:", err);
    }
  };

  const handleDuplicate = async (expId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    const exp = experiments.find(e => e.id === expId);
    if (!exp) return;
    try {
      const res = await fetch("/api/experiments", {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${token}`,
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          name: `${exp.name} (Copy)`,
          grid_type: exp.grid_type,
          description: exp.description || "",
          tags: exp.tags || []
        })
      });
      if (res.ok) {
        fetchExperiments();
      } else {
        const err = await res.json();
        alert(err.detail || "Failed to duplicate experiment");
      }
    } catch (err) {
      console.error("Duplicate failure:", err);
    }
  };

  const handleDelete = async (expId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm("Are you sure you want to delete this experiment record?")) return;
    try {
      const res = await fetch(`/api/experiments/${expId}`, {
        method: "DELETE",
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (res.ok) {
        setExperiments(experiments.filter(e => e.id !== expId));
        if (compareList.includes(expId)) setCompareList([]);
        if (replayExpId === expId) setReplayExpId(null);
      }
    } catch (err) {
      console.error("Delete failure:", err);
    }
  };

  const toggleCompare = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (compareList.includes(id)) {
      setCompareList(compareList.filter(item => item !== id));
      setCompareResult(null);
    } else {
      if (compareList.length >= 2) return;
      const newList = [...compareList, id];
      setCompareList(newList);
      if (newList.length === 2) {
        triggerComparison(newList);
      }
    }
  };

  const triggerComparison = async (ids: string[]) => {
    try {
      const res = await fetch("/api/experiments/compare", {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${token}`,
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ experiment_ids: ids })
      });
      if (res.ok) {
        const data = await res.json();
        setCompareResult(data);
      }
    } catch (err) {
      console.error("Comparison load failure:", err);
    }
  };

  const handleStartReplay = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setReplayExpId(id);
    setReplayStep(0);
    setReplayState("playing");
    try {
      const res = await fetch(`/api/experiments/${id}/replay`, {
        method: "POST",
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setReplayData(data);
      }
    } catch (err) {
      console.error("Replay download failure:", err);
    }
  };

  const handleShareSubmit = async () => {
    if (!sharingExp) return;
    try {
      const res = await fetch(`/api/experiments/${sharingExp.id}/share`, {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${token}`,
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          shared_with_user_id: shareUserId || null,
          shared_with_tenant_id: shareTenantId || null
        })
      });
      if (res.ok) {
        alert("Experiment shared successfully.");
        setSharingExp(null);
        setShareUserId("");
        setShareTenantId("");
      } else {
        const err = await res.json();
        alert(`Sharing restriction enforced: ${err.detail}`);
      }
    } catch (err) {
      console.error("Share error:", err);
    }
  };

  useEffect(() => {
    setLoading(true);
    fetchExperiments().finally(() => setLoading(false));
  }, [search, selectedTag, token]);

  // Periodic Replay Tick Simulation
  useEffect(() => {
    let interval: any = null;
    if (replayState === "playing" && replayData) {
      interval = setInterval(() => {
        setReplayStep(prev => {
          if (prev >= replayData.telemetry_history.length - 1) {
            setReplayState("paused");
            return prev;
          }
          return prev + 1;
        });
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [replayState, replayData]);

  // Unique tags list extraction
  const allTags = ["All", ...Array.from(new Set(experiments.flatMap(e => e.tags || [])))];

  // Compare chart data preparation
  const chartData = compareResult ? [
    {
      metric: "Detection Rate",
      [compareResult.experiment_a.id.substring(0, 8)]: compareResult.experiment_a.detection_rate,
      [compareResult.experiment_b.id.substring(0, 8)]: compareResult.experiment_b.detection_rate
    },
    {
      metric: "Resilience Score",
      [compareResult.experiment_a.id.substring(0, 8)]: compareResult.experiment_a.resilience_score,
      [compareResult.experiment_b.id.substring(0, 8)]: compareResult.experiment_b.resilience_score
    },
    {
      metric: "Attack Success Rate",
      [compareResult.experiment_a.id.substring(0, 8)]: compareResult.experiment_a.attack_success_rate,
      [compareResult.experiment_b.id.substring(0, 8)]: compareResult.experiment_b.attack_success_rate
    }
  ] : [];

  return (
    <div className="flex flex-col gap-6 w-full h-full p-6 overflow-y-auto text-[#E5E7EB] font-sans">
      
      {/* Header Banner */}
      <div className="bg-gradient-to-r from-[#111827] to-[#1f2937] border border-[#374151] rounded-xl p-6 flex justify-between items-center shadow-2xl">
        <div className="space-y-1">
          <h2 className="text-xl font-bold text-white uppercase tracking-wider flex items-center gap-2">
            <Folder className="text-amber-500 w-6 h-6" /> Research Workspace & Experiments
          </h2>
          <p className="text-xs text-[#9CA3AF]">
            Query time-series telemetry databases, compute comparative metrics, share findings, and replay cyber-physical attacks.
          </p>
        </div>
        
        {planTier.toLowerCase() === 'free' && (
          <div className="flex items-center gap-3 bg-amber-500/10 border border-amber-500/30 p-3 rounded-lg shadow-inner">
            <ShieldAlert className="text-amber-500 w-5 h-5 shrink-0" />
            <div>
              <span className="text-[11px] text-white font-bold block">Community Limits Active</span>
              <span className="text-[9px] text-[#9CA3AF]">Max 10 stored experiments.</span>
            </div>
            <button 
              onClick={onUpgradeClick}
              className="px-2.5 py-1 bg-amber-500 hover:bg-amber-600 text-slate-900 font-bold rounded text-[10px] transition-colors"
            >
              UPGRADE
            </button>
          </div>
        )}
      </div>

      {/* Filter and Query Toolbar */}
      <div className="bg-[#111827] border border-[#1F2937] rounded-lg p-4 grid grid-cols-1 md:grid-cols-3 gap-4 items-center">
        <div className="relative">
          <Search className="absolute left-3 top-2.5 text-[#9CA3AF] w-4 h-4" />
          <input 
            type="text" 
            placeholder="Search experiments by name..." 
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 bg-[#1F2937] border border-[#374151] rounded-md text-xs text-white focus:outline-none focus:ring-1 focus:ring-amber-500"
          />
        </div>

        <div className="flex items-center gap-2">
          <Tag className="text-[#9CA3AF] w-4 h-4" />
          <select 
            value={selectedTag} 
            onChange={(e) => setSelectedTag(e.target.value)}
            className="flex-1 px-3 py-1.5 bg-[#1F2937] border border-[#374151] rounded-md text-xs text-white focus:outline-none"
          >
            {allTags.map(tag => (
              <option key={tag} value={tag}>{tag}</option>
            ))}
          </select>
        </div>

        <div className="flex justify-end gap-2">
          {compareList.length > 0 && (
            <button 
              onClick={() => {
                setCompareList([]);
                setCompareResult(null);
              }}
              className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-[#9CA3AF] hover:text-white border border-[#374151] rounded-md text-xs transition"
            >
              Clear Comparison ({compareList.length})
            </button>
          )}
        </div>
      </div>

      {/* Content Columns */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Left Column: Experiments Listing */}
        <div className="lg:col-span-2 bg-[#111827] border border-[#1F2937] rounded-xl p-5 flex flex-col gap-4">
          <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
            📂 Experiment Catalog
          </h3>

          {loading ? (
            <div className="text-center py-20 text-[#9CA3AF]">
              Loading saved telemetry runs...
            </div>
          ) : experiments.length === 0 ? (
            <div className="text-center py-20 text-[#9CA3AF]">
              No experiment records found. Try launching a scenario playbook first.
            </div>
          ) : (
            <div className="space-y-3 max-h-[500px] overflow-y-auto pr-1">
              {experiments.map((exp) => {
                const isComparing = compareList.includes(exp.id);
                
                return (
                  <div 
                    key={exp.id}
                    className={`border rounded-lg p-4 flex justify-between items-center transition-all duration-200 ${
                      isComparing ? "border-amber-500/80 bg-amber-500/5" : "border-[#1F2937] hover:border-slate-700 bg-[#1f2937]/30"
                    }`}
                  >
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-bold text-white block">{exp.name}</span>
                        {exp.tags && exp.tags.map(tag => (
                          <span key={tag} className="px-1.5 py-0.5 rounded bg-slate-800 text-[#9CA3AF] text-[8px] uppercase tracking-wider font-mono">
                            {tag}
                          </span>
                        ))}
                      </div>
                      <span className="text-[10px] text-[#9CA3AF]">
                        Grid Topology: <strong className="text-slate-200 font-mono">{exp.grid_type}</strong> | Run date: {new Date(exp.created_at).toLocaleDateString()}
                      </span>
                    </div>

                    <div className="flex items-center gap-2.5">
                      <button 
                        onClick={(e) => handleStartReplay(exp.id, e)}
                        className="px-2.5 py-1.5 bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/25 border border-emerald-500/20 font-bold rounded text-[10px] transition-colors flex items-center gap-1"
                      >
                        <Play className="w-3 h-3" /> Replay
                      </button>

                      <button 
                        onClick={(e) => toggleCompare(exp.id, e)}
                        className={`px-2.5 py-1.5 border font-bold rounded text-[10px] transition-colors ${
                          isComparing 
                            ? "bg-amber-500/20 border-amber-500 text-amber-400" 
                            : "border-[#374151] text-[#9CA3AF] hover:text-white hover:bg-[#1F2937]"
                        }`}
                      >
                        Compare
                      </button>

                      <button 
                        onClick={(e) => handleDuplicate(exp.id, e)}
                        className="p-1.5 text-[#9CA3AF] hover:text-white hover:bg-slate-800 rounded transition-colors"
                        title="Duplicate Experiment"
                      >
                        <Copy className="w-3.5 h-3.5" />
                      </button>

                      <button 
                        onClick={(e) => { e.stopPropagation(); setSharingExp(exp); }}
                        className="p-1.5 text-[#9CA3AF] hover:text-indigo-400 hover:bg-slate-800 rounded transition-colors"
                        title="Share Experiment"
                      >
                        <Share2 className="w-3.5 h-3.5" />
                      </button>

                      <button 
                        onClick={(e) => handleDelete(exp.id, e)}
                        className="p-1.5 text-[#9CA3AF] hover:text-red-500 hover:bg-slate-800 rounded transition-colors"
                        title="Delete Record"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Right Column: Comparative Analytics / Metrics */}
        <div className="bg-[#111827] border border-[#1F2937] rounded-xl p-5 flex flex-col gap-4">
          <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
            <ArrowLeftRight className="text-amber-500 w-4 h-4" /> Comparative Analytics
          </h3>

          {compareResult ? (
            <div className="space-y-5">
              
              {/* Header Titles */}
              <div className="grid grid-cols-2 gap-4 text-center border-b border-[#1F2937] pb-3">
                <div>
                  <span className="text-[10px] text-[#9CA3AF] uppercase block">EXP A</span>
                  <span className="text-xs font-bold text-emerald-400 truncate block">
                    {experiments.find(e => e.id === compareResult.experiment_a.id)?.name || "Experiment A"}
                  </span>
                </div>
                <div>
                  <span className="text-[10px] text-[#9CA3AF] uppercase block">EXP B</span>
                  <span className="text-xs font-bold text-amber-500 truncate block">
                    {experiments.find(e => e.id === compareResult.experiment_b.id)?.name || "Experiment B"}
                  </span>
                </div>
              </div>

              {/* Data Table */}
              <div className="space-y-3 text-xs">
                <div>
                  <span className="text-[10px] text-[#9CA3AF] block text-center mb-1 uppercase tracking-wider">Resilience Score</span>
                  <div className="grid grid-cols-2 gap-2 text-center font-bold text-sm">
                    <span className="text-emerald-400 font-mono">{compareResult.experiment_a.resilience_score.toFixed(1)}%</span>
                    <span className="text-amber-500 font-mono">{compareResult.experiment_b.resilience_score.toFixed(1)}%</span>
                  </div>
                </div>

                <div>
                  <span className="text-[10px] text-[#9CA3AF] block text-center mb-1 uppercase tracking-wider">Detection Rate</span>
                  <div className="grid grid-cols-2 gap-2 text-center font-bold text-sm">
                    <span className="text-emerald-400 font-mono">{compareResult.experiment_a.detection_rate.toFixed(1)}%</span>
                    <span className="text-amber-500 font-mono">{compareResult.experiment_b.detection_rate.toFixed(1)}%</span>
                  </div>
                </div>

                <div>
                  <span className="text-[10px] text-[#9CA3AF] block text-center mb-1 uppercase tracking-wider">Recovery Time</span>
                  <div className="grid grid-cols-2 gap-2 text-center font-bold text-sm">
                    <span className="text-emerald-400 font-mono">{compareResult.experiment_a.recovery_time}s</span>
                    <span className="text-amber-500 font-mono">{compareResult.experiment_b.recovery_time}s</span>
                  </div>
                </div>

                <div>
                  <span className="text-[10px] text-[#9CA3AF] block text-center mb-1 uppercase tracking-wider">Financial Loss</span>
                  <div className="grid grid-cols-2 gap-2 text-center font-bold text-sm">
                    <span className="text-emerald-400 font-mono">RM {compareResult.experiment_a.financial_loss.toLocaleString()}</span>
                    <span className="text-amber-500 font-mono">RM {compareResult.experiment_b.financial_loss.toLocaleString()}</span>
                  </div>
                </div>

                <div>
                  <span className="text-[10px] text-[#9CA3AF] block text-center mb-1 uppercase tracking-wider">Attack Success Rate</span>
                  <div className="grid grid-cols-2 gap-2 text-center font-bold text-sm">
                    <span className="text-emerald-400 font-mono">{compareResult.experiment_a.attack_success_rate.toFixed(1)}%</span>
                    <span className="text-amber-500 font-mono">{compareResult.experiment_b.attack_success_rate.toFixed(1)}%</span>
                  </div>
                </div>
              </div>

              {/* Bar Chart Visualization */}
              <div className="h-44 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={chartData}>
                    <XAxis dataKey="metric" stroke="#9CA3AF" fontSize={8} />
                    <YAxis stroke="#9CA3AF" fontSize={8} />
                    <Tooltip contentStyle={{ backgroundColor: "#111827", borderColor: "#374151" }} labelStyle={{ color: "#fff" }} />
                    <Bar dataKey={compareResult.experiment_a.id.substring(0, 8)} fill="#10B981" />
                    <Bar dataKey={compareResult.experiment_b.id.substring(0, 8)} fill="#F59E0B" />
                  </BarChart>
                </ResponsiveContainer>
              </div>

              {/* Reports Export Links */}
              <div className="border-t border-[#1F2937] pt-4 space-y-2">
                <span className="text-[10px] text-[#9CA3AF] block uppercase tracking-wider font-mono">Generate Experiment Report</span>
                <div className="grid grid-cols-3 gap-2">
                  <a 
                    href={`/api/experiments/${compareResult.experiment_a.id}/export/pdf`}
                    download
                    className="py-1.5 bg-[#1F2937] hover:bg-[#374151] rounded text-[10px] font-bold text-center border border-[#374151] flex items-center justify-center gap-1"
                  >
                    <Download className="w-3 h-3" /> PDF
                  </a>
                  <a 
                    href={`/api/experiments/${compareResult.experiment_a.id}/export/csv`}
                    download
                    className="py-1.5 bg-[#1F2937] hover:bg-[#374151] rounded text-[10px] font-bold text-center border border-[#374151] flex items-center justify-center gap-1"
                  >
                    <Download className="w-3 h-3" /> CSV
                  </a>
                  <a 
                    href={`/api/experiments/${compareResult.experiment_a.id}/export/json`}
                    download
                    className="py-1.5 bg-[#1F2937] hover:bg-[#374151] rounded text-[10px] font-bold text-center border border-[#374151] flex items-center justify-center gap-1"
                  >
                    <Download className="w-3 h-3" /> JSON
                  </a>
                </div>
              </div>

            </div>
          ) : (
            <div className="flex flex-col items-center justify-center h-80 border border-dashed border-[#1F2937] rounded-xl text-[#9CA3AF]">
              <ArrowLeftRight className="w-8 h-8 mb-2 opacity-40 text-amber-500" />
              <span className="text-xs">Compare two experiments side-by-side.</span>
              <span className="text-[10px] text-slate-500">Check compare checkboxes in catalog list.</span>
            </div>
          )}

        </div>
      </div>

      {/* Historical Replay Slider Console */}
      {replayExpId && replayData && (
        <div className="bg-[#111827] border border-amber-500/30 rounded-xl p-5 flex flex-col gap-4 shadow-xl">
          
          <div className="flex items-center justify-between border-b border-[#1F2937] pb-3">
            <div className="flex items-center gap-2">
              <span className="animate-pulse w-2.5 h-2.5 rounded-full bg-emerald-500" />
              <h3 className="text-sm font-bold text-white uppercase tracking-wider">
                Replaying Grid Playbook Trace: {experiments.find(e => e.id === replayExpId)?.name}
              </h3>
            </div>
            
            <div className="flex items-center gap-3">
              <button 
                onClick={() => setReplayState(replayState === "playing" ? "paused" : "playing")}
                className="p-1.5 bg-[#1F2937] hover:bg-slate-800 rounded border border-[#374151] text-white"
              >
                {replayState === "playing" ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
              </button>
              <button 
                onClick={() => {
                  setReplayState("idle");
                  setReplayExpId(null);
                  setReplayData(null);
                }}
                className="p-1.5 bg-[#1F2937] hover:bg-slate-800 rounded border border-[#374151] text-white"
              >
                <Square className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Slider */}
          <div className="flex items-center gap-4 bg-[#1F2937]/30 border border-[#1F2937] p-3 rounded-lg">
            <span className="text-[10px] font-mono text-[#9CA3AF]">Frame 0</span>
            <input 
              type="range"
              min="0"
              max={replayData.telemetry_history.length - 1}
              value={replayStep}
              onChange={(e) => setReplayStep(parseInt(e.target.value))}
              className="flex-1 accent-amber-500 cursor-pointer"
            />
            <span className="text-[10px] font-mono text-white font-bold">
              Frame {replayStep} / {replayData.telemetry_history.length - 1}
            </span>
          </div>

          {/* Telemetry Chart & Log Traces */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            
            {/* Visual Chart */}
            <div className="bg-[#1f2937]/20 border border-[#1F2937] rounded-lg p-4 h-56 flex flex-col justify-between">
              <span className="text-[10px] text-[#9CA3AF] uppercase block mb-2 font-mono">Dynamic Telemetry Monitor</span>
              <div className="flex-1 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={replayData.telemetry_history.slice(0, replayStep + 1)}>
                    <XAxis dataKey="step" stroke="#9CA3AF" fontSize={8} />
                    <YAxis stroke="#9CA3AF" fontSize={8} />
                    <Tooltip contentStyle={{ backgroundColor: "#111827", borderColor: "#374151" }} />
                    <Area type="monotone" dataKey="voltage" stroke="#10B981" fill="#10B981" fillOpacity={0.1} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* SCADA Actions Log */}
            <div className="bg-[#1f2937]/20 border border-[#1F2937] rounded-lg p-4 h-56 flex flex-col">
              <span className="text-[10px] text-[#9CA3AF] uppercase block mb-3 font-mono flex items-center gap-1">
                <Clock className="w-3.5 h-3.5 text-emerald-400" /> SCADA Event Logs
              </span>
              <div className="flex-1 overflow-y-auto space-y-2 font-mono text-[10px]">
                {replayData.scada_events.map((evt, idx) => (
                  <div key={idx} className="border-l-2 border-emerald-500 pl-2 text-slate-300">
                    {evt}
                  </div>
                ))}
              </div>
            </div>

            {/* Attack & FLISR Logs */}
            <div className="bg-[#1f2937]/20 border border-[#1F2937] rounded-lg p-4 h-56 flex flex-col">
              <span className="text-[10px] text-[#9CA3AF] uppercase block mb-3 font-mono flex items-center gap-1">
                <AlertTriangle className="w-3.5 h-3.5 text-rose-500" /> Intrusion & Recovery Log
              </span>
              <div className="flex-1 overflow-y-auto space-y-2 font-mono text-[10px]">
                {replayData.attack_events.map((evt, idx) => (
                  <div key={idx} className="border-l-2 border-rose-500 pl-2 text-rose-400">
                    [Intrusion] {evt}
                  </div>
                ))}
                {replayData.flisr_actions.map((evt, idx) => (
                  <div key={idx} className="border-l-2 border-blue-500 pl-2 text-blue-400">
                    [FLISR-Auto] {evt}
                  </div>
                ))}
              </div>
            </div>

          </div>

        </div>
      )}

      {/* Share Configuration Modal */}
      {sharingExp && (
        <div className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4 backdrop-blur-sm">
          <div className="bg-[#111827] border border-[#374151] rounded-xl max-w-sm w-full p-6 shadow-2xl space-y-4">
            <h3 className="text-base font-bold text-white uppercase">Share Experiment</h3>
            <p className="text-xs text-[#9CA3AF]">
              Configure peer access rules for <strong className="text-white">{sharingExp.name}</strong>.
            </p>
            
            <div className="space-y-3">
              <div>
                <label className="text-[10px] text-[#9CA3AF] uppercase block mb-1">Target User ID</label>
                <input 
                  type="text"
                  placeholder="e.g. 5f0426bb-..."
                  value={shareUserId}
                  onChange={(e) => setShareUserId(e.target.value)}
                  className="w-full px-3 py-1.5 bg-[#1F2937] border border-[#374151] rounded text-xs text-white placeholder-slate-600 focus:outline-none focus:ring-1 focus:ring-amber-500"
                />
              </div>

              <div>
                <label className="text-[10px] text-[#9CA3AF] uppercase block mb-1">Target Tenant ID</label>
                <input 
                  type="text"
                  placeholder="e.g. a8b42cf9-..."
                  value={shareTenantId}
                  onChange={(e) => setShareTenantId(e.target.value)}
                  className="w-full px-3 py-1.5 bg-[#1F2937] border border-[#374151] rounded text-xs text-white placeholder-slate-600 focus:outline-none focus:ring-1 focus:ring-amber-500"
                />
              </div>
            </div>

            <div className="flex justify-end gap-3 pt-2">
              <button 
                onClick={() => setSharingExp(null)}
                className="px-4 py-2 border border-[#374151] hover:bg-[#1F2937] text-white rounded text-xs transition"
              >
                Cancel
              </button>
              <button 
                onClick={handleShareSubmit}
                className="px-4 py-2 bg-amber-500 hover:bg-amber-600 text-slate-900 font-bold rounded text-xs transition"
              >
                Submit Share
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
};
