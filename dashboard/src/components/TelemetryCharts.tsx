import React, { useState } from "react";
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid } from "recharts";

interface TelemetryChartsProps {
  history: any[];
}

export const TelemetryCharts: React.FC<TelemetryChartsProps> = ({ history }) => {
  const [selectedBus, setSelectedBus] = useState<string>("Bus_5");
  const [selectedLine, setSelectedLine] = useState<string>("L5_6");

  // Format historical telemetry for Recharts
  const chartData = history.map((frame) => {
    const state = frame.state || {};
    const buses = state.buses || {};
    const lines = state.lines || {};
    const ts = new Date(frame.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });

    return {
      time: ts,
      busVoltage: buses[selectedBus]?.voltage_pu || 0,
      lineCurrent: lines[selectedLine]?.current_pu || 0,
      lineCapacity: lines[selectedLine]?.capacity_pct || 0
    };
  });

  return (
    <div className="bg-scada-panel border border-scada-border rounded-lg p-4 h-[300px] flex flex-col justify-between">
      <div className="flex justify-between items-center mb-2">
        <h2 className="text-sm font-semibold tracking-wider text-scada-dimText uppercase">
          Real-Time Telemetry Trends
        </h2>
        <div className="flex gap-4">
          {/* Bus Selector */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-scada-dimText">Bus:</span>
            <select
              value={selectedBus}
              onChange={(e) => setSelectedBus(e.target.value)}
              className="bg-scada-bg border border-scada-border rounded px-2 py-1 text-xs text-white focus:outline-none"
            >
              {Array.from({ length: 9 }, (_, i) => `Bus_${i + 1}`).map((b) => (
                <option key={b} value={b}>{b.replace("_", " ")}</option>
              ))}
            </select>
          </div>

          {/* Line Selector */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-scada-dimText">Line:</span>
            <select
              value={selectedLine}
              onChange={(e) => setSelectedLine(e.target.value)}
              className="bg-scada-bg border border-scada-border rounded px-2 py-1 text-xs text-white focus:outline-none"
            >
              {["L1_4", "L2_7", "L3_9", "L4_5", "L4_9", "L5_6", "L6_7", "L7_8", "L8_9"].map((l) => (
                <option key={l} value={l}>LINE {l.replace("L", "").replace("_", "-")}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Recharts Layout */}
      <div className="flex-1 grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Voltage Chart */}
        <div className="h-[210px]">
          <p className="text-xs text-center text-scada-dimText mb-1 font-semibold">
            {selectedBus.replace("_", " ")} Voltage (p.u.)
          </p>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#24314A" />
              <XAxis dataKey="time" stroke="#9CA3AF" fontSize={10} tickLine={false} />
              <YAxis stroke="#9CA3AF" fontSize={10} domain={[0.0, 1.2]} tickCount={6} />
              <Tooltip
                contentStyle={{ backgroundColor: "#0B0F19", borderColor: "#24314A" }}
                labelStyle={{ color: "#E5E7EB" }}
              />
              <Line
                type="monotone"
                dataKey="busVoltage"
                stroke="#10B981"
                strokeWidth={2}
                dot={false}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Current Loading Chart */}
        <div className="h-[210px]">
          <p className="text-xs text-center text-scada-dimText mb-1 font-semibold">
            Line {selectedLine.replace("L", "").replace("_", "-")} Loading (%)
          </p>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#24314A" />
              <XAxis dataKey="time" stroke="#9CA3AF" fontSize={10} tickLine={false} />
              <YAxis stroke="#9CA3AF" fontSize={10} domain={[0, 120]} tickCount={6} />
              <Tooltip
                contentStyle={{ backgroundColor: "#0B0F19", borderColor: "#24314A" }}
                labelStyle={{ color: "#E5E7EB" }}
              />
              <Line
                type="monotone"
                dataKey="lineCapacity"
                stroke="#3B82F6"
                strokeWidth={2}
                dot={false}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
};
