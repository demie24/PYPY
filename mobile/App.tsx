import React, { useState, useEffect } from "react";
import { StatusBar } from "expo-status-bar";
import { StyleSheet, Text, View, SafeAreaView, TouchableOpacity } from "react-native";
import { Shield, LayoutDashboard, MessageSquare, Radio } from "lucide-react-native";
import { DashboardScreen } from "./src/screens/DashboardScreen";
import { CopilotScreen } from "./src/screens/CopilotScreen";
import { EmergencyScreen } from "./src/screens/EmergencyScreen";
import { useWebSocket } from "./src/hooks/useWebSocket";

export default function App() {
  const [currentScreen, setCurrentScreen] = useState<"dashboard" | "copilot" | "emergency">("dashboard");
  const { connected, latency, telemetry, alerts, reconnectCountdown, sendControl } = useWebSocket();

  // Highlight indicator if there are unacknowledged warnings
  const unacknowledgedCount = alerts.filter(a => !a.acknowledged).length;

  console.log(`[App.tsx] Rendering Screen: ${currentScreen}, Connected: ${connected}, Stale: ${telemetry?.isStale}`);

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar style="light" />

      {/* Mobile SCADA Header */}
      <View style={styles.header}>
        <View style={styles.headerLeft}>
          <Shield size={20} color={connected ? "#10B981" : "#EF4444"} />
          <View style={styles.titleContainer}>
            <Text style={styles.titleText}>PYPY FIELD OPS</Text>
            <View style={styles.statusRow}>
              <View style={[styles.statusDot, { backgroundColor: connected ? "#10B981" : "#EF4444" }]} />
              <Text style={styles.statusText}>
                {connected ? `SYNCED (${latency !== null ? `${latency}ms` : "OK"})` : `OFFLINE${reconnectCountdown > 0 ? ` (RETRY ${reconnectCountdown}s)` : ""}`}
              </Text>
            </View>
          </View>
        </View>

        <View style={styles.headerRight}>
          <Text style={styles.threatLabel}>THREAT LEVEL</Text>
          <Text style={[styles.threatValue, { color: telemetry.threat_score > 70 ? "#EF4444" : telemetry.threat_score > 30 ? "#F59E0B" : "#10B981" }]}>
            {telemetry.threat_score.toFixed(1)}%
          </Text>
        </View>
      </View>

      {/* Telemetry Stale Banner */}
      {telemetry.isStale && (
        <View style={styles.staleBanner}>
          <Text style={styles.staleBannerText}>
            ▲ OFFLINE DATA - TELEMETRY IS STALE (NO RECENT HEARTBEAT)
          </Text>
        </View>
      )}

      {/* Screen Render Slot */}
      <View style={styles.content}>
        {currentScreen === "dashboard" && (
          <DashboardScreen telemetry={telemetry} alerts={alerts} onSendControl={sendControl} />
        )}
        {currentScreen === "copilot" && (
          <CopilotScreen telemetry={telemetry} onSendControl={sendControl} />
        )}
        {currentScreen === "emergency" && (
          <EmergencyScreen telemetry={telemetry} onSendControl={sendControl} />
        )}
      </View>

      {/* Bottom Navigation Bar */}
      <View style={styles.navBar}>
        <TouchableOpacity
          style={[styles.navItem, currentScreen === "dashboard" && styles.navItemActive]}
          onPress={() => setCurrentScreen("dashboard")}
        >
          <LayoutDashboard size={20} color={currentScreen === "dashboard" ? "#06B6D4" : "#9CA3AF"} />
          <Text style={[styles.navText, currentScreen === "dashboard" && styles.navTextActive]}>Overview</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.navItem, currentScreen === "copilot" && styles.navItemActive]}
          onPress={() => setCurrentScreen("copilot")}
        >
          <View style={styles.avatarNavContainer}>
            <MessageSquare size={20} color={currentScreen === "copilot" ? "#06B6D4" : "#9CA3AF"} />
            {unacknowledgedCount > 0 && (
              <View style={styles.badge}>
                <Text style={styles.badgeText}>{unacknowledgedCount}</Text>
              </View>
            )}
          </View>
          <Text style={[styles.navText, currentScreen === "copilot" && styles.navTextActive]}>Copilot</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.navItem, currentScreen === "emergency" && styles.navItemActive]}
          onPress={() => setCurrentScreen("emergency")}
        >
          <Radio size={20} color={currentScreen === "emergency" ? "#EF4444" : "#9CA3AF"} />
          <Text style={[styles.navText, currentScreen === "emergency" && styles.navTextActive, currentScreen === "emergency" && { color: "#EF4444" }]}>
            EMERGENCY
          </Text>
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#0B0F19"
  },
  header: {
    height: 56,
    borderBottomWidth: 1,
    borderBottomColor: "#24314A",
    backgroundColor: "#161E2E",
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingHorizontal: 16
  },
  headerLeft: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10
  },
  titleContainer: {
    flexDirection: "column"
  },
  titleText: {
    fontSize: 12,
    fontWeight: "bold",
    color: "#E5E7EB",
    letterSpacing: 1
  },
  statusRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4
  },
  statusDot: {
    width: 6,
    height: 6,
    borderRadius: 3
  },
  statusText: {
    fontSize: 8,
    color: "#9CA3AF",
    fontWeight: "600",
    letterSpacing: 0.5
  },
  headerRight: {
    alignItems: "flex-end"
  },
  threatLabel: {
    fontSize: 7,
    color: "#9CA3AF",
    fontWeight: "bold",
    letterSpacing: 0.5
  },
  threatValue: {
    fontSize: 14,
    fontWeight: "bold"
  },
  staleBanner: {
    backgroundColor: "#78350F",
    paddingVertical: 4,
    alignItems: "center",
    justifyContent: "center",
    borderBottomWidth: 1,
    borderBottomColor: "#F59E0B30"
  },
  staleBannerText: {
    color: "#F59E0B",
    fontSize: 8,
    fontWeight: "bold",
    letterSpacing: 0.5
  },
  content: {
    flex: 1
  },
  navBar: {
    height: 56,
    borderTopWidth: 1,
    borderTopColor: "#24314A",
    backgroundColor: "#161E2E",
    flexDirection: "row",
    justifyContent: "space-around",
    alignItems: "center"
  },
  navItem: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    gap: 2
  },
  navItemActive: {
    backgroundColor: "rgba(36, 49, 74, 0.1)"
  },
  navText: {
    fontSize: 8,
    color: "#9CA3AF",
    fontWeight: "500"
  },
  navTextActive: {
    color: "#06B6D4",
    fontWeight: "bold"
  },
  avatarNavContainer: {
    position: "relative"
  },
  badge: {
    position: "absolute",
    top: -5,
    right: -10,
    backgroundColor: "#06B6D4",
    width: 14,
    height: 14,
    borderRadius: 7,
    justifyContent: "center",
    alignItems: "center"
  },
  badgeText: {
    color: "#FFFFFF",
    fontSize: 8,
    fontWeight: "bold"
  }
});
