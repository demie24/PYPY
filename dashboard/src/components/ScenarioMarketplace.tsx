import React, { useEffect, useState } from "react";
import { 
  Search, Lock, ExternalLink, Zap, BookOpen, Clock, Heart, Sparkles
} from "lucide-react";

interface ScenarioTemplate {
  id: string;
  name: string;
  description: string;
  grid_type: string;
  category: string;
  difficulty: string;
  mitre_attack_id: string;
  mitre_attack_name: string;
  objective: string;
  timeline: string[];
  impact: string;
  required_plan: string;
  config: any;
}

interface ScenarioMarketplaceProps {
  planTier: string;
  onUpgradeClick: () => void;
  token?: string;
}

const PLAN_LEVELS: { [key: string]: number } = {
  "free": 0,
  "academic_premium": 1,
  "research_lab": 2,
  "enterprise": 3
};

export const ScenarioMarketplace: React.FC<ScenarioMarketplaceProps> = ({
  planTier,
  onUpgradeClick,
  token = ""
}) => {
  const [scenarios, setScenarios] = useState<ScenarioTemplate[]>([]);
  const [favorites, setFavorites] = useState<string[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [selectedScenario, setSelectedScenario] = useState<ScenarioTemplate | null>(null);
  
  // Filters state
  const [search, setSearch] = useState<string>("");
  const [category, setCategory] = useState<string>("All");
  const [difficulty, setDifficulty] = useState<string>("All");
  const [gridType, setGridType] = useState<string>("All");
  
  // Launching action states
  const [launchingId, setLaunchingId] = useState<string | null>(null);

  const fetchScenarios = async () => {
    try {
      const headers: HeadersInit = {};
      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }
      
      // Build query string
      const params = new URLSearchParams();
      if (category !== "All") params.append("category", category);
      if (difficulty !== "All") params.append("difficulty", difficulty);
      if (gridType !== "All") params.append("grid_type", gridType);
      if (search) params.append("search", search);
      
      const res = await fetch(`/api/scenarios?${params.toString()}`, { headers });
      if (res.ok) {
        const data = await res.json();
        // Parse timeline JSON if returned as string
        const parsed = data.map((item: any) => ({
          ...item,
          timeline: typeof item.timeline === "string" ? JSON.parse(item.timeline) : item.timeline
        }));
        setScenarios(parsed);
      }
    } catch (err) {
      console.error("Error fetching scenarios:", err);
    }
  };

  const fetchFavorites = async () => {
    if (!token) return;
    try {
      const res = await fetch("/api/scenarios/favorites", {
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setFavorites(data.map((fav: any) => fav.id));
      }
    } catch (err) {
      console.error("Error fetching favorites:", err);
    }
  };

  const handleToggleFavorite = async (templateId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!token) return;
    const isFav = favorites.includes(templateId);
    try {
      const headers = {
        "Authorization": `Bearer ${token}`,
        "Content-Type": "application/json"
      };
      if (isFav) {
        const res = await fetch(`/api/scenarios/favorites/${templateId}`, {
          method: "DELETE",
          headers
        });
        if (res.ok) {
          setFavorites(favorites.filter(id => id !== templateId));
        }
      } else {
        const res = await fetch("/api/scenarios/favorites", {
          method: "POST",
          headers,
          body: JSON.stringify({ template_id: templateId })
        });
        if (res.ok) {
          setFavorites([...favorites, templateId]);
        }
      }
    } catch (err) {
      console.error("Error toggling favorite:", err);
    }
  };

  const handleDeployScenario = async (scenario: ScenarioTemplate, e: React.MouseEvent) => {
    e.stopPropagation();
    const userRank = PLAN_LEVELS[planTier.toLowerCase()] ?? 1;
    const reqRank = PLAN_LEVELS[scenario.required_plan.toLowerCase()] ?? 0;
    
    if (userRank < reqRank) {
      alert(`Access Restricted: Upgrading your subscription plan is required to unlock ${scenario.name}.`);
      onUpgradeClick();
      return;
    }
    
    setLaunchingId(scenario.id);
    try {
      const res = await fetch(`/api/scenarios/${scenario.id}/launch`, {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${token}`,
          "Content-Type": "application/json"
        }
      });
      if (res.ok) {
        const data = await res.json();
        alert(`Successfully launched simulation run!\nJob ID: ${data.job_id}`);
      } else {
        const err = await res.json();
        alert(`Failed to launch: ${err.detail || "Orchestration system error"}`);
      }
    } catch (err) {
      console.error("Error launching scenario:", err);
    } finally {
      setLaunchingId(null);
    }
  };

  useEffect(() => {
    setLoading(true);
    Promise.all([fetchScenarios(), fetchFavorites()]).finally(() => setLoading(false));
  }, [category, difficulty, gridType, search, token]);

  const userPlanRank = PLAN_LEVELS[planTier.toLowerCase()] ?? 1;

  return (
    <div className="flex flex-col gap-6 w-full h-full p-6 overflow-y-auto text-[#E5E7EB] font-sans">
      
      {/* Header Panel */}
      <div className="relative overflow-hidden bg-gradient-to-r from-[#111827] to-[#1f2937] border border-[#374151] rounded-xl p-6 shadow-2xl flex items-center justify-between">
        <div className="space-y-2 relative z-10">
          <h2 className="text-xl font-bold text-white uppercase tracking-wider flex items-center gap-2">
            <BookOpen className="text-emerald-400 w-6 h-6" /> Cyber Range Scenario Library
          </h2>
          <p className="text-xs text-[#9CA3AF] max-w-2xl">
            Deploy pre-configured cyber-physical attacks and contingencies into production simulation containers instantly. Ensure that your current subscription rank matches the scenario difficulty.
          </p>
        </div>
        <div className="absolute right-0 top-0 opacity-10 pointer-events-none transform translate-x-10 -translate-y-10">
          <Sparkles className="w-64 h-64 text-emerald-400" />
        </div>
      </div>

      {/* Filters Section */}
      <div className="bg-[#111827] border border-[#1F2937] rounded-lg p-4 grid grid-cols-1 md:grid-cols-4 gap-4 items-center">
        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-2.5 text-[#9CA3AF] w-4 h-4" />
          <input 
            type="text" 
            placeholder="Search scenarios..." 
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 bg-[#1F2937] border border-[#374151] rounded-md text-xs text-white placeholder-[#9CA3AF] focus:ring-1 focus:ring-emerald-500 focus:outline-none"
          />
        </div>

        {/* Category Filter */}
        <div>
          <select 
            value={category} 
            onChange={(e) => setCategory(e.target.value)}
            className="w-full px-3 py-1.5 bg-[#1F2937] border border-[#374151] rounded-md text-xs text-white focus:ring-1 focus:ring-emerald-500 focus:outline-none"
          >
            <option value="All">All Categories</option>
            <option value="Attack">Attacks</option>
            <option value="Contingency">Contingencies</option>
            <option value="Validation">Validations</option>
          </select>
        </div>

        {/* Difficulty Filter */}
        <div>
          <select 
            value={difficulty} 
            onChange={(e) => setDifficulty(e.target.value)}
            className="w-full px-3 py-1.5 bg-[#1F2937] border border-[#374151] rounded-md text-xs text-white focus:ring-1 focus:ring-emerald-500 focus:outline-none"
          >
            <option value="All">All Difficulties</option>
            <option value="Beginner">Beginner</option>
            <option value="Intermediate">Intermediate</option>
            <option value="Advanced">Advanced</option>
            <option value="Expert">Expert</option>
          </select>
        </div>

        {/* Grid Model Filter */}
        <div>
          <select 
            value={gridType} 
            onChange={(e) => setGridType(e.target.value)}
            className="w-full px-3 py-1.5 bg-[#1F2937] border border-[#374151] rounded-md text-xs text-white focus:ring-1 focus:ring-emerald-500 focus:outline-none"
          >
            <option value="All">All Grids</option>
            <option value="IEEE14">IEEE 14 Bus</option>
            <option value="IEEE39">IEEE 39 Bus</option>
            <option value="IEEE57">IEEE 57 Bus</option>
            <option value="IEEE118">IEEE 118 Bus</option>
          </select>
        </div>
      </div>

      {/* Grid List */}
      {loading ? (
        <div className="flex items-center justify-center py-20 text-[#9CA3AF]">
          <span className="animate-spin mr-2">&#9696;</span> Loading scenarios catalog...
        </div>
      ) : scenarios.length === 0 ? (
        <div className="text-center py-20 text-[#9CA3AF]">
          No scenario templates match your filter selections.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {scenarios.map((sc) => {
            const reqRank = PLAN_LEVELS[sc.required_plan.toLowerCase()] ?? 0;
            const isLocked = userPlanRank < reqRank;
            const isFav = favorites.includes(sc.id);
            
            return (
              <div 
                key={sc.id}
                onClick={() => setSelectedScenario(sc)}
                className={`group cursor-pointer bg-[#111827] border ${
                  isLocked ? "border-rose-950/40 hover:border-rose-900/50" : "border-[#1F2937] hover:border-emerald-500/40"
                } rounded-xl p-5 flex flex-col justify-between transition-all duration-300 transform hover:-translate-y-1 shadow-lg relative`}
              >
                <div>
                  <div className="flex justify-between items-start mb-3 gap-2">
                    <h3 className="text-sm font-bold text-white group-hover:text-emerald-400 transition-colors uppercase tracking-wide">
                      {sc.name}
                    </h3>
                    <div className="flex gap-2">
                      <button 
                        onClick={(e) => handleToggleFavorite(sc.id, e)}
                        className={`text-slate-500 hover:text-red-500 transition-colors`}
                      >
                        <Heart className={`w-4 h-4 ${isFav ? "fill-red-500 text-red-500" : ""}`} />
                      </button>
                    </div>
                  </div>

                  <p className="text-xs text-[#9CA3AF] mb-4 line-clamp-3 leading-relaxed">
                    {sc.description}
                  </p>

                  <div className="grid grid-cols-2 gap-2 text-[10px] font-mono mb-4 text-[#9CA3AF]">
                    <div className="bg-[#1f2937]/30 border border-[#1F2937] p-2 rounded">
                      <span className="block text-[8px] uppercase tracking-wider text-[#9CA3AF] mb-0.5">Category</span>
                      <span className="text-white font-bold">{sc.category}</span>
                    </div>
                    <div className="bg-[#1f2937]/30 border border-[#1F2937] p-2 rounded">
                      <span className="block text-[8px] uppercase tracking-wider text-[#9CA3AF] mb-0.5">Difficulty</span>
                      <span className="text-white font-bold">{sc.difficulty}</span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center justify-between border-t border-[#1F2937] pt-4 mt-auto">
                  {isLocked ? (
                    <div className="flex items-center justify-between w-full">
                      <span className="text-rose-500 font-bold text-[9px] uppercase tracking-wider flex items-center gap-1">
                        <Lock className="w-3.5 h-3.5" /> LOCKED ({sc.required_plan.replace("_", " ")})
                      </span>
                      <button 
                        onClick={(e) => {
                          e.stopPropagation();
                          onUpgradeClick();
                        }}
                        className="px-2.5 py-1 bg-gradient-to-r from-amber-500 to-orange-600 hover:from-amber-600 hover:to-orange-700 text-slate-900 font-bold rounded text-[9px] transition-colors"
                      >
                        UPGRADE
                      </button>
                    </div>
                  ) : (
                    <div className="flex items-center justify-between w-full">
                      <span className="text-[10px] text-[#9CA3AF] font-mono">
                        Grid: <strong className="text-white">{sc.grid_type}</strong>
                      </span>
                      <button
                        onClick={(e) => handleDeployScenario(sc, e)}
                        disabled={launchingId === sc.id}
                        className="px-3 py-1.5 bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/25 border border-emerald-500/20 font-bold rounded text-[10px] transition-colors flex items-center gap-1"
                      >
                        {launchingId === sc.id ? (
                          <>
                            <span className="animate-spin text-[8px]">&#9696;</span> Deploying
                          </>
                        ) : (
                          <>
                            <Zap className="w-3 h-3" /> Deploy
                          </>
                        )}
                      </button>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Scenario Preview Modal */}
      {selectedScenario && (
        <div className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4 backdrop-blur-sm">
          <div className="bg-[#111827] border border-[#374151] rounded-xl max-w-xl w-full p-6 shadow-2xl relative animate-fade-in max-h-[90vh] overflow-y-auto flex flex-col space-y-4">
            
            {/* Title */}
            <div className="flex justify-between items-start border-b border-[#1F2937] pb-3">
              <div>
                <h2 className="text-lg font-bold text-white uppercase">{selectedScenario.name}</h2>
                <div className="flex gap-2 mt-1">
                  <span className="px-2 py-0.5 rounded bg-emerald-500/15 text-emerald-400 text-[9px] border border-emerald-500/20 font-bold">
                    {selectedScenario.category}
                  </span>
                  <span className="px-2 py-0.5 rounded bg-indigo-500/15 text-indigo-400 text-[9px] border border-indigo-500/20 font-bold">
                    {selectedScenario.difficulty}
                  </span>
                </div>
              </div>
              <button 
                onClick={() => setSelectedScenario(null)}
                className="text-[#9CA3AF] hover:text-white transition text-lg"
              >
                &times;
              </button>
            </div>

            {/* Modal Content */}
            <div className="space-y-4 text-xs">
              <div>
                <span className="text-[#9CA3AF] font-bold block uppercase tracking-wider mb-1">Objective</span>
                <p className="text-slate-300 leading-relaxed bg-[#1f2937]/20 border border-[#1F2937] p-3 rounded">
                  {selectedScenario.objective}
                </p>
              </div>

              <div>
                <span className="text-[#9CA3AF] font-bold block uppercase tracking-wider mb-1">MITRE ATT&CK Mapping</span>
                <div className="flex items-center gap-1.5 text-blue-400">
                  <a 
                    href={`https://attack.mitre.org/techniques/${selectedScenario.mitre_attack_id}/`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="hover:underline flex items-center gap-1 font-mono"
                  >
                    {selectedScenario.mitre_attack_id} - {selectedScenario.mitre_attack_name}
                    <ExternalLink className="w-3.5 h-3.5" />
                  </a>
                </div>
              </div>

              <div>
                <span className="text-[#9CA3AF] font-bold block uppercase tracking-wider mb-1">Recommended Grid Model</span>
                <span className="font-mono text-white text-xs">{selectedScenario.grid_type}</span>
              </div>

              <div>
                <span className="text-[#9CA3AF] font-bold block uppercase tracking-wider mb-1.5">Execution Timeline</span>
                <div className="space-y-2">
                  {selectedScenario.timeline && selectedScenario.timeline.map((step, index) => (
                    <div key={index} className="flex items-start gap-2 text-[11px]">
                      <Clock className="w-3.5 h-3.5 text-indigo-400 mt-0.5 shrink-0" />
                      <span className="text-slate-300 font-mono">{step}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <span className="text-[#9CA3AF] font-bold block uppercase tracking-wider mb-1">System Impact</span>
                <p className="text-slate-300 bg-rose-950/10 border border-rose-950/20 p-3 rounded leading-relaxed">
                  {selectedScenario.impact}
                </p>
              </div>

              <div>
                <span className="text-[#9CA3AF] font-bold block uppercase tracking-wider mb-1">Access Tier Constraint</span>
                <span className="font-bold text-white capitalize">{selectedScenario.required_plan.replace("_", " ")}</span>
              </div>
            </div>

            {/* Footer buttons */}
            <div className="border-t border-[#1F2937] pt-4 flex justify-end gap-3">
              <button 
                onClick={() => setSelectedScenario(null)}
                className="px-4 py-2 border border-[#374151] hover:bg-[#1F2937] text-white rounded text-xs transition"
              >
                Close Preview
              </button>
              {userPlanRank < (PLAN_LEVELS[selectedScenario.required_plan.toLowerCase()] ?? 0) ? (
                <button 
                  onClick={() => {
                    setSelectedScenario(null);
                    onUpgradeClick();
                  }}
                  className="px-4 py-2 bg-gradient-to-r from-amber-500 to-orange-600 hover:from-amber-600 hover:to-orange-700 text-slate-900 font-bold rounded text-xs transition flex items-center gap-1"
                >
                  <Lock className="w-3.5 h-3.5" /> Upgrade Plan
                </button>
              ) : (
                <button 
                  onClick={(e) => {
                    setSelectedScenario(null);
                    handleDeployScenario(selectedScenario, e);
                  }}
                  disabled={launchingId === selectedScenario.id}
                  className="px-4 py-2 bg-emerald-500 hover:bg-emerald-600 text-slate-900 font-bold rounded text-xs transition flex items-center gap-1.5"
                >
                  <Zap className="w-3.5 h-3.5" /> Launch Range
                </button>
              )}
            </div>

          </div>
        </div>
      )}

    </div>
  );
};
