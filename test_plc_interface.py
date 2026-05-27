import unittest
import sys
import os

# Adjust path to import from core/hardware
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(CURRENT_DIR, "core", "hardware"))

from hardware_state_manager import HardwareStateManager
from relay_controller import RelayController
from plc_interface import PLCInterface

class TestPLCInterface(unittest.TestCase):
    def setUp(self):
        self.mgr = HardwareStateManager()
        self.ctrl = RelayController(self.mgr)
        self.plc = PLCInterface(self.mgr, self.ctrl)
        
    def test_read_coils(self):
        # Read first 9 coils (Breakers L1_4 to L8_9)
        coils = self.plc.read_coils(1, 9)
        self.assertEqual(len(coils), 9)
        # L7_8 is normally OPEN (0), others are CLOSED (1)
        self.assertEqual(coils[7], 0)
        self.assertEqual(coils[0], 1)
        
    def test_read_discrete_inputs(self):
        # Read auxiliary feedback starting at 0x1001
        inputs = self.plc.read_discrete_inputs(0x1001, 9)
        self.assertEqual(len(inputs), 9)
        self.assertEqual(inputs[7], 0)
        self.assertEqual(inputs[0], 1)
        
    def test_read_input_registers(self):
        # Read bus voltages starting at 0x3001
        # Bus 1 voltage is 1.04 -> Scaled x1000 = 1040
        regs = self.plc.read_input_registers(0x3001, 3)
        self.assertEqual(len(regs), 3)
        self.assertEqual(regs[0], 1040)
        self.assertEqual(regs[1], 1025)
        
    def test_write_single_coil(self):
        # Close L7_8 (address 8: 1-indexed index 7)
        success = self.plc.write_single_coil(8, 1)
        self.assertTrue(success)
        self.assertEqual(self.mgr.relays["L7_8"]["coil"], "CLOSED")
        
    def test_comms_failure(self):
        self.plc.set_comms_failure(True)
        
        # Read operations return None
        coils = self.plc.read_coils(1, 9)
        self.assertIsNone(coils)
        
        # Write operation returns False and trust is penalized
        success = self.plc.write_single_coil(8, 1)
        self.assertFalse(success)
        self.assertLess(self.mgr.devices["plc"]["trust"], 1.0)

if __name__ == "__main__":
    unittest.main()
