import unittest
import sys
import os
import time

# Adjust path to import from core/hardware
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

from core.hardware.digispark_attack_engine import DigisparkAttackEngine

class TestDigisparkAttackEngine(unittest.TestCase):
    def setUp(self):
        self.engine = DigisparkAttackEngine()
        
    def test_payload_registration(self):
        self.assertIn("keystroke_bypass", self.engine.payloads)
        self.assertIn("unauthorized_serial", self.engine.payloads)
        self.assertIn("firmware_flasher", self.engine.payloads)
        
        metadata = self.engine.payloads["keystroke_bypass"]
        self.assertEqual(metadata["type"], "HID_KEYSTROKE")
        self.assertEqual(metadata["target_device"], "operator_console")
        
    def test_trigger_attack(self):
        # Triggering unknown payload should fail
        success = self.engine.trigger_attack("invalid_payload")
        self.assertFalse(success)
        self.assertEqual(self.engine.attack_state, "IDLE")
        
        # Triggering valid payload
        success = self.engine.trigger_attack("keystroke_bypass")
        self.assertTrue(success)
        self.assertEqual(self.engine.attack_state, "ARMED")
        self.assertEqual(self.engine.active_payload_id, "keystroke_bypass")
        self.assertGreater(self.engine.started_at, 0.0)
        self.assertTrue(len(self.engine.usb_events) > 0)
        self.assertEqual(self.engine.usb_events[-1]["event_type"], "USB_INSERTED")
        
    def test_tick_transitions(self):
        self.engine.execution_duration = 0.1  # Fast execution for test
        self.engine.trigger_attack("keystroke_bypass")
        
        # First tick transitions ARMED -> EXECUTING
        payload = self.engine.tick()
        self.assertEqual(self.engine.attack_state, "EXECUTING")
        self.assertEqual(payload["attack_state"], "EXECUTING")
        self.assertEqual(self.engine.usb_events[-1]["event_type"], "HID_INJECTION_START")
        
        # Wait for duration and tick again to transition to COMPLETED
        time.sleep(0.15)
        payload = self.engine.tick()
        self.assertEqual(self.engine.attack_state, "COMPLETED")
        self.assertEqual(payload["attack_state"], "COMPLETED")
        self.assertEqual(self.engine.usb_events[-1]["event_type"], "HID_INJECTION_COMPLETE")
        
    def test_reset(self):
        self.engine.trigger_attack("keystroke_bypass")
        self.engine.reset()
        self.assertEqual(self.engine.attack_state, "IDLE")
        self.assertIsNone(self.engine.active_payload_id)
        self.assertEqual(self.engine.usb_events[-1]["event_type"], "USB_REMOVED")

if __name__ == "__main__":
    unittest.main()
