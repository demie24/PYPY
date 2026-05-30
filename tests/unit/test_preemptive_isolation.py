import unittest
import sys
import os

# Setup import paths

from core.self_healing.preemptive_isolation_engine import PreemptiveIsolationEngine
from core.self_healing.topology_recovery_engine import TopologyRecoveryEngine

class TestPreemptiveIsolation(unittest.TestCase):
    def setUp(self):
        self.topo_engine = TopologyRecoveryEngine()
        self.engine = PreemptiveIsolationEngine(self.topo_engine)

    def test_no_telemetry(self):
        res = self.engine.analyze_isolation(None, {})
        self.assertFalse(res["preemptive_isolation_active"])
        self.assertEqual(res["recommended_isolation"], [])

    def test_no_threat(self):
        telemetry = {
            "state": {
                "breakers": {"L1_4": "CLOSED"},
                "buses": {"Bus_5": {"voltage_pu": 1.0}},
                "lines": {"L1_4": {"capacity_pct": 50.0}}
            }
        }
        res = self.engine.analyze_isolation(telemetry, {})
        self.assertFalse(res["preemptive_isolation_active"])

    def test_bus_voltage_collapse_isolation(self):
        # Bus_6 voltage collapsing to 0.85
        telemetry = {
            "state": {
                "breakers": {
                    "L1_4": "CLOSED",
                    "L2_7": "CLOSED",
                    "L3_9": "CLOSED",
                    "L4_5": "CLOSED",
                    "L4_9": "CLOSED",
                    "L5_6": "CLOSED",
                    "L6_7": "CLOSED",
                    "L7_8": "CLOSED",
                    "L8_9": "CLOSED"
                },
                "buses": {
                    "Bus_6": {"voltage_pu": 0.85},
                    "Bus_5": {"voltage_pu": 1.0}
                },
                "lines": {
                    "L5_6": {"capacity_pct": 50.0},
                    "L6_7": {"capacity_pct": 50.0}
                }
            }
        }
        res = self.engine.analyze_isolation(telemetry, {})
        self.assertTrue(res["preemptive_isolation_active"])
        # Bus_6 is connected to L5_6 and L6_7
        targets = [r["target"] for r in res["recommended_isolation"]]
        self.assertIn("L5_6", targets)
        self.assertIn("L6_7", targets)

    def test_cyber_compromise_isolation(self):
        # Bus_7 cyber compromised
        telemetry = {
            "state": {
                "breakers": {
                    "L2_7": "CLOSED",
                    "L6_7": "CLOSED",
                    "L7_8": "CLOSED"
                },
                "buses": {
                    "Bus_7": {"voltage_pu": 1.0},
                    "Bus_5": {"voltage_pu": 1.0}
                },
                "lines": {}
            }
        }
        attack_status = {
            "compromised_nodes": {
                "Bus_7": {"attack_type": "FDIA"}
            }
        }
        res = self.engine.analyze_isolation(telemetry, {}, attack_status)
        self.assertTrue(res["preemptive_isolation_active"])
        targets = [r["target"] for r in res["recommended_isolation"]]
        self.assertIn("L2_7", targets)
        self.assertIn("L6_7", targets)
        self.assertIn("L7_8", targets)

    def test_line_overload_isolation(self):
        # Line L1_4 overloaded
        telemetry = {
            "state": {
                "breakers": {"L1_4": "CLOSED"},
                "buses": {"Bus_5": {"voltage_pu": 1.0}},
                "lines": {"L1_4": {"capacity_pct": 115.0}}
            }
        }
        res = self.engine.analyze_isolation(telemetry, {})
        self.assertTrue(res["preemptive_isolation_active"])
        self.assertEqual(res["recommended_isolation"][0]["target"], "L1_4")
        self.assertEqual(res["recommended_isolation"][0]["command"], "OPEN")

    def test_protect_bus5_hospital(self):
        # Let's set up breakers such that:
        # L2_7 and L7_8 are OPEN.
        # If we compromise Bus_6, candidate isolation breakers are L5_6 and L6_7.
        # Opening L5_6 will isolate Bus_6 (load) but not Bus_5 (which remains connected to Bus_1 generator).
        # This will be allowed and registered in side_effects with severity HIGH.
        # But if we also open L4_5, then opening L5_6 would isolate Bus_5 (hospital), which will be BLOCKED.
        telemetry = {
            "state": {
                "breakers": {
                    "L1_4": "CLOSED",
                    "L2_7": "OPEN", # Open to make Bus_6 isolatable
                    "L3_9": "CLOSED",
                    "L4_5": "CLOSED", # Kept closed so Bus_5 is safe when L5_6 is opened
                    "L4_9": "CLOSED",
                    "L5_6": "CLOSED",
                    "L6_7": "CLOSED",
                    "L7_8": "OPEN", # Open
                    "L8_9": "CLOSED"
                },
                "buses": {
                    "Bus_6": {"voltage_pu": 1.0},
                    "Bus_5": {"voltage_pu": 1.0}
                },
                "lines": {}
            }
        }
        attack_status = {
            "compromised_nodes": {
                "Bus_6": {"attack_type": "FDIA"}
            }
        }
        res = self.engine.analyze_isolation(telemetry, {}, attack_status)
        targets = [r["target"] for r in res["recommended_isolation"]]
        # Since Bus_5 is not isolated, L5_6 and L6_7 should both be allowed targets
        self.assertIn("L5_6", targets)
        self.assertIn("L6_7", targets)
        # Side effect on L5_6 should be registered for Bus_6
        self.assertIn("L5_6", res["side_effects"])
        self.assertEqual(res["side_effects"]["L5_6"]["severity"], "HIGH")
        self.assertIn("Bus_6", res["side_effects"]["L5_6"]["isolated_loads"])

        # Now, if we set L4_5 to OPEN, opening L5_6 will isolate Bus_5, which should be blocked
        telemetry["state"]["breakers"]["L4_5"] = "OPEN"
        res_blocked = self.engine.analyze_isolation(telemetry, {}, attack_status)
        targets_blocked = [r["target"] for r in res_blocked["recommended_isolation"]]
        self.assertNotIn("L5_6", targets_blocked)
        self.assertIn("L5_6", res_blocked["side_effects"])
        self.assertIn("Bus_5", res_blocked["side_effects"]["L5_6"]["isolated_loads"])

if __name__ == "__main__":
    unittest.main()
