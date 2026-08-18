import unittest
import sys
import os

# Setup import paths

from core.self_healing.islanding_engine import IslandingEngine

class TestIslandingEngine(unittest.TestCase):
    def setUp(self):
        self.engine = IslandingEngine()

    def test_nominal_islanding(self):
        # Full grid closed, normal voltages
        telemetry = {
            "state": {
                "buses": {
                    f"Bus_{i+1}": {"voltage_pu": 1.0, "is_load": i in [4, 5, 7], "is_gen": i in [0, 1, 2], "P_mw": 0.0, "Q_mvar": 0.0}
                    for i in range(9)
                },
                "lines": {
                    line_id: {"capacity_pct": 20.0}
                    for line_id in ["L1_4", "L2_7", "L3_9", "L4_5", "L4_9", "L5_6", "L6_7", "L8_9"]
                },
                "breakers": {
                    line_id: "CLOSED"
                    for line_id in ["L1_4", "L2_7", "L3_9", "L4_5", "L4_9", "L5_6", "L6_7", "L8_9"]
                }
            }
        }
        # L7_8 normally open
        telemetry["state"]["breakers"]["L7_8"] = "OPEN"

        res = self.engine.analyze_islanding(telemetry)
        self.assertEqual(len(res["active_islands"]), 1)
        self.assertEqual(len(res["healthy_zones"]), 1)
        self.assertEqual(len(res["unstable_zones"]), 0)
        self.assertEqual(len(res["splitting_commands"]), 0)

    def test_unstable_voltage_collapse_islanding(self):
        # Collapse on Bus 5 (voltage = 0.5)
        telemetry = {
            "state": {
                "buses": {
                    f"Bus_{i+1}": {"voltage_pu": 1.0 if i != 4 else 0.5, "is_load": i in [4, 5, 7], "is_gen": i in [0, 1, 2], "P_mw": 0.0, "Q_mvar": 0.0}
                    for i in range(9)
                },
                "lines": {
                    line_id: {"capacity_pct": 20.0}
                    for line_id in ["L1_4", "L2_7", "L3_9", "L4_5", "L4_9", "L5_6", "L6_7", "L8_9"]
                },
                "breakers": {
                    line_id: "CLOSED"
                    for line_id in ["L1_4", "L2_7", "L3_9", "L4_5", "L4_9", "L5_6", "L6_7", "L8_9"]
                }
            }
        }
        telemetry["state"]["breakers"]["L7_8"] = "OPEN"

        res = self.engine.analyze_islanding(telemetry)
        self.assertEqual(len(res["active_islands"]), 1)
        self.assertEqual(len(res["unstable_zones"]), 1)
        # Should propose opening lines connected to Bus_5 (L4_5 and L5_6)
        splitting_targets = [cmd["target"] for cmd in res["splitting_commands"]]
        self.assertIn("L4_5", splitting_targets)
        self.assertIn("L5_6", splitting_targets)

    def test_compromised_voltage_channel_does_not_directly_trip_breakers(self):
        telemetry = {
            "state": {
                "buses": {
                    f"Bus_{i+1}": {"voltage_pu": 0.5 if i == 4 else 1.0, "P_mw": 0.0}
                    for i in range(9)
                },
                "lines": {},
                "breakers": {
                    line["id"]: ("OPEN" if line["id"] == "L7_8" else "CLOSED")
                    for line in self.engine.topo_engine.topo.lines
                },
            }
        }
        attack_status = {"compromised_nodes": {"Bus_5": {"type": "FDIA"}}}

        result = self.engine.analyze_islanding(telemetry, attack_status)

        self.assertTrue(result["unstable_zones"])
        self.assertEqual(result["splitting_commands"], [])

if __name__ == "__main__":
    unittest.main()
