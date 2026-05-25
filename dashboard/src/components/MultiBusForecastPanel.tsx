import React from "react";
import { Cpu, Clock, AlertTriangle } from "lucide-react";

interface BusForecast {
  predicted: number;
  actual: number;
  delta: number;
  status: string;
}

interface MultiBusForecastData {
  timestamp: number;
  forecasts: Record<string, BusForecast>;
  overall_status: string;
  confidence: number;
  forecast_horizon_seconds: number;
}

interface MultiBusForecastPanelProps {
  forecastData: MultiBusForecastData | null;
}

export const MultiBusForecastPanel: React.FC<MultiBusForecastPanelProps> = ({ forecastData }) => {
  const getStatusStyle = (status: string) => {
    switch (status) {
      case "CRITICAL":
        return "bg-red-500/15 border-red-500 text-red-400 animate-pulse font-extrabold scada-glow-red";
      case "WARNING":
        return "bg-orange-500/15 border-orange-500 text-orange-400 font-bold";
      default:
        return "bg-emerald-500/10 border-emerald-500/30 text-scada-nominal font-medium";
    }
  };

  const getDeltaColor = (delta: number) => {
    const absD = Math.abs(delta);
    if (absD > 0.10) return "text-red-400";
    if (absD > 0.04) return "text-orange-400";
    if (absD > 0.01) return "text-yellow-400";
    return "text-scada-nominal";
  };

  const hasData = forecastData !== null && forecastData.forecasts !== undefined;

  return (
    <div className="bg-scada-panel border border-scada-border rounded-lg p-4 h-[300px] flex flex-col justify-between overflow-hidden">
      {/* Header Panel */}
      <div className="flex justify-between items-center mb-2 border-b border-scada-border/40 pb-1.5 shrink-0">
        <h2 className="text-sm font-semibold tracking-wider text-scada-dimText uppercase flex items-center gap-1.5">
          <Cpu size={16} className={hasData && forecastData.overall_status === "CRITICAL" ? "text-red-500 animate-bounce" : "text-amber-500"} />
          AI Multi-Bus Stability Forecast
        </h2>
        <div className="flex items-center gap-1.5 font-mono text-[9px] text-scada-dimText">
          <Clock size={10} />
          <span>Horizon: 10s</span>
        </div>
      </div>

      {/* Main Panel Content */}
      {!hasData ? (
        <div className="flex-1 flex flex-col items-center justify-center gap-2 font-mono text-xs text-scada-dimText italic">
          <div className="animate-spin w-4 h-4 border-2 border-amber-500 border-t-transparent rounded-full"></div>
          <span>Inference buffer warming up... Awaiting MQTT cycles...</span>
        </div>
      ) : (
        <div className="flex-1 flex flex-col justify-between overflow-hidden">
          {/* Global Alert Bar if Grid degraded */}
          {forecastData.overall_status !== "NORMAL" && (
            <div className={`p-1.5 px-3 mb-2 rounded border text-[9px] font-mono flex items-center gap-2 ${
              forecastData.overall_status === "CRITICAL"
                ? "bg-red-500/10 border-red-500/30 text-red-300 animate-pulse"
                : "bg-orange-500/10 border-orange-500/30 text-orange-300"
            }`}>
              <AlertTriangle size={12} className="shrink-0 animate-bounce" />
              <span className="font-bold">GRID VOLTAGE INSTABILITY DETECTED AT t+10s SECONDS</span>
            </div>
          )}

          {/* Table of predicted bus voltages */}
          <div className="flex-1 overflow-y-auto pr-1">
            <table className="w-full text-left font-mono text-[9px] border-collapse">
              <thead>
                <tr className="text-scada-dimText border-b border-scada-border/20 text-[8px] uppercase tracking-wider">
                  <th className="pb-1 font-semibold">Bus Target</th>
                  <th className="pb-1 font-semibold text-right">Actual</th>
                  <th className="pb-1 font-semibold text-right">Forecast (10s)</th>
                  <th className="pb-1 font-semibold text-right">Error Δ</th>
                  <th className="pb-1 font-semibold text-center">Stability</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-scada-border/10">
                {Object.entries(forecastData.forecasts).map(([busName, data]) => (
                  <tr key={busName} className="hover:bg-white/5 transition-colors">
                    <td className="py-1.5 font-bold text-white uppercase">{busName.replace("_", " ")}</td>
                    <td className="py-1.5 text-right font-scada-nums font-bold text-cyan-400">{data.actual.toFixed(4)}</td>
                    <td className="py-1.5 text-right font-scada-nums font-bold text-amber-400">{data.predicted.toFixed(4)}</td>
                    <td className={`py-1.5 text-right font-scada-nums font-bold ${getDeltaColor(data.delta)}`}>
                      {data.delta >= 0 ? "+" : ""}{data.delta.toFixed(4)}
                    </td>
                    <td className="py-1.5 text-center">
                      <span className={`px-2 py-0.5 border rounded-[3px] text-[8px] tracking-wider uppercase font-semibold ${getStatusStyle(data.status)}`}>
                        {data.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Bottom Info Strip */}
          <div className="flex justify-between items-center border-t border-scada-border/20 pt-2 shrink-0 font-mono text-[8px] text-scada-dimText">
            <div className="flex items-center gap-2">
              <span>CONFIDENCE:</span>
              <span className="text-white font-bold font-scada-nums text-[9px]">
                {Math.round(forecastData.confidence * 100)}%
              </span>
            </div>
            <div className="flex items-center gap-1.5">
              <span>UPDATED:</span>
              <span className="text-white font-scada-nums text-[8px]">
                {new Date(forecastData.timestamp).toLocaleTimeString([], { hour12: false })}
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
