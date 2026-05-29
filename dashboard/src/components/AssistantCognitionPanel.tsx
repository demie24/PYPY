import React, { useState, useEffect, useRef } from "react";
import {
  Send, Mic, Bot, Sparkles, User, Cpu, Smile, Volume2, RotateCcw,
  MessageSquare, Compass, GitBranch,
  ShieldCheck, Terminal, Sliders, Activity, AlertCircle, Play, Zap, Clock, WifiOff
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

interface AssistantIntent {
  intent?: Record<string, string[]>;
}

interface AssistantResponse {
  text?: string;
  is_voice?: boolean;
  action?: any;
}

interface SemanticIntent {
  category: string;
  action: string | null;
  confidence: number;
  parameters: Record<string, any>;
  is_fuzzy: boolean;
  is_followup: boolean;
}

interface ContextualMemory {
  active_thread_id: string | null;
  active_subject: string | null;
  recent_references: Record<string, any>;
  active_messages: Interaction[];
  thread_count: number;
}

interface Reasoning {
  should_execute: boolean;
  should_respond: boolean;
  resolved_action: string | null;
  parameters: Record<string, any>;
  webhook_trigger: string | null;
  followup_recommendation: string | null;
  reasoning_logs: string[];
  grid_critical: boolean;
}

interface AutomationHooks {
  trigger_count: number;
  latest_hook_status: Record<string, any>;
  supported_hooks: string[];
}

interface SemanticResponse {
  text: string;
  clean_tts_text: string;
  timestamp: number;
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
  assistantSemanticIntent?: { semantic_intent: SemanticIntent } | null;
  assistantContextualMemory?: { contextual_memory: ContextualMemory } | null;
  assistantReasoning?: { reasoning: Reasoning } | null;
  assistantAutomationHooks?: { automation_hooks: AutomationHooks } | null;
  assistantSemanticResponse?: { semantic_response: SemanticResponse } | null;
  connected: boolean;
  onSendControl: (payload: any) => void;
  // Phase 9.3 new props
  assistantVoiceState?: any | null;
  assistantWakeWord?: any | null;
  assistantProactive?: any | null;
  assistantVoiceMemory?: any | null;
  assistantPresence?: any | null;
}

export const AssistantCognitionPanel: React.FC<AssistantCognitionPanelProps> = ({
  assistantState,
  assistantEmotion,
  assistantContext,
  assistantMemory,
  assistantRuntime,
  assistantSemanticIntent,
  assistantContextualMemory,
  assistantReasoning,
  assistantAutomationHooks,
  assistantSemanticResponse,
  connected,
  onSendControl,
  assistantVoiceState,
  assistantWakeWord,
  assistantProactive,
  assistantVoiceMemory,
  assistantPresence
}) => {
  const [chatText, setChatText] = useState("");
  const [isListeningVoice, setIsListeningVoice] = useState(false);
  const [voiceSimProgress, setVoiceSimProgress] = useState(0);
  const [activeTab, setActiveTab] = useState<"reasoning" | "voice_wake" | "presence_pacing" | "proactive_hooks">("reasoning");
  const chatEndRef = useRef<HTMLDivElement>(null);

  // Extract variables with defaults
  const state = assistantState?.state ?? "IDLE";
  const emotion = assistantEmotion?.emotion ?? { assistant_mood: "calm", user_mood: "calm" };
  const context = assistantContext?.context ?? { session_active: false, current_topic: null, interaction_depth: 0 };
  const memory = assistantMemory?.memory ?? { interactions: [], user_preferences: { name: "Operator", language: "ms", tone: "casual" }, command_history: [] };
  const runtime = assistantRuntime ?? { status: "OFFLINE", uptime_sec: 0 };

  // Semantic parameters:
  const semanticIntent = assistantSemanticIntent?.semantic_intent ?? {
    category: "UNKNOWN",
    action: null,
    confidence: 0.0,
    parameters: {},
    is_fuzzy: false,
    is_followup: false
  };
  const contextualMemory = assistantContextualMemory?.contextual_memory ?? {
    active_thread_id: null,
    active_subject: null,
    recent_references: {},
    active_messages: [],
    thread_count: 0
  };
  const reasoning = assistantReasoning?.reasoning ?? {
    should_execute: false,
    should_respond: false,
    resolved_action: null,
    parameters: {},
    webhook_trigger: null,
    followup_recommendation: null,
    reasoning_logs: ["Reasoning engine stand-by."],
    grid_critical: false
  };
  const automationHooks = assistantAutomationHooks?.automation_hooks ?? {
    trigger_count: 0,
    latest_hook_status: {},
    supported_hooks: []
  };
  const semanticResponse = assistantSemanticResponse?.semantic_response ?? {
    text: "",
    clean_tts_text: "",
    timestamp: 0
  };

  // Phase 9.3 Parameters:
  const voiceState = assistantVoiceState?.voice_state ?? {
    voice_state: "IDLE",
    session_active: false,
    session_id: null,
    time_remaining: 0.0,
    total_sessions: 0,
    state_duration: 0.0
  };
  const wakeWord = assistantWakeWord?.wake_word ?? {
    attention_active: false,
    time_remaining: 0.0,
    last_wake_word: null,
    last_confidence: 0.0
  };
  const proactive = assistantProactive?.proactive ?? {
    total_notifications_sent: 0,
    cooldown_timers: {
      broker_disconnect: 0.0,
      relay_unstable: 0.0,
      sync_recovered: 0.0,
      latency_spike: 0.0
    },
    latest_notification: null,
    history: []
  };
  const voiceMemory = assistantVoiceMemory?.voice_memory ?? {
    active_session_id: null,
    session_messages: [],
    session_commands: [],
    created_at: 0.0,
    latest_command: null,
    latest_voice_text: null,
    total_cached_sessions: 0
  };
  const presence = assistantPresence?.presence ?? {
    attention_state: "ATTENTIVE",
    breathing_coordinate: 0.0,
    breathing_frequency_hz: 1.0,
    idle_duration_sec: 0.0
  };

  // SVG Breathing core coordinate calculation
  const [localBreathingCoordinate, setLocalBreathingCoordinate] = useState(0);

  useEffect(() => {
    let animFrameId: number;
    let lastTime = performance.now();
    let phase = 0;

    const animate = (time: number) => {
      const dt = (time - lastTime) / 1000;
      lastTime = time;

      const freq = presence.breathing_frequency_hz ?? 1.0;
      phase += 2 * Math.PI * freq * dt;
      if (phase > 2 * Math.PI) {
        phase -= 2 * Math.PI;
      }

      let coord = 0;
      if (state === "ERROR") {
        coord = 0.7 * Math.sin(phase) + 0.3 * Math.sin(phase * 5.0);
      } else {
        coord = Math.sin(phase);
      }

      setLocalBreathingCoordinate(coord);
      animFrameId = requestAnimationFrame(animate);
    };

    animFrameId = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(animFrameId);
  }, [state, presence.breathing_frequency_hz]);

  // Determine interactions list (use contextual active messages first for thread summary, fallback to old list)
  const displayInteractions = (contextualMemory.active_messages && contextualMemory.active_messages.length > 0)
    ? contextualMemory.active_messages
    : (memory.interactions ?? []);

  // Auto-scroll to bottom of chat
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [displayInteractions.length, state]);

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

  // Simulated alerts helpers
  const triggerWakeWordSim = () => {
    onSendControl({
      topic: "assistant/wake_word_trigger",
      payload: { text: "hey pypy" }
    });
  };

  const triggerLatencySpikeSim = () => {
    onSendControl({
      topic: "assistant/proactive_trigger",
      payload: { latency_ms: 620.0, latency_spike: true }
    });
  };

  const triggerRelayInstabilitySim = () => {
    onSendControl({
      topic: "assistant/proactive_trigger",
      payload: { relay_unstable: true }
    });
  };

  const triggerBrokerDisconnectSim = () => {
    onSendControl({
      topic: "assistant/proactive_trigger",
      payload: { comms_online: false }
    });
  };

  const triggerSyncRecoverySim = () => {
    onSendControl({
      topic: "assistant/proactive_trigger",
      payload: { sync_recovered: true }
    });
  };

  // Helper for Pacing delay calculation description
  const getPacingDelayValue = (mood: string, critical: boolean) => {
    if (critical) return 0.0;
    if (mood === "excited") return 0.15;
    if (mood === "tired") return 1.10;
    if (mood === "serious" || mood === "focused") return 0.30;
    return 0.50;
  };

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

      {/* Main content grid split 50% / 50% */}
      <div className="flex-1 flex gap-3 overflow-hidden z-10 min-h-0">
        {/* Left Side: Conversational Console (Chat) */}
        <div className="w-[50%] flex flex-col overflow-hidden bg-scada-bg/50 border border-scada-border/30 rounded p-2">
          {/* Topic & Depth Banner */}
          <div className="flex justify-between items-center mb-1 border-b border-scada-border/20 pb-1.5 shrink-0 text-[8px] text-scada-dimText uppercase tracking-wider font-semibold">
            <span className="flex items-center gap-1">
              <Compass size={9} /> Topic: <span className="text-cyan-300 font-bold">{contextualMemory.active_subject ?? context.current_topic ?? "NONE"}</span>
            </span>
            <span>Thread: <span className="text-white font-bold">{contextualMemory.active_thread_id ? `T-${contextualMemory.active_thread_id.substring(0, 4)}` : "NONE"}</span></span>
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
                const isSummary = msg.role === "system_summary" || msg.role === "system";

                if (isSummary) {
                  return (
                    <div key={idx} className="flex justify-center my-1.5">
                      <span className="bg-scada-bg/85 border border-purple-500/20 px-2 py-0.5 rounded text-[7px] text-purple-300 italic text-center max-w-[95%]">
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

          {/* Voice status info */}
          {semanticResponse.clean_tts_text && (
            <div className="bg-black/10 border border-scada-border/20 rounded p-1 mb-1 shrink-0 text-[6.5px] text-emerald-400 flex items-center gap-1 select-none">
              <Volume2 size={8} className="shrink-0 text-emerald-400 animate-pulse" />
              <span className="truncate">TTS Text: {semanticResponse.clean_tts_text}</span>
            </div>
          )}

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

        {/* Right Side: Cognition Monitoring & Semantic Visualizations */}
        <div className="w-[50%] flex flex-col overflow-hidden">
          {/* Tab Selector */}
          <div className="flex border-b border-scada-border/30 mb-2 bg-scada-bg/30 rounded-t overflow-hidden shrink-0">
            <button
              onClick={() => setActiveTab("reasoning")}
              className={`flex-1 py-1.5 text-[7.5px] uppercase tracking-wider font-bold text-center border-b-2 transition-all flex items-center justify-center gap-1 ${
                activeTab === "reasoning"
                  ? "border-purple-500 text-white bg-purple-500/10"
                  : "border-transparent text-scada-dimText hover:text-white hover:bg-scada-border/10"
              }`}
            >
              <Activity size={10} />
              Reasoning
            </button>
            <button
              onClick={() => setActiveTab("voice_wake")}
              className={`flex-1 py-1.5 text-[7.5px] uppercase tracking-wider font-bold text-center border-b-2 transition-all flex items-center justify-center gap-1 ${
                activeTab === "voice_wake"
                  ? "border-cyan-500 text-white bg-cyan-500/10"
                  : "border-transparent text-scada-dimText hover:text-white hover:bg-scada-border/10"
              }`}
            >
              <Volume2 size={10} />
              Voice & Wake
            </button>
            <button
              onClick={() => setActiveTab("presence_pacing")}
              className={`flex-1 py-1.5 text-[7.5px] uppercase tracking-wider font-bold text-center border-b-2 transition-all flex items-center justify-center gap-1 ${
                activeTab === "presence_pacing"
                  ? "border-emerald-500 text-white bg-emerald-500/10"
                  : "border-transparent text-scada-dimText hover:text-white hover:bg-scada-border/10"
              }`}
            >
              <Clock size={10} />
              Presence
            </button>
            <button
              onClick={() => setActiveTab("proactive_hooks")}
              className={`flex-1 py-1.5 text-[7.5px] uppercase tracking-wider font-bold text-center border-b-2 transition-all flex items-center justify-center gap-1 ${
                activeTab === "proactive_hooks"
                  ? "border-amber-500 text-white bg-amber-500/10"
                  : "border-transparent text-scada-dimText hover:text-white hover:bg-scada-border/10"
              }`}
            >
              <Zap size={10} />
              Proactive
            </button>
          </div>

          {/* Tab Content Panels */}
          <div className="flex-1 overflow-hidden flex flex-col">
            {/* 1. REASONING */}
            {activeTab === "reasoning" && (
              <div className="flex-1 flex flex-col overflow-hidden justify-between">
                {/* Cognitive FSM Row */}
                <div className="bg-scada-bg/40 border border-scada-border/30 rounded p-1.5 mb-1.5 shrink-0">
                  <div className="text-[7.5px] font-bold text-scada-dimText uppercase tracking-wider mb-1 flex items-center gap-1">
                    <Cpu size={9} className="text-purple-400" />
                    <span>Cognitive State Machine</span>
                  </div>
                  <div className="flex gap-0.5 items-center justify-between py-1 px-1 border border-scada-border/15 rounded bg-black/15">
                    {renderFsmNode("IDLE", "IDLE")}
                    <span className="text-scada-dimText text-[6px]">→</span>
                    {renderFsmNode("LISTENING", "LISTEN")}
                    <span className="text-scada-dimText text-[6px]">→</span>
                    {renderFsmNode("THINKING", "THINK")}
                    <span className="text-scada-dimText text-[6px]">→</span>
                    {renderFsmNode("EXECUTING", "EXEC")}
                    <span className="text-scada-dimText text-[6px]">→</span>
                    {renderFsmNode("RESPONDING", "RESP")}
                  </div>
                </div>

                {/* Reasoning Logs Console */}
                <div className="flex-1 bg-scada-bg/70 border border-scada-border/30 rounded p-2 flex flex-col overflow-hidden mb-1.5">
                  <div className="text-[7.5px] font-bold text-scada-dimText uppercase tracking-wider mb-1 flex items-center gap-1 border-b border-scada-border/20 pb-0.5 shrink-0">
                    <Terminal size={9} className="text-purple-400" />
                    <span>5-Step Decision Reasoning Log</span>
                  </div>
                  <div className="flex-1 overflow-y-auto space-y-1.5 scrollbar-thin text-[7px] font-mono leading-normal pt-1">
                    {reasoning.reasoning_logs.map((log: string, index: number) => {
                      let color = "text-white/80";
                      if (log.includes("SAFETY OVERRIDE")) color = "text-rose-400 font-bold bg-rose-950/20 border-l border-rose-500 pl-1";
                      else if (log.includes("Automation planning")) color = "text-amber-400";
                      else if (log.includes("Critical=True")) color = "text-rose-400";
                      else if (log.includes("resolving") || log.includes("resolved")) color = "text-emerald-400";
                      return (
                        <div key={index} className={color}>
                          &gt; {log}
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Grid stress sync */}
                <div className="bg-scada-bg/60 border border-scada-border/30 rounded p-1.5 shrink-0">
                  <div className="flex justify-between items-center text-[7.5px]">
                    <span className="text-scada-dimText uppercase tracking-wider flex items-center gap-1 font-bold">
                      <AlertCircle size={9} className="text-rose-400 animate-pulse" />
                      <span>Stress Empathy Override</span>
                    </span>
                    <span className={`font-bold px-1 rounded text-[6.5px] ${reasoning.grid_critical ? "text-rose-400 bg-rose-950/50 border border-rose-500/30 animate-pulse" : "text-emerald-400 bg-emerald-950/40 border border-emerald-500/20"}`}>
                      {reasoning.grid_critical ? "LOCKOUT ACTIVE" : "NOMINAL"}
                    </span>
                  </div>
                  <p className="text-[6.5px] text-scada-dimText/80 mt-1 leading-tight">
                    Lockout redirects entertainment commands to status queries when threat &gt; 70.0%. Current state: {reasoning.grid_critical ? "LOCK ENGAGED" : "NOMINAL"}.
                  </p>
                </div>
              </div>
            )}

            {/* 2. VOICE & WAKE WORD */}
            {activeTab === "voice_wake" && (
              <div className="flex-1 flex flex-col overflow-hidden justify-between">
                {/* Wake Word Status */}
                <div className="bg-scada-bg/70 border border-scada-border/30 rounded p-2 mb-1.5 shrink-0">
                  <div className="text-[7.5px] font-bold text-scada-dimText uppercase tracking-wider mb-2 border-b border-scada-border/20 pb-0.5 flex justify-between items-center">
                    <span className="flex items-center gap-1">
                      <Mic size={9} className="text-cyan-400" />
                      <span>Wake-Word Attention Guard</span>
                    </span>
                    <span className={`px-1.5 py-0.2 rounded text-[6.5px] font-bold font-mono border ${
                      wakeWord.attention_active 
                        ? "bg-emerald-950/80 border-emerald-500 text-emerald-400 animate-pulse" 
                        : "bg-scada-bg border-scada-border text-scada-dimText"
                    }`}>
                      {wakeWord.attention_active ? "ATTENTION ACTIVE" : "STANDBY"}
                    </span>
                  </div>

                  <div className="grid grid-cols-2 gap-2 text-[7.5px]">
                    <div className="bg-black/20 p-1.5 rounded border border-scada-border/10 flex flex-col justify-between">
                      <span className="text-scada-dimText">Target Wake word:</span>
                      <span className="text-white font-bold">"baby" / "hey pypy"</span>
                    </div>
                    <div className="bg-black/20 p-1.5 rounded border border-scada-border/10 flex flex-col justify-between">
                      <span className="text-scada-dimText">Attention Window:</span>
                      <span className={`font-bold ${wakeWord.attention_active ? "text-cyan-400" : "text-scada-dimText"}`}>
                        {wakeWord.time_remaining}s remaining
                      </span>
                    </div>
                    <div className="bg-black/20 p-1.5 rounded border border-scada-border/10 flex flex-col justify-between">
                      <span className="text-scada-dimText">Matched Word:</span>
                      <span className="text-emerald-400 font-bold">"{wakeWord.last_wake_word ?? "NONE"}"</span>
                    </div>
                    <div className="bg-black/20 p-1.5 rounded border border-scada-border/10 flex flex-col justify-between">
                      <span className="text-scada-dimText">Matching Conf:</span>
                      <span className="text-cyan-400 font-bold">{(wakeWord.last_confidence * 100).toFixed(0)}%</span>
                    </div>
                  </div>
                </div>

                {/* Session Stage Timeline */}
                <div className="bg-scada-bg/70 border border-scada-border/30 rounded p-2 mb-1.5 flex-1 flex flex-col overflow-hidden">
                  <div className="text-[7.5px] font-bold text-scada-dimText uppercase tracking-wider mb-2 border-b border-scada-border/20 pb-0.5 flex justify-between items-center shrink-0">
                    <span className="flex items-center gap-1">
                      <GitBranch size={9} className="text-purple-400" />
                      <span>Voice Session Stage Timeline</span>
                    </span>
                    <span className="text-[6.5px] text-scada-dimText">
                      ID: {voiceState.session_id ? `S-${voiceState.session_id.substring(0, 5)}` : "NONE"}
                    </span>
                  </div>

                  {/* Horizontal visual timeline */}
                  <div className="flex items-center justify-between py-2 px-1 border border-scada-border/15 rounded bg-black/15 my-1.5 shrink-0 select-none">
                    <div className={`px-1.5 py-0.5 rounded text-[6.5px] font-bold font-mono transition-all border ${voiceState.voice_state === "WAKING" ? "bg-cyan-500 text-black border-cyan-300 scale-105" : "bg-scada-bg/60 text-scada-dimText/60 border-scada-border/10"}`}>WAKING</div>
                    <span className="text-scada-dimText text-[8px]">&gt;</span>
                    <div className={`px-1.5 py-0.5 rounded text-[6.5px] font-bold font-mono transition-all border ${voiceState.voice_state === "LISTENING" ? "bg-cyan-500 text-black border-cyan-300 scale-105" : "bg-scada-bg/60 text-scada-dimText/60 border-scada-border/10"}`}>LISTENING</div>
                    <span className="text-scada-dimText text-[8px]">&gt;</span>
                    <div className={`px-1.5 py-0.5 rounded text-[6.5px] font-bold font-mono transition-all border ${voiceState.voice_state === "THINKING" ? "bg-purple-500 text-white border-purple-300 scale-105 animate-pulse" : "bg-scada-bg/60 text-scada-dimText/60 border-scada-border/10"}`}>THINKING</div>
                    <span className="text-scada-dimText text-[8px]">&gt;</span>
                    <div className={`px-1.5 py-0.5 rounded text-[6.5px] font-bold font-mono transition-all border ${voiceState.voice_state === "SPEAKING" ? "bg-emerald-500 text-black border-emerald-300 scale-105" : "bg-scada-bg/60 text-scada-dimText/60 border-scada-border/10"}`}>SPEAKING</div>
                  </div>

                  {/* Session Metrics list */}
                  <div className="flex-1 overflow-y-auto pr-0.5 space-y-1 scrollbar-thin text-[7px] font-mono leading-normal pt-1">
                    <div className="flex justify-between border-b border-scada-border/10 pb-0.5">
                      <span className="text-scada-dimText">SESSION ACTIVE:</span>
                      <span className={voiceState.session_active ? "text-emerald-400 font-bold" : "text-rose-400 font-bold"}>
                        {voiceState.session_active ? "TRUE" : "FALSE"}
                      </span>
                    </div>
                    <div className="flex justify-between border-b border-scada-border/10 pb-0.5">
                      <span className="text-scada-dimText">SESSION TIME REMAINING:</span>
                      <span className="text-white">{voiceState.time_remaining}s</span>
                    </div>
                    <div className="flex justify-between border-b border-scada-border/10 pb-0.5">
                      <span className="text-scada-dimText">STATE DURATION:</span>
                      <span className="text-white">{voiceState.state_duration}s</span>
                    </div>
                    <div className="flex justify-between border-b border-scada-border/10 pb-0.5">
                      <span className="text-scada-dimText">TOTAL SESSIONS SPAWNED:</span>
                      <span className="text-cyan-400">{voiceState.total_sessions}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-scada-dimText">LATEST VOICE TEXT:</span>
                      <span className="text-cyan-300 italic truncate max-w-[150px]">
                        {voiceMemory.latest_voice_text ? `"${voiceMemory.latest_voice_text}"` : "NONE"}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Confidence Gauges */}
                <div className="bg-scada-bg/60 border border-scada-border/30 rounded p-1.5 shrink-0 text-[7px]">
                  <div className="text-[7.5px] font-bold text-scada-dimText uppercase tracking-wider mb-1 flex items-center gap-1">
                    <Sliders size={8} className="text-cyan-400" />
                    <span>Dynamic Matching Confidence Gauges</span>
                  </div>
                  
                  {/* Wake Confidence bar */}
                  <div className="mb-1">
                    <div className="flex justify-between text-[6.5px] mb-0.2">
                      <span className="text-scada-dimText uppercase">Wake Word (Threshold: 0.70)</span>
                      <span className="text-cyan-400">{(wakeWord.last_confidence * 100).toFixed(0)}%</span>
                    </div>
                    <div className="w-full bg-scada-bg h-1 rounded-full overflow-hidden border border-scada-border/20">
                      <div
                        className={`h-full rounded-full transition-all duration-300 ${wakeWord.last_confidence >= 0.70 ? "bg-cyan-500" : "bg-rose-500"}`}
                        style={{ width: `${Math.min(100, wakeWord.last_confidence * 100)}%` }}
                      />
                    </div>
                  </div>

                  {/* STT/Intent confidence bar */}
                  <div>
                    <div className="flex justify-between text-[6.5px] mb-0.2">
                      <span className="text-scada-dimText uppercase">Intent Parsing (Threshold: 0.40)</span>
                      <span className="text-cyan-400">{(semanticIntent.confidence * 100).toFixed(0)}%</span>
                    </div>
                    <div className="w-full bg-scada-bg h-1 rounded-full overflow-hidden border border-scada-border/20">
                      <div
                        className={`h-full rounded-full transition-all duration-300 ${semanticIntent.confidence >= 0.40 ? "bg-cyan-500" : "bg-rose-500"}`}
                        style={{ width: `${Math.min(100, semanticIntent.confidence * 100)}%` }}
                      />
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* 3. PRESENCE & PACING */}
            {activeTab === "presence_pacing" && (
              <div className="flex-1 flex flex-col overflow-hidden justify-between">
                {/* Breathing Core Graph Card */}
                <div className="bg-scada-bg/70 border border-scada-border/30 rounded p-3 mb-1.5 flex-1 flex flex-col justify-center items-center overflow-hidden">
                  <div className="text-[7.5px] font-bold text-scada-dimText uppercase tracking-wider mb-2 border-b border-scada-border/20 pb-0.5 w-full flex items-center justify-between shrink-0">
                    <span className="flex items-center gap-1">
                      <Cpu size={9} className="text-emerald-400" />
                      <span>Real-time Presence Core Node</span>
                    </span>
                    <span className={`px-1 rounded text-[6px] font-bold ${
                      presence.attention_state === "FOCUS" ? "bg-cyan-500 text-black animate-pulse" :
                      presence.attention_state === "ATTENTIVE" ? "bg-emerald-500 text-black" : "bg-scada-bg border border-scada-border text-scada-dimText"
                    }`}>{presence.attention_state}</span>
                  </div>

                  {/* Smooth Animated Breathing Core SVG */}
                  <div className="flex-1 flex items-center justify-center py-2 shrink-0 relative w-full">
                    <svg viewBox="0 0 100 100" className="w-24 h-24 mx-auto select-none">
                      {/* Glow definitions */}
                      <defs>
                        <radialGradient id="presenceGlowCyan">
                          <stop offset="0%" stopColor="#06b6d4" stopOpacity="0.8" />
                          <stop offset="60%" stopColor="#8b5cf6" stopOpacity="0.3" />
                          <stop offset="100%" stopColor="#020617" stopOpacity="0" />
                        </radialGradient>
                        <radialGradient id="presenceGlowEmerald">
                          <stop offset="0%" stopColor="#10b981" stopOpacity="0.8" />
                          <stop offset="60%" stopColor="#06b6d4" stopOpacity="0.3" />
                          <stop offset="100%" stopColor="#020617" stopOpacity="0" />
                        </radialGradient>
                        <radialGradient id="presenceGlowPurple">
                          <stop offset="0%" stopColor="#8b5cf6" stopOpacity="0.8" />
                          <stop offset="60%" stopColor="#ec4899" stopOpacity="0.3" />
                          <stop offset="100%" stopColor="#020617" stopOpacity="0" />
                        </radialGradient>
                        <radialGradient id="presenceGlowRose">
                          <stop offset="0%" stopColor="#f43f5e" stopOpacity="0.8" />
                          <stop offset="60%" stopColor="#e11d48" stopOpacity="0.4" />
                          <stop offset="100%" stopColor="#020617" stopOpacity="0" />
                        </radialGradient>
                      </defs>

                      {/* Outermost breathing orbit ring */}
                      <circle cx="50" cy="50" r={30 + localBreathingCoordinate * 8} fill="none" 
                        stroke={state === "ERROR" ? "#rose" : state === "THINKING" ? "#purple" : "#cyan"}
                        className="transition-all duration-75"
                        strokeWidth="1" strokeDasharray="3,3" opacity="0.3" 
                        style={{
                          stroke: state === "ERROR" ? "#f43f5e" : state === "THINKING" ? "#a855f7" : state === "RESPONDING" ? "#10b981" : "#06b6d4"
                        }}
                      />

                      {/* Second breathing ring */}
                      <circle cx="50" cy="50" r={22 + localBreathingCoordinate * 4} fill="none"
                        className="transition-all duration-75"
                        strokeWidth="1.5" opacity="0.4"
                        style={{
                          stroke: state === "ERROR" ? "#f43f5e" : state === "THINKING" ? "#a855f7" : state === "RESPONDING" ? "#10b981" : "#06b6d4"
                        }}
                      />

                      {/* Glowing radial core */}
                      <circle cx="50" cy="50" r={14 + localBreathingCoordinate * 3} 
                        className="transition-all duration-75"
                        fill={
                          state === "ERROR" ? "url(#presenceGlowRose)" : 
                          state === "THINKING" ? "url(#presenceGlowPurple)" : 
                          state === "RESPONDING" ? "url(#presenceGlowEmerald)" : "url(#presenceGlowCyan)"
                        } 
                      />

                      {/* Inner solid node */}
                      <circle cx="50" cy="50" r={6 + localBreathingCoordinate} 
                        className="transition-all duration-75"
                        fill={
                          state === "ERROR" ? "#f43f5e" : 
                          state === "THINKING" ? "#a855f7" : 
                          state === "RESPONDING" ? "#10b981" : "#06b6d4"
                        } 
                      />
                    </svg>

                    {/* Numeric Breathing Monitor Overlay */}
                    <div className="absolute bottom-1 right-2 text-right text-[6px] text-scada-dimText bg-black/40 px-1 py-0.5 rounded border border-scada-border/10">
                      <div>COORD: {localBreathingCoordinate.toFixed(4)}</div>
                      <div>FREQ: {presence.breathing_frequency_hz} Hz</div>
                    </div>
                  </div>

                  {/* Presence State Data */}
                  <div className="grid grid-cols-2 gap-1 w-full text-[7px] font-mono border-t border-scada-border/10 pt-2 shrink-0">
                    <div className="flex justify-between">
                      <span className="text-scada-dimText">ATTENTION:</span>
                      <span className="text-white font-bold">{presence.attention_state}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-scada-dimText">FREQ MODE:</span>
                      <span className="text-cyan-400 font-bold">{presence.breathing_frequency_hz} Hz</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-scada-dimText">IDLE TIMER:</span>
                      <span className="text-white">{presence.idle_duration_sec}s</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-scada-dimText">ST Stress Override:</span>
                      <span className={reasoning.grid_critical ? "text-rose-400 font-bold" : "text-emerald-400 font-bold"}>
                        {reasoning.grid_critical ? "BYPASS ON" : "NOMINAL"}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Conversation Pacing Panel */}
                <div className="bg-scada-bg/70 border border-scada-border/30 rounded p-2 shrink-0">
                  <div className="text-[7.5px] font-bold text-scada-dimText uppercase tracking-wider mb-1 flex items-center gap-1 border-b border-scada-border/20 pb-0.5">
                    <Clock size={9} className="text-emerald-400" />
                    <span>Emotion-Based Pacing Modulator</span>
                  </div>
                  <div className="flex justify-between items-center text-[7.5px] py-1 bg-black/15 px-1.5 rounded border border-scada-border/5 mb-1.5">
                    <span className="text-scada-dimText">Calculated Pacing Delay:</span>
                    <span className="text-emerald-400 font-bold text-[8px] bg-emerald-950/40 px-1 rounded border border-emerald-500/20">
                      {getPacingDelayValue(emotion.assistant_mood, reasoning.grid_critical).toFixed(2)} seconds
                    </span>
                  </div>
                  <p className="text-[6.5px] text-scada-dimText/80 leading-tight">
                    Excited speaks fast (0.15s), Serious nominal (0.30s), Calm default (0.50s), Tired slow (1.10s).
                    {reasoning.grid_critical ? (
                      <span className="text-rose-400 font-bold block mt-0.5">CRITICAL OVERRIDE ACTIVE: 0.0s delay forced for rapid SCADA action.</span>
                    ) : (
                      <span className="text-emerald-400 block mt-0.5">Nominal pacing delay is currently applied.</span>
                    )}
                  </p>
                </div>
              </div>
            )}

            {/* 4. PROACTIVE ALERTS & HOOKS */}
            {activeTab === "proactive_hooks" && (
              <div className="flex-1 flex flex-col overflow-hidden justify-between">
                {/* Alerts logs & n8n hooks */}
                <div className="bg-scada-bg/70 border border-scada-border/30 rounded p-2 mb-1.5 flex-1 flex flex-col overflow-hidden">
                  <div className="text-[7.5px] font-bold text-scada-dimText uppercase tracking-wider mb-2 border-b border-scada-border/20 pb-0.5 flex justify-between items-center shrink-0">
                    <span className="flex items-center gap-1">
                      <Zap size={9} className="text-amber-400" />
                      <span>Proactive Grid Notifications</span>
                    </span>
                    <span className="text-[6.5px] text-scada-dimText">
                      Sent: {proactive.total_notifications_sent}
                    </span>
                  </div>

                  {/* Cooldown Timers Progress Bars */}
                  <div className="space-y-1 mb-2 shrink-0">
                    {/* A. broker_disconnect */}
                    <div>
                      <div className="flex justify-between text-[6.5px] text-scada-dimText leading-none mb-0.2">
                        <span>Heartbeat Disconnection</span>
                        <span className={proactive.cooldown_timers.broker_disconnect > 0 ? "text-rose-400 font-bold" : "text-emerald-400 font-bold"}>
                          {proactive.cooldown_timers.broker_disconnect > 0 ? `${proactive.cooldown_timers.broker_disconnect}s locked` : "READY"}
                        </span>
                      </div>
                      <div className="w-full bg-scada-bg h-1 rounded-full overflow-hidden border border-scada-border/20">
                        <div className={`h-full rounded-full transition-all duration-300 ${proactive.cooldown_timers.broker_disconnect > 0 ? "bg-rose-500" : "bg-emerald-500"}`}
                          style={{ width: proactive.cooldown_timers.broker_disconnect > 0 ? `${(proactive.cooldown_timers.broker_disconnect / 45.0) * 100}%` : "100%" }}
                        />
                      </div>
                    </div>
                    {/* B. relay_unstable */}
                    <div>
                      <div className="flex justify-between text-[6.5px] text-scada-dimText leading-none mb-0.2">
                        <span>Relay Instability</span>
                        <span className={proactive.cooldown_timers.relay_unstable > 0 ? "text-rose-400 font-bold" : "text-emerald-400 font-bold"}>
                          {proactive.cooldown_timers.relay_unstable > 0 ? `${proactive.cooldown_timers.relay_unstable}s locked` : "READY"}
                        </span>
                      </div>
                      <div className="w-full bg-scada-bg h-1 rounded-full overflow-hidden border border-scada-border/20">
                        <div className={`h-full rounded-full transition-all duration-300 ${proactive.cooldown_timers.relay_unstable > 0 ? "bg-rose-500" : "bg-emerald-500"}`}
                          style={{ width: proactive.cooldown_timers.relay_unstable > 0 ? `${(proactive.cooldown_timers.relay_unstable / 45.0) * 100}%` : "100%" }}
                        />
                      </div>
                    </div>
                    {/* C. sync_recovered */}
                    <div>
                      <div className="flex justify-between text-[6.5px] text-scada-dimText leading-none mb-0.2">
                        <span>Telemetry Sync Recovery</span>
                        <span className={proactive.cooldown_timers.sync_recovered > 0 ? "text-rose-400 font-bold" : "text-emerald-400 font-bold"}>
                          {proactive.cooldown_timers.sync_recovered > 0 ? `${proactive.cooldown_timers.sync_recovered}s locked` : "READY"}
                        </span>
                      </div>
                      <div className="w-full bg-scada-bg h-1 rounded-full overflow-hidden border border-scada-border/20">
                        <div className={`h-full rounded-full transition-all duration-300 ${proactive.cooldown_timers.sync_recovered > 0 ? "bg-rose-500" : "bg-emerald-500"}`}
                          style={{ width: proactive.cooldown_timers.sync_recovered > 0 ? `${(proactive.cooldown_timers.sync_recovered / 45.0) * 100}%` : "100%" }}
                        />
                      </div>
                    </div>
                    {/* D. latency_spike */}
                    <div>
                      <div className="flex justify-between text-[6.5px] text-scada-dimText leading-none mb-0.2">
                        <span>Latency Spike (Ping &gt; 500ms)</span>
                        <span className={proactive.cooldown_timers.latency_spike > 0 ? "text-rose-400 font-bold" : "text-emerald-400 font-bold"}>
                          {proactive.cooldown_timers.latency_spike > 0 ? `${proactive.cooldown_timers.latency_spike}s locked` : "READY"}
                        </span>
                      </div>
                      <div className="w-full bg-scada-bg h-1 rounded-full overflow-hidden border border-scada-border/20">
                        <div className={`h-full rounded-full transition-all duration-300 ${proactive.cooldown_timers.latency_spike > 0 ? "bg-rose-500" : "bg-emerald-500"}`}
                          style={{ width: proactive.cooldown_timers.latency_spike > 0 ? `${(proactive.cooldown_timers.latency_spike / 45.0) * 100}%` : "100%" }}
                        />
                      </div>
                    </div>
                  </div>

                  {/* Scrolling alerts history logs */}
                  <div className="flex-1 bg-black/15 border border-scada-border/10 rounded p-1 flex flex-col overflow-hidden">
                    <div className="text-[6.5px] text-scada-dimText uppercase font-bold tracking-wider mb-0.5 border-b border-scada-border/10 pb-0.5 shrink-0 flex items-center gap-1">
                      <Terminal size={7} /> Alerts dispatch history (45s Lockout)
                    </div>
                    <div className="flex-1 overflow-y-auto space-y-1.5 scrollbar-thin text-[6.5px] font-mono leading-tight pt-1 pr-0.5">
                      {proactive.history.length === 0 ? (
                        <div className="h-full flex items-center justify-center text-scada-dimText/40 italic">
                          No alerts recorded. Standby...
                        </div>
                      ) : (
                        [...proactive.history].reverse().map((item: any, idx: number) => (
                          <div key={idx} className="border-l border-amber-500 pl-1 py-0.5">
                            <div className="flex justify-between font-bold text-amber-400 text-[6px]">
                              <span>CAT: {item.category}</span>
                              <span>T: {new Date(item.timestamp).toLocaleTimeString()}</span>
                            </div>
                            <div className="text-white italic">"{item.message}"</div>
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                </div>

                {/* n8n hooks status */}
                <div className="bg-scada-bg/50 border border-scada-border/30 rounded p-1.5 mb-1.5 shrink-0 text-[7px]">
                  {automationHooks.latest_hook_status?.status ? (
                    <div className="flex justify-between items-center text-amber-400">
                      <span className="flex items-center gap-1 font-bold">
                        <ShieldCheck size={8} /> n8n: {automationHooks.latest_hook_status.hook_name}
                      </span>
                      <span className="bg-emerald-500 text-black px-1 rounded text-[6px] font-mono font-bold">SUCCESS</span>
                    </div>
                  ) : (
                    <span className="text-scada-dimText italic">n8n webhook listener active...</span>
                  )}
                </div>

                {/* Simulation Buttons Grid */}
                <div className="bg-scada-bg/70 border border-scada-border/30 rounded p-2 shrink-0">
                  <div className="text-[7.5px] font-bold text-scada-dimText uppercase tracking-wider mb-1 flex items-center gap-1 border-b border-scada-border/20 pb-0.5">
                    <Activity size={8} className="text-amber-400" />
                    <span>Real-time Hardware Simulation Controls</span>
                  </div>

                  <div className="grid grid-cols-3 gap-1 pt-1.5">
                    <button onClick={triggerWakeWordSim}
                      className="bg-cyan-950 hover:bg-cyan-900 border border-cyan-500/30 rounded py-1 text-[7px] text-cyan-300 font-bold transition-all hover:scale-102 flex items-center justify-center gap-0.5">
                      <Play size={7} /> Wake Word
                    </button>
                    <button onClick={triggerLatencySpikeSim}
                      className="bg-amber-950 hover:bg-amber-900 border border-amber-500/30 rounded py-1 text-[7px] text-amber-300 font-bold transition-all hover:scale-102 flex items-center justify-center gap-0.5">
                      <Zap size={7} /> Latency
                    </button>
                    <button onClick={triggerRelayInstabilitySim}
                      className="bg-rose-950 hover:bg-rose-900 border border-rose-500/30 rounded py-1 text-[7px] text-rose-300 font-bold transition-all hover:scale-102 flex items-center justify-center gap-0.5">
                      <Zap size={7} /> Flapping
                    </button>
                    <button onClick={triggerBrokerDisconnectSim}
                      className="bg-rose-950 hover:bg-rose-900 border border-rose-500/30 rounded py-1 text-[7px] text-rose-300 font-bold transition-all hover:scale-102 flex items-center justify-center gap-0.5 col-span-1.5">
                      <WifiOff size={7} /> Disconnect
                    </button>
                    <button onClick={triggerSyncRecoverySim}
                      className="bg-emerald-950 hover:bg-emerald-900 border border-emerald-500/30 rounded py-1 text-[7px] text-emerald-300 font-bold transition-all hover:scale-102 flex items-center justify-center gap-0.5 col-span-1.5">
                      <RotateCcw size={7} /> Recover Sync
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
