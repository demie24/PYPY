import React, { useState } from "react";
import { StyleSheet, Text, View, TouchableOpacity, Alert } from "react-native";
import { AlertOctagon, ShieldAlert, Cpu } from "lucide-react-native";

interface EmergencyScreenProps {
  telemetry: {
    threat_score: number;
    attack_active: boolean;
    voltages: Record<string, number>;
  };
  onSendControl: (payload: any) => void;
}

export const EmergencyScreen: React.FC<EmergencyScreenProps> = ({
  telemetry,
  onSendControl
}) => {
  const safeTelemetry = telemetry || {
    threat_score: 0.0,
    attack_active: false,
    voltages: {}
  };

  const [tapCounts, setTapCounts] = useState<Record<string, number>>({
    isolate: 0,
    island: 0,
    flisr: 0
  });

  console.log(`[EmergencyScreen] Rendering. Threat Score: ${safeTelemetry.threat_score ?? 0}%`);

  const handleDoubleTapAction = (actionKey: string, commandText: string, payload: any) => {
    const currentTaps = tapCounts[actionKey] ?? 0;
    
    if (currentTaps < 1) {
      // Register first tap and set reset timer
      setTapCounts(prev => ({ ...prev, [actionKey]: 1 }));
      setTimeout(() => {
        setTapCounts(prev => ({ ...prev, [actionKey]: 0 }));
      }, 2000); // 2 seconds threshold
      return;
    }

    // Reset tap count
    setTapCounts(prev => ({ ...prev, [actionKey]: 0 }));

    // Client-side safety gate checks (Phase 10 Safety Validation)
    const threatScore = safeTelemetry.threat_score ?? 0.0;
    if (threatScore > 90) {
      Alert.alert(
        "SAFETY BLOCK: HIGH THREAT STATUS",
        "Threat index exceeds 90%. Autonomous security loops have frozen remote breaker actions. Access manually from local sub-station panel.",
        [{ text: "OK" }]
      );
      return;
    }

    // Dispatches MQTT command payload to gateway
    onSendControl(payload);
    
    Alert.alert(
      "EMERGENCY SCADA DISPATCHED",
      `Control command [${commandText}] disptached to gateway. Monitoring grid transients...`,
      [{ text: "OK" }]
    );
  };

  return (
    <View style={styles.container}>
      <View style={styles.emergencyHeader}>
        <AlertOctagon size={24} color="#EF4444" />
        <View style={styles.emergencyHeaderText}>
          <Text style={styles.emergencyHeaderTitle}>EMERGENCY OVERRIDE CONSOLE</Text>
          <Text style={styles.emergencyHeaderSub}>Double-tap command button to confirm dispatch</Text>
        </View>
      </View>

      {/* Grid Diagnostics summary */}
      <View style={styles.diagBox}>
        <View style={styles.diagRow}>
          <ShieldAlert size={14} color="#EF4444" />
          <Text style={styles.diagText}>ACTIVE THREAT INDEX: {(safeTelemetry.threat_score ?? 0.0).toFixed(1)}%</Text>
        </View>
        <View style={styles.diagRow}>
          <Cpu size={14} color="#06B6D4" />
          <Text style={styles.diagText}>GATEWAY STATUS: ONLINE (VALIDATING GATES)</Text>
        </View>
      </View>

      {/* Dispatch Action Panel */}
      <View style={styles.actionsContainer}>
        {/* Action 1: Force Line Isolation */}
        <TouchableOpacity
          activeOpacity={0.8}
          style={[
            styles.actionButton,
            styles.actionButtonRed,
            tapCounts["isolate"] === 1 && styles.actionButtonActive
          ]}
          onPress={() => handleDoubleTapAction(
            "isolate",
            "Force Line 4-5 Isolation",
            { topic: "grid/control", payload: { action: "open_breaker", line: "L4_5" } }
          )}
        >
          <Text style={styles.actionTitle}>FORCE LINE 4-5 ISOLATION</Text>
          <Text style={styles.actionDesc}>
            {tapCounts["isolate"] === 1 ? "TAP AGAIN TO CONFIRM DISPATCH" : "Isolates substation 5 from faulty feeder line"}
          </Text>
        </TouchableOpacity>

        {/* Action 2: Sub-station Islanding */}
        <TouchableOpacity
          activeOpacity={0.8}
          style={[
            styles.actionButton,
            styles.actionButtonOrange,
            tapCounts["island"] === 1 && styles.actionButtonActive
          ]}
          onPress={() => handleDoubleTapAction(
            "island",
            "Bus 8 Load Shedding / Islanding",
            { topic: "grid/control", payload: { action: "isolate_bus", bus: "Bus_8" } }
          )}
        >
          <Text style={styles.actionTitle}>ACTIVATE BUS 8 ISLANDING</Text>
          <Text style={styles.actionDesc}>
            {tapCounts["island"] === 1 ? "TAP AGAIN TO CONFIRM DISPATCH" : "Prevents voltage collapse by shedding Bus 8 loads"}
          </Text>
        </TouchableOpacity>

        {/* Action 3: FLISR Engage Override */}
        <TouchableOpacity
          activeOpacity={0.8}
          style={[
            styles.actionButton,
            styles.actionButtonCyan,
            tapCounts["flisr"] === 1 && styles.actionButtonActive
          ]}
          onPress={() => handleDoubleTapAction(
            "flisr",
            "Force Close Tie-Breaker L7_8",
            { topic: "grid/control", payload: { action: "close_breaker", line: "L7_8" } }
          )}
        >
          <Text style={styles.actionTitle}>ENGAGE FLISR RESTORATION</Text>
          <Text style={styles.actionDesc}>
            {tapCounts["flisr"] === 1 ? "TAP AGAIN TO CONFIRM DISPATCH" : "Forces tie-switch L7_8 to close to restore power"}
          </Text>
        </TouchableOpacity>
      </View>

      <Text style={styles.warningFooter}>
        WARNING: Remote controls are statefully logged. Cyber-physical safety validation curves are active.
      </Text>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#0B0F19",
    padding: 16
  },
  emergencyHeader: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    marginBottom: 20
  },
  emergencyHeaderText: {
    flexDirection: "column"
  },
  emergencyHeaderTitle: {
    fontSize: 12,
    fontWeight: "bold",
    color: "#EF4444",
    letterSpacing: 0.5
  },
  emergencyHeaderSub: {
    fontSize: 8,
    color: "#9CA3AF",
    marginTop: 2
  },
  diagBox: {
    backgroundColor: "#161E2E",
    borderWidth: 1,
    borderColor: "#EF444430",
    borderRadius: 8,
    padding: 12,
    marginBottom: 20,
    gap: 6
  },
  diagRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8
  },
  diagText: {
    fontSize: 9,
    fontWeight: "bold",
    color: "#E5E7EB",
    fontFamily: "monospace"
  },
  actionsContainer: {
    gap: 12,
    flex: 1
  },
  actionButton: {
    borderRadius: 10,
    padding: 14,
    borderWidth: 1.5,
    justifyContent: "center"
  },
  actionButtonActive: {
    backgroundColor: "#EF444420",
    borderColor: "#EF4444",
    borderWidth: 2
  },
  actionButtonRed: {
    backgroundColor: "#450A0A10",
    borderColor: "#EF444430"
  },
  actionButtonOrange: {
    backgroundColor: "#451A0310",
    borderColor: "#F59E0B30"
  },
  actionButtonCyan: {
    backgroundColor: "#06B6D410",
    borderColor: "#06B6D430"
  },
  actionTitle: {
    fontSize: 11,
    fontWeight: "bold",
    color: "#E5E7EB",
    letterSpacing: 0.5,
    marginBottom: 4
  },
  actionDesc: {
    fontSize: 8,
    color: "#9CA3AF",
    lineHeight: 12
  },
  warningFooter: {
    fontSize: 7,
    color: "#9CA3AF",
    textAlign: "center",
    fontStyle: "italic",
    lineHeight: 10
  }
});
