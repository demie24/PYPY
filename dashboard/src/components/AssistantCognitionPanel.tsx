import React, { useState, useEffect, useRef } from "react";
import {
  Send, Mic, Bot, Sparkles, User, Clock, Cpu, Zap,
  AlertCircle, Smile, Volume2, RotateCcw,
  MessageSquare, Compass, Database
} from "lucide-react";

interface Interaction {
  role: string;
  text: string;
}

interface UserPreferences {
  name: string;
  language: string;
  tone: string;
}

interface AssistantMemory {
  memory?: {
    interactions: Interaction[];
    user_preferences: UserPreferences;
    command_history: string[];
  };
}

interface AssistantEmotion {
  emotion?: {
    assistant_mood: string;
    user_mood: string;
    user_mood_confidence?: number;
  };
}

interface AssistantContext {
  context?: {
    session_active: boolean;
    last_interaction_time: number;
    current_topic: string | null;
    assistant_state: string;
    interaction_depth: number;
    previous_action: string | null;
  };
}

interface AssistantState {
  state?: string;
}

interface AssistantIntent {
  intent?: Record<string, string[]>;
}

interface AssistantResponse {
  text?: string;
  is_voice?: boolean;
  action?: any;
}

interface AssistantCognitionPanelProps {
  assistantState: AssistantState | null;
  assistantIntent: AssistantIntent | null;
  assistantEmotion: AssistantEmotion | null;
  assistantActions: any | null;
  assistantContext: AssistantContext | null;
  assistantMemory: AssistantMemory | null;
  assistantResponse: AssistantResponse | null;
  assistantRuntime: any | null;
  connected: boolean;
  onSendControl: (payload: any) => void;
}

