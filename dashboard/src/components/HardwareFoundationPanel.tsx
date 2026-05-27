import React, { useState } from "react";
import {
  Cpu, Activity, Wifi, Thermometer, RefreshCw, Terminal, Sliders, AlertTriangle
} from "lucide-react";

interface DeviceInfo {
  name: string;
  status: string;
  latency_ms: number;
  trust: number;
  last_seen: number;
  type: string;
}

interface RelayState {
  coil: string;
  feedback: string;
  last_changed: number;
}

interface SensorData {
  timestamp: number;
  buses: Record<string, { voltage_pu: number; angle_rad: number; P_mw: number; Q_mvar: number }>;
  lines: Record<string, { current_pu: number; current_amp: number; temperature_c: number; capacity_pct: number }>;
  breakers: Record<string, string>;
}

interface DeviceHealthData {
  timestamp: number;
  devices: Record<string, DeviceInfo>;
}

interface RelayTelemetryData {
  timestamp: number;
  relays: Record<string, RelayState>;
}

interface GpioData {
  timestamp: number;
  gpio: Record<string, number>;
}

interface CommandLogData {
  timestamp: number;
  command: string;
  target: string;
  source: string;
  status: string;
  details: string;
  device?: string;
}

interface HardwareFoundationPanelProps {
  hardwareRelay: RelayTelemetryData | null;
  hardwareGpio: GpioData | null;
  hardwareSensor: SensorData | null;
  hardwareDeviceHealth: DeviceHealthData | null;
  hardwareCommandLog: CommandLogData | null;
  onSendControl: (payload: any) => void;
}

type ActiveTab = "devices" | "relays" | "sensors" | "logs" | "faults";

