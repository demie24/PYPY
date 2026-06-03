import React, { useState } from "react";
import { StyleSheet, View, Image, Text } from "react-native";
import { Bot } from "lucide-react-native";

interface MascotAvatarProps {
  size?: number;
  pulseState?: "IDLE" | "THINKING" | "LISTENING" | "RESPONDING" | "ERROR";
  isAlert?: boolean;
}

export const MascotAvatar: React.FC<MascotAvatarProps> = ({
  size = 64,
  pulseState = "IDLE",
  isAlert = false
}) => {
  const [imageFailed, setImageFailed] = useState(false);

  const getBorderColor = () => {
    if (isAlert) return "#EF4444";
    switch (pulseState) {
      case "ERROR": return "#EF4444";
      case "THINKING": return "#A855F7";
      case "LISTENING": return "#22D3EE";
      case "RESPONDING": return "#10B981";
      default: return "#06B6D4";
    }
  };

  const borderColor = getBorderColor();

  return (
    <View style={[styles.container, { width: size, height: size, borderColor }, isAlert && styles.alertGlow]}>
      {imageFailed ? (
        <View style={styles.fallbackContainer}>
          <Bot size={size * 0.45} color={borderColor} />
          <Text style={[styles.fallbackText, { color: borderColor }]}>PYPY AI</Text>
        </View>
      ) : (
        <Image
          source={{ uri: "http://localhost:3001/avatar.png" }}
          onError={() => {
            console.log("[MascotAvatar] Failed to load remote avatar image, displaying fallback.");
            setImageFailed(true);
          }}
          style={styles.avatarImage}
        />
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    borderRadius: 9999,
    borderWidth: 2,
    padding: 2,
    backgroundColor: "#161E2E",
    justifyContent: "center",
    alignItems: "center",
    overflow: "hidden"
  },
  avatarImage: {
    width: "100%",
    height: "100%",
    borderRadius: 9999
  },
  fallbackContainer: {
    width: "100%",
    height: "100%",
    backgroundColor: "#0B0F19",
    justifyContent: "center",
    alignItems: "center"
  },
  fallbackText: {
    fontSize: 6,
    fontWeight: "bold",
    letterSpacing: 0.5,
    marginTop: 2
  },
  alertGlow: {
    shadowColor: "#EF4444",
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.8,
    shadowRadius: 10
  }
});
