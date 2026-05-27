import unittest
import sys
import os

# Setup import paths
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "core", "self_healing")))

from survival_optimizer import SurvivalOptimizer

class TestSurvivalOptimizer(unittest.TestCase):
    def setUp(self):
        self.optimizer = SurvivalOptimizer()

    def test_nominal_strategy_ranking(self):
        # Grid is perfectly nominal
        telemetry = {
            "state": {
                "buses": {
                    "Bus_1": {"voltage_pu": 1.0, "is_load": False, "P_mw": 0.0},
                    "Bus_2": {"voltage_pu": 1.0, "is_load": False, "P_mw": 0.0},
                    "Bus_3": {"voltage_pu": 1.0, "is_load": False, "P_mw": 0.0},
                    "Bus_5": {"voltage_pu": 1.0, "is_load": True, "P_mw": 125.0}, # nominal Bus 5 load is 125MW
                    "Bus_6": {"voltage_pu": 1.0, "is_load": True, "P_mw": 90.0},  # nominal Bus 6 load is 90MW
                    "Bus_8": {"voltage_pu": 1.0, "is_load": True, "P_mw": 100.0}  # nominal Bus 8 load is 100MW
                },
                "lines": {
                    "L1_4": {"capacity_pct": 20.0}
                }
            }
        }
        res = self.optimizer.optimize_survival(telemetry, {}, False)
        self.assertEqual(res["load_retention_pct"], 100.0)
        self.assertEqual(res["survivability_score"], 100.0)
        
        # Nominal strategy should rank 1st with score 100
        best_strat = res["strategy_ranking"][0]
        self.assertEqual(best_strat["strategy"], "NOMINAL")
        self.assertEqual(best_strat["score"], 100.0)

    def test_overload_strategy_ranking(self):
        # A line is overloaded (> 95%)
        telemetry = {
            "state": {
                "buses": {
                    "Bus_1": {"voltage_pu": 1.0, "is_load": False, "P_mw": 0.0},
                    "Bus_2": {"voltage_pu": 1.0, "is_load": False, "P_mw": 0.0},
                    "Bus_3": {"voltage_pu": 1.0, "is_load": False, "P_mw": 0.0},
                    "Bus_5": {"voltage_pu": 1.0, "is_load": True, "P_mw": 125.0},
                    "Bus_6": {"voltage_pu": 1.0, "is_load": True, "P_mw": 90.0},
                    "Bus_8": {"voltage_pu": 1.0, "is_load": True, "P_mw": 100.0}
                },
                "lines": {
                    "L1_4": {"capacity_pct": 105.0} # overload
                }
            }
        }
        res = self.optimizer.optimize_survival(telemetry, {}, False)
        # Should prefer ISLANDING or DEGRADED over NOMINAL
        best_strats = [s["strategy"] for s in res["strategy_ranking"][:2]]
        self.assertIn("ISLANDING", best_strats)
        self.assertIn("DEGRADED", best_strats)

if __name__ == "__main__":
    unittest.main()
