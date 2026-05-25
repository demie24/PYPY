import { useEffect, useState, useRef } from "react";

import { GridDiagram } from "./components/GridDiagram.tsx";
import { TelemetryCharts } from "./components/TelemetryCharts.tsx";
import { AlertsPanel } from "./components/AlertsPanel.tsx";
import { ThreatScorePanel } from "./components/ThreatScorePanel.tsx";
import { ForecastPanel } from "./components/ForecastPanel.tsx";
import { MultiBusForecastPanel } from "./components/MultiBusForecastPanel.tsx";
import { ThreatAwareForecastPanel } from "./components/ThreatAwareForecastPanel.tsx";
import { PhysicsValidationPanel } from "./components/PhysicsValidationPanel.tsx";
import { TrustAnalysisPanel } from "./components/TrustAnalysisPanel.tsx";

import {
  Wifi,
  Cpu,
  Zap,
  AlertOctagon,
  MonitorPlay
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
  const [physicsValidation, setPhysicsValidation] = useState<any>(null);
  const [trustScores, setTrustScores] = useState<any>(null);
  const [adaptiveFilter, setAdaptiveFilter] = useState<any>(null);
  const [flisrAuto, setFlisrAuto] = useState<boolean>(true);
  const [recording, setRecording] = useState<boolean>(false);
  const [crtEnabled, setCrtEnabled] = useState<boolean>(true);

  // FLISR state tracking
  const [flisrState, setFlisrState] = useState<string>("NORMAL");
  const [flisrIsolated, setFlisrIsolated] = useState<string[]>([]);
  const [flisrReconfigured, setFlisrReconfigured] = useState<string[]>([]);
  const [flisrTripped, setFlisrTripped] = useState<string[]>([]);

  // Cyber attack visual state tracking
  const [activeAttack, setActiveAttack] = useState<string | null>(null);
  const [, setAttackTarget] = useState<string | null>(null);

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
          if (data.ai_prediction) {
            setAiPrediction(data.ai_prediction);
            setPredictionHistory([data.ai_prediction]);
          }
          if (data.ai_forecast_multi_bus) {
            setMultiBusForecast(data.ai_forecast_multi_bus);
          }
          if (data.ai_threat_forecast) {
            setThreatAwareForecast(data.ai_threat_forecast);
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
        } 
        // Handle active MQTT stream broadcasts
        else if (data.topic && data.payload) {
          const { topic, payload } = data;
          
          if (topic === "grid/telemetry") {
            setTelemetry(payload);
            setHistory((prev) => {
              const next = [...prev, payload];
              if (next.length > 50) next.shift();
              return next;
            });

            // Phase 5B: Authoritative attack state from telemetry payload
            // This is the ground-truth source - always in sync with backend
            const atkStatus = payload?.attack_status;
            if (atkStatus) {
              const backendAtk = atkStatus.active_attack || null;
              setActiveAttack(backendAtk);
              if (!backendAtk) {
                setAttackTarget(null);
              }
            }
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
            setAiPrediction(payload);
            setPredictionHistory((prev) => {
              const next = [...prev, payload];
              if (next.length > 50) next.shift();
              return next;
            });
          } else if (topic === "grid/ai_forecast_multi_bus") {
            setMultiBusForecast(payload);
          } else if (topic === "grid/ai_threat_forecast") {
            setThreatAwareForecast(payload);
          } else if (topic === "grid/physics_validation") {
            setPhysicsValidation(payload);
          } else if (topic === "grid/trust_scores") {
            setTrustScores(payload);
          } else if (topic === "grid/adaptive_filter") {
            setAdaptiveFilter(payload);
          }
        }
      } catch (err) {
        console.error("Failed to parse WebSocket message:", err);
      }
    };

    ws.onclose = () => {
      console.log("WebSocket disconnected. Retrying connection...");
      setConnected(false);
      reconnectTimeoutRef.current = setTimeout(connectWebSocket, 3000);
    };

    ws.onerror = (err) => {
      console.error("WebSocket encountered error:", err);
      ws.close();
    };
  };

  useEffect(() => {
    connectWebSocket();
    return () => {
      if (wsRef.current) wsRef.current.close();
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
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
    setThreatData(null);
    setAiPrediction(null);
    setPredictionHistory([]);
    setMultiBusForecast(null);
    setThreatAwareForecast(null);
    setPhysicsValidation(null);
    setTrustScores(null);
    setAdaptiveFilter(null);
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
            {aiPrediction ? (
              <span className={`font-bold text-sm tracking-wide font-scada-nums ${
                aiPrediction.predicted_threat >= 76.0 ? "text-red-500 animate-pulse scada-text-glow-red" :
                aiPrediction.predicted_threat >= 51.0 ? "text-orange-500" :
                aiPrediction.predicted_threat >= 26.0 ? "text-yellow-500 scada-text-glow-warning" :
                "text-scada-nominal scada-text-glow-green"
              }`}>
                {aiPrediction.predicted_threat.toFixed(0)}% ({aiPrediction.cascade_risk})
              </span>
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
          <div className="flex-1">
            <GridDiagram 
              telemetry={telemetry} 
              onToggleBreaker={toggleBreaker} 
              attackStatus={telemetry?.attack_status}
              flisrState={flisrState}
              flisrIsolated={flisrIsolated}
              flisrReconfigured={flisrReconfigured}
              flisrTripped={flisrTripped}
            />
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4 shrink-0">
            <TelemetryCharts history={history} />
            <ForecastPanel predictionHistory={predictionHistory} aiPrediction={aiPrediction} />
            <MultiBusForecastPanel forecastData={multiBusForecast} />
            <ThreatAwareForecastPanel forecastData={threatAwareForecast} />
            <PhysicsValidationPanel validationData={physicsValidation} />
            <TrustAnalysisPanel trustScores={trustScores} filterData={adaptiveFilter} />
          </div>
        </section>

        {/* Right column: Incident logs, Cyber attack injection console */}
        <section className="h-full flex flex-col justify-between gap-4 overflow-hidden">
          <ThreatScorePanel 
            threatData={threatData}
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
              {events
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
              {events.length === 0 && (
                <p className="text-scada-dimText italic">No logs recorded. Awaiting telemetry stream...</p>
              )}
            </div>
          </div>

          {/* Alerts and Attacks */}
          <div className="flex-shrink-0">
            <AlertsPanel
              events={events}
              alerts={alerts}
              flisrAuto={flisrAuto}
              flisrState={flisrState}
              flisrIsolated={flisrIsolated}
              flisrReconfigured={flisrReconfigured}
              flisrTripped={flisrTripped}
              onSendConfig={sendConfig}
              onSendAttack={sendAttack}
              onSendControl={handleResetAlarms}
              recording={recording}
              setRecording={setRecording}
              activeAttack={activeAttack}
              attackStatus={telemetry?.attack_status}
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
