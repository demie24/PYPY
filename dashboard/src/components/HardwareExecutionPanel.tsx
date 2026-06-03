import React, { useState } from "react";
import {
  Shield,
  AlertTriangle,
  Check,
  Lock,
  Unlock,
  AlertOctagon,
  Info
} from "lucide-react";

interface HardwareExecutionPanelProps {
  executionGateway: any;
  reliability: any;
  safetyGuard: any;
  telemetryValidation: any;
  onSendControl: (payload: any) => void;
}

export const HardwareExecutionPanel: React.FC<HardwareExecutionPanelProps> = ({
  executionGateway,
  reliability,
  safetyGuard,
  telemetryValidation,
  onSendControl
}) => {
  const [activeTab, setActiveTab] = useState<"safety" | "integrity" | "reliability" | "logs">("safety");
  const [selectedPort, setSelectedPort] = useState<string>("esp32");

  // Fallback defaults in case backend is bootstrapping/offline
  const estopActive = safetyGuard?.emergency_stop_active || false;
  const integrityScore = telemetryValidation?.telemetry_integrity_score !== undefined
    ? telemetryValidation.telemetry_integrity_score
    : 100.0;
  const integrityStatus = telemetryValidation?.status || "NOMINAL";
  const validationAlerts = telemetryValidation?.alerts || [];
  const safetyAlerts = safetyGuard?.alerts || [];
  const reliabilityScores = reliability?.reliability_scores || {};
  const lockoutStates = reliability?.lockout_states || {};
  const reliabilityAlerts = reliability?.alerts || [];
  const executionLog = executionGateway?.execution_log || [];
  const compromisedZones = executionGateway?.compromised_zones || [];

  const getIntegrityColor = (score: number) => {
    if (score >= 90.0) return "text-emerald-400";
    if (score >= 70.0) return "text-amber-400";
    return "text-red-400 animate-pulse font-bold";
  };

  const getIntegrityBgColor = (score: number) => {
    if (score >= 90.0) return "bg-emerald-500/10 border-emerald-500/30";
    if (score >= 70.0) return "bg-amber-500/10 border-amber-500/30";
    return "bg-red-500/10 border-red-500/30 animate-pulse";
  };

  const handleTriggerEstop = () => {
    onSendControl({
      command: "TRIGGER_EMERGENCY_STOP",
      target: "all",
      source: "SCADA_OPERATOR"
    });
  };

  const handleResetEstop = () => {
    onSendControl({
      command: "RESET_EMERGENCY_STOP",
      target: "all",
      source: "SCADA_OPERATOR"
    });
  };

  const handleQuarantine = () => {
    onSendControl({
      command: "QUARANTINE_PORT",
      target: "all",
      port: selectedPort
    });
  };

  const handleRelease = () => {
    onSendControl({
      command: "RELEASE_PORT",
      target: "all",
      port: selectedPort
    });
  };

  return (
    <div className="bg-scada-panel border border-scada-border rounded-lg p-3 h-[380px] flex flex-col justify-between overflow-hidden">
      {/* Header */}
      <div className="flex justify-between items-center mb-2 border-b border-scada-border/40 pb-1.5 shrink-0">
        <h2 className="text-xs font-bold tracking-wider text-scada-dimText uppercase flex items-center gap-1.5">
          <Shield size={14} className={estopActive ? "text-red-500 animate-pulse" : "text-emerald-400"} />
          Physical Execution & Edge Reliability (Phase 7.5)
        </h2>
        {/* Navigation Tabs */}
        <div className="flex bg-scada-bg/80 border border-scada-border/40 rounded p-0.5">
          <button
            onClick={() => setActiveTab("safety")}
            className={`px-2 py-0.5 rounded text-[9px] font-mono transition-colors ${
              activeTab === "safety"
                ? "bg-blue-500/20 border border-blue-500/40 text-blue-300 font-bold"
                : "text-scada-dimText hover:text-white"
            }`}
          >
            SAFETY & ESTOP
          </button>
          <button
            onClick={() => setActiveTab("integrity")}
            className={`px-2 py-0.5 rounded text-[9px] font-mono transition-colors ${
              activeTab === "integrity"
                ? "bg-blue-500/20 border border-blue-500/40 text-blue-300 font-bold"
                : "text-scada-dimText hover:text-white"
            }`}
          >
            INTEGRITY
          </button>
          <button
            onClick={() => setActiveTab("reliability")}
            className={`px-2 py-0.5 rounded text-[9px] font-mono transition-colors ${
              activeTab === "reliability"
                ? "bg-blue-500/20 border border-blue-500/40 text-blue-300 font-bold"
                : "text-scada-dimText hover:text-white"
            }`}
          >
            RELIABILITY
          </button>
          <button
            onClick={() => setActiveTab("logs")}
            className={`px-2 py-0.5 rounded text-[9px] font-mono transition-colors ${
              activeTab === "logs"
                ? "bg-blue-500/20 border border-blue-500/40 text-blue-300 font-bold"
                : "text-scada-dimText hover:text-white"
            }`}
          >
            EXECUTION QUEUE
          </button>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 overflow-hidden min-h-0 py-1">
        {/* Tab 1: Safety & Emergency Stop */}
        {activeTab === "safety" && (
          <div className="h-full flex gap-3">
            {/* E-Stop Status Card */}
            <div className={`w-1/2 rounded border p-3 flex flex-col justify-between ${getIntegrityBgColor(estopActive ? 0 : 100)}`}>
              <div className="flex flex-col items-center justify-center flex-1">
                <AlertOctagon size={48} className={estopActive ? "text-red-500 animate-bounce" : "text-emerald-500/30"} />
                <span className="text-[10px] font-mono text-scada-dimText uppercase mt-2">Emergency Shutdown System</span>
                <span className={`text-base font-bold font-mono tracking-wider mt-1 ${estopActive ? "text-red-400" : "text-emerald-400"}`}>
                  {estopActive ? "ACTIVE LOCKOUT" : "NOMINAL - STANDBY"}
                </span>
              </div>
              
              <div className="mt-2 shrink-0">
                {estopActive ? (
                  <button
                    onClick={handleResetEstop}
                    className="w-full bg-emerald-600/30 border border-emerald-500/50 hover:bg-emerald-600/50 text-emerald-300 rounded py-1.5 text-xs font-mono font-bold flex items-center justify-center gap-1.5 uppercase transition-colors"
                  >
                    <Unlock size={14} /> Reset Emergency Lockout
                  </button>
                ) : (
                  <button
                    onClick={handleTriggerEstop}
                    className="w-full bg-red-600/40 border border-red-500 hover:bg-red-600/60 text-red-200 rounded py-1.5 text-xs font-mono font-bold flex items-center justify-center gap-1.5 uppercase animate-pulse transition-all shadow-[0_0_15px_rgba(239,68,68,0.4)]"
                  >
                    <Lock size={14} /> TRIGGER EMERGENCY STOP
                  </button>
                )}
              </div>
            </div>

            {/* Interlock Logs */}
            <div className="w-1/2 flex flex-col justify-between">
              <span className="text-[9px] font-bold text-scada-dimText uppercase tracking-wider mb-1">
                Safety Interlock Alerts
              </span>
              <div className="flex-1 bg-black/20 border border-scada-border/30 rounded p-2 overflow-y-auto font-mono text-[8px] scrollbar-thin">
                {safetyAlerts.length === 0 ? (
                  <div className="h-full flex flex-col items-center justify-center text-scada-dimText/60">
                    <Check size={20} className="text-emerald-500/50 mb-1" />
                    <span>No interlock violations detected.</span>
                  </div>
                ) : (
                  <div className="flex flex-col gap-1.5">
                    {safetyAlerts.map((alert: string, idx: number) => (
                      <div key={idx} className="flex gap-1.5 bg-red-950/20 border border-red-950/40 rounded p-1.5 text-red-400">
                        <AlertTriangle size={12} className="shrink-0 mt-0.5" />
                        <span className="leading-normal">{alert}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Tab 2: Telemetry Integrity Gauge */}
        {activeTab === "integrity" && (
          <div className="h-full flex gap-3">
            {/* Integrity Meter */}
            <div className={`w-1/3 rounded border p-3 flex flex-col justify-between text-center ${getIntegrityBgColor(integrityScore)}`}>
              <span className="text-[8px] font-bold text-scada-dimText uppercase tracking-wider">
                Telemetry Sanity
              </span>
              <div className="flex flex-col items-center justify-center my-3">
                <span className={`text-4xl font-extrabold font-scada-nums leading-none tracking-tight ${getIntegrityColor(integrityScore)}`}>
                  {integrityScore.toFixed(0)}
                </span>
                <span className="text-[7px] text-scada-dimText font-mono uppercase mt-1">Integrity Index</span>
              </div>
              <div className="flex justify-between items-center text-[8px] font-mono border-t border-scada-border/20 pt-1.5 text-scada-dimText">
                <span>STATUS</span>
                <span className={getIntegrityColor(integrityScore)}>{integrityStatus}</span>
              </div>
            </div>

            {/* Validation Alerts */}
            <div className="w-2/3 flex flex-col justify-between">
              <span className="text-[9px] font-bold text-scada-dimText uppercase tracking-wider mb-1">
                Real-Time Sanity Logs (1Hz Audit)
              </span>
              <div className="flex-1 bg-black/20 border border-scada-border/30 rounded p-2 overflow-y-auto font-mono text-[8px] scrollbar-thin">
                {validationAlerts.length === 0 ? (
                  <div className="h-full flex flex-col items-center justify-center text-scada-dimText/60">
                    <Check size={20} className="text-emerald-500/50 mb-1" />
                    <span>All sensor signals comply with physics models.</span>
                  </div>
                ) : (
                  <div className="flex flex-col gap-1.5">
                    {validationAlerts.map((alert: string, idx: number) => (
                      <div key={idx} className="flex gap-1.5 bg-amber-950/20 border border-amber-950/40 rounded p-1.5 text-amber-400">
                        <AlertTriangle size={12} className="shrink-0 mt-0.5" />
                        <span className="leading-normal">{alert}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Tab 3: Edge Reliability Heatmap */}
        {activeTab === "reliability" && (
          <div className="h-full flex gap-3">
            {/* Reliability Grid */}
            <div className="w-3/5 flex flex-col justify-between">
              <span className="text-[9px] font-bold text-scada-dimText uppercase tracking-wider mb-1">
                ESP32 & PLC Fleet Diagnostics
              </span>
              <div className="grid grid-cols-2 gap-2 flex-1 overflow-y-auto scrollbar-thin">
                {Object.keys(reliabilityScores).length === 0 ? (
                  <div className="col-span-2 h-full flex items-center justify-center font-mono text-[9px] text-scada-dimText/60">
                    No active device telemetry.
                  </div>
                ) : (
                  Object.keys(reliabilityScores).map((device) => {
                    const score = reliabilityScores[device];
                    const isLocked = lockoutStates[device] || false;
                    
                    let scoreColor = "text-emerald-400";
                    let bg = "bg-emerald-500/10 border-emerald-500/25";
                    if (isLocked) {
                      scoreColor = "text-red-400 animate-pulse font-bold";
                      bg = "bg-red-500/10 border-red-500/30";
                    } else if (score < 0.6) {
                      scoreColor = "text-red-400";
                      bg = "bg-red-500/10 border-red-500/20";
                    } else if (score < 0.9) {
                      scoreColor = "text-amber-400";
                      bg = "bg-amber-500/10 border-amber-500/20";
                    }

                    return (
                      <div key={device} className={`rounded border p-1.5 flex justify-between items-center font-mono text-[8px] ${bg}`}>
                        <div className="flex flex-col truncate">
                          <span className="text-white font-bold truncate">{device.replace("_", " ")}</span>
                          <span className="text-scada-dimText uppercase scale-90 origin-left mt-0.5">
                            {isLocked ? "FLAPPING LOCKOUT" : "ONLINE"}
                          </span>
                        </div>
                        <span className={`text-[11px] font-scada-nums font-bold ${scoreColor}`}>
                          {((score ?? 1.0) * 100).toFixed(0)}%
                        </span>
                      </div>
                    );
                  })
                )}
              </div>
            </div>

            {/* Timeout Alerts */}
            <div className="w-2/5 flex flex-col justify-between border-l border-scada-border/20 pl-3">
              <span className="text-[9px] font-bold text-scada-dimText uppercase tracking-wider mb-1">
                Relay Feedback Failures
              </span>
              <div className="flex-1 bg-black/20 border border-scada-border/30 rounded p-2 overflow-y-auto font-mono text-[8px] scrollbar-thin">
                {reliabilityAlerts.length === 0 ? (
                  <div className="h-full flex flex-col items-center justify-center text-scada-dimText/60">
                    <Check size={20} className="text-emerald-500/50 mb-1" />
                    <span>No contact timeout flags.</span>
                  </div>
                ) : (
                  <div className="flex flex-col gap-1">
                    {reliabilityAlerts.map((alert: string, idx: number) => (
                      <div key={idx} className="bg-red-950/20 border border-red-950/40 rounded p-1 text-red-400 flex gap-1">
                        <AlertTriangle size={10} className="shrink-0 mt-0.5" />
                        <span className="leading-tight">{alert}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Tab 4: Execution Logs */}
        {activeTab === "logs" && (
          <div className="h-full flex gap-3">
            {/* Logs Table */}
            <div className="w-2/3 flex flex-col justify-between">
              <span className="text-[9px] font-bold text-scada-dimText uppercase tracking-wider mb-1">
                Execution Queue Logs
              </span>
              <div className="flex-1 bg-black/20 border border-scada-border/30 rounded overflow-hidden flex flex-col font-mono text-[8px]">
                <div className="grid grid-cols-12 gap-1 bg-scada-bg/80 border-b border-scada-border/40 p-1 font-bold text-scada-dimText text-[7px] shrink-0">
                  <div className="col-span-3">TIMESTAMP</div>
                  <div className="col-span-2">COMMAND</div>
                  <div className="col-span-2">TARGET</div>
                  <div className="col-span-3">SOURCE</div>
                  <div className="col-span-2 text-right">STATUS</div>
                </div>
                <div className="flex-1 overflow-y-auto p-1 flex flex-col gap-1.5 scrollbar-thin">
                  {executionLog.length === 0 ? (
                    <div className="h-full flex items-center justify-center text-scada-dimText/60 text-[8px]">
                      No command logs registered.
                    </div>
                  ) : (
                    [...executionLog].reverse().map((entry: any, idx: number) => {
                      let color = "text-emerald-400";
                      if (entry.status === "BLOCKED") color = "text-red-400 font-bold";
                      else if (entry.status === "FAILED") color = "text-amber-400";

                      return (
                        <div key={idx} className="grid grid-cols-12 gap-1 border-b border-scada-border/10 pb-1 items-center">
                          <div className="col-span-3 text-scada-dimText font-scada-nums">
                            {new Date(entry.timestamp ?? Date.now()).toLocaleTimeString()}
                          </div>
                          <div className="col-span-2 text-white font-medium">{entry.command}</div>
                          <div className="col-span-2 text-blue-400 font-semibold">{entry.target}</div>
                          <div className="col-span-3 text-scada-dimText truncate">{entry.source}</div>
                          <div className={`col-span-2 text-right font-bold ${color}`}>{entry.status}</div>
                        </div>
                      );
                    })
                  )}
                </div>
              </div>
            </div>

            {/* Quarantine & Mappings */}
            <div className="w-1/3 flex flex-col justify-between border-l border-scada-border/20 pl-3">
              <span className="text-[9px] font-bold text-scada-dimText uppercase tracking-wider mb-1">
                Port Quarantine Control
              </span>
              <div className="bg-scada-bg/60 border border-scada-border/40 rounded p-2 flex-1 flex flex-col justify-between mb-1.5">
                <div className="flex flex-col gap-1.5">
                  <span className="text-[7.5px] text-scada-dimText uppercase font-mono">Select Interface Port</span>
                  <select
                    value={selectedPort}
                    onChange={(e) => setSelectedPort(e.target.value)}
                    className="bg-black/40 border border-scada-border/60 rounded text-[9px] p-1 text-white focus:outline-none focus:border-blue-500 font-mono w-full"
                  >
                    <option value="esp32">ESP32 Fleet Bus</option>
                    <option value="plc">PLC Ethernet Port</option>
                    <option value="esp32_zone1">ESP32 Zone 1</option>
                    <option value="esp32_zone2">ESP32 Zone 2</option>
                    <option value="esp32_zone3">ESP32 Zone 3</option>
                    <option value="plc_primary">Modbus PLC Primary</option>
                  </select>
                </div>
                
                <div className="flex gap-2 mt-2">
                  <button
                    onClick={handleQuarantine}
                    className="flex-1 bg-red-700/20 border border-red-500/40 hover:bg-red-700/40 text-red-300 rounded py-1 text-[8px] font-mono font-bold uppercase transition-colors"
                  >
                    Quarantine
                  </button>
                  <button
                    onClick={handleRelease}
                    className="flex-1 bg-emerald-700/20 border border-emerald-500/40 hover:bg-emerald-700/40 text-emerald-300 rounded py-1 text-[8px] font-mono font-bold uppercase transition-colors"
                  >
                    Release
                  </button>
                </div>
              </div>

              {/* Compromised Zones list */}
              <div className="shrink-0 bg-black/10 border border-scada-border/20 rounded p-1.5">
                <span className="text-[7.5px] font-bold text-scada-dimText uppercase tracking-wider block mb-1">
                  Active Quarantine List
                </span>
                <div className="flex flex-wrap gap-1 max-h-[60px] overflow-y-auto scrollbar-thin">
                  {compromisedZones.length === 0 ? (
                    <span className="text-[7.5px] text-emerald-400 font-mono">No active quarantines.</span>
                  ) : (
                    compromisedZones.map((zone: string, idx: number) => (
                      <span key={idx} className="bg-red-950/35 border border-red-500/30 text-red-400 rounded px-1 text-[7.5px] font-mono shrink-0 uppercase">
                        {zone}
                      </span>
                    ))
                  )}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="flex justify-between items-center border-t border-scada-border/20 pt-1.5 shrink-0 font-mono text-[7.5px] text-scada-dimText mt-1">
        <span className="uppercase font-semibold text-white">Proxy Gateway Interface</span>
        <span className="flex items-center gap-1">
          <Info size={9} /> Loop Check Rate: 1.0Hz
        </span>
      </div>
    </div>
  );
};
