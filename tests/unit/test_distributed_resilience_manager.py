import unittest
import sys
import os

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

from core.hardware.distributed_resilience_manager import DistributedResilienceManager

class TestDistributedResilienceManager(unittest.TestCase):
    def setUp(self):
        self.manager = DistributedResilienceManager()

    def test_initial_state(self):
        self.assertEqual(self.manager.survivability_score, 100.0)
        self.assertEqual(self.manager.resilience_state, "NOMINAL")
        self.assertFalse(self.manager.containment_active)
        self.assertEqual(self.manager.escalation_level, 0)
        self.assertEqual(self.manager.alerts, [])

    def test_evaluate_resilience_nominal(self):
        state_mgr = {
            "relays": {
                "L1_4": {"feedback": "CLOSED"},
                "L4_5": {"feedback": "CLOSED"}
            },
            "sensors": {
                "line_1_i": 0.5,
                "line_2_i": 0.8
            }
        }
        fleet_state = {
            "fleet": {
                "esp32_zone1": {"status": "ONLINE"}
            }
        }
        
        score, state = self.manager.evaluate_resilience(
            state_manager_state=state_mgr,
            fleet_state=fleet_state,
            alerts_list=[],
            timing_drift_detected=False,
            congestion_active=False
        )
        
        self.assertEqual(score, 100.0)
        self.assertEqual(state, "NOMINAL")
        self.assertEqual(self.manager.escalation_level, 0)
        self.assertFalse(self.manager.containment_active)

    def test_evaluate_resilience_degradations(self):
        # 1. Tripped breaker (-10 points)
        # 2. Quarantined device (-15 points)
        # 3. Overloaded line (-15 points)
        # 4. Clock drift (-10 points)
        # Total deduction: 50 points -> Score: 50.0 (CRITICAL, level 2)
        state_mgr = {
            "relays": {
                "L1_4": {"feedback": "CLOSED"},
                "L4_5": {"feedback": "OPEN"}  # Tripped
            },
            "sensors": {
                "line_1_i": 1.5,  # Overloaded (> 1.0)
                "line_2_i": 0.2
            }
        }
        fleet_state = {
            "fleet": {
                "esp32_zone1": {"status": "QUARANTINED"}  # Quarantined
            }
        }

        score, state = self.manager.evaluate_resilience(
            state_manager_state=state_mgr,
            fleet_state=fleet_state,
            alerts_list=[],
            timing_drift_detected=True,  # Drift
            congestion_active=False
        )

        self.assertEqual(score, 50.0)
        self.assertEqual(state, "CRITICAL")
        self.assertEqual(self.manager.escalation_level, 2)
        # Containment is engaged when there are overloaded lines and tripped breakers
        self.assertTrue(self.manager.containment_active)
        self.assertEqual(len(self.manager.alerts), 5)  # Breaker, Quarantined, Overload, Drift, Containment

    def test_emergency_state(self):
        # Heavy degradation to trigger EMERGENCY state (< 40.0)
        state_mgr = {
            "relays": {
                "L1_4": {"feedback": "OPEN"},
                "L4_5": {"feedback": "OPEN"},
                "L5_6": {"feedback": "OPEN"},
                "L2_7": {"feedback": "OPEN"}
            },
            "sensors": {}
        }
        fleet_state = {
            "fleet": {
                "esp32_zone1": {"status": "QUARANTINED"},
                "esp32_zone2": {"status": "QUARANTINED"}
            }
        }

        score, state = self.manager.evaluate_resilience(
            state_manager_state=state_mgr,
            fleet_state=fleet_state,
            alerts_list=[],
            timing_drift_detected=True,
            congestion_active=True
        )

        self.assertLess(score, 40.0)
        self.assertEqual(state, "EMERGENCY")
        self.assertEqual(self.manager.escalation_level, 3)

    def test_get_telemetry_payload(self):
        self.manager.survivability_score = 85.5
        self.manager.resilience_state = "DEGRADED"
        self.manager.containment_active = False
        self.manager.escalation_level = 1
        self.manager.alerts = ["DEGRADED_TEST"]
        
        payload = self.manager.get_telemetry_payload()
        
        self.assertIn("timestamp", payload)
        self.assertEqual(payload["survivability_score"], 85.5)
        self.assertEqual(payload["resilience_state"], "DEGRADED")
        self.assertEqual(payload["containment_active"], False)
        self.assertEqual(payload["escalation_level"], 1)
        self.assertEqual(payload["alerts"], ["DEGRADED_TEST"])

if __name__ == "__main__":
    unittest.main()
