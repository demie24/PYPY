import unittest
import sys
import os

# Setup import paths
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "core", "self_healing")))

from predictive_stability_engine import PredictiveStabilityEngine

class TestPredictiveStability(unittest.TestCase):
    def setUp(self):
        self.engine = PredictiveStabilityEngine(history_len=5)

    def test_insufficient_history(self):
        telemetry = {
            "state": {
                "buses": {"Bus_5": {"voltage_pu": 1.0, "frequency_hz": 60.0}},
                "lines": {"L1_2": {"capacity_pct": 50.0}}
            }
        }
        res = self.engine.evaluate_predictive_stability(telemetry)
        self.assertEqual(res["collapse_probability"], 0.0)
        self.assertEqual(res["survivability_horizon"], 999.0)
        self.assertEqual(res["predicted_overloads"], [])
        self.assertEqual(res["propagation_trajectory"], [])

    def test_nominal_stability(self):
        telemetry1 = {
            "state": {
                "buses": {"Bus_5": {"voltage_pu": 1.0, "frequency_hz": 60.0}},
                "lines": {"L1_2": {"capacity_pct": 50.0}}
            }
        }
        telemetry2 = {
            "state": {
                "buses": {"Bus_5": {"voltage_pu": 1.0, "frequency_hz": 60.0}},
                "lines": {"L1_2": {"capacity_pct": 50.0}}
            }
        }
        self.engine.update_history(telemetry1)
        res = self.engine.evaluate_predictive_stability(telemetry2)
        self.assertEqual(res["collapse_probability"], 0.0)
        self.assertEqual(res["survivability_horizon"], 999.0)
        self.assertEqual(res["predicted_overloads"], [])

    def test_decaying_metrics(self):
        # Frame 1: Nominal
        telemetry1 = {
            "state": {
                "buses": {
                    "Bus_5": {"voltage_pu": 1.0, "frequency_hz": 60.0},
                    "Bus_6": {"voltage_pu": 1.0, "frequency_hz": 60.0}
                },
                "lines": {
                    "L1_2": {"capacity_pct": 70.0}
                }
            }
        }
        # Frame 2: Stress / Decay
        telemetry2 = {
            "state": {
                "buses": {
                    "Bus_5": {"voltage_pu": 0.94, "frequency_hz": 60.0},
                    "Bus_6": {"voltage_pu": 1.0, "frequency_hz": 60.0}
                },
                "lines": {
                    "L1_2": {"capacity_pct": 95.0}
                }
            }
        }
        self.engine.update_history(telemetry1)
        res = self.engine.evaluate_predictive_stability(telemetry2)
        
        # Verify collapse probability is high
        self.assertGreater(res["collapse_probability"], 50.0)
        # Verify survivability horizon is small (minimum of voltage decay time and line overload time)
        # voltage decay rate: dv/dt = -0.06. Margin: 0.94 - 0.85 = 0.09. Time: 1.5s
        # line overload rate: dc/dt = 25.0. Margin: 110 - 95 = 15. Time: 0.6s
        # Survivability horizon should be 0.6s
        self.assertEqual(res["survivability_horizon"], 0.6)
        self.assertEqual(len(res["predicted_overloads"]), 1)
        self.assertEqual(res["predicted_overloads"][0]["line_id"], "L1_2")
        self.assertIn("L1_2", res["propagation_trajectory"])
        self.assertIn("Bus_5", res["propagation_trajectory"])

if __name__ == "__main__":
    unittest.main()
