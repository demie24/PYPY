import time
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("hardware.digispark_engine")

class DigisparkAttackEngine:
    def __init__(self):
        # Payload Registry (simulated payloads metadata)
        self.payloads = {
            "keystroke_bypass": {
                "name": "Keystroke SCADA Bypass",
                "type": "HID_KEYSTROKE",
                "target_device": "operator_console",
                "description": "Simulates automated keystrokes opening firewalls or resetting lockout rules.",
                "phases": ["INITIAL_ACCESS", "PRIVILEGE_ESCALATION", "IMPACT"]
            },
            "unauthorized_serial": {
                "name": "Serial Port Hijacker",
                "type": "SERIAL_EMULATION",
                "target_device": "esp32_gateway",
                "description": "Enumerates raw serial interfaces to inject malicious hex frames directly.",
                "phases": ["INITIAL_ACCESS", "LATERAL_MOVEMENT", "IMPACT"]
            },
            "firmware_flasher": {
                "name": "OTA Firmware Overwrite",
                "type": "FIRMWARE_ATTACK",
                "target_device": "substation_plc",
                "description": "Attaches as USB DFU device to flash malicious custom firmware.",
                "phases": ["INITIAL_ACCESS", "IMPACT"]
            }
        }
        
        # State: IDLE, DELAYED, ARMED, EXECUTING, COMPLETED, FAILED
        self.attack_state = "IDLE"
        self.active_payload_id: Optional[str] = None
        self.started_at: float = 0.0
        
        # Delayed trigger variables
        self.delay_ticks_remaining = 0
        
        # Staged execution variables
        self.current_step_index = 0
        self.payload_steps: List[str] = []
        self.stealth_wait_ticks = 0  # Number of ticks to wait before next step (stealth simulation)
        self.current_phase = "NOMINAL"  # INITIAL_ACCESS, RECONNAISSANCE, PRIVILEGE_ESCALATION, LATERAL_MOVEMENT, IMPACT
        
        # HID execution logs (detailed keystroke timeline)
        self.hid_timeline: List[Dict[str, Any]] = []
        
        # USB events history logs
        self.usb_events: List[Dict[str, Any]] = []
        
        # Test compatibility helper
        self.execution_duration = 0.0
        
    def trigger_attack(self, payload_id: str, delay_ticks: int = 0, steps: List[str] = None) -> bool:
        """
        Triggers a simulated USB injection attack with optional delayed trigger.
        """
        if payload_id not in self.payloads:
            logger.warning(f"Failed to trigger Digispark payload: {payload_id} not in registry.")
            return False
            
        self.active_payload_id = payload_id
        self.payload_steps = steps if steps else ["GUI r", "DELAY 200", "STRING cmd", "ENTER"]
        self.current_step_index = 0
        self.hid_timeline.clear()
        
        if delay_ticks > 0:
            self.attack_state = "DELAYED"
            self.delay_ticks_remaining = delay_ticks
            self.log_usb_event(
                event_type="USB_INSERTED_STEALTH",
                device="Digispark ATTINY85",
                details=f"USB device mounted. Delayed trigger active ({delay_ticks} ticks delay).",
                severity="WARNING"
            )
            logger.info(f"Digispark attack engine loaded in DELAYED state: {payload_id} (delay={delay_ticks} ticks)")
        else:
            self.attack_state = "ARMED"
            self.started_at = time.time()
            self.log_usb_event(
                event_type="USB_INSERTED",
                device="Digispark ATTINY85",
                details=f"Hardware injection payload {payload_id} mounted as keyboard/serial device.",
                severity="WARNING"
            )
            logger.info(f"Digispark attack engine armed immediately: {payload_id}")
            
        return True
        
    def tick(self) -> Dict[str, Any]:
        """
        Processes HID attack lifecycle state transitions and staged command entry.
        """
        now = time.time()
        
        # Check compatibility duration override
        if self.execution_duration > 0.0 and self.attack_state == "EXECUTING":
            if now - self.started_at >= self.execution_duration:
                self.attack_state = "COMPLETED"
                self.current_phase = "IMPACT"
                self.log_usb_event(
                    event_type="HID_INJECTION_COMPLETE",
                    device="Digispark ATTINY85",
                    details="Keystroke script completed. Hardware device unplugged.",
                    severity="INFO"
                )
                logger.info("Digispark HID script execution completed.")
                return self.get_status_payload()
        
        if self.attack_state == "DELAYED":
            self.delay_ticks_remaining -= 1
            if self.delay_ticks_remaining <= 0:
                self.attack_state = "ARMED"
                self.started_at = now
                self.log_usb_event(
                    event_type="USB_DELAY_EXPIRED",
                    device="Digispark ATTINY85",
                    details=f"Stealth delay expired. Arming attack execution.",
                    severity="WARNING"
                )
                logger.info("Digispark stealth delay expired, arming engine.")
            return self.get_status_payload()
            
        if self.attack_state == "ARMED":
            self.attack_state = "EXECUTING"
            self.current_phase = "INITIAL_ACCESS"
            self.log_usb_event(
                event_type="HID_INJECTION_START",
                device="Digispark ATTINY85",
                details=f"Executing payload {self.active_payload_id} (HID script injection active).",
                severity="HIGH"
            )
            logger.info(f"Digispark starting HID script execution: {self.active_payload_id}")
            
        elif self.attack_state == "EXECUTING":
            if self.stealth_wait_ticks > 0:
                # Waiting (simulating keystroke timing / delay commands)
                self.stealth_wait_ticks -= 1
                self.log_hid_action(f"Stealth delay wait... Ticks left: {self.stealth_wait_ticks}")
            elif self.current_step_index < len(self.payload_steps):
                # Execute next step
                step = self.payload_steps[self.current_step_index]
                self.execute_step(step)
                self.current_step_index += 1
            else:
                # All steps completed
                self.attack_state = "COMPLETED"
                self.current_phase = "IMPACT"
                self.log_usb_event(
                    event_type="HID_INJECTION_COMPLETE",
                    device="Digispark ATTINY85",
                    details=f"Keystroke script completed. Hardware device unplugged.",
                    severity="INFO"
                )
                logger.info("Digispark HID script execution completed.")
                
        return self.get_status_payload()
        
    def execute_step(self, step: str):
        """
        Executes a single step of the DuckyScript payload.
        """
        parts = step.split(" ", 1)
        cmd = parts[0]
        arg = parts[1] if len(parts) > 1 else ""
        
        # 1. Update escalation phase based on script command hints
        if cmd == "DELAY":
            try:
                ms = int(arg)
                # Translate ms to simulated ticks (e.g. 500ms = 1 tick, 1000ms = 2 ticks)
                self.stealth_wait_ticks = max(1, ms // 500)
                self.log_hid_action(f"Stealth DELAY command: wait {self.stealth_wait_ticks} ticks")
            except ValueError:
                self.stealth_wait_ticks = 1
        elif cmd == "STRING":
            self.log_hid_action(f"Typed string: '{arg}'")
            # If string indicates checking system config or routing
            if "ipconfig" in arg or "netstat" in arg or "discovery" in arg:
                self.current_phase = "RECONNAISSANCE"
            elif "whoami" in arg or "privilege" in arg or "sudo" in arg:
                self.current_phase = "PRIVILEGE_ESCALATION"
        elif cmd == "ENTER":
            self.log_hid_action("Pressed ENTER key")
        elif cmd.startswith("WRITE_MODBUS"):
            self.current_phase = "LATERAL_MOVEMENT"
            self.log_hid_action(f"Injected Modbus command: {step}")
        elif cmd.startswith("SPOOF") or cmd.startswith("CORRUPT"):
            self.current_phase = "IMPACT"
            self.log_hid_action(f"Executed telemetry integrity attack: {step}")
        else:
            self.log_hid_action(f"Executed HID action: {step}")
            
    def log_hid_action(self, action: str):
        self.hid_timeline.append({
            "timestamp": int(time.time() * 1000),
            "step": self.current_step_index + 1,
            "action": action
        })
        if len(self.hid_timeline) > 30:
            self.hid_timeline.pop(0)
            
    def log_usb_event(self, event_type: str, device: str, details: str, severity: str):
        event = {
            "timestamp": int(time.time() * 1000),
            "event_type": event_type,
            "device": device,
            "details": details,
            "severity": severity
        }
        self.usb_events.append(event)
        if len(self.usb_events) > 30:
            self.usb_events.pop(0)
            
    def reset(self):
        self.attack_state = "IDLE"
        self.active_payload_id = None
        self.started_at = 0.0
        self.current_step_index = 0
        self.payload_steps.clear()
        self.stealth_wait_ticks = 0
        self.current_phase = "NOMINAL"
        self.hid_timeline.clear()
        self.log_usb_event(
            event_type="USB_REMOVED",
            device="Digispark ATTINY85",
            details="Attack engine reset, device disconnected.",
            severity="INFO"
        )
        logger.info("Digispark engine reset.")
        
    def get_status_payload(self) -> Dict[str, Any]:
        return {
            "timestamp": int(time.time() * 1000),
            "attack_state": self.attack_state,
            "active_payload": self.active_payload_id,
            "time_elapsed": round(time.time() - self.started_at, 2) if self.started_at > 0.0 else 0.0,
            "current_step": self.current_step_index,
            "total_steps": len(self.payload_steps),
            "current_phase": self.current_phase,
            "events_count": len(self.usb_events),
            "hid_timeline": self.hid_timeline
        }
