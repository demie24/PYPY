import React, { useState, useEffect } from "react";
import { Activity, ShieldAlert, AlertTriangle, ZoomIn, ZoomOut, RotateCcw, Maximize } from "lucide-react";

interface GridDiagramProps {
  telemetry: any;
  onToggleBreaker: (lineId: string) => void;
  attackStatus: any;
  flisrState: string;
  flisrIsolated: string[];
  flisrReconfigured: string[];
  flisrTripped: string[];
  selectedGrid?: string;
}

// Realistic New England IEEE 39-Bus SCADA coordinates mapping
const defaultBusCoords: Record<string, { x: number; y: number; label: string; name: string }> = {
  "Bus_1": { x: 1359.1, y: 752.8, label: "B1", name: "Bus 1" },
  "Bus_2": { x: 1161.0, y: 705.4, label: "B2", name: "Bus 2" },
  "Bus_3": { x: 1164.5, y: 592.2, label: "B3", name: "Bus 3" },
  "Bus_4": { x: 1293.6, y: 503.2, label: "B4", name: "Bus 4" },
  "Bus_5": { x: 1520.0, y: 506.2, label: "B5", name: "Bus 5" },
  "Bus_6": { x: 1695.0, y: 434.6, label: "B6", name: "Bus 6" },
  "Bus_7": { x: 1832.1, y: 514.6, label: "B7", name: "Bus 7" },
  "Bus_8": { x: 1678.2, y: 581.4, label: "B8", name: "Bus 8" },
  "Bus_9": { x: 1703.0, y: 685.2, label: "B9", name: "Bus 9" },
  "Bus_10": { x: 1504.9, y: 253.9, label: "B10", name: "Bus 10" },
  "Bus_11": { x: 1668.1, y: 328.8, label: "B11", name: "Bus 11" },
  "Bus_12": { x: 1494.0, y: 312.7, label: "B12", name: "Bus 12" },
  "Bus_13": { x: 1313.7, y: 310.9, label: "B13", name: "Bus 13" },
  "Bus_14": { x: 1185.6, y: 400.5, label: "B14", name: "Bus 14" },
  "Bus_15": { x: 963.4, y: 385.7, label: "B15", name: "Bus 15" },
  "Bus_16": { x: 740.4, y: 410.0, label: "B16", name: "Bus 16" },
  "Bus_17": { x: 772.4, y: 519.8, label: "B17", name: "Bus 17" },
  "Bus_18": { x: 968.9, y: 552.8, label: "B18", name: "Bus 18" },
  "Bus_19": { x: 516.8, y: 431.3, label: "B19", name: "Bus 19" },
  "Bus_20": { x: 308.2, y: 465.8, label: "B20", name: "Bus 20" },
  "Bus_21": { x: 752.0, y: 303.1, label: "B21", name: "Bus 21" },
  "Bus_22": { x: 678.0, y: 200.9, label: "B22", name: "Bus 22" },
  "Bus_23": { x: 516.5, y: 237.6, label: "B23", name: "Bus 23" },
  "Bus_24": { x: 620.7, y: 333.2, label: "B24", name: "Bus 24" },
  "Bus_25": { x: 964.2, y: 758.2, label: "B25", name: "Bus 25" },
  "Bus_26": { x: 747.0, y: 730.4, label: "B26", name: "Bus 26" },
  "Bus_27": { x: 697.4, y: 623.2, label: "B27", name: "Bus 27" },
  "Bus_28": { x: 560.8, y: 763.6, label: "B28", name: "Bus 28" },
  "Bus_29": { x: 638.3, y: 822.9, label: "B29", name: "Bus 29" },
  "Bus_30": { x: 1210.6, y: 802.5, label: "G30", name: "Gen 30 (Slack)" },
  "Bus_31": { x: 1900.0, y: 405.2, label: "G31", name: "Gen 31" },
  "Bus_32": { x: 1584.6, y: 162.2, label: "G32", name: "Gen 32" },
  "Bus_33": { x: 350.3, y: 374.2, label: "G33", name: "Gen 33" },
  "Bus_34": { x: 100.0, y: 461.2, label: "G34", name: "Gen 34" },
  "Bus_35": { x: 655.2, y: 100.0, label: "G35", name: "Gen 35" },
  "Bus_36": { x: 357.4, y: 172.8, label: "G36", name: "Gen 36" },
  "Bus_37": { x: 979.4, y: 864.7, label: "G37", name: "Gen 37" },
  "Bus_38": { x: 509.4, y: 900.0, label: "G38", name: "Gen 38" },
  "Bus_39": { x: 1566.5, y: 763.0, label: "G39", name: "Gen 39" }
};

