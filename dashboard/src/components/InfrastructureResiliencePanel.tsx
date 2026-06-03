import React, { useState } from "react";
import {
  Shield,
  AlertTriangle,
  Check,
  RefreshCw,
  Play,
  Activity
} from "lucide-react";

interface InfrastructureResiliencePanelProps {
  resilience: any;
  disasterRecovery: any;
  redundancy: any;
  deploymentHardening: any;
  largeScaleSync: any;
  onSendControl: (payload: any) => void;
}

export const InfrastructureResiliencePanel: React.FC<InfrastructureResiliencePanelProps> = ({
  resilience,
  disasterRecovery,
  redundancy,
  deploymentHardening,
  largeScaleSync,
  onSendControl
}) => {
  const [activeTab, setActiveTab] = useState<"resilience" | "disaster" | "redundancy" | "sync" | "hardening">("resilience");
  const [selectedWorkflow, setSelectedWorkflow] = useState<string>("BLACKSTART_RESTORATION");

  // Fallbacks in case backend is offline/bootstrapping
  const survivabilityScore = resilience?.survivability_score !== undefined ? resilience.survivability_score : 100.0;
  const resilienceState = resilience?.resilience_state || "NOMINAL";
  const containmentActive = resilience?.containment_active || false;
  const escalationLevel = resilience?.escalation_level !== undefined ? resilience.escalation_level : 0;
  const resilienceAlerts = resilience?.alerts || [];

  const activeWorkflow = disasterRecovery?.active_workflow || null;
  const workflowStatus = disasterRecovery?.workflow_status || "IDLE";
  const restorationStage = disasterRecovery?.restoration_stage !== undefined ? disasterRecovery.restoration_stage : 0;
  const checkpoints = disasterRecovery?.recovery_checkpoints || [];
  const priorityList = disasterRecovery?.prioritized_infrastructure || [];

  const devicePairs = redundancy?.device_pairs || {};
  const redundancyHealth = redundancy?.redundancy_health || {};
  const failoverHistory = redundancy?.failover_history || [];
  const backupsSync = redundancy?.active_backups_synchronized || {};
  const redundantExecutionActive = redundancy?.redundant_execution_active || false;

  const complianceScore = deploymentHardening?.compliance_score !== undefined ? deploymentHardening.compliance_score : 100.0;
  const safetyStatus = deploymentHardening?.deployment_safety_status || "SECURE";
  const segmentationValid = deploymentHardening?.network_segmentation_valid !== undefined ? deploymentHardening.network_segmentation_valid : true;
  const readinessStatus = deploymentHardening?.readiness_status || "READINESS_VERIFIED";
  const complianceChecks = deploymentHardening?.checks || {};

  const syncStabilized = largeScaleSync?.sync_stabilized !== undefined ? largeScaleSync.sync_stabilized : true;
  const loadBalanceFactor = largeScaleSync?.load_balance_factor !== undefined ? largeScaleSync.load_balance_factor : 0.1;
  const congestionDetected = largeScaleSync?.congestion_detected || false;
  const zoneOffsets = largeScaleSync?.multi_zone_offsets || {};
  const syncInterval = largeScaleSync?.sync_interval_ms || 100.0;
  const recoveryAttempts = largeScaleSync?.recovery_attempts || 0;

  const handleStartRecovery = () => {
    onSendControl({
      command: "TRIGGER_DISASTER_RECOVERY",
      target: "all",
      workflow: selectedWorkflow
    });
  };

  const handleToggleRedundancy = () => {
    onSendControl({
      command: "TOGGLE_REDUNDANT_EXECUTION",
      target: "all",
      enabled: !redundantExecutionActive
    });
  };

  const handleToggleHardeningCheck = (check: string, currentState: boolean) => {
    onSendControl({
      command: "SET_HARDENING_CHECK",
      target: "all",
      check: check,
      state: !currentState
    });
  };

  const handleResetResilience = () => {
    onSendControl({
      command: "RESET_ALARMS",
      target: "all",
      source: "SCADA_OPERATOR"
    });
  };

  const getResilienceStateColor = (state: string) => {
    switch (state) {
      case "NOMINAL": return "text-emerald-400";
      case "DEGRADED": return "text-amber-400";
      case "CRITICAL": return "text-orange-400";
      case "EMERGENCY": return "text-red-500 animate-pulse font-bold";
      default: return "text-scada-dimText";
    }
  };

  const getComplianceStatusColor = (status: string) => {
    switch (status) {
      case "SECURE": return "text-emerald-400";
      case "WARNING": return "text-amber-400";
      case "INSECURE": return "text-red-500 animate-pulse font-bold";
      default: return "text-scada-dimText";
    }
  };

  return (
    <div className="bg-scada-panel border border-scada-border rounded-lg p-3 h-[380px] flex flex-col justify-between overflow-hidden">
      {/* Header */}
      <div className="flex justify-between items-center mb-2 border-b border-scada-border/40 pb-1.5 shrink-0">
        <h2 className="text-xs font-bold tracking-wider text-scada-dimText uppercase flex items-center gap-1.5">
          <Activity size={14} className={resilienceState === "EMERGENCY" ? "text-red-500 animate-pulse" : "text-emerald-400"} />
          Distributed Resilience & Deployment Hardening (Phase 7.6)
        </h2>
        {/* Navigation Tabs */}
        <div className="flex bg-scada-bg/80 border border-scada-border/40 rounded p-0.5">
          {["resilience", "disaster", "redundancy", "sync", "hardening"].map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab as any)}
              className={`px-1.5 py-0.5 rounded text-[9px] font-mono transition-colors capitalize ${
                activeTab === tab
                  ? "bg-scada-border/60 text-white font-bold"
                  : "text-scada-dimText hover:text-white"
              }`}
            >
              {tab === "resilience" ? "Overview" : tab}
            </button>
          ))}
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 overflow-y-auto pr-1 min-h-0 text-scada-text font-mono text-[11px] leading-relaxed">
        {/* Tab 1: Overview */}
        {activeTab === "resilience" && (
          <div className="space-y-2.5">
            <div className="grid grid-cols-2 gap-2">
              <div className="bg-scada-bg/50 border border-scada-border/30 rounded p-2 flex flex-col justify-between">
                <span className="text-[10px] text-scada-dimText">Survivability Score</span>
                <div className="flex items-baseline gap-1 mt-1">
                  <span className={`text-2xl font-bold tracking-tight ${survivabilityScore >= 70 ? "text-emerald-400" : "text-red-400 animate-pulse"}`}>
                    {(survivabilityScore ?? 100.0).toFixed(1)}%
                  </span>
                </div>
              </div>
              <div className="bg-scada-bg/50 border border-scada-border/30 rounded p-2 flex flex-col justify-between">
                <span className="text-[10px] text-scada-dimText">Resilience State</span>
                <div className="flex items-center gap-1.5 mt-1">
                  <span className={`text-[13px] font-bold ${getResilienceStateColor(resilienceState)}`}>
                    {resilienceState}
                  </span>
                  {containmentActive && (
                    <span className="bg-red-950/80 border border-red-500/50 text-red-400 text-[8px] px-1 py-0.2 rounded animate-pulse">
                      CONTAINMENT
                    </span>
                  )}
                </div>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div className="bg-scada-bg/50 border border-scada-border/30 rounded p-2">
                <span className="text-[10px] text-scada-dimText block mb-1">Escalation Status</span>
                <div className="flex gap-1.5 mt-0.5">
                  {[0, 1, 2, 3].map((lvl) => (
                    <div
                      key={lvl}
                      className={`h-2 flex-1 rounded border ${
                        escalationLevel >= lvl
                          ? lvl === 3 ? "bg-red-500 border-red-400" : lvl === 2 ? "bg-orange-500 border-orange-400" : "bg-amber-500 border-amber-400"
                          : "bg-scada-bg/85 border-scada-border/30"
                      }`}
                      title={`Escalation Level ${lvl}`}
                    />
                  ))}
                </div>
                <span className="text-[9px] text-scada-dimText block mt-1 text-right">Level {escalationLevel} Active</span>
              </div>
              <div className="bg-scada-bg/50 border border-scada-border/30 rounded p-2 flex flex-col justify-between">
                <span className="text-[10px] text-scada-dimText">Security Readiness</span>
                <span className={`text-[12px] font-bold ${safetyStatus === "SECURE" ? "text-emerald-400" : "text-red-400 animate-pulse"}`}>
                  {readinessStatus}
                </span>
              </div>
            </div>

            {/* Resilience Alerts List */}
            <div className="border border-scada-border/20 rounded bg-scada-bg/30 p-1.5 max-h-[105px] overflow-y-auto">
              <span className="text-[9px] text-scada-dimText font-bold block mb-1 uppercase tracking-wider">Active Resilience Logs</span>
              {resilienceAlerts.length === 0 ? (
                <div className="text-[10px] text-scada-dimText italic py-2 text-center flex items-center justify-center gap-1">
                  <Check size={12} className="text-emerald-400" />
                  All resilience metrics within nominal bounds
                </div>
              ) : (
                <div className="space-y-1">
                  {resilienceAlerts.map((alert: string, idx: number) => (
                    <div key={idx} className="flex gap-1 items-start text-[10px] border-b border-scada-border/10 pb-0.5 last:border-0">
                      <AlertTriangle size={11} className="text-amber-400 shrink-0 mt-0.5" />
                      <span className="text-scada-text">{alert}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Tab 2: Disaster Recovery */}
        {activeTab === "disaster" && (
          <div className="space-y-2.5">
            <div className="flex gap-2 items-center">
              <div className="flex-1 bg-scada-bg/60 border border-scada-border/40 rounded p-1 flex items-center justify-between">
                <span className="text-[10px] text-scada-dimText uppercase pl-1">Workflow Target:</span>
                <select
                  value={selectedWorkflow}
                  onChange={(e) => setSelectedWorkflow(e.target.value)}
                  disabled={activeWorkflow !== null}
                  className="bg-scada-bg text-scada-text border border-scada-border/50 text-[10px] rounded px-1.5 py-0.5 outline-none font-mono"
                >
                  <option value="BLACKSTART_RESTORATION">Blackstart Recovery</option>
                  <option value="SYSTEM_RESET_RECOVERY">System Reset Recovery</option>
                </select>
              </div>
              <button
                onClick={handleStartRecovery}
                disabled={activeWorkflow !== null}
                className="bg-emerald-600 hover:bg-emerald-500 disabled:bg-scada-border/40 disabled:text-scada-dimText text-white px-2.5 py-1.5 rounded text-[10px] flex items-center gap-1 transition-colors font-bold uppercase"
              >
                <Play size={11} />
                Trigger
              </button>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div className="bg-scada-bg/50 border border-scada-border/30 rounded p-2 flex flex-col justify-between">
                <span className="text-[10px] text-scada-dimText">Recovery Status</span>
                <div className="flex items-center gap-1.5 mt-1">
                  <span className={`text-[12px] font-bold ${workflowStatus === "IN_PROGRESS" ? "text-amber-400 animate-pulse" : workflowStatus === "COMPLETED" ? "text-emerald-400" : workflowStatus === "ROLLING_BACK" ? "text-red-500 animate-pulse font-bold" : "text-scada-dimText"}`}>
                    {workflowStatus}
                  </span>
                </div>
              </div>
              <div className="bg-scada-bg/50 border border-scada-border/30 rounded p-2 flex flex-col justify-between">
                <span className="text-[10px] text-scada-dimText">Restoration Stage</span>
                <span className="text-[12px] text-scada-text mt-1">
                  {activeWorkflow ? `Stage ${restorationStage} / 3` : "IDLE (Stage 0)"}
                </span>
              </div>
            </div>

            {/* Checkpoints & Prioritized Infrastructure */}
            <div className="grid grid-cols-2 gap-2">
              <div className="border border-scada-border/20 rounded bg-scada-bg/30 p-1.5">
                <span className="text-[9px] text-scada-dimText font-bold block mb-1 uppercase">Active Checkpoints</span>
                {checkpoints.length === 0 ? (
                  <span className="text-[10px] text-scada-dimText italic">No saved checkpoints</span>
                ) : (
                  <div className="space-y-0.5 max-h-[80px] overflow-y-auto">
                    {checkpoints.map((cp: string, idx: number) => (
                      <div key={idx} className="text-[9px] text-scada-text flex items-center gap-1 border-b border-scada-border/10 pb-0.5">
                        <Shield size={9} className="text-emerald-400" />
                        <span className="truncate" title={cp}>{cp.split("_")[0]} ({cp.split("_").pop()})</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div className="border border-scada-border/20 rounded bg-scada-bg/30 p-1.5">
                <span className="text-[9px] text-scada-dimText font-bold block mb-1">RESTORATION PRIORITY</span>
                <div className="flex flex-wrap gap-1 max-h-[80px] overflow-y-auto">
                  {priorityList.slice(0, 6).map((node: string, idx: number) => (
                    <span
                      key={idx}
                      className={`text-[8px] px-1 py-0.2 rounded border ${
                        idx === 0
                          ? "bg-emerald-950/80 border-emerald-500/50 text-emerald-400 font-bold"
                          : "bg-scada-bg border-scada-border/30 text-scada-dimText"
                      }`}
                    >
                      {node}
                    </span>
                  ))}
                  {priorityList.length > 6 && (
                    <span className="text-[8px] text-scada-dimText self-center">+{priorityList.length - 6} more</span>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Tab 3: Redundancy & Failover */}
        {activeTab === "redundancy" && (
          <div className="space-y-2.5">
            <div className="flex justify-between items-center bg-scada-bg/60 border border-scada-border/40 rounded p-1.5">
              <span className="text-[10px] text-scada-dimText uppercase">Redundant routing Mode</span>
              <button
                onClick={handleToggleRedundancy}
                className={`px-3 py-1 rounded text-[10px] font-bold uppercase transition-colors ${
                  redundantExecutionActive
                    ? "bg-emerald-600 hover:bg-emerald-500 text-white"
                    : "bg-scada-border/40 text-scada-dimText hover:text-white"
                }`}
              >
                {redundantExecutionActive ? "ACTIVE" : "DISABLED"}
              </button>
            </div>

            {/* Device pairs mapping health list */}
            <div className="border border-scada-border/20 rounded bg-scada-bg/30 p-1.5">
              <span className="text-[9px] text-scada-dimText font-bold block mb-1 uppercase">Primary-Backup Redundancy Health</span>
              <div className="grid grid-cols-2 gap-2 max-h-[105px] overflow-y-auto">
                {Object.entries(devicePairs).map(([primary, backup]: [string, any], idx) => {
                  const health = redundancyHealth[primary] !== undefined ? redundancyHealth[primary] : 100.0;
                  const isSync = backupsSync[backup] !== undefined ? backupsSync[backup] : true;
                  return (
                    <div key={idx} className="bg-scada-bg/50 border border-scada-border/20 rounded p-1.5 flex flex-col justify-between">
                      <div className="flex justify-between items-start">
                        <span className="text-[9px] text-white font-bold">{primary.replace("esp32_", "Zone ").replace("plc_", "PLC ")}</span>
                        <span className={`text-[9px] font-bold ${health >= 80 ? "text-emerald-400" : "text-red-400"}`}>{(health ?? 100.0).toFixed(0)}%</span>
                      </div>
                      <div className="flex justify-between text-[8px] text-scada-dimText mt-1">
                        <span>Backup: {backup.replace("esp32_", "").replace("plc_", "")}</span>
                        <span className={isSync ? "text-emerald-400" : "text-amber-500"}>{isSync ? "SYNC" : "NO-SYNC"}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Failover Events history log */}
            <div className="border border-scada-border/20 rounded bg-scada-bg/30 p-1.5">
              <span className="text-[9px] text-scada-dimText font-bold block mb-1 uppercase">Failover Coordination Logs</span>
              {failoverHistory.length === 0 ? (
                <div className="text-[9px] text-scada-dimText italic py-1 text-center">No recent redundancy failovers</div>
              ) : (
                <div className="space-y-1 max-h-[70px] overflow-y-auto">
                  {failoverHistory.map((item: any, idx: number) => (
                    <div key={idx} className="text-[9px] text-scada-text border-b border-scada-border/10 pb-0.5 last:border-0 flex justify-between items-center">
                      <span className="text-emerald-400">⚡ {item.primary} &rarr; {item.backup}</span>
                      <span className="text-[8px] text-scada-dimText">FAILOVER_OK</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Tab 4: Clock Synchronization */}
        {activeTab === "sync" && (
          <div className="space-y-2.5">
            <div className="grid grid-cols-2 gap-2">
              <div className="bg-scada-bg/50 border border-scada-border/30 rounded p-2 flex flex-col justify-between">
                <span className="text-[10px] text-scada-dimText">Clock Sync Stabilization</span>
                <div className="flex items-center gap-1.5 mt-1">
                  <span className={`text-[12px] font-bold ${syncStabilized ? "text-emerald-400" : "text-red-400 animate-pulse font-bold"}`}>
                    {syncStabilized ? "STABILIZED" : "DRIFT_ALERT"}
                  </span>
                </div>
              </div>
              <div className="bg-scada-bg/50 border border-scada-border/30 rounded p-2 flex flex-col justify-between">
                <span className="text-[10px] text-scada-dimText">Dynamic Sync Interval</span>
                <span className="text-[12px] text-scada-text mt-1">
                  {(syncInterval ?? 1000.0).toFixed(0)} ms
                </span>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div className="bg-scada-bg/50 border border-scada-border/30 rounded p-2">
                <span className="text-[10px] text-scada-dimText block">Timing Congestion</span>
                <div className="flex items-baseline gap-1 mt-0.5">
                  <span className={`text-[12px] font-bold ${congestionDetected ? "text-red-500 animate-pulse" : "text-emerald-400"}`}>
                    {congestionDetected ? "CONGESTED" : "NOMINAL"}
                  </span>
                  <span className="text-[8px] text-scada-dimText">({((loadBalanceFactor ?? 0.0) * 100).toFixed(0)}% load)</span>
                </div>
              </div>
              <div className="bg-scada-bg/50 border border-scada-border/30 rounded p-2 flex flex-col justify-between">
                <span className="text-[10px] text-scada-dimText">Timing Recovery Loops</span>
                <span className="text-[12px] text-scada-text mt-1">
                  {recoveryAttempts} resets
                </span>
              </div>
            </div>

            {/* Zone Timing Offsets list */}
            <div className="border border-scada-border/20 rounded bg-scada-bg/30 p-1.5">
              <span className="text-[9px] text-scada-dimText font-bold block mb-1 uppercase">Multi-Zone Timing Coordination</span>
              <div className="grid grid-cols-4 gap-1.5">
                {Object.entries(zoneOffsets).map(([zone, offset]: [string, any], idx) => (
                  <div key={idx} className="bg-scada-bg/50 border border-scada-border/20 rounded p-1 text-center">
                    <span className="text-[8px] text-scada-dimText block truncate">{zone.replace("zone_", "Zone ").replace("plc_zone", "PLC")}</span>
                    <span className={`text-[10px] font-bold ${Math.abs(offset) > 15.0 ? "text-red-400 animate-pulse" : "text-emerald-400"}`}>
                      {(offset ?? 0.0).toFixed(1)}ms
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Tab 5: Hardening & Compliance */}
        {activeTab === "hardening" && (
          <div className="space-y-2">
            <div className="grid grid-cols-3 gap-2">
              <div className="bg-scada-bg/50 border border-scada-border/30 rounded p-1.5 flex flex-col justify-between text-center">
                <span className="text-[9px] text-scada-dimText">Hardening Score</span>
                <span className={`text-[13px] font-bold mt-0.5 ${complianceScore >= 90 ? "text-emerald-400" : complianceScore >= 70 ? "text-amber-400" : "text-red-400 animate-pulse"}`}>
                  {(complianceScore ?? 100.0).toFixed(0)}%
                </span>
              </div>
              <div className="bg-scada-bg/50 border border-scada-border/30 rounded p-1.5 flex flex-col justify-between text-center">
                <span className="text-[9px] text-scada-dimText">Segmentation</span>
                <span className={`text-[11px] font-bold mt-0.5 ${segmentationValid ? "text-emerald-400" : "text-red-400 animate-pulse"}`}>
                  {segmentationValid ? "VALID" : "UNSEGMENTED"}
                </span>
              </div>
              <div className="bg-scada-bg/50 border border-scada-border/30 rounded p-1.5 flex flex-col justify-between text-center">
                <span className="text-[9px] text-scada-dimText">Hardening Status</span>
                <span className={`text-[11px] font-bold mt-0.5 ${getComplianceStatusColor(safetyStatus)}`}>
                  {safetyStatus}
                </span>
              </div>
            </div>

            {/* Compliance checklists */}
            <div className="border border-scada-border/20 rounded bg-scada-bg/30 p-1.5">
              <span className="text-[9px] text-scada-dimText font-bold block mb-1 uppercase">Deployment Compliance Checklist</span>
              <div className="grid grid-cols-2 gap-1.5 max-h-[105px] overflow-y-auto">
                {Object.entries(complianceChecks).map(([check, state]: [string, any], idx) => (
                  <div
                    key={idx}
                    onClick={() => handleToggleHardeningCheck(check, state)}
                    className={`flex items-center gap-1.5 p-1 rounded border transition-colors cursor-pointer ${
                      state
                        ? "bg-emerald-950/20 border-emerald-500/30 text-emerald-400"
                        : "bg-red-950/20 border-red-500/30 text-red-400"
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={state}
                      readOnly
                      className="accent-emerald-500 pointer-events-none"
                    />
                    <span className="text-[8px] truncate" title={check}>{check.replace(/_/g, " ")}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Footer Controls */}
      <div className="flex justify-between items-center border-t border-scada-border/40 pt-1.5 mt-2 shrink-0">
        <span className="text-[9px] text-scada-dimText">Orchestration Coordination Panel</span>
        <button
          onClick={handleResetResilience}
          className="text-scada-dimText hover:text-white border border-scada-border hover:bg-scada-border/30 rounded px-2 py-0.5 text-[9px] transition-colors flex items-center gap-1 font-mono uppercase"
        >
          <RefreshCw size={9} />
          Reset Subsystems
        </button>
      </div>
    </div>
  );
};
