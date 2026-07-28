// dashboard/src/components/OperationsCenter.tsx
// PYPY V11.8 — Operations, Observability & Security Hardening
// Full-featured Operations Center UI with real-time metrics, alerts, logs,
// backup management, security events, and disaster recovery.

import React, { useState, useEffect, useCallback, useRef } from "react";

// ─── Types ────────────────────────────────────────────────────────────────────

interface SystemMetrics {
  cpu_percent: number;
  ram_percent: number;
  disk_percent: number;
  ram_used_mb: number;
  ram_total_mb: number;
  disk_used_gb: number;
  disk_total_gb: number;
  net_sent_mb: number;
  net_recv_mb: number;
  load_avg_1m: number;
  load_avg_5m: number;
  load_avg_15m: number;
  timestamp: string;
}

interface ServiceStatus {
  status: "online" | "offline" | "degraded";
  port?: number;
}

interface ServiceHealth {
  gateway: ServiceStatus;
  redis: ServiceStatus;
  mqtt: ServiceStatus;
  postgres: ServiceStatus;
  celery_worker: ServiceStatus;
  timestamp: string;
}

interface AlertEvent {
  id: string;
  rule_id: string;
  rule_name: string;
  severity: "critical" | "warning" | "info";
  message: string;
  fired_at: string;
  acknowledged: boolean;
}

interface LogEntry {
  id: string;
  service: string;
  level: "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL";
  message: string;
  extra?: Record<string, unknown>;
  logged_at: string;
}

interface BackupFile {
  filename: string;
  size_mb: number;
  created_at: string;
  filepath: string;
}

interface SecurityEvent {
  id: string;
  event_type: string;
  description: string;
  ip_address: string;
  user_id: string | null;
  occurred_at: string;
}

interface IPBlock {
  id: string;
  ip_address: string;
  reason: string;
  blocked_until: string | null;
  blocked_at: string | null;
}

interface MetricHistory {
  cpu_percent: number;
  ram_percent: number;
  avg_latency_ms: number;
  error_rate_percent: number;
  active_simulations: number;
  captured_at: string;
}

type ActiveTab = "overview" | "metrics" | "alerts" | "logs" | "backups" | "security" | "dr";

// ─── Constants ────────────────────────────────────────────────────────────────

const API_BASE = "/api";
const REFRESH_INTERVAL_MS = 5000;

const SERVICE_LABELS: Record<string, string> = {
  gateway: "API Gateway",
  redis: "Redis Cache",
  mqtt: "MQTT Broker",
  postgres: "PostgreSQL",
  celery_worker: "Celery Worker",
};

const SEVERITY_COLORS: Record<string, string> = {
  critical: "#ef4444",
  warning: "#f59e0b",
  info: "#3b82f6",
};

const LEVEL_COLORS: Record<string, string> = {
  DEBUG: "#6b7280",
  INFO: "#3b82f6",
  WARNING: "#f59e0b",
  ERROR: "#ef4444",
  CRITICAL: "#dc2626",
};

// ─── Helper Functions ─────────────────────────────────────────────────────────

function formatBytes(mb: number): string {
  if (mb >= 1024) return `${(mb / 1024).toFixed(1)} GB`;
  return `${mb.toFixed(0)} MB`;
}

function formatDate(iso: string): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString();
}

function getStatusColor(status: string): string {
  if (status === "online") return "#22c55e";
  if (status === "degraded") return "#f59e0b";
  return "#ef4444";
}

function GaugeMeter({ value, label, unit = "%", thresholds = [70, 90] }: {
  value: number; label: string; unit?: string; thresholds?: [number, number];
}) {
  const color = value >= thresholds[1] ? "#ef4444" : value >= thresholds[0] ? "#f59e0b" : "#22c55e";
  const pct = Math.min(100, Math.max(0, value));
  return (
    <div style={{ textAlign: "center", padding: "12px" }}>
      <div style={{ position: "relative", width: 90, height: 90, margin: "0 auto 8px" }}>
        <svg viewBox="0 0 36 36" style={{ width: 90, height: 90, transform: "rotate(-90deg)" }}>
          <circle cx="18" cy="18" r="15.9" fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="3" />
          <circle
            cx="18" cy="18" r="15.9" fill="none"
            stroke={color} strokeWidth="3"
            strokeDasharray={`${pct} ${100 - pct}`}
            strokeLinecap="round"
            style={{ transition: "stroke-dasharray 0.5s ease" }}
          />
        </svg>
        <div style={{
          position: "absolute", top: "50%", left: "50%",
          transform: "translate(-50%, -50%)",
          fontSize: 14, fontWeight: 700, color: "#fff",
        }}>
          {value.toFixed(0)}{unit}
        </div>
      </div>
      <div style={{ fontSize: 12, color: "rgba(255,255,255,0.6)" }}>{label}</div>
    </div>
  );
}

