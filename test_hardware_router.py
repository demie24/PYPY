import unittest
import sys
import os

# Adjust path to import from core/hardware
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(CURRENT_DIR, "core", "hardware"))

from hardware_state_manager import HardwareStateManager
from esp32_bridge import ESP32Bridge
from plc_interface import PLCInterface
from relay_controller import RelayController
from hardware_command_router import HardwareCommandRouter

class TestHardwareRouter(unittest.TestCase):
    def setUp(self):
        self.mgr = HardwareStateManager()
        self.ctrl = RelayController(self.mgr)
        self.esp = ESP32Bridge(self.mgr, self.ctrl)
        self.plc = PLCInterface(self.mgr, self.ctrl)
        self.router = HardwareCommandRouter(self.mgr, self.esp, self.plc, self.ctrl)
        
    def test_route_esp32_breaker(self):
        # Open L4_5 (nominally CLOSED) controlled by ESP32 pin_12
        cmd = {"command": "OPEN", "target": "L4_5", "source": "FLISR"}
        success, msg = self.router.route_command(cmd)
        
        self.assertTrue(success)
        self.assertEqual(self.mgr.gpio["pin_12"], 0)
        self.assertEqual(self.mgr.relays["L4_5"]["coil"], "OPEN")
        
        # Verify transaction logged
        self.assertEqual(len(self.router.command_history), 1)
        self.assertEqual(self.router.command_history[0]["device"], "esp32")
        self.assertEqual(self.router.command_history[0]["status"], "SUCCESS")
        
    def test_route_plc_breaker(self):
        # Close L7_8 (nominally OPEN) controlled by PLC Modbus coil 8
        cmd = {"command": "CLOSE", "target": "L7_8", "source": "FLISR"}
        success, msg = self.router.route_command(cmd)
        
        self.assertTrue(success)
        self.assertEqual(self.mgr.relays["L7_8"]["coil"], "CLOSED")
        
        # Verify transaction logged
        self.assertEqual(len(self.router.command_history), 1)
        self.assertEqual(self.router.command_history[0]["device"], "plc")
        self.assertEqual(self.router.command_history[0]["status"], "SUCCESS")
        
    def test_safety_interlock_generator(self):
        # Open Gen 1 Transformer L1_4: works because L2_7 and L3_9 are CLOSED
        cmd1 = {"command": "OPEN", "target": "L1_4", "source": "SCADA"}
        success1, msg1 = self.router.route_command(cmd1)
        self.assertTrue(success1)
        
        # Open Gen 2 Transformer L2_7: works because L3_9 is CLOSED
        cmd2 = {"command": "OPEN", "target": "L2_7", "source": "SCADA"}
        success2, msg2 = self.router.route_command(cmd2)
        self.assertTrue(success2)
        
        # Open Gen 3 Transformer L3_9: blocked because it is the final closed generator path
        cmd3 = {"command": "OPEN", "target": "L3_9", "source": "SCADA"}
        success3, msg3 = self.router.route_command(cmd3)
        self.assertFalse(success3)
        self.assertIn("Interlock", msg3)
        
        # Transaction logged as BLOCKED
        self.assertEqual(self.router.command_history[-1]["status"], "BLOCKED")
        
    def test_chattering_lockout(self):
        # Toggling twice immediately blocks the second command
        cmd1 = {"command": "OPEN", "target": "L4_5", "source": "SCADA"}
        success1, _ = self.router.route_command(cmd1)
        self.assertTrue(success1)
        
        cmd2 = {"command": "CLOSE", "target": "L4_5", "source": "SCADA"}
        success2, msg2 = self.router.route_command(cmd2)
        self.assertFalse(success2)
        self.assertIn("lockout", msg2)

if __name__ == "__main__":
    unittest.main()
