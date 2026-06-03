import { useState, useEffect, useRef } from "react";
import { NativeModules } from "react-native";

interface Alert {
  id: string;
  source: string;
  event: string;
  severity: "CRITICAL" | "WARNING" | "INFO";
  timestamp: number;
  acknowledged: boolean;
}

interface Telemetry {
  voltages: Record<string, number>;
  breakers: Record<string, number>;
  threat_score: number;
  attack_active: boolean;
  isStale: boolean;
}

const DEFAULT_TELEMETRY: Telemetry = {
  voltages: {
    Bus_1: 1.0, Bus_2: 1.0, Bus_3: 1.0,
    Bus_4: 1.0, Bus_5: 1.0, Bus_6: 1.0,
    Bus_7: 1.0, Bus_8: 1.0, Bus_9: 1.0
  },
  breakers: {
    L1_4: 1, L2_5: 1, L3_6: 1,
    L4_5: 1, L5_7: 1, L6_8: 1,
    L7_8: 1, L8_9: 1
  },
  threat_score: 0.0,
  attack_active: false,
  isStale: true
};

const getGatewayHost = () => {
  try {
    const scriptURL = NativeModules.SourceCode?.scriptURL || "";
    if (scriptURL) {
      const match = scriptURL.match(/https?:\/\/([^:/]+)(:\d+)?/);
      if (match && match[1]) {
        const host = match[1];
        if (host !== "localhost" && host !== "127.0.0.1") {
          return host;
        }
      }
    }
  } catch (e) {
    console.log("[useWebSocket] Failed to extract host from scriptURL:", e);
  }
  return "localhost";
};

