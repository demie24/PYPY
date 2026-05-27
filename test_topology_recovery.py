import unittest
import sys
import os

# Setup import paths
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "core", "self_healing")))

from topology_recovery_engine import TopologyRecoveryEngine

class TestTopologyRecovery(unittest.TestCase):
    def setUp(self):
        self.engine = TopologyRecoveryEngine()

    def test_nominal_topology(self):
        # All breakers CLOSED
        breakers = {line["id"]: "CLOSED" for line in self.engine.topo.lines}
        telemetry = {
            "state": {
                "breakers": breakers,
                "buses": {f"Bus_{i+1}": {"voltage_pu": 1.0} for i in range(9)}
            }
        }
        analysis = self.engine.analyze_topology(telemetry)
        
        # In nominal state, there should be exactly 1 connected component (all buses connected)
        self.assertEqual(len(analysis["components"]), 1)
        self.assertEqual(len(analysis["isolated_segments"]), 0)
        self.assertEqual(len(analysis["reroute_options"]), 0)

    def test_isolated_segment(self):
        # Open L4_5 and L5_6 to isolate Load 5 (Bus 5/index 4) and Load 6 (Bus 6/index 5)
        # Note: Load 5 is index 4, Load 6 is index 5
        breakers = {line["id"]: "CLOSED" for line in self.engine.topo.lines}
        breakers["L4_5"] = "OPEN"
        breakers["L6_7"] = "OPEN"
        
        telemetry = {
            "state": {
                "breakers": breakers,
                "buses": {f"Bus_{i+1}": {"voltage_pu": 1.0 if i != 4 and i != 5 else 0.0} for i in range(9)}
            }
        }
        
        analysis = self.engine.analyze_topology(telemetry)
        
        # We expect index 4 and 5 to be in an isolated segment
        self.assertGreater(len(analysis["isolated_segments"]), 0)
        isolated_buses = []
        for seg in analysis["isolated_segments"]:
            isolated_buses.extend(seg)
            
        self.assertIn(4, isolated_buses)
        self.assertIn(5, isolated_buses)

    def test_reroute_options(self):
        # Normally-open tie breaker is L7_8.
        # If L8_9 is open, Bus 7 (Load 8) is isolated from Bus 8.
        breakers = {line["id"]: "CLOSED" for line in self.engine.topo.lines}
        breakers["L7_8"] = "OPEN"
        breakers["L8_9"] = "OPEN"
        
        telemetry = {
            "state": {
                "breakers": breakers,
                "buses": {f"Bus_{i+1}": {"voltage_pu": 1.0 if i != 7 else 0.0} for i in range(9)}
            }
        }
        
        analysis = self.engine.analyze_topology(telemetry)
        
        # Bus 7 (index 7) should be isolated
        self.assertTrue(any(7 in seg for seg in analysis["isolated_segments"]))
        
        # Closing L7_8 should connect index 7 back to index 6 (Bus 7, which is energized via L2_7)
        options = [opt["line_id"] for opt in analysis["reroute_options"]]
        self.assertIn("L7_8", options)

if __name__ == "__main__":
    unittest.main()
