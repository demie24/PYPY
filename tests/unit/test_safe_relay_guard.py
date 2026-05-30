import unittest
import sys
import os

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

from core.hardware.safe_relay_guard import SafeRelayGuard

class TestSafeRelayGuard(unittest.TestCase):
    def setUp(self):
        self.guard = SafeRelayGuard()

    def test_emergency_stop_routing(self):
        # Trigger E-stop
        commands = self.guard.trigger_emergency_stop()
        self.assertTrue(self.guard.emergency_stop_active)
        self.assertEqual(len(commands), 9) # All 9 lines commanded
        self.assertTrue(any(c["target"] == "L7_8" and c["command"] == "OPEN" for c in commands))
        self.assertTrue(any(c["target"] == "L1_4" and c["command"] == "CLOSED" for c in commands))

        # Check block when active
        safe, msg = self.guard.validate_command({"command": "OPEN", "target": "L1_4"}, {})
        self.assertFalse(safe)
        self.assertIn("Emergency Stop is active", msg)

        # Reset E-stop
        self.guard.reset_emergency_stop()
        self.assertFalse(self.guard.emergency_stop_active)
        
        # Commands should validate normally now
        safe, msg = self.guard.validate_command({"command": "CLOSE", "target": "L1_4"}, {})
        self.assertTrue(safe)

    def test_generator_isolation_interlock(self):
        # Trying to open L1_4 (radial generator line to Bus 1)
        safe, msg = self.guard.validate_command(
            {"command": "OPEN", "target": "L1_4", "source": "SCADA_OPERATOR"},
            {}
        )
        self.assertFalse(safe)
        self.assertIn("would isolate generator", msg)

    def test_parallel_check_syncs(self):
        # Line L4_9 is OPEN, we attempt to CLOSE it.
        # Check condition where terminal voltages are out of sync: Bus 4 v=1.0, Bus 9 v=0.85
        current_state = {
            "sensors": {
                "bus_4_v": 1.0,
                "bus_9_v": 0.85
            }
        }
        
        # Should fail sync check (|1.0 - 0.85| = 0.15 pu > 0.1 pu limit)
        safe, msg = self.guard.validate_command(
            {"command": "CLOSE", "target": "L4_9", "source": "SCADA_OPERATOR"},
            current_state
        )
        self.assertFalse(safe)
        self.assertIn("PARALLEL_SYNC_FAIL", msg)

        # In-sync voltages (|1.0 - 0.95| = 0.05 pu <= 0.1 pu limit)
        current_state_ok = {
            "sensors": {
                "bus_4_v": 1.0,
                "bus_9_v": 0.95
            }
        }
        safe, msg = self.guard.validate_command(
            {"command": "CLOSE", "target": "L4_9", "source": "SCADA_OPERATOR"},
            current_state_ok
        )
        self.assertTrue(safe)

    def test_anti_cascade_protection(self):
        # Opening line L4_5 (radial-ish or loop path).
        # Terminal buses are Bus 4 and Bus 5.
        # Adjacent lines to Terminal Bus 4 include L1_4 and L4_9.
        # Let's mock a load current of 0.98 pu (>0.95 pu limit) on line L4_9.
        current_state = {
            "sensors": {
                "line_L4_9_i": 0.98
            }
        }
        
        # Opening L4_5 should be blocked due to cascading overload risk on L4_9
        safe, msg = self.guard.validate_command(
            {"command": "OPEN", "target": "L4_5", "source": "SCADA_OPERATOR"},
            current_state
        )
        self.assertFalse(safe)
        self.assertIn("CASCADING_TRIP_RISK", msg)

        # Normal current (0.6 pu <= 0.95 pu limit)
        current_state_ok = {
            "sensors": {
                "line_L4_9_i": 0.6
            }
        }
        safe, msg = self.guard.validate_command(
            {"command": "OPEN", "target": "L4_5", "source": "SCADA_OPERATOR"},
            current_state_ok
        )
        self.assertTrue(safe)

if __name__ == "__main__":
    unittest.main()