export const GridDiagram: React.FC<GridDiagramProps> = ({
  telemetry,
  onToggleBreaker,
  attackStatus,
  flisrState,
  flisrIsolated,
  flisrReconfigured,
  flisrTripped: _flisrTripped,
  selectedGrid
}) => {
  const [topology, setTopology] = useState<any>(null);
  const [hoveredEl, setHoveredEl] = useState<{ type: "bus" | "line"; id: string; data: any } | null>(null);

  // Zoom & Pan State
  const [zoom, setZoom] = useState<number>(1.0);
  const [panX, setPanX] = useState<number>(0);
  const [panY, setPanY] = useState<number>(0);
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const [dragStart, setDragStart] = useState<{ x: number; y: number }>({ x: 0, y: 0 });

  const gridName = selectedGrid || telemetry?.grid_name || "ieee39";

  // Fetch dynamic topology on mount or grid name change
  useEffect(() => {
    const host = window.location.hostname || "localhost";
    fetch(`http://${host}:8000/api/telemetry/topology?grid_name=${gridName}`)
      .then((res) => res.json())
      .then((data) => setTopology(data))
      .catch((err) => {
        console.error("Failed to fetch topology:", err);
      });
  }, [gridName]);

  const state = telemetry?.state || {};
  const buses = state.buses || {};
  const lines = state.lines || {};
  const breakers = state.breakers || {};

  const activeAttack = attackStatus?.active_attack || null;
  const compromisedNodes = attackStatus?.compromised_nodes || {};

  const activeBuses = topology?.buses 
    ? Object.keys(topology.buses) 
    : Array.from({ length: 39 }, (_, i) => `Bus_${i+1}`);

  const activeLines = topology?.lines || [];

  // Compute raw coords for all active buses
  const rawCoords = activeBuses.reduce((acc, bid) => {
    const isIeee39 = gridName === "ieee39";
    let raw = isIeee39 ? defaultBusCoords[bid] : null;
    
    if (!raw) {
      const idx = parseInt(bid.replace("Bus_", ""), 10) || 0;
      const total = activeBuses.length;
      
      // Concentric rings layout to prevent overlaps in high-density grids
      const center = { x: 1000, y: 500 };
      let rings: { radius: number; count: number }[] = [];
      if (total <= 14) {
        rings = [
          { radius: 150, count: 4 },
          { radius: 320, count: 10 }
        ];
      } else if (total <= 57) {
        rings = [
          { radius: 120, count: 6 },
          { radius: 240, count: 14 },
          { radius: 360, count: 18 },
          { radius: 480, count: 19 }
        ];
      } else {
        // IEEE 118 or larger
        rings = [
          { radius: 80, count: 6 },
          { radius: 180, count: 12 },
          { radius: 280, count: 18 },
          { radius: 380, count: 24 },
          { radius: 480, count: 28 },
          { radius: 580, count: 30 }
        ];
      }
      
      // Find ring matching the index
      let ringIndex = 0;
      let accum = 0;
      for (let r = 0; r < rings.length; r++) {
        if (idx - 1 < accum + rings[r].count) {
          ringIndex = r;
          break;
        }
        accum += rings[r].count;
        ringIndex = r;
      }
      
      const currentRing = rings[ringIndex];
      const indexInRing = idx - 1 - accum;
      const angle = (indexInRing / (currentRing?.count || 1)) * 2 * Math.PI;
      
      const x = center.x + Math.cos(angle) * (currentRing?.radius || 300);
      const y = center.y + Math.sin(angle) * (currentRing?.radius || 300);
      
      raw = {
        x: isNaN(x) ? 1000 : x,
        y: isNaN(y) ? 500 : y,
        label: `B${idx}`,
        name: `Bus ${idx}`
      };
    }
    acc[bid] = raw;
    return acc;
  }, {} as Record<string, { x: number; y: number; label: string; name: string }>);

  // Calculate bounding box of raw coords to dynamically fit & center the topology
  const xs = Object.values(rawCoords).map(c => c.x);
  const ys = Object.values(rawCoords).map(c => c.y);
  const minX = xs.length > 0 ? Math.min(...xs) : 100;
  const maxX = xs.length > 0 ? Math.max(...xs) : 1900;
  const minY = ys.length > 0 ? Math.min(...ys) : 100;
  const maxY = ys.length > 0 ? Math.max(...ys) : 900;

  const dx = maxX - minX || 1;
  const dy = maxY - minY || 1;

  // Viewport dimensions
  const V_WIDTH = 2000;
  const V_HEIGHT = 1000;
  const MARGIN_X = 140; // horizontal margins to prevent label clipping
  const MARGIN_Y = 140; // vertical margins to accommodate generator/load badges

  const targetW = V_WIDTH - 2 * MARGIN_X;
  const targetH = V_HEIGHT - 2 * MARGIN_Y;

  // Maintain aspect ratio
  const autoScale = Math.min(targetW / dx, targetH / dy);

  // Translation offsets to center inside the target workspace
  const tx = MARGIN_X + (targetW - dx * autoScale) / 2 - minX * autoScale;
  const ty = MARGIN_Y + (targetH - dy * autoScale) / 2 - minY * autoScale;

  const getBusCoord = (busId: string) => {
    const raw = rawCoords[busId];
    if (!raw) {
      return { x: 1000, y: 500, label: "UNK", name: "Unknown" };
    }
    return {
      x: raw.x * autoScale + tx,
      y: raw.y * autoScale + ty,
      label: raw.label,
      name: raw.name
    };
  };

  const getBusColorClass = (v: number, busId: string) => {
    if (compromisedNodes[busId]) {
      const type = compromisedNodes[busId].type;
      if (type === "DOS") {
        return "stroke-slate-600 opacity-60 animate-pulse";
      }
      if (type === "SENSOR_SPOOFING") {
        return "stroke-scada-warning animate-pulse";
      }
      return "attack-targeted-node stroke-scada-trip animate-pulse";
    }
    if (v < 0.2) return "stroke-slate-700 opacity-30"; // Offline
    if (v < 0.90 || v > 1.10) return "stroke-scada-trip animate-pulse"; // Critical
    if (v < 0.95 || v > 1.05) return "stroke-scada-warning"; // Warning
    return "stroke-scada-nominal"; // Normal (Green)
  };

  const getBusTextClass = (v: number, busId: string) => {
    if (compromisedNodes[busId]) {
      const type = compromisedNodes[busId].type;
      if (type === "DOS") return "text-slate-500 font-mono";
      if (type === "SENSOR_SPOOFING") return "text-scada-warning font-scada-nums animate-pulse";
      return "text-scada-trip font-scada-nums animate-pulse";
    }
    if (v < 0.2) return "text-slate-600 opacity-60 font-mono";
    if (v < 0.90 || v > 1.10) return "text-scada-trip font-scada-nums font-bold animate-pulse";
    if (v < 0.95 || v > 1.05) return "text-scada-warning font-scada-nums font-semibold";
    return "text-scada-nominal font-scada-nums";
  };

  // Drag-to-pan handlers
  const handleMouseDown = (e: React.MouseEvent<SVGSVGElement, MouseEvent>) => {
    const target = e.target as SVGElement;
    if (target.tagName === "svg" || target.classList.contains("canvas-bg")) {
      setIsDragging(true);
      setDragStart({ x: e.clientX - panX, y: e.clientY - panY });
    }
  };

  const handleMouseMove = (e: React.MouseEvent<SVGSVGElement, MouseEvent>) => {
    if (isDragging) {
      setPanX(e.clientX - dragStart.x);
      setPanY(e.clientY - dragStart.y);
    }
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  const handleWheel = (e: React.WheelEvent<SVGSVGElement>) => {
    e.preventDefault();
    const zoomFactor = 1.05;
    if (e.deltaY < 0) {
      setZoom((z) => Math.min(2.5, z * zoomFactor));
    } else {
      setZoom((z) => Math.max(0.3, z / zoomFactor));
    }
  };

  const resetView = () => {
    setZoom(1.0);
    setPanX(0);
    setPanY(0);
  };


  return (
    <div className="relative bg-scada-panel border border-scada-border rounded-lg p-4 overflow-hidden h-[540px] flex flex-col justify-between shadow-2xl">
      {/* Top Banner */}
      <div className="flex justify-between items-center border-b border-scada-border/40 pb-2">
        <h2 className="text-xs font-bold tracking-wider text-scada-dimText uppercase flex items-center gap-1.5">
          <Activity size={14} className="text-scada-nominal animate-pulse" />
          Interactive {(telemetry?.grid_name || "ieee39").toUpperCase().replace("IEEE", "IEEE ")} Transmission SCADA Diagram
        </h2>
        
        {/* Navigation & Controls */}
        <div className="flex items-center gap-2">
          <button onClick={() => setZoom(z => Math.min(2.5, z + 0.1))} className="bg-scada-bg hover:bg-scada-border/40 border border-scada-border text-scada-dimText hover:text-white p-1 rounded" title="Zoom In">
            <ZoomIn size={12} />
          </button>
          <button onClick={() => setZoom(z => Math.max(0.3, z - 0.1))} className="bg-scada-bg hover:bg-scada-border/40 border border-scada-border text-scada-dimText hover:text-white p-1 rounded" title="Zoom Out">
            <ZoomOut size={12} />
          </button>
          <button onClick={resetView} className="bg-scada-bg hover:bg-scada-border/40 border border-scada-border text-scada-dimText hover:text-white p-1 rounded" title="Reset View">
            <RotateCcw size={12} />
          </button>
          <button onClick={() => { setZoom(1.0); setPanX(0); setPanY(0); }} className="bg-scada-bg hover:bg-scada-border/40 border border-scada-border text-scada-dimText hover:text-white p-1 rounded" title="Fit to Screen">
            <Maximize size={12} />
          </button>
          {activeAttack && (
            <div className="bg-red-500/10 border border-red-500/30 text-scada-trip text-[10px] px-2 py-0.5 rounded font-mono font-bold animate-pulse flex items-center gap-1">
              <ShieldAlert size={12} /> {activeAttack === "SCENARIO" ? `SCENARIO: ${attackStatus?.active_scenario_name}` : `${activeAttack} ATTACK ACTIVE`}
            </div>
          )}
        </div>
      </div>

      {/* SVG Canvas Area */}
      <div className="flex-1 relative flex items-center justify-center bg-black/20 rounded-md my-2 border border-scada-border/20 overflow-hidden">
        {/* Real-time SCADA Inspector Widget */}
        {hoveredEl && (
          <div className="absolute top-3 left-3 z-10 w-64 bg-scada-panel/95 border border-cyan-500/30 rounded p-2.5 font-mono text-[9px] text-scada-dimText shadow-2xl backdrop-blur-sm animate-fade-in pointer-events-none">
            <div className="flex justify-between items-center border-b border-scada-border/40 pb-1.5 mb-1.5">
              <span className="text-white font-bold tracking-widest text-[10px] uppercase flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-cyan-500 animate-ping"></span>
                {hoveredEl.type === "bus" ? hoveredEl.id.replace("Bus_", "BUS Bar ") : `Segment ${hoveredEl.id.replace("L_", "").replace("_", "-")}`}
              </span>
              <span className="px-1.5 py-0.5 rounded bg-cyan-500/10 text-cyan-400 font-bold uppercase text-[8px]">
                {hoveredEl.type.toUpperCase()}
              </span>
            </div>

            <div className="space-y-1">
              {hoveredEl.type === "bus" ? (
                <>
                  <div className="flex justify-between">
                    <span>Voltage Magnitude:</span>
                    <strong className="text-white">{(hoveredEl.data?.voltage_pu || 1.0).toFixed(4)} pu</strong>
                  </div>
                  <div className="flex justify-between">
                    <span>Absolute Voltage:</span>
                    <strong className="text-cyan-400">{( (hoveredEl.data?.voltage_pu || 1.0) * (gridName === "ieee39" ? 345 : 115) ).toFixed(2)} kV</strong>
                  </div>
                  <div className="flex justify-between">
                    <span>Phase Angle:</span>
                    <strong className="text-white">{( (hoveredEl.data?.angle_rad || 0) * 180 / Math.PI ).toFixed(2)}°</strong>
                  </div>
                  <div className="flex justify-between">
                    <span>Frequency:</span>
                    <strong className="text-white">{(hoveredEl.data?.frequency_hz || 60.0).toFixed(3)} Hz</strong>
                  </div>
                  {hoveredEl.data?.P_mw !== undefined && hoveredEl.data?.P_mw > 0 && (
                    <div className="flex justify-between text-emerald-400">
                      <span>Generator Output:</span>
                      <strong>{hoveredEl.data.P_mw.toFixed(1)} MW</strong>
                    </div>
                  )}
                  {hoveredEl.data?.P_mw === undefined && (
                    <div className="flex justify-between text-blue-400">
                      <span>Load Draw:</span>
                      <strong>{((hoveredEl.data?.active_power || 0) * 100).toFixed(1)} MW</strong>
                    </div>
                  )}
                  <div className="flex justify-between">
                    <span>Substation Status:</span>
                    <span className={compromisedNodes[hoveredEl.id] ? "text-red-400 font-bold" : (hoveredEl.data?.voltage_pu || 1.0) < 0.90 ? "text-yellow-400" : "text-emerald-400"}>
                      {compromisedNodes[hoveredEl.id] ? compromisedNodes[hoveredEl.id].type : (hoveredEl.data?.voltage_pu || 1.0) < 0.90 ? "UNDERVOLT" : "NOMINAL"}
                    </span>
                  </div>
                </>
              ) : (
                <>
                  <div className="flex justify-between">
                    <span>Breaker Status:</span>
                    <strong className={breakers[hoveredEl.id] === "CLOSED" ? "text-emerald-400" : "text-red-400"}>
                      {breakers[hoveredEl.id] || "CLOSED"}
                    </strong>
                  </div>
                  <div className="flex justify-between">
                    <span>Active Power Flow:</span>
                    <strong className="text-white">{(hoveredEl.data?.active_power_flow || 0).toFixed(2)} MW</strong>
                  </div>
                  <div className="flex justify-between">
                    <span>Reactive Power Flow:</span>
                    <strong className="text-white">{(hoveredEl.data?.reactive_power_flow || 0).toFixed(2)} MVAR</strong>
                  </div>
                  <div className="flex justify-between">
                    <span>Line Loading:</span>
                    <strong className={(hoveredEl.data?.loading_percent || 0) > 100 ? "text-red-400 font-extrabold" : (hoveredEl.data?.loading_percent || 0) > 80 ? "text-yellow-400 font-bold" : "text-emerald-400"}>
                      {(hoveredEl.data?.loading_percent || 0).toFixed(1)}%
                    </strong>
                  </div>
                  <div className="flex justify-between">
                    <span>Self-Healing State:</span>
                    <span className={flisrIsolated.includes(hoveredEl.id) ? "text-red-400 font-bold" : flisrReconfigured.includes(hoveredEl.id) ? "text-emerald-400" : "text-gray-500"}>
                      {flisrIsolated.includes(hoveredEl.id) ? "ISOLATED" : flisrReconfigured.includes(hoveredEl.id) ? "RECONFIGURED" : "DEFAULT"}
                    </span>
                  </div>
                </>
              )}
            </div>
          </div>
        )}
        <svg 
          viewBox="0 0 2000 1000"
          className="w-full h-full cursor-grab active:cursor-grabbing"
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
          onWheel={handleWheel}
        >
          <defs>
            <marker
              id="arrow"
              viewBox="0 0 10 10"
              refX="6"
              refY="5"
              markerWidth="6"
              markerHeight="6"
              orient="auto-start-reverse"
            >
              <path d="M 0 2 L 10 5 L 0 8 z" fill="#3B82F6" />
            </marker>
          </defs>
          <rect width="2000" height="1000" fill="transparent" className="canvas-bg" />
          
          <g transform={`translate(${panX}, ${panY}) scale(${zoom})`}>
            
            {/* Regional Grouping Boxes (SCADA Zones) - only for IEEE 39 */}
            {(telemetry?.grid_name === "ieee39" || (!telemetry?.grid_name && activeBuses.length === 39)) && (
              <g opacity={0.85}>
                <rect x={50} y={50} width={540} height={900} rx={10} fill="rgba(16, 185, 129, 0.01)" stroke="rgba(16, 185, 129, 0.12)" strokeWidth={1.5} strokeDasharray="6,4" />
                <text x={320} y={80} textAnchor="middle" fill="#10B981" fontSize="11" fontWeight="bold" opacity={0.5} letterSpacing={2}>WESTERN GENERATION HUB (ZONE 1)</text>

                <rect x={600} y={50} width={645} height={900} rx={10} fill="rgba(59, 130, 246, 0.01)" stroke="rgba(59, 130, 246, 0.12)" strokeWidth={1.5} strokeDasharray="6,4" />
                <text x={922.5} y={80} textAnchor="middle" fill="#3B82F6" fontSize="11" fontWeight="bold" opacity={0.5} letterSpacing={2}>CENTRAL TRANSMISSION GRID (ZONE 2)</text>

                <rect x={1255} y={50} width={695} height={900} rx={10} fill="rgba(139, 92, 246, 0.01)" stroke="rgba(139, 92, 246, 0.12)" strokeWidth={1.5} strokeDasharray="6,4" />
                <text x={1602.5} y={80} textAnchor="middle" fill="#8B5CF6" fontSize="11" fontWeight="bold" opacity={0.5} letterSpacing={2}>EASTERN LOAD ZONE (ZONE 3)</text>
              </g>
            )}

            {/* Draw Transmission Lines & Transformers */}
            {activeLines.map((line: any) => {
              const start = getBusCoord(line.from_bus);
              const end = getBusCoord(line.to_bus);
              const ldata = lines[line.id] || {};
              const isClosed = breakers[line.id] === "CLOSED";
              const pFlow = ldata.active_power_flow || 0;
              
              // Check terminal bus voltages
              const vFrom = buses[line.from_bus]?.voltage_pu || 0.0;
              const vTo = buses[line.to_bus]?.voltage_pu || 0.0;
              const isDeEnergized = !isClosed || (vFrom < 0.2 && vTo < 0.2);

              const loading = ldata.loading_percent || 0.0;
              const isOverloaded = isClosed && loading > 100;
              const isWarningOverload = isClosed && loading > 80 && loading <= 100;

              const isIsolatedByFlisr = flisrIsolated.includes(line.id);
              const comp = compromisedNodes[line.id];
              const isCompromised = !!comp;
              
              const isHealedTie = flisrReconfigured.includes(line.id) || (line.id === "L7_8" && isClosed && flisrState === "RESTORED");

              // Determine flow direction and animation class
              let flowClass = "";
              if (isClosed && Math.abs(pFlow) > 1.0) {
                flowClass = pFlow > 0 ? "flow-active-forward" : "flow-active-reverse";
              }

              // Vector math for transformer rendering
              const dx = end.x - start.x;
              const dy = end.y - start.y;
              const len = Math.sqrt(dx * dx + dy * dy) || 1;
              const ux = dx / len;
              const uy = dy / len;
              const mx = (start.x + end.x) / 2;
              const my = (start.y + end.y) / 2;

              return (
                <g key={line.id}>
                  {/* Thick background hit box */}
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
                  
                  {/* Transformer Overlapping Circles Schematic symbol */}
                  {line.is_trafo ? (
                    <g opacity={isDeEnergized ? 0.35 : 1}>
                      {/* Connection line segments */}
                      <line
                        x1={start.x}
                        y1={start.y}
                        x2={mx - 18 * ux}
                        y2={my - 18 * uy}
                        stroke={isClosed ? "#3b82f6" : "#EF4444"}
                        strokeWidth={2}
                        strokeDasharray={!isClosed ? "3,3" : undefined}
                      />
                      <line
                        x1={mx + 18 * ux}
                        y1={my + 18 * uy}
                        x2={end.x}
                        y2={end.y}
                        stroke={isClosed ? "#3b82f6" : "#EF4444"}
                        strokeWidth={2}
                        strokeDasharray={!isClosed ? "3,3" : undefined}
                      />
                      
                      {/* Overlapping Circles */}
                      <circle cx={mx - 7 * ux} cy={my - 7 * uy} r={11} fill="none" stroke={isClosed ? "#60A5FA" : "#EF4444"} strokeWidth={2} />
                      <circle cx={mx + 7 * ux} cy={my + 7 * uy} r={11} fill="none" stroke={isClosed ? "#60A5FA" : "#EF4444"} strokeWidth={2} />
                      
                      {/* Trafo icon overlay tag */}
                      <text x={mx + 20} y={my + 4} fill="#60A5FA" fontSize="9" fontWeight="bold" opacity={0.7} className="font-mono">T</text>
                    </g>
                  ) : (
                    /* Standard Transmission Line */
                    <line
                      x1={start.x}
                      y1={start.y}
                      x2={end.x}
                      y2={end.y}
                      stroke={
                        isCompromised
                          ? comp.type === "DOS" ? "#334155" : "#EF4444"
                          : isIsolatedByFlisr
                          ? "#EF4444"
                          : isDeEnergized
                          ? "#374151"
                          : isOverloaded
                          ? "#EF4444"
                          : isWarningOverload
                          ? "#F59E0B"
                          : isHealedTie
                          ? "#10B981"
                          : "#1F2937"
                      }
                      strokeWidth={isCompromised ? 6 : isHealedTie ? 5.5 : isDeEnergized ? 2.5 : 3.5}
                      strokeDasharray={isIsolatedByFlisr ? "4,4" : isDeEnergized && !isClosed ? "3,3" : undefined}
                      opacity={isDeEnergized ? 0.35 : 1}
                      className={isCompromised && comp.type !== "DOS" ? "faulted-line" : ""}
                    />
                  )}

                  {/* Animated Power Flow Path (Only for Transmission Lines) */}
                  {!line.is_trafo && isClosed && !isDeEnergized && !isCompromised && !isIsolatedByFlisr && (
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
                          : "#10B981" // Nominal flow colored SCADA Green
                      }
                      strokeWidth={isOverloaded ? 3.0 : isWarningOverload ? 2.6 : 2.2}
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

            {/* Draw Breakers */}
            {activeLines.map((line: any) => {
              const start = getBusCoord(line.from_bus);
              const end = getBusCoord(line.to_bus);
              const isClosed = breakers[line.id] === "CLOSED";
              
              const mx = (start.x + end.x) / 2;
              const my = (start.y + end.y) / 2;

              const comp = compromisedNodes[line.id];
              const isBreakerManipulated = comp && comp.type === "BREAKER_MANIPULATION";
              const isJammed = comp && comp.type === "DOS";

              return (
                <g 
                  key={`brk-${line.id}`} 
                  className="cursor-pointer group"
                  onClick={() => onToggleBreaker(line.id)}
                >
                  {(!isClosed || isBreakerManipulated) && (
                    <circle
                      cx={mx}
                      cy={my}
                      r={isBreakerManipulated ? 24 : 20}
                      fill="none"
                      stroke={isBreakerManipulated ? "#F59E0B" : "#EF4444"}
                      className="trip-ripple"
                      pointerEvents="none"
                    />
                  )}

                  <circle cx={mx} cy={my} r={18} fill="rgba(0,0,0,0.5)" className="opacity-0 group-hover:opacity-100 transition-opacity" />
                  
                  <rect
                    x={mx - 8}
                    y={my - 8}
                    width={16}
                    height={16}
                    fill={isJammed ? "#475569" : isClosed ? "#10B981" : "#EF4444"}
                    stroke={isBreakerManipulated ? "#F59E0B" : "#111827"}
                    strokeWidth={isBreakerManipulated ? 2.0 : 1.2}
                    className={isBreakerManipulated ? "animate-pulse" : "transition-colors duration-300"}
                  />
                  
                  {isJammed ? (
                    <path d={`M ${mx - 4} ${my - 4} L ${mx + 4} ${my + 4} M ${mx + 4} ${my - 4} L ${mx - 4} ${my + 4}`} stroke="#FFFFFF" strokeWidth="1.5" />
                  ) : (
                    <text x={mx} y={my + 4.5} textAnchor="middle" fill="#FFFFFF" fontSize="11" fontWeight="bold" className="pointer-events-none select-none font-mono">
                      {isClosed ? "C" : "O"}
                    </text>
                  )}
                </g>
              );
            })}

            {/* Draw Substation Bus Bars */}
            {activeBuses.map((bid) => {
              const coord = getBusCoord(bid);
              const busData = buses[bid] || {};
              const v = busData.voltage_pu || 0.0;
              const busColorClass = getBusColorClass(v, bid);
              
              const length = 75;
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
                  {/* SCADA substation glow effect */}
                  <line
                    x1={x1}
                    y1={coord.y}
                    x2={x2}
                    y2={coord.y}
                    strokeWidth={9}
                    stroke={v < 0.2 ? "transparent" : (v < 0.90 ? "rgba(245, 158, 11, 0.15)" : "rgba(16, 185, 129, 0.15)")}
                    className="transition-all duration-300"
                    pointerEvents="none"
                  />
                  
                  {/* Thick Bus Bar */}
                  <line
                    x1={x1}
                    y1={coord.y}
                    x2={x2}
                    y2={coord.y}
                    strokeWidth={5}
                    className={`${busColorClass} transition-all duration-300`}
                  />
                  
                  {/* Label */}
                  <text 
                    x={coord.x} 
                    y={coord.y - 15} 
                    textAnchor="middle" 
                    fill={isComp ? "#EF4444" : "#F3F4F6"}
                    fontSize="12.5" 
                    fontWeight="bold"
                    stroke="#090d16"
                    strokeWidth="3.5"
                    paintOrder="stroke fill"
                    strokeLinejoin="round"
                    className="tracking-wider font-mono select-none"
                  >
                    {bid.replace("Bus_", "BUS ")}
                  </text>

                  {/* Voltage Magnitude (pu) */}
                  <text 
                    x={coord.x} 
                    y={coord.y + 20} 
                    textAnchor="middle" 
                    fontSize="11.5" 
                    stroke="#090d16"
                    strokeWidth="3"
                    paintOrder="stroke fill"
                    strokeLinejoin="round"
                    className={`${getBusTextClass(v, bid)} font-bold font-scada-nums select-none`}
                  >
                    {isComp && compType === "DOS" ? "COMM LOSS" : `${(v ?? 0).toFixed(3)} pu`}
                  </text>

                  {/* Voltage Angle (Degrees) */}
                  {!isComp && v >= 0.2 && (
                    <text 
                      x={coord.x} 
                      y={coord.y + 32} 
                      textAnchor="middle" 
                      fontSize="9.5" 
                      fill="#9CA3AF"
                      stroke="#090d16"
                      strokeWidth="2.5"
                      paintOrder="stroke fill"
                      strokeLinejoin="round"
                      className="font-mono font-semibold select-none"
                    >
                      {`${((busData.angle_rad || 0) * 180 / Math.PI).toFixed(1)}°`}
                    </text>
                  )}

                  {isComp && (
                    <g transform={`translate(${coord.x + 35}, ${coord.y - 10})`}>
                      <circle cx="0" cy="0" r="8" fill="#7F1D1D" stroke="#EF4444" strokeWidth="1.2" />
                      <text x="0" y="3" textAnchor="middle" fill="#EF4444" fontSize="9" fontWeight="bold">!</text>
                    </g>
                  )}
                </g>
              );
            })}

            {/* Static Loading Labels next to Lines */}
            {activeLines.map((line: any) => {
              const start = getBusCoord(line.from_bus);
              const end = getBusCoord(line.to_bus);
              const ldata = lines[line.id] || {};
              const isClosed = breakers[line.id] === "CLOSED";
              const loading = ldata.loading_percent || 0.0;

              const isComp = !!compromisedNodes[line.id];
              const compType = compromisedNodes[line.id]?.type;

              if (!isClosed) return null;

              // Place text offset from breaker
              const textPosX = (start.x + end.x) / 2;
              const textPosY = (start.y + end.y) / 2 - 16;

              return (
                <g key={`lbl-${line.id}`}>
                  <rect
                    x={textPosX - 25}
                    y={textPosY - 9}
                    width={50}
                    height={14}
                    rx={2}
                    fill="#05080E"
                    stroke={isComp ? "#EF4444" : loading > 100 ? "#EF4444" : loading > 80 ? "#F59E0B" : "#10B981"}
                    strokeWidth={0.8}
                    opacity={0.85}
                  />
                  <text
                    x={textPosX}
                    y={textPosY + 2}
                    textAnchor="middle"
                    fill={isComp && compType === "DOS" ? "#475569" : loading > 100 ? "#EF4444" : loading > 80 ? "#F59E0B" : "#10B981"}
                    fontSize="9.5"
                    fontWeight="bold"
                    stroke="#05080E"
                    strokeWidth="2.5"
                    paintOrder="stroke fill"
                    strokeLinejoin="round"
                    className="font-scada-nums select-none"
                  >
                    {isComp && compType === "DOS" ? "N/A" : `${(loading ?? 0).toFixed(0)}%`}
                  </text>
                </g>
              );
            })}

            {/* Draw Generator Icons & Real-time Outputs */}
            {activeBuses.map((bid) => {
              const coord = getBusCoord(bid);
              const busData = buses[bid] || {};
              const isGen = topology?.buses?.[bid]?.is_gen ?? (parseInt(bid.replace("Bus_", ""), 10) >= 30);
              if (!isGen) return null;

              const cy = coord.y - 45;
              const cx = coord.x;
              
              // Generator real-time output
              const pGen = busData.P_mw || 0.0;
              const qGen = busData.Q_mvar || 0.0;

              return (
                <g key={`gen-${bid}`} className="pointer-events-none">
                  {/* Generator rotor symbol */}
                  <circle cx={cx} cy={cy} r={13} fill="#06090F" stroke="#10B981" strokeWidth={2} />
                  <path d={`M ${cx - 6} ${cy} Q ${cx - 3} ${cy - 4} ${cx} ${cy} T ${cx + 6} ${cy}`} fill="none" stroke="#10B981" strokeWidth={1.8} />
                  <line x1={cx} y1={coord.y - 3} x2={cx} y2={cy + 13} stroke="#10B981" strokeWidth={2} />
                  
                  {/* Power labels */}
                  {pGen > 0 && (
                    <g>
                      <text 
                        x={cx + 18} 
                        y={cy - 1} 
                        fill="#10B981" 
                        fontSize="9.5" 
                        fontWeight="bold" 
                        stroke="#05080E"
                        strokeWidth="2.5"
                        paintOrder="stroke fill"
                        strokeLinejoin="round"
                        className="font-mono select-none"
                      >
                        {`${pGen.toFixed(0)} MW`}
                      </text>
                      <text 
                        x={cx + 18} 
                        y={cy + 9} 
                        fill="#059669" 
                        fontSize="8.5" 
                        fontWeight="semibold"
                        stroke="#05080E"
                        strokeWidth="2"
                        paintOrder="stroke fill"
                        strokeLinejoin="round"
                        className="font-mono select-none"
                      >
                        {`${qGen.toFixed(0)} MV`}
                      </text>
                    </g>
                  )}
                </g>
              );
            })}

            {/* Draw Load Indicator Arrows & Real-time Consumption */}
            {activeBuses.map((bid) => {
              const coord = getBusCoord(bid);
              const busData = buses[bid] || {};
              const isLoad = topology?.buses?.[bid]?.is_load ?? (parseInt(bid.replace("Bus_", ""), 10) < 30 && parseInt(bid.replace("Bus_", ""), 10) % 3 === 0);
              if (!isLoad) return null;

              const ly = coord.y + 44;
              const lx = coord.x;
              
              const pLoad = busData.P_mw || 0.0;

              return (
                <g key={`load-${bid}`} className="pointer-events-none">
                  <path
                    d={`M ${lx} ${ly} L ${lx} ${ly + 12}`}
                    stroke="#3B82F6"
                    strokeWidth={1.5}
                    markerEnd="url(#arrow)"
                  />
                  {pLoad > 0 && (
                    <text 
                      x={lx + 10} 
                      y={ly + 8} 
                      fill="#60A5FA" 
                      fontSize="9.5" 
                      stroke="#05080E"
                      strokeWidth="2.5"
                      paintOrder="stroke fill"
                      strokeLinejoin="round"
                      className="font-mono select-none"
                    >
                      {`${pLoad.toFixed(0)} MW`}
                    </text>
                  )}
                </g>
              );
            })}
          </g>
        </svg>
      </div>

      {/* Floating Status card */}
      <div className="bg-scada-bg/85 border border-scada-border rounded p-2 text-[10px] text-scada-dimText flex justify-between items-center backdrop-blur-sm">
        <span className="flex items-center gap-1.5">
          <AlertTriangle size={12} className="text-scada-warning" />
          Drag to pan. Scroll to zoom. Click breakers to toggle.
        </span>
        {hoveredEl && (
          <span className="font-mono text-white font-semibold">
            {hoveredEl.type === "bus"
              ? `${hoveredEl.id.replace("Bus_", "BUS ")}: P=${(hoveredEl.data?.active_power ?? 0).toFixed(1)}MW Q=${(hoveredEl.data?.reactive_power ?? 0).toFixed(1)}MVAR`
              : `LINE ${hoveredEl.id.replace("L_line_", "Line ").replace("L_trafo_", "Trafo ")}: P_flow=${(hoveredEl.data?.active_power_flow ?? 0).toFixed(1)}MW Q_flow=${(hoveredEl.data?.reactive_power_flow ?? 0).toFixed(1)}MVAR`}
          </span>
        )}
      </div>
    </div>
  );
};
