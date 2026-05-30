import unittest
import sys
import os

# Setup import paths

from core.self_healing.recovery_scoring_engine import RecoveryScoringEngine

class TestRecoveryScoring(unittest.TestCase):
    def setUp(self):
        self.scorer = RecoveryScoringEngine()

    def test_nominal_score(self):
        # Nominal telemetry, healthy system, no sequences
        telemetry = {"state": {"buses": {}, "lines": {}, "breakers": {}}}
        sequence = []
        sandbox_results = {
            "predicted_voltages": [1.0] * 9,
            "predicted_loadings": {"L1_4": 0.20, "L2_5": 0.30},
            "cascade_risk": 0.0
        }
        res = self.scorer.score_plan(
            telemetry=telemetry,
            sequence=sequence,
            sandbox_results=sandbox_results,
            predicted_instability_prob=0.0,
            historical_success_rate=1.0
        )
        self.assertEqual(res["optimization_score"], 100.0)
        self.assertEqual(res["voltage_stability_score"], 100.0)
        self.assertEqual(res["thermal_loading_score"], 100.0)
        self.assertEqual(res["restoration_speed_score"], 100.0)

    def test_deviant_voltages(self):
        # Test penalty for voltage deviation
        telemetry = {"state": {}}
        sequence = []
        # Bus voltages deviate slightly (e.g. 0.90 pu)
        sandbox_results = {
            "predicted_voltages": [0.90] * 9,
            "predicted_loadings": {},
            "cascade_risk": 0.0
        }
        res = self.scorer.score_plan(
            telemetry=telemetry,
            sequence=sequence,
            sandbox_results=sandbox_results,
            predicted_instability_prob=0.0,
            historical_success_rate=1.0
        )
        self.assertLess(res["voltage_stability_score"], 100.0)
        self.assertLess(res["optimization_score"], 100.0)

    def test_thermal_loading_overload(self):
        # Thermal loading exceeding 80%
        telemetry = {"state": {}}
        sequence = []
        sandbox_results = {
            "predicted_voltages": [1.0] * 9,
            "predicted_loadings": {"L1_4": 0.90}, # 90% loading
            "cascade_risk": 0.0
        }
        res = self.scorer.score_plan(
            telemetry=telemetry,
            sequence=sequence,
            sandbox_results=sandbox_results,
            predicted_instability_prob=0.0,
            historical_success_rate=1.0
        )
        self.assertLess(res["thermal_loading_score"], 100.0)
        self.assertEqual(res["thermal_loading_score"], 75.0) # 100 - (90 - 80)*2.5 = 75.0

    def test_speed_and_switching_penalties(self):
        # Longer plan should reduce speed and switching scores
        telemetry = {"state": {}}
        sequence = [
            {"command": "CLOSED", "target": "L7_8"},
            {"command": "CLOSED", "target": "L4_5"}
        ]
        sandbox_results = {
            "predicted_voltages": [1.0] * 9,
            "predicted_loadings": {},
            "cascade_risk": 0.0
        }
        res = self.scorer.score_plan(
            telemetry=telemetry,
            sequence=sequence,
            sandbox_results=sandbox_results,
            predicted_instability_prob=0.0,
            historical_success_rate=1.0
        )
        self.assertEqual(res["restoration_speed_score"], 85.0) # 100 - 15 * (2 - 1) = 85.0
        self.assertEqual(res["switching_operations_score"], 80.0) # 100 - 10 * 2 = 80.0

if __name__ == "__main__":
    unittest.main()
