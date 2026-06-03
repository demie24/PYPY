import React, { useState } from "react";
import {
  Usb, ShieldAlert, AlertOctagon, Terminal, Lock, Unlock, RefreshCw, Play, Trash2, PlusCircle, Shield, Zap, Clock, GitBranch
} from "lucide-react";

interface USBDevice {
  vendor_id: string;
  product_id: string;
  name: string;
  trusted: boolean;
  status: string;
}

interface USBEvent {
  timestamp: number;
  event_type: string;
  device: string;
  details: string;
  severity: string;
}

interface BadUSBStatus {
  timestamp: number;
  attack_state: string;
  active_payload: string | null;
  time_elapsed: number;
  current_phase?: string;
  total_steps?: number;
  current_step?: number;
  events_count: number;
}

interface IntrusionAlert {
  timestamp: number;
  alert_type: string;
  target: string;
  details: string;
  severity: string;
}

interface TrustStatus {
  trust_score: number;
  unauthorized_count: number;
  total_devices: number;
  propagation_level?: number;
}

interface AttackOrchestrationStatus {
  timestamp: number;
  attack_escalation_state: string;
  quarantined_ports: string[];
  hardware_trust: number;
  intrusion_score: number;
  digispark_state: string;
  campaign?: {
    active_campaign: string | null;
    step: number;
    phase_label: string;
  };
}

interface PropagationNode {
  id: string;
  label: string;
  status: string;
}

interface PropagationLink {
  source: string;
  target: string;
  status: string;
}

interface AttackPropagationChain {
  timestamp: number;
  nodes: PropagationNode[];
  links: PropagationLink[];
}

interface CyberPhysicalAttackPanelProps {
  hardwareUsbEvents: { events: USBEvent[] } | null;
  hardwareRogueDevices: { devices: USBDevice[] } | null;
  hardwareBadusb: BadUSBStatus | null;
  hardwareIntrusionAlerts: { alerts: IntrusionAlert[] } | null;
  hardwareDeviceTrust: TrustStatus | null;
  hardwareAttackState: AttackOrchestrationStatus | null;
  hardwareAttackPropagation: AttackPropagationChain | null;
  onSendControl: (payload: any) => void;
}

// Propagation graph node positions (normalized 0..1 in the SVG viewport)
const NODE_POSITIONS: Record<string, { x: number; y: number }> = {
  USB_Port_7: { x: 0.10, y: 0.5 },
  ESP32_Bridge: { x: 0.37, y: 0.5 },
  PLC_Modbus_Gateway: { x: 0.64, y: 0.5 },
  Breaker_Relays: { x: 0.90, y: 0.5 },
};

function getNodeColor(status: string): string {
  switch (status) {
    case "NOMINAL": return "#10b981";
    case "COMPROMISED": return "#f43f5e";
    case "QUARANTINED": return "#f59e0b";
    default: return "#64748b";
  }
}

function getLinkColor(status: string): string {
  switch (status) {
    case "ACTIVE": return "#06b6d4";
    case "BLOCKED": return "#f59e0b";
    default: return "#374151";
  }
}