export const useWebSocket = () => {
  const [connected, setConnected] = useState(false);
  const [latency, setLatency] = useState<number | null>(null);
  const [telemetry, setTelemetry] = useState<Telemetry>(DEFAULT_TELEMETRY);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [reconnectCountdown, setReconnectCountdown] = useState<number>(0);
  
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const heartbeatIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const lastTelemetryTimeRef = useRef<number>(0);
  const pingTimeRef = useRef<number>(0);

  const connect = () => {
    const host = getGatewayHost();
    const wsUrl = `ws://${host}:8000/ws`;
    console.log(`[useWebSocket] Syncing with gateway at: ${wsUrl}`);
    
    if (wsRef.current) {
      try {
        wsRef.current.close();
      } catch (e) {}
    }

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log(`[useWebSocket] Connected to gateway at ${wsUrl}`);
        setConnected(true);
        setReconnectCountdown(0);
        lastTelemetryTimeRef.current = Date.now();
        
        // Start heartbeat pinging every 10 seconds
        if (heartbeatIntervalRef.current) clearInterval(heartbeatIntervalRef.current);
        heartbeatIntervalRef.current = setInterval(() => {
          if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
            pingTimeRef.current = Date.now();
            wsRef.current.send(JSON.stringify({
              topic: "grid/ping",
              payload: { timestamp: pingTimeRef.current }
            }));
          }
        }, 10000);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          // 1. Handle PONG response for latency checks
          if (data.type === "PONG") {
            const now = Date.now();
            setLatency(now - pingTimeRef.current);
            return;
          }

          // 2. Handle BOOTSTRAP payload
          if (data.type === "BOOTSTRAP") {
            lastTelemetryTimeRef.current = Date.now();
            const t = data.telemetry ?? {};
            const threat = data.threat ?? {};
            setTelemetry({
              voltages: t.voltages ?? DEFAULT_TELEMETRY.voltages,
              breakers: t.breakers ?? DEFAULT_TELEMETRY.breakers,
              threat_score: threat.threat_score ?? 0.0,
              attack_active: threat.attack_active ?? false,
              isStale: false
            });

            if (data.alerts && Array.isArray(data.alerts)) {
              const mappedAlerts: Alert[] = data.alerts.map((a: any) => ({
                id: a.alert_id ?? a.id ?? String(Math.random()),
                source: a.source ?? "SYSTEM",
                event: a.event ?? a.msg ?? "Grid anomaly",
                severity: a.severity ?? "WARNING",
                timestamp: a.timestamp ?? Date.now(),
                acknowledged: a.acknowledged ?? false
              }));
              setAlerts(mappedAlerts);
            }
            return;
          }

          // 3. Handle incremental MQTT broadcasts from gateway (formatted as { topic, payload })
          const topic = data.topic;
          const payload = data.payload;

          if (topic && payload) {
            if (topic === "grid/telemetry") {
              lastTelemetryTimeRef.current = Date.now();
              setTelemetry(prev => ({
                ...prev,
                voltages: payload.voltages ?? prev.voltages,
                breakers: payload.breakers ?? prev.breakers,
                isStale: false
              }));
            } else if (topic === "grid/threat") {
              setTelemetry(prev => ({
                ...prev,
                threat_score: payload.threat_score ?? prev.threat_score,
                attack_active: payload.attack_active ?? prev.attack_active
              }));
            } else if (topic === "grid/alerts") {
              const newAlert: Alert = {
                id: payload.alert_id ?? payload.id ?? String(Math.random()),
                source: payload.source ?? "SYSTEM",
                event: payload.event ?? payload.msg ?? "Grid intrusion warning",
                severity: payload.severity ?? "WARNING",
                timestamp: payload.timestamp ?? Date.now(),
                acknowledged: payload.acknowledged ?? false
              };
              setAlerts(prev => {
                // Deduplicate alerts
                if (prev.some(a => a.id === newAlert.id)) return prev;
                return [newAlert, ...prev];
              });
            }
          }
        } catch (err) {
          console.error("Error parsing gateway WebSocket frame:", err);
        }
      };

      ws.onerror = (e) => {
        console.warn("[useWebSocket] Socket error:", e);
        setConnected(false);
      };

      ws.onclose = (e) => {
        console.log("[useWebSocket] Socket closed:", e.code, e.reason);
        handleDisconnect();
      };
    } catch (err) {
      console.warn("[useWebSocket] Error instantiating WebSocket:", err);
      handleDisconnect();
    }
  };

  const handleDisconnect = () => {
    setConnected(false);
    setLatency(null);
    if (heartbeatIntervalRef.current) clearInterval(heartbeatIntervalRef.current);
    
    // Start a 3-second reconnect countdown
    let count = 3;
    setReconnectCountdown(count);
    
    if (reconnectIntervalRef.current) clearInterval(reconnectIntervalRef.current);
    reconnectIntervalRef.current = setInterval(() => {
      count -= 1;
      setReconnectCountdown(count);
      if (count <= 0) {
        if (reconnectIntervalRef.current) clearInterval(reconnectIntervalRef.current);
        connect();
      }
    }, 1000);
  };

  useEffect(() => {
    connect();
    
    // Telemetry freshness monitor (runs at 1Hz)
    const freshnessInterval = setInterval(() => {
      const now = Date.now();
      const diff = now - lastTelemetryTimeRef.current;
      if (diff > 5000) { // stale after 5 seconds of silence
        setTelemetry(prev => {
          if (prev.isStale) return prev;
          return { ...prev, isStale: true };
        });
      }
    }, 1000);

    return () => {
      if (wsRef.current) wsRef.current.close();
      if (reconnectIntervalRef.current) clearInterval(reconnectIntervalRef.current);
      if (heartbeatIntervalRef.current) clearInterval(heartbeatIntervalRef.current);
      clearInterval(freshnessInterval);
    };
  }, []);

  const sendControl = (payload: any) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN && connected) {
      try {
        wsRef.current.send(JSON.stringify(payload));
      } catch (err) {
        console.error("[useWebSocket] Failed to send control payload:", err);
      }
    } else {
      console.warn("WebSocket not synced. Control command suppressed.");
    }
  };

  return { connected, latency, telemetry, alerts, reconnectCountdown, sendControl };
};
