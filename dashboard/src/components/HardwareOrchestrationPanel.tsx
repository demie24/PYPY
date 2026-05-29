import React, { useState } from "react";
import {
  Cpu, ListOrdered, AlertTriangle, Shield
} from "lucide-react";

interface FleetDevice {
  name: string;
  status: string;
  latency_ms: number;
  trust: number;
  role: string;
}

interface EdgeDevicesData {
  timestamp: number;
  fleet: Record<string, FleetDevice>;
  failover_routes: Record<string, string>;
  average_trust: number;
}

interface ActivePlan {
  plan_id: string;
  status: string;
  progress: string;
  error: string;
}

interface PlanLog {
  timestamp: number;
  plan_id: string;
  status: string;
  steps_count: number;
  completed_count: number;
  error: string;
}

interface RelayExecutionData {
  timestamp: number;
  active_plans: ActivePlan[];
  history: PlanLog[];
}

interface PendingTx {
  tx_id: string;
  target: string;
  status: string;
  retries: number;
}

interface TxHistoryLog {
  timestamp: number;
  tx_id: string;
  target: string;
  command: string;
  breaker: string;
  status: string;
  retries: number;
  duration_ms: number;
  error: string;
}

interface DistributedBusData {
  timestamp: number;
  bus_load_pct: number;
  transmitted_count: number;
  dropped_count: number;
  retry_count: number;
  pending_queue_size: number;
  pending: PendingTx[];
  history: TxHistoryLog[];
}

interface SynchronizationData {
  timestamp: number;
  tick_counter: number;
  device_drifts: Record<string, number>;
  failover_alignment: Record<string, boolean>;
  synchronization_status: string;
}

interface ConflictLog {
  timestamp: number;
  breaker: string;
  proposed_source: string;
  proposed_priority: number;
  retaining_source: string;
  retaining_priority: number;
  action: string;
}

interface ConflictsData {
  timestamp: number;
  conflicts: ConflictLog[];
}

interface OrchestrationData {
  timestamp: number;
  active_locks: Record<string, { source: string; priority: number }>;
  orchestrator_status: string;
  active_plans_count: number;
}

interface HardwareOrchestrationPanelProps {
  hardwareOrchestration: OrchestrationData | null;
  hardwareEdgeDevices: EdgeDevicesData | null;
  hardwareRelayExecution: RelayExecutionData | null;
  hardwareDistributedBus: DistributedBusData | null;
  hardwareSynchronization: SynchronizationData | null;
  hardwareOrchestrationConflicts: ConflictsData | null;
  onSendControl: (payload: any) => void;
}

type ActiveTab = "fleet" | "execution" | "conflicts" | "comms";

