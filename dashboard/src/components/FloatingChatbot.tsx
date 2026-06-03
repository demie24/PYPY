import React, { useState, useEffect, useRef } from "react";
import {
  Send, Mic, Volume2, MessageSquare, Compass, Minimize2, Sparkles, User
} from "lucide-react";

interface Interaction {
  role: string;
  text: string;
  timestamp?: number;
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

interface AssistantResponse {
  text?: string;
  is_voice?: boolean;
  action?: any;
}

interface SemanticResponse {
  text: string;
  clean_tts_text: string;
  timestamp: number;
}

interface ContextualMemory {
  active_thread_id: string | null;
  active_subject: string | null;
  recent_references: Record<string, any>;
  active_messages: Interaction[];
  thread_count: number;
}

interface Dialogue {
  dialogue_state: string;
  parameter_needed: string;
  clarification_question: string;
  has_pending_phrase: boolean;
}

interface LiveStream {
  is_streaming: boolean;
  status: string;
  full_response_text: string;
  output_buffer: string;
  progress_pct: number;
  elapsed_sec: number;
  interrupted_at_text: string;
  interruption_apology: string;
}

interface FloatingChatbotProps {
  connected: boolean;
  onSendControl: (payload: any) => void;
  assistantState: AssistantState | null;
  assistantEmotion: AssistantEmotion | null;
  assistantContext: AssistantContext | null;
  assistantMemory: AssistantMemory | null;
  assistantResponse: AssistantResponse | null;
  assistantRuntime: any | null;
  assistantSemanticResponse?: { semantic_response: SemanticResponse } | null;
  assistantContextualMemory?: { contextual_memory: ContextualMemory } | null;
  assistantDialogue?: Dialogue | null;
  assistantLiveStream?: LiveStream | null;
  assistantVoiceState?: any | null;
  assistantWakeWord?: any | null;
  assistantVoiceMemory?: any | null;
  assistantPresence?: any | null;
  activeAttack?: boolean;
}

export const FloatingChatbot: React.FC<FloatingChatbotProps> = ({
  connected,
  onSendControl,
  assistantState,
  assistantContext,
  assistantMemory,
  assistantRuntime,
  assistantSemanticResponse,
  assistantContextualMemory,
  activeAttack = false
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [chatText, setChatText] = useState("");
  const [isListeningVoice, setIsListeningVoice] = useState(false);
  const [voiceSimProgress, setVoiceSimProgress] = useState(0);
  const [lastSeenMessageCount, setLastSeenMessageCount] = useState(0);

  const chatEndRef = useRef<HTMLDivElement>(null);

  const state = assistantState?.state ?? "IDLE";
  const context = assistantContext?.context ?? { session_active: false, current_topic: null, interaction_depth: 0 };
  const memory = assistantMemory?.memory ?? { interactions: [], user_preferences: { name: "Operator", language: "ms", tone: "casual" }, command_history: [] };
  const runtime = assistantRuntime ?? { status: "OFFLINE", uptime_sec: 0 };

  const semanticResponse = assistantSemanticResponse?.semantic_response ?? {
    text: "",
    clean_tts_text: "",
    timestamp: 0
  };

  const contextualMemory = assistantContextualMemory?.contextual_memory ?? {
    active_thread_id: null,
    active_subject: null,
    recent_references: {},
    active_messages: [],
    thread_count: 0
  };

  // Determine interactions list
  const displayInteractions = (contextualMemory.active_messages && contextualMemory.active_messages.length > 0)
    ? contextualMemory.active_messages
    : (memory.interactions ?? []);

  // Update last seen count when open, so the unread count goes to 0
  useEffect(() => {
    if (isOpen) {
      setLastSeenMessageCount(displayInteractions.length);
    }
  }, [isOpen, displayInteractions.length]);

  // Auto-scroll to bottom of chat
  useEffect(() => {
    if (isOpen) {
      chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [displayInteractions.length, state, isOpen]);

  const unreadCount = displayInteractions.length - lastSeenMessageCount;

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

  const handleQuickCommand = (phrase: string) => {
    onSendControl({
      topic: "assistant/chat_input",
      payload: { text: phrase }
    });
  };

  // Determine if it should pulse red due to an active attack or error state
  const isAlertState = activeAttack || state === "ERROR";

  return (
    <div className="fixed bottom-6 right-6 z-50 font-mono">
      {/* Minimized Mode Floating Mascot Button */}
      <button
        onClick={() => setIsOpen(true)}
        className={`relative w-16 h-16 rounded-full bg-scada-panel border-2 flex items-center justify-center overflow-hidden transition-all duration-300 transform hover:scale-110 active:scale-95 shadow-[0_0_20px_rgba(0,0,0,0.6)] ${
          isOpen ? "scale-0 opacity-0 pointer-events-none" : "scale-100 opacity-100"
        } ${
          isAlertState
            ? "border-scada-trip animate-pulse shadow-[0_0_15px_rgba(239,68,68,0.6)]"
            : state === "THINKING"
            ? "border-purple-500 shadow-[0_0_15px_rgba(168,85,247,0.5)]"
            : state === "LISTENING"
            ? "border-cyan-400 shadow-[0_0_15px_rgba(34,211,238,0.6)] animate-pulse"
            : connected
            ? "border-cyan-500/50 hover:border-cyan-400 hover:shadow-[0_0_15px_rgba(6,182,212,0.4)]"
            : "border-rose-500/50"
        }`}
        title="S-GRID AI Assistant"
      >
        <img
          src="/avatar.png"
          alt="Dog Mascot"
          className="w-[90%] h-[90%] rounded-full object-cover"
        />

        {/* Online Status Small Pulse Ring */}
        <span className={`absolute bottom-0 right-2 block h-3 w-3 rounded-full border border-scada-panel ${
          connected ? "bg-scada-nominal animate-pulse" : "bg-scada-trip"
        }`} />

        {/* Unread Message Count Badge */}
        {!isOpen && unreadCount > 0 && (
          <span className="absolute -top-1 -right-1 flex h-5 w-5 items-center justify-center rounded-full bg-cyan-500 text-[10px] font-bold text-white shadow-md animate-bounce">
            {unreadCount}
          </span>
        )}
      </button>

      {/* Expanded Mode Chat Panel */}
      <div
        className={`absolute bottom-0 right-0 w-80 md:w-96 h-[500px] rounded-2xl border bg-scada-panel/95 backdrop-blur-md shadow-[0_10px_30px_rgba(0,0,0,0.8)] flex flex-col overflow-hidden transition-all duration-300 transform origin-bottom-right ${
          isOpen ? "scale-100 opacity-100 pointer-events-auto" : "scale-0 opacity-0 pointer-events-none"
        } ${
          isAlertState
            ? "border-scada-trip/40 shadow-[0_0_20px_rgba(239,68,68,0.25)]"
            : "border-scada-border/60 hover:border-cyan-500/30 shadow-[0_0_20px_rgba(6,182,212,0.15)]"
        }`}
      >
        {/* Header */}
        <div className="p-3 border-b border-scada-border/40 bg-scada-bg/85 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-2">
            <div className="relative w-9 h-9 rounded-full overflow-hidden border border-cyan-500/40">
              <img
                src="/avatar.png"
                alt="Dog Mascot"
                className="w-full h-full object-cover"
              />
            </div>
            <div>
              <div className="text-[10px] font-bold uppercase tracking-wider text-cyan-400 flex items-center gap-1">
                <span>RAG AI Mascot</span>
                <Sparkles size={10} className="text-cyan-300 animate-pulse" />
              </div>
              <div className="text-[8px] text-scada-dimText flex items-center gap-1 uppercase">
                <span className={`inline-block w-1.5 h-1.5 rounded-full ${
                  connected ? "bg-scada-nominal animate-pulse" : "bg-scada-trip"
                }`} />
                <span>{connected ? "ONLINE (Active)" : "OFFLINE"}</span>
                {state !== "IDLE" && (
                  <span className="text-cyan-300 font-bold ml-1 animate-pulse">[{state}]</span>
                )}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setIsOpen(false)}
              className="p-1.5 hover:bg-scada-border/40 rounded-lg text-scada-dimText hover:text-white transition-all"
              title="Minimize Assistant"
            >
              <Minimize2 size={12} />
            </button>
          </div>
        </div>

        {/* Info panel */}
        <div className="bg-scada-bg/40 px-3 py-1 border-b border-scada-border/20 text-[7px] text-scada-dimText flex justify-between items-center shrink-0 uppercase tracking-wide">
          <span className="truncate">
            TOPIC: <span className="text-cyan-400 font-semibold">{contextualMemory.active_subject ?? context.current_topic ?? "NONE"}</span>
          </span>
          <span>
            UPTIME: <span className="text-white">{runtime.uptime_sec}s</span>
          </span>
        </div>

        {/* Message Thread */}
        <div className="flex-1 overflow-y-auto p-3 space-y-2.5 scrollbar-thin bg-scada-bg/25">
          {displayInteractions.length === 0 ? (
            <div className="h-full flex flex-col justify-center items-center text-center p-4">
              <Sparkles className="w-8 h-8 text-cyan-400/40 mb-2 animate-pulse" />
              <p className="text-scada-dimText text-[9px] uppercase tracking-wider font-bold">Ready for operator requests</p>
              <p className="text-scada-dimText/60 text-[8px] mt-1 max-w-[200px] leading-relaxed">
                Tanya saya tentang status grid, pasang youtube, atau buka dashboard. Saya boleh respons dalam loghat santai Melayu.
              </p>
            </div>
          ) : (
            displayInteractions.map((msg: Interaction, idx: number) => {
              const isUser = msg.role === "user";
              const isSummary = msg.role === "system_summary" || msg.role === "system";

              if (isSummary) {
                return (
                  <div key={idx} className="flex justify-center my-1">
                    <span className="bg-scada-bg/90 border border-purple-500/20 px-2.5 py-0.5 rounded text-[8px] text-purple-300 italic text-center max-w-[95%]">
                      {msg.text}
                    </span>
                  </div>
                );
              }

              return (
                <div key={idx} className={`flex ${isUser ? "justify-end" : "justify-start"} animate-fadeIn`}>
                  <div className={`max-w-[85%] rounded-xl p-2.5 border flex gap-2 leading-relaxed shadow-sm ${
                    isUser
                      ? "bg-cyan-950/40 border-cyan-500/20 text-cyan-100"
                      : "bg-scada-panel border-scada-border/40 text-emerald-100"
                  }`}>
                    <div className="shrink-0 mt-0.5">
                      {isUser ? <User size={10} className="text-cyan-400" /> : <img src="/avatar.png" alt="mascot" className="w-3.5 h-3.5 rounded-full object-cover" />}
                    </div>
                    <div className="flex flex-col">
                      <div className="text-[7px] text-scada-dimText uppercase tracking-wider mb-0.5 font-bold">
                        {isUser ? "OPERATOR" : "GRID_AI"}
                      </div>
                      <p className="text-[8.5px] break-words whitespace-pre-wrap leading-tight text-white/90">{msg.text}</p>
                    </div>
                  </div>
                </div>
              );
            })
          )}

          {/* Typing Indicator */}
          {state !== "IDLE" && state !== "ERROR" && (
            <div className="flex justify-start">
              <div className="bg-scada-panel border border-scada-border/30 rounded-xl p-2 px-3 flex items-center gap-2">
                <div className="flex gap-0.5 shrink-0">
                  <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-bounce" style={{ animationDelay: "0ms" }}></span>
                  <span className="w-1.5 h-1.5 rounded-full bg-purple-400 animate-bounce" style={{ animationDelay: "150ms" }}></span>
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-bounce" style={{ animationDelay: "300ms" }}></span>
                </div>
                <span className="text-[8px] text-scada-dimText uppercase tracking-wider">
                  {state === "LISTENING" ? "Listening..." :
                   state === "THINKING" ? "Analyzing Intent..." :
                   state === "EXECUTING" ? "Routing Action..." : "Formulating response..."}
                </span>
              </div>
            </div>
          )}
          <div ref={chatEndRef} />
        </div>

        {/* TTS Clean Audio Text */}
        {semanticResponse.clean_tts_text && (
          <div className="bg-black/20 border-t border-scada-border/20 px-3 py-1 shrink-0 text-[7px] text-emerald-400 flex items-center gap-1.5 select-none">
            <Volume2 size={8} className="shrink-0 text-emerald-400 animate-pulse" />
            <span className="truncate">TTS Audio: "{semanticResponse.clean_tts_text}"</span>
          </div>
        )}

        {/* Quick Commands panel */}
        <div className="px-3 py-2 border-t border-scada-border/30 bg-scada-bg/40 shrink-0">
          <div className="text-[7.5px] text-scada-dimText uppercase mb-1 font-bold">Suggested Actions</div>
          <div className="grid grid-cols-2 gap-1.5">
            <button
              onClick={() => handleQuickCommand("check latency")}
              className="bg-scada-panel hover:bg-scada-border/40 border border-scada-border/30 hover:border-cyan-500/20 rounded-md p-1.5 text-left text-[8px] text-scada-dimText truncate flex items-center gap-1 transition-all"
            >
              <MessageSquare size={8} className="text-cyan-400" /> "Check Latency"
            </button>
            <button
              onClick={() => handleQuickCommand("check latency lepas tu kalau tinggi trigger recovery workflow")}
              className="bg-scada-panel hover:bg-scada-border/40 border border-scada-border/30 hover:border-purple-500/20 rounded-md p-1.5 text-left text-[8px] text-scada-dimText truncate flex items-center gap-1 transition-all"
            >
              <Compass size={8} className="text-purple-400" /> "Run Chained Plan"
            </button>
          </div>
        </div>

        {/* Input Footer */}
        <div className="p-3 border-t border-scada-border/40 bg-scada-bg/85 flex gap-2 shrink-0 items-center">
          <button
            onClick={handleSimulateVoice}
            disabled={isListeningVoice || state !== "IDLE"}
            className={`p-2.5 rounded-lg border transition-all flex items-center justify-center shrink-0 ${
              isListeningVoice
                ? "bg-rose-950/70 border-rose-500 text-rose-400 animate-pulse"
                : "bg-cyan-950/70 border-cyan-500/40 hover:bg-cyan-900 text-cyan-400 disabled:opacity-50"
            }`}
            title="Simulate Voice Input"
          >
            {isListeningVoice ? <Volume2 size={12} className="animate-bounce" /> : <Mic size={12} />}
          </button>

          <input
            type="text"
            value={chatText}
            onChange={(e) => setChatText(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSendChat()}
            placeholder={isListeningVoice ? `Listening (${voiceSimProgress}%)...` : "Type request..."}
            disabled={isListeningVoice || state !== "IDLE"}
            className="flex-1 bg-scada-bg border border-scada-border/50 text-white rounded-lg p-2 text-[9px] outline-none placeholder:text-scada-dimText/60 focus:border-cyan-500/50 transition-all"
          />

          <button
            onClick={handleSendChat}
            disabled={!chatText.trim() || state !== "IDLE"}
            className="p-2.5 bg-emerald-950 border border-emerald-500/40 hover:bg-emerald-900 text-emerald-400 rounded-lg disabled:opacity-40 shrink-0 transition-all"
          >
            <Send size={12} />
          </button>
        </div>
      </div>
    </div>
  );
};
