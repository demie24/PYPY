import React from "react";
import { StyleSheet, Text, View, TouchableOpacity } from "react-native";
import { AlertOctagon } from "lucide-react-native";

interface BusState {
  voltage: number;
  status: "NOMINAL" | "WARNING" | "TRIP";
  isAttacked?: boolean;
}

interface MiniTopologyProps {
  telemetry: {
    voltages: Record<string, number>;
    breakers: Record<string, number>;
    threat_score: number;
    attack_active: boolean;
  };
  onSendControl: (payload: any) => void;
}

export const MiniTopology: React.FC<MiniTopologyProps> = ({
  telemetry,
  onSendControl
}) => {
  const safeTelemetry = telemetry || {
    voltages: {},
    breakers: {},
    threat_score: 0,
    attack_active: false
  };
  const safeVoltages = safeTelemetry.voltages || {};
  const attackActive = safeTelemetry.attack_active ?? false;

  // Map voltages to bus status
  const getBusData = (busId: string): BusState => {
    const voltage = safeVoltages[busId] ?? 1.0;
    const isAttacked = attackActive && (busId === "Bus_5" || busId === "Bus_8"); // Mock affected nodes
    let status: "NOMINAL" | "WARNING" | "TRIP" = "NOMINAL";

    if (voltage < 0.85 || voltage > 1.15) {
      status = "TRIP";
    } else if (voltage < 0.95 || voltage > 1.05) {
      status = "WARNING";
    }

    return { voltage, status, isAttacked };
  };

  const handleBusTap = (busId: string) => {
    // Send a query requesting a topology explanation for the tapped bus
    onSendControl({
      topic: "assistant/chat_input",
      payload: { text: `explain topology for ${busId}` }
    });
  };

  const renderBusNode = (busId: string, label: string) => {
    const data = getBusData(busId);
    let statusColor = "#10B981"; // Nominal green
    if (data.status === "TRIP") statusColor = "#EF4444"; // Trip red
    else if (data.status === "WARNING") statusColor = "#F59E0B"; // Warning amber

    return (
      <TouchableOpacity
        key={busId}
        style={[
          styles.node,
          { borderColor: statusColor },
          data.isAttacked && styles.nodeAttacked
        ]}
        onPress={() => handleBusTap(busId)}
      >
        <Text style={styles.nodeLabel}>{label}</Text>
        <Text style={[styles.nodeValue, { color: statusColor }]}>
          {data.voltage.toFixed(3)}
        </Text>
        {data.isAttacked && (
          <View style={styles.attackIndicator}>
            <AlertOctagon size={8} color="#FFFFFF" />
          </View>
        )}
      </TouchableOpacity>
    );
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>INTELLIGENT TOPOLOGY DIAGRAM</Text>

      {/* Row 1: Slack/Generator Buses */}
      <View style={styles.row}>
        {renderBusNode("Bus_1", "BUS 1 (GEN)")}
        {renderBusNode("Bus_2", "BUS 2 (GEN)")}
        {renderBusNode("Bus_3", "BUS 3 (GEN)")}
      </View>

      {/* Row 2: Mid-Level Load Buses */}
      <View style={styles.row}>
        {renderBusNode("Bus_4", "BUS 4")}
        {renderBusNode("Bus_5", "BUS 5")}
        {renderBusNode("Bus_6", "BUS 6")}
      </View>

      {/* Row 3: Lower Load Buses */}
      <View style={styles.row}>
        {renderBusNode("Bus_7", "BUS 7")}
        {renderBusNode("Bus_8", "BUS 8")}
        {renderBusNode("Bus_9", "BUS 9")}
      </View>
      
      <Text style={styles.footerNote}>Tap Bus Node to request AI topology reasoning</Text>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    backgroundColor: "#161E2E",
    borderWidth: 1,
    borderColor: "#24314A",
    borderRadius: 12,
    padding: 16,
    marginVertical: 10
  },
  title: {
    fontSize: 9,
    fontWeight: "bold",
    color: "#9CA3AF",
    letterSpacing: 1,
    marginBottom: 12,
    textAlign: "center"
  },
  row: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginBottom: 12,
    gap: 8
  },
  node: {
    flex: 1,
    backgroundColor: "#0B0F19",
    borderWidth: 1.5,
    borderRadius: 8,
    padding: 8,
    alignItems: "center",
    justifyContent: "center",
    position: "relative",
    height: 52
  },
  nodeAttacked: {
    borderStyle: "dashed",
    borderColor: "#EF4444",
    backgroundColor: "#450A0A"
  },
  nodeLabel: {
    fontSize: 7,
    fontWeight: "bold",
    color: "#9CA3AF",
    marginBottom: 2
  },
  nodeValue: {
    fontSize: 10,
    fontWeight: "bold",
    fontFamily: "monospace"
  },
  attackIndicator: {
    position: "absolute",
    top: 2,
    right: 2,
    backgroundColor: "#EF4444",
    borderRadius: 99,
    width: 12,
    height: 12,
    justifyContent: "center",
    alignItems: "center"
  },
  footerNote: {
    fontSize: 7,
    color: "#9CA3AF",
    textAlign: "center",
    marginTop: 4,
    fontStyle: "italic"
  }
});
