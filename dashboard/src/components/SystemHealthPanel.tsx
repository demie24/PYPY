import React from "react";
import { Activity, Clock, Server, Wifi, Database } from "lucide-react";

interface SystemHealthPanelProps {
  connected: boolean;
  wsLatency: number;
  reconnectCount: number;
  msgRate: number;
  aiOrchestrator: any;
  telemetry: any;
}

export const SystemHealthPanel: React.FC<SystemHealthPanelProps> = ({
  connected,
  wsLatency,
  reconnectCount,
  msgRate,
  aiOrchestrator,
  telemetry
}) => {
  // Static list of container services to display in the matrix
  const services = [
    { id: "mqtt", name: "Mosquitto Broker", status: connected ? "HEALTHY" : "OFFLINE", type: "INFRA" },
    { id: "gateway", name: "FastAPI Gateway", status: connected ? "HEALTHY" : "OFFLINE", type: "INFRA" },
    { id: "simulator", name: "Twin Simulator", status: telemetry ? "HEALTHY" : "OFFLINE", type: "PHYSICS" },
    { id: "protection", name: "FLISR / Relays", status: telemetry ? "HEALTHY" : "OFFLINE", type: "PHYSICS" },
    { id: "scorer", name: "Threat Engine", status: aiOrchestrator ? "HEALTHY" : "OFFLINE", type: "AI" },
    { id: "lstm_bus5", name: "LSTM Bus 5 Predictor", status: aiOrchestrator ? "HEALTHY" : "OFFLINE", type: "AI" },
    { id: "lstm_multi", name: "LSTM Multi-Bus", status: aiOrchestrator ? "HEALTHY" : "OFFLINE", type: "AI" },
    { id: "lstm_threat", name: "Threat-Aware LSTM", status: aiOrchestrator ? "HEALTHY" : "OFFLINE", type: "AI" }
  ];

  const getStatusColor = (status: string) => {
    if (status === "HEALTHY") return "bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.7)]";
    if (status === "DEGRADED") return "bg-amber-500 shadow-[0_0_8px_rgba(245,158,11,0.7)]";
    return "bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.7)] animate-pulse";
  };

  const getStatusTextColor = (status: string) => {
    if (status === "HEALTHY") return "text-emerald-400";
    if (status === "DEGRADED") return "text-amber-400";
    return "text-red-400 font-bold";
  };

  return (
    <div className="bg-scada-panel border border-scada-border rounded-lg p-3 h-[300px] flex flex-col justify-between overflow-hidden">
      {/* Header */}
      <div className="flex justify-between items-center mb-1.5 border-b border-scada-border/40 pb-1 shrink-0">
        <h2 className="text-xs font-bold tracking-wider text-scada-dimText uppercase flex items-center gap-1.5">
          <Activity size={14} className={connected ? "text-emerald-400 animate-pulse" : "text-gray-500"} />
          System Health Monitoring
        </h2>
        <div className="flex items-center gap-1 font-mono text-[8px] text-scada-dimText">
          <Clock size={8} />
          <span>Sys Diagnostics</span>
        </div>
      </div>

      {/* Main Stats Grid */}
      <div className="grid grid-cols-2 gap-2 mb-2 shrink-0 font-mono text-[9px]">
        <div className="bg-scada-bg/60 border border-scada-border/40 rounded p-1 flex items-center justify-between h-[42px]">
          <div className="flex items-center gap-1.5">
            <Wifi size={14} className="text-blue-400" />
            <div className="flex flex-col">
              <span className="text-[6.5px] text-scada-dimText uppercase">WS LATENCY</span>
              <span className="text-white font-bold font-scada-nums leading-none mt-0.5">
                {connected ? `${(wsLatency ?? 0).toFixed(0)} ms` : "OFFLINE"}
              </span>
            </div>
          </div>
        </div>
        <div className="bg-scada-bg/60 border border-scada-border/40 rounded p-1 flex items-center justify-between h-[42px]">
          <div className="flex items-center gap-1.5">
            <Database size={14} className="text-purple-400" />
            <div className="flex flex-col">
              <span className="text-[6.5px] text-scada-dimText uppercase">MQTT TELEM RATE</span>
              <span className="text-white font-bold font-scada-nums leading-none mt-0.5">
                {connected ? `${(msgRate ?? 0.0).toFixed(1)} Hz` : "0.0 Hz"}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Connection & Reconnect counters */}
      <div className="grid grid-cols-2 gap-2 mb-2 shrink-0 font-mono text-[8px] bg-scada-bg/40 border border-scada-border/20 rounded p-1">
        <div className="flex justify-between items-center text-scada-dimText px-1">
          <span>WS LINK</span>
          <span className={connected ? "text-emerald-400 font-bold" : "text-red-500 font-bold"}>
            {connected ? "CONNECTED" : "DISCONNECTED"}
          </span>
        </div>
        <div className="flex justify-between items-center text-scada-dimText px-1 border-l border-scada-border/30">
          <span>RECONNECTS</span>
          <span className="text-white font-bold font-scada-nums">{reconnectCount}</span>
        </div>
      </div>

      {/* Services Grid Title */}
      <div className="text-[8px] font-bold text-scada-dimText uppercase tracking-wider mb-1 shrink-0">
        Docker Service Matrix
      </div>

      {/* Visual Service Health Lights Grid */}
      <div className="flex-1 overflow-y-auto bg-black/15 border border-scada-border/30 rounded p-1.5 scrollbar-thin">
        <div className="grid grid-cols-2 gap-1.5">
          {services.map((svc) => (
            <div
              key={svc.id}
              className="bg-scada-bg/60 border border-scada-border/40 rounded p-1 flex items-center justify-between font-mono text-[8px]"
            >
              <div className="flex items-center gap-1.5 truncate">
                <span className={`w-2 h-2 rounded-full ${getStatusColor(svc.status)} shrink-0`}></span>
                <span className="text-white truncate font-medium">{svc.name}</span>
              </div>
              <span className={`text-[6.5px] uppercase scale-90 ${getStatusTextColor(svc.status)} shrink-0`}>
                {svc.status}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Footer Uptime Info */}
      <div className="flex justify-between items-center border-t border-scada-border/20 pt-1 shrink-0 font-mono text-[7px] text-scada-dimText mt-1">
        <span className="uppercase font-semibold">GRID TELEMETRY OK</span>
        <span className="flex items-center gap-1">
          <Server size={8} /> Node Status: ACTIVE
        </span>
      </div>
    </div>
  );
};
