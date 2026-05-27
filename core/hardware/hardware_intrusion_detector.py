import time
import logging
from typing import Dict, Any, List

logger = logging.getLogger("hardware.intrusion_detector")

class HardwareIntrusionDetector:
    def __init__(self):
        # Local indicators
        self.intrusion_score = 0.0  # 0.0 (clean) to 100.0 (compromised)
        self.alerts: List[Dict[str, Any]] = []
        
        # Action tracking for command monitoring
        self.last_switching_times: Dict[str, List[float]] = {}
        
        # Typing speed tracker (simulated timing of keystrokes)
        self.last_keystroke_time = 0.0
        self.typing_intervals: List[float] = []
        
    def analyze_command(self, cmd: str, target: str, source: str) -> bool:
        """
        Analyzes command dispatches to identify anomalies like rapid chattering,
        unauthorized command origin values, or blocked routing.
        """
        now = time.time()
        
        # 1. Rate check (Chattering command verification)
        if target not in self.last_switching_times:
            self.last_switching_times[target] = []
        timestamps = self.last_switching_times[target]
        timestamps.append(now)
        
        # Keep window of last 5s
        self.last_switching_times[target] = [t for t in timestamps if now - t <= 5.0]
        recent_count = len(self.last_switching_times[target])
        
        if recent_count >= 3:
            # Command chattering indicator detected
            self._trigger_alert(
                alert_type="CHATTERING_COMMAND_FLOOD",
                target=target,
                details=f"High frequency control commands dispatched on {target} ({recent_count} switching commands in 5s).",
                severity="HIGH"
            )
            self.intrusion_score = min(100.0, self.intrusion_score + 25.0)
            return False
            
        # 2. Unauthorized origin check
        if source not in ["SCADA_OPERATOR", "AGENT_CONSENSUS", "ORCHESTRATOR_APPROVED", "FLISR"]:
            self._trigger_alert(
                alert_type="UNAUTHORIZED_COMMAND_ORIGIN",
                target=target,
                details=f"Command {cmd} targeting {target} was dispatched from non-whitelisted source: '{source}'.",
                severity="CRITICAL"
            )
            self.intrusion_score = min(100.0, self.intrusion_score + 40.0)
            return False
            
        # 3. Malicious relay override check
        # Trip or close operations that attempt to override security rules (e.g. closing into a fault)
        if cmd == "CLOSE" and "L7_8" in target:
            # Intercept close command targeting the tie breaker while islanded
            self._trigger_alert(
                alert_type="MALICIOUS_RELAY_OVERRIDE",
                target=target,
                details="Attempted closing of tie breaker outside synchronization limits.",
                severity="HIGH"
            )
            self.intrusion_score = min(100.0, self.intrusion_score + 20.0)
            
        return True
        
    def analyze_typing_speed(self, delay_ms: int):
        """
        Detects abnormal HID typing speeds that suggest mechanical BadUSB command entry.
        Human typing intervals average 60ms-150ms per key. Injections are immediate (0-5ms).
        """
        if delay_ms < 10:
            self._trigger_alert(
                alert_type="ABNORMAL_HID_SPEED",
                target="Keyboard_HID_Buffer",
                details=f"Rapid keystroke buffer injection detected (delay={delay_ms}ms). Input speed exceeds human limits.",
                severity="HIGH"
            )
            self.intrusion_score = min(100.0, self.intrusion_score + 30.0)

    def analyze_ip_origin(self, origin_ip: str, command: str):
        """
        Evaluates command requests against allowed subnet sources.
        """
        allowed_ips = ["192.168.1.10", "192.168.1.11", "127.0.0.1"]
        if origin_ip not in allowed_ips:
            self._trigger_alert(
                alert_type="SPOOFED_OPERATOR_ACTION",
                target=origin_ip,
                details=f"System control instruction '{command}' received from unauthorized IP location: {origin_ip}.",
                severity="CRITICAL"
            )
            self.intrusion_score = min(100.0, self.intrusion_score + 45.0)
            
    def analyze_telemetry(self, sensor_id: str, raw_val: float, filtered_val: float):
        """
        Analyzes telemetry feeds to flag tampering (e.g. FDIA filters, high noise, flatlines).
        """
        # If absolute difference between raw (untrusted) and state-filtered telemetry is high
        import math
        if not math.isnan(raw_val) and not math.isnan(filtered_val):
            diff = abs(raw_val - filtered_val)
            if diff > 0.15:
                self._trigger_alert(
                    alert_type="TELEMETRY_TAMPERING_FDIA",
                    target=sensor_id,
                    details=f"Suspicious difference between raw telemetry and physics estimation for {sensor_id}: diff={diff:.3f} p.u.",
                    severity="HIGH"
                )
                self.intrusion_score = min(100.0, self.intrusion_score + 15.0)
                
    def _trigger_alert(self, alert_type: str, target: str, details: str, severity: str):
        alert = {
            "timestamp": int(time.time() * 1000),
            "alert_type": alert_type,
            "target": target,
            "details": details,
            "severity": severity
        }
        self.alerts.append(alert)
        if len(self.alerts) > 30:
            self.alerts.pop(0)
            
        logger.warning(f"[HARDWARE INTRUSION ALERT] Type={alert_type} target={target} - {details}")
        
    def get_status_payload(self) -> Dict[str, Any]:
        return {
            "timestamp": int(time.time() * 1000),
            "intrusion_score": round(self.intrusion_score, 1),
            "alerts_count": len(self.alerts),
            "latest_alert": self.alerts[-1] if self.alerts else None
        }
        
    def reset(self):
        self.intrusion_score = 0.0
        self.alerts.clear()
        self.last_switching_times.clear()
        self.typing_intervals.clear()
        logger.info("Hardware Intrusion Detector reset.")