function MiniChart({ data, color = "#6366f1" }: { data: number[]; color?: string }) {
  if (!data || data.length < 2) return <div style={{ height: 40 }} />;
  const max = Math.max(...data, 1);
  const min = Math.min(...data, 0);
  const range = max - min || 1;
  const w = 160, h = 40;
  const points = data.map((v, i) => {
    const x = (i / (data.length - 1)) * w;
    const y = h - ((v - min) / range) * (h - 4) - 2;
    return `${x},${y}`;
  }).join(" ");

  return (
    <svg width={w} height={h} style={{ overflow: "visible" }}>
      <polyline points={points} fill="none" stroke={color} strokeWidth="1.5" />
      <polygon
        points={`0,${h} ${points} ${w},${h}`}
        fill={`${color}22`}
      />
    </svg>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────

const OperationsCenter: React.FC = () => {
  const [activeTab, setActiveTab] = useState<ActiveTab>("overview");
  const [systemMetrics, setSystemMetrics] = useState<SystemMetrics | null>(null);
  const [serviceHealth, setServiceHealth] = useState<ServiceHealth | null>(null);
  const [alerts, setAlerts] = useState<AlertEvent[]>([]);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [backups, setBackups] = useState<BackupFile[]>([]);
  const [securityEvents, setSecurityEvents] = useState<SecurityEvent[]>([]);
  const [ipBlocks, setIPBlocks] = useState<IPBlock[]>([]);
  const [metricHistory, setMetricHistory] = useState<MetricHistory[]>([]);
  const [loading, setLoading] = useState(true);
  const [lastRefresh, setLastRefresh] = useState<string>("");
  const [logSearch, setLogSearch] = useState("");
  const [logService, setLogService] = useState("");
  const [logLevel, setLogLevel] = useState("");
  const [alertFilter, setAlertFilter] = useState<"all" | "critical" | "warning">("all");
  const [backupRunning, setBackupRunning] = useState(false);
  const [blockIP, setBlockIP] = useState("");
  const [blockReason, setBlockReason] = useState("");
  const [newBlockVisible, setNewBlockVisible] = useState(false);
  const [drStatus, setDrStatus] = useState<{ all_healthy: boolean; recommendations: unknown[]; services?: Record<string, ServiceStatus | string> } | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const [simulationMetrics, setSimulationMetrics] = useState({ running: 0, queued: 0, failed: 0 });

  const fetchWithFallback = useCallback(async (path: string, fallback: unknown = null) => {
    try {
      const token = localStorage.getItem("pypy_token");
      const res = await fetch(`${API_BASE}${path}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!res.ok) return fallback;
      return await res.json();
    } catch {
      return fallback;
    }
  }, []);

  const refreshAll = useCallback(async () => {
    const [sys, svc, alrt, lg, bk, sec, ipb, hist, dr, snap] = await Promise.all([
      fetchWithFallback("/operations/metrics/system"),
      fetchWithFallback("/operations/metrics/services"),
      fetchWithFallback("/operations/alerts?limit=50"),
      fetchWithFallback("/operations/logs?limit=100"),
      fetchWithFallback("/operations/backups"),
      fetchWithFallback("/security/audit-events?limit=50"),
      fetchWithFallback("/security/ip-blocks"),
      fetchWithFallback("/operations/metrics/history?limit=60"),
      fetchWithFallback("/operations/disaster-recovery/status"),
      fetchWithFallback("/operations/metrics/snapshot"),
    ]);

    if (sys) setSystemMetrics(sys as SystemMetrics);
    if (svc) setServiceHealth(svc as ServiceHealth);
    if (alrt) setAlerts(alrt as AlertEvent[]);
    if (lg) setLogs(lg as LogEntry[]);
    if (bk) setBackups(bk as BackupFile[]);
    if (sec) setSecurityEvents(sec as SecurityEvent[]);
    if (ipb) setIPBlocks(ipb as IPBlock[]);
    if (hist) setMetricHistory(hist as MetricHistory[]);
    if (dr) setDrStatus(dr as { all_healthy: boolean; recommendations: unknown[] });
    if (snap) {
      const s = snap as { simulations?: { running_simulations?: number; queued_simulations?: number; failed_simulations?: number } };
      setSimulationMetrics({
        running: s.simulations?.running_simulations ?? 0,
        queued: s.simulations?.queued_simulations ?? 0,
        failed: s.simulations?.failed_simulations ?? 0,
      });
    }
    setLastRefresh(new Date().toLocaleTimeString());
    setLoading(false);
  }, [fetchWithFallback]);

  useEffect(() => {
    refreshAll();
    intervalRef.current = setInterval(refreshAll, REFRESH_INTERVAL_MS);
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, [refreshAll]);

  const acknowledgeAlert = async (alertId: string) => {
    const token = localStorage.getItem("pypy_token");
    await fetch(`${API_BASE}/operations/alerts/${alertId}/acknowledge`, {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    setAlerts(prev => prev.map(a => a.id === alertId ? { ...a, acknowledged: true } : a));
  };

  const runBackup = async (type: "postgres" | "full") => {
    setBackupRunning(true);
    const token = localStorage.getItem("pypy_token");
    try {
      await fetch(`${API_BASE}/operations/backups/run/${type}`, {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      await refreshAll();
    } finally {
      setBackupRunning(false);
    }
  };

  const deleteBackup = async (filename: string) => {
    if (!window.confirm(`Delete backup: ${filename}?`)) return;
    const token = localStorage.getItem("pypy_token");
    await fetch(`${API_BASE}/operations/backups/${encodeURIComponent(filename)}`, {
      method: "DELETE",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    setBackups(prev => prev.filter(b => b.filename !== filename));
  };

  const submitIPBlock = async () => {
    if (!blockIP) return;
    const token = localStorage.getItem("pypy_token");
    await fetch(`${API_BASE}/security/ip-blocks`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ ip_address: blockIP, reason: blockReason || "manual_block", blocked_hours: 24 }),
    });
    setBlockIP(""); setBlockReason(""); setNewBlockVisible(false);
    await refreshAll();
  };

  const unblockIP = async (ip: string) => {
    const token = localStorage.getItem("pypy_token");
    await fetch(`${API_BASE}/security/ip-blocks/${encodeURIComponent(ip)}`, {
      method: "DELETE",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    setIPBlocks(prev => prev.filter(b => b.ip_address !== ip));
  };

  const criticalAlerts = alerts.filter(a => !a.acknowledged && a.severity === "critical").length;
  const filteredAlerts = alerts.filter(a => alertFilter === "all" || a.severity === alertFilter);
  const filteredLogs = logs.filter(l =>
    (!logSearch || l.message.toLowerCase().includes(logSearch.toLowerCase())) &&
    (!logService || l.service === logService) &&
    (!logLevel || l.level === logLevel)
  );
  const cpuHistory = metricHistory.map(m => m.cpu_percent);
  const ramHistory = metricHistory.map(m => m.ram_percent);
  const latencyHistory = metricHistory.map(m => m.avg_latency_ms);

  // ─── Styles ─────────────────────────────────────────────────────────────────

  const styles = {
    container: {
      background: "linear-gradient(135deg, #0a0e1a 0%, #0d1225 50%, #0a1020 100%)",
      minHeight: "100vh",
      color: "#e2e8f0",
      fontFamily: "'Inter', 'Segoe UI', sans-serif",
      padding: "24px",
    } as React.CSSProperties,
    header: {
      display: "flex",
      justifyContent: "space-between",
      alignItems: "center",
      marginBottom: 24,
    } as React.CSSProperties,
    title: {
      fontSize: 28,
      fontWeight: 800,
      background: "linear-gradient(90deg, #6366f1, #8b5cf6, #06b6d4)",
      WebkitBackgroundClip: "text",
      WebkitTextFillColor: "transparent",
      backgroundClip: "text",
    } as React.CSSProperties,
    badge: (color: string) => ({
      display: "inline-flex",
      alignItems: "center",
      gap: 6,
      padding: "4px 12px",
      borderRadius: 20,
      background: `${color}22`,
      border: `1px solid ${color}55`,
      color,
      fontSize: 12,
      fontWeight: 600,
    } as React.CSSProperties),
    tabs: {
      display: "flex",
      gap: 4,
      marginBottom: 24,
      background: "rgba(255,255,255,0.04)",
      padding: 4,
      borderRadius: 12,
      overflowX: "auto" as const,
    } as React.CSSProperties,
    tab: (active: boolean) => ({
      padding: "8px 16px",
      borderRadius: 8,
      border: "none",
      cursor: "pointer",
      fontWeight: 600,
      fontSize: 13,
      transition: "all 0.2s",
      whiteSpace: "nowrap" as const,
      background: active ? "linear-gradient(135deg, #6366f1, #8b5cf6)" : "transparent",
      color: active ? "#fff" : "rgba(255,255,255,0.55)",
    } as React.CSSProperties),
    card: {
      background: "rgba(255,255,255,0.04)",
      border: "1px solid rgba(255,255,255,0.08)",
      borderRadius: 16,
      padding: "20px",
      backdropFilter: "blur(12px)",
    } as React.CSSProperties,
    grid2: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 } as React.CSSProperties,
    grid3: { display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16 } as React.CSSProperties,
    grid4: { display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16 } as React.CSSProperties,
    gridMeta: { display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: 12 } as React.CSSProperties,
    serviceChip: (status: string) => ({
      display: "flex",
      alignItems: "center",
      gap: 8,
      padding: "10px 14px",
      background: "rgba(255,255,255,0.04)",
      borderRadius: 10,
      border: `1px solid ${getStatusColor(status)}33`,
    } as React.CSSProperties),
    dot: (color: string) => ({
      width: 8, height: 8,
      borderRadius: "50%",
      background: color,
      boxShadow: `0 0 6px ${color}`,
      flexShrink: 0,
    } as React.CSSProperties),
    sectionTitle: {
      fontSize: 14,
      fontWeight: 700,
      color: "rgba(255,255,255,0.9)",
      marginBottom: 12,
      display: "flex",
      alignItems: "center",
      gap: 8,
    } as React.CSSProperties,
    table: {
      width: "100%",
      borderCollapse: "collapse" as const,
      fontSize: 13,
    } as React.CSSProperties,
    th: {
      textAlign: "left" as const,
      padding: "8px 12px",
      borderBottom: "1px solid rgba(255,255,255,0.08)",
      color: "rgba(255,255,255,0.5)",
      fontWeight: 600,
      fontSize: 11,
      textTransform: "uppercase" as const,
      letterSpacing: "0.05em",
    } as React.CSSProperties,
    td: {
      padding: "8px 12px",
      borderBottom: "1px solid rgba(255,255,255,0.04)",
      color: "rgba(255,255,255,0.8)",
    } as React.CSSProperties,
    input: {
      background: "rgba(255,255,255,0.06)",
      border: "1px solid rgba(255,255,255,0.12)",
      borderRadius: 8,
      padding: "8px 12px",
      color: "#e2e8f0",
      fontSize: 13,
      outline: "none",
      width: "100%",
    } as React.CSSProperties,
    btn: (color: string = "#6366f1") => ({
      background: `linear-gradient(135deg, ${color}, ${color}cc)`,
      border: "none",
      borderRadius: 8,
      padding: "8px 16px",
      color: "#fff",
      fontWeight: 600,
      fontSize: 13,
      cursor: "pointer",
      transition: "opacity 0.2s",
    } as React.CSSProperties),
    btnGhost: {
      background: "rgba(255,255,255,0.06)",
      border: "1px solid rgba(255,255,255,0.12)",
      borderRadius: 8,
      padding: "6px 12px",
      color: "rgba(255,255,255,0.7)",
      fontWeight: 600,
      fontSize: 12,
      cursor: "pointer",
    } as React.CSSProperties,
  };

  if (loading) {
    return (
      <div style={{ ...styles.container, display: "flex", alignItems: "center", justifyContent: "center" }}>
        <div style={{ textAlign: "center" }}>
          <div style={{ fontSize: 48, marginBottom: 16 }}>🔭</div>
          <div style={{ fontSize: 18, fontWeight: 700, color: "#6366f1" }}>Loading Operations Center...</div>
        </div>
      </div>
    );
  }

  // ─── Render ─────────────────────────────────────────────────────────────────

  return (
    <div style={styles.container}>
      {/* Header */}
      <div style={styles.header}>
        <div>
          <div style={styles.title}>⚙️ Operations Center</div>
          <div style={{ fontSize: 13, color: "rgba(255,255,255,0.4)", marginTop: 4 }}>
            V11.8 · Observability, Security & Backup · Auto-refreshes every 5s · Last: {lastRefresh}
          </div>
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          {criticalAlerts > 0 && (
            <div style={styles.badge("#ef4444")}>
              🔴 {criticalAlerts} Critical Alert{criticalAlerts > 1 ? "s" : ""}
            </div>
          )}
          {drStatus && !drStatus.all_healthy && (
            <div style={styles.badge("#f59e0b")}>⚠️ Service Degraded</div>
          )}
          {drStatus?.all_healthy && <div style={styles.badge("#22c55e")}>✅ All Systems Healthy</div>}
          <button style={styles.btn()} onClick={refreshAll}>↻ Refresh</button>
        </div>
      </div>

      {/* Tab Navigation */}
      <div style={styles.tabs}>
        {([
          ["overview", "📊 Overview"],
          ["metrics", "📈 Metrics"],
          ["alerts", `🚨 Alerts ${alerts.filter(a => !a.acknowledged).length > 0 ? `(${alerts.filter(a => !a.acknowledged).length})` : ""}`],
          ["logs", "📋 Logs"],
          ["backups", "💾 Backups"],
          ["security", "🔒 Security"],
          ["dr", "🏥 Disaster Recovery"],
        ] as [ActiveTab, string][]).map(([id, label]) => (
          <button key={id} style={styles.tab(activeTab === id)} onClick={() => setActiveTab(id)}>
            {label}
          </button>
        ))}
      </div>

      {/* ─── OVERVIEW TAB ──────────────────────────────────────────────────── */}
      {activeTab === "overview" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          {/* Service Health Grid */}
          <div style={styles.card}>
            <div style={styles.sectionTitle}>🌐 Service Health</div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 10 }}>
              {serviceHealth && Object.entries(serviceHealth).filter(([k]) => k !== "timestamp").map(([key, info]) => {
                const s = (info as ServiceStatus);
                return (
                  <div key={key} style={styles.serviceChip(s.status)}>
                    <div style={styles.dot(getStatusColor(s.status))} />
                    <div>
                      <div style={{ fontSize: 13, fontWeight: 600 }}>{SERVICE_LABELS[key] || key}</div>
                      <div style={{ fontSize: 11, color: getStatusColor(s.status), textTransform: "capitalize" }}>
                        {s.status}{s.port ? ` :${s.port}` : ""}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Resource Gauges */}
          <div style={styles.card}>
            <div style={styles.sectionTitle}>💻 Resource Utilisation</div>
            <div style={{ display: "flex", justifyContent: "space-around", flexWrap: "wrap" }}>
              {systemMetrics && <>
                <GaugeMeter value={systemMetrics.cpu_percent} label="CPU" />
                <GaugeMeter value={systemMetrics.ram_percent} label="RAM" />
                <GaugeMeter value={systemMetrics.disk_percent} label="Disk" thresholds={[80, 90]} />
                <GaugeMeter value={systemMetrics.load_avg_1m * 25} label="Load Avg" unit="" thresholds={[60, 85]} />
              </>}
            </div>
            {systemMetrics && (
              <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12, marginTop: 16 }}>
                {[
                  ["RAM Used", `${formatBytes(systemMetrics.ram_used_mb)} / ${formatBytes(systemMetrics.ram_total_mb)}`],
                  ["Disk Used", `${systemMetrics.disk_used_gb} GB / ${systemMetrics.disk_total_gb} GB`],
                  ["Net ↑", `${formatBytes(systemMetrics.net_sent_mb)}`],
                  ["Net ↓", `${formatBytes(systemMetrics.net_recv_mb)}`],
                ].map(([label, value]) => (
                  <div key={label} style={{ textAlign: "center", padding: "8px", background: "rgba(255,255,255,0.03)", borderRadius: 8 }}>
                    <div style={{ fontSize: 11, color: "rgba(255,255,255,0.45)", marginBottom: 4 }}>{label}</div>
                    <div style={{ fontSize: 14, fontWeight: 700 }}>{value}</div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Simulation & AI Quick Stats */}
          <div style={styles.grid3}>
            {[
              { label: "Running Sims", value: simulationMetrics.running, color: "#22c55e", icon: "⚡" },
              { label: "Queued Sims", value: simulationMetrics.queued, color: "#6366f1", icon: "🔄" },
              { label: "Failed Sims", value: simulationMetrics.failed, color: "#ef4444", icon: "❌" },
            ].map(({ label, value, color, icon }) => (
              <div key={label} style={{ ...styles.card, textAlign: "center" }}>
                <div style={{ fontSize: 32 }}>{icon}</div>
                <div style={{ fontSize: 32, fontWeight: 800, color, marginTop: 4 }}>{value}</div>
                <div style={{ fontSize: 13, color: "rgba(255,255,255,0.5)", marginTop: 4 }}>{label}</div>
              </div>
            ))}
          </div>

          {/* Recent Alerts */}
          {alerts.filter(a => !a.acknowledged).length > 0 && (
            <div style={styles.card}>
              <div style={styles.sectionTitle}>🚨 Active Alerts</div>
              {alerts.filter(a => !a.acknowledged).slice(0, 5).map(alert => (
                <div key={alert.id} style={{
                  display: "flex", justifyContent: "space-between", alignItems: "center",
                  padding: "10px 14px", borderRadius: 10, marginBottom: 8,
                  background: `${SEVERITY_COLORS[alert.severity]}11`,
                  border: `1px solid ${SEVERITY_COLORS[alert.severity]}33`,
                }}>
                  <div>
                    <span style={{ color: SEVERITY_COLORS[alert.severity], fontWeight: 700, fontSize: 13 }}>
                      [{alert.severity.toUpperCase()}]
                    </span>
                    <span style={{ marginLeft: 8, fontSize: 13 }}>{alert.rule_name}: {alert.message}</span>
                  </div>
                  <button style={styles.btnGhost} onClick={() => acknowledgeAlert(alert.id)}>ACK</button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ─── METRICS TAB ───────────────────────────────────────────────────── */}
      {activeTab === "metrics" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          <div style={styles.grid2}>
            <div style={styles.card}>
              <div style={styles.sectionTitle}>📈 CPU % (last 60 snapshots)</div>
              <MiniChart data={cpuHistory} color="#6366f1" />
              <div style={{ fontSize: 12, color: "rgba(255,255,255,0.4)", marginTop: 8 }}>
                Current: {systemMetrics?.cpu_percent.toFixed(1)}%
              </div>
            </div>
            <div style={styles.card}>
              <div style={styles.sectionTitle}>💾 RAM % (last 60 snapshots)</div>
              <MiniChart data={ramHistory} color="#8b5cf6" />
              <div style={{ fontSize: 12, color: "rgba(255,255,255,0.4)", marginTop: 8 }}>
                Current: {systemMetrics?.ram_percent.toFixed(1)}%
              </div>
            </div>
          </div>
          <div style={styles.grid2}>
            <div style={styles.card}>
              <div style={styles.sectionTitle}>⏱ API Latency ms</div>
              <MiniChart data={latencyHistory} color="#06b6d4" />
            </div>
            <div style={styles.card}>
              <div style={styles.sectionTitle}>📊 System Load Avg (1m / 5m / 15m)</div>
              <div style={{ display: "flex", gap: 24, marginTop: 12 }}>
                {systemMetrics && [
                  ["1m", systemMetrics.load_avg_1m],
                  ["5m", systemMetrics.load_avg_5m],
                  ["15m", systemMetrics.load_avg_15m],
                ].map(([label, v]) => (
                  <div key={label} style={{ textAlign: "center" }}>
                    <div style={{ fontSize: 24, fontWeight: 800, color: "#6366f1" }}>{(v as number).toFixed(2)}</div>
                    <div style={{ fontSize: 11, color: "rgba(255,255,255,0.45)" }}>{label}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
          <div style={styles.card}>
            <div style={styles.sectionTitle}>🔗 Prometheus Scrape Endpoint</div>
            <div style={{ fontFamily: "monospace", fontSize: 12, color: "#06b6d4", background: "rgba(6,182,212,0.06)", padding: "10px 14px", borderRadius: 8 }}>
              GET /api/operations/metrics/prometheus
            </div>
            <div style={{ fontSize: 12, color: "rgba(255,255,255,0.4)", marginTop: 8 }}>
              Point your Prometheus scrape config at this endpoint. Grafana dashboard JSON available in <code>monitoring/grafana/dashboards/pypy_operations.json</code>.
            </div>
          </div>
        </div>
      )}

      {/* ─── ALERTS TAB ────────────────────────────────────────────────────── */}
      {activeTab === "alerts" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div style={{ display: "flex", gap: 8 }}>
            {(["all", "critical", "warning"] as const).map(f => (
              <button key={f} style={styles.tab(alertFilter === f)} onClick={() => setAlertFilter(f)}>
                {f.toUpperCase()}
              </button>
            ))}
            <div style={{ flex: 1 }} />
            <button style={styles.btn("#ef4444")} onClick={async () => {
              const token = localStorage.getItem("pypy_token");
              await fetch(`${API_BASE}/operations/alerts/evaluate`, {
                method: "POST",
                headers: token ? { Authorization: `Bearer ${token}` } : {},
              });
              await refreshAll();
            }}>
              ⚡ Run Evaluation
            </button>
          </div>
          <div style={styles.card}>
            <table style={styles.table}>
              <thead>
                <tr>
                  <th style={styles.th}>Severity</th>
                  <th style={styles.th}>Rule</th>
                  <th style={styles.th}>Message</th>
                  <th style={styles.th}>Fired At</th>
                  <th style={styles.th}>Status</th>
                  <th style={styles.th}>Action</th>
                </tr>
              </thead>
              <tbody>
                {filteredAlerts.length === 0 && (
                  <tr><td colSpan={6} style={{ ...styles.td, textAlign: "center", color: "rgba(255,255,255,0.3)" }}>
                    No alerts found.
                  </td></tr>
                )}
                {filteredAlerts.map(alert => (
                  <tr key={alert.id}>
                    <td style={styles.td}>
                      <span style={{ color: SEVERITY_COLORS[alert.severity], fontWeight: 700 }}>
                        {alert.severity.toUpperCase()}
                      </span>
                    </td>
                    <td style={styles.td}>{alert.rule_name}</td>
                    <td style={styles.td}>{alert.message}</td>
                    <td style={styles.td}>{formatDate(alert.fired_at)}</td>
                    <td style={styles.td}>
                      <span style={{ color: alert.acknowledged ? "#22c55e" : "#f59e0b" }}>
                        {alert.acknowledged ? "✅ ACK" : "🔔 Active"}
                      </span>
                    </td>
                    <td style={styles.td}>
                      {!alert.acknowledged && (
                        <button style={styles.btnGhost} onClick={() => acknowledgeAlert(alert.id)}>ACK</button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ─── LOGS TAB ──────────────────────────────────────────────────────── */}
      {activeTab === "logs" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div style={{ display: "flex", gap: 10 }}>
            <input
              style={{ ...styles.input, maxWidth: 300 }}
              placeholder="Search logs..."
              value={logSearch}
              onChange={e => setLogSearch(e.target.value)}
            />
            <select style={{ ...styles.input, maxWidth: 180 }} value={logService} onChange={e => setLogService(e.target.value)}>
              <option value="">All Services</option>
              {["gateway", "copilot", "simulation", "billing", "experiments", "marketplace"].map(s => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
            <select style={{ ...styles.input, maxWidth: 140 }} value={logLevel} onChange={e => setLogLevel(e.target.value)}>
              <option value="">All Levels</option>
              {["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"].map(l => (
                <option key={l} value={l}>{l}</option>
              ))}
            </select>
          </div>
          <div style={{ ...styles.card, maxHeight: 520, overflowY: "auto" }}>
            <table style={styles.table}>
              <thead style={{ position: "sticky", top: 0, background: "#0d1225" }}>
                <tr>
                  <th style={styles.th}>Time</th>
                  <th style={styles.th}>Service</th>
                  <th style={styles.th}>Level</th>
                  <th style={styles.th}>Message</th>
                </tr>
              </thead>
              <tbody>
                {filteredLogs.length === 0 && (
                  <tr><td colSpan={4} style={{ ...styles.td, textAlign: "center", color: "rgba(255,255,255,0.3)" }}>
                    No logs found.
                  </td></tr>
                )}
                {filteredLogs.map(log => (
                  <tr key={log.id}>
                    <td style={{ ...styles.td, whiteSpace: "nowrap", fontSize: 11 }}>{formatDate(log.logged_at)}</td>
                    <td style={{ ...styles.td, fontWeight: 600, color: "#6366f1" }}>{log.service}</td>
                    <td style={styles.td}>
                      <span style={{ color: LEVEL_COLORS[log.level] || "#fff", fontWeight: 700, fontSize: 11 }}>
                        {log.level}
                      </span>
                    </td>
                    <td style={{ ...styles.td, fontFamily: "monospace", fontSize: 12 }}>{log.message}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ─── BACKUPS TAB ───────────────────────────────────────────────────── */}
      {activeTab === "backups" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div style={{ display: "flex", gap: 10 }}>
            <button style={styles.btn("#22c55e")} disabled={backupRunning} onClick={() => runBackup("postgres")}>
              {backupRunning ? "Running..." : "💾 Backup Postgres"}
            </button>
            <button style={styles.btn("#6366f1")} disabled={backupRunning} onClick={() => runBackup("full")}>
              {backupRunning ? "Running..." : "📦 Full Backup"}
            </button>
          </div>
          <div style={styles.card}>
            <div style={styles.sectionTitle}>💾 Backup Archive ({backups.length} files)</div>
            <table style={styles.table}>
              <thead>
                <tr>
                  <th style={styles.th}>Filename</th>
                  <th style={styles.th}>Size</th>
                  <th style={styles.th}>Created</th>
                  <th style={styles.th}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {backups.length === 0 && (
                  <tr><td colSpan={4} style={{ ...styles.td, textAlign: "center", color: "rgba(255,255,255,0.3)" }}>
                    No backups found. Run a backup to get started.
                  </td></tr>
                )}
                {backups.map(bk => (
                  <tr key={bk.filename}>
                    <td style={{ ...styles.td, fontFamily: "monospace", fontSize: 12 }}>{bk.filename}</td>
                    <td style={styles.td}>{bk.size_mb.toFixed(2)} MB</td>
                    <td style={styles.td}>{formatDate(bk.created_at)}</td>
                    <td style={styles.td}>
                      <div style={{ display: "flex", gap: 6 }}>
                        <button style={styles.btnGhost} onClick={async () => {
                          const token = localStorage.getItem("pypy_token");
                          const res = await fetch(`${API_BASE}/operations/backups/${encodeURIComponent(bk.filename)}/restore`, {
                            method: "POST",
                            headers: token ? { Authorization: `Bearer ${token}` } : {},
                          });
                          const data = await res.json();
                          alert(data.message || data.error || "Restore triggered.");
                        }}>↩ Restore</button>
                        <button style={{ ...styles.btnGhost, color: "#ef4444" }} onClick={() => deleteBackup(bk.filename)}>🗑</button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ─── SECURITY TAB ──────────────────────────────────────────────────── */}
      {activeTab === "security" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div style={styles.grid2}>
            <div style={styles.card}>
              <div style={styles.sectionTitle}>🛡 Security Posture</div>
              {[
                ["Rate Limiting", "150 req/min per IP", "#22c55e"],
                ["JWT Expiry", "15 min (900s)", "#22c55e"],
                ["Brute Force", "5 attempts → 15 min lockout", "#22c55e"],
                ["Security Headers", "HSTS, X-Frame-Options, nosniff", "#22c55e"],
                ["CORS", "Env-var driven allowlist", "#22c55e"],
                ["IP Blocking", `${ipBlocks.length} active blocks`, ipBlocks.length > 0 ? "#f59e0b" : "#22c55e"],
              ].map(([label, value, color]) => (
                <div key={label} style={{ display: "flex", justifyContent: "space-between", padding: "8px 0", borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
                  <span style={{ fontSize: 13, color: "rgba(255,255,255,0.6)" }}>{label}</span>
                  <span style={{ fontSize: 13, fontWeight: 600, color: color as string }}>{value}</span>
                </div>
              ))}
            </div>
            <div style={styles.card}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                <div style={styles.sectionTitle}>🚫 Active IP Blocks ({ipBlocks.length})</div>
                <button style={styles.btn("#ef4444")} onClick={() => setNewBlockVisible(!newBlockVisible)}>+ Block IP</button>
              </div>
              {newBlockVisible && (
                <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
                  <input style={styles.input} placeholder="IP Address (e.g. 192.168.1.100)" value={blockIP} onChange={e => setBlockIP(e.target.value)} />
                  <input style={styles.input} placeholder="Reason" value={blockReason} onChange={e => setBlockReason(e.target.value)} />
                  <button style={styles.btn("#ef4444")} onClick={submitIPBlock}>Block</button>
                </div>
              )}
              {ipBlocks.length === 0 && <div style={{ fontSize: 13, color: "rgba(255,255,255,0.3)" }}>No active IP blocks.</div>}
              {ipBlocks.map(b => (
                <div key={b.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "8px 0", borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
                  <div>
                    <span style={{ fontFamily: "monospace", fontSize: 13 }}>{b.ip_address}</span>
                    <span style={{ fontSize: 11, color: "rgba(255,255,255,0.4)", marginLeft: 8 }}>{b.reason}</span>
                  </div>
                  <button style={{ ...styles.btnGhost, color: "#ef4444" }} onClick={() => unblockIP(b.ip_address)}>Unblock</button>
                </div>
              ))}
            </div>
          </div>
          <div style={styles.card}>
            <div style={styles.sectionTitle}>📋 Security Audit Events</div>
            <div style={{ maxHeight: 400, overflowY: "auto" }}>
              <table style={styles.table}>
                <thead style={{ position: "sticky", top: 0, background: "#0d1225" }}>
                  <tr>
                    <th style={styles.th}>Time</th>
                    <th style={styles.th}>Event Type</th>
                    <th style={styles.th}>IP</th>
                    <th style={styles.th}>Description</th>
                  </tr>
                </thead>
                <tbody>
                  {securityEvents.length === 0 && (
                    <tr><td colSpan={4} style={{ ...styles.td, textAlign: "center", color: "rgba(255,255,255,0.3)" }}>No security events recorded.</td></tr>
                  )}
                  {securityEvents.map(ev => (
                    <tr key={ev.id}>
                      <td style={{ ...styles.td, fontSize: 11, whiteSpace: "nowrap" }}>{formatDate(ev.occurred_at)}</td>
                      <td style={styles.td}>
                        <span style={{ color: ev.event_type.includes("FAIL") || ev.event_type.includes("LOCK") || ev.event_type.includes("BLOCK") ? "#ef4444" : "#22c55e", fontWeight: 700, fontSize: 12 }}>
                          {ev.event_type}
                        </span>
                      </td>
                      <td style={{ ...styles.td, fontFamily: "monospace", fontSize: 12 }}>{ev.ip_address}</td>
                      <td style={{ ...styles.td, fontSize: 12 }}>{ev.description}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* ─── DISASTER RECOVERY TAB ─────────────────────────────────────────── */}
      {activeTab === "dr" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div style={styles.card}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div style={styles.sectionTitle}>🏥 Disaster Recovery Status</div>
              <div style={drStatus?.all_healthy ? styles.badge("#22c55e") : styles.badge("#ef4444")}>
                {drStatus?.all_healthy ? "✅ All Services Online" : "❌ Services Degraded"}
              </div>
            </div>
            {drStatus && Object.entries(drStatus.services || {}).filter(([k]) => k !== "timestamp").map(([service, info]) => {
              const s = info as ServiceStatus;
              return (
                <div key={service} style={{ ...styles.serviceChip(s.status), marginBottom: 8 }}>
                  <div style={styles.dot(getStatusColor(s.status))} />
                  <div style={{ flex: 1 }}>
                    <span style={{ fontWeight: 600 }}>{SERVICE_LABELS[service] || service}</span>
                    <span style={{ fontSize: 12, color: "rgba(255,255,255,0.4)", marginLeft: 10 }}>
                      {s.port ? `Port ${s.port}` : "Internal"}
                    </span>
                  </div>
                  <span style={{ color: getStatusColor(s.status), fontWeight: 700, fontSize: 13 }}>
                    {s.status.toUpperCase()}
                  </span>
                </div>
              );
            })}
          </div>
          {drStatus && (drStatus.recommendations as { service: string; recommendation: string; command: string }[]).length > 0 && (
            <div style={styles.card}>
              <div style={styles.sectionTitle}>🔧 Recovery Recommendations</div>
              {(drStatus.recommendations as { service: string; recommendation: string; command: string }[]).map((r, i) => (
                <div key={i} style={{ padding: "12px 16px", background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.25)", borderRadius: 10, marginBottom: 10 }}>
                  <div style={{ fontWeight: 700, color: "#ef4444", marginBottom: 6 }}>⚠️ {r.recommendation}</div>
                  <div style={{ fontFamily: "monospace", fontSize: 12, background: "rgba(0,0,0,0.3)", padding: "8px 12px", borderRadius: 6, color: "#06b6d4" }}>
                    $ {r.command}
                  </div>
                </div>
              ))}
            </div>
          )}
          <div style={styles.card}>
            <div style={styles.sectionTitle}>📝 Recovery Playbook</div>
            {[
              ["Gateway Offline", "docker compose restart gateway && docker compose logs -f gateway"],
              ["Redis Offline", "docker compose restart redis && redis-cli ping"],
              ["MQTT Offline", "docker compose restart mqtt && mosquitto_sub -t '#' -C 1"],
              ["Postgres Offline", "docker compose restart postgres && psql -U pypy_admin -d pypy_saas -c '\\l'"],
              ["Worker Offline", "docker compose restart celery_worker celery_beat"],
              ["Full Recovery", "./scripts/deploy_local.sh"],
            ].map(([scenario, cmd]) => (
              <div key={scenario} style={{ marginBottom: 12 }}>
                <div style={{ fontSize: 13, fontWeight: 600, color: "rgba(255,255,255,0.7)", marginBottom: 4 }}>{scenario}</div>
                <div style={{ fontFamily: "monospace", fontSize: 12, background: "rgba(0,0,0,0.3)", padding: "8px 12px", borderRadius: 6, color: "#06b6d4" }}>
                  $ {cmd}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default OperationsCenter;
