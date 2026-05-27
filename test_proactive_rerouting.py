import unittest
import sys
import os

# Setup import paths
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "core", "self_healing")))

from proactive_rerouting_engine import ProactiveReroutingEngine
from topology_recovery_engine import TopologyRecoveryEngine

class TestProactiveRerouting(unittest.TestCase):
    def setUp(self):
        self.topo_engine = TopologyRecoveryEngine()
        self.engine = ProactiveReroutingEngine(self.topo_engine)

    def test_no_telemetry(self):
        res = self.engine.analyze_rerouting(None, {})
        self.assertFalse(res["proactive_rerouting_active"])
        self.assertEqual(res["reason"], "No telemetry data")

    def test_nominal_loadings(self):
        telemetry = {
            "state": {
                "breakers": {"L7_8": "OPEN"},
                "lines": {
                    "L1_4": {"capacity_pct": 50.0},
                    "L2_7": {"capacity_pct": 40.0}
                }
            }
        }
        res = self.engine.analyze_rerouting(telemetry, {"predicted_overloads": []})
        self.assertFalse(res["proactive_rerouting_active"])
        self.assertEqual(res["reason"], "Grid loadings within nominal thresholds.")

    def test_proactive_tie_line_close(self):
        telemetry = {
            "state": {
                "breakers": {"L7_8": "OPEN"},
                "lines": {
                    "L1_4": {"capacity_pct": 85.0},
                    "L2_7": {"capacity_pct": 40.0}
                }
            }
        }
        # L1_4 capacity > 80%, so it is high risk
        res = self.engine.analyze_rerouting(telemetry, {"predicted_overloads": []})
        self.assertTrue(res["proactive_rerouting_active"])
        self.assertEqual(len(res["recommended_rerouting"]), 1)
        self.assertEqual(res["recommended_rerouting"][0]["command"], "CLOSE")
        self.assertEqual(res["recommended_rerouting"][0]["target"], "L7_8")
        self.assertIn("L7_8", res["recommended_rerouting"][0]["reason"])

    def test_alternate_line_close(self):
        telemetry = {
            "state": {
                # L7_8 is closed, L4_9 is open (and not L7_8)
                "breakers": {"L7_8": "CLOSED", "L4_9": "OPEN"},
                "lines": {
                    "L1_4": {"capacity_pct": 90.0}, # terminals 0 and 3
                    "L2_7": {"capacity_pct": 40.0}
                }
            }
        }
        # L1_4 is high risk. L4_9 connects from 3 to 8. Terminal 3 is shared with L1_4 (0 to 3).
        res = self.engine.analyze_rerouting(telemetry, {"predicted_overloads": []})
        self.assertTrue(res["proactive_rerouting_active"])
        self.assertEqual(len(res["recommended_rerouting"]), 1)
        self.assertEqual(res["recommended_rerouting"][0]["command"], "CLOSE")
        self.assertEqual(res["recommended_rerouting"][0]["target"], "L4_9")
        self.assertIn("L4_9", res["recommended_rerouting"][0]["reason"])

if __name__ == "__main__":
    unittest.main()
