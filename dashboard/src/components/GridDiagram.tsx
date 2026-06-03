import React, { useState } from "react";
import { Activity, ShieldAlert, AlertTriangle } from "lucide-react";

interface GridDiagramProps {
  telemetry: any;
  onToggleBreaker: (lineId: string) => void;
  attackStatus: any;
  flisrState: string;
  flisrIsolated: string[];
  flisrReconfigured: string[];
  flisrTripped: string[];
}

export const GridDiagram: React.FC<GridDiagramProps> = ({
  telemetry,
  onToggleBreaker,
  attackStatus,
  flisrState,
  flisrIsolated,
  flisrReconfigured,
  flisrTripped: _flisrTripped
}) => {
  const [hoveredEl, setHoveredEl] = useState<{ type: "bus" | "line"; id: string; data: any } | null>(null);

  const state = telemetry?.state || {};
  const buses = state.buses || {};
  const lines = state.lines || {};
  const breakers = state.breakers || {};

  const activeAttack = attackStatus?.active_attack || null;
  const compromisedNodes = attackStatus?.compromised_nodes || {};

  // Coordinates mapping for standard IEEE 9-bus
  const busCoords: Record<string, { x: number; y: number; label: string; name: string }> = {
    "Bus_1": { x: 150, y: 60, label: "G1", name: "Gen 1 Bus" },
    "Bus_4": { x: 150, y: 160, label: "B4", name: "Junction Bus 4" },
    "Bus_5": { x: 150, y: 310, label: "L5", name: "Load Bus 5" },
    "Bus_6": { x: 400, y: 310, label: "L6", name: "Load Bus 6" },
    "Bus_7": { x: 650, y: 310, label: "G2 Node", name: "Gen 2 Bus 7" },
    "Bus_2": { x: 650, y: 410, label: "G2", name: "Gen 2 Bus" },
    "Bus_8": { x: 650, y: 160, label: "L8", name: "Load Bus 8" },
    "Bus_9": { x: 400, y: 160, label: "G3 Node", name: "Gen 3 Bus 9" },
    "Bus_3": { x: 400, y: 60, label: "G3", name: "Gen 3 Bus" },
  };

  const lineMappings = [
    { id: "L1_4", from: "Bus_1", to: "Bus_4", textPos: { x: 110, y: 110 } },
    { id: "L2_7", from: "Bus_2", to: "Bus_7", textPos: { x: 690, y: 360 } },
    { id: "L3_9", from: "Bus_3", to: "Bus_9", textPos: { x: 440, y: 110 } },
    { id: "L4_5", from: "Bus_4", to: "Bus_5", textPos: { x: 110, y: 235 } },
    { id: "L4_9", from: "Bus_4", to: "Bus_9", textPos: { x: 275, y: 140 } },
    { id: "L5_6", from: "Bus_5", to: "Bus_6", textPos: { x: 275, y: 290 } },
    { id: "L6_7", from: "Bus_6", to: "Bus_7", textPos: { x: 525, y: 290 } },
    { id: "L7_8", from: "Bus_7", to: "Bus_8", textPos: { x: 690, y: 235 } },
    { id: "L8_9", from: "Bus_8", to: "Bus_9", textPos: { x: 525, y: 140 } },
  ];

  const getBusColorClass = (v: number, busId: string) => {
    // Check if compromised under scenario/attack
    if (compromisedNodes[busId]) {
      const type = compromisedNodes[busId].type;
      if (type === "DOS") {
        return "stroke-slate-600 opacity-60 animate-pulse";
      }
      if (type === "SENSOR_SPOOFING") {
        return "stroke-amber-500 animate-pulse";
      }
      return "attack-targeted-node stroke-[#EF4444]";
    }
    
    if (v < 0.2) return "stroke-slate-700 opacity-30"; // Faded gray-out style for islanded zones
    if (v < 0.90) return "stroke-scada-warning";
    return "stroke-scada-nominal";
  };

  const getBusTextClass = (v: number, busId: string) => {
    if (compromisedNodes[busId]) {
      const type = compromisedNodes[busId].type;
      if (type === "DOS") return "text-slate-500 font-mono";
      if (type === "SENSOR_SPOOFING") return "text-amber-500 font-scada-nums animate-pulse";
      return "text-red-500 font-scada-nums animate-pulse";
    }
    if (v < 0.2) return "text-slate-600 opacity-60 font-mono";
    if (v < 0.90) return "text-scada-warning font-scada-nums";
    return "text-scada-nominal font-scada-nums";
  };

  return (
    <div className="relative bg-scada-panel border border-scada-border rounded-lg p-4 overflow-hidden h-[540px] flex flex-col justify-between shadow-2xl">
      {/* Top Banner */}
      <div className="flex justify-between items-center border-b border-scada-border/40 pb-2">
        <h2 className="text-xs font-bold tracking-wider text-scada-dimText uppercase flex items-center gap-1.5">
          <Activity size={14} className="text-scada-nominal animate-pulse" />
          Interactive IEEE 9-Bus Synchrophasor Map
        </h2>
        {activeAttack && (
          <div className="bg-red-500/10 border border-red-500/30 text-scada-trip text-[10px] px-2 py-0.5 rounded font-mono font-bold animate-pulse flex items-center gap-1">
            <ShieldAlert size={12} /> {activeAttack === "SCENARIO" ? `SCENARIO: ${attackStatus.active_scenario_name}` : `${activeAttack} ATTACK ACTIVE`}
          </div>
        )}
      </div>

      {/* SVG Canvas Area */}
      <div className="flex-1 relative flex items-center justify-center bg-black/20 rounded-md my-2 border border-scada-border/20">
        <svg viewBox="50 15 700 420" className="w-full h-full max-h-[440px]">
          <defs>
            <linearGradient id="neon-green" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#10B981" stopOpacity="0.2" />
              <stop offset="100%" stopColor="#10B981" stopOpacity="0" />
            </linearGradient>
          </defs>

          {/* Draw Transmission Lines */}
          {lineMappings.map((line) => {
            const start = busCoords[line.from];
            const end = busCoords[line.to];
            const ldata = lines[line.id] || {};
            const isClosed = breakers[line.id] === "CLOSED";
            const pFlow = ldata.P_mw || 0;
            
            // Check terminal bus voltages to determine de-energized/islanded status
            const vFrom = buses[line.from]?.voltage_pu || 0.0;
            const vTo = buses[line.to]?.voltage_pu || 0.0;
            const isDeEnergized = !isClosed || (vFrom < 0.2 && vTo < 0.2);

            // Capacity checks
            const loading = ldata.capacity_pct || 0.0;
            const isOverloaded = isClosed && loading > 100;
            const isWarningOverload = isClosed && loading > 80 && loading <= 100;

            // Check if isolated by FLISR
            const isIsolatedByFlisr = flisrIsolated.includes(line.id);
            
            // Check line compromises
            const comp = compromisedNodes[line.id];
            const isCompromised = !!comp;
            
            // Reconfigured Tie Line highlighting (uses active props and fallback)
            const isHealedTie = flisrReconfigured.includes(line.id) || (line.id === "L7_8" && isClosed && flisrState === "RESTORED");

            // Determine flow direction and animation class
            let flowClass = "";
            if (isClosed && Math.abs(pFlow) > 1.0) {
              flowClass = pFlow > 0 ? "flow-active-forward" : "flow-active-reverse";
            }

            return (
              <g key={line.id}>
                {/* Secondary thick background hit box */}
                <line
                  x1={start.x}
                  y1={start.y}
                  x2={end.x}
                  y2={end.y}
                  stroke="transparent"
                  strokeWidth={16}
                  className="cursor-pointer"
                  onMouseEnter={() => setHoveredEl({ type: "line", id: line.id, data: ldata })}
                  onMouseLeave={() => setHoveredEl(null)}
                />
                
                {/* Static line backing */}
                <line
                  x1={start.x}
                  y1={start.y}
                  x2={end.x}
                  y2={end.y}
                  stroke={
                    isCompromised
                      ? comp.type === "DOS" ? "#334155" : "#EF4444"
                      : isIsolatedByFlisr
                      ? "#EF4444" // FLISR Isolated segment
                      : isDeEnergized
                      ? "#374151" // De-energized or open line
                      : isOverloaded
                      ? "#EF4444"
                      : isWarningOverload
                      ? "#D97706" // Amber warning overload
                      : isHealedTie
                      ? "#059669"
                      : "#1F2937"
                  }
                  strokeWidth={isCompromised ? 5 : isHealedTie ? 4.5 : 3.5}
                  strokeDasharray={isIsolatedByFlisr ? "4,4" : isDeEnergized && !isClosed ? "3,3" : undefined}
                  opacity={isDeEnergized ? 0.35 : 1}
                  className={isCompromised && comp.type !== "DOS" ? "faulted-line" : ""}
                />

                {/* Animated Power Flow Path */}
                {isClosed && !isDeEnergized && !isCompromised && !isIsolatedByFlisr && (
                  <line
                    x1={start.x}
                    y1={start.y}
                    x2={end.x}
                    y2={end.y}
                    stroke={
                      isOverloaded 
                        ? "#EF4444" 
                        : isWarningOverload
                        ? "#F59E0B"
                        : isHealedTie 
                        ? "#10B981" 
                        : "#3B82F6"
                    }
                    strokeWidth={isOverloaded ? 2.5 : isWarningOverload ? 2.2 : 2}
                    className={
                      isHealedTie 
                        ? "propagate-healing" 
                        : isOverloaded
                        ? `${flowClass} animate-pulse`
                        : flowClass
                    }
                    pointerEvents="none"
                  />
                )}
              </g>
            );
          })}

          {/* Draw Breakers & Ripple rings */}
          {lineMappings.map((line) => {
            const start = busCoords[line.from];
            const end = busCoords[line.to];
            const isClosed = breakers[line.id] === "CLOSED";
            
            const mx = (start.x + end.x) / 2;
            const my = (start.y + end.y) / 2;

            // Check if breaker is compromised or jammed (e.g. BREAKER_MANIPULATION or DOS)
            const comp = compromisedNodes[line.id];
            const isBreakerManipulated = comp && comp.type === "BREAKER_MANIPULATION";
            const isJammed = comp && comp.type === "DOS";

            return (
              <g 
                key={`brk-${line.id}`} 
                className="cursor-pointer group"
                onClick={() => onToggleBreaker(line.id)}
              >
                {/* Warning Ripple Rings */}
                {(!isClosed || isBreakerManipulated) && (
                  <circle
                    cx={mx}
                    cy={my}
                    r={isBreakerManipulated ? 22 : 18}
                    fill="none"
                    stroke={isBreakerManipulated ? "#F59E0B" : "#EF4444"}
                    className="trip-ripple"
                    pointerEvents="none"
                  />
                )}

                {/* Hover circle */}
                <circle cx={mx} cy={my} r={16} fill="rgba(0,0,0,0.5)" className="opacity-0 group-hover:opacity-100 transition-opacity" />
                
                {/* Breaker Square */}
                <rect
                  x={mx - 7}
                  y={my - 7}
                  width={14}
                  height={14}
                  fill={isJammed ? "#475569" : isClosed ? "#10B981" : "#EF4444"}
                  stroke={isBreakerManipulated ? "#F59E0B" : "#111827"}
                  strokeWidth={isBreakerManipulated ? 2.5 : 1.5}
                  className={isBreakerManipulated ? "animate-pulse" : "transition-colors duration-300"}
                />
                
                {isJammed ? (
                  <path d={`M ${mx - 4} ${my - 4} L ${mx + 4} ${my + 4} M ${mx + 4} ${my - 4} L ${mx - 4} ${my + 4}`} stroke="#FFFFFF" strokeWidth="1.5" />
                ) : (
                  <text x={mx} y={my + 3.5} textAnchor="middle" fill="#FFFFFF" fontSize="9" fontWeight="bold" className="pointer-events-none select-none font-mono">
                    {isClosed ? "C" : "O"}
                  </text>
                )}
              </g>
            );
          })}

          {/* Draw Buses */}
          {Object.entries(busCoords).map(([bid, coord]) => {
            const busData = buses[bid] || {};
            const v = busData.voltage_pu || 0.0;
            const busColorClass = getBusColorClass(v, bid);
            
            const length = 55;
            const x1 = coord.x - length / 2;
            const x2 = coord.x + length / 2;

            const isComp = !!compromisedNodes[bid];
            const compType = compromisedNodes[bid]?.type;

            return (
              <g 
                key={bid} 
                className="cursor-pointer"
                onMouseEnter={() => setHoveredEl({ type: "bus", id: bid, data: busData })}
                onMouseLeave={() => setHoveredEl(null)}
              >
                {/* Thick Bus Bar */}
                <line
                  x1={x1}
                  y1={coord.y}
                  x2={x2}
                  y2={coord.y}
                  strokeWidth={6.5}
                  className={`${busColorClass} transition-all duration-300`}
                />
                
                {/* Label */}
                <text 
                  x={coord.x} 
                  y={coord.y - 12} 
                  textAnchor="middle" 
                  fill={isComp ? "#EF4444" : "#9CA3AF"}
                  fontSize="9.5" 
                  fontWeight="bold"
                  className="tracking-wider"
                >
                  {bid.replace("Bus_", "BUS ")}
                </text>

                {/* Voltage Tag (Always Visible) */}
                <text 
                  x={coord.x} 
                  y={coord.y + 18} 
                  textAnchor="middle" 
                  fontSize="10" 
                  className={`${getBusTextClass(v, bid)} font-semibold`}
                >
                  {isComp && compType === "DOS" ? "COMM LOSS" : `${(v ?? 0).toFixed(3)} pu`}
                </text>

                {/* Small indicator icons next to compromised buses */}
                {isComp && (
                  <g transform={`translate(${coord.x + 32}, ${coord.y - 6})`}>
                    <circle cx="0" cy="0" r="6" fill="#7F1D1D" stroke="#EF4444" strokeWidth="1" />
                    <text x="0" y="2.5" textAnchor="middle" fill="#EF4444" fontSize="7" fontWeight="bold">!</text>
                  </g>
                )}
              </g>
            );
          })}

          {/* Static Loading Labels next to Lines (Always Visible) */}
          {lineMappings.map((line) => {
            const ldata = lines[line.id] || {};
            const isClosed = breakers[line.id] === "CLOSED";
            const loading = ldata.capacity_pct || 0.0;

            const isComp = !!compromisedNodes[line.id];
            const compType = compromisedNodes[line.id]?.type;

            if (!isClosed) return null;

            return (
              <g key={`lbl-${line.id}`}>
                <rect
                  x={line.textPos.x - 22}
                  y={line.textPos.y - 8}
                  width={44}
                  height={13}
                  rx={2}
                  fill="#0B0F19"
                  stroke={isComp ? "#EF4444" : "#24314A"}
                  strokeWidth={1}
                  opacity={0.8}
                />
                <text
                  x={line.textPos.x}
                  y={line.textPos.y + 1}
                  textAnchor="middle"
                  fill={isComp && compType === "DOS" ? "#475569" : loading > 85 ? "#EF4444" : loading > 60 ? "#F59E0B" : "#9CA3AF"}
                  fontSize="8.5"
                  fontWeight="semibold"
                  className="font-scada-nums"
                >
                  {isComp && compType === "DOS" ? "N/A" : `${(loading ?? 0).toFixed(0)}%`}
                </text>
              </g>
            );
          })}

          {/* Draw Generator Icons */}
          {Object.entries(busCoords).map(([bid, coord]) => {
            const busData = buses[bid] || {};
            if (!busData.is_gen) return null;

            const cy = coord.y - 36;
            const cx = coord.x;

            return (
              <g key={`gen-${bid}`} className="pointer-events-none">
                <circle cx={cx} cy={cy} r={11} fill="#111827" stroke="#10B981" strokeWidth={2.5} />
                <path d={`M ${cx - 5} ${cy} Q ${cx - 2.5} ${cy - 4} ${cx} ${cy} T ${cx + 5} ${cy}`} fill="none" stroke="#10B981" strokeWidth={2} />
                <line x1={cx} y1={coord.y - 4} x2={cx} y2={cy + 11} stroke="#10B981" strokeWidth={2.5} />
              </g>
            );
          })}

          {/* Draw Load Indicator Arrows */}
          {Object.entries(busCoords).map(([bid, coord]) => {
            const busData = buses[bid] || {};
            if (!busData.is_load) return null;

            const ly = coord.y + 24;
            const lx = coord.x;

            return (
              <g key={`load-${bid}`} className="pointer-events-none">
                <path
                  d={`M ${lx} ${ly} L ${lx} ${ly + 10}`}
                  stroke="#3B82F6"
                  strokeWidth={2}
                  markerEnd="url(#arrow)"
                />
              </g>
            );
          })}
        </svg>
      </div>

      {/* Floating Status card */}
      <div className="bg-scada-bg/85 border border-scada-border rounded p-2 text-[10px] text-scada-dimText flex justify-between items-center backdrop-blur-sm">
        <span className="flex items-center gap-1.5">
          <AlertTriangle size={12} className="text-scada-warning" />
          Click breakers to simulate switch trips. DoS-affected links block gateway control.
        </span>
        {hoveredEl && (
          <span className="font-mono text-white font-semibold">
            {hoveredEl.type === "bus"
              ? `${hoveredEl.id.replace("Bus_", "BUS ")}: P=${(hoveredEl.data?.P_mw ?? 0).toFixed(1)}MW Q=${(hoveredEl.data?.Q_mvar ?? 0).toFixed(1)}MVAR`
              : `LINE ${hoveredEl.id.replace("L", "").replace("_", "-")}: P=${(hoveredEl.data?.P_mw ?? 0).toFixed(1)}MW I=${(hoveredEl.data?.current_amp ?? 0).toFixed(1)}A`}
          </span>
        )}
      </div>
    </div>
  );
};
