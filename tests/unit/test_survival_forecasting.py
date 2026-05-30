import unittest
import sys
import os

# Setup import paths

from core.self_healing.survival_forecasting_engine import SurvivalForecastingEngine

class TestSurvivalForecasting(unittest.TestCase):
    def setUp(self):
        self.engine = SurvivalForecastingEngine()

    def test_no_telemetry(self):
        res = self.engine.forecast_survival(None, {}, False)
        self.assertEqual(len(res["do_nothing_curve"]), 10)
        self.assertEqual(len(res["mitigated_curve"]), 10)
        self.assertEqual(res["recovery_success_prob"], 100.0)
        self.assertEqual(res["degraded_operation_duration"], 999.0)

    def test_nominal_grid(self):
        telemetry = {
            "state": {
                "buses": {
                    "Bus_5": {"voltage_pu": 1.0},
                    "Bus_6": {"voltage_pu": 1.0}
                },
                "lines": {
                    "L1_4": {"capacity_pct": 50.0}
                }
            }
        }
        res = self.engine.forecast_survival(telemetry, {"collapse_probability": 0.0, "survivability_horizon": 999.0}, False)
        self.assertEqual(res["do_nothing_curve"][0], 100.0)
        self.assertEqual(res["mitigated_curve"][0], 100.0)
        self.assertEqual(res["recovery_success_prob"], 95.0)
        self.assertEqual(res["degraded_operation_duration"], 999.0)

    def test_stressed_decay_forecasting(self):
        # Stress setup: Bus_5 low voltage, L1_4 heavily overloaded
        telemetry = {
            "state": {
                "buses": {
                    "Bus_5": {"voltage_pu": 0.90}, # deviation 0.1
                    "Bus_6": {"voltage_pu": 1.0}
                },
                "lines": {
                    "L1_4": {"capacity_pct": 120.0} # overload 20%
                }
            }
        }
        # Expected current score calculations:
        # Base: 100
        # v_devs = abs(1.0 - 0.9) = 0.1. Deduction: 0.1 * 100 = 10
        # capacity loading max_load = 120.0. Deduction: (120 - 100) * 2 = 40.
        # Current score: 100 - 10 - 40 = 50.0.
        
        predictive_stability = {
            "collapse_probability": 85.0,
            "survivability_horizon": 5.0
        }
        
        # Scenario 1: Do nothing (proactive_active = False)
        res_do_nothing = self.engine.forecast_survival(telemetry, predictive_stability, False)
        
        # Horizon is 5.0. Steps 1 to 4 should decay. Step 5 and beyond should be 0.0.
        self.assertLess(res_do_nothing["do_nothing_curve"][0], 50.0)
        self.assertEqual(res_do_nothing["do_nothing_curve"][4], 0.0)
        self.assertEqual(res_do_nothing["do_nothing_curve"][9], 0.0)
        
        # Success probability for collapse_prob > 80 without proactive action is 30.0%
        self.assertEqual(res_do_nothing["recovery_success_prob"], 30.0)
        self.assertEqual(res_do_nothing["degraded_operation_duration"], 5.0)

        # Scenario 2: Proactive active (proactive_active = True)
        res_mitigated = self.engine.forecast_survival(telemetry, predictive_stability, True)
        
        # Score should increase step-by-step up to max 95.0
        self.assertGreater(res_mitigated["mitigated_curve"][9], res_mitigated["mitigated_curve"][0])
        # Success probability with proactive action is 75.0%
        self.assertEqual(res_mitigated["recovery_success_prob"], 75.0)

if __name__ == "__main__":
    unittest.main()