export const HardwareFoundationPanel: React.FC<HardwareFoundationPanelProps> = ({
  hardwareRelay,
  hardwareGpio,
  hardwareSensor,
  hardwareDeviceHealth,
  hardwareCommandLog,
  onSendControl
}) => {
  const [activeTab, setActiveTab] = useState<ActiveTab>("devices");
  const [commandLogs, setCommandLogs] = useState<CommandLogData[]>([]);

  // Accumulate command logs in state
  React.useEffect(() => {
    if (hardwareCommandLog) {
      setCommandLogs(prev => {
        // Prevent duplicate logs on same timestamp
        const exists = prev.some(log => log.timestamp === hardwareCommandLog.timestamp);
        if (exists) return prev;
        const next = [hardwareCommandLog, ...prev];
        return next.slice(0, 30); // Cap at 30 entries
      });
    }
  }, [hardwareCommandLog]);

  const devices = hardwareDeviceHealth?.devices || {};
  const relays = hardwareRelay?.relays || {};
  const gpio = hardwareGpio?.gpio || {};
  const sensors: SensorData = hardwareSensor || {
    timestamp: 0,
    buses: {},
    lines: {},
    breakers: {}
  };

  // Track active fault injections state based on client updates or local toggles
  const [faults, setFaults] = useState({
    esp32_comms: false,
    esp32_latency: false,
    plc_comms: false,
    plc_latency: false,
    sensor_noise: true,
    sensor_drift: false
  });

  const handleToggleFault = (device: string, type: string, currentState: boolean) => {
    const nextState = !currentState;
    
    // Update local state immediately for fast feedback
    const key = `${device}_${type}` as keyof typeof faults;
    setFaults(prev => ({ ...prev, [key]: nextState }));

    // Send control command
    onSendControl({
      command: "INJECT_HARDWARE_FAULT",
      device,
      type,
      state: nextState
    });
  };

  const handleResetAlarms = () => {
    setFaults({
      esp32_comms: false,
      esp32_latency: false,
      plc_comms: false,
      plc_latency: false,
      sensor_noise: true,
      sensor_drift: false
    });
    onSendControl({ command: "RESET_ALARMS" });
  };

  const getStatusColor = (status: string) => {
    return status === "ONLINE" ? "text-emerald-400 border-emerald-500/25 bg-emerald-500/10" : "text-rose-400 border-rose-500/25 bg-rose-500/10 animate-pulse scada-glow-red";
  };

  const getTrustColor = (trust: number) => {
    if (trust >= 0.8) return "text-emerald-400";
    if (trust >= 0.5) return "text-amber-400";
    return "text-rose-400 animate-pulse";
  };

  return (
    <div className="bg-scada-panel border border-scada-border rounded-lg p-3 h-[320px] flex flex-col justify-between overflow-hidden relative">
      
      {/* Header */}
      <div className="flex justify-between items-center mb-1.5 border-b border-scada-border/40 pb-1 shrink-0">
        <h2 className="text-xs font-bold tracking-wider text-scada-dimText uppercase flex items-center gap-1">
          <Cpu className="w-3.5 h-3.5 text-cyan-400" />
          Hardware Abstraction Foundation
        </h2>
        <div className="flex gap-1.5 items-center">
          <button 
            onClick={handleResetAlarms}
            className="px-1.5 py-0.5 text-[10px] uppercase font-mono tracking-tighter border border-cyan-500/30 rounded bg-cyan-950/20 text-cyan-400 hover:bg-cyan-500/20 active:scale-95 transition-all"
            title="Reset All Hardware Faults and Trust"
          >
            <RefreshCw className="w-2.5 h-2.5 inline mr-1" />
            Reset HAL
          </button>
          <div className="flex border border-scada-border rounded overflow-hidden">
            {(["devices", "relays", "sensors", "logs", "faults"] as ActiveTab[]).map(t => (
              <button
                key={t}
                onClick={() => setActiveTab(t)}
                className={`px-1.5 py-0.5 text-[9px] uppercase font-mono tracking-tight transition-colors border-r last:border-0 border-scada-border/40 ${
                  activeTab === t
                    ? "bg-cyan-500/25 text-cyan-300 font-bold"
                    : "text-scada-dimText hover:text-cyan-400 hover:bg-cyan-950/10"
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
        
        {/* Tab 1: Device Registry & Heartbeats */}
        {activeTab === "devices" && (
          <div className="grid grid-cols-2 gap-2 h-full">
            {Object.keys(devices).length === 0 ? (
              <div className="col-span-2 flex flex-col items-center justify-center text-scada-dimText py-8">
                <Activity className="w-6 h-6 animate-pulse text-scada-dimText mb-1" />
                <span>Waiting for hardware heartbeats...</span>
              </div>
            ) : (
              Object.entries(devices).map(([id, dev]) => (
                <div key={id} className="border border-scada-border/60 rounded bg-scada-cardBG p-2 flex flex-col justify-between">
                  <div className="flex justify-between items-start border-b border-scada-border/30 pb-1 mb-1">
                    <span className="font-bold text-cyan-300 text-xs">{dev.name}</span>
                    <span className={`text-[9px] px-1 border rounded ${getStatusColor(dev.status)}`}>
                      {dev.status}
                    </span>
                  </div>
                  <div className="grid grid-cols-2 gap-y-1 text-[10px] text-scada-dimText">
                    <span>Latency:</span>
                    <span className="text-right text-scada-text font-bold">
                      {dev.latency_ms >= 0 ? `${dev.latency_ms.toFixed(1)} ms` : "timeout"}
                    </span>
                    <span>Trust Index:</span>
                    <span className={`text-right font-bold ${getTrustColor(dev.trust)}`}>
                      {(dev.trust * 100).toFixed(0)}%
                    </span>
                    <span>Type:</span>
                    <span className="text-right text-scada-text uppercase text-[9px]">{dev.type}</span>
                  </div>
                  <div className="mt-1.5 border-t border-scada-border/30 pt-1 flex justify-between items-center text-[9px]">
                    <span className="text-scada-dimText">Heartbeat LED:</span>
                    <span className={`w-2 h-2 rounded-full ${
                      dev.status === "ONLINE" 
                        ? (dev.latency_ms > 200 ? "bg-amber-400 animate-ping" : "bg-emerald-400 animate-pulse") 
                        : "bg-rose-600"
                    }`} />
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {/* Tab 2: Relay Grid & GPIO Pins */}
        {activeTab === "relays" && (
          <div className="grid grid-cols-3 gap-1.5">
            {Object.keys(relays).length === 0 ? (
              <div className="col-span-3 text-center text-scada-dimText py-8">
                No active virtual relay telemetry.
              </div>
            ) : (
              Object.entries(relays).map(([rid, val]) => {
                const isMismatch = val.coil !== val.feedback;
                return (
                  <div 
                    key={rid} 
                    className={`border rounded p-1 text-[10px] ${
                      isMismatch 
                        ? "border-rose-500/50 bg-rose-950/15" 
                        : "border-scada-border bg-scada-cardBG"
                    }`}
                  >
                    <div className="flex justify-between items-center border-b border-scada-border/20 pb-0.5 mb-1">
                      <span className="font-bold text-cyan-400">{rid}</span>
                      {isMismatch && (
                        <span title="Feedback Mismatch!">
                          <AlertTriangle className="w-2.5 h-2.5 text-rose-400 animate-pulse" />
                        </span>
                      )}
                    </div>
                    <div className="grid grid-cols-2 gap-x-1">
                      <span className="text-scada-dimText text-[9px]">Coil:</span>
                      <span className={`text-right font-bold ${val.coil === "CLOSED" ? "text-emerald-400" : "text-rose-400"}`}>
                        {val.coil}
                      </span>
                      <span className="text-scada-dimText text-[9px]">Aux Contact:</span>
                      <span className={`text-right font-bold ${val.feedback === "CLOSED" ? "text-emerald-400" : "text-rose-400"}`}>
                        {val.feedback}
                      </span>
                      <span className="text-scada-dimText text-[8px]">GPIO:</span>
                      <span className="text-right text-scada-dimText text-[8px]">
                        {rid === "L1_4" ? `O:${gpio["pin_4"] ?? 0} I:${gpio["pin_21"] ?? 0}` :
                         rid === "L2_7" ? `O:${gpio["pin_5"] ?? 0} I:${gpio["pin_22"] ?? 0}` :
                         rid === "L3_9" ? `O:${gpio["pin_6"] ?? 0} I:${gpio["pin_23"] ?? 0}` :
                         rid === "L4_5" ? `O:${gpio["pin_12"] ?? 0} I:${gpio["pin_25"] ?? 0}` :
                         rid === "L4_9" ? `O:${gpio["pin_13"] ?? 0} I:${gpio["pin_26"] ?? 0}` :
                         rid === "L5_6" ? `O:${gpio["pin_14"] ?? 0} I:${gpio["pin_27"] ?? 0}` :
                         rid === "L6_7" ? `O:${gpio["pin_15"] ?? 0} I:${gpio["pin_32"] ?? 0}` :
                         rid === "L7_8" ? `O:${gpio["pin_16"] ?? 0} I:${gpio["pin_33"] ?? 0}` :
                         rid === "L8_9" ? `O:${gpio["pin_17"] ?? 0} I:${gpio["pin_34"] ?? 0}` : ""}
                      </span>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        )}

        {/* Tab 3: Sensor Telemetry & Noise */}
        {activeTab === "sensors" && (
          <div className="grid grid-cols-2 gap-2">
            <div>
              <div className="border-b border-scada-border/30 pb-0.5 mb-1 text-cyan-300 font-bold text-[10px] uppercase">
                Voltage Transmitters (PTs)
              </div>
              <div className="grid grid-cols-3 gap-1 text-[9px]">
                {Object.entries(sensors.buses || {}).map(([bid, bus]) => (
                  <div key={bid} className="border border-scada-border/30 rounded p-0.5 bg-scada-cardBG">
                    <span className="text-scada-dimText mr-1">{bid.replace("Bus_", "B")}</span>
                    <span className="text-scada-text font-bold">{bus.voltage_pu.toFixed(3)}</span>
                  </div>
                ))}
              </div>
            </div>
            <div>
              <div className="border-b border-scada-border/30 pb-0.5 mb-1 text-cyan-300 font-bold text-[10px] uppercase">
                CT & Temperature Sensors
              </div>
              <div className="space-y-1 text-[9px] max-h-[190px] overflow-y-auto">
                {Object.entries(sensors.lines || {}).map(([lid, line]) => (
                  <div key={lid} className="flex justify-between items-center border border-scada-border/30 rounded p-0.5 bg-scada-cardBG">
                    <span className="text-cyan-400 font-bold">{lid}</span>
                    <span className="text-scada-text">{line.current_pu.toFixed(2)} pu</span>
                    <span className="text-scada-dimText">|</span>
                    <span className="text-amber-400 flex items-center">
                      <Thermometer className="w-2.5 h-2.5 inline" />
                      {line.temperature_c.toFixed(0)}°C
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Tab 4: Command Router Dispatch Logs */}
        {activeTab === "logs" && (
          <div className="flex flex-col gap-1 pr-1.5 h-full">
            {commandLogs.length === 0 ? (
              <div className="text-center text-scada-dimText py-8 flex flex-col items-center">
                <Terminal className="w-5 h-5 text-scada-dimText mb-1" />
                <span>No hardware dispatches logged.</span>
              </div>
            ) : (
              commandLogs.map((log, index) => (
                <div key={index} className={`border p-1 rounded text-[9.5px] ${
                  log.status === "SUCCESS" 
                    ? "border-emerald-500/20 bg-emerald-500/5 text-emerald-300/90" 
                    : (log.status === "BLOCKED" ? "border-amber-500/20 bg-amber-500/5 text-amber-300/90" : "border-rose-500/20 bg-rose-500/5 text-rose-300/90")
                }`}>
                  <div className="flex justify-between items-center border-b border-scada-border/10 pb-0.5 mb-0.5 font-bold">
                    <span>{log.command} on {log.target}</span>
                    <span className="text-[8.5px] text-scada-dimText">
                      {new Date(log.timestamp).toLocaleTimeString()}
                    </span>
                  </div>
                  <div className="flex justify-between text-[8.5px]">
                    <span>Source: <strong className="text-cyan-400">{log.source}</strong></span>
                    <span>Device: <strong>{log.device || "NONE"}</strong></span>
                    <span>Status: <strong className={log.status === "SUCCESS" ? "text-emerald-400" : "text-rose-400"}>{log.status}</strong></span>
                  </div>
                  <div className="text-[8.5px] text-scada-dimText italic mt-0.5">
                    Detail: {log.details}
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {/* Tab 5: Hardware Fault Injections */}
        {activeTab === "faults" && (
          <div className="grid grid-cols-2 gap-3 p-1">
            <div className="border border-scada-border/50 rounded p-2 bg-scada-cardBG">
              <div className="border-b border-scada-border/20 pb-1 mb-2 font-bold text-cyan-400 flex items-center gap-1">
                <Wifi className="w-3 h-3 text-cyan-400" />
                ESP32 (Substations 1-6)
              </div>
              <div className="space-y-2">
                <div className="flex justify-between items-center">
                  <span className="text-[10px] text-scada-dimText">Comms Failure (DoS):</span>
                  <button 
                    onClick={() => handleToggleFault("esp32", "comms_failure", faults.esp32_comms)}
                    className={`px-2 py-0.5 text-[9px] uppercase font-bold border rounded transition-colors ${
                      faults.esp32_comms 
                        ? "bg-rose-500/30 border-rose-500 text-rose-400 animate-pulse" 
                        : "bg-scada-panel border-scada-border text-scada-dimText hover:border-rose-500/50 hover:text-rose-400"
                    }`}
                  >
                    {faults.esp32_comms ? "Active (Offline)" : "Inject"}
                  </button>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-[10px] text-scada-dimText">Latency Ping Spike:</span>
                  <button 
                    onClick={() => handleToggleFault("esp32", "latency_spike", faults.esp32_latency)}
                    className={`px-2 py-0.5 text-[9px] uppercase font-bold border rounded transition-colors ${
                      faults.esp32_latency 
                        ? "bg-amber-500/30 border-amber-500 text-amber-400" 
                        : "bg-scada-panel border-scada-border text-scada-dimText hover:border-amber-500/50 hover:text-amber-400"
                    }`}
                  >
                    {faults.esp32_latency ? "Active (>300ms)" : "Inject"}
                  </button>
                </div>
              </div>
            </div>
            
            <div className="border border-scada-border/50 rounded p-2 bg-scada-cardBG">
              <div className="border-b border-scada-border/20 pb-1 mb-2 font-bold text-cyan-400 flex items-center gap-1">
                <Sliders className="w-3 h-3 text-cyan-400" />
                PLC (Substations 7-9)
              </div>
              <div className="space-y-2">
                <div className="flex justify-between items-center">
                  <span className="text-[10px] text-scada-dimText">Comms Failure (DoS):</span>
                  <button 
                    onClick={() => handleToggleFault("plc", "comms_failure", faults.plc_comms)}
                    className={`px-2 py-0.5 text-[9px] uppercase font-bold border rounded transition-colors ${
                      faults.plc_comms 
                        ? "bg-rose-500/30 border-rose-500 text-rose-400 animate-pulse" 
                        : "bg-scada-panel border-scada-border text-scada-dimText hover:border-rose-500/50 hover:text-rose-400"
                    }`}
                  >
                    {faults.plc_comms ? "Active (Offline)" : "Inject"}
                  </button>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-[10px] text-scada-dimText">Latency Ping Spike:</span>
                  <button 
                    onClick={() => handleToggleFault("plc", "latency_spike", faults.plc_latency)}
                    className={`px-2 py-0.5 text-[9px] uppercase font-bold border rounded transition-colors ${
                      faults.plc_latency 
                        ? "bg-amber-500/30 border-amber-500 text-amber-400" 
                        : "bg-scada-panel border-scada-border text-scada-dimText hover:border-amber-500/50 hover:text-amber-400"
                    }`}
                  >
                    {faults.plc_latency ? "Active (>400ms)" : "Inject"}
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

      </div>
      
      {/* Footer info */}
      <div className="border-t border-scada-border/30 pt-1.5 flex justify-between items-center text-[9px] text-scada-dimText shrink-0">
        <span>MQTT Topics: hardware/#</span>
        <span className="animate-pulse flex items-center gap-1">
          <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
          HAL Sync Active
        </span>
      </div>

    </div>
  );
};
