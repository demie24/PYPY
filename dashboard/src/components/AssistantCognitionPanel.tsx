import React, { useState, useEffect, useRef } from "react";
import {
  Send, Mic, Bot, Sparkles, User, Cpu, Smile, Volume2, RotateCcw,
  MessageSquare, Compass, GitBranch, Bell, CheckCircle2, XCircle, RefreshCw,
  Terminal, Sliders, Activity, Clock, AlertTriangle, Shield
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

interface ConversationalPlanning {
  active_plans_count: number;
  active_plans: any[];
  history_count: number;
  plan_history: any[];
}

interface TaskChains {
  active_chains_count: number;
  active_chains: any[];
  completed_chains_count: number;
  completed_chains: any[];
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

interface Dialogue {
  dialogue_state: string;
  parameter_needed: string;
  clarification_question: string;
  has_pending_phrase: boolean;
}

interface OrchestrationPlanner {
  last_execution_status: string;
  last_confidence_score: number;
  validation_logs_count: number;
  validation_logs: string[];
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
  // Phase 9.3 props
  assistantVoiceState?: any | null;
  assistantWakeWord?: any | null;
  assistantProactive?: any | null;
  assistantVoiceMemory?: any | null;
  assistantPresence?: any | null;
  // Phase 9.4 props
  assistantWorkflows?: any | null;
  assistantReminders?: any | null;
  assistantConditions?: any | null;
  assistantN8nBridge?: any | null;
  assistantRoutines?: any | null;
  // Phase 9.5 props
  assistantConversationPlanning?: ConversationalPlanning | null;
  assistantTaskChains?: TaskChains | null;
  assistantLiveStream?: LiveStream | null;
  assistantDialogue?: Dialogue | null;
  assistantOrchestrationPlanner?: OrchestrationPlanner | null;
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
  assistantSemanticResponse,
  connected,
  onSendControl,
  assistantVoiceState,
  assistantWakeWord,
  assistantVoiceMemory,
  assistantPresence,
  assistantWorkflows,
  assistantN8nBridge,
  assistantRoutines,
  assistantConversationPlanning,
  assistantTaskChains,
  assistantLiveStream,
  assistantDialogue,
  assistantOrchestrationPlanner
}) => {
  const [chatText, setChatText] = useState("");
  const [clarifyAnswerText, setClarifyAnswerText] = useState("");
  const [isListeningVoice, setIsListeningVoice] = useState(false);
  const [voiceSimProgress, setVoiceSimProgress] = useState(0);
  const [activeTab, setActiveTab] = useState<"reasoning" | "planning" | "dialogue" | "workflows" | "presence">("reasoning");
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
  // Removed unused automationHooks
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
  // Removed unused proactive
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

  // Phase 9.4 Parameters:
  const workflows = assistantWorkflows?.workflows ?? {
    executions: [],
    delayed_tasks_count: 0,
    delayed_queue: [],
    cooldown_timers: {},
    call_stack: [],
    total_executions: 0
  };
  // Removed unused reminders and conditions
  const n8nBridge = assistantN8nBridge?.n8n_bridge ?? {
    executions: [],
    active_retries_count: 0,
    active_retries: [],
    total_executions: 0
  };
  const routines = assistantRoutines?.routines ?? {
    recommended_routines: [],
    routines_count: 0,
    interaction_history: [],
    command_frequencies: {}
  };

  const latestWf = workflows.executions.length > 0 ? workflows.executions[workflows.executions.length - 1] : null;

  // Phase 9.5 Parameters:
  const planning = assistantConversationPlanning ?? {
    active_plans_count: 0,
    active_plans: [],
    history_count: 0,
    plan_history: []
  };
  const taskChains = assistantTaskChains ?? {
    active_chains_count: 0,
    active_chains: [],
    completed_chains_count: 0,
    completed_chains: []
  };
  const liveStream = assistantLiveStream ?? {
    is_streaming: false,
    status: "IDLE",
    full_response_text: "",
    output_buffer: "",
    progress_pct: 0.0,
    elapsed_sec: 0.0,
    interrupted_at_text: "",
    interruption_apology: ""
  };
  const dialogue = assistantDialogue ?? {
    dialogue_state: "IDLE",
    parameter_needed: "",
    clarification_question: "",
    has_pending_phrase: false
  };
  const plannerBridge = assistantOrchestrationPlanner ?? {
    last_execution_status: "IDLE",
    last_confidence_score: 1.0,
    validation_logs_count: 0,
    validation_logs: []
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

  // Determine interactions list
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

  // Phase 9.5 Simulation Controls triggers
  const triggerAmbiguityClarification = () => {
    onSendControl({
      topic: "assistant/dialogue_simulation",
      payload: {
        action: "check",
        phrase: "check latency",
        intent: { category: "CHECK_LATENCY", action: "measure", parameters: {} }
      }
    });
  };

  const triggerStreamingInterruption = () => {
    onSendControl({
      topic: "assistant/stream_simulation",
      payload: {
        action: "start",
        text: "Sila bersedia, saya sedang memulakan proses pengasingan talian grid yang mengalami gangguan transient frekuensi tinggi..."
      }
    });
    setTimeout(() => {
      onSendControl({
        topic: "assistant/stream_simulation",
        payload: { action: "interrupt" }
      });
    }, 800);
  };

  const triggerChainedTaskPlan = () => {
    onSendControl({
      topic: "assistant/plan_simulation",
      payload: {
        action: "create",
        query: "check latency lepas tu kalau tinggi trigger recovery workflow",
        intent: { category: "CHECK_LATENCY", action: "measure" }
      }
    });
    setTimeout(() => {
      onSendControl({
        topic: "assistant/chain_simulation",
        payload: { action: "submit" }
      });
    }, 200);
  };

  const triggerDependencyFailure = () => {
    const activeChain = taskChains.active_chains[taskChains.active_chains.length - 1];
    if (activeChain) {
      onSendControl({
        topic: "assistant/plan_simulation",
        payload: {
          action: "update_step",
          plan_id: activeChain.chain_id,
          step_id: activeChain.steps[0].step_id,
          status: "FAILED",
          log: "Langkah pertama dipaksa gagal untuk simulasi dep."
        }
      });
    } else {
      // Step 1: Submit plan and chain
      onSendControl({
        topic: "assistant/plan_simulation",
        payload: {
          action: "create",
          query: "check latency lepas tu kalau tinggi trigger recovery workflow",
          intent: { category: "CHECK_LATENCY", action: "measure" }
        }
      });
      setTimeout(() => {
        onSendControl({
          topic: "assistant/chain_simulation",
          payload: { action: "submit" }
        });
      }, 200);
    }
  };

  const triggerConfidenceGateBlock = () => {
    onSendControl({
      topic: "assistant/orchestration_simulation",
      payload: {
        action: "set_safety",
        confidence_threshold: 0.95,
        min_stability: 30.0
      }
    });
    // Create critical step
    onSendControl({
      topic: "assistant/plan_simulation",
      payload: {
        action: "create",
        query: "trigger emergency load shed",
        intent: { category: "TRIGGER_WORKFLOW", action: "execute", parameters: { workflow_name: "emergency_load_shed" } }
      }
    });
    setTimeout(() => {
      onSendControl({
        topic: "assistant/chain_simulation",
        payload: { action: "submit" }
      });
    }, 200);
  };

  const triggerRunawayChain = () => {
    // Submit same request twice for recursive loop detection
    onSendControl({
      topic: "assistant/plan_simulation",
      payload: {
        action: "create",
        query: "check latency please",
        intent: { category: "CHECK_LATENCY", action: "measure" }
      }
    });
    setTimeout(() => {
      onSendControl({
        topic: "assistant/chain_simulation",
        payload: { action: "submit" }
      });
      setTimeout(() => {
        onSendControl({
          topic: "assistant/chain_simulation",
          payload: { action: "submit" }
        });
      }, 100);
    }, 200);
  };

  const handleResolveDialogue = (answer: string) => {
    onSendControl({
      topic: "assistant/dialogue_simulation",
      payload: { action: "resolve", answer }
    });
    setClarifyAnswerText("");
  };

  // Removed unused handleCancelReminder

  const handleAcceptRoutine = (routineType: string) => {
    onSendControl({
      topic: "assistant/routine_trigger",
      payload: { action: "accept", routine_type: routineType }
    });
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

  const getPacingDelayValue = (mood: string, critical: boolean) => {
    if (critical) return 0.0;
    if (mood === "excited") return 0.15;
    if (mood === "tired") return 1.10;
    if (mood === "serious" || mood === "focused") return 0.30;
    return 0.50;
  };

  // Derived timeline elements
  const activePlan = planning.active_plans.length > 0 ? planning.active_plans[planning.active_plans.length - 1] : null;
  const activeChain = taskChains.active_chains.length > 0 ? taskChains.active_chains[taskChains.active_chains.length - 1] : null;
  const displayPlan = activeChain ?? activePlan;

  return (
    <div className="bg-scada-panel border border-scada-border rounded-lg p-3 h-[420px] flex flex-col overflow-hidden relative font-mono text-[9px] text-white">
      {/* Dynamic Background Glow */}
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
          {/* Link status badge */}
          <div className="flex items-center gap-1 bg-scada-bg/85 px-1.5 py-0.5 rounded border border-scada-border/30">
            <span className="text-scada-dimText">LINK:</span>
            <span className={`font-bold ${connected ? "text-emerald-400" : "text-rose-500 animate-pulse"}`}>
              {connected ? "ONLINE" : "OFFLINE"}
            </span>
          </div>
          {/* Uptime Indicator */}
          <div className="flex items-center gap-1 bg-scada-bg/85 px-1.5 py-0.5 rounded border border-scada-border/30">
            <span className="text-scada-dimText">UPTIME:</span>
            <span className={`font-bold ${runtime.status === "ONLINE" ? "text-emerald-400" : "text-rose-400"}`}>
              {runtime.uptime_sec}s
            </span>
          </div>
          <button onClick={handleResetMemory} className="p-1 hover:bg-scada-border/40 rounded text-scada-dimText hover:text-white transition-colors" title="Reset Session">
            <RotateCcw size={10} />
          </button>
        </div>
      </div>

      {/* Main content split */}
      <div className="flex-1 flex gap-3 overflow-hidden z-10 min-h-0">
        {/* Left Side: Chat Console */}
        <div className="w-[45%] flex flex-col overflow-hidden bg-scada-bg/50 border border-scada-border/30 rounded p-2">
          <div className="flex justify-between items-center mb-1 border-b border-scada-border/20 pb-1.5 shrink-0 text-[8px] text-scada-dimText uppercase tracking-wider font-semibold">
            <span className="flex items-center gap-1">
              <Compass size={9} className="text-cyan-400" /> Topic: <span className="text-cyan-300 font-bold">{contextualMemory.active_subject ?? context.current_topic ?? "NONE"}</span>
            </span>
            <span>Thread: <span className="text-white font-bold">{contextualMemory.active_thread_id ? `T-${contextualMemory.active_thread_id.substring(0, 4)}` : "NONE"}</span></span>
          </div>

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
                    <div className={`max-w-[90%] rounded p-2 border flex gap-1.5 leading-relaxed ${
                      isUser
                        ? "bg-cyan-950/40 border-cyan-500/20 text-cyan-100"
                        : "bg-scada-bg/85 border-scada-border/40 text-emerald-100"
                    }`}>
                      <div className="shrink-0 mt-0.5">
                        {isUser ? <User size={10} className="text-cyan-400" /> : <Bot size={10} className="text-emerald-400" />}
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

          {semanticResponse.clean_tts_text && (
            <div className="bg-black/10 border border-scada-border/20 rounded p-1 mb-1 shrink-0 text-[6.5px] text-emerald-400 flex items-center gap-1 select-none">
              <Volume2 size={8} className="shrink-0 text-emerald-400 animate-pulse" />
              <span className="truncate">TTS Text: {semanticResponse.clean_tts_text}</span>
            </div>
          )}

          <div className="grid grid-cols-2 gap-1 mb-1.5 shrink-0">
            <button onClick={() => handleQuickCommand("check latency", false)}
              className="bg-scada-bg hover:bg-scada-border/20 border border-scada-border/30 rounded p-1 text-left text-[7.5px] text-scada-dimText truncate flex items-center gap-1">
              <MessageSquare size={8} className="text-cyan-400" /> "Check Latency"
            </button>
            <button onClick={() => handleQuickCommand("check latency lepas tu kalau tinggi trigger recovery workflow", false)}
              className="bg-scada-bg hover:bg-scada-border/20 border border-scada-border/30 rounded p-1 text-left text-[7.5px] text-scada-dimText truncate flex items-center gap-1">
              <Compass size={8} className="text-purple-400" /> "Run Chained Plan"
            </button>
          </div>

          <div className="flex gap-1.5 shrink-0 items-center">
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

            <input
              type="text"
              value={chatText}
              onChange={(e) => setChatText(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSendChat()}
              placeholder={isListeningVoice ? `Listening (${voiceSimProgress}%)...` : "Type request..."}
              disabled={isListeningVoice || state !== "IDLE"}
              className="flex-1 bg-scada-bg border border-scada-border/50 text-white rounded p-1.5 text-[8.5px] outline-none placeholder:text-scada-dimText/60"
            />

            <button
              onClick={handleSendChat}
              disabled={!chatText.trim() || state !== "IDLE"}
              className="p-2 bg-emerald-950 border border-emerald-500/40 hover:bg-emerald-900 text-emerald-400 rounded disabled:opacity-40 shrink-0 transition-colors"
            >
              <Send size={12} />
            </button>
          </div>
        </div>

        {/* Right Side: Cognition Tabs */}
        <div className="w-[55%] flex flex-col overflow-hidden">
          <div className="flex border-b border-scada-border/30 mb-2 bg-scada-bg/30 rounded-t overflow-hidden shrink-0">
            <button
              onClick={() => setActiveTab("reasoning")}
              className={`flex-1 py-1.5 text-[7.5px] uppercase tracking-wider font-bold text-center border-b-2 transition-all flex items-center justify-center gap-0.5 ${
                activeTab === "reasoning" ? "border-purple-500 text-white bg-purple-500/10" : "border-transparent text-scada-dimText hover:text-white"
              }`}
            >
              <Activity size={9} />
              Reasoning
            </button>
            <button
              onClick={() => setActiveTab("planning")}
              className={`flex-1 py-1.5 text-[7.5px] uppercase tracking-wider font-bold text-center border-b-2 transition-all flex items-center justify-center gap-0.5 ${
                activeTab === "planning" ? "border-cyan-500 text-white bg-cyan-500/10" : "border-transparent text-scada-dimText hover:text-white"
              }`}
            >
              <GitBranch size={9} />
              Planning & Chains
            </button>
            <button
              onClick={() => setActiveTab("dialogue")}
              className={`flex-1 py-1.5 text-[7.5px] uppercase tracking-wider font-bold text-center border-b-2 transition-all flex items-center justify-center gap-0.5 ${
                activeTab === "dialogue" ? "border-yellow-500 text-white bg-yellow-500/10" : "border-transparent text-scada-dimText hover:text-white"
              }`}
            >
              <Volume2 size={9} />
              Dialogue & Stream
            </button>
            <button
              onClick={() => setActiveTab("workflows")}
              className={`flex-1 py-1.5 text-[7.5px] uppercase tracking-wider font-bold text-center border-b-2 transition-all flex items-center justify-center gap-0.5 ${
                activeTab === "workflows" ? "border-blue-500 text-white bg-blue-500/10" : "border-transparent text-scada-dimText hover:text-white"
              }`}
            >
              <Bell size={9} />
              Workflows
            </button>
            <button
              onClick={() => setActiveTab("presence")}
              className={`flex-1 py-1.5 text-[7.5px] uppercase tracking-wider font-bold text-center border-b-2 transition-all flex items-center justify-center gap-0.5 ${
                activeTab === "presence" ? "border-emerald-500 text-white bg-emerald-500/10" : "border-transparent text-scada-dimText hover:text-white"
              }`}
            >
              <Clock size={9} />
              Presence
            </button>
          </div>

          <div className="flex-1 overflow-hidden flex flex-col justify-between">
            <div className="flex-1 overflow-y-auto mb-1.5 pr-0.5 scrollbar-thin">
              {/* Tab 1: Reasoning */}
              {activeTab === "reasoning" && (
                <div className="space-y-1.5">
                  {/* Cognitive FSM */}
                  <div className="bg-scada-bg/40 border border-scada-border/30 rounded p-1.5">
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

                  {/* Reasoning Logs */}
                  <div className="bg-scada-bg/70 border border-scada-border/30 rounded p-1.5 h-[95px] flex flex-col overflow-hidden">
                    <div className="text-[7px] font-bold text-scada-dimText uppercase tracking-wider mb-1 flex items-center gap-1 border-b border-scada-border/20 pb-0.5 shrink-0">
                      <Terminal size={9} className="text-purple-400" />
                      <span>Decision Reasoning Logs</span>
                    </div>
                    <div className="flex-1 overflow-y-auto space-y-1 scrollbar-thin text-[6.5px] leading-normal pt-1">
                      {reasoning.reasoning_logs.map((log: string, index: number) => {
                        let color = "text-white/80";
                        if (log.includes("SAFETY OVERRIDE")) color = "text-rose-400 font-bold bg-rose-950/20 pl-1 border-l border-rose-500";
                        else if (log.includes("Decomposing")) color = "text-cyan-400";
                        else if (log.includes("Matched pattern")) color = "text-amber-400";
                        else if (log.includes("resolving") || log.includes("resolved")) color = "text-emerald-400";
                        return <div key={index} className={color}>&gt; {log}</div>;
                      })}
                    </div>
                  </div>

                  {/* Voice state info */}
                  <div className="bg-scada-bg/40 border border-scada-border/30 rounded p-1.5 text-[7px] space-y-1">
                    <div className="text-[7px] font-bold text-scada-dimText uppercase tracking-wider flex justify-between">
                      <span>VOICE & ATTENTION STATE</span>
                      <span className={`px-1 rounded text-[6px] ${wakeWord.attention_active ? "text-emerald-400 border border-emerald-500/20" : "text-scada-dimText bg-scada-bg"}`}>
                        {wakeWord.attention_active ? "ATTENTION ON" : "STANDBY"}
                      </span>
                    </div>
                    <div className="grid grid-cols-2 gap-1 text-[6.5px] pt-1">
                      <div className="flex justify-between"><span className="text-scada-dimText">Voice State:</span><span className="text-white">{voiceState.voice_state}</span></div>
                      <div className="flex justify-between"><span className="text-scada-dimText">Remaining Attention:</span><span className="text-white">{wakeWord.time_remaining}s</span></div>
                      <div className="flex justify-between"><span className="text-scada-dimText">Latest Intent:</span><span className="text-cyan-400 truncate max-w-[80px]">{voiceMemory.latest_command ?? semanticIntent.category}</span></div>
                      <div className="flex justify-between"><span className="text-scada-dimText">Match Conf:</span><span className="text-cyan-400">{(semanticIntent.confidence * 100).toFixed(0)}%</span></div>
                    </div>
                  </div>
                </div>
              )}

              {/* Tab 2: Planning & Chains */}
              {activeTab === "planning" && (
                <div className="space-y-1.5">
                  <div className="bg-scada-bg/60 border border-scada-border/30 rounded p-1.5">
                    <div className="text-[7px] font-bold text-scada-dimText uppercase tracking-wider mb-1 flex justify-between border-b border-scada-border/20 pb-0.5">
                      <span>MULTISTEP PLANNING CHAIN</span>
                      <span className="text-cyan-400 font-bold">Active Chains: {taskChains.active_chains_count}</span>
                    </div>

                    {displayPlan ? (
                      <div className="space-y-1.5 pt-1">
                        <div className="flex justify-between text-[7px] bg-black/20 p-1 rounded">
                          <span className="text-scada-dimText">Query: <strong className="text-white">"{displayPlan.original_query}"</strong></span>
                          <span className={`px-1 rounded text-[6px] font-bold uppercase ${
                            displayPlan.status === "COMPLETED" ? "bg-emerald-950 text-emerald-400" :
                            displayPlan.status === "FAILED" ? "bg-rose-950 text-rose-400" :
                            displayPlan.status === "TIMEOUT" ? "bg-red-950 text-red-400" : "bg-cyan-950 text-cyan-400 animate-pulse"
                          }`}>
                            {displayPlan.status}
                          </span>
                        </div>

                        {/* Steps Sequence Graph */}
                        <div className="space-y-1">
                          {displayPlan.steps.map((s: any, idx: number) => {
                            const isCurrent = activeChain && activeChain.current_step_idx === idx;
                            return (
                              <div key={idx} className={`p-1 rounded flex items-center justify-between border text-[6.5px] ${
                                isCurrent ? "bg-cyan-950/20 border-cyan-500 text-white" :
                                s.status === "SUCCESS" ? "bg-emerald-950/10 border-emerald-500/20 text-emerald-300" :
                                s.status === "FAILED" ? "bg-rose-950/10 border-rose-500/20 text-rose-300" : "bg-black/10 border-scada-border/10 text-scada-dimText"
                              }`}>
                                <div className="flex items-center gap-1.5 min-w-0">
                                  <span className="font-semibold text-scada-dimText text-[6px]">{idx + 1}.</span>
                                  <span className="truncate font-bold uppercase text-[7px]">{s.objective}</span>
                                  <span className="truncate text-scada-dimText">({s.description})</span>
                                </div>
                                <div className="flex items-center gap-1.5 shrink-0">
                                  {s.dependencies?.length > 0 && (
                                    <span className="text-[5.5px] bg-scada-bg px-1 rounded text-purple-400">Dep: s{idx}</span>
                                  )}
                                  {s.status === "SUCCESS" && <CheckCircle2 size={8.5} className="text-emerald-400" />}
                                  {s.status === "FAILED" && <XCircle size={8.5} className="text-rose-400" />}
                                  {s.status === "RUNNING" && <RefreshCw size={8.5} className="text-amber-400 animate-spin" />}
                                  {s.status === "PENDING" && <Clock size={8.5} className="text-scada-dimText" />}
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    ) : (
                      <div className="text-[7px] text-scada-dimText italic text-center py-4 flex flex-col items-center gap-1">
                        <GitBranch size={16} className="opacity-30" />
                        No active multi-step plans in loop memory.
                      </div>
                    )}
                  </div>

                  {/* Safety Gates Gauges */}
                  <div className="bg-scada-bg/40 border border-scada-border/30 rounded p-1.5">
                    <div className="text-[7.5px] font-bold text-scada-dimText uppercase tracking-wider mb-1 flex items-center gap-1">
                      <Shield size={9} className="text-amber-400" />
                      <span>Orchestration Safety & Confidence Gates</span>
                    </div>
                    <div className="space-y-1.5 pt-1 text-[6.5px]">
                      <div>
                        <div className="flex justify-between mb-0.5 text-scada-dimText">
                          <span>Threat Score Confidence</span>
                          <span className={plannerBridge.last_confidence_score >= 0.50 ? "text-emerald-400" : "text-rose-400"}>
                            {plannerBridge.last_confidence_score.toFixed(2)} (Min: 0.50)
                          </span>
                        </div>
                        <div className="w-full bg-black/40 h-1.5 rounded-full overflow-hidden border border-scada-border/10">
                          <div 
                            className={`h-full transition-all duration-500 ${plannerBridge.last_confidence_score >= 0.50 ? "bg-emerald-500" : "bg-rose-500"}`}
                            style={{ width: `${plannerBridge.last_confidence_score * 100}%` }}
                          />
                        </div>
                      </div>

                      {/* Planner Bridge status summary logs */}
                      <div className="bg-black/20 p-1.5 rounded border border-scada-border/10 h-[45px] overflow-y-auto scrollbar-thin text-[5.8px]">
                        <span className="text-scada-dimText block uppercase tracking-wider font-semibold border-b border-scada-border/15 pb-0.5 mb-1">Planner Bridge Safety Logs</span>
                        {plannerBridge.validation_logs.length === 0 ? (
                          <span className="text-scada-dimText/40 italic">Safety logs empty</span>
                        ) : (
                          plannerBridge.validation_logs.map((log: string, i: number) => {
                            let color = "text-scada-dimText";
                            if (log.includes("SAFETY REJECTION")) color = "text-rose-400 font-bold";
                            else if (log.includes("CRITICAL ESCALATION")) color = "text-amber-400 font-bold";
                            else if (log.includes("Bridging")) color = "text-cyan-400";
                            return <div key={i} className={color}>&gt; {log}</div>;
                          })
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Tab 3: Dialogue & Stream */}
              {activeTab === "dialogue" && (
                <div className="space-y-1.5">
                  {/* Realtime Response Stream Terminal */}
                  <div className="bg-black/60 border border-scada-border/30 rounded p-1.5 flex flex-col h-[90px] overflow-hidden">
                    <div className="text-[7.5px] font-bold text-scada-dimText uppercase tracking-wider mb-1 border-b border-scada-border/20 pb-0.5 flex justify-between shrink-0">
                      <span className="flex items-center gap-1"><Volume2 size={9} className="text-yellow-400" /> Live Response Stream</span>
                      {liveStream.is_streaming && <span className="text-yellow-400 animate-pulse font-bold">{liveStream.progress_pct}%</span>}
                    </div>
                    
                    <div className="flex-1 overflow-y-auto p-1 font-mono text-[7.5px] leading-tight text-cyan-300 relative scrollbar-thin bg-black/40 rounded mt-1">
                      {liveStream.output_buffer ? (
                        <span>
                          {liveStream.output_buffer}
                          {liveStream.is_streaming && <span className="inline-block w-1.5 h-3 bg-cyan-400 ml-0.5 animate-pulse" />}
                        </span>
                      ) : (
                        <span className="text-scada-dimText/30 italic">Streaming buffer idle...</span>
                      )}

                      {/* Apology Interrupted Alert */}
                      {liveStream.status === "INTERRUPTED" && (
                        <div className="mt-1.5 p-1 border border-rose-500/20 bg-rose-950/20 rounded text-[6.8px] text-rose-400 leading-tight">
                          <div className="font-bold uppercase flex items-center gap-1 mb-0.5"><AlertTriangle size={8} /> Response Interrupted</div>
                          <div className="italic text-yellow-300">"{liveStream.interruption_apology}"</div>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Active Dialogue Clarification Module */}
                  <div className="bg-scada-bg/40 border border-scada-border/30 rounded p-1.5">
                    <div className="text-[7.5px] font-bold text-scada-dimText uppercase tracking-wider mb-1 flex justify-between border-b border-scada-border/20 pb-0.5">
                      <span>DIALOGUE CLARIFICATION GATE</span>
                      <span className={`px-1.5 rounded text-[6px] font-bold ${
                        dialogue.dialogue_state === "AWAITING_CLARIFICATION" ? "bg-amber-950 text-amber-400 animate-pulse border border-amber-500/20" : "bg-black/30 text-scada-dimText"
                      }`}>
                        {dialogue.dialogue_state}
                      </span>
                    </div>

                    {dialogue.dialogue_state === "AWAITING_CLARIFICATION" ? (
                      <div className="pt-1.5 space-y-1.5">
                        <div className="text-[8px] font-bold text-white bg-amber-950/20 p-1 border-l-2 border-amber-500 rounded">
                          Question: <span className="text-amber-300 font-mono">"{dialogue.clarification_question}"</span>
                        </div>
                        <div className="flex gap-1 text-[6.5px]">
                          <span className="text-scada-dimText font-bold">Needed parameter:</span>
                          <span className="text-amber-400 uppercase tracking-wider font-semibold">{dialogue.parameter_needed}</span>
                        </div>

                        {/* Dialogue Resolution helpers */}
                        <div className="flex flex-wrap gap-1 pt-0.5">
                          {dialogue.parameter_needed === "target_bus" && (
                            <>
                              <button onClick={() => handleResolveDialogue("Bus 5")} className="px-1.5 py-0.5 bg-cyan-950 border border-cyan-500/30 text-cyan-300 rounded hover:bg-cyan-900 text-[6.5px]">Resolve: Bus 5</button>
                              <button onClick={() => handleResolveDialogue("Bus 7")} className="px-1.5 py-0.5 bg-cyan-950 border border-cyan-500/30 text-cyan-300 rounded hover:bg-cyan-900 text-[6.5px]">Resolve: Bus 7</button>
                            </>
                          )}
                          {dialogue.parameter_needed === "relay_line" && (
                            <>
                              <button onClick={() => handleResolveDialogue("L1_4")} className="px-1.5 py-0.5 bg-cyan-950 border border-cyan-500/30 text-cyan-300 rounded hover:bg-cyan-900 text-[6.5px]">Resolve: L1_4</button>
                              <button onClick={() => handleResolveDialogue("L4_5")} className="px-1.5 py-0.5 bg-cyan-950 border border-cyan-500/30 text-cyan-300 rounded hover:bg-cyan-900 text-[6.5px]">Resolve: L4_5</button>
                            </>
                          )}
                          {dialogue.parameter_needed === "workflow_name" && (
                            <>
                              <button onClick={() => handleResolveDialogue("status check")} className="px-1.5 py-0.5 bg-cyan-950 border border-cyan-500/30 text-cyan-300 rounded hover:bg-cyan-900 text-[6.5px]">Resolve: Status Check</button>
                              <button onClick={() => handleResolveDialogue("shed load")} className="px-1.5 py-0.5 bg-cyan-950 border border-cyan-500/30 text-cyan-300 rounded hover:bg-cyan-900 text-[6.5px]">Resolve: Load Shed</button>
                            </>
                          )}
                          {dialogue.parameter_needed === "delay_sec" && (
                            <>
                              <button onClick={() => handleResolveDialogue("5")} className="px-1.5 py-0.5 bg-cyan-950 border border-cyan-500/30 text-cyan-300 rounded hover:bg-cyan-900 text-[6.5px]">Resolve: 5s</button>
                              <button onClick={() => handleResolveDialogue("10")} className="px-1.5 py-0.5 bg-cyan-950 border border-cyan-500/30 text-cyan-300 rounded hover:bg-cyan-900 text-[6.5px]">Resolve: 10s</button>
                            </>
                          )}
                        </div>

                        <div className="flex gap-1">
                          <input 
                            type="text" 
                            placeholder="Type resolution answer..."
                            value={clarifyAnswerText}
                            onChange={(e) => setClarifyAnswerText(e.target.value)}
                            onKeyDown={(e) => e.key === "Enter" && handleResolveDialogue(clarifyAnswerText)}
                            className="flex-1 bg-black/40 border border-scada-border/40 text-white rounded p-1 text-[7.5px] outline-none"
                          />
                          <button 
                            onClick={() => handleResolveDialogue(clarifyAnswerText)}
                            disabled={!clarifyAnswerText.trim()}
                            className="px-2 bg-amber-950 border border-amber-500/40 text-amber-400 rounded disabled:opacity-40 text-[7px]"
                          >
                            Submit
                          </button>
                        </div>
                      </div>
                    ) : (
                      <div className="text-[7px] text-scada-dimText italic text-center py-4 flex flex-col items-center gap-1">
                        <MessageSquare size={16} className="opacity-30" />
                        No dialogue ambiguity detected. Standing by...
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Tab 4: Workflows & Reminders */}
              {activeTab === "workflows" && (
                <div className="space-y-1.5">
                  {/* Latest Execution */}
                  <div className="bg-scada-bg/60 border border-scada-border/30 rounded p-1.5">
                    <div className="text-[7px] font-bold text-scada-dimText uppercase tracking-wider mb-1 flex justify-between">
                      <span>LATEST WORKFLOW EXECUTION</span>
                      {latestWf && (
                        <span className={`px-1 rounded text-[6.5px] ${
                          latestWf.status === "SUCCESS" ? "text-emerald-400 bg-emerald-950/40" :
                          latestWf.status === "RUNNING" ? "text-amber-400 bg-amber-950/40 animate-pulse" : "text-rose-400 bg-rose-950/40"
                        }`}>
                          {latestWf.status}
                        </span>
                      )}
                    </div>

                    {latestWf ? (
                      <div className="space-y-1">
                        <div className="flex justify-between text-[7px] border-b border-scada-border/10 pb-0.5">
                          <span className="text-scada-dimText font-bold">{latestWf.workflow_name}</span>
                          <span className="text-scada-dimText text-[6px]">{new Date(latestWf.timestamp).toLocaleTimeString()}</span>
                        </div>
                        {latestWf.error && (
                          <div className="text-[6.5px] text-rose-400 bg-rose-950/10 p-0.5 rounded italic">
                            Error: {latestWf.error}
                          </div>
                        )}
                        {/* Steps checklist */}
                        <div className="pt-1 space-y-0.5 text-[6.5px]">
                          {latestWf.steps.map((s: any, i: number) => (
                            <div key={i} className="flex justify-between items-center bg-black/10 px-1 py-0.5 rounded">
                              <span className="text-white flex items-center gap-1">
                                {s.status === "SUCCESS" && <CheckCircle2 size={7.5} className="text-emerald-400 shrink-0" />}
                                {s.status === "FAILED" && <XCircle size={7.5} className="text-rose-400 shrink-0" />}
                                {s.status === "PENDING" && <RefreshCw size={7.5} className="text-amber-400 shrink-0 animate-spin" />}
                                {s.step_name}
                              </span>
                              <span className={s.status === "SUCCESS" ? "text-emerald-400" : s.status === "FAILED" ? "text-rose-400" : "text-amber-400"}>
                                {s.status}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    ) : (
                      <div className="text-[6.5px] text-scada-dimText italic text-center py-2">
                        No workflows triggered yet.
                      </div>
                    )}
                  </div>

                  {/* Delayed Task queue & n8n Bridge */}
                  <div className="grid grid-cols-2 gap-1.5">
                    <div className="bg-scada-bg/40 border border-scada-border/30 rounded p-1.5 flex flex-col h-[75px] overflow-hidden">
                      <div className="text-[6.5px] font-bold text-scada-dimText uppercase tracking-wider mb-1 border-b border-scada-border/20 pb-0.5 flex justify-between shrink-0">
                        <span>DELAYED QUEUE</span>
                        <span className="text-white">({workflows.delayed_tasks_count})</span>
                      </div>
                      <div className="flex-1 overflow-y-auto space-y-1 scrollbar-thin text-[6px]">
                        {workflows.delayed_queue.length === 0 ? (
                          <div className="h-full flex items-center justify-center text-scada-dimText/40 italic">Queue empty</div>
                        ) : (
                          workflows.delayed_queue.map((q: any) => (
                            <div key={q.task_id} className="flex justify-between bg-black/10 p-0.5 rounded">
                              <span className="text-white truncate max-w-[50px]">{q.name}</span>
                              <span className="text-cyan-300">{q.time_remaining_sec}s</span>
                            </div>
                          ))
                        )}
                      </div>
                    </div>

                    <div className="bg-scada-bg/40 border border-scada-border/30 rounded p-1.5 flex flex-col h-[75px] overflow-hidden">
                      <div className="text-[6.5px] font-bold text-scada-dimText uppercase tracking-wider mb-1 border-b border-scada-border/20 pb-0.5 flex justify-between shrink-0">
                        <span>n8n WEBHOOKS</span>
                        <span className="text-white">({n8nBridge.active_retries_count} retries)</span>
                      </div>
                      <div className="flex-1 overflow-y-auto space-y-1 scrollbar-thin text-[6px]">
                        {n8nBridge.active_retries.length === 0 && n8nBridge.executions.length === 0 ? (
                          <div className="h-full flex items-center justify-center text-scada-dimText/40 italic">No webhook logs</div>
                        ) : (
                          <>
                            {n8nBridge.active_retries.map((r: any) => (
                              <div key={r.execution_id} className="bg-rose-950/20 border-l border-rose-500 p-0.5 rounded flex flex-col">
                                <div className="flex justify-between text-rose-300 font-bold">
                                  <span className="truncate max-w-[45px]">{r.webhook_name}</span>
                                  <span>R:{r.retry_count}</span>
                                </div>
                                <span className="text-[5.5px] text-white">Next retry in {r.seconds_until_next}s</span>
                              </div>
                            ))}
                            {n8nBridge.executions.slice(-3).reverse().map((e: any) => (
                              <div key={e.execution_id} className="bg-black/10 p-0.5 rounded flex justify-between text-scada-dimText">
                                <span className="truncate max-w-[50px]">{e.webhook_name}</span>
                                <span className={e.status === "SUCCESS" ? "text-emerald-400 font-bold" : "text-rose-400 font-bold"}>{e.status}</span>
                              </div>
                            ))}
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Tab 5: Presence & Health */}
              {activeTab === "presence" && (
                <div className="space-y-1.5">
                  {/* SVG Breathing Core and Pacing info */}
                  <div className="bg-scada-bg/70 border border-scada-border/30 rounded p-1.5 flex items-center gap-2">
                    <div className="w-[30%] shrink-0 flex items-center justify-center relative">
                      <svg viewBox="0 0 100 100" className="w-14 h-14 mx-auto select-none">
                        <defs>
                          <radialGradient id="pGlowC"><stop offset="0%" stopColor="#06b6d4" stopOpacity="0.8" /><stop offset="60%" stopColor="#8b5cf6" stopOpacity="0.3" /><stop offset="100%" stopColor="#020617" stopOpacity="0" /></radialGradient>
                        </defs>
                        <circle cx="50" cy="50" r={30 + localBreathingCoordinate * 8} fill="none" strokeWidth="1" strokeDasharray="3,3" opacity="0.3" style={{ stroke: state === "ERROR" ? "#f43f5e" : state === "THINKING" ? "#a855f7" : state === "RESPONDING" ? "#10b981" : "#06b6d4" }} />
                        <circle cx="50" cy="50" r={14 + localBreathingCoordinate * 3} fill="url(#pGlowC)" />
                        <circle cx="50" cy="50" r={6 + localBreathingCoordinate} fill={state === "ERROR" ? "#f43f5e" : state === "THINKING" ? "#a855f7" : state === "RESPONDING" ? "#10b981" : "#06b6d4"} />
                      </svg>
                    </div>
                    <div className="flex-1 text-[6.5px] space-y-0.5">
                      <div className="flex justify-between"><span className="text-scada-dimText">Attention Mode:</span><span className="text-white font-bold">{presence.attention_state}</span></div>
                      <div className="flex justify-between"><span className="text-scada-dimText">Breathing Freq:</span><span className="text-cyan-400 font-bold">{presence.breathing_frequency_hz} Hz</span></div>
                      <div className="flex justify-between">
                        <span className="text-scada-dimText">Calculated Pacing:</span>
                        <span className="text-emerald-400 font-bold">{getPacingDelayValue(emotion.assistant_mood, reasoning.grid_critical).toFixed(2)}s</span>
                      </div>
                      {reasoning.grid_critical && <div className="text-[5.5px] text-rose-400 font-bold animate-pulse">GRID stress: pacing delay bypassed.</div>}
                    </div>
                  </div>

                  {/* Adaptive Routines */}
                  <div className="bg-scada-bg/60 border border-scada-border/30 rounded p-1.5 flex flex-col h-[75px] overflow-hidden">
                    <div className="text-[7px] font-bold text-scada-dimText uppercase tracking-wider mb-1 border-b border-scada-border/20 pb-0.5 flex justify-between shrink-0">
                      <span>ADAPTIVE ROUTINES SUGGESTIONS</span>
                      <span className="text-white">Count: {routines.routines_count}</span>
                    </div>
                    <div className="flex-1 overflow-y-auto space-y-1 scrollbar-thin">
                      {routines.recommended_routines.length === 0 ? (
                        <div className="h-full flex items-center justify-center text-[7px] text-scada-dimText/40 italic">
                          No routine habits suggested yet.
                        </div>
                      ) : (
                        routines.recommended_routines.map((r: any, idx: number) => (
                          <div key={idx} className="bg-black/25 px-1 py-1 rounded border border-scada-border/10 text-[6.5px] flex flex-col gap-1">
                            <div className="flex justify-between">
                              <span className="text-white font-bold">{r.routine_type}</span>
                              <span className="text-scada-dimText">Freq: {r.frequency_per_hr}/hr</span>
                            </div>
                            <span className="text-white italic leading-tight">"{r.recommendation_message}"</span>
                            {!r.accepted ? (
                              <button
                                onClick={() => handleAcceptRoutine(r.routine_type)}
                                className="self-end px-1.5 py-0.5 bg-emerald-950 border border-emerald-500/30 text-emerald-400 rounded hover:bg-emerald-900 transition-colors"
                              >
                                Accept Recommendation
                              </button>
                            ) : (
                              <span className="self-end text-emerald-400 font-bold font-mono text-[5.8px]">ACCEPTED & RUNNING</span>
                            )}
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Simulation controls grid at bottom */}
            <div className="bg-scada-bg/70 border border-scada-border/30 rounded p-2 shrink-0">
              <div className="text-[7.5px] font-bold text-scada-dimText uppercase tracking-wider mb-1 flex items-center gap-1 border-b border-scada-border/20 pb-0.5">
                <Sliders size={8} className="text-amber-400 animate-pulse" />
                <span>Conversational Planning & Orchestration Simulation Console</span>
              </div>
              <div className="grid grid-cols-3 gap-1 pt-1.5">
                <button onClick={triggerAmbiguityClarification}
                  className="bg-cyan-950 hover:bg-cyan-900 border border-cyan-500/30 rounded py-1 text-[6.5px] text-cyan-300 font-bold transition-all hover:scale-102 flex flex-col items-center justify-center gap-0.5 leading-none">
                  <MessageSquare size={8} /> Simulate Ambiguity
                </button>
                <button onClick={triggerStreamingInterruption}
                  className="bg-rose-950 hover:bg-rose-900 border border-rose-500/30 rounded py-1 text-[6.5px] text-rose-300 font-bold transition-all hover:scale-102 flex flex-col items-center justify-center gap-0.5 leading-none">
                  <Volume2 size={8} /> Simulate Interruption
                </button>
                <button onClick={triggerChainedTaskPlan}
                  className="bg-blue-950 hover:bg-blue-900 border border-blue-500/30 rounded py-1 text-[6.5px] text-blue-300 font-bold transition-all hover:scale-102 flex flex-col items-center justify-center gap-0.5 leading-none">
                  <GitBranch size={8} /> Run Chained Plan
                </button>
                <button onClick={triggerDependencyFailure}
                  className="bg-amber-950 hover:bg-amber-900 border border-amber-500/30 rounded py-1 text-[6.5px] text-amber-300 font-bold transition-all hover:scale-102 flex flex-col items-center justify-center gap-0.5 leading-none">
                  <Clock size={8} /> {taskChains.active_chains.length > 0 ? "Trip Active Step" : "Sim Dependency Fail"}
                </button>
                <button onClick={triggerConfidenceGateBlock}
                  className="bg-rose-950 hover:bg-rose-900 border border-rose-500/30 rounded py-1 text-[6.5px] text-rose-300 font-bold transition-all hover:scale-102 flex flex-col items-center justify-center gap-0.5 leading-none">
                  <Shield size={8} /> Confidence Gate Block
                </button>
                <button onClick={triggerRunawayChain}
                  className="bg-emerald-950 hover:bg-emerald-900 border border-emerald-500/30 rounded py-1 text-[6.5px] text-emerald-300 font-bold transition-all hover:scale-102 flex flex-col items-center justify-center gap-0.5 leading-none">
                  <RotateCcw size={8} /> Runaway/Loop Block
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