export const AssistantCognitionPanel: React.FC<AssistantCognitionPanelProps> = ({
  assistantState,
  assistantIntent,
  assistantEmotion,
  assistantActions,
  assistantContext,
  assistantMemory,
  assistantResponse,
  assistantRuntime,
  connected,
  onSendControl
}) => {
  const [chatText, setChatText] = useState("");
  const [isListeningVoice, setIsListeningVoice] = useState(false);
  const [voiceSimProgress, setVoiceSimProgress] = useState(0);
  const chatEndRef = useRef<HTMLDivElement>(null);

  // Extract variables with defaults
  const state = assistantState?.state ?? "IDLE";
  const emotion = assistantEmotion?.emotion ?? { assistant_mood: "calm", user_mood: "calm" };
  const context = assistantContext?.context ?? { session_active: false, current_topic: null, interaction_depth: 0 };
  const memory = assistantMemory?.memory ?? { interactions: [], user_preferences: { name: "Operator", language: "ms", tone: "casual" }, command_history: [] };
  const actions = assistantActions?.command_history ?? [];
  const lastResponse = assistantResponse;
  const runtime = assistantRuntime ?? { status: "OFFLINE", uptime_sec: 0 };

  // Auto-scroll to bottom of chat
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [memory.interactions, state]);

  // Voice simulation logic
  const handleSimulateVoice = () => {
    if (isListeningVoice) return;
    setIsListeningVoice(true);
    setVoiceSimProgress(0);

    const voicePhrases = [
      "keadaan grid ok ke?",
      "buka youtube jap",
      "siapa diri kau?",
      "buka dashboard hmi",
      "main youtube lagu best sikit",
      "pelayar web mana",
      "pukul berapa sekarang",
      "grid under attack ke"
    ];

    const randomPhrase = voicePhrases[Math.floor(Math.random() * voicePhrases.length)];

    let currentProgress = 0;
    const interval = setInterval(() => {
      currentProgress += 10;
      setVoiceSimProgress(currentProgress);
      if (currentProgress >= 100) {
        clearInterval(interval);
        setIsListeningVoice(false);
        // Send as voice input trigger
        onSendControl({
          topic: "assistant/voice_input",
          payload: { audio_text: randomPhrase }
        });
      }
    }, 150);
  };

  const handleSendChat = () => {
    if (!chatText.trim()) return;
    onSendControl({
      topic: "assistant/chat_input",
      payload: { text: chatText }
    });
    setChatText("");
  };

  const handleResetMemory = () => {
    onSendControl({
      topic: "assistant/reset",
      payload: {}
    });
  };

  const handleQuickCommand = (phrase: string, isVoice: boolean) => {
    if (isVoice) {
      onSendControl({
        topic: "assistant/voice_input",
        payload: { audio_text: phrase }
      });
    } else {
      onSendControl({
        topic: "assistant/chat_input",
        payload: { text: phrase }
      });
    }
  };

  // Helper styles for FSM States
  const getFsmStateStyle = (nodeState: string) => {
    const isActive = state === nodeState;
    if (isActive) {
      switch (nodeState) {
        case "LISTENING": return "bg-cyan-500 text-black border-cyan-300 shadow-[0_0_12px_rgba(6,182,212,0.8)] font-bold scale-105 animate-pulse";
        case "THINKING": return "bg-purple-500 text-white border-purple-300 shadow-[0_0_12px_rgba(168,85,247,0.8)] font-bold scale-105 animate-pulse";
        case "EXECUTING": return "bg-amber-500 text-black border-amber-300 shadow-[0_0_12px_rgba(245,158,11,0.8)] font-bold scale-105 animate-pulse";
        case "RESPONDING": return "bg-emerald-500 text-black border-emerald-300 shadow-[0_0_12px_rgba(16,185,129,0.8)] font-bold scale-105 animate-pulse";
        case "ERROR": return "bg-rose-500 text-white border-rose-300 shadow-[0_0_12px_rgba(244,63,94,0.8)] font-bold scale-105 animate-bounce";
        default: return "bg-blue-600 text-white border-blue-400 shadow-[0_0_10px_rgba(37,99,235,0.7)] font-bold scale-105";
      }
    }
    return "bg-scada-bg/80 border-scada-border/40 text-scada-dimText scale-95 opacity-60";
  };

  const getMoodColor = (mood: string) => {
    switch (mood) {
      case "serious": return "text-rose-400 bg-rose-500/10 border-rose-500/30";
      case "focused": return "text-orange-400 bg-orange-500/10 border-orange-500/30";
      case "happy": return "text-emerald-400 bg-emerald-500/10 border-emerald-500/30";
      case "excited": return "text-yellow-400 bg-yellow-500/10 border-yellow-500/30 animate-pulse";
      case "tired": return "text-purple-400 bg-purple-500/10 border-purple-500/30";
      case "sad": return "text-blue-400 bg-blue-500/10 border-blue-500/30";
      default: return "text-cyan-400 bg-cyan-500/10 border-cyan-500/30";
    }
  };

  const renderFsmNode = (nodeState: string, label: string) => {
    return (
      <div className={`px-2 py-1 rounded border text-[8px] font-mono transition-all duration-300 ${getFsmStateStyle(nodeState)}`}>
        {label}
      </div>
    );
  };

  // Filter out system summary messages or format them differently
  const displayInteractions = memory.interactions ?? [];

  return (
    <div className="bg-scada-panel border border-scada-border rounded-lg p-3 h-[420px] flex flex-col overflow-hidden relative font-mono text-[9px] text-white">
      {/* Dynamic Background Glow representing State */}
      <div className={`absolute inset-0 transition-opacity duration-1000 pointer-events-none opacity-[0.03] ${
        state === "LISTENING" ? "bg-cyan-500" :
        state === "THINKING" ? "bg-purple-500" :
        state === "EXECUTING" ? "bg-amber-500" :
        state === "RESPONDING" ? "bg-emerald-500" :
        state === "ERROR" ? "bg-rose-500 animate-pulse" : "bg-cyan-900"
      }`} />

      {/* Header */}
      <div className="flex justify-between items-center mb-2 border-b border-scada-border/40 pb-1.5 shrink-0 z-10">
        <div className="flex items-center gap-1.5">
          <Bot className="text-cyan-400 w-3.5 h-3.5" />
          <span className="text-[10px] font-bold uppercase tracking-wider text-cyan-100">Intelligent Personal Assistant Core</span>
        </div>
        <div className="flex items-center gap-2">
          {/* Mood Status */}
          <div className={`flex items-center gap-1 px-1.5 py-0.5 rounded border text-[8px] font-bold uppercase tracking-wider ${getMoodColor(emotion.assistant_mood)}`}>
            <Smile size={10} />
            <span>MOOD: {emotion.assistant_mood}</span>
          </div>
          {/* State Indicator */}
          <div className="flex items-center gap-1 bg-scada-bg/85 px-1.5 py-0.5 rounded border border-scada-border/30">
            <span className="text-scada-dimText">STATE:</span>
            <span className={`font-bold uppercase tracking-wider animate-pulse ${
              state === "ERROR" ? "text-rose-400" :
              state === "IDLE" ? "text-scada-dimText" :
              state === "THINKING" ? "text-purple-400" :
              state === "LISTENING" ? "text-cyan-400" : "text-emerald-400"
            }`}>
              {state}
            </span>
          </div>
          {/* Uptime Indicator */}
          <div className="flex items-center gap-1 bg-scada-bg/85 px-1.5 py-0.5 rounded border border-scada-border/30">
            <span className="text-scada-dimText">UPTIME:</span>
            <span className={`font-bold ${runtime.status === "ONLINE" ? "text-emerald-400" : "text-rose-400"}`}>
              {runtime.uptime_sec}s
            </span>
          </div>
          {/* Connection status badge */}
          <div className="flex items-center gap-1 bg-scada-bg/85 px-1.5 py-0.5 rounded border border-scada-border/30">
            <span className="text-scada-dimText">LINK:</span>
            <span className={`font-bold ${connected ? "text-emerald-400" : "text-rose-500 animate-pulse"}`}>
              {connected ? "ONLINE" : "OFFLINE"}
            </span>
          </div>
          <button onClick={handleResetMemory} className="p-1 hover:bg-scada-border/40 rounded text-scada-dimText hover:text-white transition-colors" title="Reset Session">
            <RotateCcw size={10} />
          </button>
        </div>
      </div>

      {/* Main content grid split 55% / 45% */}
      <div className="flex-1 flex gap-3 overflow-hidden z-10 min-h-0">
        {/* Left Side: Conversational Console (Chat) */}
        <div className="w-[55%] flex flex-col overflow-hidden bg-scada-bg/50 border border-scada-border/30 rounded p-2">
          {/* Topic & Depth Banner */}
          <div className="flex justify-between items-center mb-1 border-b border-scada-border/20 pb-1.5 shrink-0 text-[8px] text-scada-dimText uppercase tracking-wider font-semibold">
            <span className="flex items-center gap-1">
              <Compass size={9} /> Topic: <span className="text-cyan-300 font-bold">{context.current_topic ?? "NONE"}</span>
            </span>
            <span>Depth: <span className="text-white font-bold">{context.interaction_depth}</span></span>
          </div>

          {/* Dialog Container */}
          <div className="flex-1 overflow-y-auto space-y-2 pr-1 mb-2 scrollbar-thin bg-black/10 rounded p-1.5">
            {displayInteractions.length === 0 ? (
              <div className="h-full flex flex-col justify-center items-center text-center p-4">
                <Sparkles className="w-6 h-6 text-cyan-400/40 mb-1 animate-pulse" />
                <p className="text-scada-dimText text-[8px] uppercase tracking-wide">Ready for operator requests</p>
                <p className="text-scada-dimText/60 text-[7.5px] mt-1 max-w-[200px]">
                  Tanya saya tentang status grid, pasang youtube, atau buka dashboard. Saya boleh respons dalam loghat santai Melayu.
                </p>
              </div>
            ) : (
              displayInteractions.map((msg: Interaction, idx: number) => {
                const isUser = msg.role === "user";
                const isSummary = msg.role === "system_summary";

                if (isSummary) {
                  return (
                    <div key={idx} className="flex justify-center my-1.5">
                      <span className="bg-scada-bg/80 border border-scada-border/20 px-2 py-0.5 rounded text-[7px] text-scada-dimText italic">
                        {msg.text}
                      </span>
                    </div>
                  );
                }

                return (
                  <div key={idx} className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
                    <div className={`max-w-[85%] rounded p-2 border flex gap-1.5 leading-relaxed ${
                      isUser
                        ? "bg-cyan-950/40 border-cyan-500/20 text-cyan-100"
                        : "bg-scada-bg/85 border-scada-border/40 text-emerald-100"
                    }`}>
                      <div className="shrink-0 mt-0.5">
                        {isUser ? (
                          <User size={10} className="text-cyan-400" />
                        ) : (
                          <Bot size={10} className="text-emerald-400" />
                        )}
                      </div>
                      <div className="flex flex-col">
                        <div className="text-[7px] text-scada-dimText uppercase tracking-wider mb-0.5">
                          {isUser ? "OPERATOR" : "GRID_AI"}
                        </div>
                        <p className="text-[8.5px] break-words whitespace-pre-wrap leading-tight">{msg.text}</p>
                      </div>
                    </div>
                  </div>
                );
              })
            )}

            {/* Listening / Thinking animation overlay */}
            {state !== "IDLE" && state !== "ERROR" && (
              <div className="flex justify-start">
                <div className="bg-scada-bg border border-scada-border/20 rounded p-1.5 px-2.5 flex items-center gap-1.5">
                  <div className="flex gap-0.5 shrink-0">
                    <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-bounce" style={{ animationDelay: "0ms" }}></span>
                    <span className="w-1.5 h-1.5 rounded-full bg-purple-400 animate-bounce" style={{ animationDelay: "150ms" }}></span>
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-bounce" style={{ animationDelay: "300ms" }}></span>
                  </div>
                  <span className="text-[7.5px] text-scada-dimText uppercase tracking-wider">
                    {state === "LISTENING" ? "Listening..." :
                     state === "THINKING" ? "Analyzing Intent..." :
                     state === "EXECUTING" ? "Routing Action..." : "Formulating response..."}
                  </span>
                </div>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          {/* Quick Prompts Input Section */}
          <div className="grid grid-cols-2 gap-1 mb-1.5 shrink-0">
            <button onClick={() => handleQuickCommand("keadaan grid ok ke?", true)}
              className="bg-scada-bg hover:bg-scada-border/20 border border-scada-border/30 rounded p-1 text-left text-[7.5px] text-scada-dimText truncate flex items-center gap-1">
              <Mic size={8} className="text-cyan-400" /> "Grid ok ke?"
            </button>
            <button onClick={() => handleQuickCommand("buka youtube jap", false)}
              className="bg-scada-bg hover:bg-scada-border/20 border border-scada-border/30 rounded p-1 text-left text-[7.5px] text-scada-dimText truncate flex items-center gap-1">
              <MessageSquare size={8} className="text-purple-400" /> "Buka YouTube"
            </button>
          </div>

          {/* Input Controls */}
          <div className="flex gap-1.5 shrink-0 items-center">
            {/* STT/Voice Activation Button */}
            <button
              onClick={handleSimulateVoice}
              disabled={isListeningVoice || state !== "IDLE"}
              className={`p-2 rounded border transition-all flex items-center justify-center shrink-0 ${
                isListeningVoice
                  ? "bg-rose-950/70 border-rose-500 text-rose-400 animate-pulse"
                  : "bg-cyan-950/70 border-cyan-500/40 hover:bg-cyan-900 text-cyan-400 disabled:opacity-50"
              }`}
              title="Simulate Voice Input"
            >
              {isListeningVoice ? <Volume2 size={12} className="animate-bounce" /> : <Mic size={12} />}
            </button>

            {/* Chat text box */}
            <input
              type="text"
              value={chatText}
              onChange={(e) => setChatText(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSendChat()}
              placeholder={isListeningVoice ? `Listening to audio text (${voiceSimProgress}%)...` : "Type a request to assistant..."}
              disabled={isListeningVoice || state !== "IDLE"}
              className="flex-1 bg-scada-bg border border-scada-border/50 text-white rounded p-1.5 text-[8.5px] outline-none placeholder:text-scada-dimText/60"
            />

            {/* Send Button */}
            <button
              onClick={handleSendChat}
              disabled={!chatText.trim() || state !== "IDLE"}
              className="p-2 bg-emerald-950 border border-emerald-500/40 hover:bg-emerald-900 text-emerald-400 rounded disabled:opacity-40 shrink-0 transition-colors"
            >
              <Send size={12} />
            </button>
          </div>
        </div>

        {/* Right Side: Cognition Monitoring */}
        <div className="w-[45%] flex flex-col justify-between overflow-hidden">
          {/* FSM Loop Display */}
          <div className="bg-scada-bg/40 border border-scada-border/30 rounded p-2 shrink-0">
            <div className="text-[8px] font-bold text-scada-dimText uppercase tracking-wider mb-1.5 flex items-center gap-1">
              <Cpu size={10} className="text-purple-400" />
              <span>Cognitive State Machine</span>
            </div>
            <div className="flex flex-wrap gap-1 items-center justify-center py-1 border border-scada-border/10 rounded bg-black/10">
              {renderFsmNode("IDLE", "IDLE")}
              <span className="text-scada-dimText font-mono">→</span>
              {renderFsmNode("LISTENING", "LISTEN")}
              <span className="text-scada-dimText font-mono">→</span>
              {renderFsmNode("THINKING", "THINK")}
              <span className="text-scada-dimText font-mono">→</span>
              {renderFsmNode("EXECUTING", "EXEC")}
              <span className="text-scada-dimText font-mono">→</span>
              {renderFsmNode("RESPONDING", "RESP")}
            </div>
          </div>

          {/* Action Dispatches & SCADA controls */}
          <div className="bg-scada-bg/40 border border-scada-border/30 rounded p-2 flex-1 my-2 overflow-hidden flex flex-col">
            <div className="text-[8px] font-bold text-scada-dimText uppercase tracking-wider border-b border-scada-border/20 pb-1 shrink-0 flex items-center justify-between">
              <span className="flex items-center gap-1">
                <Zap size={10} className="text-yellow-400" />
                <span>Action Dispatcher Output</span>
              </span>
              <span className="text-[7px] text-scada-dimText uppercase">n8n Gateway</span>
            </div>

            <div className="flex-1 overflow-y-auto space-y-1.5 pt-1.5 scrollbar-thin">
              {lastResponse?.action && (
                <div className={`p-1.5 border rounded leading-normal ${
                  lastResponse.action.status === "SUCCESS" ? "bg-emerald-950/20 border-emerald-500/20 text-emerald-300" : "bg-purple-950/20 border-purple-500/30 text-purple-300"
                }`}>
                  <div className="flex justify-between items-center font-bold">
                    <span>ACTION: {lastResponse.action.action}</span>
                    <span className="text-[7px] bg-black/35 px-1 py-0.5 rounded border border-scada-border/20">{lastResponse.action.status}</span>
                  </div>
                  <div className="text-[7.5px] mt-1 text-white/80 font-mono space-y-0.5">
                    {lastResponse.action.payload && Object.entries(lastResponse.action.payload).map(([k, v]: any) => (
                      <div key={k} className="flex justify-between">
                        <span className="text-scada-dimText capitalize">{k.replace(/_/g, " ")}:</span>
                        <span className="truncate max-w-[120px]">{typeof v === "object" ? JSON.stringify(v) : String(v)}</span>
                      </div>
                    ))}
                    <div className="text-[6.5px] text-scada-dimText mt-1 flex justify-between">
                      <span>TIME: {new Date(lastResponse.action.timestamp).toLocaleTimeString()}</span>
                    </div>
                  </div>
                </div>
              )}

              {/* Memory Logs & Preference Stack */}
              <div className="p-1.5 border border-scada-border/20 rounded bg-scada-bg/25">
                <div className="text-[7.5px] font-bold text-scada-dimText uppercase tracking-wider mb-1 flex items-center gap-1">
                  <Database size={8} className="text-cyan-400" />
                  <span>Operator Profile Cache</span>
                </div>
                <div className="grid grid-cols-3 gap-1 text-[7px] font-mono leading-tight">
                  <div className="bg-black/15 p-1 rounded border border-scada-border/10">
                    <div className="text-scada-dimText">Name</div>
                    <div className="text-white font-bold truncate">{memory.user_preferences?.name ?? "Operator"}</div>
                  </div>
                  <div className="bg-black/15 p-1 rounded border border-scada-border/10">
                    <div className="text-scada-dimText">Lang</div>
                    <div className="text-white font-bold truncate">{memory.user_preferences?.language ?? "ms"}</div>
                  </div>
                  <div className="bg-black/15 p-1 rounded border border-scada-border/10">
                    <div className="text-scada-dimText">Tone</div>
                    <div className="text-white font-bold truncate">{memory.user_preferences?.tone ?? "casual"}</div>
                  </div>
                </div>
              </div>

              {/* Action Log History */}
              <div className="p-1.5 border border-scada-border/20 rounded bg-scada-bg/25 text-[7px] leading-tight">
                <div className="text-scada-dimText uppercase mb-1 font-bold flex items-center gap-1">
                  <Clock size={7} /> Commmand Logs
                </div>
                {actions.length === 0 ? (
                  <div className="text-scada-dimText/60 italic text-[6.5px]">No commands executed in this session</div>
                ) : (
                  <div className="flex flex-wrap gap-1 max-h-[35px] overflow-y-auto pr-0.5">
                    {actions.map((act: string, idx: number) => (
                      <span key={idx} className="bg-cyan-950/50 border border-cyan-800/30 px-1 py-0.5 rounded text-[6.5px] text-cyan-300">
                        {act}
                      </span>
                    ))}
                  </div>
                )}
              </div>

              {/* Supported Commands Info */}
              {assistantIntent?.intent && (
                <div className="p-1.5 border border-scada-border/20 rounded bg-scada-bg/25 text-[7px] leading-tight mt-1.5">
                  <div className="text-scada-dimText uppercase mb-1 font-bold flex items-center gap-1">
                    <Compass size={7} /> Supported Commands
                  </div>
                  <div className="grid grid-cols-2 gap-1 text-[6.5px]">
                    {Object.keys(assistantIntent.intent).map((key: string) => (
                      <div key={key} className="truncate text-cyan-300">
                        • {key.replace(/_/g, " ")}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Grid Stress Indicator Empathy Sync */}
          <div className="bg-scada-bg/60 border border-scada-border/30 rounded p-2 shrink-0">
            <div className="flex justify-between items-center text-[7.5px]">
              <span className="text-scada-dimText uppercase tracking-wider flex items-center gap-1">
                <AlertCircle size={10} className="text-rose-400" />
                <span>Grid Stress Empathy Overrides</span>
              </span>
              <span className={`font-bold ${emotion.assistant_mood === "serious" ? "text-rose-400 animate-pulse" : "text-emerald-400"}`}>
                {emotion.assistant_mood === "serious" ? "LOCK ENGAGED" : "NOMINAL"}
              </span>
            </div>
            <p className="text-[7px] text-scada-dimText/80 mt-1 leading-tight">
              Jika threat score grid melebihi 70.0, Assistant mood di-lock ke <span className="text-white font-bold">serious/focused</span> untuk menghalang arahan hiburan.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
