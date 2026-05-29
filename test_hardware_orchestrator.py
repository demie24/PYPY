import unittest
import sys
import os
import time

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(CURRENT_DIR, "core", "hardware"))

from hardware_state_manager import HardwareStateManager
from esp32_bridge import ESP32Bridge
from plc_interface import PLCInterface
from relay_controller import RelayController
from hardware_command_router import HardwareCommandRouter
from hardware_orchestrator import HardwareOrchestrator

class TestHardwareOrchestrator(unittest.TestCase):
    def setUp(self):
        self.mgr = HardwareStateManager()
        self.ctrl = RelayController(self.mgr)
        self.esp = ESP32Bridge(self.mgr, self.ctrl)
        self.plc = PLCInterface(self.mgr, self.ctrl)
        self.router = HardwareCommandRouter(self.mgr, self.esp, self.plc, self.ctrl)
        self.orch = HardwareOrchestrator(self.mgr, self.router)
        
    def test_priority_arbitration_locking(self):
        # 1. Submit high priority command (LOCAL_PROTECTION) on L1_4
        high_cmd = {"command": "OPEN", "target": "L1_4", "source": "LOCAL_PROTECTION"}
        success1, msg1 = self.orch.submit_command(high_cmd)
        self.assertTrue(success1)
        
        # Lock is established
        self.assertIn("L1_4", self.orch.breaker_locks)
        self.assertEqual(self.orch.breaker_locks["L1_4"]["source"], "LOCAL_PROTECTION")
        self.assertEqual(self.orch.breaker_locks["L1_4"]["priority"], 1)
        
        # 2. Submit low priority command (SCADA) on L1_4: blocked!
        low_cmd = {"command": "CLOSE", "target": "L1_4", "source": "SCADA"}
        success2, msg2 = self.orch.submit_command(low_cmd)
        self.assertFalse(success2)
        self.assertIn("Blocked", msg2)
        
        # Lock is still held by high priority source
        self.assertEqual(self.orch.breaker_locks["L1_4"]["source"], "LOCAL_PROTECTION")
        
        # Check conflict logged
        self.assertEqual(len(self.orch.conflicts), 1)
        self.assertEqual(self.orch.conflicts[0]["breaker"], "L1_4")
        self.assertEqual(self.orch.conflicts[0]["action"], "BLOCKED")

    def test_priority_arbitration_overriding(self):
        # 1. Submit low priority lock (SCADA)
        low_cmd = {"command": "CLOSE", "target": "L7_8", "source": "SCADA"}
        success1, _ = self.orch.submit_command(low_cmd)
        self.assertTrue(success1)
        
        # Lock established by SCADA
        self.assertEqual(self.orch.breaker_locks["L7_8"]["source"], "SCADA")
        self.assertEqual(self.orch.breaker_locks["L7_8"]["priority"], 3)
        
        # 2. Submit high priority command (LOCAL_PROTECTION): overrides lock!
        high_cmd = {"command": "OPEN", "target": "L7_8", "source": "LOCAL_PROTECTION"}
        success2, _ = self.orch.submit_command(high_cmd)
        self.assertTrue(success2)
        
        # Lock successfully updated to LOCAL_PROTECTION
        self.assertEqual(self.orch.breaker_locks["L7_8"]["source"], "LOCAL_PROTECTION")
        self.assertEqual(self.orch.breaker_locks["L7_8"]["priority"], 1)
        
        # Check conflict logged
        self.assertEqual(len(self.orch.conflicts), 1)
        self.assertEqual(self.orch.conflicts[0]["breaker"], "L7_8")
        self.assertEqual(self.orch.conflicts[0]["action"], "OVERRIDDEN")

    def test_orchestration_loop_ticks(self):
        cmd = {"command": "OPEN", "target": "L4_5", "source": "SCADA"}
        success, _ = self.orch.submit_command(cmd)
        self.assertTrue(success)
        
        # Process command queue via tick
        self.orch.tick()
        
        # Verify telemetry structures
        telem = self.orch.get_orchestration_telemetry()
        self.assertIsNotNone(telem)
        self.assertIn("L4_5", telem["active_locks"])

if __name__ == "__main__":
    unittest.main()
