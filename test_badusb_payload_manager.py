import unittest
import sys
import os

# Adjust path to import from core/hardware
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(CURRENT_DIR, "core", "hardware"))

from badusb_payload_manager import BadUSBPayloadManager

class TestBadUSBPayloadManager(unittest.TestCase):
    def setUp(self):
        self.manager = BadUSBPayloadManager()
        
    def test_payloads_exist(self):
        all_payloads = self.manager.get_all_payloads()
        self.assertEqual(len(all_payloads), 6)
        
        ids = [p["payload_id"] for p in all_payloads]
        self.assertIn("recon_discovery", ids)
        self.assertIn("firmware_modbus_hijack", ids)
        self.assertIn("trust_sabotage", ids)
        
    def test_get_payload_script(self):
        # Unknown payload returns empty script list
        script = self.manager.get_payload_script("invalid")
        self.assertEqual(script, [])
        
        # Valid payload returns script steps
        script = self.manager.get_payload_script("recon_discovery")
        self.assertGreater(len(script), 0)
        self.assertIn("GUI r", script)
        self.assertIn("STRING cmd", script)
        
    def test_get_payload_metadata(self):
        # Unknown payload returns empty dict
        meta = self.manager.get_payload_metadata("invalid")
        self.assertEqual(meta, {})
        
        # Valid payload returns category and target
        meta = self.manager.get_payload_metadata("firmware_modbus_hijack")
        self.assertEqual(meta["category"], "COMMAND_INJECTION")
        self.assertEqual(meta["target"], "PLC Modbus register port")

if __name__ == "__main__":
    unittest.main()
