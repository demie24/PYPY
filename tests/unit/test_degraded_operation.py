import unittest
import sys
import os

# Setup import paths

from core.self_healing.degraded_operation_manager import DegradedOperationManager

class TestDegradedOperation(unittest.TestCase):
    def setUp(self):
        self.manager = DegradedOperationManager()

    def test_nominal_grid(self):
        # All generators healthy, all loads powered, no overloads
        telemetry = {
            "state": {
                "buses": {
                    "Bus_1": {"voltage_pu": 1.0, "P_mw": 72.0},
                    "Bus_2": {"voltage_pu": 1.0, "P_mw": 163.0},
                    "Bus_3": {"voltage_pu": 1.0, "P_mw": 85.0},
                    "Bus_5": {"voltage_pu": 1.0, "P_mw": 125.0},
                    "Bus_8": {"voltage_pu": 1.0, "P_mw": 100.0},
                    "Bus_6": {"voltage_pu": 1.0, "P_mw": 90.0}
                },
                "lines": {
                    "L1_4": {"capacity_pct": 30.0}
                },
                "breakers": {}
            }
        }
        res = self.manager.evaluate_grid_survival(telemetry)
        self.assertFalse(res["active_degraded_mode"])
        self.assertFalse(res["load_shedding_active"])
        self.assertEqual(len(res["critical_buses_secured"]), 3)

    def test_generator_trip_and_deficit_shedding(self):
        # Trip generator Bus_2 (163MW tripped) -> Gen capacity = 72 + 85 = 157MW.
        # Demand is 125 + 100 + 90 = 315MW. Deficit is 158MW.
        # This will require load shedding.
        telemetry = {
            "state": {
                "buses": {
                    "Bus_1": {"voltage_pu": 1.0, "P_mw": 72.0},
                    "Bus_2": {"voltage_pu": 0.0, "P_mw": 0.0}, # generator offline
                    "Bus_3": {"voltage_pu": 1.0, "P_mw": 85.0},
                    "Bus_5": {"voltage_pu": 1.0, "P_mw": 125.0},
                    "Bus_8": {"voltage_pu": 1.0, "P_mw": 100.0},
                    "Bus_6": {"voltage_pu": 1.0, "P_mw": 90.0}
                },
                "lines": {
                    "L1_4": {"capacity_pct": 30.0}
                },
                "breakers": {}
            }
        }
        res = self.manager.evaluate_grid_survival(telemetry)
        self.assertTrue(res["active_degraded_mode"])
        self.assertTrue(res["load_shedding_active"])
        
        # Load priority reverse order: Bus_6 (Low priority, shed first), then Bus_8 (medium), then Bus_5 (high)
        # Total load demand is 315MW, total generation is 157MW. Deficit is 158MW.
        # Shed Bus_6 (90MW) -> remaining deficit 68MW
        # Shed Bus_8 (100MW) -> remaining deficit 0MW (68MW shed, i.e. 68% of 100MW)
        # Verify Bus_6 is shed 100%
        self.assertEqual(res["load_shed_summary"]["Bus_6"], 100.0)
        # Verify Bus_8 is shed partly (approx 68%)
        self.assertAlmostEqual(res["load_shed_summary"]["Bus_8"], 68.0, delta=1.0)
        # Verify Bus_5 is NOT shed
        self.assertNotIn("Bus_5", res["load_shed_summary"])

if __name__ == "__main__":
    unittest.main()
