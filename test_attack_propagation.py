import unittest
import sys
import os
import time

# Adjust path to import from core/hardware
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(CURRENT_DIR, "core", "hardware"))
sys.path.append(os.path.join(CURRENT_DIR, "core", "orchestrator"))

from cyber_physical_attack_orchestrator import CyberPhysicalAttackOrchestrator
from digispark_attack_engine import DigisparkAttackEngine
from badusb_payload_manager import BadUSBPayloadManager
from rogue_device_monitor import RogueDeviceMonitor
from hardware_intrusion_detector import HardwareIntrusionDetector

class TestAttackPropagation(unittest.TestCase):
    def setUp(self):
        self.orchestrator = CyberPhysicalAttackOrchestrator(
            digispark_engine=DigisparkAttackEngine(),
            badusb_manager=BadUSBPayloadManager(),
            rogue_monitor=RogueDeviceMonitor(),
            intrusion_detector=HardwareIntrusionDetector()
        )
        
    def test_initial_propagation_chain(self):
        # By default, all should be NOMINAL
        chain = self.orchestrator.get_propagation_chain()
        self.assertIn("nodes", chain)
        self.assertIn("links", chain)
        
        nodes = {n["id"]: n["status"] for n in chain["nodes"]}
        self.assertEqual(nodes["USB_Port_7"], "NOMINAL")
        self.assertEqual(nodes["ESP32_Bridge"], "NOMINAL")
        self.assertEqual(nodes["PLC_Modbus_Gateway"], "NOMINAL")
        self.assertEqual(nodes["Breaker_Relays"], "NOMINAL")
        
        links = chain["links"]
        for link in links:
            self.assertEqual(link["status"], "ACTIVE")
            
    def test_propagation_compromise_transitions(self):
        # Decay trust to trigger ESP32_Bridge compromise
        self.orchestrator.rogue.hardware_trust_score = 0.65
        self.orchestrator.intrusion.intrusion_score = 40.0
        
        chain = self.orchestrator.get_propagation_chain()
        nodes = {n["id"]: n["status"] for n in chain["nodes"]}
        self.assertEqual(nodes["USB_Port_7"], "COMPROMISED")
        self.assertEqual(nodes["ESP32_Bridge"], "COMPROMISED")
        self.assertEqual(nodes["PLC_Modbus_Gateway"], "COMPROMISED")
        self.assertEqual(nodes["Breaker_Relays"], "NOMINAL")  # threshold is 70
        
        # Increase intrusion score to compromise relays
        self.orchestrator.intrusion.intrusion_score = 75.0
        chain = self.orchestrator.get_propagation_chain()
        nodes = {n["id"]: n["status"] for n in chain["nodes"]}
        self.assertEqual(nodes["Breaker_Relays"], "COMPROMISED")

    def test_propagation_quarantine_links(self):
        # Quarantine ESP32
        self.orchestrator.execute_quarantine("ESP32")
        
        chain = self.orchestrator.get_propagation_chain()
        nodes = {n["id"]: n["status"] for n in chain["nodes"]}
        self.assertEqual(nodes["ESP32_Bridge"], "QUARANTINED")
        
        # Verify link blocking
        links = {f"{l['source']}->{l['target']}": l["status"] for l in chain["links"]}
        self.assertEqual(links["ESP32_Bridge->PLC_Modbus_Gateway"], "BLOCKED")
        self.assertEqual(links["USB_Port_7->ESP32_Bridge"], "ACTIVE")

if __name__ == "__main__":
    unittest.main()
