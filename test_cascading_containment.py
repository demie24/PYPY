import unittest
import sys
import os

# Setup import paths
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "core", "self_healing")))

from cascading_containment_engine import CascadingContainmentEngine

class TestCascadingContainment(unittest.TestCase):
    def setUp(self):
        self.engine = CascadingContainmentEngine()

    def test_empty_telemetry(self):
        res = self.engine.analyze_cascading_risk({})
        self.assertEqual(res["propagation_zones"], [])
        self.assertEqual(res["instability_spread_risk"], 0.0)
        self.assertEqual(res["isolation_boundary"], [])

    def test_overload_tracing(self):
        # Setup telemetry where line L1_4 is overloaded (> 85%)
        # Lines are defined in Topology. Lines are e.g. L1_4, L4_5, etc.
        # Let's check how Topology is defined or line IDs.
        # Let's provide breakers as all CLOSED.
        telemetry = {
            "state": {
                "breakers": {line["id"]: "CLOSED" for line in self.engine.topo_engine.topo.lines},
                "lines": {
                    line["id"]: {"capacity_pct": 20.0} for line in self.engine.topo_engine.topo.lines
                },
                "buses": {f"Bus_{i+1}": {"voltage_pu": 1.0} for i in range(9)}
            }
        }
        # Overload line L1_4
        telemetry["state"]["lines"]["L1_4"] = {"capacity_pct": 95.0}

        res = self.engine.analyze_cascading_risk(telemetry)
        
        # Risk should be greater than 0 since L1_4 is overloaded
        self.assertGreater(res["instability_spread_risk"], 0.0)

    def test_isolation_boundary_compromised_bus(self):
        # If Bus_5 is compromised or collapsed (V < 0.85), recommend opening lines connected to it.
        # Bus_5 is index 4, connected lines are L5_6, L4_5 etc.
        telemetry = {
            "state": {
                "breakers": {line["id"]: "CLOSED" for line in self.engine.topo_engine.topo.lines},
                "lines": {
                    line["id"]: {"capacity_pct": 20.0} for line in self.engine.topo_engine.topo.lines
                },
                "buses": {
                    f"Bus_{i+1}": {"voltage_pu": 1.0 if i != 4 else 0.80} for i in range(9) # Bus_5 is index 4
                }
            }
        }
        
        # Test 1: Voltage collapse at Bus_5 (V = 0.80 < 0.85)
        res = self.engine.analyze_cascading_risk(telemetry)
        self.assertTrue(len(res["isolation_boundary"]) > 0)
        
        # Test 2: Compromised node list in attack_status
        telemetry["state"]["buses"]["Bus_5"]["voltage_pu"] = 1.0
        attack_status = {
            "compromised_nodes": {"Bus_5": True}
        }
        res2 = self.engine.analyze_cascading_risk(telemetry, attack_status)
        self.assertTrue(len(res2["isolation_boundary"]) > 0)

if __name__ == "__main__":
    unittest.main()
