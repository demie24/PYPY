import unittest
import sys
import os
import json

# Setup import paths
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "core", "self_healing")))

from recovery_state_machine import RecoveryStateMachine

class MockMQTTClient:
    def __init__(self):
        self.published = []
        
    def publish(self, topic, payload):
        self.published.append({
            "topic": topic,
            "payload": json.loads(payload) if isinstance(payload, str) else payload
        })

class TestAutonomousRestoration(unittest.TestCase):
    def setUp(self):
        self.fsm = RecoveryStateMachine()
        self.client = MockMQTTClient()
        
    def test_nominal_monitoring(self):
        # Grid is completely healthy, all breakers closed, voltages 1.0 pu
        telemetry = {
            "state": {
                "breakers": {line["id"]: "CLOSED" for line in self.fsm.topo_engine.topo.lines},
                "buses": {f"Bus_{i+1}": {"voltage_pu": 1.0} for i in range(9)},
                "lines": {line["id"]: {"capacity_pct": 20.0} for line in self.fsm.topo_engine.topo.lines}
            }
        }
        
        # 1. First frame
        cmds = self.fsm.update(telemetry, self.client)
        self.assertEqual(self.fsm.state, "NORMAL")
        self.assertEqual(len(cmds), 0)

    def test_complete_recovery_cycle(self):
        # Normally open tie breaker L7_8 is OPEN.
        # Trip L8_9 to isolate Bus 7 (Load 8)
        breakers = {line["id"]: "CLOSED" for line in self.fsm.topo_engine.topo.lines}
        breakers["L7_8"] = "OPEN"
        breakers["L8_9"] = "OPEN"
        
        telemetry = {
            "state": {
                "breakers": breakers,
                "buses": {f"Bus_{i+1}": {"voltage_pu": 1.0 if i != 7 else 0.0} for i in range(9)},
                "lines": {line["id"]: {"capacity_pct": 20.0} for line in self.fsm.topo_engine.topo.lines}
            }
        }
        
        # 1. Detect isolated loads, enter ISOLATE state
        self.fsm.update(telemetry, self.client, faulted_breakers=["L8_9"])
        self.assertEqual(self.fsm.state, "ISOLATE")
        
        # 2. Wait 2 frames in ISOLATE -> transition to STABILIZE
        self.fsm.update(telemetry, self.client, faulted_breakers=["L8_9"])
        self.fsm.update(telemetry, self.client, faulted_breakers=["L8_9"])
        self.assertEqual(self.fsm.state, "STABILIZE")
        
        # 3. Wait 3 frames in STABILIZE -> transition to REROUTE
        self.fsm.update(telemetry, self.client, faulted_breakers=["L8_9"])
        self.fsm.update(telemetry, self.client, faulted_breakers=["L8_9"])
        self.fsm.update(telemetry, self.client, faulted_breakers=["L8_9"])
        self.assertEqual(self.fsm.state, "REROUTE")
        
        # 4. In REROUTE -> plan path (L7_8 close) -> transition to RESTORE
        self.fsm.update(telemetry, self.client, faulted_breakers=["L8_9"])
        self.assertEqual(self.fsm.state, "RESTORE")
        self.assertEqual(len(self.fsm.planned_sequence), 1)
        self.assertEqual(self.fsm.planned_sequence[0]["target"], "L7_8")
        
        # 5. In RESTORE -> issue command -> transition to VERIFY
        cmds = self.fsm.update(telemetry, self.client, faulted_breakers=["L8_9"])
        self.assertEqual(self.fsm.state, "RESTORE")
        self.assertEqual(len(cmds), 1)
        self.assertEqual(cmds[0]["command"], "CLOSED")
        self.assertEqual(cmds[0]["target"], "L7_8")
        
        # Second update to transition from RESTORE to VERIFY
        self.fsm.update(telemetry, self.client, faulted_breakers=["L8_9"])
        self.assertEqual(self.fsm.state, "VERIFY")
        
        # 6. In VERIFY -> grid is healthy, voltages restored -> transition back to NORMAL
        # Simulate closing L7_8 in telemetry
        telemetry["state"]["breakers"]["L7_8"] = "CLOSED"
        telemetry["state"]["buses"]["Bus_8"]["voltage_pu"] = 1.0
        
        self.fsm.update(telemetry, self.client, faulted_breakers=["L8_9"])
        self.fsm.update(telemetry, self.client, faulted_breakers=["L8_9"])
        self.fsm.update(telemetry, self.client, faulted_breakers=["L8_9"])
        self.assertEqual(self.fsm.state, "NORMAL")
        
    def test_recovery_rollback(self):
        # Set up same isolation, but during verification, voltage collapses (V < 0.88)
        breakers = {line["id"]: "CLOSED" for line in self.fsm.topo_engine.topo.lines}
        breakers["L7_8"] = "OPEN"
        breakers["L8_9"] = "OPEN"
        
        telemetry = {
            "state": {
                "breakers": breakers,
                "buses": {f"Bus_{i+1}": {"voltage_pu": 1.0 if i != 7 else 0.0} for i in range(9)},
                "lines": {line["id"]: {"capacity_pct": 20.0} for line in self.fsm.topo_engine.topo.lines}
            }
        }
        
        # Walk to VERIFY state
        self.fsm.transition_to("VERIFY")
        self.fsm.planned_sequence = [{"command": "CLOSE", "target": "L7_8", "reason": "test"}]
        self.fsm.executed_sequence = [{"command": "CLOSE", "target": "L7_8", "reason": "test"}]
        
        # Simulate voltage collapse on Bus_8 (Load 8)
        telemetry["state"]["buses"]["Bus_8"]["voltage_pu"] = 0.80
        
        # Run FSM update in VERIFY -> should detect collapse and move to ROLLBACK
        self.fsm.update(telemetry, self.client, faulted_breakers=["L8_9"])
        self.assertEqual(self.fsm.state, "ROLLBACK")
        
        # Run FSM update in ROLLBACK -> should issue OPEN control commands and lock out breaker
        self.fsm.update(telemetry, self.client, faulted_breakers=["L8_9"])
        self.assertEqual(self.fsm.state, "NORMAL")
        
        # Verify OPEN rollback command published
        published_cmds = [p for p in self.client.published if p["topic"] == "grid/control"]
        self.assertEqual(len(published_cmds), 1)
        self.assertEqual(published_cmds[0]["payload"]["command"], "OPEN")
        self.assertEqual(published_cmds[0]["payload"]["target"], "L7_8")
        
        # Verify breaker is locked out
        self.assertTrue(self.fsm.rollback_guard.is_locked_out("L7_8"))

if __name__ == "__main__":
    unittest.main()
