import { useEffect, useState, useRef, useMemo } from "react";

import { GridDiagram } from "./components/GridDiagram.tsx";
import { TelemetryCharts } from "./components/TelemetryCharts.tsx";
import { AlertsPanel } from "./components/AlertsPanel.tsx";
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
  ArrowRight
} from "lucide-react";

export default function App() {
  const [connected, setConnected] = useState<boolean>(false);
  const [telemetry, setTelemetry] = useState<any>(null);
  const [history, setHistory] = useState<any[]>([]);
  const [events, setEvents] = useState<any[]>([]);
  const [alerts, setAlerts] = useState<any[]>([]);
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
  const [proactiveAutoMode, setProactiveAutoMode] = useState<boolean>(true);
  const [flisrAuto, setFlisrAuto] = useState<boolean>(true);
  const [recording, setRecording] = useState<boolean>(false);
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
  const [annotations, setAnnotations] = useState<Record<string, string>>({});

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
    l7_attack: 2
  });
  const [panelOrder, setPanelOrder] = useState<string[]>([
    "telemetry", "forecast", "multibus", "threat_aware", "pinn", "physics", "trust", "orchestrator", "health", "pre_rl", "cyber_defense", "l6_recovery", "l6_adaptive_recovery", "l6_survival", "l6_predictive_stabilization", "l6_multi_agent", "l7_hardware", "l7_twin", "l7_attack"
  ]);

  // Timeline Replay States
  const [isReplaying, setIsReplaying] = useState<boolean>(false);
  const [replayIndex, setReplayIndex] = useState<number>(0);
  const [replayFrames, setReplayFrames] = useState<any[]>([]);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);

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
      flisrState,
      flisrIsolated,
      flisrReconfigured,
      flisrTripped,
      activeAttack
    };
  }); // Run on every render

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
        } 
        // Handle active MQTT stream broadcasts
        else if (data.topic && data.payload) {
          const { topic, payload } = data;
          
          if (topic === "grid/telemetry") {
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

  const sendAttack = (payload: any) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        topic: "grid/attack",
        payload
      }));
    }
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

  const handleResetAlarms = () => {
    sendControl({ command: "RESET_ALARMS" });
    // Instantly reset local UI states for crisp feedback
    setActiveAttack(null);
    setAttackTarget(null);
    setFlisrState("NORMAL");
    setFlisrIsolated([]);
    setFlisrReconfigured([]);
    setFlisrTripped([]);
    setPreRlData(null);
    setThreatData(null);
    setAiPrediction(null);
    setPredictionHistory([]);
    setMultiBusForecast(null);
    setThreatAwareForecast(null);
    setPhysicsValidation(null);
    setTrustScores(null);
    setAdaptiveFilter(null);
    setAiOrchestrator(null);
    setRecommendedActions(null);
    setL6Recovery(null);
    setL6AdaptiveRecovery(null);
    setL6Containment(null);
    setL6DegradedMode(null);
    setL6Agents(null);
    setL6AgentConsensus(null);
    setL6AgentConflicts(null);
    setL6DistributedState(null);
    setL6AgentConfidence(null);
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
    if (!telemetry?.state?.buses) return 0;
    return Object.values(telemetry.state.buses)
      .filter((b: any) => b.is_gen)
      .reduce((sum: number, b: any) => sum + (b.P_mw || 0), 0);
  };

  const getSumLoadPower = () => {
    if (!telemetry?.state?.buses) return 0;
    return Object.values(telemetry.state.buses)
      .filter((b: any) => b.is_load)
      .reduce((sum: number, b: any) => sum + (b.P_mw || 0), 0);
  };

  const hasActiveTrips = () => {
    if (!telemetry?.state?.breakers) return false;
    return Object.values(telemetry.state.breakers).some((v) => v === "OPEN");
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


  const dispHistory = useMemo(() => {
    if (!isReplaying || !currentFrame || !dispTelemetry) return history;
    return history.filter((h) => h.timestamp <= dispTelemetry.timestamp);
  }, [isReplaying, currentFrame, history, dispTelemetry]);

  const dispPredictionHistory = useMemo(() => {
    if (!isReplaying || !currentFrame || !dispTelemetry) return predictionHistory;
    return predictionHistory.filter((p) => p.timestamp <= dispTelemetry.timestamp);
  }, [isReplaying, currentFrame, predictionHistory, dispTelemetry]);

  const dispEvents = useMemo(() => {
    if (!isReplaying || !currentFrame) return events;
    return events.filter((e) => e.timestamp <= currentFrame.timestamp);
  }, [isReplaying, currentFrame, events]);

  const dispAlerts = useMemo(() => {
    if (!isReplaying || !currentFrame) return alerts;
    return alerts.filter((a) => a.timestamp <= currentFrame.timestamp);
  }, [isReplaying, currentFrame, alerts]);

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

  const handleAddAnnotation = (key: string, note: string) => {
    setAnnotations((prev) => ({
      ...prev,
      [key]: note
    }));
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

  return (
    <div className={`h-screen w-screen flex flex-col justify-between bg-scada-bg text-scada-text p-4 relative select-none overflow-hidden transition-all duration-300 ${
      crtEnabled ? "scada-crt" : ""
    } ${activeAttack === "REPLAY" ? "replay-active-frame border-4" : ""}`}>
      
      {/* Header Panel */}
      <header className={`flex justify-between items-center border border-scada-border rounded-lg p-3 px-4 bg-scada-panel transition-all duration-300 ${
        activeAttack ? "border-red-500/50 bg-red-950/10 scada-glow-red" : "scada-glow-green"
      }`}>
        <div className="flex items-center gap-3">
          <div className="relative">
            <Zap size={22} className={connected ? "text-scada-nominal animate-pulse" : "text-gray-500"} />
            {connected && <span className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-emerald-500 rounded-full animate-ping"></span>}
          </div>
          <div>
            <h1 className="text-md font-bold tracking-widest text-white uppercase flex items-center gap-2">
              Smart Grid Cyber-Physical SCADA Platform
            </h1>
            <p className="text-[10px] text-scada-dimText font-mono uppercase">
              Digital Twin Simulation & Cyber-Attack Response System
            </p>
          </div>
        </div>

        {/* Live Counters */}
        <div className="flex items-center gap-8 font-mono text-xs">
          <div className="flex flex-col items-end">
            <span className="text-[9px] text-scada-dimText uppercase">Total Generation</span>
            <span className="text-scada-nominal font-bold text-sm tracking-wide font-scada-nums scada-text-glow-green">
              {getSumGenPower().toFixed(1)} MW
            </span>
          </div>

          <div className="flex flex-col items-end">
            <span className="text-[9px] text-scada-dimText uppercase">Total Net Load</span>
            <span className="text-scada-nominal font-bold text-sm tracking-wide font-scada-nums scada-text-glow-green">
              {getSumLoadPower().toFixed(1)} MW
            </span>
          </div>

          <div className="flex flex-col items-end">
            <span className="text-[9px] text-scada-dimText uppercase">Grid Status</span>
            {activeAttack ? (
              <span className="text-scada-trip font-bold text-sm animate-bounce scada-text-glow-red flex items-center gap-1">
                <AlertOctagon size={14} /> CYBER ATTACK
              </span>
            ) : hasActiveTrips() ? (
              <span className="text-scada-warning font-bold text-sm animate-pulse scada-text-glow-warning">DEGRADED</span>
            ) : (
              <span className="text-scada-nominal font-bold text-sm scada-text-glow-green">NOMINAL</span>
            )}
          </div>

          <div className="flex flex-col items-end">
            <span className="text-[9px] text-scada-dimText uppercase">AI Forecast (t+10s)</span>
            {aiPrediction && (aiPrediction.predicted_bus5_voltage !== undefined || aiPrediction.predicted_threat !== undefined) ? (
              <>
                {aiPrediction.predicted_bus5_voltage !== undefined ? (
                  <span className={`font-bold text-sm tracking-wide font-scada-nums ${
                    aiPrediction.instability_risk === "CRITICAL" ? "text-red-500 animate-pulse scada-text-glow-red" :
                    aiPrediction.instability_risk === "HIGH" ? "text-orange-500" :
                    aiPrediction.instability_risk === "MEDIUM" ? "text-yellow-500 scada-text-glow-warning" :
                    "text-scada-nominal scada-text-glow-green"
                  }`}>
                    {typeof aiPrediction.predicted_bus5_voltage === "number" ? aiPrediction.predicted_bus5_voltage.toFixed(4) : "1.0000"} pu ({aiPrediction.instability_risk ?? "LOW"})
                  </span>
                ) : (
                  <span className={`font-bold text-sm tracking-wide font-scada-nums ${
                    (aiPrediction.predicted_threat ?? 0) >= 76.0 ? "text-red-500 animate-pulse scada-text-glow-red" :
                    (aiPrediction.predicted_threat ?? 0) >= 51.0 ? "text-orange-500" :
                    (aiPrediction.predicted_threat ?? 0) >= 26.0 ? "text-yellow-500 scada-text-glow-warning" :
                    "text-scada-nominal scada-text-glow-green"
                  }`}>
                    {typeof aiPrediction.predicted_threat === "number" ? aiPrediction.predicted_threat.toFixed(0) : "0"}% ({aiPrediction.cascade_risk ?? "LOW"})
                  </span>
                )}
              </>
            ) : (
              <span className="text-gray-500 font-bold text-sm animate-pulse">WARMING UP...</span>
            )}
          </div>

          <div className="h-8 w-[1px] bg-scada-border"></div>

          {/* Connection Status */}
          <div className="flex items-center gap-2">
            <button 
              onClick={() => setCrtEnabled(!crtEnabled)}
              className={`p-1.5 rounded border transition-all text-[10px] flex items-center gap-1 ${
                crtEnabled ? "bg-scada-nominal/15 border-scada-nominal text-scada-nominal" : "bg-scada-bg border-scada-border text-scada-dimText hover:text-white"
              }`}
              title="Toggle CRT Screen Scanlines"
            >
              <MonitorPlay size={12} /> CRT
            </button>
            <div className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md border ${
              connected ? "bg-emerald-500/10 border-emerald-500/20 text-scada-nominal" : "bg-red-500/10 border-red-500/20 text-scada-trip"
            }`}>
              {connected ? <Wifi size={14} /> : <Cpu size={14} />}
              <span className="font-semibold uppercase tracking-wider text-[10px]">
                {connected ? "Gateway Online" : "Gateway Offline"}
              </span>
            </div>
          </div>
        </div>
      </header>

      {/* Main Workspace Layout */}
      <main className="flex-1 grid grid-cols-1 xl:grid-cols-3 gap-4 my-4 overflow-hidden">
        {/* Left and Middle column: Grid Diagram + Telemetry Charts */}
        <section className="xl:col-span-2 flex flex-col justify-between gap-4 h-full overflow-hidden">
          <div className="shrink-0">
            <GridDiagram 
              telemetry={dispTelemetry} 
              onToggleBreaker={toggleBreaker} 
              attackStatus={dispTelemetry?.attack_status}
              flisrState={dispFlisrState}
              flisrIsolated={dispFlisrIsolated}
              flisrReconfigured={dispFlisrReconfigured}
              flisrTripped={dispFlisrTripped}
            />
          </div>
          
          {/* Lower AI Analytics Layout - Dynamic Collapsible Grid */}
          <div className="flex-1 overflow-y-auto pr-1 flex flex-col gap-4 scrollbar-thin">
            {/* Timeline Replay Control Bar */}
            <div className="bg-scada-panel border border-scada-border rounded-lg p-2 px-4 flex flex-wrap gap-4 items-center justify-between font-mono text-xs shrink-0 select-none">
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
                  <ChevronLeft size={14} />
                </button>

                {isReplaying && isPlaying ? (
                  <button
                    onClick={() => setIsPlaying(false)}
                    className="p-1 px-2.5 rounded border border-amber-500/50 bg-amber-500/10 text-amber-400 hover:bg-amber-500/20 transition-all font-bold flex items-center gap-1"
                    title="Pause Playback"
                  >
                    <Pause size={12} /> PAUSE
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
                    <PlayIcon size={12} /> PLAY
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
                  <ChevronRight size={14} />
                </button>

                {isReplaying && (
                  <button
                    onClick={() => {
                      setIsReplaying(false);
                      setIsPlaying(false);
                      setReplayIndex(replayFrames.length - 1);
                    }}
                    className="p-1 px-2 rounded border border-emerald-500/50 bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20 font-bold transition-all"
                  >
                    RESUME LIVE
                  </button>
                )}
              </div>

              {/* Scrubber slider */}
              <div className="flex-1 min-w-[200px] flex items-center gap-3">
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
                <span className="font-bold text-scada-dimText w-[90px] text-right font-scada-nums">
                  {replayFrames.length > 0 
                    ? `F ${isReplaying ? replayIndex + 1 : replayFrames.length}/${replayFrames.length}` 
                    : "NO DATA"}
                </span>
              </div>

              {/* Frame Timestamp info */}
              <div className="text-[10px] text-scada-dimText font-mono min-w-[120px] text-right">
                {isReplaying && currentFrame 
                  ? new Date(currentFrame.timestamp).toLocaleTimeString([], { hour12: false }) 
                  : "LIVE STREAM"}
              </div>
            </div>

            {/* Dynamic Grid of Panels */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 pb-4">
              {panelOrder.map((panelId) => renderPanel(panelId))}
            </div>
          </div>
        </section>

        {/* Right column: Incident logs, Cyber attack injection console */}
        <section className="h-full flex flex-col justify-between gap-4 overflow-hidden">
          <ThreatScorePanel 
            threatData={dispThreatData}
            onExecuteAction={handleExecuteAction}
            onToggleAutoDefense={handleToggleAutoDefense}
          />

          {/* Timeline & Actions */}
          <div className="flex-1 flex flex-col justify-between bg-scada-panel border border-scada-border rounded-lg p-4 max-h-[180px]">
            <h2 className="text-sm font-semibold tracking-wider text-scada-dimText uppercase mb-2 flex items-center gap-1.5 border-b border-scada-border pb-1.5">
              <Cpu size={16} className="text-scada-nominal" />
              Grid Event Logger
            </h2>
            <div className="flex-1 overflow-y-auto space-y-1 font-mono text-[10px] pr-1">
              {dispEvents
                .filter((ev) => ev.source !== "FLISR_ENGINE")
                .slice(0, 8)
                .map((ev, i) => (
                  <div key={i} className={`flex items-start gap-1 py-0.5 border-b border-scada-border/30 ${
                    ev.severity === "CRITICAL" ? "text-scada-trip" : ev.severity === "WARNING" ? "text-scada-warning" : "text-scada-dimText"
                  }`}>
                    <span className="font-bold text-gray-500 min-w-[55px]">
                      {new Date(ev.timestamp).toLocaleTimeString([], { hour12: false })}
                    </span>
                    <span className="text-white/40 font-semibold uppercase shrink-0">[{ev.source}]</span>
                    <span className="text-scada-text">{ev.event}</span>
                  </div>
                ))}
              {dispEvents.length === 0 && (
                <p className="text-scada-dimText italic">No logs recorded. Awaiting telemetry stream...</p>
              )}
            </div>
          </div>

          {/* Alerts and Attacks */}
          <div className="flex-shrink-0">
            <AlertsPanel
              events={dispEvents}
              alerts={dispAlerts}
              flisrAuto={flisrAuto}
              flisrState={dispFlisrState}
              flisrIsolated={dispFlisrIsolated}
              flisrReconfigured={dispFlisrReconfigured}
              flisrTripped={dispFlisrTripped}
              onSendConfig={sendConfig}
              onSendAttack={sendAttack}
              onSendControl={handleResetAlarms}
              recording={recording}
              setRecording={setRecording}
              activeAttack={dispActiveAttack}
              attackStatus={dispTelemetry?.attack_status}
              annotations={annotations}
              onAddAnnotation={handleAddAnnotation}
            />
          </div>
        </section>
      </main>

      {/* Footer System Tray */}
      <footer className="flex justify-between items-center text-[10px] font-mono text-scada-dimText border border-scada-border rounded-lg p-2 px-4 bg-scada-panel">
        <div className="flex items-center gap-2">
          <Cpu size={12} />
          <span>IEEE 9-Bus Simulation Node</span>
          <span>•</span>
          <span>Telemetry rate: 1.0Hz</span>
        </div>
        <div className="flex items-center gap-4">
          <span className="flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span> Simulator
          </span>
          <span className="flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span> Gateway
          </span>
          <span className="flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span> ML Model
          </span>
          <span className="flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span> FLISR
          </span>
        </div>
      </footer>
    </div>
  );
}
