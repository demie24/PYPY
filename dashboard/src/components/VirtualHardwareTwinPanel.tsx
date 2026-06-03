import React, { useState } from "react";
import {
  Activity, ShieldAlert, Wifi, Zap, RefreshCw, Sliders, Play, AlertCircle, Radio, Network
} from "lucide-react";


interface HardwareDeviceDetails {
  timestamp: number;
  is_connected: boolean;
  packet_drop_rate: number;
  heartbeat_failure: boolean;
  reconnect_time_left: number;
  latency_spike?: boolean;
  comms_failure?: boolean;
  write_delay?: number;
  modbus_exception_rate?: number;
  queued_commands_count?: number;
}

interface VirtualDevicesData {
  timestamp: number;
  esp32: HardwareDeviceDetails;
  plc: HardwareDeviceDetails;
}

interface RelayFaultsData {
  timestamp: number;
  stuck: string[];
  welded: string[];
  desynced: string[];
  oscillating: string[];
  corrupted: string[];
}

interface SpoofedTelemetryData {
  timestamp: number;
  spoofed_sensors: Record<string, number>;
  corrupted_sensors: Record<string, string>;
  fake_feedbacks: Record<string, string>;
}

interface AnomalyEvent {
  timestamp: number;
  source: string;
  event_type: string;
  details: string;
  severity: string;
  target: string;
}

interface FaultPropagationPath {
  source: string;
  compromised: boolean;
  vector: string;
  affected_nodes: string[];
  propagation_stage: string;
}

interface FaultPropagationData {
  timestamp: number;
  severity_score: number;
  propagation_paths: FaultPropagationPath[];
  scenario: string;
}

interface VirtualHardwareTwinPanelProps {
  hardwareVirtualDevices: VirtualDevicesData | null;
  hardwareRelayFaults: RelayFaultsData | null;
  hardwareSpoofedTelemetry: SpoofedTelemetryData | null;
  hardwareAnomalies: AnomalyEvent[] | null;
  hardwareFaultPropagation: FaultPropagationData | null;
  onSendControl: (payload: any) => void;
}

type ActiveTab = "devices" | "relays" | "sensors" | "propagation" | "scenarios";

