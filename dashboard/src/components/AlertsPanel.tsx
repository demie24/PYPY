import React, { useState, useMemo } from "react";
import { Play, Square, ShieldAlert, RotateCcw, AlertTriangle, ShieldCheck, Clock, AlertCircle, CheckCircle2, Radio, Check, Folder } from "lucide-react";

interface AlertsPanelProps {
  events: any[];
  alerts: any[];
  flisrAuto: boolean;
  flisrState: string;
  flisrIsolated: string[];
  flisrReconfigured: string[];
  flisrTripped: string[];
  onSendConfig: (cfg: any) => void;
  onSendAttack: (attack: any) => void;
  onSendControl: (ctrl: any) => void;
  recording: boolean;
  setRecording: (rec: boolean) => void;
  activeAttack: string | null;
  attackStatus: any;
  annotations: Record<string, string>;
  onAddAnnotation: (key: string, note: string) => void;
}

export const AlertsPanel: React.FC<AlertsPanelProps> = ({
  events,
  alerts,
  flisrAuto,
  flisrState,
  flisrIsolated,
  flisrReconfigured,
  flisrTripped: _flisrTripped,
  onSendConfig,
  onSendAttack,
  onSendControl,
  recording,
  setRecording,
  activeAttack,
  attackStatus,
  annotations,
  onAddAnnotation
}) => {
  const [attackType, setAttackType] = useState<"FDIA" | "REPLAY">("FDIA");
  const [targetType, setTargetType] = useState<"bus" | "line">("bus");
  const [targetId, setTargetId] = useState<string>("Bus_5");
  const [bias, setBias] = useState<number>(-0.15);
  const [scale, setScale] = useState<number>(0.85);
  const [selectedScenario, setSelectedScenario] = useState<string>("coordinated_cascade");

  // Operator HMI state variables
  const [ackIds, setAckIds] = useState<Set<string>>(new Set());
  const [groupBy, setGroupBy] = useState<"none" | "node" | "severity">("none");
  const [currentTab, setCurrentTab] = useState<"all" | "escalated">("all");

  const attackRunning = activeAttack !== null;
  const isScenarioRunning = activeAttack === "SCENARIO";

  // Unique key helper for alerts
  const getAlertKey = (alert: any) => {
    return `${alert.timestamp}::${alert.type}::${alert.suspect_node ?? alert.type}`;
  };

  // --- Phase 5B: Alert deduplication logic ---
  // Collapse consecutive alerts from the same suspect_node within a 30s window
  // into a single entry with a repeat counter.
  const deduplicatedAlerts = useMemo(() => {
    const seen: Record<string, { alert: any; count: number; lastTs: number }> = {};
    const result: Array<any & { _count: number }> = [];
    for (const alert of alerts) {
      const key = `${alert.type}::${alert.suspect_node ?? alert.type}`;
      const existing = seen[key];
      if (existing && (alert.timestamp - existing.lastTs) < 30000 && existing.alert.severity === alert.severity) {
        existing.count += 1;
        existing.lastTs = alert.timestamp;
      } else {
        const entry = { ...alert, _count: 1 };
        seen[key] = { alert: entry, count: 1, lastTs: alert.timestamp };
        result.push(entry);
      }
    }
    // Sync counts back
    for (const entry of result) {
      const key = `${entry.type}::${entry.suspect_node ?? entry.type}`;
      entry._count = seen[key]?.count ?? 1;
    }

    // Prioritize by severity (CRITICAL > HIGH > WARNING) and then timestamp (newest first)
    const severityWeight = (severity: string) => {
      switch (severity) {
        case "CRITICAL": return 3;
        case "HIGH": return 2;
        case "WARNING": return 1;
        default: return 0;
      }
    };
    result.sort((a, b) => {
      const wA = severityWeight(a.severity);
      const wB = severityWeight(b.severity);
      if (wA !== wB) return wB - wA;
      return b.timestamp - a.timestamp;
    });

    return result;
  }, [alerts]);

  // Acknowledge single alert handler
  const toggleAckAlert = (alertKey: string) => {
    setAckIds(prev => {
      const next = new Set(prev);
      if (next.has(alertKey)) {
        next.delete(alertKey);
      } else {
        next.add(alertKey);
      }
      return next;
    });
  };

  // Acknowledge all alerts currently visible
  const handleAckAll = () => {
    const next = new Set(ackIds);
    deduplicatedAlerts.forEach(a => {
      next.add(getAlertKey(a));
    });
    setAckIds(next);
  };

  // Escalation Queue: CRITICAL & Unacknowledged for > 15s
  const nowTime = Date.now();
  const escalatedAlerts = useMemo(() => {
    return deduplicatedAlerts.filter(a => {
      const key = getAlertKey(a);
      const isAcked = ackIds.has(key);
      const isCritical = a.severity === "CRITICAL";
      const isOlderThan15s = (nowTime - a.timestamp) > 15000;
      return isCritical && !isAcked && isOlderThan15s;
    });
  }, [deduplicatedAlerts, ackIds, nowTime]);

  // Filter alerts based on active tab and acknowledgement
  const visibleAlerts = useMemo(() => {
    if (currentTab === "escalated") {
      return escalatedAlerts;
    }
    return deduplicatedAlerts;
  }, [deduplicatedAlerts, escalatedAlerts, currentTab]);

  // Severity counts (only counting unacknowledged ones to keep operator focused!)
  const unackedCounts = useMemo(() => {
    let crit = 0, high = 0, warn = 0;
    deduplicatedAlerts.forEach(a => {
      if (!ackIds.has(getAlertKey(a))) {
        if (a.severity === "CRITICAL") crit++;
        else if (a.severity === "HIGH") high++;
        else if (a.severity === "WARNING") warn++;
      }
    });
    return { CRITICAL: crit, HIGH: high, WARNING: warn };
  }, [deduplicatedAlerts, ackIds]);

  // Compromised node status
  const compromisedCount = Object.keys(attackStatus?.compromised_nodes ?? {}).length;
  const compromisedNames = Object.keys(attackStatus?.compromised_nodes ?? {});

  const startAttack = () => {
    onSendAttack({
      action: "START",
      type: attackType,
      config: {
        target: targetId,
        bias: parseFloat(bias.toString()),
        scale: parseFloat(scale.toString())
      }
    });
  };

  const startScenario = () => {
    onSendAttack({
      action: "START_SCENARIO",
      scenario_name: selectedScenario
    });
  };

  const stopAttack = () => {
    onSendAttack({
      action: "STOP"
    });
  };

  const toggleRecording = () => {
    if (recording) {
      onSendAttack({ action: "RECORD_STOP" });
      setRecording(false);
    } else {
      onSendAttack({ action: "RECORD_START" });
      setRecording(true);
    }
  };

  const handleTargetTypeChange = (type: "bus" | "line") => {
    setTargetType(type);
    setTargetId(type === "bus" ? "Bus_5" : "L5_6");
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 h-[350px]">
      {/* 1. Attack Injector OR Scenario Timeline Console */}
      <div className="bg-scada-panel border border-scada-border rounded-lg p-4 flex flex-col justify-between overflow-hidden">
        {isScenarioRunning ? (
          /* Live Scenario Timeline view */
          <div className="flex-1 flex flex-col justify-between overflow-hidden">
            <div className="overflow-hidden flex flex-col flex-1">
              <h2 className="text-sm font-semibold tracking-wider text-scada-trip uppercase mb-1.5 flex items-center gap-1.5 shrink-0 animate-pulse">
                <ShieldAlert size={16} />
                Scenario Engine Active
              </h2>
              
              <div className="bg-black/30 border border-scada-border/40 rounded p-1.5 px-2.5 flex justify-between items-center text-[10px] font-mono mb-2 shrink-0">
                <span className="text-scada-dimText">Scenario: <strong className="text-white uppercase">{attackStatus?.active_scenario_name?.replace("_", " ")}</strong></span>
                <span className="text-scada-trip font-bold flex items-center gap-1">
                  <Clock size={11} className="animate-spin" /> {typeof attackStatus?.scenario_time === "number" ? attackStatus.scenario_time.toFixed(0) : "0"}s
                </span>
              </div>

              {/* Steps timeline */}
              <div className="flex-1 overflow-y-auto space-y-1.5 pr-1 font-mono text-[10px]">
                {attackStatus?.stages?.map((stage: any, i: number) => {
                  const isActive = stage.status === "active";
                  return (
                    <div
                      key={i}
                      className={`p-1.5 rounded border transition-all duration-300 ${
                        isActive
                           ? "bg-red-500/10 border-red-500/30 text-white"
                           : "bg-scada-bg/50 border-scada-border/20 text-scada-dimText"
                      }`}
                    >
                      <div className="flex justify-between items-center font-bold text-[9px] mb-0.5">
                        <span className={isActive ? "text-scada-trip" : "text-gray-600"}>
                          STAGE {i + 1} (+{stage.time}s)
                        </span>
                        <span className={`px-1.5 rounded text-[8px] uppercase ${
                          isActive ? "bg-red-500/20 text-scada-trip animate-pulse" : "bg-gray-800 text-gray-500"
                        }`}>
                          {stage.status}
                        </span>
                      </div>
                      <p className="leading-tight font-sans text-xs">{stage.desc}</p>
                      {isActive && (
                        <div className="text-[8px] text-scada-trip mt-1 font-mono uppercase bg-black/35 px-1 py-0.5 rounded w-max">
                          Target: {stage.target} | Vector: {stage.type}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>

            <button
              onClick={stopAttack}
              className="mt-2 w-full bg-scada-nominal hover:bg-emerald-600 text-white font-semibold py-2 px-4 rounded text-xs flex items-center justify-center gap-1.5 transition-colors animate-pulse shrink-0"
            >
              <Square size={14} /> Terminate Scenario
            </button>
          </div>
        ) : (
          /* Normal Single Attack / Scenario Loader Controls */
          <div className="flex-1 flex flex-col justify-between overflow-hidden">
            <div className="overflow-y-auto pr-1 flex-1 space-y-3.5">
              <h2 className="text-sm font-semibold tracking-wider text-scada-dimText uppercase flex items-center gap-1.5 border-b border-scada-border/40 pb-1 shrink-0">
                <ShieldAlert size={16} className="text-scada-trip" />
                Attack Injection Vector
              </h2>
              
              <div className="space-y-3 text-xs">
                {/* Attack Type Selector */}
                <div className="grid grid-cols-2 gap-2">
                  <button
                    disabled={attackRunning}
                    onClick={() => setAttackType("FDIA")}
                    className={`py-1.5 px-3 rounded font-semibold text-center border transition-colors ${
                      attackType === "FDIA"
                        ? "bg-scada-trip/15 border-scada-trip text-scada-trip"
                        : "bg-scada-bg border-scada-border text-scada-dimText hover:text-white"
                    } ${attackRunning ? "opacity-50 cursor-not-allowed" : ""}`}
                  >
                    FDIA (False Data)
                  </button>
                  <button
                    disabled={attackRunning}
                    onClick={() => setAttackType("REPLAY")}
                    className={`py-1.5 px-3 rounded font-semibold text-center border transition-colors ${
                      attackType === "REPLAY"
                        ? "bg-scada-trip/15 border-scada-trip text-scada-trip"
                        : "bg-scada-bg border-scada-border text-scada-dimText hover:text-white"
                    } ${attackRunning ? "opacity-50 cursor-not-allowed" : ""}`}
                  >
                    Replay Attack
                  </button>
                </div>

                {attackType === "FDIA" ? (
                  <div className="space-y-2">
                    {/* Target Type Selector */}
                    <div className="flex gap-4 items-center">
                      <span className="text-scada-dimText">Target Type:</span>
                      <label className="flex items-center gap-1 cursor-pointer">
                        <input
                          type="radio"
                          disabled={attackRunning}
                          checked={targetType === "bus"}
                          onChange={() => handleTargetTypeChange("bus")}
                        />
                        Bus
                      </label>
                      <label className="flex items-center gap-1 cursor-pointer">
                        <input
                          type="radio"
                          disabled={attackRunning}
                          checked={targetType === "line"}
                          onChange={() => handleTargetTypeChange("line")}
                        />
                        Line
                      </label>
                    </div>

                    {/* Target Selection */}
                    <div className="flex justify-between items-center">
                      <span className="text-scada-dimText">Target ID:</span>
                      <select
                        value={targetId}
                        disabled={attackRunning}
                        onChange={(e) => setTargetId(e.target.value)}
                        className="bg-scada-bg border border-scada-border rounded px-2 py-1 text-white focus:outline-none disabled:opacity-50 text-[11px]"
                      >
                        {targetType === "bus"
                          ? Array.from({ length: 9 }, (_, i) => `Bus_${i + 1}`).map((b) => (
                              <option key={b} value={b}>{b.replace("_", " ")}</option>
                            ))
                          : ["L1_4", "L2_7", "L3_9", "L4_5", "L4_9", "L5_6", "L6_7", "L7_8", "L8_9"].map((l) => (
                              <option key={l} value={l}>LINE {l.replace("L", "").replace("_", "-")}</option>
                            ))}
                      </select>
                    </div>

                    {/* Bias Configuration */}
                    <div className="flex justify-between items-center">
                      <span className="text-scada-dimText">Bias Offset (p.u.):</span>
                      <input
                        type="number"
                        step="0.05"
                        disabled={attackRunning}
                        value={bias}
                        onChange={(e) => setBias(parseFloat(e.target.value))}
                        className="bg-scada-bg border border-scada-border rounded px-2 py-0.5 text-white w-16 text-right focus:outline-none disabled:opacity-50"
                      />
                    </div>

                    {/* Scale Configuration */}
                    <div className="flex justify-between items-center">
                      <span className="text-scada-dimText">Scaling Factor:</span>
                      <input
                        type="number"
                        step="0.05"
                        disabled={attackRunning}
                        value={scale}
                        onChange={(e) => setScale(parseFloat(e.target.value))}
                        className="bg-scada-bg border border-scada-border rounded px-2 py-0.5 text-white w-16 text-right focus:outline-none disabled:opacity-50"
                      />
                    </div>
                  </div>
                ) : (
                  <div className="space-y-2 py-1">
                    <p className="text-scada-dimText text-[10px] leading-relaxed">
                      Record clean grid state telemetry to the memory buffer, then replay it during normal operations to mask malicious outages.
                    </p>
                    <button
                      onClick={toggleRecording}
                      disabled={attackRunning}
                      className={`w-full py-1 rounded flex items-center justify-center gap-1 font-semibold text-[10px] border transition-colors ${
                        recording
                           ? "bg-red-500/10 border-red-500 text-red-400 animate-pulse"
                           : "bg-scada-bg border-scada-border text-scada-dimText hover:text-white"
                      } ${attackRunning ? "opacity-50 cursor-not-allowed" : ""}`}
                    >
                      {recording ? <Square size={10} /> : <Play size={10} />}
                      {recording ? "Stop Recording Buffer" : "Start Recording Buffer"}
                    </button>
                  </div>
                )}

                {/* Predefined Scenario Launcher dropdown */}
                <div className="border-t border-scada-border/40 pt-2">
                  <span className="text-[10px] font-bold text-scada-dimText uppercase tracking-wider block mb-1">Predefined Scenarios</span>
                  <div className="flex gap-2">
                    <select
                      value={selectedScenario}
                      disabled={attackRunning}
                      onChange={(e) => setSelectedScenario(e.target.value)}
                      className="flex-1 bg-scada-bg border border-scada-border rounded px-2 py-1 text-white focus:outline-none text-[11px] disabled:opacity-50"
                    >
                      <option value="coordinated_cascade">Coordinated Outage Cascade</option>
                      <option value="stealthy_fdia">Stealthy FDIA Sequence</option>
                      <option value="coordinated_cyber_physical">Cyber-Physical Jamming</option>
                    </select>
                    <button
                      disabled={attackRunning}
                      onClick={startScenario}
                      className="bg-red-950/20 border border-red-500/40 text-scada-trip hover:bg-red-900/30 px-3 py-1 rounded text-xs font-semibold disabled:opacity-50 transition-colors"
                    >
                      Launch
                    </button>
                  </div>
                </div>
              </div>
            </div>

            <div className="flex gap-2 mt-2">
              {!attackRunning ? (
                <button
                  onClick={startAttack}
                  className="flex-1 bg-scada-trip hover:bg-red-600 text-white font-semibold py-2 px-4 rounded text-xs flex items-center justify-center gap-1.5 transition-colors"
                >
                  <Play size={14} /> Inject Cyber Attack
                </button>
              ) : (
                <button
                  onClick={stopAttack}
                  className="flex-1 bg-scada-nominal hover:bg-emerald-600 text-white font-semibold py-2 px-4 rounded text-xs flex items-center justify-center gap-1.5 transition-colors animate-pulse"
                >
                  <Square size={14} /> Terminate Simulation
                </button>
              )}
            </div>
          </div>
        )}
      </div>

      {/* 2. FLISR Restoration Timeline & Controls */}
      <div className="bg-scada-panel border border-scada-border rounded-lg p-4 flex flex-col justify-between overflow-hidden">
        <div>
          <h2 className="text-sm font-semibold tracking-wider text-scada-dimText uppercase mb-2 flex items-center justify-between">
            <span className="flex items-center gap-1.5">
              <ShieldCheck size={16} className="text-scada-nominal" />
              FLISR Restoration Logic
            </span>
            <span className={`text-[10px] px-2 py-0.5 rounded font-mono uppercase ${
              flisrAuto ? "bg-emerald-500/10 text-scada-nominal" : "bg-yellow-500/10 text-scada-warning"
            }`}>
              {flisrAuto ? "Auto Healing Active" : "Manual Grid"}
            </span>
          </h2>
          
          <div className="space-y-3">
            {/* Auto FLISR Toggle */}
            <div className="flex justify-between items-center text-xs">
              <span className="text-scada-dimText font-medium">Automatic Restoration Mode:</span>
              <button
                onClick={() => onSendConfig({ flisr_auto: !flisrAuto })}
                className={`px-3 py-1 rounded font-semibold text-xs transition-colors ${
                  flisrAuto
                    ? "bg-scada-nominal hover:bg-emerald-600 text-white"
                    : "bg-scada-border hover:bg-scada-border/80 text-scada-dimText hover:text-white"
                }`}
              >
                {flisrAuto ? "ENABLED" : "DISABLED"}
              </button>
            </div>

            {/* Clear Alarm Systems */}
            <div className="flex justify-between items-center text-xs">
              <span className="text-scada-dimText font-medium">Reset Grid & Breakers:</span>
              <button
                onClick={() => {
                  onSendControl({ command: "RESET_ALARMS" });
                  setAckIds(new Set());
                }}
                className="bg-scada-border hover:bg-scada-border/80 border border-scada-border text-white px-3 py-1 rounded flex items-center gap-1 transition-colors text-xs"
              >
                <RotateCcw size={12} /> Reset System
              </button>
            </div>
          </div>
        </div>

        {/* FLISR State Machine HMI */}
        <div className="bg-black/30 border border-scada-border/60 rounded p-2.5 my-2 text-[10px] font-mono space-y-1.5 shrink-0">
          <div className="flex justify-between items-center">
            <span className="text-scada-dimText uppercase text-[9px]">FSM State:</span>
            <span className={`px-2 py-0.5 rounded font-bold uppercase tracking-widest text-[9px] ${
              flisrState === "NORMAL" 
                ? "bg-emerald-500/10 text-scada-nominal" 
                : flisrState === "FAULT_DETECTED"
                ? "bg-red-500/10 text-scada-trip animate-pulse"
                : flisrState === "ISOLATION"
                ? "bg-amber-500/10 text-scada-warning animate-pulse"
                : flisrState === "RESTORATION"
                ? "bg-blue-500/10 text-blue-400 animate-pulse"
                : "bg-purple-500/10 text-purple-400 font-extrabold"
            }`}>
              {flisrState}
            </span>
          </div>
          <div className="grid grid-cols-2 gap-2 text-[9px]">
            <div className="flex flex-col bg-scada-bg/40 p-1 rounded border border-scada-border/30">
              <span className="text-gray-500 font-sans font-semibold uppercase text-[8px]">Isolated Segs</span>
              <span className="text-white truncate">
                {flisrIsolated.length > 0 ? flisrIsolated.join(", ") : "NONE"}
              </span>
            </div>
            <div className="flex flex-col bg-scada-bg/40 p-1 rounded border border-scada-border/30">
              <span className="text-gray-500 font-sans font-semibold uppercase text-[8px]">Tie Switches</span>
              <span className="text-scada-nominal truncate font-bold">
                {flisrReconfigured.length > 0 ? flisrReconfigured.join(", ") : "NONE"}
              </span>
            </div>
          </div>
        </div>

        {/* FLISR Event logs container */}
        <div className="flex-1 mt-3 overflow-y-auto border border-scada-border bg-scada-bg rounded p-2 max-h-[140px]">
          <p className="text-[10px] font-bold text-scada-dimText tracking-wider uppercase mb-1">Restoration Logs</p>
          <div className="space-y-1">
            {events
              .filter((ev) => ev.source === "FLISR_ENGINE")
              .slice(0, 10)
              .map((ev, i) => (
                <div key={i} className="text-[10px] font-mono text-scada-warning border-l-2 border-scada-warning pl-1.5 leading-relaxed">
                  <span className="text-scada-dimText font-bold mr-1">
                    {new Date(ev.timestamp).toLocaleTimeString([], { hour12: false })}
                  </span>
                  {ev.event}
                </div>
              ))}
            {events.filter((ev) => ev.source === "FLISR_ENGINE").length === 0 && (
              <p className="text-[10px] text-scada-dimText font-mono italic">No self-healing events logged.</p>
            )}
          </div>
        </div>
      </div>

      {/* 3. Cyber Alarms / Intrusion Detection System (IDS) Panel */}
      <div className="bg-scada-panel border border-scada-border rounded-lg p-4 flex flex-col justify-between overflow-hidden">
        <div>
          <h2 className="text-sm font-semibold tracking-wider text-scada-dimText uppercase mb-2 flex items-center justify-between">
            <span className="flex items-center gap-1.5">
              <AlertTriangle size={16} className="text-scada-trip animate-pulse" />
              AI Intrusion Detection System
            </span>
            <button
              onClick={handleAckAll}
              className="text-[9px] bg-scada-border hover:bg-scada-border/80 border border-scada-border px-1.5 py-0.5 rounded text-white font-mono uppercase"
              title="Acknowledge All Unacknowledged Alarms"
            >
              Ack All
            </button>
          </h2>

          {/* Tab Selection & Grouping Controls */}
          <div className="flex items-center justify-between mb-2 border-b border-scada-border/30 pb-1 shrink-0 font-mono text-[9px]">
            <div className="flex gap-2">
              <button
                onClick={() => setCurrentTab("all")}
                className={`pb-0.5 font-bold uppercase transition-all border-b-2 ${
                  currentTab === "all" ? "border-emerald-500 text-white" : "border-transparent text-scada-dimText"
                }`}
              >
                All ({deduplicatedAlerts.length})
              </button>
              <button
                onClick={() => setCurrentTab("escalated")}
                className={`pb-0.5 font-bold uppercase transition-all border-b-2 ${
                  currentTab === "escalated" ? "border-red-500 text-red-400 animate-pulse" : "border-transparent text-scada-dimText"
                }`}
              >
                Escalated ({escalatedAlerts.length})
              </button>
            </div>
            
            <div className="flex items-center gap-1 text-[8px] text-scada-dimText">
              <Folder size={10} />
              <span>Group:</span>
              <select
                value={groupBy}
                onChange={(e) => setGroupBy(e.target.value as any)}
                className="bg-scada-bg border border-scada-border rounded text-white focus:outline-none px-1"
              >
                <option value="none">None</option>
                <option value="node">Node</option>
                <option value="severity">Severity</option>
              </select>
            </div>
          </div>

          {/* Severity summary badge strip */}
          <div className="flex gap-1.5 mb-2">
            <span className={`flex items-center gap-1 px-2 py-0.5 rounded text-[9px] font-bold uppercase border ${
              unackedCounts.CRITICAL > 0
                ? "bg-red-500/15 border-red-500/40 text-red-400 font-extrabold animate-pulse"
                : "bg-scada-bg border-scada-border/30 text-gray-600"
            }`}>
              <AlertCircle size={9} />
              CRIT {unackedCounts.CRITICAL}
            </span>
            <span className={`flex items-center gap-1 px-2 py-0.5 rounded text-[9px] font-bold uppercase border ${
              unackedCounts.HIGH > 0
                ? "bg-orange-500/15 border-orange-500/40 text-orange-400"
                : "bg-scada-bg border-scada-border/30 text-gray-600"
            }`}>
              <AlertTriangle size={9} />
              HIGH {unackedCounts.HIGH}
            </span>
            <span className={`flex items-center gap-1 px-2 py-0.5 rounded text-[9px] font-bold uppercase border ${
              unackedCounts.WARNING > 0
                ? "bg-yellow-500/15 border-yellow-500/40 text-yellow-400"
                : "bg-scada-bg border-scada-border/30 text-gray-600"
            }`}>
              <Radio size={9} />
              WARN {unackedCounts.WARNING}
            </span>
            {deduplicatedAlerts.length === 0 && (
              <span className="flex items-center gap-1 px-2 py-0.5 rounded text-[9px] font-bold uppercase border bg-emerald-500/10 border-emerald-500/30 text-scada-nominal">
                <CheckCircle2 size={9} /> NOMINAL
              </span>
            )}
          </div>

          {/* Compromised node count summary banner */}
          {compromisedCount > 0 && (
            <div className="mb-2 bg-red-900/20 border border-red-500/30 rounded px-2 py-1 text-[9px] font-mono text-red-300 flex items-center justify-between">
              <span className="flex items-center gap-1">
                <ShieldAlert size={10} className="animate-pulse" />
                <span className="font-bold text-red-400">{compromisedCount} NODE{compromisedCount > 1 ? "S" : ""} COMPROMISED</span>
              </span>
              <span className="text-red-500/70 truncate max-w-[120px]">
                {compromisedNames.slice(0, 3).join(", ")}{compromisedNames.length > 3 ? ` +${compromisedNames.length - 3}` : ""}
              </span>
            </div>
          )}
        </div>

        {/* Alarms list container with dynamic grouping and filter acknowledgements */}
        <div className="flex-1 overflow-y-auto border border-scada-border bg-scada-bg rounded p-2 max-h-[150px] scrollbar-thin">
          <div className="space-y-2">
            {groupBy === "none" ? (
              visibleAlerts.map((alert, i) => {
                const key = getAlertKey(alert);
                const isAcked = ackIds.has(key);
                return (
                  <div
                    key={i}
                    className={`text-[10px] font-mono p-1.5 rounded flex flex-col gap-0.5 border transition-opacity duration-300 relative ${
                      isAcked
                        ? "bg-scada-panel/40 border-scada-border/20 text-gray-500 opacity-60"
                        : alert.severity === "CRITICAL"
                        ? "bg-red-500/10 border-red-500/30 text-red-400 animate-pulse font-bold"
                        : alert.severity === "HIGH"
                        ? "bg-orange-500/10 border-orange-500/30 text-orange-300"
                        : "bg-yellow-500/10 border-yellow-500/30 text-yellow-400"
                    }`}
                  >
                    <div className="flex justify-between items-center font-bold text-[9px] uppercase tracking-wider">
                      <div className="flex items-center gap-1.5">
                        <span className={`px-1 py-0.5 rounded text-[8px] ${
                          isAcked ? "bg-gray-800 text-gray-500" :
                          alert.severity === "CRITICAL" ? "bg-red-500/30 text-red-300" :
                          alert.severity === "HIGH" ? "bg-orange-500/30 text-orange-300" :
                          "bg-yellow-500/30 text-yellow-300"
                        }`}>{alert.severity}</span>
                        <span className="text-white/70">{alert.type}</span>
                        {alert._count > 1 && (
                          <span className="px-1.5 py-0.5 rounded-full bg-white/10 text-gray-300 text-[8px] font-bold">
                            ×{alert._count}
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-scada-dimText font-semibold">
                          {new Date(alert.timestamp).toLocaleTimeString([], { hour12: false })}
                        </span>
                        <button
                          onClick={() => toggleAckAlert(key)}
                          className={`p-0.5 rounded border border-scada-border hover:text-white transition-colors ${
                            isAcked ? "bg-emerald-500/20 text-emerald-400" : "bg-black/30 text-gray-400"
                          }`}
                          title={isAcked ? "Mark Unacknowledged" : "Mark Acknowledged"}
                        >
                          <Check size={9} />
                        </button>
                      </div>
                    </div>
                    <p className={`leading-tight mt-0.5 ${isAcked ? "text-gray-500 line-through" : "text-white"}`}>
                      {alert.msg}
                    </p>
                    {alert.suspect_node && (
                      <span className={`text-[8px] px-1 py-0.5 rounded w-max mt-0.5 font-bold uppercase ${
                        isAcked ? "bg-gray-800/30 text-gray-600" : "bg-black/40 text-gray-400"
                      }`}>
                        Suspect Node: {alert.suspect_node}
                      </span>
                    )}
                    <div className="mt-1 flex gap-1 items-center font-mono text-[8px]">
                      <span className="text-emerald-500 shrink-0 uppercase font-semibold">NOTE:</span>
                      <input
                        type="text"
                        value={annotations[key] || ""}
                        onChange={(e) => onAddAnnotation(key, e.target.value)}
                        placeholder="Add operator note..."
                        className="bg-black/40 border border-scada-border/20 rounded px-1.5 py-0.5 text-white flex-1 focus:outline-none focus:border-emerald-500/50 text-[8px]"
                      />
                    </div>
                  </div>
                );
              })
            ) : (
              // Grouped Render Layout
              (() => {
                const groups: Record<string, typeof deduplicatedAlerts> = {};
                visibleAlerts.forEach(a => {
                  const grpKey = groupBy === "node" 
                    ? (a.suspect_node ?? "SYSTEM") 
                    : a.severity;
                  if (!groups[grpKey]) groups[grpKey] = [];
                  groups[grpKey].push(a);
                });

                return Object.entries(groups).map(([grpName, items]) => (
                  <div key={grpName} className="border border-scada-border/20 rounded p-1.5 bg-black/10">
                    <span className="text-[8px] font-bold text-emerald-400 uppercase tracking-wider block border-b border-scada-border/20 pb-0.5 mb-1.5">
                      {grpName} ({items.length})
                    </span>
                    <div className="space-y-1">
                      {items.map((alert, i) => {
                        const key = getAlertKey(alert);
                        const isAcked = ackIds.has(key);
                        return (
                          <div
                            key={i}
                            className={`text-[9px] font-mono p-1 rounded flex flex-col gap-0.5 transition-opacity duration-300 relative ${
                              isAcked
                                ? "text-gray-500 opacity-60 line-through"
                                : alert.severity === "CRITICAL"
                                ? "text-red-400 font-bold"
                                : alert.severity === "HIGH"
                                ? "text-orange-300"
                                : "text-yellow-400"
                            }`}
                          >
                            <div className="flex justify-between items-center font-bold">
                              <span>{alert.type} {alert._count > 1 ? `(×${alert._count})` : ""}</span>
                              <div className="flex items-center gap-1.5">
                                <span>{new Date(alert.timestamp).toLocaleTimeString([], { hour12: false })}</span>
                                <button
                                  onClick={() => toggleAckAlert(key)}
                                  className={`p-0.2 rounded border scale-90 border-scada-border transition-colors ${
                                    isAcked ? "bg-emerald-500/20 text-emerald-400" : "bg-black/30 text-gray-400"
                                  }`}
                                >
                                  <Check size={8} />
                                </button>
                              </div>
                            </div>
                            <p className="text-[8.5px] leading-tight text-white/80">{alert.msg}</p>
                            <div className="mt-1 flex gap-1 items-center font-mono text-[7.5px]">
                              <span className="text-emerald-500 shrink-0 font-semibold uppercase">NOTE:</span>
                              <input
                                type="text"
                                value={annotations[key] || ""}
                                onChange={(e) => onAddAnnotation(key, e.target.value)}
                                placeholder="Add note..."
                                className="bg-black/40 border border-scada-border/20 rounded px-1 text-white flex-1 focus:outline-none focus:border-emerald-500/50 text-[7.5px]"
                              />
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                ));
              })()
            )}
            
            {visibleAlerts.length === 0 && (
              <p className="text-[10px] text-scada-dimText font-mono italic text-center py-8">
                {currentTab === "escalated" 
                  ? "No escalated unacknowledged critical alerts."
                  : "No cyber anomalies detected. Sensors nominal."
                }
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