export const HardwareOrchestrationPanel: React.FC<HardwareOrchestrationPanelProps> = ({
  hardwareOrchestration,
  hardwareEdgeDevices,
  hardwareRelayExecution,
  hardwareDistributedBus,
  hardwareSynchronization,
  hardwareOrchestrationConflicts,
  onSendControl
}) => {
  const [activeTab, setActiveTab] = useState<ActiveTab>("fleet");

  const formatTime = (ts: number) => {
    return new Date(ts).toLocaleTimeString();
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "ONLINE":
        return "text-emerald-400 border-emerald-500/25 bg-emerald-500/10";
      case "QUARANTINED":
        return "text-rose-400 border-rose-500/30 bg-rose-500/15 animate-pulse scada-glow-red";
      case "OFFLINE":
      default:
        return "text-rose-400 border-rose-500/25 bg-rose-500/10 border-dashed";
    }
  };

  const getPlanStatusColor = (status: string) => {
    switch (status) {
      case "COMPLETED":
        return "text-emerald-400";
      case "ROLLBACK":
        return "text-orange-400 animate-pulse";
      case "ROLLED_BACK":
        return "text-amber-400";
      case "ROLLBACK_FAILED":
        return "text-rose-400 font-bold animate-bounce";
      case "RUNNING":
        return "text-cyan-400 animate-pulse";
      default:
        return "text-scada-dimText";
    }
  };

  // Safe destructuring with fallback values
  const fleetMap = hardwareEdgeDevices?.fleet || {};
  const failoverRoutes = hardwareEdgeDevices?.failover_routes || {};
  const averageTrust = hardwareEdgeDevices?.average_trust || 1.0;
  
  const activePlans = hardwareRelayExecution?.active_plans || [];
  const planHistory = hardwareRelayExecution?.history || [];
  
  const conflictsList = hardwareOrchestrationConflicts?.conflicts || [];
  
  const busLoad = hardwareDistributedBus?.bus_load_pct || 0.0;
  const txCount = hardwareDistributedBus?.transmitted_count || 0;
  const dropCount = hardwareDistributedBus?.dropped_count || 0;
  const retryCount = hardwareDistributedBus?.retry_count || 0;
  const busHistory = hardwareDistributedBus?.history || [];
  
  const tickCounter = hardwareSynchronization?.tick_counter || 0;
  const deviceDrifts = hardwareSynchronization?.device_drifts || {};
  const failoverAlignment = hardwareSynchronization?.failover_alignment || {};
  const syncStatus = hardwareSynchronization?.synchronization_status || "SYNCHRONIZED";

  const activeLocks = hardwareOrchestration?.active_locks || {};
  const orchestratorStatus = hardwareOrchestration?.orchestrator_status || "NOMINAL";

  // Trigger manual NTP sync command
  const handleSyncClock = (devId: string) => {
    onSendControl({
      command: "INJECT_HARDWARE_FAULT",
      device: devId,
      type: "SYNC_CLOCK",
      state: false
    });
  };

  return (
    <div className="bg-scada-panel border border-scada-border rounded-lg p-3 h-[320px] flex flex-col justify-between overflow-hidden relative">
      
      {/* Header */}
      <div className="flex justify-between items-center mb-1.5 border-b border-scada-border/40 pb-1 shrink-0">
        <h2 className="text-xs font-bold tracking-wider text-scada-dimText uppercase flex items-center gap-1">
          <Cpu className="w-3.5 h-3.5 text-indigo-400" />
          Hardware Orchestration Panel (Phase 7.4)
        </h2>
        
        <div className="flex gap-1.5 items-center">
          <div className="flex border border-scada-border rounded overflow-hidden">
            {(["fleet", "execution", "conflicts", "comms"] as ActiveTab[]).map(t => (
              <button
                key={t}
                onClick={() => setActiveTab(t)}
                className={`px-1.5 py-0.5 text-[9px] uppercase font-mono tracking-tight transition-colors border-r last:border-0 border-scada-border/40 ${
                  activeTab === t
                    ? "bg-indigo-500/25 text-indigo-300 font-bold"
                    : "text-scada-dimText hover:text-indigo-400 hover:bg-indigo-950/10"
                }`}
              >
                {t}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto pr-1 text-[11px] font-mono text-scada-text min-h-0">
        
        {/* Tab 1: ESP32/PLC Fleet Map */}
        {activeTab === "fleet" && (
          <div className="flex flex-col gap-2 h-full">
            {/* Device Grid */}
            <div className="grid grid-cols-3 gap-1.5">
              {Object.entries(fleetMap).map(([id, dev]) => {
                const isStandby = dev.role === "STANDBY";
                return (
                  <div key={id} className={`border rounded p-1.5 ${isStandby ? "border-slate-700 bg-slate-900/40" : "border-scada-border/60 bg-scada-cardBG"} flex flex-col justify-between`}>
                    <div className="flex justify-between items-start border-b border-scada-border/10 pb-0.5 mb-1">
                      <span className={`font-bold text-[10px] ${isStandby ? "text-slate-400" : "text-indigo-300"}`}>
                        {id.replace("esp32_", "ESP-").replace("plc_", "PLC-")}
                      </span>
                      <span className={`text-[8px] px-1 border rounded ${getStatusBadge(dev.status)}`}>
                        {dev.status}
                      </span>
                    </div>
                    <div className="text-[9px] text-scada-dimText space-y-0.5">
                      <div className="flex justify-between">
                        <span>Role:</span>
                        <span className={isStandby ? "text-slate-400" : "text-indigo-400 font-bold"}>{dev.role}</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Trust:</span>
                        <span className={dev.trust < 0.5 ? "text-rose-400 animate-pulse font-bold" : "text-emerald-400"}>
                          {dev.trust.toFixed(2)}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span>Latency:</span>
                        <span className="text-scada-text">{dev.latency_ms > 0 ? `${dev.latency_ms.toFixed(0)}ms` : "N/A"}</span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
            
            {/* Failover Routing Timeline / Flow */}
            <div className="border border-scada-border/40 rounded p-1.5 bg-scada-cardBG flex-1 flex flex-col justify-between min-h-0">
              <div className="border-b border-scada-border/20 pb-0.5 mb-1 font-bold text-indigo-400 text-[10px] flex justify-between">
                <span>Active Routing & Failover Paths</span>
                <span className="text-[9px] text-scada-dimText">Fleet Trust: <strong className="text-emerald-400">{averageTrust.toFixed(2)}</strong></span>
              </div>
              <div className="flex-1 overflow-y-auto grid grid-cols-2 gap-x-2 gap-y-1 text-[9px] pr-1">
                {Object.keys(failoverRoutes).length === 0 ? (
                  <div className="col-span-2 text-center text-scada-dimText py-4">Generating failover table...</div>
                ) : (
                  Object.entries(failoverRoutes).map(([breaker, controller]) => {
                    const isFailover = controller.includes("backup") || controller.includes("plc_primary");
                    return (
                      <div key={breaker} className="flex justify-between items-center border-b border-scada-border/10 pb-0.5">
                        <span className="text-scada-text font-bold">{breaker}</span>
                        <span className="text-scada-dimText">&rarr;</span>
                        <span className={`px-1 rounded font-bold ${isFailover ? "bg-orange-500/20 text-orange-400 animate-pulse" : "bg-indigo-500/10 text-indigo-300"}`}>
                          {controller.replace("_primary", "").replace("_zone", " Z")} {isFailover && "(FAILOVER)"}
                        </span>
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          </div>
        )}

        {/* Tab 2: Relay Switching & Rollbacks */}
        {activeTab === "execution" && (
          <div className="grid grid-cols-2 gap-2 h-full">
            {/* Active plans */}
            <div className="border border-scada-border/40 rounded p-1.5 flex flex-col bg-scada-cardBG">
              <div className="border-b border-scada-border/20 pb-0.5 mb-1 font-bold text-indigo-400 text-[10px]">
                Active Switching Sequences
              </div>
              <div className="flex-1 overflow-y-auto space-y-1.5 pr-0.5">
                {activePlans.length === 0 ? (
                  <div className="text-center text-scada-dimText py-8 flex flex-col items-center justify-center">
                    <ListOrdered className="w-5 h-5 text-indigo-500/40 mb-1" />
                    <span>No switching sequences executing.</span>
                  </div>
                ) : (
                  activePlans.map(plan => (
                    <div key={plan.plan_id} className="border border-scada-border/30 rounded p-1.5 bg-scada-panel/40">
                      <div className="flex justify-between items-center border-b border-scada-border/10 pb-0.5 mb-1">
                        <span className="font-bold text-indigo-300">{plan.plan_id}</span>
                        <span className={`text-[9px] font-bold ${getPlanStatusColor(plan.status)}`}>
                          {plan.status}
                        </span>
                      </div>
                      <div className="flex justify-between text-[9px] text-scada-dimText">
                        <span>Progress:</span>
                        <span className="text-scada-text font-bold">{plan.progress} steps</span>
                      </div>
                      {plan.error && (
                        <div className="text-[8px] text-rose-400 mt-1 border-t border-rose-500/20 pt-0.5 overflow-hidden text-ellipsis whitespace-nowrap">
                          Error: {plan.error}
                        </div>
                      )}
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Historical logs */}
            <div className="border border-scada-border/40 rounded p-1.5 flex flex-col bg-scada-cardBG">
              <div className="border-b border-scada-border/20 pb-0.5 mb-1 font-bold text-indigo-400 text-[10px]">
                Switching Plan History
              </div>
              <div className="flex-1 overflow-y-auto space-y-1 text-[8.5px]">
                {planHistory.length === 0 ? (
                  <div className="text-center text-scada-dimText py-6">No historical records.</div>
                ) : (
                  planHistory.map((log, idx) => (
                    <div key={idx} className="border-b border-scada-border/10 pb-1 last:border-0">
                      <div className="flex justify-between text-scada-dimText">
                        <span>{formatTime(log.timestamp)}</span>
                        <span className={`font-bold ${getPlanStatusColor(log.status)}`}>
                          {log.status}
                        </span>
                      </div>
                      <div className="flex justify-between text-[9px] text-scada-text">
                        <span>{log.plan_id}</span>
                        <span>{log.completed_count}/{log.steps_count} steps</span>
                      </div>
                      {log.error && (
                        <p className="text-[8.5px] text-orange-400 italic">Rollback: {log.error}</p>
                      )}
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        )}

        {/* Tab 3: Arbitration & Conflicts */}
        {activeTab === "conflicts" && (
          <div className="flex flex-col gap-1.5 h-full">
            <div className="flex justify-between items-center border-b border-scada-border/30 pb-1 mb-0.5 text-indigo-300 font-bold text-[10px]">
              <span>Centralized Command Arbitration Console</span>
              <span className={`px-1 rounded text-[8px] font-bold ${orchestratorStatus === "CONFLICT_ALERT" ? "bg-rose-500/20 text-rose-400 animate-pulse" : "bg-emerald-500/20 text-emerald-400"}`}>
                Arbitrator: {orchestratorStatus}
              </span>
            </div>
            
            {/* Active Locks */}
            <div className="grid grid-cols-3 gap-1 bg-slate-950/20 border border-scada-border/20 rounded p-1 mb-1 shrink-0">
              <span className="col-span-3 text-[9px] text-scada-dimText font-bold">Active Breaker Locks:</span>
              {Object.keys(activeLocks).length === 0 ? (
                <span className="col-span-3 text-[8.5px] text-slate-500 italic">No breakers locked.</span>
              ) : (
                Object.entries(activeLocks).map(([breaker, lock]) => (
                  <div key={breaker} className="border border-indigo-500/20 rounded px-1 py-0.5 bg-indigo-950/5 text-[8.5px] flex justify-between items-center">
                    <span className="font-bold text-indigo-300">{breaker}</span>
                    <span className="text-slate-400 text-[8px]">P{lock.priority}</span>
                  </div>
                ))
              )}
            </div>
            
            <div className="flex-1 overflow-y-auto space-y-1.5 pr-0.5 min-h-0">
              {conflictsList.length === 0 ? (
                <div className="text-center text-scada-dimText py-8 flex flex-col items-center justify-center">
                  <Shield className="w-5 h-5 text-emerald-500/40 mb-1" />
                  <span>No command collisions or priority blocks logged.</span>
                </div>
              ) : (
                [...conflictsList].reverse().map((c, idx) => (
                  <div key={idx} className="border border-scada-border/40 rounded p-1.5 bg-scada-panel/40 text-[9px]">
                    <div className="flex justify-between items-center border-b border-scada-border/10 pb-0.5 mb-1">
                      <span className="font-bold text-rose-400 flex items-center gap-0.5">
                        <AlertTriangle className="w-2.5 h-2.5 animate-pulse" /> COLLISION: {c.breaker}
                      </span>
                      <span className="text-[7.5px] px-1 rounded bg-rose-500/25 text-rose-300 border border-rose-500/20 font-bold">
                        {c.action}
                      </span>
                    </div>
                    <div className="text-scada-dimText leading-normal">
                      Proposed by <strong className="text-scada-text">{c.proposed_source} (P{c.proposed_priority})</strong> rejected; breaker retained by <strong className="text-indigo-300">{c.retaining_source} (P{c.retaining_priority})</strong>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        {/* Tab 4: Comms, Retries, Sync & Drift */}
        {activeTab === "comms" && (
          <div className="grid grid-cols-2 gap-2 h-full">
            {/* Bus Metrics */}
            <div className="border border-scada-border/40 rounded p-1.5 flex flex-col bg-scada-cardBG">
              <div className="border-b border-scada-border/20 pb-0.5 mb-1 font-bold text-indigo-400 text-[10px] flex justify-between items-center">
                <span>Distributed Command Bus</span>
                <span className={`w-2 h-2 rounded-full ${busLoad > 30.0 ? "bg-orange-500 animate-pulse" : "bg-emerald-400 animate-pulse"}`} />
              </div>
              <div className="flex-1 overflow-y-auto space-y-1 text-[9.5px] text-scada-dimText">
                <div className="flex justify-between">
                  <span>Bus Load:</span>
                  <span className="text-scada-text font-bold">{busLoad.toFixed(1)}%</span>
                </div>
                <div className="flex justify-between">
                  <span>Tx Packets:</span>
                  <span className="text-scada-text font-bold">{txCount}</span>
                </div>
                <div className="flex justify-between">
                  <span>Dropped Packets:</span>
                  <span className={`font-bold ${dropCount > 0 ? "text-rose-400" : "text-emerald-400"}`}>{dropCount}</span>
                </div>
                <div className="flex justify-between">
                  <span>Active Retries:</span>
                  <span className={`font-bold ${retryCount > 0 ? "text-orange-400 animate-pulse" : "text-emerald-400"}`}>{retryCount}</span>
                </div>
                <div className="border-t border-scada-border/10 pt-1 mt-1 flex-1 flex flex-col min-h-0">
                  <span className="font-bold text-[8.5px] text-indigo-400 block mb-0.5">Recent Bus Transmissions:</span>
                  <div className="flex-1 overflow-y-auto space-y-0.5 pr-0.5">
                    {busHistory.length === 0 ? (
                      <span className="text-[8.5px] text-slate-500 italic">No transmissions logged.</span>
                    ) : (
                      busHistory.slice(0, 8).map((tx, idx) => (
                        <div key={idx} className="flex justify-between text-[8px] text-scada-text border-b border-scada-border/5 pb-0.5">
                          <span className="truncate max-w-[65px] font-bold text-scada-dimText">{tx.breaker || "CMD"}</span>
                          <span className={tx.status === "ACKED" ? "text-emerald-400" : "text-rose-400"}>{tx.status}</span>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </div>
            </div>

            {/* Drift / Sync engine */}
            <div className="border border-scada-border/40 rounded p-1.5 flex flex-col bg-scada-cardBG">
              <div className="border-b border-scada-border/20 pb-0.5 mb-1 font-bold text-indigo-400 text-[10px] flex justify-between items-center">
                <span>Clock Sync (PTP Protocol)</span>
                <span className={`text-[8px] px-1 rounded font-bold ${syncStatus === "SYNCHRONIZED" ? "bg-emerald-500/25 text-emerald-400" : "bg-orange-500/25 text-orange-400 animate-pulse"}`}>
                  {syncStatus}
                </span>
              </div>
              <div className="flex-1 overflow-y-auto space-y-1 text-[9px] pr-1">
                <div className="flex justify-between border-b border-scada-border/10 pb-0.5 text-scada-dimText">
                  <span>Virtual Tick:</span>
                  <span className="text-scada-text font-bold">#{tickCounter}</span>
                </div>
                {Object.entries(deviceDrifts).map(([devId, drift]) => {
                  const alignmentOk = failoverAlignment[devId] !== false;
                  return (
                    <div key={devId} className={`flex items-center justify-between border-b border-scada-border/10 pb-0.5 last:border-0 ${alignmentOk ? "" : "border-rose-500/20 text-rose-300 bg-rose-500/5 px-0.5 rounded"}`}>
                      <span className="text-indigo-300 font-bold truncate max-w-[70px]">
                        {devId.replace("esp32_", "ESP-").replace("plc_", "PLC-")}
                      </span>
                      <span className={`text-[8px] font-bold ${drift > 2.0 ? "text-orange-400" : "text-emerald-400"}`}>
                        +{drift.toFixed(2)}ms
                      </span>
                      <button
                        onClick={() => handleSyncClock(devId)}
                        className="px-1 bg-indigo-500/25 border border-indigo-500/30 rounded text-[7px] text-indigo-300 hover:bg-indigo-500/40 active:scale-95 transition-all uppercase"
                        title="Force sync clock drift"
                      >
                        Sync
                      </button>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}

      </div>
      
      {/* Footer Info */}
      <div className="border-t border-scada-border/30 pt-1.5 flex justify-between items-center text-[9px] text-scada-dimText shrink-0">
        <span>Central Arbitration Loop: Active</span>
        <span className="animate-pulse flex items-center gap-1 font-bold text-indigo-400">
          <span className="w-1.5 h-1.5 rounded-full bg-indigo-500" />
          Orchestration Enabled
        </span>
      </div>

    </div>
  );
};
