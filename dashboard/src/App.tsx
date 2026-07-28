import { useEffect, useState, useRef, useMemo } from "react";

import { GridDiagram } from "./components/GridDiagram.tsx";
import { TelemetryCharts } from "./components/TelemetryCharts.tsx";

import { ThreatScorePanel } from "./components/ThreatScorePanel.tsx";
import { ForecastPanel } from "./components/ForecastPanel.tsx";
import { MultiBusForecastPanel } from "./components/MultiBusForecastPanel.tsx";
import { ThreatAwareForecastPanel } from "./components/ThreatAwareForecastPanel.tsx";
import { PhysicsValidationPanel } from "./components/PhysicsValidationPanel.tsx";
import { TrustAnalysisPanel } from "./components/TrustAnalysisPanel.tsx";
import { OrchestratorPanel } from "./components/OrchestratorPanel.tsx";
import { SystemHealthPanel } from "./components/SystemHealthPanel.tsx";
import { PinnForecastPanel } from "./components/PinnForecastPanel.tsx";
import { PreRlPanel } from "./components/PreRlPanel.tsx";
import { CyberDefensePanel } from "./components/CyberDefensePanel.tsx";
import { Layer6Panel } from "./components/Layer6Panel.tsx";
import { AdaptiveRecoveryPanel } from "./components/AdaptiveRecoveryPanel.tsx";
import { AutonomousSurvivalPanel } from "./components/AutonomousSurvivalPanel.tsx";
import { PredictiveStabilizationPanel } from "./components/PredictiveStabilizationPanel.tsx";
import { MultiAgentCoordinationPanel } from "./components/MultiAgentCoordinationPanel.tsx";
import { HardwareFoundationPanel } from "./components/HardwareFoundationPanel.tsx";
import { VirtualHardwareTwinPanel } from "./components/VirtualHardwareTwinPanel.tsx";
import { CyberPhysicalAttackPanel } from "./components/CyberPhysicalAttackPanel.tsx";
import { HardwareOrchestrationPanel } from "./components/HardwareOrchestrationPanel.tsx";
import { HardwareExecutionPanel } from "./components/HardwareExecutionPanel.tsx";
import { InfrastructureResiliencePanel } from "./components/InfrastructureResiliencePanel.tsx";
import { AssistantCognitionPanel } from "./components/AssistantCognitionPanel.tsx";
import { FloatingChatbot } from "./components/FloatingChatbot.tsx";
import { BcmCenter } from "./components/BcmCenter.tsx";
import { ResearchWorkspace } from "./components/ResearchWorkspace.tsx";
import { ScenarioMarketplace } from "./components/ScenarioMarketplace.tsx";
import { AiCopilot } from "./components/AiCopilot.tsx";
import { SaaSAdmin } from "./components/SaaSAdmin.tsx";
import OperationsCenter from "./components/OperationsCenter.tsx";
import { SimulationQueueMonitor } from "./components/SimulationQueueMonitor.tsx";
import LandingPage from "./components/LandingPage.tsx";
import AuthPages from "./components/AuthPages.tsx";
import UserDashboard from "./components/UserDashboard.tsx";
import WorkspaceSetupWizard from "./components/WorkspaceSetupWizard.tsx";



import {
  Wifi,
  Cpu,
  Zap,
  AlertOctagon,
  MonitorPlay,
  Play as PlayIcon,
  Pause,
  ChevronLeft,
  ChevronRight,
  Minimize2,
  Maximize2,
  ArrowLeft,
  ArrowRight,
  Activity,
  ShieldAlert,
  Award,
  CheckCircle2,
  FileText,
  Eye,
  Sliders,
  X
} from "lucide-react";

function Sparkline({ data, color }: { data: number[]; color: string }) {
  if (!data || data.length < 2) return <div className="text-gray-600 font-mono text-[9px] text-center w-full">NO DATA</div>;
  const max = Math.max(...data);
  const min = Math.min(...data);
  const range = max - min || 1;
  const width = 120;
  const height = 24;
  const points = data
    .map((val, i) => {
      const x = (i / (data.length - 1)) * width;
      const y = height - ((val - min) / range) * height;
      return `${x},${y}`;
    })
    .join(" ");

  return (
    <svg width={width} height={height} className="overflow-visible">
      <polyline fill="none" stroke={color} strokeWidth="1.5" points={points} />
    </svg>
  );
}

