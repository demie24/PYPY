import React from "react";
import { Shield, Clock, ShieldCheck, ShieldAlert, Cpu } from "lucide-react";

interface BusForecast {
  predicted: number;
  actual: number;
  delta: number;
}

interface ThreatAwareForecastData {
  timestamp: number;
  forecasts: Record<string, BusForecast>;
  cyber_instability_probability?: number;
  predicted_threat?: number;
  status: string; // "NORMAL" | "SUSPICIOUS" | "CYBER-CRITICAL"
  confidence: number;
  forecast_horizon_seconds: number;
}

interface ThreatAwareForecastPanelProps {
  forecastData: ThreatAwareForecastData | null;
}

export const ThreatAwareForecastPanel: React.FC<ThreatAwareForecastPanelProps> = ({ forecastData }) => {
  const getStatusStyle = (status: string) => {
    switch (status) {
      case "CYBER-CRITICAL":
        return "bg-red-500/15 border-red-500 text-red-400 animate-pulse font-extrabold scada-glow-red";
      case "SUSPICIOUS":
        return "bg-yellow-500/15 border-yellow-500 text-yellow-400 font-bold";
      default:
        return "bg-emerald-500/10 border-emerald-500/30 text-scada-nominal font-medium";
    }
  };

  const hasData = forecastData !== null && forecastData !== undefined;
  
  const cyberProb = hasData 
    ? (forecastData.cyber_instability_probability !== undefined 
        ? forecastData.cyber_instability_probability 
        : (forecastData.predicted_threat !== undefined 
            ? (forecastData.predicted_threat > 1.0 ? forecastData.predicted_threat / 100 : forecastData.predicted_threat)
            : 0.0))
    : 0.0;

  const status = hasData ? (forecastData.status ?? "NORMAL") : "NORMAL";
  const confidence = hasData ? (forecastData.confidence ?? 0.0) : 0.0;

  // Evaluate if physical voltage deviation is occurring without cyber indicators
  const hasVoltageDeviation = hasData && forecastData.forecasts ? Object.values(forecastData.forecasts).some(
    (f) => f && (typeof f.predicted === "number" && (f.predicted < 0.95 || f.predicted > 1.05))
  ) : false;

  const isPhysicalInstability = hasVoltageDeviation && cyberProb < 0.30;
  const isCyberInstability = hasVoltageDeviation && cyberProb >= 0.30;

  return (
    <div className="bg-scada-panel border border-scada-border rounded-lg p-4 h-[300px] flex flex-col justify-between overflow-hidden">
      {/* Header */}
      <div className="flex justify-between items-center mb-2 border-b border-scada-border/40 pb-1.5 shrink-0">
        <h2 className="text-sm font-semibold tracking-wider text-scada-dimText uppercase flex items-center gap-1.5">
          <Shield size={16} className={status === "CYBER-CRITICAL" ? "text-red-500 animate-pulse" : "text-emerald-500"} />
          Cyber-Aware AI Predictor
        </h2>
        <div className="flex items-center gap-1.5 font-mono text-[9px] text-scada-dimText">
          <Clock size={10} />
          <span>Horizon: 10s</span>
        </div>
      </div>

      {/* Main Content */}
      {!hasData ? (
        <div className="flex-1 flex flex-col items-center justify-center gap-2 font-mono text-xs text-scada-dimText italic">
          <div className="animate-spin w-4 h-4 border-2 border-emerald-500 border-t-transparent rounded-full"></div>
          <span>Security predictor warming up... Awaiting MQTT cycles...</span>
        </div>
      ) : (
        <div className="flex-1 flex flex-col justify-between overflow-hidden">
          
          {/* Status Indicators */}
          <div className="grid grid-cols-2 gap-3 mb-2 shrink-0">
            <div className="bg-scada-bg/60 border border-scada-border/50 rounded p-2 flex flex-col justify-between h-[65px]">
              <span className="text-[8px] text-scada-dimText uppercase font-mono font-semibold">Forecast Mode</span>
              <span className={`px-2 py-0.5 border rounded-[3px] text-[9px] tracking-widest uppercase font-semibold text-center font-mono mt-1 ${getStatusStyle(status)}`}>
                {status}
              </span>
            </div>
            
            <div className="bg-scada-bg/60 border border-scada-border/50 rounded p-2 flex flex-col justify-between h-[65px]">
              <span className="text-[8px] text-scada-dimText uppercase font-mono font-semibold">Cyber Anomaly Risk</span>
              <div className="flex items-baseline gap-1 mt-1">
                <span className={`text-base font-bold font-scada-nums ${
                  cyberProb >= 0.70 ? "text-red-400 scada-text-glow-red font-extrabold" :
                  cyberProb >= 0.30 ? "text-yellow-400" : "text-scada-nominal"
                }`}>
                  {typeof cyberProb === "number" ? (cyberProb * 100).toFixed(1) : "0.0"}%
                </span>
                <span className="text-[8px] text-scada-dimText font-mono">prob</span>
              </div>
            </div>
          </div>

          {/* Progress Bars and Metrics */}
          <div className="flex-1 space-y-2 mt-1">
            {/* Risk Gauge Bar */}
            <div className="space-y-1">
              <div className="flex justify-between text-[8px] font-mono font-semibold text-scada-dimText">
                <span>CYBER ATTACK PROBABILITY GAUGE:</span>
                <span className={cyberProb >= 0.30 ? "text-yellow-400 font-bold" : ""}>
                  {typeof cyberProb === "number" ? (cyberProb * 100).toFixed(0) : "0"}%
                </span>
              </div>
              <div className="w-full h-1.5 bg-scada-bg rounded overflow-hidden border border-scada-border/40">
                <div 
                  className={`h-full transition-all duration-500 ${
                    cyberProb >= 0.70 ? "bg-red-500" :
                    cyberProb >= 0.30 ? "bg-yellow-500" : "bg-emerald-500"
                  }`}
                  style={{ width: `${cyberProb * 100}%` }}
                ></div>
              </div>
            </div>

            {/* Forecast Confidence Bar */}
            <div className="space-y-1">
              <div className="flex justify-between text-[8px] font-mono font-semibold text-scada-dimText">
                <span>AI FORECAST CONFIDENCE:</span>
                <span className="text-white font-bold font-scada-nums">
                  {typeof confidence === "number" ? (confidence * 100).toFixed(0) : "0"}%
                </span>
              </div>
              <div className="w-full h-1.5 bg-scada-bg rounded overflow-hidden border border-scada-border/40">
                <div 
                  className="h-full bg-cyan-500 transition-all duration-500"
                  style={{ width: `${confidence * 100}%` }}
                ></div>
              </div>
            </div>

            {/* Diagnostics Analysis Box */}
            <div className="mt-2 p-2 bg-scada-bg/85 border border-scada-border/40 rounded flex-1 flex flex-col justify-center min-h-[60px]">
              <div className="flex items-center gap-1.5 mb-1 shrink-0">
                {isCyberInstability ? (
                  <ShieldAlert size={12} className="text-red-400 animate-bounce" />
                ) : isPhysicalInstability ? (
                  <Cpu size={12} className="text-cyan-400" />
                ) : (
                  <ShieldCheck size={12} className="text-emerald-400" />
                )}
                <span className="text-[8px] font-bold font-mono tracking-wider uppercase text-white">
                  {isCyberInstability ? "CYBERATTACK INSTABILITY IDENTIFIED" :
                   isPhysicalInstability ? "PHYSICAL GRID INSTABILITY IDENTIFIED" :
                   status === "SUSPICIOUS" ? "ANOMALOUS TELEMETRY DRIFT" : "SYSTEM STATE NOMINAL"}
                </span>
              </div>
              <p className="text-[8px] font-mono text-scada-dimText leading-tight">
                {isCyberInstability 
                  ? "AI detected synchronized voltage deviations accompanied by active intrusion vectors. Telemetry has high probability of being tampered." 
                  : isPhysicalInstability 
                  ? "Voltage deviations detected but cyberattack probability is low. Instability is physical (e.g. FLISR action or line trip). Telemetry is verified." 
                  : status === "SUSPICIOUS"
                  ? "Grid telemetry is showing minor anomalies or transient drifts. Threat scoring engine monitoring."
                  : "All telemetry lines are clean. The digital twin model and physical sensors are running in full synchronization."}
              </p>
            </div>
          </div>

          {/* Footer Info */}
          <div className="flex justify-between items-center border-t border-scada-border/20 pt-2 shrink-0 font-mono text-[8px] text-scada-dimText mt-1">
            <div className="flex items-center gap-1">
              <span>CYBER ENGINE:</span>
              <span className={`font-bold ${status === "CYBER-CRITICAL" ? "text-red-400 animate-pulse" : "text-emerald-400"}`}>
                {status === "CYBER-CRITICAL" ? "ALERT" : "SHIELD ONLINE"}
              </span>
            </div>
            <div className="flex items-center gap-1">
              <span>UPDATED:</span>
              <span className="text-white font-scada-nums">
                {forecastData.timestamp ? new Date(forecastData.timestamp).toLocaleTimeString([], { hour12: false }) : "N/A"}
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
