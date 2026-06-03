import React, { useState, useEffect, useRef } from "react";
import { StyleSheet, Text, View, ScrollView, TextInput, TouchableOpacity, KeyboardAvoidingView, Platform } from "react-native";
import { MascotAvatar } from "../components/MascotAvatar";
import { Send, Mic, Volume2 } from "lucide-react-native";
import * as Speech from "expo-speech";

interface Interaction {
  role: string;
  text: string;
}

interface CopilotScreenProps {
  telemetry: {
    threat_score: number;
    attack_active: boolean;
  };
  onSendControl: (payload: any) => void;
}

export const CopilotScreen: React.FC<CopilotScreenProps> = ({
  telemetry,
  onSendControl
}) => {
  const safeTelemetry = telemetry || {
    threat_score: 0.0,
    attack_active: false
  };

  const [messages, setMessages] = useState<Interaction[]>([
    { role: "assistant", text: "Selamat sejahtera! Saya Grid AI Copilot. Ada sebarang status pencawang atau parameter grid yang anda ingin semak sekarang?" }
  ]);
  const [inputText, setInputText] = useState("");
  const [isListeningVoice, setIsListeningVoice] = useState(false);
  const [voiceEnabled, setVoiceEnabled] = useState(true);
  const chatEndRef = useRef<ScrollView>(null);

  console.log(`[CopilotScreen] Rendering. Message count: ${messages.length}, Voice Enabled: ${voiceEnabled}, Listening: ${isListeningVoice}`);

  // Trigger speech read out of new assistant messages if voice is enabled
  useEffect(() => {
    const latestMsg = messages[messages.length - 1];
    if (latestMsg && latestMsg.role === "assistant" && voiceEnabled) {
      try {
        Speech.speak(latestMsg.text, { language: "ms" });
      } catch (err) {
        console.warn("[CopilotScreen] Speech.speak failed or not supported by platform:", err);
      }
    }
  }, [messages.length, voiceEnabled]);

  const handleSendChat = () => {
    if (!inputText.trim()) return;
    
    // Add user message locally
    const userMsg = inputText;
    setMessages(prev => [...prev, { role: "user", text: userMsg }]);
    setInputText("");

    // Simulate RAG Assistant response locally for stand-alone runtime verification
    setTimeout(() => {
      let aiText = "Saya faham. Grid status berada dalam keadaan nominal.";
      if (userMsg.toLowerCase().includes("status")) {
        aiText = `Semakan telemetry: Threat score berada pada tahap ${(safeTelemetry.threat_score ?? 0.0).toFixed(1)}%. ${safeTelemetry.attack_active ? "GANGGUAN AKTIF DIKESAN." : "Tiada serangan dikesan."}`;
      } else if (userMsg.toLowerCase().includes("topology")) {
        aiText = "Topologi IEEE 9-Bus dimodelkan stateful. Talian L7_8 berfungsi sebagai tie-breaker isolasi.";
      } else if (userMsg.toLowerCase().includes("mitigation") || userMsg.toLowerCase().includes("sop")) {
        aiText = "SOP low-voltage recovery: Mengesyorkan pengasingan pencawang terjejas sebelum penutupan tie-breaker.";
      }
      
      setMessages(prev => [...prev, { role: "assistant", text: aiText }]);
    }, 800);

    onSendControl({
      topic: "assistant/chat_input",
      payload: { text: userMsg }
    });
  };

  const handleQuickAction = (phrase: string) => {
    setInputText(phrase);
  };

  const handleSimulateVoice = () => {
    if (isListeningVoice) return;
    setIsListeningVoice(true);
    setTimeout(() => {
      setIsListeningVoice(false);
      setInputText("semak status grid");
    }, 1500);
  };

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === "ios" ? "padding" : "height"}
      style={styles.container}
    >
      {/* Top Profile Card */}
      <View style={styles.profileCard}>
        <MascotAvatar size={52} pulseState={isListeningVoice ? "LISTENING" : "IDLE"} isAlert={safeTelemetry.attack_active} />
        <View style={styles.profileInfo}>
          <Text style={styles.mascotName}>S-GRID COPILOT</Text>
          <Text style={styles.mascotRole}>Mobile Field Assistant Mascot</Text>
        </View>
        <TouchableOpacity
          style={[styles.voiceToggle, voiceEnabled && styles.voiceToggleActive]}
          onPress={() => setVoiceEnabled(!voiceEnabled)}
        >
          <Volume2 size={16} color={voiceEnabled ? "#06B6D4" : "#9CA3AF"} />
        </TouchableOpacity>
      </View>

      {/* Message Area */}
      <ScrollView
        ref={chatEndRef}
        style={styles.chatArea}
        contentContainerStyle={styles.chatContent}
        onContentSizeChange={() => chatEndRef.current?.scrollToEnd({ animated: true })}
      >
        {messages.map((msg, idx) => {
          const isUser = msg.role === "user";
          return (
            <View key={idx} style={[styles.messageRow, isUser ? styles.rowUser : styles.rowAI]}>
              <View style={[styles.bubble, isUser ? styles.bubbleUser : styles.bubbleAI]}>
                <Text style={styles.bubbleRole}>{isUser ? "OPERATOR" : "AI MASCOT"}</Text>
                <Text style={styles.bubbleText}>{msg.text}</Text>
              </View>
            </View>
          );
        })}
      </ScrollView>

      {/* Suggested Quick Commands */}
      <View style={styles.quickActionsRow}>
        <TouchableOpacity style={styles.quickActionBtn} onPress={() => handleQuickAction("Semak status grid")}>
          <Text style={styles.quickActionTxt}>Check Status</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.quickActionBtn} onPress={() => handleQuickAction("Explain Bus 5 topology")}>
          <Text style={styles.quickActionTxt}>Explain Topology</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.quickActionBtn} onPress={() => handleQuickAction("SOP mitigation")}>
          <Text style={styles.quickActionTxt}>Get SOP</Text>
        </TouchableOpacity>
      </View>

      {/* Input Tray */}
      <View style={styles.inputTray}>
        <TouchableOpacity
          style={[styles.micBtn, isListeningVoice && styles.micBtnActive]}
          onPress={handleSimulateVoice}
        >
          <Mic size={18} color={isListeningVoice ? "#EF4444" : "#06B6D4"} />
        </TouchableOpacity>

        <TextInput
          value={inputText}
          onChangeText={setInputText}
          onSubmitEditing={handleSendChat}
          placeholder={isListeningVoice ? "Sila bercakap..." : "Type request..."}
          placeholderTextColor="#9CA3AF"
          style={styles.textInput}
        />

        <TouchableOpacity
          style={styles.sendBtn}
          onPress={handleSendChat}
          disabled={!inputText.trim()}
        >
          <Send size={18} color={inputText.trim() ? "#06B6D4" : "#24314A"} />
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#0B0F19"
  },
  profileCard: {
    height: 72,
    borderBottomWidth: 1,
    borderBottomColor: "#24314A",
    backgroundColor: "#161E2E",
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 16,
    gap: 12
  },
  profileInfo: {
    flex: 1,
    flexDirection: "column"
  },
  mascotName: {
    fontSize: 12,
    fontWeight: "bold",
    color: "#E5E7EB",
    letterSpacing: 0.5
  },
  mascotRole: {
    fontSize: 8,
    color: "#06B6D4",
    fontWeight: "600",
    marginTop: 2
  },
  voiceToggle: {
    padding: 10,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: "#24314A",
    backgroundColor: "#0B0F19"
  },
  voiceToggleActive: {
    borderColor: "#06B6D430",
    backgroundColor: "#06B6D410"
  },
  chatArea: {
    flex: 1
  },
  chatContent: {
    padding: 16,
    gap: 12
  },
  messageRow: {
    flexDirection: "row",
    width: "100%"
  },
  rowUser: {
    justifyContent: "flex-end"
  },
  rowAI: {
    justifyContent: "flex-start"
  },
  bubble: {
    maxWidth: "80%",
    borderRadius: 12,
    padding: 10,
    borderWidth: 1
  },
  bubbleAI: {
    backgroundColor: "#161E2E",
    borderColor: "#24314A",
    color: "#E5E7EB"
  },
  bubbleUser: {
    backgroundColor: "#06B6D410",
    borderColor: "#06B6D430",
    color: "#E5E7EB"
  },
  bubbleRole: {
    fontSize: 6,
    fontWeight: "bold",
    color: "#9CA3AF",
    letterSpacing: 0.5,
    marginBottom: 4
  },
  bubbleText: {
    fontSize: 10,
    lineHeight: 14,
    color: "#E5E7EB"
  },
  quickActionsRow: {
    flexDirection: "row",
    justifyContent: "center",
    gap: 8,
    paddingHorizontal: 16,
    paddingBottom: 10
  },
  quickActionBtn: {
    backgroundColor: "#161E2E",
    borderWidth: 1,
    borderColor: "#24314A",
    borderRadius: 6,
    paddingVertical: 6,
    paddingHorizontal: 10
  },
  quickActionTxt: {
    fontSize: 8,
    color: "#06B6D4",
    fontWeight: "bold"
  },
  inputTray: {
    height: 56,
    borderTopWidth: 1,
    borderTopColor: "#24314A",
    backgroundColor: "#161E2E",
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 16,
    gap: 12
  },
  micBtn: {
    padding: 8,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: "#24314A",
    backgroundColor: "#0B0F19"
  },
  micBtnActive: {
    borderColor: "#EF444430",
    backgroundColor: "#EF444410"
  },
  textInput: {
    flex: 1,
    backgroundColor: "#0B0F19",
    borderWidth: 1,
    borderColor: "#24314A",
    borderRadius: 8,
    height: 36,
    paddingHorizontal: 12,
    fontSize: 10,
    color: "#E5E7EB"
  },
  sendBtn: {
    padding: 6
  }
});
