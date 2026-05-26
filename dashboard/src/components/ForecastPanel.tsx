import React from "react";
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid } from "recharts";
import { TrendingDown, Clock, Cpu } from "lucide-react";

interface ForecastPanelProps {
  predictionHistory: any[];
  aiPrediction: any | null;
}

export const ForecastPanel: React.FC<ForecastPanelProps> = ({
  predictionHistory,
  aiPrediction,
}) => {
  // Format historical predictions for Recharts
  const chartData = predictionHistory.map((frame) => {
    const ts = new Date(frame.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    return {
      time: ts,
      actual: frame.actual_bus5_voltage || 1.0,
      predicted: frame.predicted_bus5_voltage || 1.0,
    };
  });

  const getRiskStyle = (risk: string) => {
    switch (risk) {
      case "CRITICAL":
        return "bg-red-500/15 border-red-500 text-red-400 animate-pulse font-extrabold scada-glow-red";
      case "HIGH":
        return "bg-orange-500/15 border-orange-500 text-orange-400 font-bold";
      case "MEDIUM":
        return "bg-yellow-500/15 border-yellow-500 text-yellow-400 font-semibold";
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

  const hasData = aiPrediction !== null && chartData.length > 0;

  return (
    <div className="bg-scada-panel border border-scada-border rounded-lg p-4 h-[300px] flex flex-col justify-between overflow-hidden">
      {/* Header Panel */}
      <div className="flex justify-between items-center mb-2 border-b border-scada-border/40 pb-1.5 shrink-0">
        <h2 className="text-sm font-semibold tracking-wider text-scada-dimText uppercase flex items-center gap-1.5">
          <Cpu size={16} className={hasData && aiPrediction.predicted_instability ? "text-red-500 animate-bounce" : "text-cyan-500"} />
          AI Voltage Forecast (Bus 5)
        </h2>
        <div className="flex items-center gap-1.5 font-mono text-[9px] text-scada-dimText">
          <Clock size={10} />
          <span>Horizon: 10s</span>
        </div>
      </div>

      {/* Main Panel Content */}
      {!hasData ? (
        <div className="flex-1 flex flex-col items-center justify-center gap-2 font-mono text-xs text-scada-dimText italic">
          <div className="animate-spin w-4 h-4 border-2 border-cyan-500 border-t-transparent rounded-full"></div>
          <span>Inference buffer warming up... Awaiting MQTT cycles...</span>
        </div>
      ) : (
        <div className="flex-1 grid grid-cols-1 md:grid-cols-3 gap-4 overflow-hidden">
          {/* Trend Chart (2/3 width) */}
          <div className="md:col-span-2 h-[210px] flex flex-col justify-between">
            <p className="text-[9px] text-center text-scada-dimText mb-1 font-semibold uppercase tracking-wider font-mono">
              Actual (Cyan) vs Predicted (Amber) Voltage (p.u.)
            </p>
            <div className="flex-1">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#24314A" />
                  <XAxis dataKey="time" stroke="#9CA3AF" fontSize={9} tickLine={false} />
                  <YAxis stroke="#9CA3AF" fontSize={9} domain={[0.6, 1.2]} tickCount={7} />
                  <Tooltip
                    contentStyle={{ backgroundColor: "#0B0F19", borderColor: "#24314A" }}
                    labelStyle={{ color: "#E5E7EB" }}
                  />
                  <Line
                    type="monotone"
                    dataKey="actual"
                    stroke="#06B6D4"
                    strokeWidth={2}
                    dot={false}
                    isAnimationActive={false}
                  />
                  <Line
                    type="monotone"
                    dataKey="predicted"
                    stroke="#F59E0B"
                    strokeWidth={2}
                    dot={false}
                    isAnimationActive={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Sidebar Metrics (1/3 width) */}
          <div className="flex flex-col justify-between border-l border-scada-border/30 pl-3 font-mono text-[9px] space-y-2.5">
            {/* Risk Indicator */}
            <div className="flex flex-col">
              <span className="text-scada-dimText uppercase text-[8px]">Instability Risk:</span>
              <span className={`mt-0.5 px-2 py-0.5 border rounded text-[9px] uppercase tracking-widest text-center ${getRiskStyle(aiPrediction?.instability_risk ?? "LOW")}`}>
                {aiPrediction?.instability_risk ?? "LOW"}
              </span>
            </div>

            {/* Voltage Metrics */}
            <div className="grid grid-cols-2 gap-1.5 bg-black/20 p-1.5 rounded border border-scada-border/20">
              <div className="flex flex-col">
                <span className="text-gray-500 text-[7px] uppercase font-sans font-semibold">Actual</span>
                <span className="text-cyan-400 font-bold font-scada-nums text-[10px]">
                  {typeof aiPrediction?.actual_bus5_voltage === "number" ? aiPrediction.actual_bus5_voltage.toFixed(4) : "1.0000"}
                </span>
              </div>
              <div className="flex flex-col">
                <span className="text-gray-500 text-[7px] uppercase font-sans font-semibold">Forecast</span>
                <span className="text-amber-400 font-bold font-scada-nums text-[10px]">
                  {typeof aiPrediction?.predicted_bus5_voltage === "number" ? aiPrediction.predicted_bus5_voltage.toFixed(4) : "1.0000"}
                </span>
              </div>
            </div>

            {/* Error Delta */}
            <div className="flex justify-between items-center border-t border-scada-border/20 pt-1.5">
              <span className="text-scada-dimText uppercase flex items-center gap-1">
                <TrendingDown size={10} /> Prediction Δ:
              </span>
              <span className={`font-bold font-scada-nums text-[10px] ${getDeltaColor(aiPrediction?.prediction_delta ?? 0.0)}`}>
                {aiPrediction?.prediction_delta >= 0 ? "+" : ""}{typeof aiPrediction?.prediction_delta === "number" ? aiPrediction.prediction_delta.toFixed(4) : "0.0000"}
              </span>
            </div>

            {/* Confidence Gauge */}
            <div>
              <div className="flex justify-between text-scada-dimText uppercase mb-0.5 text-[8px]">
                <span>AI Confidence:</span>
                <span className="text-white font-bold font-scada-nums text-[9px]">
                  {Math.round((aiPrediction?.confidence ?? 1.0) * 100)}%
                </span>
              </div>
              <div className="w-full bg-scada-bg h-1 rounded-full overflow-hidden border border-scada-border/30">
                <div 
                  className={`h-full transition-all duration-300 ${
                    (aiPrediction?.confidence ?? 1.0) >= 0.85 ? "bg-scada-nominal" :
                    (aiPrediction?.confidence ?? 1.0) >= 0.70 ? "bg-yellow-500" :
                    "bg-red-500"
                  }`} 
                  style={{ width: `${(aiPrediction?.confidence ?? 1.0) * 100}%` }}
                ></div>
              </div>
            </div>

            {/* Timestamp */}
            <div className="text-[7px] text-gray-500 flex justify-between items-center border-t border-scada-border/10 pt-1">
              <span>UPDATED:</span>
              <span>{new Date(aiPrediction?.timestamp ?? Date.now()).toLocaleTimeString([], { hour12: false })}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
