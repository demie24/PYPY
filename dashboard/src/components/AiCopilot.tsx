import React, { useEffect, useState, useRef } from "react";
import { 
  Send, Sparkles, AlertTriangle, Download, BookOpen, 
  HelpCircle, Cpu, Clipboard, RefreshCw
} from "lucide-react";

interface Citation {
  type: string;
  name: string;
  mitre?: string;
}

interface ChatMessage {
  id?: string;
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  created_at?: string;
}

interface AiCopilotProps {
  planTier: string;
  onUpgradeClick: () => void;
  token?: string;
}

const QUOTA_LIMITS: { [key: string]: number } = {
  "free": 50,
  "academic_premium": 500,
  "research_lab": 2000,
  "enterprise": 999999
};

export const AiCopilot: React.FC<AiCopilotProps> = ({
  planTier,
  onUpgradeClick,
  token = ""
}) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputVal, setInputVal] = useState("");
  const [loading, setLoading] = useState(false);
  const [messagesCount, setMessagesCount] = useState(0);
  
  // RAG Selected Citation state
  const [activeCitations, setActiveCitations] = useState<Citation[]>([]);

  // Thesis/Journal State
  const [activeTab, setActiveTab] = useState<"chat" | "thesis">("chat");
  const [selectedSection, setSelectedSection] = useState("abstract");
  const [thesisExpId, setThesisExpId] = useState("");
  const [generatedThesis, setGeneratedThesis] = useState("");
  const [generatingThesis, setGeneratingThesis] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  const tierQuota = QUOTA_LIMITS[planTier.toLowerCase()] ?? 50;
  const isLocked = planTier.toLowerCase() === "free" && messagesCount >= tierQuota;

  const fetchHistory = async () => {
    try {
      const res = await fetch("/api/copilot/history", {
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setMessages(data);
        // Count number of user queries
        const userMsgs = data.filter((m: any) => m.role === "user").length;
        setMessagesCount(userMsgs);
      }
    } catch (err) {
      console.error("History fetch error:", err);
    }
  };

  const handleSend = async (textToSend?: string) => {
    const prompt = (textToSend || inputVal).trim();
    if (!prompt || isLocked || loading) return;

    if (!textToSend) setInputVal("");
    
    // Optimistic local add
    const tempUserMsg: ChatMessage = { role: "user", content: prompt };
    setMessages(prev => [...prev, tempUserMsg]);
    setLoading(true);

    try {
      const res = await fetch("/api/copilot/chat", {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${token}`,
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ message: prompt })
      });
      
      if (res.ok) {
        const data = await res.json();
        setMessages(prev => [...prev, { 
          role: "assistant", 
          content: data.reply,
          citations: data.citations
        }]);
        setMessagesCount(prev => prev + 1);
        if (data.citations && data.citations.length > 0) {
          setActiveCitations(data.citations);
        }
      } else {
        const err = await res.json();
        setMessages(prev => [...prev, { 
          role: "assistant", 
          content: `Quota Restriction: ${err.detail || "Server failed to reply"}` 
        }]);
      }
    } catch (err) {
      console.error("Chat error:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateThesis = async () => {
    if (!thesisExpId.trim()) {
      alert("Please enter a valid Experiment ID.");
      return;
    }
    setGeneratingThesis(true);
    try {
      const res = await fetch("/api/copilot/report", {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${token}`,
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          experiment_id: thesisExpId,
          section: selectedSection
        })
      });
      if (res.ok) {
        const data = await res.json();
        setGeneratedThesis(data.section_text);
      } else {
        const err = await res.json();
        alert(err.detail || "Failed to generate report section");
      }
    } catch (err) {
      console.error("Thesis generator failure:", err);
    } finally {
      setGeneratingThesis(false);
    }
  };

  const handleExport = () => {
    const log = messages.map(m => `[${m.role.toUpperCase()}] ${m.content}`).join("\n\n");
    const blob = new Blob([log], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `copilot_chat_${new Date().toISOString().slice(0,10)}.txt`;
    link.click();
  };

  const handleCopyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    alert("Copied text to clipboard.");
  };

  useEffect(() => {
    fetchHistory();
  }, [token]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const suggestedPrompts = [
    "Explain state estimation detection decisions on voltage collapse.",
    "Recommend FLISR mitigation actions for an active breaker fault.",
    "Summarize cybersecurity impacts mapping to MITRE ATT&CK."
  ];

  return (
    <div className="flex flex-col gap-6 w-full h-full p-6 text-[#E5E7EB] font-sans overflow-hidden">
      
      {/* Top Header Panel */}
      <div className="bg-gradient-to-r from-[#111827] to-[#1f2937] border border-[#374151] rounded-xl p-5 flex justify-between items-center shadow-xl shrink-0">
        <div className="space-y-1">
          <h2 className="text-xl font-bold text-white uppercase tracking-wider flex items-center gap-2">
            <Sparkles className="text-amber-400 w-6 h-6 animate-pulse" /> AI Copilot & Research Assistant
          </h2>
          <p className="text-xs text-[#9CA3AF]">
            Consult explainable AI models on state estimation anomalies, load resilience, and mitigation strategies.
          </p>
        </div>

        {/* Tab triggers */}
        <div className="flex gap-2 bg-[#1F2937] p-1 rounded-lg border border-[#374151]">
          <button 
            onClick={() => setActiveTab("chat")}
            className={`px-3 py-1.5 rounded-md text-xs font-bold transition-all ${
              activeTab === "chat" ? "bg-amber-500 text-slate-900" : "text-[#9CA3AF] hover:text-white"
            }`}
          >
            Chat Sandbox
          </button>
          <button 
            onClick={() => setActiveTab("thesis")}
            className={`px-3 py-1.5 rounded-md text-xs font-bold transition-all ${
              activeTab === "thesis" ? "bg-amber-500 text-slate-900" : "text-[#9CA3AF] hover:text-white"
            }`}
          >
            Thesis Assistant
          </button>
        </div>
      </div>

      {/* Monthly Quota Alert */}
      {isLocked && (
        <div className="bg-rose-950/20 border border-rose-900/50 p-4 rounded-lg flex items-center justify-between shrink-0">
          <div className="flex items-center gap-2.5 text-rose-400 text-xs">
            <AlertTriangle className="w-5 h-5 shrink-0" />
            <span>Monthly Copilot prompts quota limits reached ({messagesCount} / {tierQuota}). Upgrade plan to resume prompt completions.</span>
          </div>
          <button 
            onClick={onUpgradeClick}
            className="px-3 py-1.5 bg-gradient-to-r from-amber-500 to-orange-600 text-slate-900 font-bold rounded text-xs transition"
          >
            Upgrade Plan
          </button>
        </div>
      )}

      {/* Main Sandbox Area */}
      {activeTab === "chat" ? (
        <div className="flex-1 flex gap-6 overflow-hidden">
          
          {/* Left Area: Chat sandbox and inputs */}
          <div className="flex-1 flex flex-col gap-4 overflow-hidden">
            
            {/* Message log viewport */}
            <div className="flex-1 bg-[#111827] border border-[#1F2937] rounded-xl p-4 overflow-y-auto space-y-4">
              {messages.length === 0 ? (
                <div className="text-center py-20 text-[#9CA3AF] text-xs">
                  No chat log history. Choose a suggested prompt below to begin.
                </div>
              ) : (
                messages.map((m, idx) => (
                  <div 
                    key={idx}
                    onClick={() => m.citations && m.citations.length > 0 && setActiveCitations(m.citations)}
                    className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
                  >
                    <div 
                      className={`max-w-xl p-3.5 rounded-xl text-xs leading-relaxed transition-all ${
                        m.role === "user" 
                          ? "bg-amber-500/10 text-white border border-amber-500/20" 
                          : `bg-[#1f2937]/50 text-slate-300 border ${
                              m.citations && m.citations.length > 0 ? "border-indigo-500/30 hover:border-indigo-400/50 cursor-pointer" : "border-[#1F2937]"
                            }`
                      }`}
                    >
                      <span className="font-bold text-[10px] block uppercase tracking-wider mb-1.5 font-mono text-[#9CA3AF]">
                        {m.role === "user" ? "Researcher prompt" : "Security Assistant AI"}
                      </span>
                      <p className="whitespace-pre-line">{m.content}</p>
                      
                      {m.citations && m.citations.length > 0 && (
                        <div className="flex gap-1.5 mt-3 flex-wrap">
                          {m.citations.map((cit, cIdx) => (
                            <span 
                              key={cIdx} 
                              className="px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 text-[9px] font-mono border border-indigo-500/30"
                            >
                              [{cit.type.toUpperCase()}] {cit.name}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                ))
              )}
              {loading && (
                <div className="flex justify-start">
                  <div className="bg-[#1f2937]/50 text-[#9CA3AF] p-4 rounded-xl border border-[#1F2937] animate-pulse text-xs max-w-sm flex items-center gap-2">
                    <Cpu className="w-4 h-4 animate-spin text-amber-500" />
                    Solving power flow grids state residuals...
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Suggested prompts toolbar */}
            {messages.length === 0 && (
              <div className="flex flex-col gap-2 shrink-0">
                <span className="text-[10px] text-[#9CA3AF] font-mono uppercase tracking-wider">Suggested Queries</span>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
                  {suggestedPrompts.map((prompt, pIdx) => (
                    <button 
                      key={pIdx}
                      onClick={() => handleSend(prompt)}
                      disabled={isLocked || loading}
                      className="p-3 bg-[#111827] hover:bg-[#1F2937] border border-[#1F2937] hover:border-amber-500/30 rounded-lg text-left text-[10px] text-[#9CA3AF] hover:text-white transition"
                    >
                      {prompt}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Inputs row */}
            <div className="flex gap-3 shrink-0">
              <input 
                type="text" 
                placeholder={isLocked ? "Quota exceeded." : "Ask copilot to write mitigation algorithms..."}
                value={inputVal}
                onChange={(e) => setInputVal(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSend()}
                disabled={isLocked || loading}
                className="flex-1 px-4 py-3 bg-[#111827] border border-[#1F2937] rounded-lg text-xs text-white focus:outline-none focus:ring-1 focus:ring-amber-500 focus:border-amber-500"
              />
              <button 
                onClick={() => handleSend()}
                disabled={isLocked || loading || !inputVal.trim()}
                className="px-5 py-3 bg-amber-500 hover:bg-amber-600 disabled:opacity-50 text-slate-900 font-bold rounded-lg text-xs transition flex items-center justify-center gap-1.5"
              >
                <Send className="w-4 h-4" /> Send
              </button>
              {messages.length > 0 && (
                <button 
                  onClick={handleExport}
                  className="px-3 py-3 border border-[#374151] hover:bg-[#1F2937] text-white rounded-lg text-xs transition"
                  title="Export Chat History"
                >
                  <Download className="w-4 h-4" />
                </button>
              )}
            </div>

          </div>

          {/* Right Sidebar: Citations and Quota meters */}
          <div className="w-80 flex flex-col gap-6 shrink-0">
            
            {/* Citations block */}
            <div className="flex-1 bg-[#111827] border border-[#1F2937] rounded-xl p-5 flex flex-col gap-4">
              <h3 className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-2">
                <BookOpen className="text-indigo-400 w-4 h-4" /> RAG Knowledge Sources
              </h3>
              
              {activeCitations.length > 0 ? (
                <div className="space-y-3 overflow-y-auto flex-1 pr-1">
                  <span className="text-[10px] text-[#9CA3AF] block font-mono">Sources referenced in active answer:</span>
                  {activeCitations.map((cit, idx) => (
                    <div key={idx} className="bg-[#1f2937]/30 border border-[#1F2937] p-3 rounded-lg text-[11px] space-y-1">
                      <span className="px-1.5 py-0.5 rounded bg-indigo-500/15 text-indigo-400 text-[8px] uppercase tracking-wider font-mono font-bold">
                        {cit.type}
                      </span>
                      <strong className="text-white block mt-1">{cit.name}</strong>
                      {cit.mitre && (
                        <span className="text-[9px] text-[#9CA3AF] block font-mono">MITRE Technique: {cit.mitre}</span>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="flex-1 flex flex-col items-center justify-center text-[#9CA3AF] text-center text-[10px]">
                  <HelpCircle className="w-8 h-8 mb-2 opacity-30 text-slate-500" />
                  <span>Click an assistant bubble to view RAG search references.</span>
                </div>
              )}
            </div>

            {/* Quota display */}
            <div className="bg-[#111827] border border-[#1F2937] rounded-xl p-5 space-y-3 shrink-0">
              <h3 className="text-xs font-bold text-white uppercase tracking-wider">Quota Meter</h3>
              <div className="space-y-1">
                <div className="flex justify-between text-[10px] font-mono text-[#9CA3AF]">
                  <span>Monthly Prompts Used</span>
                  <span>{messagesCount} / {tierQuota}</span>
                </div>
                <div className="w-full bg-[#1F2937] h-2 rounded-full overflow-hidden">
                  <div 
                    className="bg-amber-500 h-full transition-all duration-300"
                    style={{ width: `${Math.min(100, (messagesCount / tierQuota) * 100)}%` }}
                  />
                </div>
              </div>
              <span className="text-[9px] text-slate-500 block font-mono">
                Level: <strong className="text-slate-300 capitalize">{planTier}</strong>
              </span>
            </div>

          </div>

        </div>
      ) : (
        
        /* Thesis generator panel */
        <div className="flex-1 bg-[#111827] border border-[#1F2937] rounded-xl p-6 flex flex-col gap-6 overflow-y-auto">
          
          <div className="space-y-2">
            <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
              📝 Thesis & Research Journal Assistant
            </h3>
            <p className="text-xs text-[#9CA3AF]">
              Generate thesis-grade documentation drafts (Abstract, Discussion, and Conclusion) referencing historical simulator metrics.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 items-end bg-[#1f2937]/20 border border-[#1F2937] p-5 rounded-lg">
            
            <div>
              <label className="text-[10px] text-[#9CA3AF] uppercase block mb-1.5 font-mono">Experiment ID</label>
              <input 
                type="text" 
                placeholder="e.g. fd28a7c2-..."
                value={thesisExpId}
                onChange={(e) => setThesisExpId(e.target.value)}
                className="w-full px-3 py-1.5 bg-[#111827] border border-[#374151] rounded text-xs text-white placeholder-slate-600 focus:outline-none"
              />
            </div>

            <div>
              <label className="text-[10px] text-[#9CA3AF] uppercase block mb-1.5 font-mono">Journal Section</label>
              <select 
                value={selectedSection}
                onChange={(e) => setSelectedSection(e.target.value)}
                className="w-full px-3 py-1.5 bg-[#111827] border border-[#374151] rounded text-xs text-white focus:outline-none"
              >
                <option value="abstract">Abstract</option>
                <option value="discussion">Discussion / Methodology</option>
                <option value="conclusion">Conclusion</option>
              </select>
            </div>

            <button 
              onClick={handleGenerateThesis}
              disabled={generatingThesis}
              className="py-1.5 bg-amber-500 hover:bg-amber-600 disabled:opacity-50 text-slate-900 font-bold rounded text-xs transition flex items-center justify-center gap-2"
            >
              {generatingThesis ? (
                <>
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" /> Analyzing
                </>
              ) : (
                <>
                  <Cpu className="w-3.5 h-3.5" /> Generate Draft
                </>
              )}
            </button>

          </div>

          {generatedThesis && (
            <div className="flex-1 flex flex-col gap-3">
              <div className="flex justify-between items-center">
                <span className="text-[10px] text-amber-500 uppercase tracking-wider font-mono font-bold">
                  Generated {selectedSection.toUpperCase()} Draft Text
                </span>
                <button 
                  onClick={() => handleCopyToClipboard(generatedThesis)}
                  className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 border border-[#374151] rounded text-[10px] text-[#9CA3AF] hover:text-white flex items-center gap-1 transition"
                >
                  <Clipboard className="w-3 h-3" /> Copy
                </button>
              </div>

              <div className="flex-1 bg-[#1F2937]/30 border border-[#1F2937] p-5 rounded-lg font-mono text-[11px] leading-relaxed text-slate-300 whitespace-pre-wrap select-text">
                {generatedThesis}
              </div>
            </div>
          )}

        </div>
      )}

    </div>
  );
};