const PropagationGraphSVG: React.FC<{ chain: AttackPropagationChain | null }> = ({ chain }) => {
  const W = 300;
  const H = 80;

  const nodes: PropagationNode[] = chain?.nodes ?? [
    { id: "USB_Port_7", label: "USB Interface", status: "NOMINAL" },
    { id: "ESP32_Bridge", label: "ESP32 Bridge", status: "NOMINAL" },
    { id: "PLC_Modbus_Gateway", label: "Modbus GW", status: "NOMINAL" },
    { id: "Breaker_Relays", label: "Breakers", status: "NOMINAL" },
  ];

  const links: PropagationLink[] = chain?.links ?? [
    { source: "USB_Port_7", target: "ESP32_Bridge", status: "ACTIVE" },
    { source: "ESP32_Bridge", target: "PLC_Modbus_Gateway", status: "ACTIVE" },
    { source: "PLC_Modbus_Gateway", target: "Breaker_Relays", status: "ACTIVE" },
  ];

  const px = (id: string) => (NODE_POSITIONS[id]?.x ?? 0.5) * W;
  const py = (id: string) => (NODE_POSITIONS[id]?.y ?? 0.5) * H;

  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" height="100%">
      <defs>
        <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="2.5" result="blur"/>
          <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
        </filter>
      </defs>

      {/* Links */}
      {links.map((link, idx) => {
        const x1 = px(link.source) + 14;
        const y1 = py(link.source);
        const x2 = px(link.target) - 14;
        const y2 = py(link.target);
        const color = getLinkColor(link.status);
        return (
          <g key={idx}>
            <line x1={x1} y1={y1} x2={x2} y2={y2}
              stroke={color} strokeWidth={link.status === "BLOCKED" ? 2 : 1.5}
              strokeDasharray={link.status === "BLOCKED" ? "4 2" : undefined}
              opacity={0.8}
            />
            {/* Arrow */}
            <polygon
              points={`${x2},${y2} ${x2 - 5},${y2 - 3} ${x2 - 5},${y2 + 3}`}
              fill={color} opacity={0.9}
            />
          </g>
        );
      })}

      {/* Nodes */}
      {nodes.map((node, idx) => {
        const x = px(node.id);
        const y = py(node.id);
        const color = getNodeColor(node.status);
        const isCompromised = node.status === "COMPROMISED";
        const shortLabel = node.label.split(" ")[0];
        return (
          <g key={idx} filter="url(#glow)">
            {isCompromised && (
              <circle cx={x} cy={y} r={16} fill={color} opacity={0.12}>
                <animate attributeName="r" values="14;20;14" dur="1.5s" repeatCount="indefinite"/>
                <animate attributeName="opacity" values="0.12;0.06;0.12" dur="1.5s" repeatCount="indefinite"/>
              </circle>
            )}
            <circle cx={x} cy={y} r={14} fill={`${color}22`} stroke={color} strokeWidth={1.5}/>
            <text x={x} y={y + 1} textAnchor="middle" dominantBaseline="middle"
              fontSize={7} fill={color} fontWeight="bold" fontFamily="monospace">
              {shortLabel}
            </text>
            <text x={x} y={y + 21} textAnchor="middle" fontSize={5.5} fill="#94a3b8" fontFamily="monospace">
              {node.status}
            </text>
          </g>
        );
      })}
    </svg>
  );
};

// Vertical campaign timeline component
const CampaignTimeline: React.FC<{ campaign: AttackOrchestrationStatus["campaign"] | undefined }> = ({ campaign }) => {
  const TOTAL_STEPS = 4;
  const currentStep = campaign?.step ?? 0;
  const isActive = !!campaign?.active_campaign;

  return (
    <div className="flex flex-col items-center h-full py-1">
      {Array.from({ length: TOTAL_STEPS }, (_, i) => {
        const step = i + 1;
        const isDone = step < currentStep;
        const isCurrent = step === currentStep && isActive;
        return (
          <div key={step} className="flex flex-col items-center">
            <div className={`w-4 h-4 rounded-full border flex items-center justify-center text-[6px] font-bold transition-all ${
              isCurrent ? "bg-orange-500 border-orange-400 text-white animate-pulse" :
              isDone ? "bg-emerald-600 border-emerald-400 text-white" :
              "bg-scada-bg border-scada-border/40 text-scada-dimText"
            }`}>
              {isDone ? "✓" : step}
            </div>
            {step < TOTAL_STEPS && (
              <div className={`w-0.5 h-3 my-0.5 transition-all ${
                isDone ? "bg-emerald-500" : "bg-scada-border/30"
              }`}/>
            )}
          </div>
        );
      })}
    </div>
  );
};

