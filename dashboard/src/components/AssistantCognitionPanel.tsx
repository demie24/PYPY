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
  // Phase 9.6 props
  assistantPredictiveCoordination?: any | null;
  assistantPersistentMemory?: any | null;
  assistantPatternAwareness?: any | null;
  assistantWorkflowOptimizer?: any | null;
  assistantCrossSystemCoordination?: any | null;
  // Phase 9.7 props
  assistantEdgeAwareness?: any | null;
  assistantRelayHealth?: any | null;
  assistantTelemetryCorrelation?: any | null;
  assistantSynchronizationAwareness?: any | null;
  assistantCyberPhysicalReasoning?: any | null;
  // Phase 9.8 props
  assistantAgentCoordination?: any | null;
  assistantTelemetryAgent?: any | null;
  assistantRelayAgent?: any | null;
  assistantWorkflowAgent?: any | null;
  assistantSecurityAgent?: any | null;
  // Phase 9.9 props
  assistantSwarmCoordination?: any | null;
  assistantFederatedMemory?: any | null;
  assistantDistributedConsensus?: any | null;
  assistantEdgeMesh?: any | null;
  assistantSwarmAnomalyFusion?: any | null;
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
  assistantOrchestrationPlanner,
  // Phase 9.6 destruct
  assistantPredictiveCoordination,
  assistantPersistentMemory,
  assistantPatternAwareness,
  assistantWorkflowOptimizer,
  assistantCrossSystemCoordination,
  // Phase 9.7 destruct
  assistantEdgeAwareness,
  assistantRelayHealth,
  assistantTelemetryCorrelation,
  assistantSynchronizationAwareness,
  assistantCyberPhysicalReasoning,
  // Phase 9.8 destruct
  assistantAgentCoordination,
  assistantTelemetryAgent,
  assistantRelayAgent,
  assistantWorkflowAgent,
  assistantSecurityAgent,
  // Phase 9.9 destruct
  assistantSwarmCoordination,
  assistantFederatedMemory,
  assistantDistributedConsensus,
  assistantEdgeMesh,
  assistantSwarmAnomalyFusion
}) => {

  const [chatText, setChatText] = useState("");
  const [clarifyAnswerText, setClarifyAnswerText] = useState("");
  const [isListeningVoice, setIsListeningVoice] = useState(false);
  const [voiceSimProgress, setVoiceSimProgress] = useState(0);
  const [activeTab, setActiveTab] = useState<"reasoning" | "planning" | "dialogue" | "workflows" | "presence" | "autonomy" | "cyberPhysical" | "multiAgent" | "swarm">("reasoning");
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

  // Phase 9.6 defaults
  const predictive = assistantPredictiveCoordination ?? { latency_history: [], forecasts: [], suggestions: [], workflow_timings: {} };
  const persistentMemory = assistantPersistentMemory ?? { total_interactions: 0, recurring_count: 0, recurring_actions: [], latest_interactions: [] };
  const patterns = assistantPatternAwareness ?? { active_patterns_count: 0, active_patterns: [], voltage_oscillations_count: 0, consecutive_failures: {} };
  const optimizer = assistantWorkflowOptimizer ?? { recommendations_count: 0, recommendations: [], active_optimizations_count: 0, active_optimizations: [] };
  const coordination = assistantCrossSystemCoordination ?? { sync_state: "SYNCED", drift_sec: 0, conflict_logs_count: 0, conflict_logs: [], last_sync_timestamp: 0 };

  // Phase 9.7 defaults
  const edgeAwareness = assistantEdgeAwareness ?? { nodes: {}, anomalies: {}, worst_node: null, worst_node_health: 1.0, average_latency_ms: 0.0, distributed_anomaly_count: 0 };
  const relayHealth = assistantRelayHealth ?? { breakers: {}, unstable_breakers: [], timing_anomalies: [], wear_report: {}, recommendations: [], unstable_count: 0 };
  const telemetryCorrelation = assistantTelemetryCorrelation ?? { high_correlations: [], cascades: [], linkage_logs: [], correlation_matrix_size: 0 };
  const syncAwareness = assistantSynchronizationAwareness ?? { node_sync_states: {}, skewed_nodes: [], critical_skewed_nodes: [], max_drift_node: null, max_drift_ms: 0.0, warnings: [], skewed_count: 0 };
  const cpReasoning = assistantCyberPhysicalReasoning ?? { severity_score: 0.0, severity_level: "LOW", suggestions: [], reasoning_logs: ["Reasoning engine stand-by."] };

  // Phase 9.8 defaults
  const agentCoord = assistantAgentCoordination ?? { status: "NOMINAL", consensus_state: "IDLE", consensus_score: 1.0, delegation_chain: [], inter_agent_logs: [] };
  const telAgent = assistantTelemetryAgent ?? agentCoord.telemetry_agent ?? { status: "NOMINAL", confidence_score: 1.0, anomalies: [], drift_summary: {}, rolling_averages: {}, event_priority_matrix: {} };
  const relAgent = assistantRelayAgent ?? agentCoord.relay_agent ?? { status: "NOMINAL", confidence_score: 1.0, relay_anomalies: [], stabilization_recommendations: [], breaker_oscillations: [], timing_latencies: {} };
  const wfAgent = assistantWorkflowAgent ?? agentCoord.workflow_agent ?? { status: "NOMINAL", confidence_score: 1.0, workflow_runs: {}, recovery_plans: [], stalled_chains: [], escalations: [] };
  const secAgent = assistantSecurityAgent ?? agentCoord.security_agent ?? { status: "NOMINAL", confidence_score: 1.0, threat_alerts: [], safety_recommendations: [], threat_scores: {} };

  // Phase 9.9 defaults
  const swarmCoord = assistantSwarmCoordination ?? { status: "NOMINAL", coordination_chain: [], coordination_logs: [], simulation_mode: null };
  const fedMemory = assistantFederatedMemory ?? swarmCoord.federated_memory ?? { status: "NOMINAL", sync_status: "SYNCED", lamport_clock: 0, sync_count: 0, conflict_logs: [], shared_memory: {} };
  const distConsensus = assistantDistributedConsensus ?? swarmCoord.distributed_consensus ?? { status: "NOMINAL", consensus_state: "IDLE", consensus_score: 1.0, consensus_drift: 0.0, votes: {}, drift_history: [], consensus_logs: [] };
  const edgeMesh = assistantEdgeMesh ?? swarmCoord.edge_mesh ?? { status: "NOMINAL", mesh_status: "CONNECTED", links: [], partition_failures: [], cascade_risk_paths: [], relay_groups: {} };
  const swarmAnomalyFusion = assistantSwarmAnomalyFusion ?? swarmCoord.anomaly_fusion ?? { status: "NOMINAL", fused_anomalies: [], swarm_threat_score: 0.0, priority_queue: [], correlation_matrix: {} };




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

  const handleApproveOptimization = (workflowName: string) => {
    onSendControl({
      topic: "assistant/workflow_optimizer_simulation",
      payload: { action: "approve", workflow_name: workflowName }
    });
  };
  // Phase 9.7 simulation triggers
  const triggerRelayInstability = () => {
    onSendControl({
      topic: "assistant/relay_health_simulation",
      payload: { action: "set_wear", breaker_id: "L3_6", switch_count: 172 }
    });
  };

  const triggerSyncDriftSpikes = () => {
    onSendControl({
      topic: "assistant/synchronization_awareness_simulation",
      payload: { action: "trigger_drift", node_id: "esp32_zone3", drift_sec: 0.085 }
    });
  };

  const triggerTelemetryCorrelationAnomalies = () => {
    onSendControl({
      topic: "assistant/telemetry_correlation_simulation",
      payload: {
        action: "inject_correlation",
        snapshot: {
          bus_5_v: 0.82,
          line_L4_5_load: 108.5,
          breaker_L4_5: 0.0
        }
      }
    });
  };

  const triggerCascadingNodeFailures = () => {
    onSendControl({
      topic: "assistant/edge_awareness_simulation",
      payload: { action: "set_health", node_id: "esp32_zone1", latency_ms: 185.0, packet_loss_pct: 12.0, online: true, drift_sec: 0.04 }
    });
    setTimeout(() => {
      onSendControl({
        topic: "assistant/edge_awareness_simulation",
        payload: { action: "set_health", node_id: "esp32_zone2", latency_ms: 220.0, packet_loss_pct: 18.0, online: true, drift_sec: 0.06 }
      });
    }, 100);
  };

  const triggerDistributedTimingSkew = () => {
    onSendControl({
      topic: "assistant/synchronization_awareness_simulation",
      payload: { action: "trigger_drift", node_id: "esp32_zone1", drift_sec: 0.035 }
    });
    onSendControl({
      topic: "assistant/synchronization_awareness_simulation",
      payload: { action: "trigger_drift", node_id: "esp32_zone2", drift_sec: 0.042 }
    });
    onSendControl({
      topic: "assistant/synchronization_awareness_simulation",
      payload: { action: "trigger_drift", node_id: "esp32_zone3", drift_sec: 0.049 }
    });
  };

  const triggerRelayOscillationBehavior = () => {
    onSendControl({
      topic: "assistant/relay_health_simulation",
      payload: { action: "trigger_oscillation", breaker_id: "L3_6" }
    });
  };

  const triggerEdgeNodeDegradationReplay = () => {
    onSendControl({
      topic: "assistant/edge_awareness_simulation",
      payload: { action: "set_health", node_id: "esp32_zone3", latency_ms: 280.0, packet_loss_pct: 25.0, online: true, drift_sec: 0.07 }
    });
  };

  const triggerClearCPReasoning = () => {
    onSendControl({
      topic: "assistant/edge_awareness_simulation",
      payload: { action: "reset" }
    });
    onSendControl({
      topic: "assistant/relay_health_simulation",
      payload: { action: "reset" }
    });
    onSendControl({
      topic: "assistant/telemetry_correlation_simulation",
      payload: { action: "reset" }
    });
    onSendControl({
      topic: "assistant/synchronization_awareness_simulation",
      payload: { action: "reset" }
    });
  };

  const triggerRecurringAnomaly = () => {
    onSendControl({
      topic: "assistant/predictive_coordination_simulation",
      payload: { action: "add_latency", latency: 55.0 }
    });
    setTimeout(() => onSendControl({
      topic: "assistant/predictive_coordination_simulation",
      payload: { action: "add_latency", latency: 75.0 }
    }), 100);
    setTimeout(() => onSendControl({
      topic: "assistant/predictive_coordination_simulation",
      payload: { action: "add_latency", latency: 95.0 }
    }), 200);
  };

  const triggerRepeatedWorkflowFailure = () => {
    onSendControl({
      topic: "assistant/workflow_trigger",
      payload: { action: "execute", workflow_name: "system_status_check" }
    });
    setTimeout(() => {
      onSendControl({
        topic: "assistant/pattern_awareness_simulation",
        payload: { action: "analyze" }
      });
    }, 100);
  };

  const triggerOrchestrationDrift = () => {
    onSendControl({
      topic: "assistant/predictive_coordination_simulation",
      payload: { action: "add_latency", latency: 185.0 }
    });
    setTimeout(() => {
      onSendControl({
        topic: "assistant/cross_system_coordination_simulation",
        payload: { action: "tick" }
      });
    }, 100);
  };

  const triggerConfidenceInstability = () => {
    onSendControl({
      topic: "assistant/orchestration_simulation",
      payload: { action: "set_safety", confidence_threshold: 0.95 }
    });
  };

  const triggerClearMemory = () => {
    onSendControl({
      topic: "assistant/persistent_memory_simulation",
      payload: { action: "clear" }
    });
  };

  const triggerOptimizationConflict = () => {
    onSendControl({
      topic: "assistant/proactive_trigger",
      payload: { threat_score: 10.0, latency_ms: 25.0 }
    });
    setTimeout(() => {
      onSendControl({
        topic: "assistant/proactive_trigger",
        payload: { threat_score: 85.0, latency_ms: 180.0 }
      });
      onSendControl({
        topic: "assistant/cross_system_coordination_simulation",
        payload: { action: "tick" }
      });
    }, 200);
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
            <button
              onClick={() => setActiveTab("autonomy")}
              className={`flex-1 py-1.5 text-[7.5px] uppercase tracking-wider font-bold text-center border-b-2 transition-all flex items-center justify-center gap-0.5 ${
                activeTab === "autonomy" ? "border-indigo-500 text-white bg-indigo-500/10" : "border-transparent text-scada-dimText hover:text-white"
              }`}
            >
              <Sliders size={9} />
              Autonomy
            </button>
            <button
              onClick={() => setActiveTab("cyberPhysical")}
              className={`flex-1 py-1.5 text-[7.5px] uppercase tracking-wider font-bold text-center border-b-2 transition-all flex items-center justify-center gap-0.5 ${
                activeTab === "cyberPhysical" ? "border-rose-500 text-white bg-rose-500/10" : "border-transparent text-scada-dimText hover:text-white"
              }`}
            >
              <Activity size={9} />
              CP-Aware
            </button>
            <button
              onClick={() => setActiveTab("multiAgent")}
              className={`flex-1 py-1.5 text-[7.5px] uppercase tracking-wider font-bold text-center border-b-2 transition-all flex items-center justify-center gap-0.5 ${
                activeTab === "multiAgent" ? "border-amber-500 text-white bg-amber-500/10" : "border-transparent text-scada-dimText hover:text-white"
              }`}
            >
              <Cpu size={9} />
              Multi-Agent
            </button>
            <button
              onClick={() => setActiveTab("swarm")}
              className={`flex-1 py-1.5 text-[7.5px] uppercase tracking-wider font-bold text-center border-b-2 transition-all flex items-center justify-center gap-0.5 ${
                activeTab === "swarm" ? "border-fuchsia-500 text-white bg-fuchsia-500/10" : "border-transparent text-scada-dimText hover:text-white"
              }`}
            >
              <Bot size={9} />
              Swarm
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

              {/* Tab 6: Autonomy */}
              {activeTab === "autonomy" && (
                <div className="space-y-1.5">
                  {/* Predictive Coordination */}
                  <div className="bg-scada-bg/60 border border-scada-border/30 rounded p-1.5">
                    <div className="text-[7px] font-bold text-scada-dimText uppercase tracking-wider mb-1 border-b border-scada-border/20 pb-0.5 flex justify-between shrink-0">
                      <span>Predictive Coordination & Trends</span>
                      <span className="text-cyan-400 font-bold">Sync: {coordination.sync_state}</span>
                    </div>
                    <div className="text-[6.5px] space-y-1">
                      <div className="flex justify-between">
                        <span className="text-scada-dimText">Clock Drift Offset:</span>
                        <span className={coordination.drift_sec > 0 ? "text-amber-400 font-bold animate-pulse" : "text-emerald-400 font-bold"}>
                          {coordination.drift_sec > 0 ? `+${coordination.drift_sec}s` : "0.00s (Stable)"}
                        </span>
                      </div>
                      
                      {/* Forecasts */}
                      <div className="mt-1">
                        <span className="text-scada-dimText font-bold">Recurring Forecasts:</span>
                        {predictive.forecasts && predictive.forecasts.length > 0 ? (
                          <div className="space-y-1 mt-1">
                            {predictive.forecasts.map((f: any, idx: number) => (
                              <div key={idx} className="bg-black/30 p-1 rounded border border-scada-border/20 flex flex-col">
                                <div className="flex justify-between font-bold text-white">
                                  <span>{f.category}</span>
                                  <span className="text-yellow-400">{(f.confidence * 100).toFixed(0)}% Conf</span>
                                </div>
                                <span className="text-scada-dimText mt-0.5">{f.description}</span>
                                <span className="text-cyan-400 text-[5.8px] mt-0.5">Horizon: {f.time_horizon_sec}s | Projected: {f.predicted_value.toFixed(1)}</span>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <div className="text-scada-dimText/40 italic mt-0.5 pl-1">No upcoming anomalies forecasted.</div>
                        )}
                      </div>

                      {/* Suggestions */}
                      <div className="mt-1">
                        <span className="text-scada-dimText font-bold">Coordination Suggestions:</span>
                        {predictive.suggestions && predictive.suggestions.length > 0 ? (
                          <div className="space-y-1 mt-1">
                            {predictive.suggestions.map((s: any, idx: number) => (
                              <div key={idx} className="bg-cyan-950/40 p-1.5 rounded border border-cyan-800/35 flex flex-col">
                                <span className="font-bold text-cyan-300">{s.title}</span>
                                <span className="text-white text-[5.8px] leading-tight mt-0.5">{s.description}</span>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <div className="text-scada-dimText/40 italic mt-0.5 pl-1">No active suggestions.</div>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Persistent Routine Memory & Pattern Awareness */}
                  <div className="grid grid-cols-2 gap-1.5">
                    <div className="bg-scada-bg/60 border border-scada-border/30 rounded p-1.5 flex flex-col overflow-hidden h-[95px]">
                      <div className="text-[7px] font-bold text-scada-dimText uppercase tracking-wider mb-1 border-b border-scada-border/20 pb-0.5 shrink-0">
                        Persistent Memory
                      </div>
                      <div className="flex-1 overflow-y-auto space-y-1 scrollbar-thin">
                        <div className="text-[6px] text-scada-dimText">Total interactions stored: {persistentMemory.total_interactions}</div>
                        {persistentMemory.recurring_actions && persistentMemory.recurring_actions.length > 0 ? (
                          persistentMemory.recurring_actions.map((act: any, idx: number) => (
                            <div key={idx} className="bg-black/25 px-1 py-0.5 rounded border border-scada-border/10 text-[5.8px] leading-none flex justify-between">
                              <span className="text-white font-bold max-w-[55%] truncate">{act.action}</span>
                              <span className="text-cyan-400 font-mono">Count: {act.count} ({act.dominant_bin})</span>
                            </div>
                          ))
                        ) : (
                          <div className="text-scada-dimText/30 italic text-[6px] h-full flex items-center justify-center">No recurring routine habits stored.</div>
                        )}
                      </div>
                    </div>

                    <div className="bg-scada-bg/60 border border-scada-border/30 rounded p-1.5 flex flex-col overflow-hidden h-[95px]">
                      <div className="text-[7px] font-bold text-scada-dimText uppercase tracking-wider mb-1 border-b border-scada-border/20 pb-0.5 shrink-0">
                        Pattern Confidence
                      </div>
                      <div className="flex-1 overflow-y-auto space-y-1 scrollbar-thin">
                        {patterns.active_patterns && patterns.active_patterns.length > 0 ? (
                          patterns.active_patterns.map((pat: any, idx: number) => (
                            <div key={idx} className="bg-black/25 p-1 rounded border border-scada-border/15 text-[5.8px] leading-tight flex flex-col">
                              <div className="flex justify-between font-bold">
                                <span className="text-white truncate max-w-[55%]">{pat.pattern_id}</span>
                                <span className="text-amber-400">{(pat.confidence_score * 100).toFixed(0)}% Conf</span>
                              </div>
                              <span className="text-scada-dimText mt-0.5">{pat.description}</span>
                            </div>
                          ))
                        ) : (
                          <div className="text-scada-dimText/30 italic text-[6px] h-full flex items-center justify-center">No anomaly patterns identified.</div>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Adaptive Workflow Optimizer */}
                  <div className="bg-scada-bg/60 border border-scada-border/30 rounded p-1.5">
                    <div className="text-[7px] font-bold text-scada-dimText uppercase tracking-wider mb-1 border-b border-scada-border/20 pb-0.5 shrink-0">
                      Adaptive Timing Optimization Recommendations
                    </div>
                    <div className="space-y-1 mt-1 max-h-[75px] overflow-y-auto scrollbar-thin">
                      {optimizer.recommendations && optimizer.recommendations.length > 0 ? (
                        optimizer.recommendations.map((r: any, idx: number) => (
                          <div key={idx} className="bg-black/25 p-1 rounded border border-scada-border/20 text-[6.5px] flex items-center justify-between gap-2">
                            <div className="flex flex-col gap-0.5 flex-1 leading-tight">
                              <div className="flex gap-1.5 font-bold">
                                <span className="text-white">{r.workflow_name}</span>
                                <span className="text-amber-400">{r.optimization_type}</span>
                              </div>
                              <span className="text-scada-dimText">{r.description}</span>
                            </div>
                            {r.status === "PENDING_APPROVAL" ? (
                              <button
                                onClick={() => handleApproveOptimization(r.workflow_name)}
                                className="px-1.5 py-0.5 bg-emerald-950 border border-emerald-500/30 text-emerald-400 rounded font-bold hover:bg-emerald-900 transition-colors text-[5.8px]"
                              >
                                Approve
                              </button>
                            ) : r.status === "APPROVED" ? (
                              <span className="text-emerald-400 font-bold font-mono text-[5.8px]">APPLIED</span>
                            ) : (
                              <span className="text-rose-400 font-bold font-mono text-[5.8px]">{r.status}</span>
                            )}
                          </div>
                        ))
                      ) : (
                        <div className="text-scada-dimText/40 italic text-[6.5px] pl-1">No timing optimizations recommended.</div>
                      )}
                    </div>
                  </div>

                  {/* Conflict Prevention Log */}
                  {coordination.conflict_logs && coordination.conflict_logs.length > 0 && (
                    <div className="bg-rose-950/20 border border-rose-800/30 rounded p-1.5 shrink-0">
                      <div className="text-[7px] font-bold text-rose-400 uppercase tracking-wider mb-1 flex items-center gap-1">
                        <AlertTriangle size={8} className="animate-pulse" />
                        <span>Conflict Prevention & Safety Override Logs</span>
                      </div>
                      <div className="space-y-0.5 max-h-[40px] overflow-y-auto scrollbar-thin text-[5.8px] leading-tight font-mono text-rose-300">
                        {coordination.conflict_logs.map((log: string, idx: number) => (
                          <div key={idx} className="border-b border-rose-900/10 pb-0.5">
                            {log}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Tab 7: Cyber-Physical Awareness (Phase 9.7) */}
              {activeTab === "cyberPhysical" && (
                <div className="space-y-1.5">
                  {/* Cyber-Physical Severity Panel */}
                  <div className="bg-scada-bg/60 border border-scada-border/30 rounded p-1.5">
                    <div className="text-[7.5px] font-bold text-scada-dimText uppercase tracking-wider mb-1 border-b border-scada-border/20 pb-0.5 flex justify-between shrink-0">
                      <span>Cyber-Physical State Analysis</span>
                      <span className={cpReasoning.severity_level === "CRITICAL" || cpReasoning.severity_level === "HIGH" ? "text-rose-500 font-bold animate-pulse" : "text-cyan-400 font-bold"}>
                        {cpReasoning.severity_level} (Score: {cpReasoning.severity_score.toFixed(1)})
                      </span>
                    </div>
                    <div className="grid grid-cols-2 gap-1.5 mt-1 shrink-0">
                      <div className="bg-black/30 p-1.5 rounded border border-scada-border/25 flex flex-col justify-center items-center">
                        <span className="text-[5.8px] text-scada-dimText uppercase tracking-wider">Average Latency</span>
                        <span className="text-white font-bold font-mono text-[9px] mt-0.5">{edgeAwareness.average_latency_ms.toFixed(1)}ms</span>
                      </div>
                      <div className="bg-black/30 p-1.5 rounded border border-scada-border/25 flex flex-col justify-center items-center">
                        <span className="text-[5.8px] text-scada-dimText uppercase tracking-wider">Timing Skews</span>
                        <span className="text-white font-bold font-mono text-[9px] mt-0.5">{syncAwareness.skewed_count} Nodes</span>
                      </div>
                    </div>

                    {/* Recommendations Checklist */}
                    <div className="mt-1">
                      <span className="text-scada-dimText font-bold text-[6.5px]">CP Advisory Recommendations:</span>
                      {cpReasoning.suggestions && cpReasoning.suggestions.length > 0 ? (
                        <div className="space-y-1 mt-1">
                          {cpReasoning.suggestions.map((s: any, idx: number) => (
                            <div key={idx} className="bg-black/20 p-1.5 rounded border border-scada-border/15 flex items-center justify-between text-[6px]">
                              <div className="flex flex-col leading-tight">
                                <span className={`font-bold ${s.severity === "CRITICAL" ? "text-rose-400" : s.severity === "HIGH" ? "text-amber-400" : "text-cyan-400"}`}>{s.action} ({s.target})</span>
                                <span className="text-white mt-0.5">{s.description}</span>
                              </div>
                              {s.severity === "BLOCKED" ? (
                                <span className="text-rose-500 font-bold text-[5.5px] uppercase">BLOCKED</span>
                              ) : (
                                <span className="text-emerald-400 font-bold text-[5.5px] uppercase">ADVISORY</span>
                              )}
                            </div>
                          ))}
                        </div>
                      ) : (
                        <div className="text-emerald-400 italic text-[6px] pl-1 mt-0.5">Grid state is nominal. No mitigation required.</div>
                      )}
                    </div>
                  </div>

                  {/* Edge Nodes & Relays */}
                  <div className="grid grid-cols-2 gap-1.5 h-[115px]">
                    {/* Edge Nodes stability */}
                    <div className="bg-scada-bg/60 border border-scada-border/30 rounded p-1.5 flex flex-col overflow-hidden">
                      <span className="text-[7px] font-bold text-scada-dimText uppercase tracking-wider mb-1 border-b border-scada-border/20 pb-0.5 shrink-0 flex justify-between">
                        <span>Edge Node Status</span>
                        {edgeAwareness.worst_node && (
                          <span className="text-rose-400 text-[5.8px]">Worst: {edgeAwareness.worst_node}</span>
                        )}
                      </span>
                      <div className="flex-1 overflow-y-auto space-y-1 scrollbar-thin text-[5.8px] leading-tight">
                        {edgeAwareness.nodes && Object.keys(edgeAwareness.nodes).map((key) => {
                          const val = edgeAwareness.nodes[key];
                          return (
                            <div key={key} className="bg-black/25 px-1 py-0.5 rounded border border-scada-border/10 flex justify-between">
                              <span className="text-white font-bold">{key}</span>
                              <div className="flex gap-1.5 font-mono">
                                <span className={val.online ? "text-emerald-400" : "text-rose-400"}>{val.online ? "ON" : "OFF"}</span>
                                <span className="text-cyan-400">{val.latency_ms.toFixed(0)}ms</span>
                                <span className={Math.abs(val.drift_sec) > 0.025 ? "text-rose-400" : "text-emerald-400"}>{(val.drift_sec * 1000).toFixed(0)}ms</span>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>

                    {/* Relays health */}
                    <div className="bg-scada-bg/60 border border-scada-border/30 rounded p-1.5 flex flex-col overflow-hidden">
                      <span className="text-[7px] font-bold text-scada-dimText uppercase tracking-wider mb-1 border-b border-scada-border/20 pb-0.5 shrink-0 flex justify-between">
                        <span>Relay Breaker Health</span>
                        {relayHealth.unstable_count > 0 && (
                          <span className="text-rose-400 animate-pulse text-[5.8px]">Unstable: {relayHealth.unstable_count}</span>
                        )}
                      </span>
                      <div className="flex-1 overflow-y-auto space-y-1 scrollbar-thin text-[5.8px] leading-tight">
                        {relayHealth.breakers && Object.keys(relayHealth.breakers).map((key) => {
                          const val = relayHealth.breakers[key];
                          return (
                            <div key={key} className="bg-black/25 px-1.5 py-0.5 rounded border border-scada-border/10 flex flex-col">
                              <div className="flex justify-between font-bold">
                                <span className="text-white">{key}</span>
                                <span className={val.unstable ? "text-rose-400 font-bold" : "text-cyan-400"}>{val.state}</span>
                              </div>
                              <div className="flex justify-between text-[5.2px] text-scada-dimText font-mono mt-0.5">
                                <span>Wear: {val.wear_pct.toFixed(0)}%</span>
                                <span className={val.timing_ms > 120 ? "text-rose-400" : "text-emerald-400"}>{val.timing_ms.toFixed(0)}ms</span>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  </div>

                  {/* Telemetry Correlation Mapping & Sync Skew */}
                  <div className="bg-scada-bg/60 border border-scada-border/30 rounded p-1.5 h-[110px] flex flex-col overflow-hidden">
                    <span className="text-[7px] font-bold text-scada-dimText uppercase tracking-wider mb-1 border-b border-scada-border/20 pb-0.5 shrink-0">
                      Telemetry Correlations & Skew Warnings
                    </span>
                    <div className="flex-1 grid grid-cols-2 gap-1.5 overflow-hidden">
                      {/* Correlations & Cascades */}
                      <div className="overflow-y-auto space-y-1 scrollbar-thin text-[5.8px] leading-tight">
                        <span className="text-[5.5px] font-bold text-scada-dimText uppercase">High Correlation Pairs</span>
                        {telemetryCorrelation.high_correlations && telemetryCorrelation.high_correlations.length > 0 ? (
                          telemetryCorrelation.high_correlations.map((c: any, idx: number) => (
                            <div key={idx} className="bg-black/25 px-1 py-0.5 rounded border border-scada-border/10 flex justify-between font-mono">
                              <span className="text-white truncate max-w-[70%]">{c.var1.replace("_load","").replace("_v","")} ↔ {c.var2.replace("_load","").replace("_v","")}</span>
                              <span className="text-yellow-400">{c.correlation > 0 ? `+${c.correlation.toFixed(2)}` : c.correlation.toFixed(2)}</span>
                            </div>
                          ))
                        ) : (
                          <div className="text-scada-dimText/40 italic">Waiting for correlation dataset...</div>
                        )}

                        {telemetryCorrelation.cascades && telemetryCorrelation.cascades.length > 0 && (
                          <div className="mt-1 space-y-0.5">
                            <span className="text-[5.5px] font-bold text-rose-400 uppercase">Cascading Links</span>
                            {telemetryCorrelation.cascades.map((c: any, idx: number) => (
                              <div key={idx} className="bg-rose-950/20 px-1 py-0.5 rounded border border-rose-900/30 flex justify-between text-rose-300 font-mono">
                                <span>{c.cause.replace("breaker_","")} → {c.effect.replace("bus_","").replace("_v","")}</span>
                                <span>{(c.linkage_score * 100).toFixed(0)}% Link</span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>

                      {/* Sync Warnings & Skews */}
                      <div className="overflow-y-auto space-y-1 scrollbar-thin text-[5.8px] leading-tight">
                        <span className="text-[5.5px] font-bold text-scada-dimText uppercase">Clock Sync & Timing Warnings</span>
                        {syncAwareness.warnings && syncAwareness.warnings.length > 0 ? (
                          syncAwareness.warnings.map((w: string, idx: number) => (
                            <div key={idx} className={`p-1 rounded border leading-tight ${w.includes("CRITICAL") ? "bg-rose-950/20 border-rose-900/30 text-rose-300" : "bg-amber-950/20 border-amber-900/30 text-amber-300"}`}>
                              {w.replace("CLOCK_SKEW_CRITICAL: ", "").replace("CLOCK_SKEW_WARNING: ", "")}
                            </div>
                          ))
                        ) : (
                          <div className="text-emerald-400 italic">Timing synchronization is locked and in-sync.</div>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Reasoning Logs */}
                  {cpReasoning.reasoning_logs && cpReasoning.reasoning_logs.length > 0 && (
                    <div className="bg-black/30 border border-scada-border/20 rounded p-1.5 shrink-0 flex flex-col h-[70px] overflow-hidden">
                      <span className="text-[7px] font-bold text-scada-dimText uppercase tracking-wider mb-1 border-b border-scada-border/10 pb-0.5 shrink-0 flex items-center gap-1">
                        <Terminal size={8} className="text-purple-400 animate-pulse" />
                        <span>Cognitive Reasoning Engine Trace</span>
                      </span>
                      <div className="flex-1 overflow-y-auto space-y-0.5 text-[5.8px] leading-tight font-mono text-purple-300 scrollbar-thin">
                        {cpReasoning.reasoning_logs.map((log: string, idx: number) => (
                          <div key={idx} className="border-b border-purple-900/5 pb-0.5">
                            {log}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Tab 8: Multi-Agent Coordination (Phase 9.8) */}
              {activeTab === "multiAgent" && (
                <div className="space-y-1.5">
                  {/* Coordinator & Consensus Gauge */}
                  <div className="bg-scada-bg/60 border border-scada-border/30 rounded p-1.5">
                    <div className="text-[7.5px] font-bold text-scada-dimText uppercase tracking-wider mb-1 border-b border-scada-border/20 pb-0.5 flex justify-between shrink-0">
                      <span className="flex items-center gap-1"><Cpu size={9} className="text-amber-400" /> Multi-Agent Coordinator</span>
                      <span className={`px-1 rounded text-[6px] font-bold uppercase ${
                        agentCoord.status === "CRITICAL" ? "bg-rose-950 text-rose-400" :
                        agentCoord.status === "LOOP_PREVENTED" ? "bg-red-950 text-red-400 animate-bounce" :
                        agentCoord.status === "DEGRADED" ? "bg-amber-950 text-amber-400" : "bg-emerald-950 text-emerald-400"
                      }`}>
                        {agentCoord.status}
                      </span>
                    </div>

                    <div className="grid grid-cols-2 gap-1.5 mt-1 text-[6.5px] shrink-0">
                      {/* Consensus Indicator */}
                      <div className="bg-black/30 p-1.5 rounded border border-scada-border/15 flex flex-col justify-between">
                        <div>
                          <div className="flex justify-between font-bold">
                            <span className="text-scada-dimText">Consensus:</span>
                            <span className={`font-mono ${
                              agentCoord.consensus_state === "APPROVED" ? "text-emerald-400" :
                              agentCoord.consensus_state.startsWith("BLOCKED") ? "text-rose-400 font-bold" : "text-cyan-400"
                            }`}>{agentCoord.consensus_state}</span>
                          </div>
                          <div className="flex justify-between mt-0.5">
                            <span className="text-scada-dimText">Score:</span>
                            <span className="text-white font-mono">{agentCoord.consensus_score.toFixed(2)} (Min: 0.75)</span>
                          </div>
                        </div>
                        <div className="w-full bg-black/40 h-1.5 rounded-full overflow-hidden border border-scada-border/10 mt-1">
                          <div 
                            className={`h-full transition-all duration-500 ${
                              agentCoord.consensus_score >= 0.75 ? "bg-emerald-500" : "bg-rose-500"
                            }`}
                            style={{ width: `${agentCoord.consensus_score * 100}%` }}
                          />
                        </div>
                      </div>

                      {/* Sync Timeline & Drift */}
                      <div className="bg-black/30 p-1.5 rounded border border-scada-border/15 flex flex-col justify-between font-mono text-[6px]">
                        <div>
                          <span className="text-scada-dimText font-bold">Timeline Sync:</span>
                          <div className="flex justify-between mt-0.5">
                            <span>Telemetry Anomaly:</span>
                            <span className={telAgent.anomalies?.length > 0 ? "text-rose-400 font-bold" : "text-emerald-400"}>
                              {telAgent.anomalies?.length > 0 ? "DETECTED" : "NOMINAL"}
                            </span>
                          </div>
                          <div className="flex justify-between">
                            <span>Security Alerts:</span>
                            <span className={secAgent.threat_alerts?.length > 0 ? "text-rose-400 font-bold animate-pulse" : "text-emerald-400"}>
                              {secAgent.threat_alerts?.length > 0 ? "ALERT" : "NOMINAL"}
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Active Agent Graph (4 agents) */}
                  <div className="bg-scada-bg/60 border border-scada-border/30 rounded p-1.5">
                    <div className="text-[7.5px] font-bold text-scada-dimText uppercase tracking-wider mb-1.5 border-b border-scada-border/20 pb-0.5 shrink-0">
                      Active Agent Graph & Statuses
                    </div>
                    <div className="grid grid-cols-4 gap-1">
                      {/* Telemetry Agent Card */}
                      <div className="bg-black/25 border border-scada-border/15 p-1 rounded flex flex-col justify-between text-[6px] h-[55px]">
                        <div>
                          <span className="font-bold text-cyan-400 block truncate">TelemetryAgent</span>
                          <span className="text-[5.5px] text-scada-dimText font-mono block mt-0.5">Status: <strong className="text-white">{telAgent.status.replace("_ANOMALY","")}</strong></span>
                        </div>
                        <div className="mt-1 border-t border-scada-border/10 pt-0.5 font-mono text-[5.2px] flex justify-between">
                          <span>Conf: {telAgent.confidence_score}</span>
                          <span className="text-scada-dimText">Anom: {telAgent.anomalies?.length || 0}</span>
                        </div>
                      </div>

                      {/* Relay Agent Card */}
                      <div className="bg-black/25 border border-scada-border/15 p-1 rounded flex flex-col justify-between text-[6px] h-[55px]">
                        <div>
                          <span className="font-bold text-amber-400 block truncate">RelayAgent</span>
                          <span className="text-[5.5px] text-scada-dimText font-mono block mt-0.5">Status: <strong className="text-white">{relAgent.status.replace("_ANOMALY","")}</strong></span>
                        </div>
                        <div className="mt-1 border-t border-scada-border/10 pt-0.5 font-mono text-[5.2px] flex justify-between">
                          <span>Conf: {relAgent.confidence_score}</span>
                          <span className="text-scada-dimText">Osc: {relAgent.breaker_oscillations?.length || 0}</span>
                        </div>
                      </div>

                      {/* Security Agent Card */}
                      <div className="bg-black/25 border border-scada-border/15 p-1 rounded flex flex-col justify-between text-[6px] h-[55px]">
                        <div>
                          <span className="font-bold text-purple-400 block truncate">SecurityAgent</span>
                          <span className="text-[5.5px] text-scada-dimText font-mono block mt-0.5">Status: <strong className="text-white">{secAgent.status}</strong></span>
                        </div>
                        <div className="mt-1 border-t border-scada-border/10 pt-0.5 font-mono text-[5.2px] flex justify-between">
                          <span>Conf: {secAgent.confidence_score}</span>
                          <span className="text-scada-dimText">Alts: {secAgent.threat_alerts?.length || 0}</span>
                        </div>
                      </div>

                      {/* Workflow Agent Card */}
                      <div className="bg-black/25 border border-scada-border/15 p-1 rounded flex flex-col justify-between text-[6px] h-[55px]">
                        <div>
                          <span className="font-bold text-blue-400 block truncate">WorkflowAgent</span>
                          <span className="text-[5.5px] text-scada-dimText font-mono block mt-0.5">Status: <strong className="text-white">{wfAgent.status}</strong></span>
                        </div>
                        <div className="mt-1 border-t border-scada-border/10 pt-0.5 font-mono text-[5.2px] flex justify-between">
                          <span>Conf: {wfAgent.confidence_score}</span>
                          <span className="text-scada-dimText">Plans: {wfAgent.recovery_plans?.length || 0}</span>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Inter-Agent Communication flow & Logs */}
                  <div className="bg-scada-bg/60 border border-scada-border/30 rounded p-1.5">
                    <div className="text-[7.5px] font-bold text-scada-dimText uppercase tracking-wider mb-1 border-b border-scada-border/20 pb-0.5 flex justify-between shrink-0">
                      <span>Inter-Agent Communication Flow</span>
                      {agentCoord.delegation_chain?.length > 0 && (
                        <span className="text-cyan-400 text-[6px] font-mono">Depth: {agentCoord.delegation_chain.length - 1}/3</span>
                      )}
                    </div>

                    {agentCoord.delegation_chain?.length > 0 ? (
                      <div className="bg-black/20 p-1 rounded border border-scada-border/15 mb-1 text-[5.8px] font-mono flex items-center gap-1 flex-wrap shrink-0">
                        {agentCoord.delegation_chain.map((agent: string, idx: number) => (
                          <React.Fragment key={idx}>
                            {idx > 0 && <span className="text-amber-400">➔</span>}
                            <span className={`px-1 py-0.2 rounded border ${
                              agent === "TelemetryAgent" ? "bg-cyan-950/40 border-cyan-500/30 text-cyan-300" :
                              agent === "RelayAgent" ? "bg-amber-950/40 border-amber-500/30 text-amber-300" :
                              agent === "SecurityAgent" ? "bg-purple-950/40 border-purple-500/30 text-purple-300" :
                              "bg-blue-950/40 border-blue-500/30 text-blue-300"
                            }`}>{agent}</span>
                          </React.Fragment>
                        ))}
                      </div>
                    ) : (
                      <div className="text-[6.5px] text-scada-dimText italic mb-1 shrink-0">Delegation chain idle.</div>
                    )}

                    {/* Logs container */}
                    <div className="bg-black/30 border border-scada-border/20 rounded p-1 flex flex-col h-[50px] overflow-hidden">
                      <div className="text-[6.5px] font-bold text-scada-dimText uppercase tracking-wider mb-0.5 flex items-center gap-1 shrink-0 border-b border-scada-border/10 pb-0.5">
                        <Terminal size={8} className="text-purple-400 animate-pulse" />
                        <span>Active Delegation Chain Logs</span>
                      </div>
                      <div className="flex-1 overflow-y-auto space-y-0.5 text-[5.8px] leading-tight font-mono text-purple-300 scrollbar-thin">
                        {agentCoord.inter_agent_logs && agentCoord.inter_agent_logs.length > 0 ? (
                          agentCoord.inter_agent_logs.map((log: string, idx: number) => {
                            let color = "text-purple-300";
                            if (log.includes("ALARM") || log.includes("LOOP") || log.includes("limit")) color = "text-rose-400 font-bold bg-rose-950/20 px-1 rounded border-l border-rose-500";
                            else if (log.includes("KONSENSUS") || log.includes("APPROVED")) color = "text-emerald-400 font-bold";
                            else if (log.includes("SEKATAN") || log.includes("BLOCKED")) color = "text-amber-400 font-bold";
                            return <div key={idx} className={color}>&gt; {log}</div>;
                          })
                        ) : (
                          <div className="text-scada-dimText/30 italic text-[6px] h-full flex items-center justify-center">No active communications.</div>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>


            {/* Simulation controls grid at bottom */}
            <div className="bg-scada-bg/70 border border-scada-border/30 rounded p-2 shrink-0 space-y-2 max-h-[105px] overflow-y-auto scrollbar-thin">
              <div>
                <div className="text-[7px] font-bold text-scada-dimText uppercase tracking-wider mb-1 flex items-center gap-1 border-b border-scada-border/20 pb-0.5">
                  <Sliders size={8} className="text-cyan-400 animate-pulse" />
                  <span>Planning & Dialogue Simulation Controls (Phase 9.5)</span>
                </div>
                <div className="grid grid-cols-3 gap-1 pt-1">
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

              <div>
                <div className="text-[7px] font-bold text-scada-dimText uppercase tracking-wider mb-1 flex items-center gap-1 border-b border-scada-border/20 pb-0.5">
                  <Sliders size={8} className="text-amber-400 animate-pulse" />
                  <span>Autonomy & Predictive Simulation Controls (Phase 9.6)</span>
                </div>
                <div className="grid grid-cols-3 gap-1 pt-1">
                  <button onClick={triggerRecurringAnomaly}
                    className="bg-cyan-950 hover:bg-cyan-900 border border-cyan-500/30 rounded py-1 text-[6.5px] text-cyan-300 font-bold transition-all hover:scale-102 flex flex-col items-center justify-center gap-0.5 leading-none animate-pulse">
                    <Activity size={8} /> Rec Telemetry Anomaly
                  </button>
                  <button onClick={triggerRepeatedWorkflowFailure}
                    className="bg-rose-950 hover:bg-rose-900 border border-rose-500/30 rounded py-1 text-[6.5px] text-rose-300 font-bold transition-all hover:scale-102 flex flex-col items-center justify-center gap-0.5 leading-none">
                    <AlertTriangle size={8} /> Rep Workflow Failure
                  </button>
                  <button onClick={triggerOrchestrationDrift}
                    className="bg-blue-950 hover:bg-blue-900 border border-blue-500/30 rounded py-1 text-[6.5px] text-blue-300 font-bold transition-all hover:scale-102 flex flex-col items-center justify-center gap-0.5 leading-none">
                    <Clock size={8} /> Comms Clock Drift
                  </button>
                  <button onClick={triggerConfidenceInstability}
                    className="bg-amber-950 hover:bg-amber-900 border border-amber-500/30 rounded py-1 text-[6.5px] text-amber-300 font-bold transition-all hover:scale-102 flex flex-col items-center justify-center gap-0.5 leading-none">
                    <Shield size={8} /> Conf Instability
                  </button>
                  <button onClick={triggerOptimizationConflict}
                    className="bg-rose-950 hover:bg-rose-900 border border-rose-500/30 rounded py-1 text-[6.5px] text-rose-300 font-bold transition-all hover:scale-102 flex flex-col items-center justify-center gap-0.5 leading-none">
                    <AlertTriangle size={8} /> Optimization Conflict
                  </button>
                  <button onClick={triggerClearMemory}
                    className="bg-emerald-950 hover:bg-emerald-900 border border-emerald-500/30 rounded py-1 text-[6.5px] text-emerald-300 font-bold transition-all hover:scale-102 flex flex-col items-center justify-center gap-0.5 leading-none">
                    <RotateCcw size={8} /> Clear Memory
                  </button>
                </div>
              </div>

              <div>
                <div className="text-[7px] font-bold text-scada-dimText uppercase tracking-wider mb-1 flex items-center gap-1 border-b border-scada-border/20 pb-0.5">
                  <Sliders size={8} className="text-rose-400 animate-pulse" />
                  <span>Cyber-Physical & Edge Simulation Controls (Phase 9.7)</span>
                </div>
                <div className="grid grid-cols-3 gap-1 pt-1">
                  <button onClick={triggerRelayInstability}
                    className="bg-cyan-950 hover:bg-cyan-900 border border-cyan-500/30 rounded py-1 text-[6.5px] text-cyan-300 font-bold transition-all hover:scale-102 flex flex-col items-center justify-center gap-0.5 leading-none">
                    <Activity size={8} /> Instability Simulation
                  </button>
                  <button onClick={triggerSyncDriftSpikes}
                    className="bg-rose-950 hover:bg-rose-900 border border-rose-500/30 rounded py-1 text-[6.5px] text-rose-300 font-bold transition-all hover:scale-102 flex flex-col items-center justify-center gap-0.5 leading-none">
                    <Clock size={8} /> Sync Drift Spike
                  </button>
                  <button onClick={triggerTelemetryCorrelationAnomalies}
                    className="bg-blue-950 hover:bg-blue-900 border border-blue-500/30 rounded py-1 text-[6.5px] text-blue-300 font-bold transition-all hover:scale-102 flex flex-col items-center justify-center gap-0.5 leading-none">
                    <Sliders size={8} /> Correlation Anomaly
                  </button>
                  <button onClick={triggerCascadingNodeFailures}
                    className="bg-amber-950 hover:bg-amber-900 border border-amber-500/30 rounded py-1 text-[6.5px] text-amber-300 font-bold transition-all hover:scale-102 flex flex-col items-center justify-center gap-0.5 leading-none">
                    <AlertTriangle size={8} /> Cascading Failures
                  </button>
                  <button onClick={triggerDistributedTimingSkew}
                    className="bg-rose-950 hover:bg-rose-900 border border-rose-500/30 rounded py-1 text-[6.5px] text-rose-300 font-bold transition-all hover:scale-102 flex flex-col items-center justify-center gap-0.5 leading-none">
                    <Clock size={8} /> Timing Skew
                  </button>
                  <button onClick={triggerRelayOscillationBehavior}
                    className="bg-orange-950 hover:bg-orange-900 border border-orange-500/30 rounded py-1 text-[6.5px] text-orange-300 font-bold transition-all hover:scale-102 flex flex-col items-center justify-center gap-0.5 leading-none animate-pulse">
                    <Activity size={8} /> Relay Oscillation
                  </button>
                  <button onClick={triggerEdgeNodeDegradationReplay}
                    className="bg-emerald-950 hover:bg-emerald-900 border border-emerald-500/30 rounded py-1 text-[6.5px] text-emerald-300 font-bold transition-all hover:scale-102 flex flex-col items-center justify-center gap-0.5 leading-none">
                    <Sliders size={8} /> Degradation Replay
                  </button>
                  <button onClick={triggerClearCPReasoning}
                    className="bg-emerald-950 hover:bg-emerald-900 border border-emerald-500/30 rounded py-1 text-[6.5px] text-emerald-300 font-bold transition-all hover:scale-102 flex flex-col items-center justify-center gap-0.5 leading-none col-span-2">
                    <RotateCcw size={8} /> Clear CP Diagnostics
                  </button>
                </div>
              </div>

              <div>
                <div className="text-[7px] font-bold text-scada-dimText uppercase tracking-wider mb-1 flex items-center gap-1 border-b border-scada-border/20 pb-0.5">
                  <Sliders size={8} className="text-amber-400 animate-pulse" />
                  <span>Distributed Multi-Agent Simulation Controls (Phase 9.8)</span>
                </div>
                <div className="grid grid-cols-3 gap-1 pt-1">
                  <button onClick={() => onSendControl({ topic: "assistant/agent_coordination_simulation", payload: { action: "set_mode", mode: null } })}
                    className="bg-cyan-950 hover:bg-cyan-900 border border-cyan-500/30 rounded py-1 text-[6.5px] text-cyan-300 font-bold transition-all hover:scale-102 flex flex-col items-center justify-center gap-0.5 leading-none">
                    <CheckCircle2 size={8} /> Consensus Agreement
                  </button>
                  <button onClick={() => onSendControl({ topic: "assistant/agent_coordination_simulation", payload: { action: "set_mode", mode: "conflicting_recommendations" } })}
                    className="bg-rose-950 hover:bg-rose-900 border border-rose-500/30 rounded py-1 text-[6.5px] text-rose-300 font-bold transition-all hover:scale-102 flex flex-col items-center justify-center gap-0.5 leading-none">
                    <AlertTriangle size={8} /> Conflict Arbitration
                  </button>
                  <button onClick={() => onSendControl({ topic: "assistant/agent_coordination_simulation", payload: { action: "set_mode", mode: "drift_storm" } })}
                    className="bg-amber-950 hover:bg-amber-900 border border-amber-500/30 rounded py-1 text-[6.5px] text-amber-300 font-bold transition-all hover:scale-102 flex flex-col items-center justify-center gap-0.5 leading-none">
                    <Clock size={8} /> Drift Storm
                  </button>
                  <button onClick={() => onSendControl({ topic: "assistant/agent_coordination_simulation", payload: { action: "set_mode", mode: "cascading_failures" } })}
                    className="bg-red-950 hover:bg-red-900 border border-red-500/30 rounded py-1 text-[6.5px] text-red-300 font-bold transition-all hover:scale-102 flex flex-col items-center justify-center gap-0.5 leading-none">
                    <RefreshCw size={8} className="animate-spin" /> Recursive Loop Block
                  </button>
                  <button onClick={() => onSendControl({ topic: "assistant/agent_coordination_simulation", payload: { action: "set_mode", mode: "relay_spikes" } })}
                    className="bg-blue-950 hover:bg-blue-900 border border-blue-500/30 rounded py-1 text-[6.5px] text-blue-300 font-bold transition-all hover:scale-102 flex flex-col items-center justify-center gap-0.5 leading-none">
                    <Activity size={8} /> Wear & Tear Spike
                  </button>
                  <button onClick={() => onSendControl({ topic: "assistant/agent_coordination_simulation", payload: { action: "set_mode", mode: "delegation_timeout" } })}
                    className="bg-orange-950 hover:bg-orange-900 border border-orange-500/30 rounded py-1 text-[6.5px] text-orange-300 font-bold transition-all hover:scale-102 flex flex-col items-center justify-center gap-0.5 leading-none">
                    <Clock size={8} /> Delegation Timeout
                  </button>
                  <button onClick={() => onSendControl({ topic: "assistant/agent_coordination_simulation", payload: { action: "consensus_instability" } })}
                    className="bg-purple-950 hover:bg-purple-900 border border-purple-500/30 rounded py-1 text-[6.5px] text-purple-300 font-bold transition-all hover:scale-102 flex flex-col items-center justify-center gap-0.5 leading-none col-span-1">
                    <Shield size={8} /> Security Rejection
                  </button>
                  <button onClick={() => onSendControl({ topic: "assistant/agent_coordination_simulation", payload: { action: "reset" } })}
                    className="bg-emerald-950 hover:bg-emerald-900 border border-emerald-500/30 rounded py-1 text-[6.5px] text-emerald-300 font-bold transition-all hover:scale-102 flex flex-col items-center justify-center gap-0.5 leading-none col-span-2">
                    <RotateCcw size={8} /> Reset Multi-Agent
                  </button>
                </div>
              </div>

              {/* Tab 9: Swarm Cognition (Phase 9.9) */}
              {activeTab === "swarm" && (
                <div className="space-y-1.5">
                  {/* Row 1: Swarm Coordination Graph & Consensus Gauge */}
                  <div className="grid grid-cols-2 gap-1.5">
                    {/* Swarm Coordination Graph */}
                    <div className="bg-scada-bg/60 border border-scada-border/30 rounded p-1.5 flex flex-col justify-between h-[125px]">
                      <div className="text-[7.5px] font-bold text-scada-dimText uppercase tracking-wider border-b border-scada-border/20 pb-0.5 flex justify-between shrink-0">
                        <span className="flex items-center gap-1"><Bot size={9} className="text-fuchsia-400" /> Swarm Coordination Graph</span>
                        <span className={`px-1 rounded text-[6.5px] font-mono ${
                          swarmCoord.status === "CRITICAL" ? "bg-rose-950 text-rose-400" :
                          swarmCoord.status === "LOOP_PREVENTED" ? "bg-red-950 text-red-400 animate-bounce" :
                          swarmCoord.status === "STORM_MITIGATED" ? "bg-amber-950 text-amber-400 animate-pulse" : "bg-emerald-950 text-emerald-400"
                        }`}>{swarmCoord.status}</span>
                      </div>
                      
                      <div className="flex-1 relative flex items-center justify-center mt-1">
                        <svg className="w-full h-full max-h-[90px]" viewBox="0 0 100 60">
                          {/* Connections */}
                          <line x1="50" y1="30" x2="20" y2="15" stroke="#475569" strokeWidth="1" strokeDasharray={swarmCoord.status === "CRITICAL" ? "1.5" : "0"} />
                          <line x1="50" y1="30" x2="80" y2="15" stroke="#475569" strokeWidth="1" />
                          <line x1="50" y1="30" x2="20" y2="45" stroke="#475569" strokeWidth="1" />
                          <line x1="50" y1="30" x2="80" y2="45" stroke="#475569" strokeWidth="1" />

                          {/* Animation pulses along lines */}
                          {swarmCoord.status !== "LOOP_PREVENTED" && (
                            <>
                              <circle cx="35" cy="22.5" r="1.2" fill="#38bdf8" className="animate-ping" />
                              <circle cx="65" cy="22.5" r="1.2" fill="#a855f7" />
                              <circle cx="35" cy="37.5" r="1.2" fill="#f43f5e" />
                              <circle cx="65" cy="37.5" r="1.2" fill="#10b981" />
                            </>
                          )}

                          {/* Spokes */}
                          <circle cx="20" cy="15" r="6" fill="#1e293b" stroke="#38bdf8" strokeWidth="1" />
                          <text x="20" y="17" textAnchor="middle" fontSize="4.5" fill="#f8fafc" fontWeight="bold">MEM</text>

                          <circle cx="80" cy="15" r="6" fill="#1e293b" stroke="#a855f7" strokeWidth="1" />
                          <text x="80" y="17" textAnchor="middle" fontSize="4.5" fill="#f8fafc" fontWeight="bold">CON</text>

                          <circle cx="20" cy="45" r="6" fill="#1e293b" stroke="#f43f5e" strokeWidth="1" />
                          <text x="20" y="47" textAnchor="middle" fontSize="4.5" fill="#f8fafc" fontWeight="bold">MSH</text>

                          <circle cx="80" cy="45" r="6" fill="#1e293b" stroke="#10b981" strokeWidth="1" />
                          <text x="80" y="47" textAnchor="middle" fontSize="4.5" fill="#f8fafc" fontWeight="bold">FSN</text>

                          {/* Central Swarm Hub */}
                          <circle cx="50" cy="30" r="10" fill="#0f172a" stroke="#d946ef" strokeWidth="1.5" />
                          <text x="50" y="32" textAnchor="middle" fontSize="5" fill="#d946ef" fontWeight="bold" className="animate-pulse">HUB</text>
                        </svg>
                      </div>
                    </div>

                    {/* Consensus Gauge */}
                    <div className="bg-scada-bg/60 border border-scada-border/30 rounded p-1.5 flex flex-col justify-between h-[125px]">
                      <div className="text-[7.5px] font-bold text-scada-dimText uppercase tracking-wider border-b border-scada-border/20 pb-0.5 flex justify-between shrink-0">
                        <span className="flex items-center gap-1"><Shield size={9} className="text-purple-400" /> Distributed Consensus Gauge</span>
                        <span className={`px-1 rounded text-[6.5px] font-bold ${
                          distConsensus.consensus_state === "APPROVED" ? "bg-emerald-950 text-emerald-400" :
                          distConsensus.consensus_state.startsWith("BLOCKED") ? "bg-rose-950 text-rose-400" : "bg-cyan-950 text-cyan-400"
                        }`}>{distConsensus.consensus_state}</span>
                      </div>

                      <div className="flex-1 flex items-center justify-center gap-2 mt-1">
                        <div className="w-[50px] h-[50px] relative">
                          <svg viewBox="0 0 50 50" className="w-full h-full">
                            <circle cx="25" cy="25" r="20" fill="none" stroke="#1e293b" strokeWidth="4" />
                            <circle 
                              cx="25" 
                              cy="25" 
                              r="20" 
                              fill="none" 
                              stroke={distConsensus.consensus_score >= 0.80 ? "#10b981" : "#f43f5e"} 
                              strokeWidth="4" 
                              strokeDasharray={2 * Math.PI * 20}
                              strokeDashoffset={2 * Math.PI * 20 * (1 - distConsensus.consensus_score)}
                              transform="rotate(-90 25 25)"
                              className="transition-all duration-500"
                            />
                            <text x="25" y="28" textAnchor="middle" fontSize="7" fill="#ffffff" fontWeight="bold" className="font-mono">
                              {Math.round(distConsensus.consensus_score * 100)}%
                            </text>
                          </svg>
                        </div>
                        <div className="flex-1 font-mono text-[5.8px] leading-normal text-scada-dimText">
                          <div className="flex justify-between">
                            <span>Score:</span>
                            <strong className="text-white">{(distConsensus.consensus_score ?? 0).toFixed(2)}</strong>
                          </div>
                          <div className="flex justify-between">
                            <span>Threshold:</span>
                            <span className="text-cyan-400">0.80</span>
                          </div>
                          <div className="flex justify-between">
                            <span>Drift Rate:</span>
                            <span className={distConsensus.consensus_drift > 0.40 ? "text-rose-400 font-bold" : "text-white"}>
                              {(distConsensus.consensus_drift ?? 0).toFixed(2)}
                            </span>
                          </div>
                          <div className="flex justify-between">
                            <span>Active Nodes:</span>
                            <span className="text-white">{Object.keys(distConsensus.votes ?? {}).length} nodes</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Row 2: Edge-Mesh Topology Map & Swarm Anomaly Fusion Heatmap */}
                  <div className="grid grid-cols-2 gap-1.5">
                    {/* Edge-Mesh Topology Map */}
                    <div className="bg-scada-bg/60 border border-scada-border/30 rounded p-1.5 flex flex-col justify-between h-[125px]">
                      <div className="text-[7.5px] font-bold text-scada-dimText uppercase tracking-wider border-b border-scada-border/20 pb-0.5 flex justify-between shrink-0">
                        <span className="flex items-center gap-1"><Compass size={9} className="text-rose-400 animate-spin" style={{ animationDuration: '6s' }} /> Edge-Mesh Topology Map</span>
                        <span className={`px-1 rounded text-[6.5px] font-mono ${
                          edgeMesh.mesh_status === "CONNECTED" ? "bg-emerald-950 text-emerald-400" :
                          edgeMesh.mesh_status === "PARTITIONED" ? "bg-rose-950 text-rose-400 animate-pulse" : "bg-amber-950 text-amber-400"
                        }`}>{edgeMesh.mesh_status}</span>
                      </div>

                      <div className="flex-1 mt-1 relative bg-black/20 rounded border border-scada-border/10">
                        <svg className="w-full h-full" viewBox="0 0 100 65">
                          {((edgeMesh.links && edgeMesh.links.length > 0) ? edgeMesh.links : [
                            { source: "esp32_zone1", target: "plc_primary", status: "ACTIVE" },
                            { source: "esp32_zone2", target: "plc_primary", status: "ACTIVE" },
                            { source: "esp32_zone2", target: "esp32_zone3", status: "ACTIVE" },
                            { source: "esp32_zone3", target: "plc_backup", status: "ACTIVE" },
                            { source: "esp32_zone3", target: "esp32_backup", status: "ACTIVE" },
                            { source: "plc_backup", target: "esp32_backup", status: "ACTIVE" }
                          ]).map((link: any, idx: number) => {
                            const nodePositions: Record<string, { x: number; y: number }> = {
                              plc_primary: { x: 25, y: 15 },
                              esp32_zone1: { x: 12, y: 48 },
                              esp32_zone2: { x: 38, y: 48 },
                              plc_backup: { x: 75, y: 15 },
                              esp32_zone3: { x: 62, y: 48 },
                              esp32_backup: { x: 88, y: 48 }
                            };
                            const pS = nodePositions[link.source];
                            const pT = nodePositions[link.target];
                            if (!pS || !pT) return null;
                            const isBroken = link.status === "BROKEN";
                            return (
                              <line 
                                key={idx} 
                                x1={pS.x} 
                                y1={pS.y} 
                                x2={pT.x} 
                                y2={pT.y} 
                                stroke={isBroken ? "#ef4444" : "#10b981"} 
                                strokeWidth={isBroken ? 1.5 : 1}
                                strokeDasharray={isBroken ? "2,2" : "0"}
                              />
                            );
                          })}

                          {[
                            { id: "plc_primary", label: "PLC 1", x: 25, y: 15, col: "#38bdf8" },
                            { id: "esp32_zone1", label: "Z1", x: 12, y: 48, col: "#10b981" },
                            { id: "esp32_zone2", label: "Z2", x: 38, y: 48, col: "#10b981" },
                            { id: "plc_backup", label: "PLC 2", x: 75, y: 15, col: "#a855f7" },
                            { id: "esp32_zone3", label: "Z3", x: 62, y: 48, col: "#10b981" },
                            { id: "esp32_backup", label: "BCK", x: 88, y: 48, col: "#f59e0b" }
                          ].map((n) => {
                            const isWorst = edgeMesh.worst_node === n.id;
                            return (
                              <g key={n.id}>
                                <circle 
                                  cx={n.x} 
                                  cy={n.y} 
                                  r={isWorst ? 4.5 : 3.5} 
                                  fill="#0f172a" 
                                  stroke={isWorst ? "#ef4444" : n.col} 
                                  strokeWidth={isWorst ? 1.5 : 1} 
                                  className={isWorst ? "animate-pulse" : ""}
                                />
                                <text x={n.x} y={n.y + 1.5} textAnchor="middle" fontSize="3.8" fill="#f8fafc" fontWeight="bold">{n.label}</text>
                              </g>
                            );
                          })}
                        </svg>
                      </div>
                    </div>

                    {/* Swarm Anomaly Fusion Heatmap */}
                    <div className="bg-scada-bg/60 border border-scada-border/30 rounded p-1.5 flex flex-col justify-between h-[125px]">
                      <div className="text-[7.5px] font-bold text-scada-dimText uppercase tracking-wider border-b border-scada-border/20 pb-0.5 flex justify-between shrink-0">
                        <span className="flex items-center gap-1"><Activity size={9} className="text-emerald-400" /> Swarm Anomaly Fusion Heatmap</span>
                        <span className="text-[6.5px] text-scada-dimText font-mono">Score: <strong className="text-white">{swarmAnomalyFusion.swarm_threat_score.toFixed(1)}/10.0</strong></span>
                      </div>

                      <div className="flex-1 mt-1 grid grid-cols-4 gap-1 p-0.5 bg-black/10 rounded">
                        {(() => {
                          const keys = ["telemetry", "relay", "security", "edge"];
                          const defaultMatrix: Record<string, Record<string, number>> = {
                            telemetry: { telemetry: 1.0, relay: 0.15, security: 0.15, edge: 0.15 },
                            relay: { telemetry: 0.15, relay: 1.0, security: 0.15, edge: 0.15 },
                            security: { telemetry: 0.15, relay: 0.15, security: 1.0, edge: 0.15 },
                            edge: { telemetry: 0.15, relay: 0.15, security: 0.15, edge: 1.0 }
                          };
                          const matrix = swarmAnomalyFusion.correlation_matrix && Object.keys(swarmAnomalyFusion.correlation_matrix).length > 0 
                            ? swarmAnomalyFusion.correlation_matrix 
                            : defaultMatrix;

                          return keys.map((k1) => 
                            keys.map((k2) => {
                              const val = Number(matrix[k1]?.[k2] ?? 0.0);
                              return (
                                <div 
                                  key={`${k1}-${k2}`} 
                                  className={`rounded-[2px] flex flex-col justify-center items-center font-mono text-[5.5px] leading-tight select-none border border-scada-border/5 ${
                                    val >= 0.8 ? "bg-rose-500/80 text-white font-bold animate-pulse" :
                                    val >= 0.5 ? "bg-amber-500/50 text-amber-100" :
                                    val > 0.2 ? "bg-cyan-500/30 text-cyan-200" : "bg-black/35 text-scada-dimText"
                                  }`}
                                  title={`${k1} <-> ${k2}: ${val.toFixed(2)}`}
                                >
                                  <span className="text-[4px] uppercase text-white/40">{k1.substring(0,3)}/{k2.substring(0,3)}</span>
                                  <span>{val.toFixed(2)}</span>
                                </div>
                              );
                            })
                          );
                        })()}
                      </div>
                    </div>
                  </div>

                  {/* Row 3: Federated Memory & Consensus Drift Timeline */}
                  <div className="grid grid-cols-2 gap-1.5">
                    {/* Federated Memory Sync */}
                    <div className="bg-scada-bg/60 border border-scada-border/30 rounded p-1.5 flex flex-col justify-between h-[115px]">
                      <div className="text-[7.5px] font-bold text-scada-dimText uppercase tracking-wider border-b border-scada-border/20 pb-0.5 flex justify-between shrink-0">
                        <span className="flex items-center gap-1"><GitBranch size={9} className="text-cyan-400" /> Federated Memory Workspace</span>
                        <span className={`px-1 rounded text-[6px] font-bold uppercase ${
                          fedMemory.sync_status === "SYNCED" ? "bg-emerald-950 text-emerald-400" :
                          fedMemory.sync_status === "STORM_PREVENTED" ? "bg-red-950 text-red-400 animate-bounce" : "bg-amber-950 text-amber-400"
                        }`}>{fedMemory.sync_status}</span>
                      </div>

                      <div className="flex-1 grid grid-cols-2 gap-1.5 mt-1 overflow-hidden">
                        <div className="bg-black/20 border border-scada-border/10 p-1.5 rounded text-[5.8px] font-mono leading-relaxed overflow-y-auto scrollbar-thin">
                          <div className="text-[6.5px] font-bold text-cyan-400 uppercase mb-0.5">Shared Variables</div>
                          {Object.keys(fedMemory.shared_memory ?? {}).length > 0 ? (
                            Object.entries(fedMemory.shared_memory).map(([key, val]: [string, any]) => (
                              <div key={key} className="border-b border-scada-border/5 pb-0.5 flex justify-between">
                                <span className="text-scada-dimText truncate pr-1 max-w-[50px]">{key}:</span>
                                <span className="text-white font-bold truncate max-w-[40px]">{String(val)}</span>
                              </div>
                            ))
                          ) : (
                            <div className="text-[5.5px] text-scada-dimText">Tiada pembolehubah dikongsi.</div>
                          )}
                        </div>

                        <div className="bg-black/20 border border-scada-border/10 p-1.5 rounded text-[5.8px] font-mono leading-relaxed overflow-hidden flex flex-col">
                          <div className="text-[6.5px] font-bold text-cyan-400 uppercase mb-0.5 shrink-0">State Metrics</div>
                          <div className="flex-1 space-y-0.5 text-[5.5px] overflow-y-auto scrollbar-thin">
                            <div>Lamport Clock: <strong className="text-white">{fedMemory.lamport_clock}</strong></div>
                            <div>Sync Count: <strong className="text-white">{fedMemory.sync_count}</strong></div>
                            {fedMemory.conflict_logs?.length > 0 ? (
                              <div className="border-t border-scada-border/10 mt-1 pt-0.5">
                                <span className="text-amber-400 font-bold block">Conflict Logs:</span>
                                <div className="text-[4.8px] text-amber-200/80 leading-normal max-h-[40px] overflow-y-auto scrollbar-thin">
                                  {fedMemory.conflict_logs.map((log: string, idx: number) => (
                                    <div key={idx} className="border-b border-scada-border/5 pb-0.5">{log}</div>
                                  ))}
                                </div>
                              </div>
                            ) : (
                              <div className="text-emerald-400 font-bold mt-1 text-[5px]">Replikasi memori bersih dari konflik.</div>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Consensus Drift Timeline */}
                    <div className="bg-scada-bg/60 border border-scada-border/30 rounded p-1.5 flex flex-col justify-between h-[115px]">
                      <div className="text-[7.5px] font-bold text-scada-dimText uppercase tracking-wider border-b border-scada-border/20 pb-0.5 flex justify-between shrink-0">
                        <span className="flex items-center gap-1"><Clock size={9} className="text-pink-400" /> Consensus Drift Timeline</span>
                        <span className="text-[6.5px] text-scada-dimText font-mono">Max Drift: <strong className="text-white">{(distConsensus.consensus_drift ?? 0).toFixed(2)}</strong></span>
                      </div>

                      <div className="flex-1 mt-1.5 flex flex-col justify-between">
                        <div className="flex-1 bg-black/35 rounded border border-scada-border/10 p-1 flex items-center justify-center">
                          {(() => {
                            const driftHistory = distConsensus.drift_history ?? [];
                            const points = driftHistory.length > 0 ? driftHistory : [
                              { drift: 0.05 }, { drift: 0.08 }, { drift: 0.06 }, { drift: 0.12 }, { drift: 0.09 }, { drift: 0.15 }, { drift: 0.10 }
                            ];
                            const pointsStr = points.map((p: any, idx: number) => {
                              const x = (idx / Math.max(1, points.length - 1)) * 95 + 2.5;
                              const y = 35 - Math.min(1.0, p.drift ?? 0) * 30;
                              return `${x},${y}`;
                            }).join(" ");

                            return (
                              <svg className="w-full h-full max-h-[50px]" viewBox="0 0 100 40">
                                <line x1="0" y1="35" x2="100" y2="35" stroke="#334155" strokeWidth="0.5" strokeDasharray="2,2" />
                                <line x1="0" y1="20" x2="100" y2="20" stroke="#334155" strokeWidth="0.5" strokeDasharray="2,2" />
                                <line x1="0" y1="5" x2="100" y2="5" stroke="#334155" strokeWidth="0.5" strokeDasharray="2,2" />
                                <polyline fill="none" stroke="#ec4899" strokeWidth="1.2" points={pointsStr} />
                              </svg>
                            );
                          })()}
                        </div>
                        <span className="text-[5.2px] font-mono text-scada-dimText mt-1 block text-center uppercase tracking-wider">Historical Drift Divergence Curve</span>
                      </div>
                    </div>
                  </div>

                  {/* Row 4: Federated Synchronization Activity & Collaborative Orchestration Chains */}
                  <div className="grid grid-cols-2 gap-1.5">
                    {/* Federated Sync Activity */}
                    <div className="bg-scada-bg/60 border border-scada-border/30 rounded p-1.5 flex flex-col justify-between h-[105px]">
                      <div className="text-[7.5px] font-bold text-scada-dimText uppercase tracking-wider border-b border-scada-border/20 pb-0.5 shrink-0">
                        <span className="flex items-center gap-1"><Bell size={9} className="text-amber-400" /> Federated Synchronization Activity</span>
                      </div>
                      <div className="flex-1 mt-1 font-mono text-[5.8px] space-y-1 overflow-y-auto scrollbar-thin">
                        <div className="flex justify-between">
                          <span>Sync Status:</span>
                          <span className={fedMemory.sync_status === "STORM_PREVENTED" ? "text-red-400 font-bold animate-ping" : "text-emerald-400 font-bold"}>
                            {fedMemory.sync_status}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span>Consensus State:</span>
                          <span className={distConsensus.consensus_state === "APPROVED" ? "text-emerald-400 font-bold" : "text-rose-400 font-bold"}>
                            {distConsensus.consensus_state}
                          </span>
                        </div>
                        <div className="w-full bg-black/40 h-2 rounded border border-scada-border/10 overflow-hidden relative">
                          <div 
                            className={`h-full transition-all duration-300 ${
                              fedMemory.sync_status === "STORM_PREVENTED" ? "bg-red-500 animate-pulse" : "bg-cyan-500"
                            }`} 
                            style={{ width: `${Math.min(100, (fedMemory.sync_count ?? 0) % 100)}%` }}
                          />
                        </div>
                        <div className="text-[5px] text-scada-dimText text-right">
                          Sync iteration cycle index: {fedMemory.sync_count}
                        </div>
                      </div>
                    </div>

                    {/* Collaborative Orchestration Chains */}
                    <div className="bg-scada-bg/60 border border-scada-border/30 rounded p-1.5 flex flex-col justify-between h-[105px]">
                      <div className="text-[7.5px] font-bold text-scada-dimText uppercase tracking-wider border-b border-scada-border/20 pb-0.5 shrink-0">
                        <span className="flex items-center gap-1"><GitBranch size={9} className="text-fuchsia-400" /> Collaborative Orchestration Chains</span>
                      </div>
                      <div className="flex-1 mt-1 flex flex-col justify-between overflow-hidden">
                        <div className="flex items-center gap-0.5 overflow-x-auto scrollbar-none whitespace-nowrap text-[5.5px] bg-black/25 p-1 rounded border border-scada-border/10 shrink-0">
                          {swarmCoord.coordination_chain?.length > 0 ? (
                            swarmCoord.coordination_chain.map((c: string, idx: number) => (
                              <React.Fragment key={idx}>
                                {idx > 0 && <span className="text-scada-dimText font-mono">➔</span>}
                                <span className={`px-1 rounded-[2px] font-bold ${
                                  c === "EdgeMeshOrchestrator" ? "bg-rose-950 text-rose-300" :
                                  c === "FederatedMemoryManager" ? "bg-cyan-950 text-cyan-300" :
                                  c === "SwarmAnomalyFusionEngine" ? "bg-emerald-950 text-emerald-300" : "bg-purple-950 text-purple-300"
                                }`}>{c.replace("Orchestrator","").replace("Manager","").replace("Engine","")}</span>
                              </React.Fragment>
                            ))
                          ) : (
                            <span className="text-scada-dimText italic">Tiada rantaian koordinasi aktif.</span>
                          )}
                        </div>

                        <div className="flex-1 mt-1 bg-black/25 rounded border border-scada-border/10 p-1 font-mono text-[5.2px] leading-tight text-fuchsia-300 overflow-y-auto scrollbar-thin">
                          {swarmCoord.coordination_logs?.length > 0 ? (
                            swarmCoord.coordination_logs.map((log: string, idx: number) => (
                              <div key={idx} className="border-b border-scada-border/5 pb-0.5">{log}</div>
                            ))
                          ) : (
                            <div className="text-scada-dimText italic">Menunggu log koordinasi swarm...</div>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Row 5: Swarm Cognition Simulation Console */}
                  <div className="bg-scada-bg/60 border border-scada-border/30 rounded p-1.5 shrink-0">
                    <div className="text-[7.5px] font-bold text-scada-dimText uppercase tracking-wider mb-1 flex items-center gap-1 border-b border-scada-border/20 pb-0.5">
                      <Sliders size={8} className="text-fuchsia-400 animate-pulse" />
                      <span>Federated Swarm Cognition Simulation Console (Phase 9.9)</span>
                    </div>
                    <div className="grid grid-cols-3 gap-1 pt-1 shrink-0">
                      <button onClick={() => onSendControl({ topic: "assistant/swarm_coordination_simulation", payload: { action: "set_mode", mode: null } })}
                        className="bg-cyan-950 hover:bg-cyan-900 border border-cyan-500/30 rounded py-1 text-[6.5px] text-cyan-300 font-bold transition-all hover:scale-102 flex flex-col items-center justify-center gap-0.5 leading-none">
                        <CheckCircle2 size={8} /> Swarm Consensus
                      </button>
                      <button onClick={() => onSendControl({ topic: "assistant/swarm_coordination_simulation", payload: { action: "set_mode", mode: "swarm_consensus_instability" } })}
                        className="bg-purple-950 hover:bg-purple-900 border border-purple-500/30 rounded py-1 text-[6.5px] text-purple-300 font-bold transition-all hover:scale-102 flex flex-col items-center justify-center gap-0.5 leading-none">
                        <AlertTriangle size={8} /> Instability Failure
                      </button>
                      <button onClick={() => onSendControl({ topic: "assistant/swarm_coordination_simulation", payload: { action: "set_mode", mode: "federated_memory_conflicts" } })}
                        className="bg-yellow-950 hover:bg-yellow-900 border border-yellow-500/30 rounded py-1 text-[6.5px] text-yellow-300 font-bold transition-all hover:scale-102 flex flex-col items-center justify-center gap-0.5 leading-none">
                        <GitBranch size={8} /> Memory Conflict
                      </button>
                      <button onClick={() => onSendControl({ topic: "assistant/swarm_coordination_simulation", payload: { action: "set_mode", mode: "edge_mesh_partition_failures" } })}
                        className="bg-rose-950 hover:bg-rose-900 border border-rose-500/30 rounded py-1 text-[6.5px] text-rose-300 font-bold transition-all hover:scale-102 flex flex-col items-center justify-center gap-0.5 leading-none">
                        <Compass size={8} /> Mesh Partition
                      </button>
                      <button onClick={() => onSendControl({ topic: "assistant/swarm_coordination_simulation", payload: { action: "set_mode", mode: "anomaly_fusion_overload" } })}
                        className="bg-red-950 hover:bg-red-900 border border-red-500/30 rounded py-1 text-[6.5px] text-red-300 font-bold transition-all hover:scale-102 flex flex-col items-center justify-center gap-0.5 leading-none">
                        <Activity size={8} /> Fusion Overload
                      </button>
                      <button onClick={() => onSendControl({ topic: "assistant/swarm_coordination_simulation", payload: { action: "set_mode", mode: "synchronization_storms" } })}
                        className="bg-amber-950 hover:bg-amber-900 border border-amber-500/30 rounded py-1 text-[6.5px] text-amber-300 font-bold transition-all hover:scale-102 flex flex-col items-center justify-center gap-0.5 leading-none">
                        <Clock size={8} /> Sync Storm
                      </button>
                      <button onClick={() => onSendControl({ topic: "assistant/swarm_coordination_simulation", payload: { action: "set_mode", mode: "distributed_drift_escalation" } })}
                        className="bg-orange-950 hover:bg-orange-900 border border-orange-500/30 rounded py-1 text-[6.5px] text-orange-300 font-bold transition-all hover:scale-102 flex flex-col items-center justify-center gap-0.5 leading-none">
                        <RefreshCw size={8} className="animate-spin" /> Drift Escalation
                      </button>
                      <button onClick={() => onSendControl({ topic: "assistant/swarm_coordination_simulation", payload: { action: "set_mode", mode: "collaborative_recovery_failures" } })}
                        className="bg-pink-950 hover:bg-pink-900 border border-pink-500/30 rounded py-1 text-[6.5px] text-pink-300 font-bold transition-all hover:scale-102 flex flex-col items-center justify-center gap-0.5 leading-none">
                        <AlertTriangle size={8} /> Recovery Failure
                      </button>
                      <button onClick={() => onSendControl({ topic: "assistant/swarm_coordination_simulation", payload: { action: "reset" } })}
                        className="bg-emerald-950 hover:bg-emerald-900 border border-emerald-500/30 rounded py-1 text-[6.5px] text-emerald-300 font-bold transition-all hover:scale-102 flex flex-col items-center justify-center gap-0.5 leading-none col-span-1">
                        <RotateCcw size={8} /> Reset Swarm
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

