import React from "react";
import { StyleSheet, Text, View, ScrollView, TouchableOpacity, FlatList } from "react-native";
import { TelemetryCard } from "../components/TelemetryCard";
import { MiniTopology } from "../components/MiniTopology";
import { ShieldAlert, CheckCircle, Flame } from "lucide-react-native";

interface Alert {
  id: string;
  source: string;
  event: string;
  severity: "CRITICAL" | "WARNING" | "INFO";
  timestamp: number;
  acknowledged: boolean;
}

interface DashboardScreenProps {
  telemetry: {
    voltages: Record<string, number>;
    breakers: Record<string, number>;
    threat_score: number;
    attack_active: boolean;
  };
  alerts: Alert[];
  onSendControl: (payload: any) => void;
}

export const DashboardScreen: React.FC<DashboardScreenProps> = ({
  telemetry,
  alerts,
  onSendControl
}) => {
  const safeTelemetry = telemetry || {
    voltages: {},
    breakers: {},
    threat_score: 0,
    attack_active: false
  };
  const safeVoltages = safeTelemetry.voltages || {};
  const safeAlerts = alerts || [];
  const activeAlerts = safeAlerts.filter(a => a && !a.acknowledged);
  const threatScore = safeTelemetry.threat_score ?? 0;
  const attackActive = safeTelemetry.attack_active ?? false;

  console.log(`[DashboardScreen] Rendering. Threat Score: ${threatScore}%, Active Alerts: ${activeAlerts.length}, Voltages Count: ${Object.keys(safeVoltages).length}`);

  const getGridHealthText = () => {
    if (attackActive) return { text: "CRITICAL ATTACK ACTIVE", color: "#EF4444" };
    if (threatScore > 50) return { text: "DEGRADED SECURITY", color: "#F59E0B" };
    return { text: "GRID NOMINAL", color: "#10B981" };
  };

  const health = getGridHealthText();

  const handleAcknowledgeAlert = (alertId: string) => {
    onSendControl({
      topic: "assistant/chat_input",
      payload: { text: `acknowledge alert ${alertId}` }
    });
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.contentContainer}>
      {/* Grid Health Status Indicator */}
      <View style={[styles.healthBanner, { backgroundColor: health.color + "12", borderColor: health.color + "30" }]}>
        {attackActive ? (
          <Flame size={24} color={health.color} />
        ) : (
          <CheckCircle size={24} color={health.color} />
        )}
        <View style={styles.healthBannerText}>
          <Text style={[styles.healthTitle, { color: health.color }]}>{health.text}</Text>
          <Text style={styles.healthSubText}>Observability rating: {(100 - threatScore).toFixed(0)}%</Text>
        </View>
      </View>

      {/* Telemetry Row */}
      <View style={styles.telemetryGrid}>
        <TelemetryCard
          title="Grid Threat Index"
          value={`${threatScore.toFixed(0)}%`}
          unit="risk"
          status={threatScore > 70 ? "TRIP" : threatScore > 30 ? "WARNING" : "NOMINAL"}
        />
        <TelemetryCard
          title="Bus 5 Voltage"
          value={`${(safeVoltages["Bus_5"] ?? 1.0).toFixed(3)}`}
          unit="p.u."
          status={(safeVoltages["Bus_5"] ?? 1.0) < 0.90 || (safeVoltages["Bus_5"] ?? 1.0) > 1.10 ? "TRIP" : (safeVoltages["Bus_5"] ?? 1.0) < 0.95 || (safeVoltages["Bus_5"] ?? 1.0) > 1.05 ? "WARNING" : "NOMINAL"}
        />
      </View>

      {/* Mini Interactive Topology Grid */}
      <MiniTopology telemetry={safeTelemetry} onSendControl={onSendControl} />

      {/* Priority Mobile Alert Feed */}
      <View style={styles.alertsContainer}>
        <Text style={styles.sectionTitle}>CRITICAL SCADA ALERT FEED ({activeAlerts.length})</Text>
        {activeAlerts.length === 0 ? (
          <View style={styles.noAlerts}>
            <Text style={styles.noAlertsText}>No active grid alerts. Operational channels clear.</Text>
          </View>
        ) : (
          activeAlerts.slice(0, 4).map((alert) => (
            <View key={alert.id} style={[styles.alertCard, alert.severity === "CRITICAL" && styles.alertCardCritical]}>
              <View style={styles.alertHeader}>
                <View style={styles.alertLabelContainer}>
                  <ShieldAlert size={14} color={alert.severity === "CRITICAL" ? "#EF4444" : "#F59E0B"} />
                  <Text style={[styles.alertSource, { color: alert.severity === "CRITICAL" ? "#EF4444" : "#F59E0B" }]}>
                    {alert.source}
                  </Text>
                </View>
                <Text style={styles.alertTime}>
                  {new Date(alert.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                </Text>
              </View>
              <Text style={styles.alertText}>{alert.event}</Text>
              <TouchableOpacity
                style={styles.ackButton}
                onPress={() => handleAcknowledgeAlert(alert.id)}
              >
                <Text style={styles.ackButtonText}>ACKNOWLEDGE</Text>
              </TouchableOpacity>
            </View>
          ))
        )}
      </View>
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#0B0F19"
  },
  contentContainer: {
    padding: 16,
    paddingBottom: 24
  },
  healthBanner: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    borderWidth: 1,
    borderRadius: 12,
    padding: 16,
    marginBottom: 16
  },
  healthBannerText: {
    flexDirection: "column"
  },
  healthTitle: {
    fontSize: 14,
    fontWeight: "bold",
    letterSpacing: 0.5
  },
  healthSubText: {
    fontSize: 9,
    color: "#9CA3AF",
    marginTop: 2
  },
  telemetryGrid: {
    flexDirection: "row",
    gap: 12,
    marginBottom: 8
  },
  alertsContainer: {
    marginTop: 8
  },
  sectionTitle: {
    fontSize: 10,
    fontWeight: "bold",
    color: "#9CA3AF",
    letterSpacing: 1,
    marginBottom: 10
  },
  noAlerts: {
    backgroundColor: "#161E2E",
    borderWidth: 1,
    borderColor: "#24314A",
    borderRadius: 12,
    padding: 20,
    alignItems: "center",
    justifyContent: "center"
  },
  noAlertsText: {
    fontSize: 9,
    color: "#9CA3AF",
    textAlign: "center"
  },
  alertCard: {
    backgroundColor: "#161E2E",
    borderWidth: 1,
    borderColor: "#24314A",
    borderRadius: 12,
    padding: 12,
    marginBottom: 10
  },
  alertCardCritical: {
    borderColor: "#EF444430",
    backgroundColor: "#450A0A10"
  },
  alertHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 6
  },
  alertLabelContainer: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6
  },
  alertSource: {
    fontSize: 9,
    fontWeight: "bold",
    textTransform: "uppercase"
  },
  alertTime: {
    fontSize: 8,
    color: "#9CA3AF"
  },
  alertText: {
    fontSize: 10,
    color: "#E5E7EB",
    marginBottom: 10,
    lineHeight: 14
  },
  ackButton: {
    backgroundColor: "#24314A",
    borderRadius: 6,
    paddingVertical: 6,
    alignItems: "center"
  },
  ackButtonText: {
    fontSize: 8,
    fontWeight: "bold",
    color: "#E5E7EB",
    letterSpacing: 0.5
  }
});
