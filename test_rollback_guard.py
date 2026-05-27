import unittest
import sys
import os
import time

# Setup import paths
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "core", "self_healing")))

from rollback_guard import RollbackGuard

class TestRollbackGuard(unittest.TestCase):
    def setUp(self):
        self.guard = RollbackGuard()

    def test_lockout_registration(self):
        breaker = "L7_8"
        self.assertFalse(self.guard.is_locked_out(breaker))
        
        # Lockout for 1 second
        self.guard.lockout(breaker, duration=1.0)
        self.assertTrue(self.guard.is_locked_out(breaker))
        self.assertEqual(self.guard.rollback_count, 1)
        
        # Wait 1.1 seconds for lockout to expire
        time.sleep(1.1)
        self.assertFalse(self.guard.is_locked_out(breaker))

    def test_oscillation_detection(self):
        # Empty action logs
        logs = []
        osc, reason = self.guard.detect_oscillation(logs)
        self.assertFalse(osc)
        
        now_ms = time.time() * 1000
        
        # Breaker toggled twice in logs
        logs = [
            {"timestamp": now_ms - 2000, "target": "L7_8", "action": "CLOSE"},
            {"timestamp": now_ms - 1000, "target": "L7_8", "action": "OPEN"},
        ]
        osc, reason = self.guard.detect_oscillation(logs)
        self.assertFalse(osc)
        
        # Breaker toggled three times (CLOSE -> OPEN -> CLOSE)
        logs.append({"timestamp": now_ms, "target": "L7_8", "action": "CLOSE"})
        osc, reason = self.guard.detect_oscillation(logs)
        self.assertTrue(osc)
        self.assertIn("L7_8", reason)

if __name__ == "__main__":
    unittest.main()
