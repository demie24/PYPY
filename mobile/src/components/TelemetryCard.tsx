import React from "react";
import { StyleSheet, Text, View } from "react-native";

interface TelemetryCardProps {
  title: string;
  value: string;
  unit: string;
  status: "NOMINAL" | "WARNING" | "TRIP";
}

export const TelemetryCard: React.FC<TelemetryCardProps> = ({
  title,
  value,
  unit,
  status
}) => {
  const getStatusConfig = () => {
    switch (status) {
      case "TRIP":
        return { color: "#EF4444", bg: "#450A0A", label: "TRIP" };
      case "WARNING":
        return { color: "#F59E0B", bg: "#451A03", label: "WARN" };
      default:
        return { color: "#10B981", bg: "#064E3B", label: "OK" };
    }
  };

  const config = getStatusConfig();

  return (
    <View style={[styles.card, { borderColor: config.color + "30" }]}>
      <View style={styles.cardHeader}>
        <Text style={styles.cardTitle}>{title}</Text>
        <View style={[styles.badge, { backgroundColor: config.bg }]}>
          <Text style={[styles.badgeText, { color: config.color }]}>{config.label}</Text>
        </View>
      </View>
      <View style={styles.valueRow}>
        <Text style={styles.valueText}>{value}</Text>
        <Text style={styles.unitText}>{unit}</Text>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  card: {
    backgroundColor: "#161E2E",
    borderWidth: 1,
    borderRadius: 12,
    padding: 12,
    flex: 1,
    minWidth: 140
  },
  cardHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 8
  },
  cardTitle: {
    fontSize: 9,
    fontWeight: "bold",
    color: "#9CA3AF",
    textTransform: "uppercase",
    letterSpacing: 0.5
  },
  badge: {
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4
  },
  badgeText: {
    fontSize: 7,
    fontWeight: "bold"
  },
  valueRow: {
    flexDirection: "row",
    alignItems: "baseline",
    gap: 2
  },
  valueText: {
    fontSize: 18,
    fontWeight: "bold",
    color: "#FFFFFF",
    fontFamily: "monospace"
  },
  unitText: {
    fontSize: 9,
    color: "#9CA3AF",
    fontWeight: "500"
  }
});