export const VirtualHardwareTwinPanel: React.FC<VirtualHardwareTwinPanelProps> = ({
  hardwareVirtualDevices,
  hardwareRelayFaults,
  hardwareSpoofedTelemetry,
  hardwareAnomalies,
  hardwareFaultPropagation,
  onSendControl
}) => {
  const [activeTab, setActiveTab] = useState<ActiveTab>("devices");

  // Format timestamp helper
  const formatTime = (ts: number) => {
    return new Date(ts).toLocaleTimeString();
  };

  const getStatusColor = (status: string | boolean) => {
    const isOnline = typeof status === "string" ? status === "ONLINE" : status;
    return isOnline 
      ? "text-emerald-400 border-emerald-500/25 bg-emerald-500/10" 
      : "text-rose-400 border-rose-500/25 bg-rose-500/10 animate-pulse scada-glow-red";
  };

  const getSeverityBadgeClass = (severity: string) => {
    switch (severity) {
      case "CRITICAL":
        return "text-rose-400 border-rose-500/30 bg-rose-500/10 animate-pulse";
      case "HIGH":
        return "text-orange-400 border-orange-500/30 bg-orange-500/10";
      case "WARNING":
        return "text-amber-400 border-amber-500/30 bg-amber-500/10";
      default:
        return "text-cyan-400 border-cyan-500/30 bg-cyan-500/10";
    }
  };

  // Launch a pre-defined hardware fault scenario
  const handleLaunchScenario = (scenario: string) => {
    onSendControl({
      command: "LAUNCH_HARDWARE_SCENARIO",
      scenario
    });
  };

  // Clear all faults
  const handleClearFaults = () => {
    onSendControl({
      command: "TERMINATE_HARDWARE_SCENARIO"
    });
  };

  // Extract variables safely with nominal fallbacks
  const espDetails: HardwareDeviceDetails = hardwareVirtualDevices?.esp32 || {
    timestamp: Date.now(),
    is_connected: true,
    packet_drop_rate: 0,
    heartbeat_failure: false,
    reconnect_time_left: 0,
    latency_spike: false
  };

  const plcDetails: HardwareDeviceDetails = hardwareVirtualDevices?.plc || {
    timestamp: Date.now(),
    is_connected: true,
    packet_drop_rate: 0,
    heartbeat_failure: false,
    write_delay: 0,
    modbus_exception_rate: 0,
    queued_commands_count: 0,
    reconnect_time_left: 0
  };

  const activeWelded = hardwareRelayFaults?.welded || [];
  const activeStuck = hardwareRelayFaults?.stuck || [];
  const activeDesynced = hardwareRelayFaults?.desynced || [];
  const activeOscillating = hardwareRelayFaults?.oscillating || [];

  const spoofedSensors = hardwareSpoofedTelemetry?.spoofed_sensors || {};
  const corruptedSensors = hardwareSpoofedTelemetry?.corrupted_sensors || {};
  const fakeFeedbacks = hardwareSpoofedTelemetry?.fake_feedbacks || {};

  const anomaliesList = hardwareAnomalies || [];
  const severityScore = hardwareFaultPropagation?.severity_score || 0.0;
  const propagationPaths = hardwareFaultPropagation?.propagation_paths || [];
  const activeScenario = hardwareFaultPropagation?.scenario || "NONE";

  return (
    <div className="bg-scada-panel border border-scada-border rounded-lg p-3 h-[320px] flex flex-col justify-between overflow-hidden relative">
      
      {/* Header */}
      <div className="flex justify-between items-center mb-1.5 border-b border-scada-border/40 pb-1 shrink-0">
        <h2 className="text-xs font-bold tracking-wider text-scada-dimText uppercase flex items-center gap-1">
          <Network className="w-3.5 h-3.5 text-orange-400" />
          Virtual Hardware Twin Simulator
        </h2>
        <div className="flex gap-1.5 items-center">
          <button 
            onClick={handleClearFaults}
            className="px-1.5 py-0.5 text-[9px] uppercase font-mono tracking-tighter border border-rose-500/30 rounded bg-rose-950/20 text-rose-400 hover:bg-rose-500/20 active:scale-95 transition-all"
            title="Clear All Active Faults and Scenarios"
          >
            <RefreshCw className="w-2 inline mr-1" />
            Clear Faults
          </button>
          <div className="flex border border-scada-border rounded overflow-hidden">
            {(["devices", "relays", "sensors", "propagation", "scenarios"] as ActiveTab[]).map(t => (
              <button
                key={t}
                onClick={() => setActiveTab(t)}
                className={`px-1.5 py-0.5 text-[9px] uppercase font-mono tracking-tight transition-colors border-r last:border-0 border-scada-border/40 ${
                  activeTab === t
                    ? "bg-orange-500/25 text-orange-300 font-bold"
                    : "text-scada-dimText hover:text-orange-400 hover:bg-orange-950/10"
                }`}
              >
                {t}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 overflow-y-auto pr-1 text-[11px] font-mono text-scada-text min-h-0">
        
        {/* Tab 1: Virtual Devices Status */}
        {activeTab === "devices" && (
          <div className="grid grid-cols-2 gap-2 h-full">
            {/* ESP32 Device Card */}
            <div className="border border-scada-border/60 rounded bg-scada-cardBG p-2 flex flex-col justify-between">
              <div className="flex justify-between items-start border-b border-scada-border/30 pb-1 mb-1">
                <span className="font-bold text-cyan-300 text-xs">Virtual ESP32</span>
                <span className={`text-[9px] px-1 border rounded ${getStatusColor(espDetails.is_connected)}`}>
                  {espDetails.is_connected ? "CONNECTED" : "OFFLINE"}
                </span>
              </div>
              <div className="space-y-1 text-[10px] text-scada-dimText">
                <div className="flex justify-between">
                  <span>Packet Drop Rate:</span>
                  <span className={`font-bold ${(espDetails.packet_drop_rate ?? 0) > 0 ? "text-orange-400" : "text-scada-text"}`}>
                    {((espDetails.packet_drop_rate ?? 0) * 100).toFixed(0)}%
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>Latency Spike:</span>
                  <span className={espDetails.latency_spike ? "text-orange-400 font-bold animate-pulse" : "text-emerald-400"}>
                    {espDetails.latency_spike ? "ACTIVE (>300ms)" : "NOMINAL"}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>Heartbeat Error:</span>
                  <span className={espDetails.heartbeat_failure ? "text-rose-400 font-bold animate-pulse" : "text-emerald-400"}>
                    {espDetails.heartbeat_failure ? "FAILING" : "OK"}
                  </span>
                </div>
                {(espDetails.reconnect_time_left ?? 0) > 0 && (
                  <div className="flex justify-between text-cyan-400 animate-pulse text-[9px]">
                    <span>Reconnecting in:</span>
                    <span>{(espDetails.reconnect_time_left ?? 0).toFixed(1)}s</span>
                  </div>
                )}
              </div>
              <div className="mt-1.5 border-t border-scada-border/30 pt-1 flex justify-between items-center text-[9px] text-scada-dimText">
                <span>Substations: 1-6</span>
                <span className={`w-2 h-2 rounded-full ${espDetails.is_connected ? "bg-emerald-400 animate-pulse" : "bg-rose-500 animate-ping"}`} />
              </div>
            </div>

            {/* PLC Device Card */}
            <div className="border border-scada-border/60 rounded bg-scada-cardBG p-2 flex flex-col justify-between">
              <div className="flex justify-between items-start border-b border-scada-border/30 pb-1 mb-1">
                <span className="font-bold text-cyan-300 text-xs">Virtual Modbus PLC</span>
                <span className={`text-[9px] px-1 border rounded ${getStatusColor(plcDetails.is_connected)}`}>
                  {plcDetails.is_connected ? "CONNECTED" : "OFFLINE"}
                </span>
              </div>
              <div className="space-y-1 text-[10px] text-scada-dimText">
                <div className="flex justify-between">
                  <span>Modbus Exception:</span>
                  <span className={`font-bold ${plcDetails.modbus_exception_rate && (plcDetails.modbus_exception_rate ?? 0) > 0 ? "text-orange-400" : "text-scada-text"}`}>
                    {plcDetails.modbus_exception_rate ? ((plcDetails.modbus_exception_rate ?? 0) * 100).toFixed(0) : 0}%
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>Command Delay:</span>
                  <span className={`font-bold ${plcDetails.write_delay && (plcDetails.write_delay ?? 0) > 0 ? "text-orange-400 animate-pulse" : "text-scada-text"}`}>
                    {plcDetails.write_delay ? (plcDetails.write_delay ?? 0).toFixed(1) : 0}s
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>Queued Commands:</span>
                  <span className={`font-bold ${plcDetails.queued_commands_count && (plcDetails.queued_commands_count ?? 0) > 0 ? "text-amber-400 animate-pulse" : "text-scada-text"}`}>
                    {plcDetails.queued_commands_count || 0}
                  </span>
                </div>
                {(plcDetails.reconnect_time_left ?? 0) > 0 && (
                  <div className="flex justify-between text-cyan-400 animate-pulse text-[9px]">
                    <span>Reconnecting in:</span>
                    <span>{(plcDetails.reconnect_time_left ?? 0).toFixed(1)}s</span>
                  </div>
                )}
              </div>
              <div className="mt-1.5 border-t border-scada-border/30 pt-1 flex justify-between items-center text-[9px] text-scada-dimText">
                <span>Substations: 7-9</span>
                <span className={`w-2 h-2 rounded-full ${plcDetails.is_connected ? "bg-emerald-400 animate-pulse" : "bg-rose-500 animate-ping"}`} />
              </div>
            </div>
          </div>
        )}

        {/* Tab 2: Relay Fault Registry */}
        {activeTab === "relays" && (
          <div className="grid grid-cols-3 gap-1.5 h-full overflow-y-auto">
            {activeWelded.length === 0 && activeStuck.length === 0 && activeDesynced.length === 0 && activeOscillating.length === 0 ? (
              <div className="col-span-3 text-center text-scada-dimText py-8 flex flex-col items-center justify-center">
                <ShieldAlert className="w-5 h-5 text-emerald-500/60 mb-1" />
                <span>All virtual relays operating nominally.</span>
              </div>
            ) : (
              <>
                {/* Welded Relays */}
                {activeWelded.map(rid => (
                  <div key={`${rid}-w`} className="border border-rose-500/30 rounded p-1.5 bg-rose-950/10 flex flex-col justify-between">
                    <span className="font-bold text-rose-400 text-xs">{rid}</span>
                    <span className="text-[9px] text-rose-300 uppercase font-bold animate-pulse flex items-center gap-0.5">
                      <Zap className="w-2.5 h-2.5 inline" /> WELDED CLOSED
                    </span>
                  </div>
                ))}
                {/* Stuck Relays */}
                {activeStuck.map(rid => (
                  <div key={`${rid}-s`} className="border border-red-500/30 rounded p-1.5 bg-red-950/10 flex flex-col justify-between">
                    <span className="font-bold text-red-400 text-xs">{rid}</span>
                    <span className="text-[9px] text-red-300 uppercase font-bold flex items-center gap-0.5">
                      <AlertCircle className="w-2.5 h-2.5 inline" /> ACTUATOR STUCK
                    </span>
                  </div>
                ))}
                {/* Desynced Relays */}
                {activeDesynced.map(rid => (
                  <div key={`${rid}-d`} className="border border-orange-500/30 rounded p-1.5 bg-orange-950/10 flex flex-col justify-between">
                    <span className="font-bold text-orange-400 text-xs">{rid}</span>
                    <span className="text-[9px] text-orange-300 uppercase font-bold flex items-center gap-0.5">
                      <Sliders className="w-2.5 h-2.5 inline" /> DESYNCHRONIZED
                    </span>
                  </div>
                ))}
                {/* Oscillating Relays */}
                {activeOscillating.map(rid => (
                  <div key={`${rid}-o`} className="border border-amber-500/30 rounded p-1.5 bg-amber-950/10 flex flex-col justify-between">
                    <span className="font-bold text-amber-400 text-xs">{rid}</span>
                    <span className="text-[9px] text-amber-300 uppercase font-bold animate-bounce flex items-center gap-0.5">
                      <Activity className="w-2.5 h-2.5 inline" /> CHATTERING
                    </span>
                  </div>
                ))}
              </>
            )}
          </div>
        )}

        {/* Tab 3: Spoofed Sensors & Anomalies */}
        {activeTab === "sensors" && (
          <div className="grid grid-cols-2 gap-2 h-full">
            {/* Spoofed list */}
            <div className="border border-scada-border/40 rounded p-1.5 flex flex-col bg-scada-cardBG">
              <div className="border-b border-scada-border/20 pb-0.5 mb-1 font-bold text-cyan-400 text-[10px]">
                Active Telemetry Spoofs
              </div>
              <div className="flex-1 overflow-y-auto space-y-1 text-[9px]">
                {Object.keys(spoofedSensors).length === 0 && Object.keys(corruptedSensors).length === 0 && Object.keys(fakeFeedbacks).length === 0 ? (
                  <div className="text-center text-scada-dimText py-6">No sensor offsets active.</div>
                ) : (
                  <>
                    {Object.entries(spoofedSensors).map(([sid, val]) => (
                      <div key={sid} className="flex justify-between items-center text-orange-300">
                        <span>{sid}:</span>
                        <span>bias {val > 0 ? `+${val}` : val}</span>
                      </div>
                    ))}
                    {Object.entries(corruptedSensors).map(([sid, val]) => (
                      <div key={sid} className="flex justify-between items-center text-rose-400 font-bold">
                        <span>{sid}:</span>
                        <span>{val} CORRUPT</span>
                      </div>
                    ))}
                    {Object.entries(fakeFeedbacks).map(([bid, val]) => (
                      <div key={bid} className="flex justify-between items-center text-amber-400">
                        <span>Breaker {bid}:</span>
                        <span>force {val}</span>
                      </div>
                    ))}
                  </>
                )}
              </div>
            </div>

            {/* Scrollable anomalies list */}
            <div className="border border-scada-border/40 rounded p-1.5 flex flex-col bg-scada-cardBG">
              <div className="border-b border-scada-border/20 pb-0.5 mb-1 font-bold text-cyan-400 text-[10px] flex justify-between items-center">
                <span>Twin Anomalies Log</span>
                <span className={`px-1 rounded text-[9px] ${(severityScore ?? 0) >= 60 ? "bg-rose-500/25 text-rose-400 animate-pulse font-bold" : ((severityScore ?? 0) >= 30 ? "bg-amber-500/25 text-amber-400" : "bg-cyan-500/25 text-cyan-400")}`}>
                  Sev: {(severityScore ?? 0).toFixed(0)}
                </span>
              </div>
              <div className="flex-1 overflow-y-auto space-y-1 text-[8.5px]">
                {anomaliesList.length === 0 ? (
                  <div className="text-center text-scada-dimText py-6">No anomalies detected.</div>
                ) : (
                  [...anomaliesList].reverse().map((a, idx) => (
                    <div key={idx} className="border-b border-scada-border/10 pb-0.5 last:border-0">
                      <div className="flex justify-between text-scada-dimText">
                        <span>{formatTime(a.timestamp)}</span>
                        <span className={`px-0.5 rounded text-[8px] font-bold ${getSeverityBadgeClass(a.severity)}`}>
                          {a.event_type}
                        </span>
                      </div>
                      <p className="text-scada-text text-[9px] break-words">{a.details}</p>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        )}

        {/* Tab 4: Cyber-Physical Propagation Map */}
        {activeTab === "propagation" && (
          <div className="flex flex-col gap-1.5 h-full">
            <div className="flex justify-between items-center border-b border-scada-border/30 pb-1 mb-0.5 text-cyan-300 font-bold text-[10px]">
              <span>Attack Propagation Pathways</span>
              <span className="text-[9px] text-scada-dimText">Scenario: <strong className="text-orange-400">{activeScenario}</strong></span>
            </div>
            
            <div className="flex-1 overflow-y-auto space-y-1.5 pr-0.5">
              {propagationPaths.length === 0 ? (
                <div className="text-center text-scada-dimText py-8 flex flex-col items-center justify-center">
                  <Wifi className="w-5 h-5 text-emerald-500/50 mb-1" />
                  <span>No active compromise propagation vectors detected.</span>
                </div>
              ) : (
                propagationPaths.map((p, idx) => (
                  <div key={idx} className="border border-scada-border/40 rounded p-1.5 bg-scada-panel/40 text-[9.5px]">
                    <div className="flex justify-between items-center border-b border-scada-border/10 pb-0.5 mb-1 font-bold">
                      <span className="text-orange-400 uppercase flex items-center gap-0.5">
                        <Radio className="w-2.5 h-2.5 animate-pulse" /> {p.source} &rarr; {p.propagation_stage}
                      </span>
                      <span className="text-[8.5px] px-1 rounded bg-rose-500/20 text-rose-300 border border-rose-500/20">
                        {p.vector}
                      </span>
                    </div>
                    <div className="text-scada-dimText">
                      Impacted hardware nodes: <strong className="text-scada-text">{p.affected_nodes.join(", ")}</strong>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        {/* Tab 5: Predefined Fault Scenarios */}
        {activeTab === "scenarios" && (
          <div className="grid grid-cols-2 gap-2 p-0.5 h-full">
            <div className="border border-scada-border/50 rounded bg-scada-cardBG p-1.5 flex flex-col justify-between">
              <div>
                <span className="font-bold text-orange-400 text-[10.5px] flex items-center gap-0.5">
                  <Play className="w-2.5 h-2.5" /> DoS Propagation
                </span>
                <p className="text-[9px] text-scada-dimText mt-0.5">Jam substation heartbeats and trigger sensor drops.</p>
              </div>
              <button 
                onClick={() => handleLaunchScenario("dos_propagation")}
                className={`w-full py-0.5 text-[9px] uppercase font-bold border rounded transition-colors ${
                  activeScenario === "dos_propagation"
                    ? "bg-rose-500/30 border-rose-500 text-rose-400 animate-pulse"
                    : "bg-scada-panel border-scada-border text-scada-dimText hover:border-orange-500 hover:text-orange-300"
                }`}
              >
                {activeScenario === "dos_propagation" ? "Running" : "Launch"}
              </button>
            </div>

            <div className="border border-scada-border/50 rounded bg-scada-cardBG p-1.5 flex flex-col justify-between">
              <div>
                <span className="font-bold text-orange-400 text-[10.5px] flex items-center gap-0.5">
                  <Play className="w-2.5 h-2.5" /> Modbus Hijack
                </span>
                <p className="text-[9px] text-scada-dimText mt-0.5">Hijack PLC registers and weld breaker contact feedback.</p>
              </div>
              <button 
                onClick={() => handleLaunchScenario("plc_modbus_hijack")}
                className={`w-full py-0.5 text-[9px] uppercase font-bold border rounded transition-colors ${
                  activeScenario === "plc_modbus_hijack"
                    ? "bg-rose-500/30 border-rose-500 text-rose-400 animate-pulse"
                    : "bg-scada-panel border-scada-border text-scada-dimText hover:border-orange-500 hover:text-orange-300"
                }`}
              >
                {activeScenario === "plc_modbus_hijack" ? "Running" : "Launch"}
              </button>
            </div>

            <div className="border border-scada-border/50 rounded bg-scada-cardBG p-1.5 flex flex-col justify-between">
              <div>
                <span className="font-bold text-orange-400 text-[10.5px] flex items-center gap-0.5">
                  <Play className="w-2.5 h-2.5" /> Sensor Storm
                </span>
                <p className="text-[9px] text-scada-dimText mt-0.5">Inject voltage drift biases, NaNs, and current corruption.</p>
              </div>
              <button 
                onClick={() => handleLaunchScenario("sensor_corruption_storm")}
                className={`w-full py-0.5 text-[9px] uppercase font-bold border rounded transition-colors ${
                  activeScenario === "sensor_corruption_storm"
                    ? "bg-rose-500/30 border-rose-500 text-rose-400 animate-pulse"
                    : "bg-scada-panel border-scada-border text-scada-dimText hover:border-orange-500 hover:text-orange-300"
                }`}
              >
                {activeScenario === "sensor_corruption_storm" ? "Running" : "Launch"}
              </button>
            </div>

            <div className="border border-scada-border/50 rounded bg-scada-cardBG p-1.5 flex flex-col justify-between">
              <div>
                <span className="font-bold text-orange-400 text-[10.5px] flex items-center gap-0.5">
                  <Play className="w-2.5 h-2.5" /> Relay Welding
                </span>
                <p className="text-[9px] text-scada-dimText mt-0.5">Weld L4_5 CLOSED and stick L7_8 OPEN to lock out FLISR.</p>
              </div>
              <button 
                onClick={() => handleLaunchScenario("relay_welding_lockout")}
                className={`w-full py-0.5 text-[9px] uppercase font-bold border rounded transition-colors ${
                  activeScenario === "relay_welding_lockout"
                    ? "bg-rose-500/30 border-rose-500 text-rose-400 animate-pulse"
                    : "bg-scada-panel border-scada-border text-scada-dimText hover:border-orange-500 hover:text-orange-300"
                }`}
              >
                {activeScenario === "relay_welding_lockout" ? "Running" : "Launch"}
              </button>
            </div>
          </div>
        )}

      </div>
      
      {/* Footer Info */}
      <div className="border-t border-scada-border/30 pt-1.5 flex justify-between items-center text-[9px] text-scada-dimText shrink-0">
        <span>Hardware Twin: Mapped Substations 1-9</span>
        <span className="animate-pulse flex items-center gap-1 font-bold text-orange-400">
          <span className="w-1.5 h-1.5 rounded-full bg-orange-500" />
          Twin Connected
        </span>
      </div>

    </div>
  );
};