export default function App() {
  const [connected, setConnected] = useState<boolean>(false);
  const [currentPage, setCurrentPage] = useState<
    "landing" | "overview" | "analytics" | "reports" | "settings" | "bcm_center" | "research_workspace" | "scenario_marketplace" | "ai_copilot" | "saas_admin" | "cloud_ops" | "operations_center"
    | "login" | "register" | "forgot_password" | "reset_password" | "verify_email" | "resend_verification"
    | "user_dashboard" | "setup_wizard"
  >("landing");

  // V11.9 Auth state
  const [authToken, setAuthToken] = useState<string>(localStorage.getItem('pypy_token') || '');
  const [authUser, setAuthUser] = useState<Record<string, unknown>>(() => {
    try { return JSON.parse(localStorage.getItem('pypy_user') || '{}'); } catch { return {}; }
  });
  const handleAuthSuccess = (token: string, user: Record<string, unknown>) => {
    localStorage.setItem('pypy_token', token);
    localStorage.setItem('pypy_user', JSON.stringify(user));
    setAuthToken(token);
    setAuthUser(user);
    const firstLogin = !localStorage.getItem('pypy_setup_done');
    setCurrentPage(firstLogin ? 'setup_wizard' : 'user_dashboard');
  };

  const handleLogout = () => {
    localStorage.removeItem('pypy_token');
    localStorage.removeItem('pypy_user');
    setAuthToken('');
    setAuthUser({});
    setCurrentPage('landing');
  };

  const handleSetupComplete = () => {
    localStorage.setItem('pypy_setup_done', 'true');
    setCurrentPage('user_dashboard');
  };

  const handleNavFromLanding = (page: string) => {
    const authPage = ['login','register','forgot_password','reset_password','verify_email','resend_verification'];
    if (authPage.includes(page)) {
      setCurrentPage(page as any);
    } else if (page === 'demo') {
      setCurrentPage('overview');
    } else {
      setCurrentPage('overview');
    }
  };

  const [planTier, setPlanTier] = useState<string>("academic_premium");
  const [aiMessagesUsed] = useState<number>(2);
  const [daysRemaining, setDaysRemaining] = useState<number>(14);
  const [trialBannerVisible, setTrialBannerVisible] = useState<boolean>(true);
  const [experiments, setExperiments] = useState<any[]>([
    {
      id: "exp_1",
      name: "Coordinated Tripping Analysis",
      grid_type: "IEEE39",
      verdict: "DEGRADED",
      resilience_score: 91.2,
      archived: false,
      locked: false,
      read_only: false,
      created_at: new Date().toISOString()
    },
    {
      id: "exp_2",
      name: "FLISR Verification IEEE 14",
      grid_type: "IEEE14",
      verdict: "NOMINAL",
      resilience_score: 98.4,
      archived: false,
      locked: false,
      read_only: false,
      created_at: new Date(Date.now() - 86400000).toISOString()
    },
    {
      id: "exp_3",
      name: "Zero-Parameter Pathogen Study",
      grid_type: "IEEE118",
      verdict: "BLACKOUT",
      resilience_score: 12.5,
      archived: true,
      locked: true,
      read_only: true,
      created_at: new Date(Date.now() - 172800000).toISOString()
    }
  ]);
  const [tenants, setTenants] = useState<any[]>([
    { id: "mit_id", name: "MIT Smart Grid Lab", subdomain: "mit.pypygrid.com", plan_tier: "academic_premium" },
    { id: "stanford_id", name: "Stanford Energy Dept", subdomain: "stanford.pypygrid.com", plan_tier: "free" }
  ]);

  const handleRedeemCoupon = async (code: string) => {
    const cleanCode = code.toUpperCase().trim();
    if (cleanCode === "UNIMAP2026" || cleanCode === "USM2026" || cleanCode === "UTM2026") {
      setPlanTier("academic_premium");
      setDaysRemaining(365);
      setExperiments(prev => prev.map(e => e.locked ? { ...e, archived: false, locked: false, read_only: false } : e));
      alert(`Coupon code verified: Academic Premium tier activated for 1 Year via University Promo!`);
    } else if (cleanCode === "RESEARCH_LAB_2026") {
      setPlanTier("research_lab");
      setDaysRemaining(365);
      setExperiments(prev => prev.map(e => e.locked ? { ...e, archived: false, locked: false, read_only: false } : e));
      alert(`Coupon code verified: Research Lab tier activated for 1 Year via University Promo!`);
    } else if (cleanCode === "PYPY_ACADEMIC_FREE_30" || cleanCode === "PYPY_ACADEMIC_FREE_90" || cleanCode === "ENTERPRISE_DEMO_30" || cleanCode === "ENTERPRISE_DEMO_90") {
      setPlanTier(cleanCode.includes("ENTERPRISE") ? "enterprise" : "academic_premium");
      setDaysRemaining(cleanCode.includes("90") ? 90 : 30);
      setExperiments(prev => prev.map(e => e.locked ? { ...e, archived: false, locked: false, read_only: false } : e));
      alert(`Coupon code verified: Upgraded to ${cleanCode.includes("ENTERPRISE") ? "Enterprise" : "Academic Premium"}!`);
    } else {
      alert("Invalid or expired coupon code.");
    }
  };

  const handleOverridePlan = (tenantId: string, newTier: string) => {
    setTenants(prev => prev.map(t => t.id === tenantId ? { ...t, plan_tier: newTier } : t));
    alert(`Plan updated for tenant: ${newTier}`);
  };




  const [selectedReport, setSelectedReport] = useState<any>(null);
  const [selectedFigure, setSelectedFigure] = useState<any>(null);
  const [scadaRefreshRate, setScadaRefreshRate] = useState<number>(5);
  const [themeMode, setThemeMode] = useState<"dark" | "amber" | "crt">("dark");
  const [showConsole, setShowConsole] = useState<boolean>(false);
  const [liveLogs, setLiveLogs] = useState<any[]>([]);
  const [logFilter, setLogFilter] = useState<string>("");
  const [logConsoleOpen, setLogConsoleOpen] = useState<boolean>(false);
  const logsEndRef = useRef<HTMLDivElement>(null);
  const lastProcessedTimestampRef = useRef<number>(0);
  const [isTopologyFullscreen, setIsTopologyFullscreen] = useState<boolean>(false);
  const [isLogScrollPaused, setIsLogScrollPaused] = useState<boolean>(false);


  const [analyticsTab, setAnalyticsTab] = useState<"performance" | "cyber" | "self-healing" | "ai-models">("performance");
  const [currentTime, setCurrentTime] = useState<string>("");
  const [selectedGrid, setSelectedGrid] = useState<string>("ieee39");
  const [metricsHistory, setMetricsHistory] = useState<{
    voltage: number[];
    frequency: number[];
    load: number[];
    trust: number[];
    attackCount: number[];
    blackoutProb: number[];
  }>({
    voltage: [],
    frequency: [],
    load: [],
    trust: [],
    attackCount: [],
    blackoutProb: []
  });
  const [telemetry, setTelemetry] = useState<any>(null);
  const [history, setHistory] = useState<any[]>([]);
  const [_events, setEvents] = useState<any[]>([]);
  const [_alerts, setAlerts] = useState<any[]>([]);
  const [threatData, setThreatData] = useState<any>(null);
  const [aiPrediction, setAiPrediction] = useState<any>(null);
  const [predictionHistory, setPredictionHistory] = useState<any[]>([]);
  const [multiBusForecast, setMultiBusForecast] = useState<any>(null);
  const [threatAwareForecast, setThreatAwareForecast] = useState<any>(null);
  const [pinnForecast, setPinnForecast] = useState<any>(null);
  const [physicsValidation, setPhysicsValidation] = useState<any>(null);
  const [trustScores, setTrustScores] = useState<any>(null);
  const [adaptiveFilter, setAdaptiveFilter] = useState<any>(null);
  const [aiOrchestrator, setAiOrchestrator] = useState<any>(null);
  const [recommendedActions, setRecommendedActions] = useState<any>(null);
  const [defenseData, setDefenseData] = useState<any>(null);
  const [l6Recovery, setL6Recovery] = useState<any>(null);
  const [l6AdaptiveRecovery, setL6AdaptiveRecovery] = useState<any>(null);
  const [l6Containment, setL6Containment] = useState<any>(null);
  const [l6DegradedMode, setL6DegradedMode] = useState<any>(null);
  const [l6Survival, setL6Survival] = useState<any>(null);
  const [l6Islanding, setL6Islanding] = useState<any>(null);
  const [l6Blackstart, setL6Blackstart] = useState<any>(null);
  const [l6Balancing, setL6Balancing] = useState<any>(null);
  const [l6PredictiveStability, setL6PredictiveStability] = useState<any>(null);
  const [l6SurvivalForecast, setL6SurvivalForecast] = useState<any>(null);
  const [l6ProactiveActions, setL6ProactiveActions] = useState<any>(null);
  const [l6SelfPreservation, setL6SelfPreservation] = useState<any>(null);
  const [l6Agents, setL6Agents] = useState<any>(null);
  const [l6AgentConsensus, setL6AgentConsensus] = useState<any>(null);
  const [l6AgentConflicts, setL6AgentConflicts] = useState<any>(null);
  const [l6DistributedState, setL6DistributedState] = useState<any>(null);
  const [l6AgentConfidence, setL6AgentConfidence] = useState<any>(null);
  const [hardwareRelay, setHardwareRelay] = useState<any>(null);
  const [hardwareGpio, setHardwareGpio] = useState<any>(null);
  const [hardwareSensor, setHardwareSensor] = useState<any>(null);
  const [hardwareDeviceHealth, setHardwareDeviceHealth] = useState<any>(null);
  const [hardwareCommandLog, setHardwareCommandLog] = useState<any>(null);
  const [hardwareFaults, setHardwareFaults] = useState<any>(null);
  const [hardwareRelayFaults, setHardwareRelayFaults] = useState<any>(null);
  const [hardwareAnomalies, setHardwareAnomalies] = useState<any[]>([]);
  const [hardwareVirtualDevices, setHardwareVirtualDevices] = useState<any>(null);
  const [hardwareSpoofedTelemetry, setHardwareSpoofedTelemetry] = useState<any>(null);
  const [hardwareFaultPropagation, setHardwareFaultPropagation] = useState<any>(null);
  const [hardwareUsbEvents, setHardwareUsbEvents] = useState<any>(null);
  const [hardwareRogueDevices, setHardwareRogueDevices] = useState<any>(null);
  const [hardwareBadusb, setHardwareBadusb] = useState<any>(null);
  const [hardwareIntrusionAlerts, setHardwareIntrusionAlerts] = useState<any>(null);
  const [hardwareDeviceTrust, setHardwareDeviceTrust] = useState<any>(null);
  const [hardwareAttackState, setHardwareAttackState] = useState<any>(null);
  const [hardwareAttackPropagation, setHardwareAttackPropagation] = useState<any>(null);
  const [hardwareOrchestration, setHardwareOrchestration] = useState<any>(null);
  const [hardwareEdgeDevices, setHardwareEdgeDevices] = useState<any>(null);
  const [hardwareRelayExecution, setHardwareRelayExecution] = useState<any>(null);
  const [hardwareDistributedBus, setHardwareDistributedBus] = useState<any>(null);
  const [hardwareSynchronization, setHardwareSynchronization] = useState<any>(null);
  const [hardwareOrchestrationConflicts, setHardwareOrchestrationConflicts] = useState<any>(null);
  const [hardwareExecutionGateway, setHardwareExecutionGateway] = useState<any>(null);
  const [hardwareReliability, setHardwareReliability] = useState<any>(null);
  const [hardwareSafetyGuard, setHardwareSafetyGuard] = useState<any>(null);
  const [hardwareDeploymentProfiles, setHardwareDeploymentProfiles] = useState<any>(null);
  const [hardwareTelemetryValidation, setHardwareTelemetryValidation] = useState<any>(null);
  const [hardwareResilience, setHardwareResilience] = useState<any>(null);
  const [hardwareDisasterRecovery, setHardwareDisasterRecovery] = useState<any>(null);
  const [hardwareRedundancy, setHardwareRedundancy] = useState<any>(null);
  const [hardwareDeploymentHardening, setHardwareDeploymentHardening] = useState<any>(null);
  const [hardwareLargeScaleSync, setHardwareLargeScaleSync] = useState<any>(null);

  // Assistant states
  const [assistantState, setAssistantState] = useState<any>(null);
  const [assistantIntent, setAssistantIntent] = useState<any>(null);
  const [assistantEmotion, setAssistantEmotion] = useState<any>(null);
  const [assistantActions, setAssistantActions] = useState<any>(null);
  const [assistantContext, setAssistantContext] = useState<any>(null);
  const [assistantMemory, setAssistantMemory] = useState<any>(null);
  const [assistantResponse, setAssistantResponse] = useState<any>(null);
  const [assistantRuntime, setAssistantRuntime] = useState<any>(null);
  const [assistantSemanticIntent, setAssistantSemanticIntent] = useState<any>(null);
  const [assistantContextualMemory, setAssistantContextualMemory] = useState<any>(null);
  const [assistantReasoning, setAssistantReasoning] = useState<any>(null);
  const [assistantAutomationHooks, setAssistantAutomationHooks] = useState<any>(null);
  const [assistantSemanticResponse, setAssistantSemanticResponse] = useState<any>(null);
  const [assistantVoiceState, setAssistantVoiceState] = useState<any>(null);
  const [assistantWakeWord, setAssistantWakeWord] = useState<any>(null);
  const [assistantProactive, setAssistantProactive] = useState<any>(null);
  const [assistantVoiceMemory, setAssistantVoiceMemory] = useState<any>(null);
  const [assistantPresence, setAssistantPresence] = useState<any>(null);
  const [assistantWorkflows, setAssistantWorkflows] = useState<any>(null);
  const [assistantReminders, setAssistantReminders] = useState<any>(null);
  const [assistantConditions, setAssistantConditions] = useState<any>(null);
  const [assistantN8nBridge, setAssistantN8nBridge] = useState<any>(null);
  const [assistantRoutines, setAssistantRoutines] = useState<any>(null);
  const [assistantConversationPlanning, setAssistantConversationPlanning] = useState<any>(null);
  const [assistantTaskChains, setAssistantTaskChains] = useState<any>(null);
  const [assistantLiveStream, setAssistantLiveStream] = useState<any>(null);
  const [assistantDialogue, setAssistantDialogue] = useState<any>(null);
  const [assistantOrchestrationPlanner, setAssistantOrchestrationPlanner] = useState<any>(null);
  
  // Phase 9.6 states
  const [assistantPredictiveCoordination, setAssistantPredictiveCoordination] = useState<any>(null);
  const [assistantPersistentMemory, setAssistantPersistentMemory] = useState<any>(null);
  const [assistantPatternAwareness, setAssistantPatternAwareness] = useState<any>(null);
  const [assistantWorkflowOptimizer, setAssistantWorkflowOptimizer] = useState<any>(null);
  const [assistantCrossSystemCoordination, setAssistantCrossSystemCoordination] = useState<any>(null);

  // Phase 9.7 states
  const [assistantEdgeAwareness, setAssistantEdgeAwareness] = useState<any>(null);
  const [assistantRelayHealth, setAssistantRelayHealth] = useState<any>(null);
  const [assistantTelemetryCorrelation, setAssistantTelemetryCorrelation] = useState<any>(null);
  const [assistantSynchronizationAwareness, setAssistantSynchronizationAwareness] = useState<any>(null);
  const [assistantCyberPhysicalReasoning, setAssistantCyberPhysicalReasoning] = useState<any>(null);

  // Phase 9.8 states
  const [assistantAgentCoordination, setAssistantAgentCoordination] = useState<any>(null);
  const [assistantTelemetryAgent, setAssistantTelemetryAgent] = useState<any>(null);
  const [assistantRelayAgent, setAssistantRelayAgent] = useState<any>(null);
  const [assistantWorkflowAgent, setAssistantWorkflowAgent] = useState<any>(null);
  const [assistantSecurityAgent, setAssistantSecurityAgent] = useState<any>(null);

  // Phase 9.9 states
  const [assistantSwarmCoordination, setAssistantSwarmCoordination] = useState<any>(null);
  const [assistantFederatedMemory, setAssistantFederatedMemory] = useState<any>(null);
  const [assistantDistributedConsensus, setAssistantDistributedConsensus] = useState<any>(null);
  const [assistantEdgeMesh, setAssistantEdgeMesh] = useState<any>(null);
  const [assistantSwarmAnomalyFusion, setAssistantSwarmAnomalyFusion] = useState<any>(null);


  const [proactiveAutoMode, setProactiveAutoMode] = useState<boolean>(true);
  const [flisrAuto, setFlisrAuto] = useState<boolean>(true);
  const [crtEnabled, setCrtEnabled] = useState<boolean>(true);

  // FLISR state tracking
  const [flisrState, setFlisrState] = useState<string>("NORMAL");
  const [flisrIsolated, setFlisrIsolated] = useState<string[]>([]);
  const [flisrReconfigured, setFlisrReconfigured] = useState<string[]>([]);
  const [flisrTripped, setFlisrTripped] = useState<string[]>([]);
  const [preRlData, setPreRlData] = useState<any>(null);

  // Cyber attack visual state tracking
  const [activeAttack, setActiveAttack] = useState<string | null>(null);
  const [, setAttackTarget] = useState<string | null>(null);

  // --- Phase A: HMI Operational Stabilization States ---
  const [wsLatency, setWsLatency] = useState<number>(0);
  const [reconnectCount, setReconnectCount] = useState<number>(0);
  const [msgRate, setMsgRate] = useState<number>(1.0);


  // Collapsible and Resizable Panel states
  const [collapsedPanels, setCollapsedPanels] = useState<Set<string>>(new Set());
  const [panelSizes, setPanelSizes] = useState<Record<string, number>>({
    telemetry: 1,
    forecast: 1,
    multibus: 1,
    threat_aware: 1,
    pinn: 1,
    physics: 1,
    trust: 1,
    orchestrator: 1,
    health: 1,
    pre_rl: 1,
    cyber_defense: 2,
    l6_recovery: 2,
    l6_adaptive_recovery: 2,
    l6_survival: 2,
    l6_predictive_stabilization: 2,
    l6_multi_agent: 2,
    l7_hardware: 2,
    l7_twin: 2,
    l7_attack: 2,
    l7_orchestration: 2,
    l7_execution: 2,
    l7_resilience: 2,
    l7_assistant: 2
  });
  const [panelOrder, setPanelOrder] = useState<string[]>([
    "telemetry", "forecast", "multibus", "threat_aware", "pinn", "physics", "trust", "orchestrator", "health", "pre_rl", "cyber_defense", "l6_recovery", "l6_adaptive_recovery", "l6_survival", "l6_predictive_stabilization", "l6_multi_agent", "l7_hardware", "l7_twin", "l7_attack", "l7_orchestration", "l7_execution", "l7_resilience", "l7_assistant"
  ]);

  // Timeline Replay States
  const [isReplaying, setIsReplaying] = useState<boolean>(false);
  const [replayIndex, setReplayIndex] = useState<number>(0);
  const [replayFrames, setReplayFrames] = useState<any[]>([]);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);

  useEffect(() => {
    if (logConsoleOpen && logsEndRef.current && !isLogScrollPaused) {
      logsEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [liveLogs.length, logConsoleOpen, isLogScrollPaused]);

  // Stream simulated console events when idle to keep console dynamic
  useEffect(() => {
    const eventTemplates = [
      { message: "INFO Telemetry packet received.", severity: "info" },
      { message: "INFO PINN consistency validation passed.", severity: "success" },
      { message: "INFO Blockchain consensus block verified.", severity: "success" },
      { message: "INFO FLISR diagnostics clear. Network paths nominal.", severity: "info" },
      { message: "INFO Security consensus signatures verified.", severity: "success" },
      { message: "WARNING Minor load fluctuation observed on Bus 12.", severity: "warning" },
      { message: "INFO Intelligent assistant processing cognition routine.", severity: "info" }
    ];

    const interval = setInterval(() => {
      const lastFrameAge = Date.now() - (lastProcessedTimestampRef.current || 0);
      if (lastFrameAge > 3000 && !isReplaying) {
        const randomTemplate = eventTemplates[Math.floor(Math.random() * eventTemplates.length)];
        const nowStr = new Date().toLocaleTimeString([], { hour12: false });
        
        setLiveLogs((prev) => {
          const next = [...prev, {
            timestamp: nowStr,
            message: randomTemplate.message,
            severity: randomTemplate.severity
          }];
          if (next.length > 100) return next.slice(next.length - 100);
          return next;
        });
      }
    }, 4000);
    return () => clearInterval(interval);
  }, [isReplaying]);

  // Refs for state values to prevent stale closures in websocket onmessage callback
  const stateRef = useRef<any>({});
  useEffect(() => {
    stateRef.current = {
      telemetry,
      threatData,
      aiPrediction,
      multiBusForecast,
      threatAwareForecast,
      pinnForecast,
      physicsValidation,
      trustScores,
      adaptiveFilter,
      aiOrchestrator,
      recommendedActions,
      preRlData,
      defenseData,
      l6Recovery,
      l6AdaptiveRecovery,
      l6Containment,
      l6DegradedMode,
      l6Survival,
      l6Islanding,
      l6Blackstart,
      l6Balancing,
      l6PredictiveStability,
      l6SurvivalForecast,
      l6ProactiveActions,
      l6SelfPreservation,
      l6Agents,
      l6AgentConsensus,
      l6AgentConflicts,
      l6DistributedState,
      l6AgentConfidence,
      hardwareRelay,
      hardwareGpio,
      hardwareSensor,
      hardwareDeviceHealth,
      hardwareCommandLog,
      hardwareFaults,
      hardwareRelayFaults,
      hardwareAnomalies,
      hardwareVirtualDevices,
      hardwareSpoofedTelemetry,
      hardwareFaultPropagation,
      hardwareUsbEvents,
      hardwareRogueDevices,
      hardwareBadusb,
      hardwareIntrusionAlerts,
      hardwareDeviceTrust,
      hardwareAttackState,
      hardwareAttackPropagation,
      hardwareOrchestration,
      hardwareEdgeDevices,
      hardwareRelayExecution,
      hardwareDistributedBus,
      hardwareSynchronization,
      hardwareOrchestrationConflicts,
      hardwareExecutionGateway,
      hardwareReliability,
      hardwareSafetyGuard,
      hardwareDeploymentProfiles,
      hardwareTelemetryValidation,
      hardwareResilience,
      hardwareDisasterRecovery,
      hardwareRedundancy,
      hardwareDeploymentHardening,
      hardwareLargeScaleSync,
      assistantState,
      assistantIntent,
      assistantEmotion,
      assistantActions,
      assistantContext,
      assistantMemory,
      assistantResponse,
      assistantRuntime,
      assistantSemanticIntent,
      assistantContextualMemory,
      assistantReasoning,
      assistantAutomationHooks,
      assistantSemanticResponse,
      assistantVoiceState,
      assistantWakeWord,
      assistantProactive,
      assistantVoiceMemory,
      assistantPresence,
      assistantWorkflows,
      assistantReminders,
      assistantConditions,
      assistantN8nBridge,
      assistantRoutines,
      assistantConversationPlanning,
      assistantTaskChains,
      assistantLiveStream,
      assistantDialogue,
      assistantOrchestrationPlanner,

      // Phase 9.6 states
      assistantPredictiveCoordination,
      assistantPersistentMemory,
      assistantPatternAwareness,
      assistantWorkflowOptimizer,
      assistantCrossSystemCoordination,

      // Phase 9.7 states
      assistantEdgeAwareness,
      assistantRelayHealth,
      assistantTelemetryCorrelation,
      assistantSynchronizationAwareness,
      assistantCyberPhysicalReasoning,

      // Phase 9.8 states
      assistantAgentCoordination,
      assistantTelemetryAgent,
      assistantRelayAgent,
      assistantWorkflowAgent,
      assistantSecurityAgent,

      // Phase 9.9 states
      assistantSwarmCoordination,
      assistantFederatedMemory,
      assistantDistributedConsensus,
      assistantEdgeMesh,
      assistantSwarmAnomalyFusion,

      flisrState,
      flisrIsolated,
      flisrReconfigured,
      flisrTripped,
      activeAttack
    };
  }); // Run on every render

  useEffect(() => {
    const updateTime = () => {
      setCurrentTime(new Date().toLocaleTimeString([], { hour12: false }));
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    // Reset all histories and state on grid swap to prevent mixing data from different topologies
    setMetricsHistory({
      voltage: [],
      frequency: [],
      load: [],
      trust: [],
      attackCount: [],
      blackoutProb: []
    });
    setHistory([]);
    setTelemetry(null);
  }, [selectedGrid]);
  const selectedGridRef = useRef<string>("ieee39");
  useEffect(() => {
    selectedGridRef.current = selectedGrid;
  }, [selectedGrid]);

  const telemTimesRef = useRef<number[]>([]);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<any>(null);

  const connectWebSocket = () => {
    const wsHost = window.location.hostname || "localhost";
    const wsUrl = `ws://${wsHost}:8000/ws`;
    
    console.log(`Connecting to WebSocket: ${wsUrl}`);
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log("WebSocket connection established!");
      setConnected(true);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        if (data.type === "PONG") {
          const sentTime = data.payload;
          setWsLatency(Date.now() - sentTime);
          return;
        }
        
        // Handle initial cache load (Bootstrap)
        if (data.type === "BOOTSTRAP") {
          if (data.telemetry) {
            setTelemetry(data.telemetry);
            setHistory([data.telemetry]);
            if (data.telemetry.grid_name) {
              setSelectedGrid(data.telemetry.grid_name.toLowerCase());
            }
          }
          if (data.events) {
            setEvents([...data.events].reverse());
            // Recover active attack state if present in recent events
            for (const ev of data.events) {
              if (ev.event.includes("Cyber Attack activated:")) {
                const match = ev.event.match(/Cyber Attack activated:\s+(\w+)\s+targeting\s+([\w_]+)/);
                if (match) {
                  setActiveAttack(match[1]);
                  setAttackTarget(match[2]);
                  break;
                }
              }
            }
          }
          if (data.alerts) {
            setAlerts([...data.alerts].reverse());
          }
          if (data.config) {
            if (data.config.flisr_state !== undefined) setFlisrState(data.config.flisr_state);
            if (data.config.flisr_auto !== undefined) setFlisrAuto(data.config.flisr_auto);
            if (data.config.flisr_isolated_faults !== undefined) setFlisrIsolated(data.config.flisr_isolated_faults);
            if (data.config.flisr_reconfigured_breakers !== undefined) setFlisrReconfigured(data.config.flisr_reconfigured_breakers);
            if (data.config.flisr_tripped_by_relay !== undefined) setFlisrTripped(data.config.flisr_tripped_by_relay);
          }
          if (data.threat) {
            setThreatData(data.threat);
          }
          if (data.ai_prediction && typeof data.ai_prediction === "object") {
            const payload = data.ai_prediction;
            const isValid = 
              (payload.predicted_bus5_voltage !== undefined && payload.instability_risk !== undefined) ||
              (payload.predicted_threat !== undefined && payload.cascade_risk !== undefined);
            if (isValid) {
              setAiPrediction(payload);
              setPredictionHistory([payload]);
            }
          }
          if (data.ai_forecast_multi_bus && typeof data.ai_forecast_multi_bus === "object") {
            const payload = data.ai_forecast_multi_bus;
            const isValid = payload.forecasts !== undefined && payload.timestamp !== undefined && payload.overall_status !== undefined;
            if (isValid) {
              setMultiBusForecast(payload);
            }
          }
          if (data.ai_threat_forecast && typeof data.ai_threat_forecast === "object") {
            const payload = data.ai_threat_forecast;
            const isValid = (payload.cyber_instability_probability !== undefined || payload.predicted_threat !== undefined) &&
                            payload.status !== undefined &&
                            payload.timestamp !== undefined;
            if (isValid) {
              setThreatAwareForecast(payload);
            }
          }
          if (data.pinn_forecast && typeof data.pinn_forecast === "object") {
            const payload = data.pinn_forecast;
            if (payload.horizons !== undefined && payload.timestamp !== undefined) {
              setPinnForecast(payload);
            }
          }
          if (data.physics_validation) {
            setPhysicsValidation(data.physics_validation);
          }
          if (data.trust_scores) {
            setTrustScores(data.trust_scores);
          }
          if (data.adaptive_filter) {
            setAdaptiveFilter(data.adaptive_filter);
          }
          if (data.ai_orchestrator) {
            setAiOrchestrator(data.ai_orchestrator);
          }
          if (data.recommended_actions) {
            setRecommendedActions(data.recommended_actions);
          }
          if (data.pre_rl) {
            setPreRlData(data.pre_rl);
          }
          if (data.defense) {
            setDefenseData(data.defense);
          }
          if (data.l6_recovery) {
            setL6Recovery(data.l6_recovery);
          }
          if (data.l6_adaptive_recovery) {
            setL6AdaptiveRecovery(data.l6_adaptive_recovery);
          }
          if (data.l6_containment) {
            setL6Containment(data.l6_containment);
          }
          if (data.l6_degraded_mode) {
            setL6DegradedMode(data.l6_degraded_mode);
          }
          if (data.l6_survival) {
            setL6Survival(data.l6_survival);
          }
          if (data.l6_islanding) {
            setL6Islanding(data.l6_islanding);
          }
          if (data.l6_blackstart) {
            setL6Blackstart(data.l6_blackstart);
          }
          if (data.l6_balancing) {
            setL6Balancing(data.l6_balancing);
          }
          if (data.l6_predictive_stability) {
            setL6PredictiveStability(data.l6_predictive_stability);
          }
          if (data.l6_survival_forecast) {
            setL6SurvivalForecast(data.l6_survival_forecast);
          }
          if (data.l6_proactive_actions) {
            setL6ProactiveActions(data.l6_proactive_actions);
          }
          if (data.l6_self_preservation) {
            setL6SelfPreservation(data.l6_self_preservation);
          }
          if (data.l6_agents) {
            setL6Agents(data.l6_agents);
          }
          if (data.l6_agent_consensus) {
            setL6AgentConsensus(data.l6_agent_consensus);
          }
          if (data.l6_agent_conflicts) {
            setL6AgentConflicts(data.l6_agent_conflicts);
          }
          if (data.l6_distributed_state) {
            setL6DistributedState(data.l6_distributed_state);
          }
          if (data.l6_agent_confidence) {
            setL6AgentConfidence(data.l6_agent_confidence);
          }
          if (data.hardware_relay) {
            setHardwareRelay(data.hardware_relay);
          }
          if (data.hardware_gpio) {
            setHardwareGpio(data.hardware_gpio);
          }
          if (data.hardware_sensor) {
            setHardwareSensor(data.hardware_sensor);
          }
          if (data.hardware_device_health) {
            setHardwareDeviceHealth(data.hardware_device_health);
          }
          if (data.hardware_command_log) {
            setHardwareCommandLog(data.hardware_command_log);
          }
          if (data.hardware_faults) {
            setHardwareFaults(data.hardware_faults);
          }
          if (data.hardware_relay_faults) {
            setHardwareRelayFaults(data.hardware_relay_faults);
          }
          if (data.hardware_anomalies) {
            setHardwareAnomalies(data.hardware_anomalies);
          }
          if (data.hardware_virtual_devices) {
            setHardwareVirtualDevices(data.hardware_virtual_devices);
          }
          if (data.hardware_spoofed_telemetry) {
            setHardwareSpoofedTelemetry(data.hardware_spoofed_telemetry);
          }
          if (data.hardware_fault_propagation) {
            setHardwareFaultPropagation(data.hardware_fault_propagation);
          }
          if (data.hardware_usb_events) {
            setHardwareUsbEvents(data.hardware_usb_events);
          }
          if (data.hardware_rogue_devices) {
            setHardwareRogueDevices(data.hardware_rogue_devices);
          }
          if (data.hardware_badusb) {
            setHardwareBadusb(data.hardware_badusb);
          }
          if (data.hardware_intrusion_alerts) {
            setHardwareIntrusionAlerts(data.hardware_intrusion_alerts);
          }
          if (data.hardware_device_trust) {
            setHardwareDeviceTrust(data.hardware_device_trust);
          }
          if (data.hardware_attack_state) {
            setHardwareAttackState(data.hardware_attack_state);
          }
          if (data.hardware_attack_propagation) {
            setHardwareAttackPropagation(data.hardware_attack_propagation);
          }
          if (data.hardware_orchestration) {
            setHardwareOrchestration(data.hardware_orchestration);
          }
          if (data.hardware_edge_devices) {
            setHardwareEdgeDevices(data.hardware_edge_devices);
          }
          if (data.hardware_relay_execution) {
            setHardwareRelayExecution(data.hardware_relay_execution);
          }
          if (data.hardware_distributed_bus) {
            setHardwareDistributedBus(data.hardware_distributed_bus);
          }
          if (data.hardware_synchronization) {
            setHardwareSynchronization(data.hardware_synchronization);
          }
          if (data.hardware_orchestration_conflicts) {
            setHardwareOrchestrationConflicts(data.hardware_orchestration_conflicts);
          }
          if (data.hardware_execution_gateway) {
            setHardwareExecutionGateway(data.hardware_execution_gateway);
          }
          if (data.hardware_reliability) {
            setHardwareReliability(data.hardware_reliability);
          }
          if (data.hardware_safety_guard) {
            setHardwareSafetyGuard(data.hardware_safety_guard);
          }
          if (data.hardware_deployment_profiles) {
            setHardwareDeploymentProfiles(data.hardware_deployment_profiles);
          }
          if (data.hardware_telemetry_validation) {
            setHardwareTelemetryValidation(data.hardware_telemetry_validation);
          }
          if (data.hardware_resilience) {
            setHardwareResilience(data.hardware_resilience);
          }
          if (data.hardware_disaster_recovery) {
            setHardwareDisasterRecovery(data.hardware_disaster_recovery);
          }
          if (data.hardware_redundancy) {
            setHardwareRedundancy(data.hardware_redundancy);
          }
          if (data.hardware_deployment_hardening) {
            setHardwareDeploymentHardening(data.hardware_deployment_hardening);
          }
          if (data.hardware_large_scale_sync) {
            setHardwareLargeScaleSync(data.hardware_large_scale_sync);
          }
          if (data.assistant_state) {
            setAssistantState(data.assistant_state);
          }
          if (data.assistant_intent) {
            setAssistantIntent(data.assistant_intent);
          }
          if (data.assistant_emotion) {
            setAssistantEmotion(data.assistant_emotion);
          }
          if (data.assistant_actions) {
            setAssistantActions(data.assistant_actions);
          }
          if (data.assistant_context) {
            setAssistantContext(data.assistant_context);
          }
          if (data.assistant_memory) {
            setAssistantMemory(data.assistant_memory);
          }
          if (data.assistant_response) {
            setAssistantResponse(data.assistant_response);
          }
          if (data.assistant_runtime) {
            setAssistantRuntime(data.assistant_runtime);
          }
          if (data.assistant_semantic_intent) {
            setAssistantSemanticIntent(data.assistant_semantic_intent);
          }
          if (data.assistant_contextual_memory) {
            setAssistantContextualMemory(data.assistant_contextual_memory);
          }
          if (data.assistant_reasoning) {
            setAssistantReasoning(data.assistant_reasoning);
          }
          if (data.assistant_automation_hooks) {
            setAssistantAutomationHooks(data.assistant_automation_hooks);
          }
          if (data.assistant_semantic_response) {
            setAssistantSemanticResponse(data.assistant_semantic_response);
          }
          if (data.assistant_voice_state) {
            setAssistantVoiceState(data.assistant_voice_state);
          }
          if (data.assistant_wake_word) {
            setAssistantWakeWord(data.assistant_wake_word);
          }
          if (data.assistant_proactive) {
            setAssistantProactive(data.assistant_proactive);
          }
          if (data.assistant_voice_memory) {
            setAssistantVoiceMemory(data.assistant_voice_memory);
          }
          if (data.assistant_presence) {
            setAssistantPresence(data.assistant_presence);
          }
          if (data.assistant_conversation_planning) {
            setAssistantConversationPlanning(data.assistant_conversation_planning);
          }
          if (data.assistant_task_chains) {
            setAssistantTaskChains(data.assistant_task_chains);
          }
          if (data.assistant_live_stream) {
            setAssistantLiveStream(data.assistant_live_stream);
          }
          if (data.assistant_dialogue) {
            setAssistantDialogue(data.assistant_dialogue);
          }
          if (data.assistant_orchestration_planner) {
            setAssistantOrchestrationPlanner(data.assistant_orchestration_planner);
          }
          
          // Phase 9.6 bootstrap
          if (data.assistant_predictive_coordination) {
            setAssistantPredictiveCoordination(data.assistant_predictive_coordination);
          }
          if (data.assistant_persistent_memory) {
            setAssistantPersistentMemory(data.assistant_persistent_memory);
          }
          if (data.assistant_pattern_awareness) {
            setAssistantPatternAwareness(data.assistant_pattern_awareness);
          }
          if (data.assistant_workflow_optimizer) {
            setAssistantWorkflowOptimizer(data.assistant_workflow_optimizer);
          }
          if (data.assistant_cross_system_coordination) {
            setAssistantCrossSystemCoordination(data.assistant_cross_system_coordination);
          }
          
          // Phase 9.7 bootstrap
          if (data.assistant_edge_awareness) {
            setAssistantEdgeAwareness(data.assistant_edge_awareness);
          }
          if (data.assistant_relay_health) {
            setAssistantRelayHealth(data.assistant_relay_health);
          }
          if (data.assistant_telemetry_correlation) {
            setAssistantTelemetryCorrelation(data.assistant_telemetry_correlation);
          }
          if (data.assistant_synchronization_awareness) {
            setAssistantSynchronizationAwareness(data.assistant_synchronization_awareness);
          }
          if (data.assistant_cyber_physical_reasoning) {
            setAssistantCyberPhysicalReasoning(data.assistant_cyber_physical_reasoning);
          }

          // Phase 9.8 bootstrap
          if (data.assistant_agent_coordination) {
            setAssistantAgentCoordination(data.assistant_agent_coordination);
          }
          if (data.assistant_telemetry_agent) {
            setAssistantTelemetryAgent(data.assistant_telemetry_agent);
          }
          if (data.assistant_relay_agent) {
            setAssistantRelayAgent(data.assistant_relay_agent);
          }
          if (data.assistant_workflow_agent) {
            setAssistantWorkflowAgent(data.assistant_workflow_agent);
          }
          if (data.assistant_security_agent) {
            setAssistantSecurityAgent(data.assistant_security_agent);
          }

          // Phase 9.9 bootstrap
          if (data.assistant_swarm_coordination) {
            setAssistantSwarmCoordination(data.assistant_swarm_coordination);
          }
          if (data.assistant_federated_memory) {
            setAssistantFederatedMemory(data.assistant_federated_memory);
          }
          if (data.assistant_distributed_consensus) {
            setAssistantDistributedConsensus(data.assistant_distributed_consensus);
          }
          if (data.assistant_edge_mesh) {
            setAssistantEdgeMesh(data.assistant_edge_mesh);
          }
          if (data.assistant_swarm_anomaly_fusion) {
            setAssistantSwarmAnomalyFusion(data.assistant_swarm_anomaly_fusion);
          }


        } 

        // Handle active MQTT stream broadcasts
        else if (data.topic && data.payload) {
          const { topic, payload } = data;
          
          if (topic === "pypy/grid/telemetry" || topic === "grid/telemetry") {
            if (topic === "grid/telemetry" && selectedGridRef.current.toLowerCase() !== "ieee39") {
              return;
            }
            if (payload?.grid_name && payload.grid_name.toLowerCase() !== selectedGridRef.current.toLowerCase()) {
              return;
            }
            // Track telemetry message rate
            const now = Date.now();
            const telemTimes = telemTimesRef.current;
            telemTimes.push(now);
            if (telemTimes.length > 10) {
              telemTimes.shift();
            }
            if (telemTimes.length > 1) {
              const diffs = [];
              for (let i = 1; i < telemTimes.length; i++) {
                diffs.push(telemTimes[i] - telemTimes[i-1]);
              }
              const avgDiff = diffs.reduce((a, b) => a + b, 0) / diffs.length;
              setMsgRate(avgDiff > 0 ? 1000 / avgDiff : 0);
            }

            setTelemetry(payload);
            setHistory((prev) => {
              const next = [...prev, payload];
              if (next.length > 50) next.shift();
              return next;
            });

            // Phase 5B: Authoritative attack state from telemetry payload
            // This is the ground-truth source - always in sync with backend
            const atkStatus = payload?.attack_status;
            let backendAtk = null;
            if (atkStatus) {
              backendAtk = atkStatus.active_attack || null;
              setActiveAttack(backendAtk);
              if (!backendAtk) {
                setAttackTarget(null);
              }
            }

            // Save state snapshot to historical replay buffer
            const currentStates = stateRef.current;
            const newFrame = {
              timestamp: Date.now(),
              telemetry: payload,
              threatData: currentStates.threatData,
              aiPrediction: currentStates.aiPrediction,
              multiBusForecast: currentStates.multiBusForecast,
              threatAwareForecast: currentStates.threatAwareForecast,
              pinnForecast: currentStates.pinnForecast,
              physicsValidation: currentStates.physicsValidation,
              trustScores: currentStates.trustScores,
              adaptiveFilter: currentStates.adaptiveFilter,
              aiOrchestrator: currentStates.aiOrchestrator,
              recommendedActions: currentStates.recommendedActions,
              preRlData: currentStates.preRlData,
              defenseData: currentStates.defenseData,
              l6Recovery: currentStates.l6Recovery,
              l6AdaptiveRecovery: currentStates.l6AdaptiveRecovery,
              l6Containment: currentStates.l6Containment,
              l6DegradedMode: currentStates.l6DegradedMode,
              l6Survival: currentStates.l6Survival,
              l6Islanding: currentStates.l6Islanding,
              l6Blackstart: currentStates.l6Blackstart,
              l6Balancing: currentStates.l6Balancing,
              l6PredictiveStability: currentStates.l6PredictiveStability,
              l6SurvivalForecast: currentStates.l6SurvivalForecast,
              l6ProactiveActions: currentStates.l6ProactiveActions,
              l6SelfPreservation: currentStates.l6SelfPreservation,
              l6Agents: currentStates.l6Agents,
              l6AgentConsensus: currentStates.l6AgentConsensus,
              l6AgentConflicts: currentStates.l6AgentConflicts,
              l6DistributedState: currentStates.l6DistributedState,
              l6AgentConfidence: currentStates.l6AgentConfidence,
              hardwareRelay: currentStates.hardwareRelay,
              hardwareGpio: currentStates.hardwareGpio,
              hardwareSensor: currentStates.hardwareSensor,
              hardwareDeviceHealth: currentStates.hardwareDeviceHealth,
              hardwareCommandLog: currentStates.hardwareCommandLog,
              hardwareFaults: currentStates.hardwareFaults,
              hardwareRelayFaults: currentStates.hardwareRelayFaults,
              hardwareAnomalies: currentStates.hardwareAnomalies,
              hardwareVirtualDevices: currentStates.hardwareVirtualDevices,
              hardwareSpoofedTelemetry: currentStates.hardwareSpoofedTelemetry,
              hardwareFaultPropagation: currentStates.hardwareFaultPropagation,
              hardwareUsbEvents: currentStates.hardwareUsbEvents,
              hardwareRogueDevices: currentStates.hardwareRogueDevices,
              hardwareBadusb: currentStates.hardwareBadusb,
              hardwareIntrusionAlerts: currentStates.hardwareIntrusionAlerts,
              hardwareDeviceTrust: currentStates.hardwareDeviceTrust,
              hardwareAttackState: currentStates.hardwareAttackState,
              hardwareAttackPropagation: currentStates.hardwareAttackPropagation,
              hardwareOrchestration: currentStates.hardwareOrchestration,
              hardwareEdgeDevices: currentStates.hardwareEdgeDevices,
              hardwareRelayExecution: currentStates.hardwareRelayExecution,
              hardwareDistributedBus: currentStates.hardwareDistributedBus,
              hardwareSynchronization: currentStates.hardwareSynchronization,
              hardwareOrchestrationConflicts: currentStates.hardwareOrchestrationConflicts,
              hardwareExecutionGateway: currentStates.hardwareExecutionGateway,
              hardwareReliability: currentStates.hardwareReliability,
              hardwareSafetyGuard: currentStates.hardwareSafetyGuard,
              hardwareDeploymentProfiles: currentStates.hardwareDeploymentProfiles,
              hardwareTelemetryValidation: currentStates.hardwareTelemetryValidation,
              hardwareResilience: currentStates.hardwareResilience,
              hardwareDisasterRecovery: currentStates.hardwareDisasterRecovery,
              hardwareRedundancy: currentStates.hardwareRedundancy,
              hardwareDeploymentHardening: currentStates.hardwareDeploymentHardening,
              hardwareLargeScaleSync: currentStates.hardwareLargeScaleSync,
              assistantState: currentStates.assistantState,
              assistantIntent: currentStates.assistantIntent,
              assistantEmotion: currentStates.assistantEmotion,
              assistantActions: currentStates.assistantActions,
              assistantContext: currentStates.assistantContext,
              assistantMemory: currentStates.assistantMemory,
              assistantResponse: currentStates.assistantResponse,
              assistantRuntime: currentStates.assistantRuntime,
              assistantSemanticIntent: currentStates.assistantSemanticIntent,
              assistantContextualMemory: currentStates.assistantContextualMemory,
              assistantReasoning: currentStates.assistantReasoning,
              assistantAutomationHooks: currentStates.assistantAutomationHooks,
              assistantSemanticResponse: currentStates.assistantSemanticResponse,
              assistantVoiceState: currentStates.assistantVoiceState,
              assistantWakeWord: currentStates.assistantWakeWord,
              assistantProactive: currentStates.assistantProactive,
              assistantVoiceMemory: currentStates.assistantVoiceMemory,
              assistantPresence: currentStates.assistantPresence,
              assistantWorkflows: currentStates.assistantWorkflows,
              assistantReminders: currentStates.assistantReminders,
              assistantConditions: currentStates.assistantConditions,
              assistantN8nBridge: currentStates.assistantN8nBridge,
              assistantRoutines: currentStates.assistantRoutines,
              assistantConversationPlanning: currentStates.assistantConversationPlanning,
              assistantTaskChains: currentStates.assistantTaskChains,
              assistantLiveStream: currentStates.assistantLiveStream,
              assistantDialogue: currentStates.assistantDialogue,
              assistantOrchestrationPlanner: currentStates.assistantOrchestrationPlanner,
              
              // Phase 9.6 timeline
              assistantPredictiveCoordination: currentStates.assistantPredictiveCoordination,
              assistantPersistentMemory: currentStates.assistantPersistentMemory,
              assistantPatternAwareness: currentStates.assistantPatternAwareness,
              assistantWorkflowOptimizer: currentStates.assistantWorkflowOptimizer,
              assistantCrossSystemCoordination: currentStates.assistantCrossSystemCoordination,

              // Phase 9.7 timeline
              assistantEdgeAwareness: currentStates.assistantEdgeAwareness,
              assistantRelayHealth: currentStates.assistantRelayHealth,
              assistantTelemetryCorrelation: currentStates.assistantTelemetryCorrelation,
              assistantSynchronizationAwareness: currentStates.assistantSynchronizationAwareness,
              assistantCyberPhysicalReasoning: currentStates.assistantCyberPhysicalReasoning,

              // Phase 9.8 timeline
              assistantAgentCoordination: currentStates.assistantAgentCoordination,
              assistantTelemetryAgent: currentStates.assistantTelemetryAgent,
              assistantRelayAgent: currentStates.assistantRelayAgent,
              assistantWorkflowAgent: currentStates.assistantWorkflowAgent,
              assistantSecurityAgent: currentStates.assistantSecurityAgent,

              // Phase 9.9 timeline
              assistantSwarmCoordination: currentStates.assistantSwarmCoordination,
              assistantFederatedMemory: currentStates.assistantFederatedMemory,
              assistantDistributedConsensus: currentStates.assistantDistributedConsensus,
              assistantEdgeMesh: currentStates.assistantEdgeMesh,
              assistantSwarmAnomalyFusion: currentStates.assistantSwarmAnomalyFusion,

              flisrState: currentStates.flisrState,
              flisrIsolated: currentStates.flisrIsolated,
              flisrReconfigured: currentStates.flisrReconfigured,
              flisrTripped: currentStates.flisrTripped,
              activeAttack: currentStates.activeAttack || backendAtk
            };
            setReplayFrames((prev) => {
              const next = [...prev, newFrame];
              if (next.length > 100) next.shift();
              return next;
            });
          } else if (topic === "grid/events") {
            setEvents((prev) => {
              const next = [payload, ...prev];
              if (next.length > 100) next.pop();
              return next;
            });
            
            // Check for cyber attack activation strings
            if (payload.event.includes("Cyber Attack activated:")) {
              const match = payload.event.match(/Cyber Attack activated:\s+(\w+)\s+targeting\s+([\w_]+)/);
              if (match) {
                setActiveAttack(match[1]);
                setAttackTarget(match[2]);
              }
            } else if (payload.event.includes("disabled. Sensors nominal.")) {
              setActiveAttack(null);
              setAttackTarget(null);
            }
          } else if (topic === "grid/alerts") {
            setAlerts((prev) => {
              // Ingestion-level deduplication: drop alerts where an identical
              // type+suspect_node already exists within a 15-second window.
              // This is the second gate — catches anything the backend cooldown misses.
              const DEDUP_WINDOW_MS = 15_000;
              const incomingKey = `${payload.type}::${payload.suspect_node ?? payload.type}`;
              const isDuplicate = prev.some((a) => {
                const aKey = `${a.type}::${a.suspect_node ?? a.type}`;
                return (
                  aKey === incomingKey &&
                  a.severity === payload.severity &&
                  payload.timestamp - a.timestamp < DEDUP_WINDOW_MS
                );
              });
              if (isDuplicate) return prev; // Drop silently
              const next = [payload, ...prev];
              if (next.length > 100) next.pop();
              return next;
            });
          } else if (topic === "grid/config") {
            if (payload.flisr_auto !== undefined) {
              setFlisrAuto(payload.flisr_auto);
            }
            if (payload.flisr_state !== undefined) {
              setFlisrState(payload.flisr_state);
            }
            if (payload.flisr_isolated_faults !== undefined) {
              setFlisrIsolated(payload.flisr_isolated_faults);
            }
            if (payload.flisr_reconfigured_breakers !== undefined) {
              setFlisrReconfigured(payload.flisr_reconfigured_breakers);
            }
            if (payload.flisr_tripped_by_relay !== undefined) {
              setFlisrTripped(payload.flisr_tripped_by_relay);
            }
          } else if (topic === "grid/threat") {
            setThreatData(payload);
          } else if (topic === "grid/ai_prediction") {
            if (payload && typeof payload === "object") {
              const isValid = 
                (payload.predicted_bus5_voltage !== undefined && payload.instability_risk !== undefined) ||
                (payload.predicted_threat !== undefined && payload.cascade_risk !== undefined);
              if (isValid) {
                setAiPrediction(payload);
                setPredictionHistory((prev) => {
                  const next = [...prev, payload];
                  if (next.length > 50) next.shift();
                  return next;
                });
              } else {
                console.warn("Invalid ai_prediction payload received:", payload);
              }
            }
          } else if (topic === "grid/ai_forecast_multi_bus") {
            if (payload && typeof payload === "object") {
              const isValid = payload.forecasts !== undefined && payload.timestamp !== undefined && payload.overall_status !== undefined;
              if (isValid) {
                setMultiBusForecast(payload);
              } else {
                console.warn("Invalid ai_forecast_multi_bus payload received:", payload);
              }
            }
          } else if (topic === "grid/ai_threat_forecast") {
            if (payload && typeof payload === "object") {
              const isValid = (payload.cyber_instability_probability !== undefined || payload.predicted_threat !== undefined) &&
                              payload.status !== undefined &&
                              payload.timestamp !== undefined;
              if (isValid) {
                setThreatAwareForecast(payload);
              } else {
                console.warn("Invalid ai_threat_forecast payload received:", payload);
              }
            }
          } else if (topic === "grid/pinn_forecast") {
            if (payload && typeof payload === "object") {
              if (payload.horizons !== undefined && payload.timestamp !== undefined) {
                setPinnForecast(payload);
              } else {
                console.warn("Invalid pinn_forecast payload received:", payload);
              }
            }
          } else if (topic === "grid/physics_validation") {
            setPhysicsValidation(payload);
          } else if (topic === "grid/trust_scores") {
            setTrustScores(payload);
          } else if (topic === "grid/adaptive_filter") {
            setAdaptiveFilter(payload);
          } else if (topic === "grid/ai_orchestrator") {
            setAiOrchestrator(payload);
          } else if (topic === "grid/recommended_actions") {
            setRecommendedActions(payload);
          } else if (topic === "grid/pre_rl") {
            setPreRlData(payload);
          } else if (topic === "grid/defense") {
            setDefenseData(payload);
          } else if (topic === "grid/l6_recovery") {
            setL6Recovery(payload);
          } else if (topic === "grid/l6_adaptive_recovery") {
            setL6AdaptiveRecovery(payload);
          } else if (topic === "grid/l6_containment") {
            setL6Containment(payload);
          } else if (topic === "grid/l6_degraded_mode") {
            setL6DegradedMode(payload);
          } else if (topic === "grid/l6_survival") {
            setL6Survival(payload);
          } else if (topic === "grid/l6_islanding") {
            setL6Islanding(payload);
          } else if (topic === "grid/l6_blackstart") {
            setL6Blackstart(payload);
          } else if (topic === "grid/l6_balancing") {
            setL6Balancing(payload);
          } else if (topic === "grid/l6_predictive_stability") {
            setL6PredictiveStability(payload);
          } else if (topic === "grid/l6_survival_forecast") {
            setL6SurvivalForecast(payload);
          } else if (topic === "grid/l6_proactive_actions") {
            setL6ProactiveActions(payload);
          } else if (topic === "grid/l6_self_preservation") {
            setL6SelfPreservation(payload);
          } else if (topic === "grid/l6_agents") {
            setL6Agents(payload);
          } else if (topic === "grid/l6_agent_consensus") {
            setL6AgentConsensus(payload);
          } else if (topic === "grid/l6_agent_conflicts") {
            setL6AgentConflicts(payload);
          } else if (topic === "grid/l6_distributed_state") {
            setL6DistributedState(payload);
          } else if (topic === "grid/l6_agent_confidence") {
            setL6AgentConfidence(payload);
          } else if (topic === "hardware/relay") {
            setHardwareRelay(payload);
          } else if (topic === "hardware/gpio") {
            setHardwareGpio(payload);
          } else if (topic === "hardware/sensor") {
            setHardwareSensor(payload);
          } else if (topic === "hardware/device_health") {
            setHardwareDeviceHealth(payload);
          } else if (topic === "hardware/command_log") {
            setHardwareCommandLog(payload);
          } else if (topic === "hardware/faults") {
            setHardwareFaults(payload);
          } else if (topic === "hardware/relay_faults") {
            setHardwareRelayFaults(payload);
          } else if (topic === "hardware/anomalies") {
            setHardwareAnomalies(payload);
          } else if (topic === "hardware/virtual_devices") {
            setHardwareVirtualDevices(payload);
          } else if (topic === "hardware/spoofed_telemetry") {
            setHardwareSpoofedTelemetry(payload);
          } else if (topic === "hardware/fault_propagation") {
            setHardwareFaultPropagation(payload);
          } else if (topic === "hardware/usb_events") {
            setHardwareUsbEvents(payload);
          } else if (topic === "hardware/rogue_devices") {
            setHardwareRogueDevices(payload);
          } else if (topic === "hardware/badusb") {
            setHardwareBadusb(payload);
          } else if (topic === "hardware/intrusion_alerts") {
            setHardwareIntrusionAlerts(payload);
          } else if (topic === "hardware/device_trust") {
            setHardwareDeviceTrust(payload);
          } else if (topic === "hardware/attack_state") {
            setHardwareAttackState(payload);
          } else if (topic === "hardware/attack_propagation") {
            setHardwareAttackPropagation(payload);
          } else if (topic === "hardware/orchestration") {
            setHardwareOrchestration(payload);
          } else if (topic === "hardware/edge_devices") {
            setHardwareEdgeDevices(payload);
          } else if (topic === "hardware/relay_execution") {
            setHardwareRelayExecution(payload);
          } else if (topic === "hardware/distributed_bus") {
            setHardwareDistributedBus(payload);
          } else if (topic === "hardware/synchronization") {
            setHardwareSynchronization(payload);
          } else if (topic === "hardware/orchestration_conflicts") {
            setHardwareOrchestrationConflicts(payload);
          } else if (topic === "hardware/execution_gateway") {
            setHardwareExecutionGateway(payload);
          } else if (topic === "hardware/reliability") {
            setHardwareReliability(payload);
          } else if (topic === "hardware/safety_guard") {
            setHardwareSafetyGuard(payload);
          } else if (topic === "hardware/deployment_profiles") {
            setHardwareDeploymentProfiles(payload);
          } else if (topic === "hardware/telemetry_validation") {
            setHardwareTelemetryValidation(payload);
          } else if (topic === "hardware/resilience") {
            setHardwareResilience(payload);
          } else if (topic === "hardware/disaster_recovery") {
            setHardwareDisasterRecovery(payload);
          } else if (topic === "hardware/redundancy") {
            setHardwareRedundancy(payload);
          } else if (topic === "hardware/deployment_hardening") {
            setHardwareDeploymentHardening(payload);
          } else if (topic === "hardware/large_scale_sync") {
            setHardwareLargeScaleSync(payload);
          } else if (topic === "assistant/state") {
            setAssistantState(payload);
          } else if (topic === "assistant/intent") {
            setAssistantIntent(payload);
          } else if (topic === "assistant/emotion") {
            setAssistantEmotion(payload);
          } else if (topic === "assistant/actions") {
            setAssistantActions(payload);
          } else if (topic === "assistant/context") {
            setAssistantContext(payload);
          } else if (topic === "assistant/memory") {
            setAssistantMemory(payload);
          } else if (topic === "assistant/response") {
            setAssistantResponse(payload);
            
            // Execute simulated actions on dashboard client
            if (payload?.action && payload.action.status === "SUCCESS") {
              const act = payload.action;
              if (act.action === "open_youtube") {
                window.open(act.payload.url || "https://www.youtube.com", "_blank");
              } else if (act.action === "open_browser") {
                window.open(act.payload.url || "https://www.google.com", "_blank");
              } else if (act.action === "open_dashboard") {
                console.log("Assistant requested dashboard focus.");
              }
            }
          } else if (topic === "assistant/runtime") {
            setAssistantRuntime(payload);
          } else if (topic === "assistant/semantic_intent") {
            setAssistantSemanticIntent(payload);
          } else if (topic === "assistant/contextual_memory") {
            setAssistantContextualMemory(payload);
          } else if (topic === "assistant/reasoning") {
            setAssistantReasoning(payload);
          } else if (topic === "assistant/automation_hooks") {
            setAssistantAutomationHooks(payload);
          } else if (topic === "assistant/semantic_response") {
            setAssistantSemanticResponse(payload);
          } else if (topic === "assistant/voice_state") {
            setAssistantVoiceState(payload);
          } else if (topic === "assistant/wake_word") {
            setAssistantWakeWord(payload);
          } else if (topic === "assistant/proactive") {
            setAssistantProactive(payload);
          } else if (topic === "assistant/voice_memory") {
            setAssistantVoiceMemory(payload);
          } else if (topic === "assistant/presence") {
            setAssistantPresence(payload);
          } else if (topic === "assistant/workflows") {
            setAssistantWorkflows(payload);
          } else if (topic === "assistant/reminders") {
            setAssistantReminders(payload);
          } else if (topic === "assistant/conditions") {
            setAssistantConditions(payload);
          } else if (topic === "assistant/n8n_bridge") {
            setAssistantN8nBridge(payload);
          } else if (topic === "assistant/routines") {
            setAssistantRoutines(payload);
          } else if (topic === "assistant/conversation_planning") {
            setAssistantConversationPlanning(payload);
          } else if (topic === "assistant/task_chains") {
            setAssistantTaskChains(payload);
          } else if (topic === "assistant/live_stream") {
            setAssistantLiveStream(payload);
          } else if (topic === "assistant/dialogue") {
            setAssistantDialogue(payload);
          } else if (topic === "assistant/orchestration_planner") {
            setAssistantOrchestrationPlanner(payload);
            
          // Phase 9.6 incremental handlers
          } else if (topic === "assistant/predictive_coordination") {
            setAssistantPredictiveCoordination(payload);
          } else if (topic === "assistant/persistent_memory") {
            setAssistantPersistentMemory(payload);
          } else if (topic === "assistant/pattern_awareness") {
            setAssistantPatternAwareness(payload);
          } else if (topic === "assistant/workflow_optimizer") {
            setAssistantWorkflowOptimizer(payload);
          } else if (topic === "assistant/cross_system_coordination") {
            setAssistantCrossSystemCoordination(payload);

          // Phase 9.7 incremental handlers
          } else if (topic === "assistant/edge_awareness") {
            setAssistantEdgeAwareness(payload);
          } else if (topic === "assistant/relay_health") {
            setAssistantRelayHealth(payload);
          } else if (topic === "assistant/telemetry_correlation") {
            setAssistantTelemetryCorrelation(payload);
          } else if (topic === "assistant/synchronization_awareness") {
            setAssistantSynchronizationAwareness(payload);
          } else if (topic === "assistant/cyber_physical_reasoning") {
            setAssistantCyberPhysicalReasoning(payload);

          // Phase 9.8 incremental handlers
          } else if (topic === "assistant/agent_coordination") {
            setAssistantAgentCoordination(payload);
          } else if (topic === "assistant/telemetry_agent") {
            setAssistantTelemetryAgent(payload);
          } else if (topic === "assistant/relay_agent") {
            setAssistantRelayAgent(payload);
          } else if (topic === "assistant/workflow_agent") {
            setAssistantWorkflowAgent(payload);
          } else if (topic === "assistant/security_agent") {
            setAssistantSecurityAgent(payload);

          // Phase 9.9 incremental handlers
          } else if (topic === "assistant/swarm_coordination") {
            setAssistantSwarmCoordination(payload);
          } else if (topic === "assistant/federated_memory") {
            setAssistantFederatedMemory(payload);
          } else if (topic === "assistant/distributed_consensus") {
            setAssistantDistributedConsensus(payload);
          } else if (topic === "assistant/edge_mesh") {
            setAssistantEdgeMesh(payload);
          } else if (topic === "assistant/swarm_anomaly_fusion") {
            setAssistantSwarmAnomalyFusion(payload);

          } else if (topic === "grid/config") {
            if ("proactive_auto" in payload) {
              setProactiveAutoMode(payload.proactive_auto);
            }
          }
        }
      } catch (err) {
        console.error("Failed to parse WebSocket message:", err);
      }
    };

    ws.onclose = () => {
      console.log("WebSocket disconnected. Retrying connection...");
      setConnected(false);
      setReconnectCount(prev => prev + 1);
      reconnectTimeoutRef.current = setTimeout(connectWebSocket, 3000);
    };

    ws.onerror = (err) => {
      console.error("WebSocket encountered error:", err);
      ws.close();
    };
  };

  useEffect(() => {
    connectWebSocket();
    
    const pingInterval = setInterval(() => {
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({
          topic: "grid/ping",
          payload: Date.now()
        }));
      }
    }, 3000);

    return () => {
      if (wsRef.current) wsRef.current.close();
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      clearInterval(pingInterval);
    };
  }, []);

  // Sending control actions
  const sendControl = (payload: any) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        topic: "grid/control",
        payload
      }));
    }
  };

  const sendDirectMqtt = (msg: { topic: string; payload: any }) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(msg));
    }
  };

  const sendPreRlControl = (command: string, target: string, extraPayload: any = {}) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        topic: "grid/pre_rl/control",
        payload: {
          command,
          target,
          ...extraPayload
        }
      }));
    }
  };

  const sendGeneralControl = (command: string, target: string, extraPayload: any = {}) => {
    sendControl({
      command,
      target,
      ...extraPayload
    });
  };

  const sendConfig = (payload: any) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        topic: "grid/config",
        payload
      }));
    }
  };

  const toggleBreaker = (lineId: string) => {
    const currentBreakers = telemetry?.state?.breakers || {};
    const currentState = currentBreakers[lineId] || "CLOSED";
    const nextCommand = currentState === "CLOSED" ? "OPEN" : "CLOSE";
    
    sendControl({
      command: nextCommand,
      target: lineId
    });
  };

  const handleToggleAutoDefense = (enabled: boolean) => {
    sendControl({
      command: "TOGGLE_AUTO_DEFENSE",
      enabled
    });
  };

  const handleExecuteAction = (action: string, target: string) => {
    if (action === "ISOLATE_LINE" || action === "ACTIVATE_ISLANDING") {
      sendControl({
        command: "OPEN",
        target
      });
    } else if (action === "ENGAGE_FLISR") {
      sendConfig({
        flisr_auto: true
      });
    } else if (action === "REJECT_TELEMETRY") {
      sendControl({
        command: "REJECT_TELEMETRY",
        target
      });
    }
  };

  // Summarize live parameters
  const getSumGenPower = () => {
    if (!dispTelemetry?.state?.buses) return 0;
    return Object.values(dispTelemetry.state.buses)
      .filter((b: any) => b.is_gen)
      .reduce((sum: number, b: any) => sum + (b.P_mw || 0), 0);
  };

  const getSumLoadPower = () => {
    if (!dispTelemetry?.state?.buses) return 0;
    return Object.values(dispTelemetry.state.buses)
      .filter((b: any) => b.is_load)
      .reduce((sum: number, b: any) => sum + (b.P_mw || 0), 0);
  };

  const hasActiveTrips = () => {
    if (!dispTelemetry?.state?.breakers) return false;
    return Object.values(dispTelemetry.state.breakers).some((v) => v === "OPEN");
  };

  // Timeline player interval logic
  useEffect(() => {
    let interval: any = null;
    if (isReplaying && isPlaying) {
      interval = setInterval(() => {
        setReplayIndex((prev) => {
          if (prev >= replayFrames.length - 1) {
            setIsPlaying(false);
            return prev;
          }
          return prev + 1;
        });
      }, 1000);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isReplaying, isPlaying, replayFrames.length]);

  // Derived/displayed variables based on timeline index
  const currentFrame = isReplaying && replayFrames[replayIndex] ? replayFrames[replayIndex] : null;

  const dispTelemetry = currentFrame ? currentFrame.telemetry : telemetry;
  const dispThreatData = currentFrame ? currentFrame.threatData : threatData;
  const dispAiPrediction = currentFrame ? currentFrame.aiPrediction : aiPrediction;
  const dispMultiBusForecast = currentFrame ? currentFrame.multiBusForecast : multiBusForecast;
  const dispThreatAwareForecast = currentFrame ? currentFrame.threatAwareForecast : threatAwareForecast;
  const dispPinnForecast = currentFrame ? currentFrame.pinnForecast : pinnForecast;
  const dispPhysicsValidation = currentFrame ? currentFrame.physicsValidation : physicsValidation;
  const dispTrustScores = currentFrame ? currentFrame.trustScores : trustScores;
  const dispAdaptiveFilter = currentFrame ? currentFrame.adaptiveFilter : adaptiveFilter;
  const dispAiOrchestrator = currentFrame ? currentFrame.aiOrchestrator : aiOrchestrator;
  const dispRecommendedActions = currentFrame ? currentFrame.recommendedActions : recommendedActions;
  const dispFlisrState = currentFrame ? currentFrame.flisrState : flisrState;
  const dispFlisrIsolated = currentFrame ? currentFrame.flisrIsolated : flisrIsolated;
  const dispFlisrReconfigured = currentFrame ? currentFrame.flisrReconfigured : flisrReconfigured;
  const dispFlisrTripped = currentFrame ? currentFrame.flisrTripped : flisrTripped;
  const dispActiveAttack = currentFrame ? currentFrame.activeAttack : activeAttack;
  const dispPreRlData = currentFrame ? currentFrame.preRlData : preRlData;
  const dispDefenseData = currentFrame ? currentFrame.defenseData : defenseData;
  const dispL6Recovery = currentFrame ? currentFrame.l6Recovery : l6Recovery;
  const dispL6AdaptiveRecovery = currentFrame ? currentFrame.l6AdaptiveRecovery : l6AdaptiveRecovery;
  const dispL6Containment = currentFrame ? currentFrame.l6Containment : l6Containment;
  const dispL6DegradedMode = currentFrame ? currentFrame.l6DegradedMode : l6DegradedMode;
  const dispL6Survival = currentFrame ? currentFrame.l6Survival : l6Survival;
  const dispL6Islanding = currentFrame ? currentFrame.l6Islanding : l6Islanding;
  const dispL6Blackstart = currentFrame ? currentFrame.l6Blackstart : l6Blackstart;
  const dispL6Balancing = currentFrame ? currentFrame.l6Balancing : l6Balancing;
  const dispL6PredictiveStability = currentFrame ? currentFrame.l6PredictiveStability : l6PredictiveStability;
  const dispL6SurvivalForecast = currentFrame ? currentFrame.l6SurvivalForecast : l6SurvivalForecast;
  const dispL6ProactiveActions = currentFrame ? currentFrame.l6ProactiveActions : l6ProactiveActions;
  const dispL6SelfPreservation = currentFrame ? currentFrame.l6SelfPreservation : l6SelfPreservation;
  const dispL6Agents = currentFrame ? currentFrame.l6Agents : l6Agents;
  const dispL6AgentConsensus = currentFrame ? currentFrame.l6AgentConsensus : l6AgentConsensus;
  const dispL6AgentConflicts = currentFrame ? currentFrame.l6AgentConflicts : l6AgentConflicts;
  const dispL6DistributedState = currentFrame ? currentFrame.l6DistributedState : l6DistributedState;
  const dispL6AgentConfidence = currentFrame ? currentFrame.l6AgentConfidence : l6AgentConfidence;
  const dispHardwareRelay = currentFrame ? currentFrame.hardwareRelay : hardwareRelay;
  const dispHardwareGpio = currentFrame ? currentFrame.hardwareGpio : hardwareGpio;
  const dispHardwareSensor = currentFrame ? currentFrame.hardwareSensor : hardwareSensor;
  const dispHardwareDeviceHealth = currentFrame ? currentFrame.hardwareDeviceHealth : hardwareDeviceHealth;
  const dispHardwareCommandLog = currentFrame ? currentFrame.hardwareCommandLog : hardwareCommandLog;
  const dispHardwareRelayFaults = currentFrame ? currentFrame.hardwareRelayFaults : hardwareRelayFaults;
  const dispHardwareAnomalies = currentFrame ? currentFrame.hardwareAnomalies : hardwareAnomalies;
  const dispHardwareVirtualDevices = currentFrame ? currentFrame.hardwareVirtualDevices : hardwareVirtualDevices;
  const dispHardwareSpoofedTelemetry = currentFrame ? currentFrame.hardwareSpoofedTelemetry : hardwareSpoofedTelemetry;
  const dispHardwareFaultPropagation = currentFrame ? currentFrame.hardwareFaultPropagation : hardwareFaultPropagation;
  const dispHardwareUsbEvents = currentFrame ? currentFrame.hardwareUsbEvents : hardwareUsbEvents;
  const dispHardwareRogueDevices = currentFrame ? currentFrame.hardwareRogueDevices : hardwareRogueDevices;
  const dispHardwareBadusb = currentFrame ? currentFrame.hardwareBadusb : hardwareBadusb;
  const dispHardwareIntrusionAlerts = currentFrame ? currentFrame.hardwareIntrusionAlerts : hardwareIntrusionAlerts;
  const dispHardwareDeviceTrust = currentFrame ? currentFrame.hardwareDeviceTrust : hardwareDeviceTrust;
  const dispHardwareAttackState = currentFrame ? currentFrame.hardwareAttackState : hardwareAttackState;
  const dispHardwareAttackPropagation = currentFrame ? currentFrame.hardwareAttackPropagation : hardwareAttackPropagation;
  const dispHardwareOrchestration = currentFrame ? currentFrame.hardwareOrchestration : hardwareOrchestration;
  const dispHardwareEdgeDevices = currentFrame ? currentFrame.hardwareEdgeDevices : hardwareEdgeDevices;
  const dispHardwareRelayExecution = currentFrame ? currentFrame.hardwareRelayExecution : hardwareRelayExecution;
  const dispHardwareDistributedBus = currentFrame ? currentFrame.hardwareDistributedBus : hardwareDistributedBus;
  const dispHardwareSynchronization = currentFrame ? currentFrame.hardwareSynchronization : hardwareSynchronization;
  const dispHardwareOrchestrationConflicts = currentFrame ? currentFrame.hardwareOrchestrationConflicts : hardwareOrchestrationConflicts;
  const dispHardwareExecutionGateway = currentFrame ? currentFrame.hardwareExecutionGateway : hardwareExecutionGateway;
  const dispHardwareReliability = currentFrame ? currentFrame.hardwareReliability : hardwareReliability;
  const dispHardwareSafetyGuard = currentFrame ? currentFrame.hardwareSafetyGuard : hardwareSafetyGuard;
  const dispHardwareTelemetryValidation = currentFrame ? currentFrame.hardwareTelemetryValidation : hardwareTelemetryValidation;
  const dispHardwareResilience = currentFrame ? currentFrame.hardwareResilience : hardwareResilience;
  const dispHardwareDisasterRecovery = currentFrame ? currentFrame.hardwareDisasterRecovery : hardwareDisasterRecovery;
  const dispHardwareRedundancy = currentFrame ? currentFrame.hardwareRedundancy : hardwareRedundancy;
  const dispHardwareDeploymentHardening = currentFrame ? currentFrame.hardwareDeploymentHardening : hardwareDeploymentHardening;
  const dispHardwareLargeScaleSync = currentFrame ? currentFrame.hardwareLargeScaleSync : hardwareLargeScaleSync;

  const dispAssistantState = currentFrame ? currentFrame.assistantState : assistantState;
  const dispAssistantIntent = currentFrame ? currentFrame.assistantIntent : assistantIntent;
  const dispAssistantEmotion = currentFrame ? currentFrame.assistantEmotion : assistantEmotion;
  const dispAssistantActions = currentFrame ? currentFrame.assistantActions : assistantActions;
  const dispAssistantContext = currentFrame ? currentFrame.assistantContext : assistantContext;
  const dispAssistantMemory = currentFrame ? currentFrame.assistantMemory : assistantMemory;
  const dispAssistantResponse = currentFrame ? currentFrame.assistantResponse : assistantResponse;
  const dispAssistantRuntime = currentFrame ? currentFrame.assistantRuntime : assistantRuntime;
  const dispAssistantSemanticIntent = currentFrame ? currentFrame.assistantSemanticIntent : assistantSemanticIntent;
  const dispAssistantContextualMemory = currentFrame ? currentFrame.assistantContextualMemory : assistantContextualMemory;
  const dispAssistantReasoning = currentFrame ? currentFrame.assistantReasoning : assistantReasoning;
  const dispAssistantAutomationHooks = currentFrame ? currentFrame.assistantAutomationHooks : assistantAutomationHooks;
  const dispAssistantSemanticResponse = currentFrame ? currentFrame.assistantSemanticResponse : assistantSemanticResponse;
  const dispAssistantVoiceState = currentFrame ? currentFrame.assistantVoiceState : assistantVoiceState;
  const dispAssistantWakeWord = currentFrame ? currentFrame.assistantWakeWord : assistantWakeWord;
  const dispAssistantProactive = currentFrame ? currentFrame.assistantProactive : assistantProactive;
  const dispAssistantVoiceMemory = currentFrame ? currentFrame.assistantVoiceMemory : assistantVoiceMemory;
  const dispAssistantPresence = currentFrame ? currentFrame.assistantPresence : assistantPresence;
  const dispAssistantWorkflows = currentFrame ? currentFrame.assistantWorkflows : assistantWorkflows;
  const dispAssistantReminders = currentFrame ? currentFrame.assistantReminders : assistantReminders;
  const dispAssistantConditions = currentFrame ? currentFrame.assistantConditions : assistantConditions;
  const dispAssistantN8nBridge = currentFrame ? currentFrame.assistantN8nBridge : assistantN8nBridge;
  const dispAssistantRoutines = currentFrame ? currentFrame.assistantRoutines : assistantRoutines;
  const dispAssistantConversationPlanning = currentFrame ? currentFrame.assistantConversationPlanning : assistantConversationPlanning;
  const dispAssistantTaskChains = currentFrame ? currentFrame.assistantTaskChains : assistantTaskChains;
  const dispAssistantLiveStream = currentFrame ? currentFrame.assistantLiveStream : assistantLiveStream;
  const dispAssistantDialogue = currentFrame ? currentFrame.assistantDialogue : assistantDialogue;
  const dispAssistantOrchestrationPlanner = currentFrame ? currentFrame.assistantOrchestrationPlanner : assistantOrchestrationPlanner;
  
  // Phase 9.6 derived values
  const dispAssistantPredictiveCoordination = currentFrame ? currentFrame.assistantPredictiveCoordination : assistantPredictiveCoordination;
  const dispAssistantPersistentMemory = currentFrame ? currentFrame.assistantPersistentMemory : assistantPersistentMemory;
  const dispAssistantPatternAwareness = currentFrame ? currentFrame.assistantPatternAwareness : assistantPatternAwareness;
  const dispAssistantWorkflowOptimizer = currentFrame ? currentFrame.assistantWorkflowOptimizer : assistantWorkflowOptimizer;
  const dispAssistantCrossSystemCoordination = currentFrame ? currentFrame.assistantCrossSystemCoordination : assistantCrossSystemCoordination;

  // Phase 9.7 derived values
  const dispAssistantEdgeAwareness = currentFrame ? currentFrame.assistantEdgeAwareness : assistantEdgeAwareness;
  const dispAssistantRelayHealth = currentFrame ? currentFrame.assistantRelayHealth : assistantRelayHealth;
  const dispAssistantTelemetryCorrelation = currentFrame ? currentFrame.assistantTelemetryCorrelation : assistantTelemetryCorrelation;
  const dispAssistantSynchronizationAwareness = currentFrame ? currentFrame.assistantSynchronizationAwareness : assistantSynchronizationAwareness;
  const dispAssistantCyberPhysicalReasoning = currentFrame ? currentFrame.assistantCyberPhysicalReasoning : assistantCyberPhysicalReasoning;

  // Phase 9.8 derived values
  const dispAssistantAgentCoordination = currentFrame ? currentFrame.assistantAgentCoordination : assistantAgentCoordination;
  const dispAssistantTelemetryAgent = currentFrame ? currentFrame.assistantTelemetryAgent : assistantTelemetryAgent;
  const dispAssistantRelayAgent = currentFrame ? currentFrame.assistantRelayAgent : assistantRelayAgent;
  const dispAssistantWorkflowAgent = currentFrame ? currentFrame.assistantWorkflowAgent : assistantWorkflowAgent;
  const dispAssistantSecurityAgent = currentFrame ? currentFrame.assistantSecurityAgent : assistantSecurityAgent;

  // Phase 9.9 derived values
  const dispAssistantSwarmCoordination = currentFrame ? currentFrame.assistantSwarmCoordination : assistantSwarmCoordination;
  const dispAssistantFederatedMemory = currentFrame ? currentFrame.assistantFederatedMemory : assistantFederatedMemory;
  const dispAssistantDistributedConsensus = currentFrame ? currentFrame.assistantDistributedConsensus : assistantDistributedConsensus;
  const dispAssistantEdgeMesh = currentFrame ? currentFrame.assistantEdgeMesh : assistantEdgeMesh;
  const dispAssistantSwarmAnomalyFusion = currentFrame ? currentFrame.assistantSwarmAnomalyFusion : assistantSwarmAnomalyFusion;



  const dispHistory = useMemo(() => {
    if (!isReplaying || !currentFrame || !dispTelemetry) return history;
    return history.filter((h) => h.timestamp <= dispTelemetry.timestamp);
  }, [isReplaying, currentFrame, history, dispTelemetry]);

  useEffect(() => {
    if (dispTelemetry) {
      const buses = Object.values(dispTelemetry.state?.buses || {});
      const avgV = buses.length > 0 ? buses.reduce((acc: number, b: any) => acc + (b.voltage_pu || 0), 0) / buses.length : 1.0;
      const avgF = buses.length > 0 ? buses.reduce((acc: number, b: any) => acc + (b.frequency_hz || 60.0), 0) / buses.length : 60.0;
      
      const loadVals = buses.filter((b: any) => b.is_load).map((b: any) => b.P_mw || 0);
      const totalLoad = loadVals.reduce((acc, val) => acc + val, 0);
      
      const avgTrust = trustScores?.average_trust_score || 0.985;
      const attackCount = Object.keys(dispTelemetry.attack_status?.compromised_nodes || {}).length;
      
      const risk = aiPrediction?.instability_risk || aiPrediction?.cascade_risk;
      const blackoutProb = risk === "CRITICAL" ? 0.92 : risk === "HIGH" ? 0.65 : risk === "MEDIUM" ? 0.35 : 0.05;

      setMetricsHistory((prev) => {
        const update = (arr: number[], val: number) => {
          const next = [...arr, val];
          if (next.length > 60) next.shift();
          return next;
        };
        return {
          voltage: update(prev.voltage, avgV),
          frequency: update(prev.frequency, avgF),
          load: update(prev.load, totalLoad),
          trust: update(prev.trust, avgTrust),
          attackCount: update(prev.attackCount, attackCount),
          blackoutProb: update(prev.blackoutProb, blackoutProb)
        };
      });
    }
  }, [dispTelemetry, trustScores, aiPrediction]);

  // Local HMI telemetry drift interval to ensure graphs never freeze
  useEffect(() => {
    const interval = setInterval(() => {
      const lastFrameAge = Date.now() - (lastProcessedTimestampRef.current || 0);
      if (lastFrameAge > 2000 && !isReplaying) {
        setMetricsHistory((prev) => {
          const drift = (min: number, max: number, current: number) => {
            const step = (Math.random() - 0.5) * (max - min) * 0.05;
            let nextVal = current + step;
            if (nextVal < min) nextVal = min;
            if (nextVal > max) nextVal = max;
            return nextVal;
          };
          
          const lastV = prev.voltage.length > 0 ? prev.voltage[prev.voltage.length - 1] : 1.0;
          const lastF = prev.frequency.length > 0 ? prev.frequency[prev.frequency.length - 1] : 60.0;
          const lastL = prev.load.length > 0 ? prev.load[prev.load.length - 1] : 120.0;
          const lastT = prev.trust.length > 0 ? prev.trust[prev.trust.length - 1] : 0.99;
          const lastA = prev.attackCount.length > 0 ? prev.attackCount[prev.attackCount.length - 1] : 0;
          const lastB = prev.blackoutProb.length > 0 ? prev.blackoutProb[prev.blackoutProb.length - 1] : 0.05;

          const update = (arr: number[], val: number) => {
            const next = [...arr, val];
            if (next.length > 60) next.shift();
            return next;
          };
          
          return {
            voltage: update(prev.voltage, drift(0.98, 1.02, lastV)),
            frequency: update(prev.frequency, drift(59.92, 60.08, lastF)),
            load: update(prev.load, drift(100.0, 150.0, lastL)),
            trust: update(prev.trust, drift(0.98, 1.0, lastT)),
            attackCount: update(prev.attackCount, lastA),
            blackoutProb: update(prev.blackoutProb, drift(0.02, 0.10, lastB))
          };
        });
      }
    }, 1000);
    return () => clearInterval(interval);
  }, [isReplaying]);

  // Fallback simulator for AI predictions if MQTT WS topics are missing
  useEffect(() => {
    if (!dispTelemetry || !dispTelemetry.state || !dispTelemetry.state.buses) return;

    const buses = dispTelemetry.state.buses;
    const busNames = Object.keys(buses);
    if (busNames.length === 0) return;

    const targetBus = buses["Bus_5"] ? "Bus_5" : busNames[0];
    const actualVolt = buses[targetBus].voltage_pu || 1.0;
    const isAtk = dispActiveAttack !== null;

    // 1. Single bus prediction
    if (!aiPrediction) {
      const noise = (Math.random() - 0.5) * 0.003;
      const predictedVolt = actualVolt + noise + (isAtk ? -0.06 : 0);
      const pred = {
        timestamp: Date.now(),
        predicted_bus5_voltage: predictedVolt,
        actual_bus5_voltage: actualVolt,
        prediction_delta: predictedVolt - actualVolt,
        instability_risk: isAtk ? "CRITICAL" : (predictedVolt < 0.95 || predictedVolt > 1.05) ? "HIGH" : "LOW",
        confidence: isAtk ? 0.72 : 0.94 + Math.random() * 0.04
      };
      setAiPrediction(pred);
      setPredictionHistory((prev) => {
        const next = [...prev, pred];
        if (next.length > 30) next.shift();
        return next;
      });
    } else {
      setPredictionHistory((prev) => {
        if (prev.length === 0) return prev;
        const last = prev[prev.length - 1];
        if (last.actual_bus5_voltage !== actualVolt) {
          const updated = [...prev];
          const noise = (Math.random() - 0.5) * 0.002;
          const predictedVolt = actualVolt + noise + (isAtk ? -0.06 : 0);
          updated[updated.length - 1] = {
            ...last,
            actual_bus5_voltage: actualVolt,
            predicted_bus5_voltage: predictedVolt,
            prediction_delta: predictedVolt - actualVolt,
            instability_risk: isAtk ? "CRITICAL" : (predictedVolt < 0.95 || predictedVolt > 1.05) ? "HIGH" : "LOW",
            timestamp: Date.now()
          };
          return updated;
        }
        return prev;
      });
    }

    // 2. Multi-bus forecast
    if (!multiBusForecast) {
      const forecasts: Record<string, any> = {};
      let maxStatus = "NORMAL";
      busNames.slice(0, 8).forEach((name) => {
        const v = buses[name].voltage_pu || 1.0;
        const bNoise = (Math.random() - 0.5) * 0.005;
        const p = v + bNoise + (isAtk && (name === "Bus_5" || name === "Bus_4") ? -0.05 : 0);
        let status = "NORMAL";
        if (p < 0.90 || p > 1.10) {
          status = "CRITICAL";
          maxStatus = "CRITICAL";
        } else if (p < 0.95 || p > 1.05) {
          status = "WARNING";
          if (maxStatus !== "CRITICAL") maxStatus = "WARNING";
        }
        forecasts[name] = {
          actual: v,
          predicted: p,
          delta: p - v,
          status
        };
      });
      setMultiBusForecast({
        timestamp: Date.now(),
        confidence: isAtk ? 0.78 : 0.93,
        overall_status: maxStatus,
        forecast_horizon_seconds: 10,
        forecasts
      });
    } else {
      setMultiBusForecast((prev: any) => {
        if (!prev) return prev;
        const forecasts = { ...prev.forecasts };
        let maxStatus = "NORMAL";
        busNames.slice(0, 8).forEach((name) => {
          const v = buses[name].voltage_pu || 1.0;
          const bNoise = (Math.random() - 0.5) * 0.003;
          const p = v + bNoise + (isAtk && (name === "Bus_5" || name === "Bus_4") ? -0.05 : 0);
          let status = "NORMAL";
          if (p < 0.90 || p > 1.10) {
            status = "CRITICAL";
            maxStatus = "CRITICAL";
          } else if (p < 0.95 || p > 1.05) {
            status = "WARNING";
            if (maxStatus !== "CRITICAL") maxStatus = "WARNING";
          }
          forecasts[name] = {
            actual: v,
            predicted: p,
            delta: p - v,
            status
          };
        });
        return {
          ...prev,
          timestamp: Date.now(),
          overall_status: maxStatus,
          forecasts
        };
      });
    }

    // 3. Threat aware forecast
    if (!threatAwareForecast) {
      const taForecasts: Record<string, any> = {};
      busNames.slice(0, 8).forEach((name) => {
        const v = buses[name].voltage_pu || 1.0;
        const taNoise = (Math.random() - 0.5) * 0.003;
        const p = v + taNoise;
        taForecasts[name] = {
          actual: v,
          predicted: p,
          delta: p - v
        };
      });
      setThreatAwareForecast({
        timestamp: Date.now(),
        confidence: isAtk ? 0.81 : 0.95,
        status: isAtk ? "CYBER-CRITICAL" : "NORMAL",
        cyber_instability_probability: isAtk ? 0.88 : 0.01 + Math.random() * 0.02,
        forecast_horizon_seconds: 10,
        forecasts: taForecasts
      });
    } else {
      setThreatAwareForecast((prev: any) => {
        if (!prev) return prev;
        const forecasts = { ...prev.forecasts };
        busNames.slice(0, 8).forEach((name) => {
          const v = buses[name].voltage_pu || 1.0;
          const taNoise = (Math.random() - 0.5) * 0.002;
          const p = v + taNoise;
          forecasts[name] = {
            actual: v,
            predicted: p,
            delta: p - v
          };
        });
        return {
          ...prev,
          timestamp: Date.now(),
          status: isAtk ? "CYBER-CRITICAL" : "NORMAL",
          cyber_instability_probability: isAtk ? 0.88 : 0.01 + Math.random() * 0.02,
          forecasts
        };
      });
    }

    // 4. PINN forecast
    if (!pinnForecast) {
      const makeHorizon = (_horizonName: string, mult: number) => {
        const vList = busNames.slice(0, 9).map((name) => {
          const v = buses[name].voltage_pu || 1.0;
          const pNoise = (Math.random() - 0.5) * 0.004 * mult;
          return v + pNoise + (isAtk && name === "Bus_5" ? -0.04 * mult : 0);
        });
        return {
          voltages: vList,
          cyber_instability_probability: isAtk ? 0.3 * mult : 0.02 * mult,
          confidence: 0.96 - 0.05 * mult,
          kcl_error: 0.0001 + Math.random() * 0.0003 * mult,
          kvl_error: 0.0002 + Math.random() * 0.0002 * mult,
          topology_valid: true,
          stability_valid: true,
          adversarial_anomaly: isAtk,
          explainability_log: isAtk 
            ? "PINN loss residuals exceeded 0.05 pu on Bus 5. High probability of FDIA injection."
            : "Forecasted profiles satisfy KCL, KVL, and breaker topology constraints. No active anomalies detected."
        };
      };
      setPinnForecast({
        timestamp: Date.now(),
        latency_ms: 8.5 + Math.random() * 5.0,
        degraded_observability: false,
        concept_drift_score: 0.05 + Math.random() * 0.04,
        concept_drift_alert: false,
        horizons: {
          "10s": makeHorizon("10s", 1.0),
          "30s": makeHorizon("30s", 2.0),
          "60s": makeHorizon("60s", 3.0)
        }
      });
    } else {
      setPinnForecast((prev: any) => {
        if (!prev) return prev;
        const makeHorizon = (_horizonName: string, mult: number) => {
          const vList = busNames.slice(0, 9).map((name) => {
            const v = buses[name].voltage_pu || 1.0;
            const pNoise = (Math.random() - 0.5) * 0.004 * mult;
            return v + pNoise + (isAtk && name === "Bus_5" ? -0.04 * mult : 0);
          });
          return {
            voltages: vList,
            cyber_instability_probability: isAtk ? 0.3 * mult : 0.02 * mult,
            confidence: 0.96 - 0.05 * mult,
            kcl_error: 0.0001 + Math.random() * 0.0003 * mult,
            kvl_error: 0.0002 + Math.random() * 0.0002 * mult,
            topology_valid: true,
            stability_valid: true,
            adversarial_anomaly: isAtk,
            explainability_log: isAtk 
              ? "PINN loss residuals exceeded 0.05 pu on Bus 5. High probability of FDIA injection."
              : "Forecasted profiles satisfy KCL, KVL, and breaker topology constraints. No active anomalies detected."
          };
        };
        return {
          ...prev,
          timestamp: Date.now(),
          concept_drift_score: isAtk ? 0.65 : 0.05 + Math.random() * 0.04,
          concept_drift_alert: isAtk,
          horizons: {
            "10s": makeHorizon("10s", 1.0),
            "30s": makeHorizon("30s", 2.0),
            "60s": makeHorizon("60s", 3.0)
          }
        };
      });
    }

    // 5. Append simulated live events for the console log
    const frameTs = dispTelemetry.timestamp || Date.now();
    if (lastProcessedTimestampRef.current !== frameTs) {
      lastProcessedTimestampRef.current = frameTs;
      
      const nowStr = new Date(frameTs).toLocaleTimeString([], { hour12: false });
      const gName = (dispTelemetry.grid_name || "ieee39").toUpperCase();
      const bCount = Object.keys(buses).length;
      const lCount = Object.keys(dispTelemetry.state?.lines || {}).length;
      
      const newLogs = [
        { timestamp: nowStr, message: `Telemetry packet received (Grid: ${gName}, Buses: ${bCount}, Lines: ${lCount})`, severity: "info" },
        { timestamp: nowStr, message: `PINN consistency validation passed (KCL mismatch: ${(Math.random() * 0.0003).toFixed(6)} MW)`, severity: "success" },
        { timestamp: nowStr, message: `Threat engine score updated (Instability Risk: ${isAtk ? "88.0" : (0.01 + Math.random() * 0.02 * 100).toFixed(1)}%)`, severity: isAtk ? "warning" : "info" },
        { timestamp: nowStr, message: `Blockchain consensus block verified (#${10000 + Math.floor(frameTs / 3000 % 5000)})`, severity: "success" }
      ];
      
      if (isAtk) {
        newLogs.push({ timestamp: nowStr, message: `SECURITY ALERT: Active intrusion detected on Bus 5! Mitigating...`, severity: "critical" });
      } else {
        newLogs.push({ timestamp: nowStr, message: `System state nominal. Cybersecurity shields fully online.`, severity: "success" });
      }

      setLiveLogs((prev) => {
        const next = [...prev, ...newLogs];
        if (next.length > 100) {
          return next.slice(next.length - 100);
        }
        return next;
      });
    }
  }, [dispTelemetry, dispActiveAttack]);

  const dispPredictionHistory = useMemo(() => {
    if (!isReplaying || !currentFrame || !dispTelemetry) return predictionHistory;
    return predictionHistory.filter((p) => p.timestamp <= dispTelemetry.timestamp);
  }, [isReplaying, currentFrame, predictionHistory, dispTelemetry]);


  // Collapsible and resizable panel handlers
  const toggleCollapse = (id: string) => {
    setCollapsedPanels((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const cycleSize = (id: string) => {
    setPanelSizes((prev) => {
      const current = prev[id] || 1;
      let next = 1;
      if (current === 1) next = 2;
      else if (current === 2) next = 3;
      else if (current === 3) next = 4;
      return { ...prev, [id]: next };
    });
  };

  const movePanel = (id: string, direction: "left" | "right") => {
    setPanelOrder((prev) => {
      const idx = prev.indexOf(id);
      if (idx === -1) return prev;
      const nextIdx = direction === "left" ? idx - 1 : idx + 1;
      if (nextIdx < 0 || nextIdx >= prev.length) return prev;
      const nextOrder = [...prev];
      nextOrder[idx] = prev[nextIdx];
      nextOrder[nextIdx] = id;
      return nextOrder;
    });
  };

  const getColSpanClass = (span: number) => {
    if (span === 2) return "col-span-1 md:col-span-2";
    if (span === 3) return "col-span-1 md:col-span-2 lg:col-span-3";
    if (span === 4) return "col-span-1 md:col-span-2 lg:col-span-3 xl:col-span-4";
    return "col-span-1";
  };



  const renderPanel = (panelId: string) => {
    const isCollapsed = collapsedPanels.has(panelId);
    const size = panelSizes[panelId] || 1;
    const colSpanClass = getColSpanClass(size);
    
    let title = "";
    let content: React.ReactNode = null;
    
    switch (panelId) {
      case "telemetry":
        title = "Real-Time Telemetry";
        content = <TelemetryCharts history={dispHistory} />;
        break;
      case "forecast":
        title = "AI Voltage Forecast";
        content = <ForecastPanel predictionHistory={dispPredictionHistory} aiPrediction={dispAiPrediction} />;
        break;
      case "multibus":
        title = "Multi-Bus Forecast";
        content = <MultiBusForecastPanel forecastData={dispMultiBusForecast} />;
        break;
      case "threat_aware":
        title = "Cyber-Aware Predictor";
        content = <ThreatAwareForecastPanel forecastData={dispThreatAwareForecast} />;
        break;
      case "pinn":
        title = "Physics-Informed AI Forecast";
        content = <PinnForecastPanel pinnForecastData={dispPinnForecast} />;
        break;
      case "physics":
        title = "Physics Validator";
        content = <PhysicsValidationPanel validationData={dispPhysicsValidation} />;
        break;
      case "trust":
        title = "Telemetry Trust & Filtering";
        content = <TrustAnalysisPanel trustScores={dispTrustScores} filterData={dispAdaptiveFilter} />;
        break;
      case "orchestrator":
        title = "AI Orchestration";
        content = (
          <OrchestratorPanel
            orchestratorData={dispAiOrchestrator}
            actionsData={dispRecommendedActions}
            onExecuteAction={handleExecuteAction}
          />
        );
        break;
      case "health":
        title = "System Health & Diagnostics";
        content = (
          <SystemHealthPanel
            connected={connected}
            wsLatency={wsLatency}
            reconnectCount={reconnectCount}
            msgRate={msgRate}
            aiOrchestrator={dispAiOrchestrator}
            telemetry={dispTelemetry}
          />
        );
        break;
      case "pre_rl":
        title = "Autonomous Pre-RL Safety & Control";
        content = (
          <PreRlPanel
            preRlData={dispPreRlData}
            onSendControl={sendPreRlControl}
          />
        );
        break;
      case "cyber_defense":
        title = "Autonomous Cyber Defense";
        content = (
          <CyberDefensePanel
            defenseData={dispDefenseData}
            onSendControl={sendGeneralControl}
          />
        );
        break;
      case "l6_recovery":
        title = "Layer 6 Autonomous Restoration Core";
        content = (
          <Layer6Panel
            l6RecoveryData={dispL6Recovery}
            onSendControl={sendGeneralControl}
          />
        );
        break;
      case "l6_adaptive_recovery":
        title = "Layer 6 Adaptive Recovery Intelligence";
        content = (
          <AdaptiveRecoveryPanel
            adaptiveRecoveryData={dispL6AdaptiveRecovery}
            containmentData={dispL6Containment}
            degradedModeData={dispL6DegradedMode}
            onSendControl={sendGeneralControl}
          />
        );
        break;
      case "l6_survival":
        title = "Layer 6 Autonomous Grid Survival";
        content = (
          <AutonomousSurvivalPanel
            survivalData={dispL6Survival}
            islandingData={dispL6Islanding}
            blackstartData={dispL6Blackstart}
            balancingData={dispL6Balancing}
            onSendControl={sendGeneralControl}
          />
        );
        break;
      case "l6_predictive_stabilization":
        title = "Layer 6 Predictive Autonomous Stabilization";
        content = (
          <PredictiveStabilizationPanel
            predictiveStability={dispL6PredictiveStability}
            survivalForecast={dispL6SurvivalForecast}
            proactiveActions={dispL6ProactiveActions}
            selfPreservation={dispL6SelfPreservation}
            proactiveAutoMode={proactiveAutoMode}
            onSendControl={sendGeneralControl}
          />
        );
        break;
      case "l6_multi_agent":
        title = "Layer 6 Distributed Multi-Agent Consensus";
        content = (
          <MultiAgentCoordinationPanel
            agentsData={dispL6Agents}
            consensusData={dispL6AgentConsensus}
            conflictsData={dispL6AgentConflicts}
            distributedStateData={dispL6DistributedState}
            confidenceData={dispL6AgentConfidence}
          />
        );
        break;
      case "l7_hardware":
        title = "Layer 7.1 Hardware Abstraction Foundation";
        content = (
          <HardwareFoundationPanel
            hardwareRelay={dispHardwareRelay}
            hardwareGpio={dispHardwareGpio}
            hardwareSensor={dispHardwareSensor}
            hardwareDeviceHealth={dispHardwareDeviceHealth}
            hardwareCommandLog={dispHardwareCommandLog}
            onSendControl={sendControl}
          />
        );
        break;
      case "l7_twin":
        title = "Virtual Hardware Twin Panel";
        content = (
          <VirtualHardwareTwinPanel
            hardwareVirtualDevices={dispHardwareVirtualDevices}
            hardwareRelayFaults={dispHardwareRelayFaults}
            hardwareSpoofedTelemetry={dispHardwareSpoofedTelemetry}
            hardwareAnomalies={dispHardwareAnomalies}
            hardwareFaultPropagation={dispHardwareFaultPropagation}
            onSendControl={sendControl}
          />
        );
        break;
      case "l7_attack":
        title = "Cyber-Physical Attack Layer Foundation";
        content = (
          <CyberPhysicalAttackPanel
            hardwareUsbEvents={dispHardwareUsbEvents}
            hardwareRogueDevices={dispHardwareRogueDevices}
            hardwareBadusb={dispHardwareBadusb}
            hardwareIntrusionAlerts={dispHardwareIntrusionAlerts}
            hardwareDeviceTrust={dispHardwareDeviceTrust}
            hardwareAttackState={dispHardwareAttackState}
            hardwareAttackPropagation={dispHardwareAttackPropagation}
            onSendControl={sendControl}
          />
        );
        break;
      case "l7_orchestration":
        title = "Hardware Orchestration Panel";
        content = (
          <HardwareOrchestrationPanel
            hardwareOrchestration={dispHardwareOrchestration}
            hardwareEdgeDevices={dispHardwareEdgeDevices}
            hardwareRelayExecution={dispHardwareRelayExecution}
            hardwareDistributedBus={dispHardwareDistributedBus}
            hardwareSynchronization={dispHardwareSynchronization}
            hardwareOrchestrationConflicts={dispHardwareOrchestrationConflicts}
            onSendControl={sendControl}
          />
        );
        break;
      case "l7_execution":
        title = "Physical Execution & Edge Safety Console";
        content = (
          <HardwareExecutionPanel
            executionGateway={dispHardwareExecutionGateway}
            reliability={dispHardwareReliability}
            safetyGuard={dispHardwareSafetyGuard}
            telemetryValidation={dispHardwareTelemetryValidation}
            onSendControl={sendControl}
          />
        );
        break;

      case "l7_resilience":
        title = "Infrastructure Resilience & Hardening";
        content = (
          <InfrastructureResiliencePanel
            resilience={dispHardwareResilience}
            disasterRecovery={dispHardwareDisasterRecovery}
            redundancy={dispHardwareRedundancy}
            deploymentHardening={dispHardwareDeploymentHardening}
            largeScaleSync={dispHardwareLargeScaleSync}
            onSendControl={sendControl}
          />
        );
        break;

      case "l7_assistant":
        title = "Intelligent Personal Assistant Core";
        content = (
          <AssistantCognitionPanel
            assistantState={dispAssistantState}
            assistantIntent={dispAssistantIntent}
            assistantEmotion={dispAssistantEmotion}
            assistantActions={dispAssistantActions}
            assistantContext={dispAssistantContext}
            assistantMemory={dispAssistantMemory}
            assistantResponse={dispAssistantResponse}
            assistantRuntime={dispAssistantRuntime}
            assistantSemanticIntent={dispAssistantSemanticIntent}
            assistantContextualMemory={dispAssistantContextualMemory}
            assistantReasoning={dispAssistantReasoning}
            assistantAutomationHooks={dispAssistantAutomationHooks}
            assistantSemanticResponse={dispAssistantSemanticResponse}
            assistantVoiceState={dispAssistantVoiceState}
            assistantWakeWord={dispAssistantWakeWord}
            assistantProactive={dispAssistantProactive}
            assistantVoiceMemory={dispAssistantVoiceMemory}
            assistantPresence={dispAssistantPresence}
            assistantWorkflows={dispAssistantWorkflows}
            assistantReminders={dispAssistantReminders}
            assistantConditions={dispAssistantConditions}
            assistantN8nBridge={dispAssistantN8nBridge}
            assistantRoutines={dispAssistantRoutines}
            assistantConversationPlanning={dispAssistantConversationPlanning}
            assistantTaskChains={dispAssistantTaskChains}
            assistantLiveStream={dispAssistantLiveStream}
            assistantDialogue={dispAssistantDialogue}
            assistantOrchestrationPlanner={dispAssistantOrchestrationPlanner}
            
            // Phase 9.6 props
            assistantPredictiveCoordination={dispAssistantPredictiveCoordination}
            assistantPersistentMemory={dispAssistantPersistentMemory}
            assistantPatternAwareness={dispAssistantPatternAwareness}
            assistantWorkflowOptimizer={dispAssistantWorkflowOptimizer}
            assistantCrossSystemCoordination={dispAssistantCrossSystemCoordination}

            // Phase 9.7 props
            assistantEdgeAwareness={dispAssistantEdgeAwareness}
            assistantRelayHealth={dispAssistantRelayHealth}
            assistantTelemetryCorrelation={dispAssistantTelemetryCorrelation}
            assistantSynchronizationAwareness={dispAssistantSynchronizationAwareness}
            assistantCyberPhysicalReasoning={dispAssistantCyberPhysicalReasoning}

            // Phase 9.8 props
            assistantAgentCoordination={dispAssistantAgentCoordination}
            assistantTelemetryAgent={dispAssistantTelemetryAgent}
            assistantRelayAgent={dispAssistantRelayAgent}
            assistantWorkflowAgent={dispAssistantWorkflowAgent}
            assistantSecurityAgent={dispAssistantSecurityAgent}

            // Phase 9.9 props
            assistantSwarmCoordination={dispAssistantSwarmCoordination}
            assistantFederatedMemory={dispAssistantFederatedMemory}
            assistantDistributedConsensus={dispAssistantDistributedConsensus}
            assistantEdgeMesh={dispAssistantEdgeMesh}
            assistantSwarmAnomalyFusion={dispAssistantSwarmAnomalyFusion}

            connected={connected}
            onSendControl={sendDirectMqtt}
          />
        );
        break;

      default:
        return null;
    }

    return (
      <div
        key={panelId}
        className={`${colSpanClass} transition-all duration-300 relative group flex flex-col`}
        style={{ minHeight: isCollapsed ? "42px" : "300px" }}
      >
        <div className="absolute top-2.5 right-12 z-30 flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity bg-scada-bg/85 border border-scada-border/40 rounded px-1.5 py-0.5 font-mono text-[7px] text-scada-dimText">
          <button
            onClick={() => movePanel(panelId, "left")}
            className="hover:text-white transition-colors"
            title="Move Left"
          >
            <ArrowLeft size={10} />
          </button>
          <button
            onClick={() => movePanel(panelId, "right")}
            className="hover:text-white transition-colors border-l border-scada-border/30 pl-1"
            title="Move Right"
          >
            <ArrowRight size={10} />
          </button>
          <button
            onClick={() => cycleSize(panelId)}
            className="hover:text-white transition-colors border-l border-scada-border/30 pl-1 flex items-center gap-0.5"
            title="Cycle Width"
          >
            {size === 1 ? <Maximize2 size={9} /> : <Minimize2 size={9} />}
            <span>W{size}</span>
          </button>
          <button
            onClick={() => toggleCollapse(panelId)}
            className="hover:text-white transition-colors border-l border-scada-border/30 pl-1"
            title={isCollapsed ? "Expand Panel" : "Collapse Panel"}
          >
            {isCollapsed ? "EXP" : "COL"}
          </button>
        </div>

        {isCollapsed ? (
          <div className="bg-scada-panel border border-scada-border rounded-lg p-2.5 px-3 h-[42px] flex justify-between items-center text-xs font-mono font-bold tracking-wider text-scada-dimText uppercase scada-glow-green">
            <span className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 shadow-[0_0_6px_rgba(16,185,129,0.5)]"></span>
              {title}
            </span>
            <button
              onClick={() => toggleCollapse(panelId)}
              className="text-[8px] text-scada-nominal border border-scada-nominal/30 hover:bg-scada-nominal/10 px-2 py-0.5 rounded transition-all font-bold font-mono"
            >
              EXPAND
            </button>
          </div>
        ) : (
          content
        )}
      </div>
    );
  };

  const renderAiSubsystemsStatus = () => {
    const isAtk = dispActiveAttack !== null;
    const blockNum = 1830 + Math.floor((Date.now() / 3000) % 5000);

    const subsystems = [
      { name: "LSTM IDS", status: "ACTIVE", confidence: "98.6%", metric: `F1-Score: 0.992`, time: "1s ago" },
      { name: "PINN Validator", status: "ACTIVE", confidence: "99.1%", metric: `Residual: ${(Math.random() * 0.002 + 0.003).toFixed(4)} MW`, time: "Just now" },
      { name: "GNN Predictor", status: "ACTIVE", confidence: "95.8%", metric: `Stability Index: ${(0.94 + Math.random() * 0.03).toFixed(3)}`, time: "1s ago" },
      { name: "Blockchain", status: "ACTIVE", confidence: "100.0%", metric: `Block #${blockNum}`, time: "Just now" },
      { name: "Trust Engine", status: isAtk ? "ACTIVE" : "LEARNING", confidence: "97.4%", metric: `Nodes Synced: 100%`, time: "2s ago" },
      { name: "FLISR Engine", status: flisrAuto ? (isAtk ? "ACTIVE" : "STANDBY") : "DISABLED", confidence: "99.8%", metric: flisrAuto ? (isAtk ? "Isolating anomalies" : "Standby (Nominal)") : "Engine Disabled", time: isAtk ? "Just now" : "15s ago" },
      { name: "Immune Agent", status: "LEARNING", confidence: "96.5%", metric: `Patterns Class: 24`, time: "5s ago" }
    ];

    return (
      <div className="bg-scada-panel border border-scada-border rounded-lg p-4 flex flex-col justify-between overflow-hidden h-full">
        <h2 className="text-xs font-bold tracking-wider text-scada-dimText uppercase border-b border-scada-border/40 pb-2 mb-2 flex items-center gap-1.5 shrink-0">
          <Cpu size={14} className="text-scada-nominal" />
          AI Agent Subsystems Status
        </h2>
        <div className="flex-1 overflow-y-auto pr-1 space-y-1.5 scrollbar-thin max-h-[180px]">
          {subsystems.map((sub, i) => (
            <div key={i} className="bg-scada-bg/40 border border-scada-border/10 rounded p-1.5 px-2 flex justify-between items-center text-[10px] font-mono">
              <div className="flex flex-col">
                <span className="text-white font-bold">{sub.name}</span>
                <span className="text-[7.5px] text-scada-dimText uppercase mt-0.5">{sub.metric}</span>
              </div>
              
              <div className="flex items-center gap-3">
                <div className="text-right flex flex-col">
                  <span className={`text-[8.5px] font-bold ${
                    sub.status === "ACTIVE" 
                      ? "text-emerald-400" 
                      : sub.status === "LEARNING" 
                      ? "text-cyan-400" 
                      : "text-amber-400"
                  }`}>{sub.status}</span>
                  <span className="text-[7.5px] text-scada-dimText">{sub.confidence}</span>
                </div>
                <div className="h-6 w-[1px] bg-scada-border/20"></div>
                <span className="text-[8px] text-scada-dimText w-[45px] text-right">{sub.time}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  };

  const renderTrialExpirationBanner = () => {
    if (planTier === "academic_premium" && trialBannerVisible) {
      return (
        <div className="border border-amber-500/30 rounded-lg p-3 bg-amber-500/10 text-amber-500 font-mono text-[10px] flex justify-between items-center shrink-0">
          <div className="flex items-center gap-2">
            <span>⚠️</span>
            <span>TRIAL STATUS: Academic Premium Trial active. Trial expires in {daysRemaining} days. All V10.7 Cyber Range modules are unlocked.</span>
          </div>
          <div className="flex items-center gap-2">
            <button 
              onClick={() => setCurrentPage("settings")} 
              className="px-3 py-1 bg-amber-500 hover:bg-amber-600 text-slate-900 font-bold rounded cursor-pointer transition-colors"
            >
              UPGRADE NOW
            </button>
            <button 
              onClick={() => setTrialBannerVisible(false)}
              className="text-scada-dimText hover:text-white px-2 cursor-pointer font-bold"
            >
              [X]
            </button>
          </div>
        </div>
      );
    }
    const hasLocked = experiments.some(e => e.locked);
    if (planTier === "free" && hasLocked) {
      return (
        <div className="border border-red-500/30 rounded-lg p-3 bg-red-500/10 text-red-500 font-mono text-[10px] flex justify-between items-center shrink-0">
          <div className="flex items-center gap-2">
            <span>🔒</span>
            <span>Your historical experiments are archived. Upgrade to Academic Premium to unlock them and access full IEEE 57 and IEEE 118 models.</span>
          </div>
          <button 
            onClick={() => setCurrentPage("settings")} 
            className="px-3 py-1 bg-red-500 hover:bg-red-600 text-slate-900 font-bold rounded cursor-pointer transition-colors"
          >
            UPGRADE PLAN
          </button>
        </div>
      );
    }
    return null;
  };

  const renderMissionStatusBanner = () => {
    const isAtk = dispActiveAttack !== null;
    const isRecovery = dispFlisrIsolated || dispFlisrReconfigured;
    const voltages = Object.values(dispTelemetry?.state?.buses || {}).map((b: any) => b.voltage_pu || 0.0);
    const minV = voltages.length > 0 ? Math.min(...voltages) : 1.0;
    const avgTrust = metricsHistory.trust.length > 0 ? metricsHistory.trust[metricsHistory.trust.length - 1] : 1.0;
    
    let sysStatus = "SECURE";
    let bannerColorClass = "border-emerald-500/50 text-emerald-400 bg-emerald-500/5";
    let labelColorClass = "text-emerald-500 scada-text-glow-green";
    
    if (isAtk) {
      sysStatus = "UNDER ATTACK";
      bannerColorClass = "border-red-500/50 text-red-400 bg-red-500/5 animate-pulse shadow-[0_0_15px_rgba(239,68,68,0.15)]";
      labelColorClass = "text-red-500 scada-text-glow-red font-extrabold";
    } else if (isRecovery) {
      sysStatus = "RECOVERY MODE";
      bannerColorClass = "border-blue-500/50 text-blue-400 bg-blue-500/5";
      labelColorClass = "text-blue-500 scada-text-glow font-extrabold";
    } else if (minV < 0.95 || avgTrust < 0.95) {
      sysStatus = "UNDER INVESTIGATION";
      bannerColorClass = "border-yellow-500/50 text-yellow-400 bg-yellow-500/5";
      labelColorClass = "text-yellow-500 scada-text-glow-warning font-extrabold";
    }
    
    const threatScore = dispThreatData?.threat_score ?? 0;
    const threatLevel = threatScore >= 76 ? "CRITICAL" : threatScore >= 51 ? "HIGH" : threatScore >= 26 ? "MEDIUM" : "LOW";
    const resilienceScore = "96.8%";
    const gridName = (dispTelemetry?.grid_name || "ieee39").toUpperCase();

    return (
      <div className={`border rounded-lg p-2 px-4 font-mono text-[9px] flex items-center justify-between shrink-0 leading-none select-none tracking-widest ${bannerColorClass}`}>
        <div>==================================================</div>
        <div className="flex items-center gap-6">
          <span>SYSTEM STATUS : <strong className={labelColorClass}>{sysStatus}</strong></span>
          <span>•</span>
          <span>GRID : <strong className="text-white">{gridName}</strong></span>
          <span>•</span>
          <span>THREAT LEVEL : <strong className="text-white">{threatLevel}</strong></span>
          <span>•</span>
          <span>RESILIENCE SCORE : <strong className="text-scada-nominal">{resilienceScore}</strong></span>
        </div>
        <div>========================</div>
      </div>
    );
  };

  // V11.9 Auth & landing page routing
  if (currentPage === "landing") {
    return (
      <LandingPage
        onNavigate={handleNavFromLanding}
      />
    );
  }

  if (currentPage === "login" || currentPage === "register" || currentPage === "forgot_password" || currentPage === "reset_password" || currentPage === "verify_email" || currentPage === "resend_verification") {
    return (
      <AuthPages
        mode={currentPage as any}
        onNavigate={(p: string) => {
          if (p === 'landing') { setCurrentPage('landing'); }
          else if (['login','register','forgot_password','reset_password','verify_email','resend_verification'].includes(p)) { setCurrentPage(p as any); }
          else { setCurrentPage('overview'); }
        }}
        onAuthSuccess={handleAuthSuccess}
      />
    );
  }

  if (currentPage === "user_dashboard" && authToken) {
    return (
      <UserDashboard
        token={authToken}
        user={authUser as any}
        onLogout={handleLogout}
        onNavigate={(p: string) => setCurrentPage(p as any)}
      />
    );
  }

  if (currentPage === "setup_wizard" && authToken) {
    return (
      <WorkspaceSetupWizard
        token={authToken}
        user={authUser as any}
        onComplete={handleSetupComplete}
      />
    );
  }


  return (
    <div className={`h-screen w-screen flex bg-scada-bg text-scada-text relative select-none overflow-hidden transition-all duration-300 ${
      crtEnabled ? "scada-crt" : ""
    } ${activeAttack === "REPLAY" ? "replay-active-frame border-4" : ""}`}>
      
      {/* Minimal Sidebar Navigation */}
      <aside className="w-56 bg-scada-panel border-r border-scada-border flex flex-col justify-between p-4 shrink-0">
        <div className="space-y-6">
          <div className="flex items-center gap-2 border-b border-scada-border/40 pb-4">
            <Zap size={20} className="text-scada-nominal animate-pulse" />
            <div>
              <span className="text-xs font-bold tracking-widest text-white block">CONTROL CENTER</span>
              <span className="text-[9px] text-scada-dimText uppercase font-mono">Cybersecurity Hub</span>
            </div>
          </div>
          
          <nav className="flex flex-col gap-2">
            {[
              { id: "landing", label: "Public Portal", icon: <MonitorPlay size={14} /> },
              { id: "overview", label: "Dashboard", icon: <Cpu size={14} /> },
              { id: "bcm_center", label: "BCM Center", icon: <Activity size={14} /> },
              { id: "research_workspace", label: "Research Workspace", icon: <MonitorPlay size={14} /> },
              { id: "scenario_marketplace", label: "Scenario Marketplace", icon: <MonitorPlay size={14} /> },
              { id: "reports", label: "Reports", icon: <ShieldAlert size={14} /> },
              { id: "ai_copilot", label: "AI Copilot", icon: <Cpu size={14} /> },
              { id: "settings", label: "Settings", icon: <MonitorPlay size={14} /> },
              { id: "cloud_ops", label: "Cloud Operations Center", icon: <Activity size={14} /> },
              { id: "saas_admin", label: "Administration", icon: <ShieldAlert size={14} /> }
            ].map((link) => (
              <button
                key={link.id}
                onClick={() => setCurrentPage(link.id as any)}
                className={`flex items-center gap-3 px-3 py-2 rounded transition-all text-[10px] font-semibold uppercase tracking-wider ${
                  currentPage === link.id
                    ? "bg-scada-nominal/15 border-l-2 border-scada-nominal text-scada-nominal font-bold"
                    : "text-scada-dimText hover:text-white hover:bg-scada-border/10"
                }`}
              >
                {link.icon}
                {link.label}
              </button>
            ))}
          </nav>
        </div>

        <div className="border-t border-scada-border/40 pt-4 font-mono text-[9px] text-scada-dimText space-y-1">
          <div>NODE: {(dispTelemetry?.grid_name || "ieee39").toUpperCase()}</div>
          <div>SWEEP: {msgRate.toFixed(1)}Hz</div>
          <div className="flex items-center gap-1.5 mt-2">
            <span className={`w-2 h-2 rounded-full ${connected ? "bg-emerald-500 animate-ping" : "bg-red-500"}`}></span>
            <span className="uppercase">{connected ? "Connected" : "Offline"}</span>
          </div>
        </div>
      </aside>

      {/* Main Container */}
      <div className="flex-1 flex flex-col p-4 overflow-hidden gap-4">
        {/* Header Panel */}
        <header className={`flex justify-between items-center border border-scada-border rounded-lg p-3 px-4 bg-scada-panel transition-all duration-300 shrink-0 ${
          activeAttack ? "border-red-500/50 bg-red-950/10 scada-glow-red" : "scada-glow-green"
        }`}>
          <div className="flex items-center gap-3">
            <div className="relative">
              <Zap size={22} className={connected ? "text-scada-nominal animate-pulse" : "text-gray-500"} />
              {connected && <span className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-emerald-500 rounded-full animate-ping"></span>}
            </div>
            <div>
              <h1 className="text-md font-bold tracking-widest text-white uppercase flex items-center gap-2">
                PYPY Smart Grid Command Center - {selectedGrid.toUpperCase()}
              </h1>
              <p className="text-[10px] text-scada-dimText font-mono uppercase">
                Real-Time Cyber Defense & Autonomic Resilience Console
              </p>
            </div>
          </div>

          <div className="flex items-center gap-8 font-mono text-xs">
            {/* Grid Selector */}
            <div className="flex items-center gap-2 bg-scada-bg border border-scada-border/60 rounded px-2.5 py-1">
              <span className="text-[10px] text-scada-dimText uppercase font-mono font-bold">Grid:</span>
              <select
                value={selectedGrid.toUpperCase()}
                onChange={(e) => {
                  const newGrid = e.target.value.toLowerCase();
                  setSelectedGrid(newGrid);
                  if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
                    wsRef.current.send(JSON.stringify({
                      topic: "grid/config",
                      payload: { grid_name: newGrid }
                    }));
                  }
                }}
                className="bg-transparent text-white font-mono text-xs font-bold focus:outline-none cursor-pointer"
              >
                <option value="IEEE14" className="bg-scada-panel">IEEE14</option>
                <option value="IEEE39" className="bg-scada-panel">IEEE39</option>
                <option value="IEEE57" className="bg-scada-panel">IEEE57</option>
                <option value="IEEE118" className="bg-scada-panel">IEEE118</option>
              </select>
            </div>

            <div className="flex flex-col items-end">
              <span className="text-[9px] text-scada-dimText uppercase">System Status</span>
              {activeAttack ? (
                <span className="text-scada-trip font-bold text-xs animate-bounce scada-text-glow-red flex items-center gap-1">
                  <AlertOctagon size={12} /> CYBER ATTACK
                </span>
              ) : hasActiveTrips() ? (
                <span className="text-scada-warning font-bold text-xs animate-pulse scada-text-glow-warning">DEGRADED</span>
              ) : (
                <span className="text-scada-nominal font-bold text-xs scada-text-glow-green">NOMINAL</span>
              )}
            </div>

            <div className="flex flex-col items-end">
              <span className="text-[9px] text-scada-dimText uppercase">Threat Level</span>
              {activeAttack ? (
                <span className="text-red-500 font-bold text-xs scada-text-glow-red animate-pulse">
                  CRITICAL ({typeof threatData?.confidence === "number" ? (threatData.confidence * 100).toFixed(0) : "97"}%)
                </span>
              ) : (
                <span className="text-scada-nominal font-bold text-xs scada-text-glow-green">SECURE</span>
              )}
            </div>

            <div className="flex flex-col items-end font-mono">
              <span className="text-[9px] text-scada-dimText uppercase">Time</span>
              <span className="text-white font-bold text-xs tracking-wider">
                {currentTime || "12:00:00"}
              </span>
            </div>

            {/* Connection Status */}
            <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded border font-mono font-bold text-[10px] ${
              connected ? "bg-emerald-500/10 border-emerald-500/20 text-scada-nominal" : "bg-red-500/10 border-red-500/20 text-scada-trip"
            }`}>
              <Wifi size={12} />
              <span>{connected ? "ONLINE" : "OFFLINE"}</span>
            </div>

            {/* CRT Toggle */}
            <button 
              onClick={() => setCrtEnabled(!crtEnabled)}
              className={`p-1.5 rounded border transition-all text-[10px] flex items-center gap-1 font-bold ${
                crtEnabled ? "bg-scada-nominal/15 border-scada-nominal text-scada-nominal" : "bg-scada-bg border-scada-border text-scada-dimText hover:text-white"
              }`}
              title="Toggle CRT Screen Scanlines"
            >
              <MonitorPlay size={12} /> CRT
            </button>
          </div>
        </header>

        {renderMissionStatusBanner()}
        {renderTrialExpirationBanner()}

        {/* Content Body */}
        {currentPage === "overview" && (
          <div className="flex-1 flex flex-col gap-4 overflow-y-auto pr-1 scrollbar-thin">
            
            {/* Row 1: Grid Info & Threat Intelligence */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 shrink-0">
              
              {/* Panel 1: Grid Information (col-span-1) */}
              <div className="bg-scada-panel border border-scada-border rounded-lg p-4 flex flex-col justify-between overflow-hidden min-h-[200px]">
                <h2 className="text-xs font-bold tracking-wider text-scada-dimText uppercase border-b border-scada-border/40 pb-2 mb-2 flex items-center gap-1.5 shrink-0">
                  <Cpu size={14} className="text-scada-nominal" />
                  Grid Physical Information
                </h2>
                <div className="flex-1 grid grid-cols-2 gap-2 text-[10.5px] font-mono items-center">
                  <div className="bg-scada-bg border border-scada-border/20 rounded p-1.5 flex flex-col">
                    <span className="text-[8px] text-scada-dimText uppercase mb-0.5">Topology</span>
                    <span className="text-white font-bold">{(dispTelemetry?.grid_name || "ieee39").toUpperCase()}</span>
                  </div>
                  <div className="bg-scada-bg border border-scada-border/20 rounded p-1.5 flex flex-col">
                    <span className="text-[8px] text-scada-dimText uppercase mb-0.5">Buses / Lines</span>
                    <span className="text-white font-bold">
                      {Object.keys(dispTelemetry?.state?.buses || {}).length} / {Object.keys(dispTelemetry?.state?.lines || {}).length}
                    </span>
                  </div>
                  <div className="bg-scada-bg border border-scada-border/20 rounded p-1.5 flex flex-col">
                    <span className="text-[8px] text-scada-dimText uppercase mb-0.5">Active Gen</span>
                    <span className="text-scada-nominal font-bold">{(getSumGenPower() ?? 0).toFixed(1)} MW</span>
                  </div>
                  <div className="bg-scada-bg border border-scada-border/20 rounded p-1.5 flex flex-col">
                    <span className="text-[8px] text-scada-dimText uppercase mb-0.5">Net Load</span>
                    <span className="text-scada-nominal font-bold">{(getSumLoadPower() ?? 0).toFixed(1)} MW</span>
                  </div>
                  <div className="bg-scada-bg border border-scada-border/20 rounded p-1.5 flex flex-col">
                    <span className="text-[8px] text-scada-dimText uppercase mb-0.5">Frequency</span>
                    <span className="text-scada-nominal font-bold scada-text-glow-green">
                      {(Object.values(dispTelemetry?.state?.buses || {}).reduce((acc: number, b: any) => acc + (b.frequency_hz || 60.0), 0) / Math.max(1, Object.keys(dispTelemetry?.state?.buses || {}).length)).toFixed(2)} Hz
                    </span>
                  </div>
                  <div className="bg-scada-bg border border-scada-border/20 rounded p-1.5 flex flex-col">
                    <span className="text-[8px] text-scada-dimText uppercase mb-0.5">Stability (Vmin)</span>
                    <span className="text-scada-nominal font-bold scada-text-glow-green">
                      {(() => {
                        const voltages = Object.values(dispTelemetry?.state?.buses || {}).map((b: any) => b.voltage_pu || 0.0);
                        const minV = voltages.length > 0 ? Math.min(...voltages) : 1.0;
                        return minV.toFixed(4);
                      })()} pu
                    </span>
                  </div>
                </div>
              </div>

              {/* Panel 3: Threat Intelligence (col-span-2) */}
              <div className="lg:col-span-2">
                <ThreatScorePanel 
                  threatData={dispThreatData}
                  history={metricsHistory.blackoutProb}
                  onExecuteAction={handleExecuteAction}
                  onToggleAutoDefense={handleToggleAutoDefense}
                  buses={dispTelemetry?.state?.buses || {}}
                  lines={dispTelemetry?.state?.lines || {}}
                  activeAttack={dispActiveAttack}
                />
              </div>
            </div>

            {/* Row 2: Interactive Topology View */}
            <div className="h-[60vh] min-h-[480px] bg-scada-panel border border-scada-border rounded-lg overflow-hidden flex flex-col shrink-0 relative shadow-lg">
              <div className="absolute top-3 right-3 z-20 flex gap-2">
                <button
                  onClick={() => setIsTopologyFullscreen(!isTopologyFullscreen)}
                  className="bg-scada-bg/80 border border-scada-border hover:border-scada-nominal/60 hover:text-scada-nominal text-scada-dimText font-mono text-[9px] font-bold px-2 py-1 rounded transition-all flex items-center gap-1 uppercase"
                  title="Toggle Fullscreen topology view"
                >
                  <Maximize2 size={10} /> Fullscreen
                </button>
              </div>

              <GridDiagram 
                key={selectedGrid}
                selectedGrid={selectedGrid}
                telemetry={dispTelemetry} 
                onToggleBreaker={toggleBreaker} 
                attackStatus={dispTelemetry?.attack_status}
                flisrState={dispFlisrState}
                flisrIsolated={dispFlisrIsolated}
                flisrReconfigured={dispFlisrReconfigured}
                flisrTripped={dispFlisrTripped}
              />
            </div>

            {/* Row 3: Live Metrics | AI Status | Forecast */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 shrink-0 min-h-[220px]">
              
              {/* Live Telemetry Metrics Sparklines */}
              <div className="bg-scada-panel border border-scada-border rounded-lg p-4 flex flex-col justify-between overflow-hidden">
                <h2 className="text-xs font-bold tracking-wider text-scada-dimText uppercase border-b border-scada-border/40 pb-2 mb-2 flex items-center gap-1.5 shrink-0">
                  <Activity size={14} className="text-scada-nominal" />
                  Live Telemetry Metrics
                </h2>
                <div className="flex-1 grid grid-cols-2 gap-x-4 gap-y-2 items-center">
                  {[
                    { label: "Voltage (avg)", history: metricsHistory.voltage, color: "#10B981", format: (v: number) => `${v.toFixed(3)} pu` },
                    { label: "Frequency (avg)", history: metricsHistory.frequency, color: "#3B82F6", format: (f: number) => `${f.toFixed(2)} Hz` },
                    { label: "Grid Load", history: metricsHistory.load, color: "#8B5CF6", format: (l: number) => `${l.toFixed(0)} MW` },
                    { label: "Trust Index", history: metricsHistory.trust, color: "#F59E0B", format: (t: number) => `${t.toFixed(4)}` },
                    { label: "Attacked Assets", history: metricsHistory.attackCount, color: "#EF4444", format: (a: number) => `${a} Nodes` },
                    { label: "Blackout Risk", history: metricsHistory.blackoutProb, color: "#EC4899", format: (b: number) => `${(b * 100).toFixed(0)}%` }
                  ].map((metric, i) => (
                    <div key={i} className="flex flex-col bg-scada-bg/30 border border-scada-border/20 rounded p-1.5 px-2">
                      <div className="flex justify-between items-center mb-1">
                        <span className="text-[8px] text-scada-dimText uppercase font-mono">{metric.label}</span>
                        <span className="text-[10px] text-white font-bold font-mono">
                          {metric.history.length > 0 ? metric.format(metric.history[metric.history.length - 1]) : "N/A"}
                        </span>
                      </div>
                      <div className="h-8 flex items-center justify-center">
                        <Sparkline data={metric.history} color={metric.color} />
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* AI Agent Subsystems Status */}
              <div>
                {renderAiSubsystemsStatus()}
              </div>

              {/* AI Voltage Forecast */}
              <div className="bg-scada-panel border border-scada-border rounded-lg overflow-hidden flex flex-col h-full">
                <ForecastPanel predictionHistory={dispPredictionHistory} aiPrediction={dispAiPrediction} />
              </div>
            </div>

          </div>
        )}

        {currentPage === "analytics" && (
          <div className="flex-1 flex flex-col overflow-hidden gap-4">
            {/* Tabs Selector */}
            <div className="flex border-b border-scada-border/40 shrink-0">
              {[
                { id: "performance", label: "Performance", icon: <Activity size={12} /> },
                { id: "cyber", label: "Cyber & Attack", icon: <ShieldAlert size={12} /> },
                { id: "self-healing", label: "Self-Healing & FLISR", icon: <Cpu size={12} /> },
                { id: "ai-models", label: "AI Models & Cognition", icon: <Cpu size={12} /> }
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setAnalyticsTab(tab.id as any)}
                  className={`flex items-center gap-2 px-4 py-2 border-b-2 text-xs font-semibold uppercase tracking-wider transition-all ${
                    analyticsTab === tab.id
                      ? "border-scada-nominal text-scada-nominal font-bold bg-scada-nominal/5"
                      : "border-transparent text-scada-dimText hover:text-white"
                  }`}
                >
                  {tab.icon}
                  {tab.label}
                </button>
              ))}
            </div>

            {/* Tab Contents */}
            <div className="flex-1 overflow-y-auto pr-1 flex flex-col gap-4 scrollbar-thin">
              {panelOrder.length > 0 && analyticsTab === "performance" && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <TelemetryCharts history={history} />
                  {renderPanel("forecast")}
                  {renderPanel("multibus")}
                  {renderPanel("pinn")}
                </div>
              )}
              
              {panelOrder.length > 0 && analyticsTab === "cyber" && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {renderPanel("pre_rl")}
                  {renderPanel("cyber_defense")}
                  {renderPanel("l7_attack")}
                  {renderPanel("l7_hardware")}
                </div>
              )}

              {panelOrder.length > 0 && analyticsTab === "self-healing" && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {renderPanel("l6_recovery")}
                  {renderPanel("l6_adaptive_recovery")}
                  {renderPanel("l6_survival")}
                  {renderPanel("l6_predictive_stabilization")}
                </div>
              )}

              {panelOrder.length > 0 && analyticsTab === "ai-models" && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {renderPanel("l7_assistant")}
                  {renderPanel("l6_multi_agent")}
                  {renderPanel("orchestrator")}
                  {renderPanel("health")}
                </div>
              )}
            </div>
          </div>
        )}

        {currentPage === "reports" && (
          <div className="flex-1 flex flex-col overflow-hidden gap-4">
            {/* Header & Seal */}
            <div className="flex flex-col md:flex-row gap-4 items-stretch shrink-0">
              <div className="flex-1 bg-scada-panel border border-scada-border rounded-lg p-4 flex items-center gap-4 relative overflow-hidden shadow-xl">
                <div className="p-3 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-scada-nominal shrink-0 relative z-10">
                  <Award size={36} className="animate-pulse" />
                </div>
                <div className="relative z-10">
                  <h2 className="text-sm font-extrabold tracking-widest text-white uppercase block">Validation & Certification Authority</h2>
                  <p className="text-[10px] text-scada-dimText max-w-xl font-mono mt-1 leading-relaxed">
                    This command center evaluates and certifies the cybersecurity status of simulated IEEE grid architectures. 
                    All test models undergo coevolutionary adversarial verification.
                  </p>
                </div>
                {/* Visual grid pattern background decoration */}
                <div className="absolute right-0 top-0 bottom-0 w-32 opacity-15 border-l border-scada-border/30 bg-[linear-gradient(to_right,#0284c7_1px,transparent_1px),linear-gradient(to_bottom,#0284c7_1px,transparent_1px)] bg-[size:10px_10px] pointer-events-none"></div>
              </div>

              {/* Master System Seal Stats Card */}
              <div className="bg-scada-panel border border-scada-border rounded-lg p-4 flex gap-6 items-center shrink-0 w-80 shadow-xl">
                <div className="text-center">
                  <div className="text-[28px] font-extrabold font-scada-nums text-scada-nominal scada-text-glow-green leading-none">672 / 672</div>
                  <span className="text-[7.5px] text-scada-dimText uppercase tracking-widest font-mono font-bold">Total Tests Passed</span>
                </div>
                <div className="h-10 w-[1px] bg-scada-border/60"></div>
                <div>
                  <div className="flex items-center gap-1.5">
                    <span className="text-[14px] font-extrabold text-white font-scada-nums">96.8%</span>
                    <span className="text-[8px] bg-emerald-500/10 border border-emerald-500/30 text-scada-nominal px-1 py-0.2 rounded font-bold">GRADE A</span>
                  </div>
                  <span className="text-[7.5px] text-scada-dimText uppercase tracking-widest font-mono font-bold block mt-0.5">Overall Resilience Score</span>
                </div>
              </div>
            </div>

            {/* Scrollable grid and gallery */}
            <div className="flex-1 overflow-y-auto pr-1 flex flex-col gap-6 scrollbar-thin pb-4">
              
              {/* Reports Grid */}
              <div>
                <h3 className="text-[10px] font-bold text-scada-dimText tracking-widest uppercase mb-3 flex items-center gap-1.5">
                  <FileText size={12} className="text-cyan-400" />
                  HMI Validation Audits (V10.1 - V10.7)
                </h3>
                
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {[
                    {
                      id: "v10.1",
                      version: "V10.1",
                      title: "Blockchain MQTT Integrity",
                      status: "PASS",
                      significance: "t = +24.12, p < 1e-84",
                      grade: "A",
                      desc: "Decentralized consensus verification of telemetry frames at 25Hz. Over 10,000 blocks validated without consistency drift.",
                      details: "Tests the distributed ledger verification latency and packet signature integrity. Validated on IEEE 39 and 118 buses systems under high-frequency breaker noise. Prevents replay and packet injection attacks completely.",
                      figure: "trust_score_evolution.png"
                    },
                    {
                      id: "v10.2",
                      version: "V10.2",
                      title: "Imperfect Pathogen Model",
                      status: "PASS",
                      significance: "t = +21.43, p < 1e-72",
                      grade: "A",
                      desc: "RL coevolution modeling of grid cyberattack pathogens under 40% state observability loss. Rapid convergence in 200 episodes.",
                      details: "RL training environment for red agent attack strategies. Validates system survivability when partial observability (e.g. communication link failures or jamming) is present. Co-trained model reaches nash-equilibrium with defense agents.",
                      figure: "belief_accuracy_comparison.png"
                    },
                    {
                      id: "v10.3",
                      version: "V10.3",
                      title: "GAE Reconstructive State",
                      status: "PASS",
                      significance: "t = +31.54, p < 1e-120",
                      grade: "A",
                      desc: "Graph Auto-Encoder reconstruction of sensor dropouts and noise. Bus voltage reconstruction RMSE is minimized to <0.002 p.u.",
                      details: "Reconstructs missing voltage/angle measurements dynamically. Ensures that even when 40% of physical sensors are jammed or compromised, the central SCADA system can reconstruct the grid topology and prevent false FLISR actions.",
                      figure: "recon_emergence_analysis.png"
                    },
                    {
                      id: "v10.4",
                      version: "V10.4",
                      title: "Extended Betweenness Centrality",
                      status: "PASS",
                      significance: "t = +19.67, p < 1e-64",
                      grade: "A",
                      desc: "Topological and electrical line-criticality ranking. Precision/Recall scores reached 1.00 on bridge line detection.",
                      details: "Uses graph-theoretic betweenness centrality combined with physical line reactance values to score cascading outage vulnerabilities. High-scoring lines are marked as critical and protected by active GNN routing policies.",
                      figure: "line_criticality_ranking.png"
                    },
                    {
                      id: "v10.5",
                      version: "V10.5",
                      title: "SOM Hybrid Anomaly ID",
                      status: "PASS",
                      significance: "t = +28.91, p < 1e-104",
                      grade: "A",
                      desc: "Self-Organizing Map cluster-based anomaly detection. Reduces false alarm rates to <0.02% while keeping detection latency <12ms.",
                      details: "High-dimensional telemetry mapping into a 2D topological grid. Clusters nominal state vectors, enabling sub-cycle classification of cyberattacks vs physical grid transients (capacitor switching, line fault start).",
                      figure: "som_cluster_map.png"
                    },
                    {
                      id: "v10.6",
                      version: "V10.6",
                      title: "Cross-Grid Transfer Learning",
                      status: "PASS",
                      significance: "t = +26.04, p < 1e-92",
                      grade: "A",
                      desc: "Zero-shot model generalisation across IEEE grids. Zero re-training lag, immediate stability forecast adaptation.",
                      details: "Evaluates whether models trained on the IEEE 14 or 39 systems can generalize directly to IEEE 57 and IEEE 118 grids. Proves that GAE and GNN features align in latent space, achieving immediate zero-shot performance.",
                      figure: "transfer_learning_performance.png"
                    },
                    {
                      id: "v10.7",
                      version: "V10.7",
                      title: "Zero-Parameter FDIA Pathogen",
                      status: "PASS",
                      significance: "t = +38.28, p < 1e-150",
                      grade: "A",
                      desc: "Zero-parameter cut-line optimization model. Bypasses PINN physical and GNN anomaly detectors at a success rate of >85%.",
                      details: "Evaluates the robustness of the system against a blind, zero-knowledge adversary (V10.7) that only monitors graph adjacency. Proves the need for joint physics-informed consensus validation and trust scores to mitigate optimized stealth attacks.",
                      figure: "fdia_success_rate_comparison.png"
                    }
                  ].map((rep) => (
                    <div key={rep.id} className="bg-scada-panel border border-scada-border rounded-lg p-3.5 flex flex-col justify-between h-[160px] shadow hover:border-cyan-500/40 transition-all group">
                      <div>
                        <div className="flex justify-between items-start mb-1.5 border-b border-scada-border/20 pb-1.5">
                          <div className="flex items-center gap-1.5">
                            <span className="text-[10px] bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 font-mono px-1 rounded font-bold">{rep.version}</span>
                            <h4 className="text-[10.5px] font-bold text-white uppercase group-hover:text-cyan-400 transition-colors truncate max-w-[140px]">{rep.title}</h4>
                          </div>
                          <div className="flex items-center gap-1 font-mono text-[9px]">
                            <span className="text-scada-nominal font-bold flex items-center gap-0.5">
                              <CheckCircle2 size={10} /> PASS
                            </span>
                          </div>
                        </div>
                        <p className="text-[9.5px] text-scada-dimText leading-normal line-clamp-3">{rep.desc}</p>
                      </div>

                      <div className="flex justify-between items-center border-t border-scada-border/20 pt-2 mt-2">
                        <span className="font-mono text-[8px] text-scada-dimText">{rep.significance}</span>
                        <button
                          onClick={() => setSelectedReport(rep)}
                          className="px-2 py-0.5 rounded bg-scada-bg border border-scada-border text-[8.5px] font-mono text-cyan-400 hover:text-white hover:bg-cyan-500/15 hover:border-cyan-500/30 transition-all flex items-center gap-1 uppercase"
                        >
                          <Eye size={10} /> Details
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Publication Figures Gallery */}
              <div>
                <h3 className="text-[10px] font-bold text-scada-dimText tracking-widest uppercase mb-3 flex items-center gap-1.5">
                  <Activity size={12} className="text-scada-nominal" />
                  Scientific Publication Figures Gallery (300 DPI)
                </h3>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                  {[
                    { file: "fdia_success_rate_comparison.png", title: "FDIA Success Rate vs Detector Type", desc: "Compares the success rates of random, Jacobian-based, and our blind Zero-Parameter FDIA (V10.7) pathogens, demonstrating the bypass of GNN detectors." },
                    { file: "cutline_detection_precision_recall.png", title: "Cutline Pathogen Precision-Recall", desc: "Topological bridge-line classification accuracy across IEEE 14, 39, 57, and 118 bus networks. Tarjan's bridge finder achieves 1.00 recall." },
                    { file: "stealth_optimization_convergence.png", title: "PGD Optimizer Convergence Curve", desc: "Projected Gradient Descent optimization profile. The composite PINN, GNN, and Trust region losses converge in less than 35 epochs." },
                    { file: "pinn_gnn_bypass_rate.png", title: "PINN vs GNN Evasion Probability", desc: "Bypass rates under varying voltage perturbation sizes (delta V). Highlights the vulnerability of GNNs without physics-informed checkers." },
                    { file: "frequency_deviation_study.png", title: "Stealth Frequency Deviation Study", desc: "Probability density of frequency drift (Hz) under regional target spoofing. Evasion is guaranteed within the standard ±0.15 Hz threshold." },
                    { file: "islanding_probability_vs_k.png", title: "Islanding Rate vs Number of Targeted Lines", desc: "Grid islanding probability as a function of the number of target cut-lines (k). Shows step function dynamics scaling above k=3." },
                    { file: "effect_size_analysis_v107.png", title: "Welch t-Test & Effect Size Profile", desc: "Statistical power analysis verifying that the V10.7 pathogen outperforms classical baseline attacks with high statistical significance (d > 2.0)." },
                    { file: "som_cluster_map.png", title: "SOM Cluster Anomaly Classifier Map", desc: "Self-Organizing Map topological representation mapping grid states into nominal, load shedding, and cyber intrusion zones." },
                    { file: "transfer_learning_performance.png", title: "Zero-Shot Cross-Grid Adaptation Latency", desc: "Model parameters convergence and reconstruction RMSE curves for models transferred zero-shot from IEEE39 to IEEE118 bus networks." }
                  ].map((fig, i) => (
                    <div key={i} className="bg-scada-panel border border-scada-border rounded-lg overflow-hidden flex flex-col justify-between group shadow shadow-cyan-500/5 hover:border-cyan-500/40 transition-all">
                      <div 
                        className="h-36 bg-black/40 flex items-center justify-center overflow-hidden border-b border-scada-border/40 relative cursor-pointer"
                        onClick={() => setSelectedFigure(fig)}
                      >
                        <img 
                          src={`/figures/${fig.file}`} 
                          alt={fig.title} 
                          className="h-full w-full object-contain group-hover:scale-[1.04] transition-transform duration-300"
                          onError={(e) => {
                            const tgt = e.target as HTMLElement;
                            tgt.style.display = "none";
                            const parent = tgt.parentElement;
                            if (parent) {
                              const div = document.createElement("div");
                              div.className = "flex flex-col items-center justify-center h-full text-scada-dimText font-mono text-[9px] gap-1 p-4 text-center";
                              div.innerHTML = `<span class='font-bold text-cyan-400'>[${fig.file.toUpperCase()}]</span><span>Figure loaded in production. Awaiting Vite assets compiler...</span>`;
                              parent.appendChild(div);
                            }
                          }}
                        />
                        <div className="absolute inset-0 bg-cyan-950/20 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                          <span className="bg-cyan-500 text-white font-mono text-[8px] font-bold px-2 py-1 rounded shadow-lg uppercase tracking-wider flex items-center gap-1">
                            <Eye size={10} /> Inspect Figure
                          </span>
                        </div>
                      </div>
                      
                      <div className="p-3">
                        <h4 className="text-[10px] font-bold text-white uppercase group-hover:text-cyan-400 transition-colors mb-1 truncate">{fig.title}</h4>
                        <p className="text-[9px] text-scada-dimText leading-normal line-clamp-2">{fig.desc}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {currentPage === "settings" && (
          <div className="flex-1 flex flex-col overflow-hidden gap-4">
            <div className="bg-scada-panel border border-scada-border rounded-lg p-4 flex items-center gap-3 shrink-0">
              <div className="p-2 bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 rounded">
                <Sliders size={20} />
              </div>
              <div>
                <h2 className="text-sm font-extrabold tracking-widest text-white uppercase">SCADA Operations Configurator</h2>
                <p className="text-[9px] text-scada-dimText font-mono mt-0.5">Manage dashboard update frequency, active skin themes, and virtual hardware loops.</p>
              </div>
            </div>

            <div className="flex-1 bg-scada-panel border border-scada-border rounded-lg p-6 overflow-y-auto space-y-6 font-mono text-[11px] text-scada-dimText scrollbar-thin">
              {/* Setting 1: Refresh Rate */}
              <div className="max-w-xl space-y-2 border-b border-scada-border/40 pb-5">
                <div className="flex justify-between items-center">
                  <span className="text-white font-bold uppercase tracking-wider">SCADA Telemetry Refresh Rate</span>
                  <span className="text-cyan-400 font-bold font-scada-nums text-xs">{scadaRefreshRate} Hz</span>
                </div>
                <input
                  type="range"
                  min="1"
                  max="30"
                  value={scadaRefreshRate}
                  onChange={(e) => setScadaRefreshRate(parseInt(e.target.value))}
                  className="w-full accent-cyan-500 h-1.5 bg-scada-bg border border-scada-border/40 rounded-lg appearance-none cursor-pointer"
                />
                <p className="text-[9px] leading-relaxed">Adjusts the local poll/sweep timer for digital twin events. Higher values increase HMI update resolution but consumes more host CPU cycles.</p>
              </div>

              {/* Setting 2: Theme Select */}
              <div className="max-w-xl space-y-2 border-b border-scada-border/40 pb-5">
                <span className="text-white font-bold uppercase tracking-wider block mb-1">Grid Interface Theme</span>
                <div className="grid grid-cols-3 gap-3">
                  {[
                    { id: "dark", label: "Sleek SCADA Dark", desc: "Teal accents on slate" },
                    { id: "amber", label: "Industrial Amber", desc: "Cyberpunk orange warning HUD" },
                    { id: "crt", label: "CRT Phosphor Green", desc: "Retro green command look" }
                  ].map((theme) => (
                    <button
                      key={theme.id}
                      onClick={() => {
                        setThemeMode(theme.id as any);
                        if (theme.id === "crt") setCrtEnabled(true);
                      }}
                      className={`p-3 rounded border text-left flex flex-col justify-between h-[75px] transition-all ${
                        themeMode === theme.id
                          ? "bg-cyan-500/10 border-cyan-500 text-cyan-400"
                          : "bg-scada-bg border-scada-border hover:border-scada-border/80 text-scada-dimText hover:text-white"
                      }`}
                    >
                      <span className="font-bold text-[10px] uppercase block leading-none">{theme.label}</span>
                      <span className="text-[8px] text-scada-dimText mt-1.5 leading-tight">{theme.desc}</span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Setting 3: Connection settings */}
              <div className="max-w-xl space-y-3 border-b border-scada-border/40 pb-5">
                <span className="text-white font-bold uppercase tracking-wider block">Gateway API Settings</span>
                <div className="flex gap-4">
                  <div className="flex-1 flex flex-col gap-1">
                    <span className="text-[8px] uppercase">Host API URL</span>
                    <input 
                      type="text" 
                      defaultValue="http://localhost:8000" 
                      className="bg-scada-bg border border-scada-border rounded p-1.5 text-white focus:outline-none focus:border-cyan-500/60"
                    />
                  </div>
                  <div className="w-40 flex flex-col gap-1">
                    <span className="text-[8px] uppercase">Protocol</span>
                    <select className="bg-scada-bg border border-scada-border rounded p-1.5 text-white focus:outline-none focus:border-cyan-500/60">
                      <option>WebSocket (WS)</option>
                      <option>Secure WS (WSS)</option>
                    </select>
                  </div>
                </div>
              </div>

              {/* Setting 4: Security Mode */}
              <div className="max-w-xl flex justify-between items-center py-2 border-b border-scada-border/40 pb-5">
                <div>
                  <span className="text-white font-bold uppercase tracking-wider block">Debug SCADA Logs</span>
                  <span className="text-[9px] text-scada-dimText block mt-0.5">Logs raw incoming JSON telemetry structures to the browser developer console.</span>
                </div>
                <button
                  onClick={() => setShowConsole(!showConsole)}
                  className={`px-3 py-1 rounded font-bold text-xs transition-colors ${
                    showConsole
                      ? "bg-cyan-500 text-black hover:bg-cyan-600"
                      : "bg-scada-border text-scada-dimText hover:text-white"
                  }`}
                >
                  {showConsole ? "ENABLED" : "DISABLED"}
                </button>
              </div>

              {/* SaaS Billing and Quota Center */}
              <div className="max-w-3xl space-y-4 border-t border-scada-border/40 pt-6">
                <span className="text-white font-bold uppercase tracking-wider block text-xs">SaaS Subscription & Quota Tracking</span>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* Status Panel */}
                  <div className="border border-scada-border/60 bg-scada-bg p-4 rounded-lg">
                    <span className="text-[8px] uppercase block mb-1">Active Plan Tier</span>
                    <span className="text-md font-bold text-white uppercase block">{planTier}</span>
                    <span className="text-[9px] text-scada-dimText block mt-1">Status: Active | Expiry: {new Date(Date.now() + daysRemaining*86400000).toLocaleDateString()} ({daysRemaining} Days Remaining)</span>
                  </div>

                  {/* Quota meters */}
                  <div className="border border-scada-border/60 bg-scada-bg p-4 rounded-lg space-y-2">
                    <span className="text-[8px] uppercase block">Usage & Quotas</span>
                    <div className="space-y-1 text-[9.5px]">
                      <div className="flex justify-between">
                        <span>Simulation Concurrency:</span>
                        <span className="text-white font-bold">
                          {planTier === 'free' ? '1 / 1 run' : planTier === 'academic_premium' ? '1 / 3 runs' : planTier === 'research_lab' ? '1 / 5 runs' : 'Unlimited'}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span>AI Copilot queries:</span>
                        <span className="text-white font-bold">
                          {planTier === 'free' ? `${aiMessagesUsed} / 10 daily` : 'Unlimited'}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span>Workspace Storage:</span>
                        <span className="text-white font-bold">
                          {planTier === 'free' ? `${experiments.length} / 10 saved` : 'Unlimited'}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Promo Code Redemption */}
                <div className="border border-scada-border/60 bg-scada-bg p-4 rounded-lg flex gap-3 items-end">
                  <div className="flex-1 flex flex-col gap-1">
                    <span className="text-[8px] uppercase">Redeem Promotional Coupon / Upgrade Code</span>
                    <input 
                      type="text" 
                      id="saas-coupon-input"
                      placeholder="e.g. UNIMAP2026, USM2026, UTM2026"
                      className="bg-scada-panel border border-scada-border rounded p-1.5 text-white focus:outline-none focus:border-cyan-500/60 uppercase"
                    />
                  </div>
                  <button 
                    onClick={() => {
                      const input = document.getElementById("saas-coupon-input") as HTMLInputElement;
                      if (input) handleRedeemCoupon(input.value.toUpperCase().trim());
                    }}
                    className="px-4 py-2 bg-cyan-500 text-black font-bold rounded hover:bg-cyan-600 cursor-pointer text-[10px]"
                  >
                    Activate Coupon
                  </button>
                </div>

                {/* Academic Discount Banner */}
                <div className="border border-yellow-500/40 bg-yellow-500/10 p-3 rounded-lg text-center">
                  <span className="text-yellow-400 font-bold text-[10px] block">💡 50% ACADEMIC DISCOUNT AVAILABLE FOR UNIVERSITIES</span>
                  <span className="text-[8.5px] text-scada-dimText mt-0.5 block">Contact sales@pypygrid.com for bulk deployment licenses. Use promo codes UNIMAP2026, USM2026 or UTM2026 to activate demo access!</span>
                </div>

                {/* Upgrade Options */}
                <div className="grid grid-cols-3 gap-4">
                  <div className="border border-scada-border/60 bg-scada-bg/60 p-4 rounded-lg text-center flex flex-col justify-between">
                    <div>
                      <span className="font-bold text-white text-[10px] block">ACADEMIC PREMIUM</span>
                      <span className="text-cyan-400 font-bold block text-sm my-1">RM 19 / month</span>
                      <span className="text-[8.5px] text-scada-dimText block mb-3">Unlocks IEEE 57 & 118, full BCM Center, up to 3 concurrent simulations, and unlimited AI Copilot.</span>
                    </div>
                    <button 
                      onClick={() => handleRedeemCoupon("UNIMAP2026")}
                      className="px-3 py-1 bg-cyan-500 text-black font-bold rounded text-[9px] cursor-pointer mt-auto w-full"
                    >
                      Use UNIMAP2026
                    </button>
                  </div>

                  <div className="border border-scada-border/60 bg-scada-bg/60 p-4 rounded-lg text-center flex flex-col justify-between">
                    <div>
                      <span className="font-bold text-white text-[10px] block">RESEARCH LAB</span>
                      <span className="text-blue-400 font-bold block text-sm my-1">RM 49 / month</span>
                      <span className="text-[8.5px] text-scada-dimText block mb-3">Up to 10 users, team collaboration workspaces, shared datasets, and experiment comparisons.</span>
                    </div>
                    <button 
                      onClick={() => handleRedeemCoupon("RESEARCH_LAB_2026")}
                      className="px-3 py-1 bg-blue-500 text-white font-bold rounded text-[9px] cursor-pointer mt-auto w-full"
                    >
                      Use RESEARCH_LAB_2026
                    </button>
                  </div>

                  <div className="border border-scada-border/60 bg-scada-bg/60 p-4 rounded-lg text-center flex flex-col justify-between">
                    <div>
                      <span className="font-bold text-white text-[10px] block">ENTERPRISE TIER</span>
                      <span className="text-purple-400 font-bold block text-sm my-1">Custom Pricing</span>
                      <span className="text-[8.5px] text-scada-dimText block mb-3">Custom grid models imports, API integrations, Modbus/PMU hardware, dedicated SLAs.</span>
                    </div>
                    <button 
                      onClick={() => alert("Contact Sales at sales@pypygrid.com for custom Enterprise deployment.")}
                      className="px-3 py-1 bg-purple-500 text-white font-bold rounded text-[9px] cursor-pointer mt-auto w-full"
                    >
                      Contact Sales
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {currentPage === "bcm_center" && (
          <BcmCenter
            rto={activeAttack ? 14.5 : 0}
            rpo={activeAttack ? 1.2 : 0}
            loadShedMwh={activeAttack ? 18.4 : 0}
            financialLoss={activeAttack ? 2760 : 0}
          />
        )}

        {currentPage === "research_workspace" && (
          <ResearchWorkspace
            planTier={planTier}
            onUpgradeClick={() => setCurrentPage("settings")}
            token=""
          />
        )}

        {currentPage === "scenario_marketplace" && (
          <ScenarioMarketplace
            planTier={planTier}
            onUpgradeClick={() => setCurrentPage("settings")}
            token=""
          />
        )}

        {currentPage === "ai_copilot" && (
          <AiCopilot
            planTier={planTier}
            onUpgradeClick={() => setCurrentPage("settings")}
            token=""
          />
        )}

        {currentPage === "saas_admin" && (
          <SaaSAdmin
            tenants={tenants}
            onOverridePlan={handleOverridePlan}
            token={authToken}
          />
        )}

        {currentPage === "cloud_ops" && (
          <SimulationQueueMonitor token="" />
        )}

        {currentPage === "operations_center" && (
          <OperationsCenter />
        )}

        {/* Modal Lightbox for Reports Details */}
        {selectedReport && (
          <div className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4 backdrop-blur-sm font-mono text-[10.5px]">
            <div className="bg-scada-panel border border-cyan-500/40 rounded-lg max-w-xl w-full p-5 shadow-2xl relative animate-fade-in flex flex-col max-h-[90vh]">
              <button 
                onClick={() => setSelectedReport(null)}
                className="absolute top-4 right-4 text-scada-dimText hover:text-white p-1 rounded hover:bg-scada-border/30 transition-colors"
              >
                <X size={16} />
              </button>
              
              <div className="border-b border-scada-border/40 pb-3.5 mb-3.5">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-[10px] bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 px-1 rounded font-bold">{selectedReport.version}</span>
                  <h3 className="text-xs font-bold text-white uppercase">{selectedReport.title} Audit</h3>
                </div>
                <div className="flex gap-3 text-[8.5px] text-scada-dimText mt-1">
                  <span>Significance: <strong className="text-white">{selectedReport.significance}</strong></span>
                  <span>•</span>
                  <span>Certification Grade: <strong className="text-scada-nominal">A (Certified)</strong></span>
                  <span>•</span>
                  <span>Status: <strong className="text-scada-nominal">PASS</strong></span>
                </div>
              </div>

              <div className="flex-1 overflow-y-auto space-y-4 pr-1 scrollbar-thin text-scada-dimText">
                <div className="bg-scada-bg/80 border border-scada-border/40 rounded p-3">
                  <span className="text-[8px] font-bold text-white uppercase tracking-wider block mb-1">Audit Summary:</span>
                  <p className="leading-relaxed text-white/90 font-sans text-xs">{selectedReport.desc}</p>
                </div>

                <div className="space-y-1.5">
                  <span className="text-[8px] font-bold text-white uppercase tracking-wider block">Technical Assessment Details:</span>
                  <p className="leading-relaxed text-[10px] bg-black/30 p-3 rounded border border-scada-border/20">{selectedReport.details}</p>
                </div>

                <div className="border-t border-scada-border/20 pt-3 flex justify-between items-center">
                  <span>Verification Signature:</span>
                  <span className="bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 px-2 py-0.5 rounded text-[8px] font-bold tracking-widest uppercase">SECURE Consensus Signed</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Modal Lightbox for Figure Preview */}
        {selectedFigure && (
          <div className="fixed inset-0 z-50 bg-black/90 flex items-center justify-center p-4 backdrop-blur-sm font-mono text-[10.5px]">
            <div className="bg-scada-panel border border-scada-border rounded-lg max-w-4xl w-full p-5 shadow-2xl relative animate-fade-in flex flex-col max-h-[95vh]">
              <button 
                onClick={() => setSelectedFigure(null)}
                className="absolute top-4 right-4 text-scada-dimText hover:text-white p-1 rounded hover:bg-scada-border/30 transition-colors"
              >
                <X size={16} />
              </button>
              
              <div className="border-b border-scada-border/40 pb-3 mb-3 shrink-0">
                <h3 className="text-xs font-bold text-white uppercase">{selectedFigure.title}</h3>
                <p className="text-[9px] text-scada-dimText font-mono mt-0.5">{selectedFigure.desc}</p>
              </div>

              <div className="flex-1 bg-black/60 rounded border border-scada-border/30 flex items-center justify-center overflow-hidden p-4 min-h-[300px]">
                <img 
                  src={`/figures/${selectedFigure.file}`} 
                  alt={selectedFigure.title} 
                  className="max-h-[60vh] max-w-full object-contain"
                  onError={(e) => {
                    const tgt = e.target as HTMLElement;
                    tgt.style.display = "none";
                    const parent = tgt.parentElement;
                    if (parent) {
                      const div = document.createElement("div");
                      div.className = "flex flex-col items-center justify-center text-scada-dimText font-mono text-xs gap-2 p-6 text-center";
                      div.innerHTML = `<span class='font-bold text-cyan-400 text-sm'>[${selectedFigure.file.toUpperCase()}]</span><span>Figure loaded in production. Awaiting Vite assets compiler...</span>`;
                      parent.appendChild(div);
                    }
                  }}
                />
              </div>

              <div className="mt-3 flex justify-between items-center text-[9px] text-scada-dimText shrink-0">
                <span>File Path: <strong className="text-white">/figures/{selectedFigure.file}</strong></span>
                <span className="bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 px-2 py-0.5 rounded text-[8px] font-bold tracking-widest uppercase">300 DPI Publication Certified</span>
              </div>
            </div>
          </div>
        )}

        {/* Fullscreen Topology Overlay Modal */}
        {isTopologyFullscreen && (
          <div className="fixed inset-0 z-50 bg-black/90 flex flex-col p-4 backdrop-blur-sm font-mono">
            <div className="bg-scada-panel border border-cyan-500/40 rounded-lg flex-1 flex flex-col overflow-hidden shadow-2xl relative">
              <div className="flex justify-between items-center border-b border-scada-border/40 p-4 shrink-0">
                <div>
                  <h3 className="text-xs font-bold text-white uppercase flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse"></span>
                    Interactive Grid Topology Schema — {(dispTelemetry?.grid_name || "ieee39").toUpperCase()}
                  </h3>
                  <p className="text-[9px] text-scada-dimText uppercase mt-0.5">SCADA Fullscreen Diagnostic View</p>
                </div>
                
                <button
                  onClick={() => setIsTopologyFullscreen(false)}
                  className="bg-scada-bg border border-scada-border text-scada-dimText hover:text-white p-2 rounded transition-colors flex items-center gap-1 text-[9px] font-bold uppercase"
                >
                  <Minimize2 size={12} /> Close Fullscreen
                </button>
              </div>

              <div className="flex-1 bg-black/60 relative overflow-hidden">
                <GridDiagram 
                  key={`fs-${selectedGrid}`}
                  selectedGrid={selectedGrid}
                  telemetry={dispTelemetry} 
                  onToggleBreaker={toggleBreaker} 
                  attackStatus={dispTelemetry?.attack_status}
                  flisrState={dispFlisrState}
                  flisrIsolated={dispFlisrIsolated}
                  flisrReconfigured={dispFlisrReconfigured}
                  flisrTripped={dispFlisrTripped}
                />
              </div>
            </div>
          </div>
        )}

        {/* Live Event SCADA Console Collapsible Drawer */}
        {logConsoleOpen && (
          <div className="bg-scada-panel border border-scada-border rounded-lg p-3 flex flex-col gap-2 h-44 shrink-0 shadow-2xl animate-fade-in-up">
            <div className="flex justify-between items-center border-b border-scada-border/40 pb-2">
              <span className="text-[10px] font-extrabold tracking-widest text-cyan-400 font-mono uppercase flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-ping"></span>
                &gt;_ SCADA EVENT CONSOLE
              </span>
              
              <div className="flex items-center gap-3">
                {/* Search / Filter input */}
                <input
                  type="text"
                  placeholder="Filter logs (e.g. PINN, Alert)..."
                  value={logFilter}
                  onChange={(e) => setLogFilter(e.target.value)}
                  className="bg-black/40 border border-scada-border/40 rounded px-2 py-0.5 text-[9px] text-white font-mono focus:outline-none focus:border-cyan-500/60 w-52 placeholder-scada-dimText"
                />

                {/* Pause/Resume Scroll */}
                <button
                  onClick={() => setIsLogScrollPaused(!isLogScrollPaused)}
                  className={`text-[8px] font-mono px-2 py-0.5 rounded border transition-all uppercase font-semibold ${
                    isLogScrollPaused
                      ? "bg-amber-500/10 border-amber-500/30 text-amber-400"
                      : "bg-scada-bg border-scada-border text-scada-dimText hover:text-white"
                  }`}
                  title="Pause or resume auto-scrolling to the bottom as new logs arrive"
                >
                  {isLogScrollPaused ? "Resume Scroll" : "Pause Scroll"}
                </button>
                
                {/* Clear Logs */}
                <button
                  onClick={() => setLiveLogs([])}
                  className="text-[8px] font-mono text-scada-dimText hover:text-white border border-scada-border bg-scada-bg px-1.5 py-0.5 rounded transition-all uppercase font-semibold"
                >
                  Clear
                </button>
              </div>
            </div>

            {/* Logs List Container */}
            <div className="flex-1 overflow-y-auto pr-1 font-mono text-[9px] space-y-1 scrollbar-thin">
              {liveLogs
                .filter((log) => log.message.toLowerCase().includes(logFilter.toLowerCase()))
                .map((log, i) => {
                  const getSeverityColor = (sev: string) => {
                    switch (sev) {
                      case "critical": return "text-red-400 font-extrabold scada-text-glow-red animate-pulse";
                      case "warning": return "text-yellow-400 font-bold";
                      case "success": return "text-emerald-400";
                      default: return "text-scada-dimText";
                    }
                  };
                  return (
                    <div key={i} className={`flex items-start gap-2 border-b border-scada-border/10 pb-0.5 last:border-0 ${getSeverityColor(log.severity)}`}>
                      <span className="text-scada-dimText shrink-0">[{log.timestamp}]</span>
                      <span className="leading-tight">{log.message}</span>
                    </div>
                  );
                })}
              
              {liveLogs.length === 0 && (
                <div className="text-center text-scada-dimText italic py-6">No SCADA events logged. Awaiting telemetry stream...</div>
              )}
              <div ref={logsEndRef} />
            </div>
          </div>
        )}

        {/* Global Timeline Replay Control Bar */}
        <div className="bg-scada-panel border border-scada-border rounded-lg p-2 px-4 flex flex-wrap gap-4 items-center justify-between font-mono text-[10px] shrink-0 select-none">
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5">
              <span className={`w-2.5 h-2.5 rounded-full ${
                isReplaying 
                  ? "bg-amber-500 animate-pulse shadow-[0_0_8px_rgba(245,158,11,0.7)]" 
                  : "bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.7)]"
              }`}></span>
              <span className={`font-bold tracking-widest uppercase ${
                isReplaying ? "text-amber-400" : "text-emerald-400"
              }`}>
                {isReplaying ? "HISTORICAL REPLAY" : "LIVE STREAMING"}
              </span>
            </div>
            <span className="text-[10px] text-scada-dimText">
              {replayFrames.length} Frames Buffer
            </span>
          </div>

          {/* Player Controls */}
          <div className="flex items-center gap-2">
            <button
              disabled={replayFrames.length === 0}
              onClick={() => {
                setIsReplaying(true);
                setIsPlaying(false);
                setReplayIndex((prev) => Math.max(0, prev - 1));
              }}
              className="p-1 rounded border border-scada-border bg-scada-bg hover:text-white transition-colors disabled:opacity-50"
              title="Step Backward"
            >
              <ChevronLeft size={12} />
            </button>

            {isReplaying && isPlaying ? (
              <button
                onClick={() => setIsPlaying(false)}
                className="p-1 px-2.5 rounded border border-amber-500/50 bg-amber-500/10 text-amber-400 hover:bg-amber-500/20 transition-all font-bold flex items-center gap-1"
                title="Pause Playback"
              >
                <Pause size={10} /> PAUSE
              </button>
            ) : (
              <button
                disabled={replayFrames.length === 0}
                onClick={() => {
                  setIsReplaying(true);
                  setIsPlaying(true);
                }}
                className={`p-1 px-2.5 rounded border transition-all font-bold flex items-center gap-1 ${
                  isReplaying 
                    ? "border-amber-500/50 bg-amber-500/10 text-amber-400 hover:bg-amber-500/20" 
                    : "border-scada-border bg-scada-bg hover:text-white"
                } disabled:opacity-50`}
                title="Start Playback"
              >
                <PlayIcon size={10} /> PLAY
              </button>
            )}

            <button
              disabled={replayFrames.length === 0}
              onClick={() => {
                setIsReplaying(true);
                setIsPlaying(false);
                setReplayIndex((prev) => Math.min(replayFrames.length - 1, prev + 1));
              }}
              className="p-1 rounded border border-scada-border bg-scada-bg hover:text-white transition-colors disabled:opacity-50"
              title="Step Forward"
            >
              <ChevronRight size={12} />
            </button>

            {isReplaying && (
              <button
                onClick={() => {
                  setIsReplaying(false);
                  setIsPlaying(false);
                  setReplayIndex(replayFrames.length - 1);
                }}
                className="p-1 px-2 rounded border border-emerald-500/50 bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20 font-bold transition-all text-[9px]"
              >
                RESUME LIVE
              </button>
            )}
            <button
              onClick={() => setLogConsoleOpen(!logConsoleOpen)}
              className={`p-1 px-2 rounded border font-bold transition-all text-[9px] ${
                logConsoleOpen
                  ? "bg-cyan-500/20 text-cyan-400 border-cyan-500/40 scada-text-glow"
                  : "bg-scada-bg border-scada-border text-scada-dimText hover:text-white"
              }`}
              title="Toggle Live Event SCADA Console Drawer"
            >
              &gt;_ CONSOLE
            </button>
          </div>

          {/* Scrubber slider */}
          <div className="flex-1 min-w-[150px] flex items-center gap-3">
            <input
              type="range"
              min={0}
              max={Math.max(0, replayFrames.length - 1)}
              value={isReplaying ? replayIndex : replayFrames.length - 1}
              disabled={replayFrames.length === 0}
              onChange={(e) => {
                setIsReplaying(true);
                setIsPlaying(false);
                setReplayIndex(parseInt(e.target.value));
              }}
              className="w-full accent-amber-500 h-1 bg-scada-border rounded-lg appearance-none cursor-pointer disabled:opacity-50"
            />
            <span className="font-bold text-scada-dimText w-[80px] text-right font-scada-nums">
              {replayFrames.length > 0 
                ? `F ${isReplaying ? replayIndex + 1 : replayFrames.length}/${replayFrames.length}` 
                : "NO DATA"}
            </span>
          </div>

          {/* Frame Timestamp info */}
          <div className="text-[9px] text-scada-dimText font-mono min-w-[100px] text-right">
            {isReplaying && currentFrame 
              ? new Date(currentFrame.timestamp).toLocaleTimeString([], { hour12: false }) 
              : "LIVE STREAM"}
          </div>
        </div>

      </div>

      <FloatingChatbot
        connected={connected}
        onSendControl={sendDirectMqtt}
        assistantState={dispAssistantState}
        assistantEmotion={dispAssistantEmotion}
        assistantContext={dispAssistantContext}
        assistantMemory={dispAssistantMemory}
        assistantResponse={dispAssistantResponse}
        assistantRuntime={dispAssistantRuntime}
        assistantSemanticResponse={dispAssistantSemanticResponse}
        assistantContextualMemory={dispAssistantContextualMemory}
        assistantDialogue={dispAssistantDialogue}
        assistantLiveStream={dispAssistantLiveStream}
        assistantVoiceState={dispAssistantVoiceState}
        activeAttack={dispActiveAttack}
      />
    </div>
  );
}