export const CyberPhysicalAttackPanel: React.FC<CyberPhysicalAttackPanelProps> = ({
  hardwareUsbEvents,
  hardwareRogueDevices,
  hardwareBadusb,
  hardwareIntrusionAlerts,
  hardwareDeviceTrust,
  hardwareAttackState,
  hardwareAttackPropagation,
  onSendControl
}) => {
  const payloadsList = [
    { id: "recon_discovery", name: "Network Discovery (Recon)", category: "RECONNAISSANCE" },
    { id: "firmware_modbus_hijack", name: "Modbus Register Hijack", category: "COMMAND_INJECTION" },
    { id: "trust_sabotage", name: "Sensor Calibration Tampering", category: "INTEGRITY_VIOLATION" },
    { id: "dos_command_flood", name: "Relay Chattering Flood (DoS)", category: "DENIAL_OF_SERVICE" },
    { id: "credential_exfiltration", name: "Grid Config Exfiltration", category: "EXFILTRATION" },
  ];

  const usbModels = [
    { name: "Rubber Ducky Key Injector", vid: "16c0", pid: "05df" },
    { name: "Digispark ATTINY85 BadUSB", vid: "16c0", pid: "2770" },
    { name: "Teensy 4.0 Rogue Serial Host", vid: "16c0", pid: "0487" },
    { name: "Malicious DFU Firmware Flasher", vid: "03eb", pid: "204b" },
  ];

  const campaigns = [
    { id: "coordinated_blackout", label: "Coordinated Blackout" },
    { id: "stealthy_calibration_drift", label: "Stealthy Calibration Drift" },
    { id: "reconnect_flood_dos", label: "Reconnect Flood DoS" },
  ];

  const [selectedDeviceIndex, setSelectedDeviceIndex] = useState(0);
  const [selectedPayloadId, setSelectedPayloadId] = useState("recon_discovery");
  const [selectedCampaign, setSelectedCampaign] = useState("coordinated_blackout");
  const [activeTab, setActiveTab] = useState<"usb" | "hid" | "intrusion">("usb");

  const devices = hardwareRogueDevices?.devices ?? [
    { vendor_id: "0483", product_id: "5740", name: "STM32 Virtual COM Port (ESP32_Bridge)", trusted: true, status: "ACTIVE" },
    { vendor_id: "1a86", product_id: "7523", name: "CH340 Serial Converter (PLC_Modbus_Gateway)", trusted: true, status: "ACTIVE" },
  ];
  const events = hardwareUsbEvents?.events ?? [];
  const alerts = hardwareIntrusionAlerts?.alerts ?? [];
  const defaultBadusb: BadUSBStatus = { timestamp: 0, attack_state: "IDLE", active_payload: null, time_elapsed: 0, events_count: 0 };
  const defaultAttackState: AttackOrchestrationStatus = {
    timestamp: 0, attack_escalation_state: "NOMINAL", quarantined_ports: [], hardware_trust: 1.0, intrusion_score: 0.0, digispark_state: "IDLE"
  };
  const badusb = hardwareBadusb ?? defaultBadusb;
  const trust = hardwareDeviceTrust ?? { trust_score: 1.0, unauthorized_count: 0, total_devices: 2 };
  const attackState = hardwareAttackState ?? defaultAttackState;

  const handleInjectDevice = () => {
    const dev = usbModels[selectedDeviceIndex];
    onSendControl({ command: "INJECT_USB_DEVICE", vendor_id: dev.vid, product_id: dev.pid, name: dev.name });
  };

  const handleRemoveDevice = (vid: string, pid: string) => {
    onSendControl({ command: "REMOVE_USB_DEVICE", vendor_id: vid, product_id: pid });
  };

  const handleTriggerAttack = () => {
    onSendControl({ command: "TRIGGER_BADUSB_ATTACK", payload_id: selectedPayloadId });
  };

  const handleLaunchCampaign = () => {
    onSendControl({ command: "LAUNCH_HARDWARE_SCENARIO", scenario: selectedCampaign });
  };

  const handleToggleQuarantine = (port: string) => {
    const isQ = attackState.quarantined_ports.includes(port);
    onSendControl({ command: isQ ? "RELEASE_PORT" : "QUARANTINE_PORT", port });
  };

  const handleResetAlarms = () => {
    onSendControl({ command: "RESET_ALARMS" });
  };

  const getEscalationStyle = (state: string) => {
    switch (state) {
      case "NOMINAL": return "bg-emerald-500/10 border-emerald-500/30 text-emerald-400";
      case "INTRUSION_DETECTED": return "bg-amber-500/10 border-amber-500/30 text-amber-400 animate-pulse";
      case "PORT_QUARANTINED": return "bg-purple-500/15 border-purple-500/40 text-purple-400 animate-pulse";
      case "ACTIVE_HID_INJECTION": return "bg-orange-500/20 border-orange-500/50 text-orange-400 animate-pulse";
      case "COMPROMISED": return "bg-rose-500/25 border-rose-500/50 text-rose-400 animate-bounce";
      default: return "bg-gray-500/10 border-gray-500/30 text-gray-400";
    }
  };

  const getSeverityStyle = (severity: string) => {
    switch (severity) {
      case "CRITICAL": return "text-rose-400 font-bold";
      case "HIGH": return "text-orange-400";
      case "WARNING": return "text-amber-400";
      default: return "text-cyan-400";
    }
  };

  const propagationLevel = (trust.propagation_level ?? 0) * 100;

  return (
    <div className="bg-scada-panel border border-scada-border rounded-lg p-3 h-[380px] flex flex-col overflow-hidden relative font-mono text-[9px] text-white">
      {/* Dynamic background glow */}
      <div className={`absolute inset-0 transition-opacity duration-1000 pointer-events-none opacity-[0.04] ${
        attackState.attack_escalation_state === "COMPROMISED" ? "bg-rose-500" :
        attackState.attack_escalation_state === "ACTIVE_HID_INJECTION" ? "bg-orange-500" :
        attackState.attack_escalation_state === "PORT_QUARANTINED" ? "bg-purple-500" :
        attackState.attack_escalation_state === "INTRUSION_DETECTED" ? "bg-amber-500" : "bg-emerald-900"
      }`} />

      {/* ── HEADER ── */}
      <div className="flex justify-between items-center mb-1.5 border-b border-scada-border/40 pb-1.5 shrink-0 z-10">
        <div className="flex items-center gap-1.5">
          <Usb className="text-cyan-400 w-3.5 h-3.5" />
          <span className="text-[10px] font-bold uppercase tracking-wider text-cyan-100">Cyber-Physical Attack Layer</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1 bg-scada-bg/85 px-1.5 py-0.5 rounded border border-scada-border/30">
            <span className="text-scada-dimText">TRUST:</span>
            <span className={`font-bold ${trust.trust_score >= 0.8 ? "text-emerald-400" : trust.trust_score >= 0.5 ? "text-amber-400" : "text-rose-400 animate-pulse"}`}>
              {((trust?.trust_score ?? 1.0) * 100).toFixed(0)}%
            </span>
          </div>
          <div className="flex items-center gap-1 bg-scada-bg/85 px-1.5 py-0.5 rounded border border-scada-border/30">
            <span className="text-scada-dimText">INTR:</span>
            <span className={`font-bold ${attackState.intrusion_score >= 70 ? "text-rose-400 animate-pulse" : attackState.intrusion_score >= 20 ? "text-amber-400" : "text-emerald-400"}`}>
              {(attackState?.intrusion_score ?? 0.0).toFixed(0)}
            </span>
          </div>
          <div className={`px-2 py-0.5 rounded border text-[8px] font-bold uppercase tracking-wider ${getEscalationStyle(attackState.attack_escalation_state)}`}>
            {attackState.attack_escalation_state.replace(/_/g, " ")}
          </div>
          <button onClick={handleResetAlarms} className="p-1 hover:bg-scada-border/40 rounded text-scada-dimText hover:text-white" title="Reset">
            <RefreshCw size={10} />
          </button>
        </div>
      </div>

      {/* ── PROPAGATION GRAPH ── */}
      <div className="shrink-0 h-[70px] bg-scada-bg/60 border border-scada-border/30 rounded mb-1.5 px-2 relative z-10">
        <div className="absolute top-1 left-2 text-[7px] text-scada-dimText uppercase tracking-wider flex items-center gap-1">
          <GitBranch size={7} /> Compromise Propagation Chain
          {propagationLevel > 0 && (
            <span className="ml-1 text-rose-400 font-bold">{(propagationLevel ?? 0.0).toFixed(0)}% PROPAGATED</span>
          )}
        </div>
        <div className="h-full pt-3">
          <PropagationGraphSVG chain={hardwareAttackPropagation} />
        </div>
      </div>

      {/* ── TABS ── */}
      <div className="flex gap-1 mb-1.5 shrink-0 z-10">
        {(["usb", "hid", "intrusion"] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-2 py-0.5 rounded text-[8px] uppercase tracking-wider font-bold border transition-all ${
              activeTab === tab
                ? "bg-cyan-950 border-cyan-500/60 text-cyan-300"
                : "bg-scada-bg border-scada-border/30 text-scada-dimText hover:text-white"
            }`}
          >
            {tab === "usb" ? "USB Monitor" : tab === "hid" ? "HID Payloads" : "Intrusion & Quarantine"}
          </button>
        ))}
      </div>

      {/* ── TAB CONTENT ── */}
      <div className="flex-1 flex gap-2 overflow-hidden z-10 min-h-0">

        {activeTab === "usb" && (
          <>
            {/* USB Devices list */}
            <div className="flex-1 flex flex-col overflow-hidden bg-scada-bg/50 border border-scada-border/30 rounded p-2">
              <div className="flex justify-between items-center mb-1 border-b border-scada-border/20 pb-1 shrink-0">
                <span className="text-cyan-400 font-bold uppercase tracking-wider">Enumerated Devices</span>
                <span className="text-scada-dimText">Total: {devices.length} | Rogue: {trust.unauthorized_count}</span>
              </div>
              <div className="flex-1 overflow-y-auto space-y-1 pr-0.5">
                {devices.map((dev, idx) => (
                  <div key={idx} className={`p-1.5 border rounded flex justify-between items-center transition-all ${
                    dev.trusted ? "bg-emerald-950/20 border-emerald-500/20" :
                    dev.status === "QUARANTINED" ? "bg-purple-950/20 border-purple-500/30" :
                    "bg-rose-950/20 border-rose-500/30 animate-pulse"
                  }`}>
                    <div className="overflow-hidden">
                      <div className="flex items-center gap-1 font-bold">
                        {dev.trusted ? <Shield className="w-2.5 h-2.5 text-emerald-400" /> : <ShieldAlert className="w-2.5 h-2.5 text-rose-400" />}
                        <span className="truncate max-w-[120px] block">{dev.name}</span>
                      </div>
                      <div className="text-[7px] text-scada-dimText mt-0.5">
                        VID:PID <span className="text-white">{dev.vendor_id}:{dev.product_id}</span> | <span className={`font-bold ${dev.trusted ? "text-emerald-400" : dev.status === "QUARANTINED" ? "text-purple-400" : "text-rose-400"}`}>{dev.status}</span>
                      </div>
                    </div>
                    {!dev.trusted && (
                      <button onClick={() => handleRemoveDevice(dev.vendor_id, dev.product_id)}
                        className="p-0.5 hover:bg-rose-500/20 rounded border border-rose-500/30 text-rose-400 transition-colors shrink-0" title="Disconnect">
                        <Trash2 size={8} />
                      </button>
                    )}
                  </div>
                ))}
              </div>
              <div className="mt-1.5 pt-1.5 border-t border-scada-border/20 shrink-0">
                <div className="text-scada-dimText mb-1 uppercase tracking-wider text-[7px]">Inject Rogue USB Device</div>
                <div className="flex gap-1">
                  <select value={selectedDeviceIndex} onChange={(e) => setSelectedDeviceIndex(Number(e.target.value))}
                    className="flex-1 bg-scada-bg border border-scada-border/50 text-white rounded p-1 text-[8px] outline-none">
                    {usbModels.map((m, i) => <option key={i} value={i}>{m.name}</option>)}
                  </select>
                  <button onClick={handleInjectDevice}
                    className="bg-cyan-950 border border-cyan-500/40 hover:bg-cyan-900 text-cyan-400 px-2 rounded flex items-center gap-0.5 transition-colors shrink-0">
                    <PlusCircle size={8} /><span>Mount</span>
                  </button>
                </div>
              </div>
            </div>

            {/* Campaign launcher with vertical timeline */}
            <div className="w-[130px] flex flex-col bg-scada-bg/50 border border-scada-border/30 rounded p-2 shrink-0 overflow-hidden">
              <div className="flex items-center gap-1 mb-1 border-b border-scada-border/20 pb-1 shrink-0">
                <Zap size={8} className="text-orange-400" />
                <span className="text-orange-400 font-bold uppercase tracking-wider text-[8px]">Campaigns</span>
              </div>
              <div className="shrink-0 mb-2">
                <select value={selectedCampaign} onChange={(e) => setSelectedCampaign(e.target.value)}
                  className="w-full bg-scada-bg border border-scada-border/50 text-white rounded p-1 text-[7px] outline-none mb-1">
                  {campaigns.map(c => <option key={c.id} value={c.id}>{c.label}</option>)}
                </select>
                <button onClick={handleLaunchCampaign}
                  className="w-full bg-orange-950/80 border border-orange-500/40 hover:bg-orange-900 text-orange-400 py-1 rounded flex items-center justify-center gap-1 transition-colors text-[8px] font-bold">
                  <Play size={8} /> Launch
                </button>
              </div>
              {/* Vertical timeline */}
              <div className="text-scada-dimText text-[7px] uppercase tracking-wider mb-1 flex items-center gap-0.5">
                <Clock size={7} /> Progress
              </div>
              <div className="flex gap-2 flex-1 overflow-hidden">
                <div className="flex-1 text-[7px] space-y-1 text-scada-dimText">
                  {["Rogue USB Inserted", "Recon Discovery", "Privilege Escalation", "Modbus Hijack"].map((label, i) => {
                    const step = i + 1;
                    const currentStep = attackState.campaign?.step ?? 0;
                    const isActive = !!attackState.campaign?.active_campaign;
                    const isDone = step < currentStep;
                    const isCurrent = step === currentStep && isActive;
                    return (
                      <div key={i} className={`leading-tight ${isCurrent ? "text-orange-300 font-bold" : isDone ? "text-emerald-400" : "text-scada-dimText/60"}`}>
                        {isDone ? "✓" : isCurrent ? "▶" : "○"} {label}
                      </div>
                    );
                  })}
                </div>
                <CampaignTimeline campaign={attackState.campaign} />
              </div>
            </div>
          </>
        )}

        {activeTab === "hid" && (
          <>
            {/* HID payload launcher */}
            <div className="w-[160px] flex flex-col bg-scada-bg/50 border border-scada-border/30 rounded p-2 shrink-0">
              <div className="flex justify-between items-center mb-1.5 border-b border-scada-border/20 pb-1 shrink-0">
                <span className="text-cyan-400 font-bold uppercase tracking-wider">HID Payloads</span>
                <div className="flex items-center gap-1 font-bold">
                  <div className={`w-1.5 h-1.5 rounded-full ${badusb.attack_state === "EXECUTING" ? "bg-orange-500 animate-ping" : badusb.attack_state === "COMPLETED" ? "bg-emerald-500" : "bg-gray-500"}`} />
                  <span className={badusb.attack_state === "EXECUTING" ? "text-orange-400" : badusb.attack_state === "COMPLETED" ? "text-emerald-400" : "text-gray-400"}>
                    {badusb.attack_state}
                  </span>
                </div>
              </div>
              <div className="text-scada-dimText uppercase tracking-wider text-[7px] mb-1">Select DuckyScript Payload</div>
              <select value={selectedPayloadId} onChange={(e) => setSelectedPayloadId(e.target.value)}
                className="bg-scada-bg border border-scada-border/50 text-white rounded p-1 text-[8px] outline-none mb-1.5"
                disabled={badusb.attack_state === "EXECUTING"}>
                {payloadsList.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
              </select>
              <button onClick={handleTriggerAttack} disabled={badusb.attack_state === "EXECUTING"}
                className="w-full bg-orange-950/80 border border-orange-500/40 hover:bg-orange-900 text-orange-400 py-1 rounded flex items-center justify-center gap-1 transition-colors disabled:opacity-50 text-[8px] font-bold mb-2">
                <Play size={8} /> Execute Attack
              </button>
              {badusb.attack_state !== "IDLE" && (
                <div className="space-y-1 text-[7px]">
                  <div className="flex justify-between">
                    <span className="text-scada-dimText">Phase:</span>
                    <span className="text-amber-400 font-bold">{badusb.current_phase ?? "—"}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-scada-dimText">Step:</span>
                    <span className="text-white">{badusb.current_step ?? 0}/{badusb.total_steps ?? 0}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-scada-dimText">Elapsed:</span>
                    <span className="text-white">{(badusb?.time_elapsed ?? 0.0).toFixed(1)}s</span>
                  </div>
                  {badusb.attack_state === "EXECUTING" && (
                    <div className="bg-scada-bg border border-scada-border/20 rounded h-2 overflow-hidden mt-1">
                      <div className="bg-gradient-to-r from-orange-500 to-yellow-400 h-full animate-pulse"
                        style={{ width: `${Math.min(100, ((badusb.current_step ?? 0) / Math.max(badusb.total_steps ?? 1, 1)) * 100)}%` }}
                      />
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* USB Bus Console */}
            <div className="flex-1 flex flex-col overflow-hidden bg-scada-bg/50 border border-scada-border/30 rounded p-2">
              <div className="text-cyan-400 font-bold uppercase tracking-wider mb-1 flex items-center gap-1 text-[8px] shrink-0">
                <Terminal size={9} /> USB Bus Console Logs
              </div>
              <div className="flex-1 bg-scada-bg border border-scada-border/40 rounded p-1.5 overflow-y-auto space-y-1 text-[7px] font-mono leading-normal">
                {events.length === 0 ? (
                  <div className="text-scada-dimText italic text-center pt-4">No USB activity logged.</div>
                ) : (
                  [...events].reverse().map((ev, idx) => (
                    <div key={idx} className="border-b border-scada-border/10 pb-0.5">
                      <div className="flex justify-between items-center">
                        <span className="text-scada-dimText">[{new Date(ev.timestamp).toLocaleTimeString()}]</span>
                        <span className={`text-[6px] font-bold ${getSeverityStyle(ev.severity)}`}>{ev.event_type}</span>
                      </div>
                      <div className="text-white/80 mt-0.5">{ev.details}</div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </>
        )}

        {activeTab === "intrusion" && (
          <>
            {/* Quarantine controls */}
            <div className="w-[130px] flex flex-col bg-scada-bg/50 border border-scada-border/30 rounded p-2 shrink-0">
              <div className="text-cyan-400 font-bold uppercase tracking-wider mb-1 border-b border-scada-border/20 pb-1 shrink-0">Quarantine Ports</div>
              <div className="space-y-1 shrink-0">
                {["Port 7", "Port 8", "ESP32", "PLC"].map((port) => {
                  const isQ = attackState.quarantined_ports.includes(port);
                  return (
                    <button key={port} onClick={() => handleToggleQuarantine(port)}
                      className={`w-full py-1.5 rounded border flex items-center justify-center gap-1 transition-all text-[8px] font-bold ${
                        isQ ? "bg-rose-500/20 border-rose-500 text-rose-400 animate-pulse" :
                        "bg-scada-bg border-scada-border/40 hover:bg-scada-border/20 text-emerald-400"
                      }`}>
                      {isQ ? <Lock size={9} /> : <Unlock size={9} />}
                      {port}
                    </button>
                  );
                })}
              </div>
              <div className="mt-2 pt-2 border-t border-scada-border/20 text-[7px] space-y-1">
                <div className="flex justify-between"><span className="text-scada-dimText">Propagation:</span>
                  <span className={`font-bold ${propagationLevel > 50 ? "text-rose-400" : propagationLevel > 25 ? "text-amber-400" : "text-emerald-400"}`}>
                    {(propagationLevel ?? 0.0).toFixed(0)}%
                  </span>
                </div>
                <div className="w-full bg-scada-bg border border-scada-border/20 rounded h-1.5 overflow-hidden">
                  <div className={`h-full transition-all ${propagationLevel > 50 ? "bg-rose-500" : propagationLevel > 25 ? "bg-amber-500" : "bg-emerald-500"}`}
                    style={{ width: `${propagationLevel}%` }}
                  />
                </div>
              </div>
            </div>

            {/* Intrusion alerts console */}
            <div className="flex-1 flex flex-col overflow-hidden bg-scada-bg/50 border border-scada-border/30 rounded p-2">
              <div className="text-rose-400 font-bold uppercase tracking-wider mb-1 flex items-center gap-1 text-[8px] shrink-0">
                <AlertOctagon size={9} /> Intrusion Alert Console ({alerts.length})
              </div>
              <div className="flex-1 bg-scada-bg border border-scada-border/40 rounded p-1.5 overflow-y-auto space-y-1 text-[7px] font-mono leading-normal">
                {alerts.length === 0 ? (
                  <div className="text-emerald-400/80 italic text-center pt-4">No intrusion activity detected.</div>
                ) : (
                  [...alerts].reverse().map((al, idx) => (
                    <div key={idx} className="border-b border-scada-border/10 pb-0.5">
                      <div className="flex justify-between items-center">
                        <span className="text-scada-dimText">[{new Date(al.timestamp).toLocaleTimeString()}]</span>
                        <span className={`text-[6px] font-bold ${getSeverityStyle(al.severity)}`}>{al.alert_type}</span>
                      </div>
                      <div className="text-white/80 mt-0.5">
                        <span className="text-cyan-400/80">@{al.target}</span> — {al.details}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
};
