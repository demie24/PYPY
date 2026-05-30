import unittest
import sys
import os
import json
from unittest.mock import MagicMock

# Adjust path to import from core/hardware and core/orchestrator
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

from core.orchestrator.ai_orchestrator import AIOrchestrator

class TestQuarantineLogic(unittest.TestCase):
    def setUp(self):
        self.orchestrator = AIOrchestrator()
        
        # Populate state_cache with a healthy nominal grid
        self.orchestrator.state_cache["telemetry"] = {
            "timestamp": 0,
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
                    f"Bus_{i}": {"voltage_pu": 1.0, "is_load": i in [5, 6, 8]} for i in range(1, 10)
                },
                "lines": {
                    f"L{i}_{j}": {"capacity_pct": 20.0} for i, j in [(1,4), (2,7), (3,9), (4,5), (4,9), (5,6), (6,7), (7,8), (8,9)]
                }
            },
            "attack_status": {"active_attack": None, "compromised_nodes": {}}
        }
        
        self.orchestrator.state_cache["physics_validation"] = {
            "physics_anomaly_score": 0.0,
            "impossible_state": False,
            "global_grid_confidence": 100.0,
            "physics_state": "NORMAL"
        }
        
        self.orchestrator.state_cache["trust_scores"] = {
            "bus_trust": {f"Bus_{i}": 100.0 for i in range(1, 10)},
            "details": {f"Bus_{i}": {"trust_score": 100.0} for i in range(1, 10)}
        }
        
        self.orchestrator.state_cache["threat"] = {
            "cascade_probability": 0.0,
            "threat_score": 0.0,
            "severity": "LOW"
        }
        
    def test_evaluate_proposed_command_with_quarantined_ports(self):
        # 1. Nominal state: commands allowed
        self.orchestrator.last_breaker_operation_time = 0.0
        allowed, msg = self.orchestrator.evaluate_proposed_command("CLOSE", "L1_4", "FLISR")
        self.assertTrue(allowed, msg)
        
        # 2. Quarantine ESP32 via attack state
        self.orchestrator.state_cache["hardware_attack_state"] = {
            "quarantined_ports": ["ESP32"]
        }
        
        # L1_4 (dependent on ESP32) should be blocked
        self.orchestrator.last_breaker_operation_time = 0.0
        allowed, msg = self.orchestrator.evaluate_proposed_command("CLOSE", "L1_4", "FLISR")
        self.assertFalse(allowed)
        self.assertIn("Dependent interface/port ESP32 is quarantined", msg)
        
        # L7_8 (dependent on PLC) should still be allowed
        self.orchestrator.last_breaker_operation_time = 0.0
        allowed, msg = self.orchestrator.evaluate_proposed_command("CLOSE", "L7_8", "FLISR")
        self.assertTrue(allowed, msg)

    def test_evaluate_proposed_command_with_propagation_quarantine(self):
        # Quarantine PLC via attack propagation
        self.orchestrator.state_cache["hardware_attack_propagation"] = {
            "nodes": [
                {"id": "PLC_Modbus_Gateway", "status": "QUARANTINED"}
            ]
        }
        
        # L7_8 (dependent on PLC) should be blocked
        self.orchestrator.last_breaker_operation_time = 0.0
        allowed, msg = self.orchestrator.evaluate_proposed_command("CLOSE", "L7_8", "FLISR")
        self.assertFalse(allowed)
        self.assertIn("Dependent interface PLC_Modbus_Gateway is quarantined", msg)
        
        # L1_4 (dependent on ESP32) should still be allowed
        self.orchestrator.last_breaker_operation_time = 0.0
        allowed, msg = self.orchestrator.evaluate_proposed_command("CLOSE", "L1_4", "FLISR")
        self.assertTrue(allowed, msg)

    def test_process_quarantine_containment_sends_trips(self):
        # Set up mock MQTT client
        mock_client = MagicMock()
        
        # Quarantine ESP32 via attack propagation
        self.orchestrator.state_cache["hardware_attack_propagation"] = {
            "nodes": [
                {"id": "ESP32_Bridge", "status": "QUARANTINED"}
            ]
        }
        
        # Call process_quarantine_containment
        self.orchestrator.process_quarantine_containment(mock_client)
        
        # Verify it published OPEN commands for closed dependent breakers (L1_4, L2_7)
        self.assertTrue(mock_client.publish.called)
        
        calls = mock_client.publish.call_args_list
        published_targets = []
        for call in calls:
            topic = call[0][0]
            payload = json.loads(call[0][1])
            if topic == "grid/control":
                self.assertEqual(payload["command"], "OPEN")
                self.assertEqual(payload["source"], "AI_ORCHESTRATOR")
                published_targets.append(payload["target"])
                
        self.assertIn("L1_4", published_targets)
        self.assertIn("L2_7", published_targets)
        self.assertNotIn("L7_8", published_targets)  # L7_8 is dependent on PLC, not ESP32

if __name__ == "__main__":
    unittest.main()
