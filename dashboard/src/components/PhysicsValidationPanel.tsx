import React from "react";
import { Activity, Clock, ShieldAlert, CheckCircle, AlertOctagon } from "lucide-react";

interface PhysicsValidationData {
  timestamp: number;
  physics_anomaly_score: number;
  kcl_error: number;
  kvl_error: number;
  physics_state: string; // "NORMAL" | "PHYSICAL_INSTABILITY" | "CYBER_ATTACK_INSTABILITY" | "IMPOSSIBLE_STATE" | "SUSPICIOUS"
  impossible_state: boolean;
  impossible_violations: string[];
  ai_threat_prob: number;
}

interface PhysicsValidationPanelProps {
  validationData: PhysicsValidationData | null;
}

export const PhysicsValidationPanel: React.FC<PhysicsValidationPanelProps> = ({ validationData }) => {
  const getStatusBadge = (state: string) => {
    switch (state) {
      case "IMPOSSIBLE_STATE":
        return "bg-purple-500/15 border-purple-500 text-purple-400 font-extrabold animate-pulse scada-glow-purple";
      case "CYBER_ATTACK_INSTABILITY":
        return "bg-red-500/15 border-red-500 text-red-400 font-extrabold animate-bounce scada-glow-red";
      case "PHYSICAL_INSTABILITY":
        return "bg-cyan-500/15 border-cyan-500 text-cyan-400 font-bold";
      case "SUSPICIOUS":
        return "bg-yellow-500/15 border-yellow-500 text-yellow-400 font-bold";
      default:
        return "bg-emerald-500/10 border-emerald-500/30 text-scada-nominal font-medium";
    }
  };

  const getStatusText = (state: string) => {
    switch (state) {
      case "IMPOSSIBLE_STATE":
        return "TELEMETRY CORRUPT (VIOLATES LAWS)";
      case "CYBER_ATTACK_INSTABILITY":
        return "MALICIOUS INTRUSION (FDIA/SPOOF)";
      case "PHYSICAL_INSTABILITY":
        return "PHYSICAL OUTAGE (TRUSTED STATE)";
      case "SUSPICIOUS":
        return "TRANSIENT DRIFT / UNSTABLE";
      default:
        return "CONSISTENT / NOMINAL";
    }
  };

  const hasData = validationData !== null && validationData.physics_state !== undefined;
  const score = hasData ? validationData.physics_anomaly_score : 0;
  const kclErr = hasData ? validationData.kcl_error : 0.0;
  const kvlErr = hasData ? validationData.kvl_error : 0.0;
  const physicsState = hasData ? validationData.physics_state : "NORMAL";
  const impossible = hasData ? validationData.impossible_state : false;
  const violations = hasData ? validationData.impossible_violations : [];

  return (
    <div className="bg-scada-panel border border-scada-border rounded-lg p-4 h-[300px] flex flex-col justify-between overflow-hidden">
      {/* Header */}
      <div className="flex justify-between items-center mb-2 border-b border-scada-border/40 pb-1.5 shrink-0">
        <h2 className="text-sm font-semibold tracking-wider text-scada-dimText uppercase flex items-center gap-1.5">
          <Activity size={16} className={impossible ? "text-purple-500 animate-pulse" : physicsState === "CYBER_ATTACK_INSTABILITY" ? "text-red-500 animate-bounce" : "text-cyan-500"} />
          Physics-Aware State Validator
        </h2>
        <div className="flex items-center gap-1.5 font-mono text-[9px] text-scada-dimText">
          <Clock size={10} />
          <span>Real-time Checks</span>
        </div>
      </div>

      {/* Main Panel Content */}
      {!hasData ? (
        <div className="flex-1 flex flex-col items-center justify-center gap-2 font-mono text-xs text-scada-dimText italic">
          <div className="animate-spin w-4 h-4 border-2 border-cyan-500 border-t-transparent rounded-full"></div>
          <span>Validation subsystem initializing... Awaiting telemetry sweeps...</span>
        </div>
      ) : (
        <div className="flex-1 flex flex-col justify-between overflow-hidden">
          
          {/* Consistency Badge and Physics Anomaly Score */}
          <div className="grid grid-cols-2 gap-3 mb-2 shrink-0">
            <div className="bg-scada-bg/60 border border-scada-border/50 rounded p-2 flex flex-col justify-between h-[65px]">
              <span className="text-[8px] text-scada-dimText uppercase font-mono font-semibold">Grid State Integrity</span>
              <span className={`px-2 py-0.5 border rounded-[3px] text-[8px] tracking-wider uppercase font-semibold text-center font-mono mt-1 ${getStatusBadge(physicsState)}`}>
                {getStatusText(physicsState)}
              </span>
            </div>
            
            <div className="bg-scada-bg/60 border border-scada-border/50 rounded p-2 flex flex-col justify-between h-[65px]">
              <span className="text-[8px] text-scada-dimText uppercase font-mono font-semibold">Physics Anomaly Score</span>
              <div className="flex items-baseline gap-1 mt-1">
                <span className={`text-base font-bold font-scada-nums ${
                  score >= 70 ? "text-red-400 scada-text-glow-red font-extrabold" :
                  score >= 30 ? "text-yellow-400" : "text-scada-nominal"
                }`}>
                  {score}
                </span>
                <span className="text-[8px] text-scada-dimText font-mono">/100</span>
              </div>
            </div>
          </div>

          {/* Mismatch Gauges and Violations */}
          <div className="flex-1 flex flex-col justify-between overflow-hidden">
            <div className="grid grid-cols-2 gap-3 shrink-0">
              {/* KCL mismatch progress */}
              <div className="space-y-1 font-mono text-[8px]">
                <div className="flex justify-between text-scada-dimText font-semibold">
                  <span>KCL BALANCE ERR:</span>
                  <span className={`font-bold ${kclErr > 5.0 ? "text-yellow-400" : "text-white"}`}>{kclErr.toFixed(1)} MW</span>
                </div>
                <div className="w-full h-1 bg-scada-bg rounded overflow-hidden">
                  <div 
                    className={`h-full transition-all duration-300 ${kclErr > 10.0 ? "bg-red-500" : kclErr > 2.0 ? "bg-yellow-500" : "bg-emerald-500"}`}
                    style={{ width: `${Math.min(100, kclErr * 5)}%` }}
                  ></div>
                </div>
              </div>

              {/* KVL mismatch progress */}
              <div className="space-y-1 font-mono text-[8px]">
                <div className="flex justify-between text-scada-dimText font-semibold">
                  <span>KVL CONSISTENCY ERR:</span>
                  <span className={`font-bold ${kvlErr > 0.02 ? "text-yellow-400" : "text-white"}`}>{kvlErr.toFixed(4)} p.u.</span>
                </div>
                <div className="w-full h-1 bg-scada-bg rounded overflow-hidden">
                  <div 
                    className={`h-full transition-all duration-300 ${kvlErr > 0.05 ? "bg-red-500" : kvlErr > 0.01 ? "bg-yellow-500" : "bg-emerald-500"}`}
                    style={{ width: `${Math.min(100, kvlErr * 1000)}%` }}
                  ></div>
                </div>
              </div>
            </div>

            {/* Diagnostic Log */}
            <div className="mt-2 p-1.5 bg-scada-bg/85 border border-scada-border/40 rounded flex-1 overflow-y-auto flex flex-col justify-start min-h-[70px] max-h-[85px]">
              <div className="flex items-center gap-1 mb-1 shrink-0">
                {impossible ? (
                  <AlertOctagon size={12} className="text-purple-400 animate-pulse" />
                ) : physicsState === "CYBER_ATTACK_INSTABILITY" ? (
                  <ShieldAlert size={12} className="text-red-400 animate-bounce" />
                ) : physicsState === "PHYSICAL_INSTABILITY" ? (
                  <Activity size={12} className="text-cyan-400" />
                ) : (
                  <CheckCircle size={12} className="text-emerald-400" />
                )}
                <span className="text-[7.5px] font-bold font-mono tracking-wider uppercase text-white">
                  PHYSICAL LAW DIAGNOSTIC ENGINE:
                </span>
              </div>
              <div className="text-[8px] font-mono text-scada-dimText leading-snug space-y-1">
                {violations.length > 0 ? (
                  violations.map((v, idx) => (
                    <div key={idx} className="text-red-300 border-l border-red-500 pl-1.5 py-0.5">
                      {v}
                    </div>
                  ))
                ) : (
                  <p className="text-scada-dimText italic">
                    {physicsState === "PHYSICAL_INSTABILITY"
                      ? "Grid voltages deviate from nominal limits, but line power flows and bus balances perfectly satisfy Kirchhoff's Laws. Telemetry is electrically verified (trusted)."
                      : "Telemetry matches Kirchhoff's Current and Voltage Laws. Zero physical law violations detected in the network."}
                  </p>
                )}
              </div>
            </div>
          </div>

          {/* Footer Info */}
          <div className="flex justify-between items-center border-t border-scada-border/20 pt-2 shrink-0 font-mono text-[8px] text-scada-dimText mt-1">
            <div className="flex items-center gap-1.5">
              <span>PHYSICS LAWS:</span>
              <span className={`font-bold ${impossible ? "text-purple-400 animate-pulse" : kclErr > 10.0 || kvlErr > 0.05 ? "text-red-400 font-extrabold" : "text-scada-nominal"}`}>
                {impossible ? "CRITICAL CONFLICT" : kclErr > 10.0 || kvlErr > 0.05 ? "INCONSISTENT" : "KCL/KVL VERIFIED"}
              </span>
            </div>
            <div className="flex items-center gap-1">
              <span>UPDATED:</span>
              <span className="text-white font-scada-nums">
                {new Date(validationData.timestamp).toLocaleTimeString([], { hour12: false })}
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
