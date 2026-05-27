import time
import logging
from typing import Dict, Any, List, Optional
from digispark_attack_engine import DigisparkAttackEngine
from badusb_payload_manager import BadUSBPayloadManager
from rogue_device_monitor import RogueDeviceMonitor
from hardware_intrusion_detector import HardwareIntrusionDetector

logger = logging.getLogger("hardware.attack_orchestrator")

class CyberPhysicalAttackOrchestrator:
    def __init__(self,
                 digispark_engine: DigisparkAttackEngine,
                 badusb_manager: BadUSBPayloadManager,
                 rogue_monitor: RogueDeviceMonitor,
                 intrusion_detector: HardwareIntrusionDetector):
                 
        self.digispark = digispark_engine
        self.badusb = badusb_manager
        self.rogue = rogue_monitor
        self.intrusion = intrusion_detector
        
        # State machine: NOMINAL, INTRUSION_DETECTED, ACTIVE_HID_INJECTION, PORT_QUARANTINED, COMPROMISED
        self.attack_escalation_state = "NOMINAL"
        self.quarantined_ports: List[str] = []
        
        # Coordinated campaign variables
        self.active_campaign: Optional[str] = None
        self.campaign_step = 0
        self.campaign_last_tick = 0.0
        self.campaign_data: Dict[str, Any] = {}
        
    def start_campaign(self, campaign_name: str) -> bool:
        """
        Triggers a sequenced cyber-physical attack campaign.
        """
        allowed_campaigns = ["coordinated_blackout", "stealthy_calibration_drift", "reconnect_flood_dos"]
        if campaign_name not in allowed_campaigns:
            logger.warning(f"Failed to start campaign: {campaign_name} not recognized.")
            return False
            
        self.active_campaign = campaign_name
        self.campaign_step = 1
        self.campaign_last_tick = time.time()
        self.campaign_data.clear()
        
        logger.warning(f"[CAMPAIGN STARTED] Initiated coordinated campaign: {campaign_name}")
        return True
        
    def tick_campaign(self) -> Optional[Dict[str, Any]]:
        """
        Executes step transitions for coordinated campaigns.
        Called in the main HAL loop (1Hz).
        """
        if not self.active_campaign:
            return None
            
        now = time.time()
        # Campaign steps execute every 2 seconds for visibility
        if now - self.campaign_last_tick < 2.0:
            return self.get_campaign_status()
            
        self.campaign_last_tick = now
        
        if self.active_campaign == "coordinated_blackout":
            self._execute_blackout_step()
        elif self.active_campaign == "stealthy_calibration_drift":
            self._execute_drift_step()
        elif self.active_campaign == "reconnect_flood_dos":
            self._execute_flood_step()
            
        return self.get_campaign_status()
        
    def _execute_blackout_step(self):
        if self.campaign_step == 1:
            # Step 1: Insert rogue device
            self.rogue.simulate_device_insertion("16c0", "05df", "Rubber Ducky Key Injector")
            self.campaign_step = 2
            logger.info("Blackout Campaign [Step 1/4]: Inserted rogue USB Rubber Ducky device.")
        elif self.campaign_step == 2:
            # Step 2: Run discovery
            script = self.badusb.get_payload_script("recon_discovery")
            self.digispark.trigger_attack("keystroke_bypass", delay_ticks=0, steps=script)
            self.campaign_step = 3
            logger.info("Blackout Campaign [Step 2/4]: Triggered network discovery DuckyScript.")
        elif self.campaign_step == 3:
            # Step 3: Privilege escalation / Operator impersonation
            script = self.badusb.get_payload_script("operator_compromise")
            self.digispark.trigger_attack("keystroke_bypass", delay_ticks=0, steps=script)
            self.campaign_step = 4
            logger.info("Blackout Campaign [Step 3/4]: Triggered Operator Impersonation script.")
        elif self.campaign_step == 4:
            # Step 4: Hijack Modbus coils (trip L6_7 breaker)
            script = self.badusb.get_payload_script("firmware_modbus_hijack")
            self.digispark.trigger_attack("keystroke_bypass", delay_ticks=0, steps=script)
            self.campaign_step = 5
            logger.info("Blackout Campaign [Step 4/4]: Executed Modbus register hijack payload.")
        else:
            logger.info("Blackout Campaign finished successfully.")
            self.active_campaign = None
            
    def _execute_drift_step(self):
        if self.campaign_step == 1:
            # Step 1: Insert rogue device with 4-tick stealth delay
            self.rogue.simulate_device_insertion("16c0", "2770", "Stealth ATTINY85 BadUSB", stealth_ticks=4)
            self.campaign_step = 2
            logger.info("Drift Campaign [Step 1/3]: Mounted stealth BadUSB device.")
        elif self.campaign_step == 2:
            # Wait for stealth device to trigger
            if "16c0:2770" not in self.rogue.stealth_devices:
                # Device became active
                script = self.badusb.get_payload_script("trust_sabotage")
                self.digispark.trigger_attack("keystroke_bypass", delay_ticks=0, steps=script)
                self.campaign_step = 3
                logger.info("Drift Campaign [Step 2/3]: Triggered calibration tampering script.")
        elif self.campaign_step == 3:
            if self.digispark.attack_state == "COMPLETED":
                logger.info("Drift Campaign finished successfully.")
                self.active_campaign = None
                
    def _execute_flood_step(self):
        if self.campaign_step == 1:
            # Step 1: Trigger reconnect flood
            self.rogue.simulate_device_insertion("16c0", "0487", "Teensy 4.0 Rogue Serial Host")
            self.campaign_step = 2
            logger.info("DoS Campaign [Step 1/3]: Mounted Teensy device.")
        elif self.campaign_step == 2:
            # Reconnect device multiple times to trigger Reconnect Abuse
            self.rogue.simulate_device_removal("16c0", "0487")
            self.rogue.simulate_device_insertion("16c0", "0487", "Teensy 4.0 Rogue Serial Host")
            self.rogue.simulate_device_removal("16c0", "0487")
            self.rogue.simulate_device_insertion("16c0", "0487", "Teensy 4.0 Rogue Serial Host")
            self.campaign_step = 3
            logger.info("DoS Campaign [Step 2/3]: Executed rapid connection cycles.")
        elif self.campaign_step == 3:
            logger.info("DoS Campaign completed.")
            self.active_campaign = None
            
    def get_campaign_status(self) -> Dict[str, Any]:
        return {
            "active_campaign": self.active_campaign,
            "step": self.campaign_step,
            "phase_label": f"Step {self.campaign_step}" if self.active_campaign else "IDLE"
        }
        
    def execute_quarantine(self, port_id: str) -> bool:
        """
        Operator or AI Agent action to isolate a virtual port or device to suppress propagation.
        """
        if port_id not in self.quarantined_ports:
            self.quarantined_ports.append(port_id)
            self.rogue.quarantine_port(port_id)
            logger.warning(f"[QUARANTINE ENGAGED] Isolated compromised interface port: {port_id}")
            return True
        return False
        
    def remove_quarantine(self, port_id: str) -> bool:
        if port_id in self.quarantined_ports:
            self.quarantined_ports.remove(port_id)
            self.rogue.release_port(port_id)
            logger.info(f"[QUARANTINE RELEASED] Restored interface port: {port_id}")
            return True
        return False
        
    def evaluate_escalation_state(self):
        """
        Computes the global attack orchestration state machine based on constituent engine variables.
        Also triggers autonomous quarantine escalation.
        """
        trust = self.rogue.hardware_trust_score
        score = self.intrusion.intrusion_score
        digi_state = self.digispark.attack_state
        
        # 1. Autonomous Quarantine Escalation
        # If trust score falls below 0.40 or intrusion score exceeds 75.0, automatically quarantine the rogue port.
        if (trust <= 0.40 or score >= 75.0) and "Port 7" not in self.quarantined_ports:
            logger.warning("[AUTONOMOUS DEFENSE] Intrusion threshold exceeded. Initiating quarantine on Port 7.")
            self.execute_quarantine("Port 7")
            
        # 2. State Machine transitions
        if self.quarantined_ports:
            self.attack_escalation_state = "PORT_QUARANTINED"
        elif digi_state in ["ARMED", "EXECUTING"]:
            self.attack_escalation_state = "ACTIVE_HID_INJECTION"
        elif trust <= 0.40 or score >= 70.0:
            self.attack_escalation_state = "COMPROMISED"
        elif trust < 1.0 or score >= 20.0:
            self.attack_escalation_state = "INTRUSION_DETECTED"
        else:
            self.attack_escalation_state = "NOMINAL"
            
    def get_propagation_chain(self) -> Dict[str, Any]:
        """
        Computes the dynamic compromise propagation path from insertion point to substation relay.
        """
        trust = self.rogue.hardware_trust_score
        score = self.intrusion.intrusion_score
        
        # Determine node statuses
        usb_status = "COMPROMISED" if trust < 1.0 else "NOMINAL"
        bridge_status = "COMPROMISED" if trust < 0.70 else "NOMINAL"
        gateway_status = "COMPROMISED" if score >= 35.0 else "NOMINAL"
        relay_status = "COMPROMISED" if score >= 70.0 else "NOMINAL"
        
        # Check quarantine
        if "Port 7" in self.quarantined_ports:
            usb_status = "QUARANTINED"
        if "ESP32" in self.quarantined_ports:
            bridge_status = "QUARANTINED"
        if "PLC" in self.quarantined_ports:
            gateway_status = "QUARANTINED"
            
        return {
            "timestamp": int(time.time() * 1000),
            "nodes": [
                {"id": "USB_Port_7", "label": "USB Physical Interface", "status": usb_status},
                {"id": "ESP32_Bridge", "label": "Virtual Device COM Bridge", "status": bridge_status},
                {"id": "PLC_Modbus_Gateway", "label": "Modbus Gateway Protocol", "status": gateway_status},
                {"id": "Breaker_Relays", "label": "Physical Breaker Actuators", "status": relay_status}
            ],
            "links": [
                {"source": "USB_Port_7", "target": "ESP32_Bridge", "status": "BLOCKED" if usb_status == "QUARANTINED" else "ACTIVE"},
                {"source": "ESP32_Bridge", "target": "PLC_Modbus_Gateway", "status": "BLOCKED" if bridge_status == "QUARANTINED" else "ACTIVE"},
                {"source": "PLC_Modbus_Gateway", "target": "Breaker_Relays", "status": "BLOCKED" if gateway_status == "QUARANTINED" else "ACTIVE"}
            ]
        }
            
    def get_orchestration_payload(self) -> Dict[str, Any]:
        self.evaluate_escalation_state()
        return {
            "timestamp": int(time.time() * 1000),
            "attack_escalation_state": self.attack_escalation_state,
            "quarantined_ports": self.quarantined_ports,
            "hardware_trust": round(self.rogue.hardware_trust_score, 2),
            "intrusion_score": round(self.intrusion.intrusion_score, 1),
            "digispark_state": self.digispark.attack_state,
            "campaign": self.get_campaign_status()
        }
        
    def reset(self):
        self.digispark.reset()
        self.rogue.reset()
        self.intrusion.reset()
        self.quarantined_ports.clear()
        self.active_campaign = None
        self.campaign_step = 0
        self.campaign_data.clear()
        self.attack_escalation_state = "NOMINAL"
        logger.info("Central Attack Orchestrator fully reset to NOMINAL grid states.")
