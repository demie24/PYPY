import unittest
import sys
import os
import time
import json
import numpy as np

# Setup import paths
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from core.self_healing.islanding_engine import IslandingEngine
from core.self_healing.restoration_planner import RestorationPlanner
from core.self_healing.proactive_rerouting_engine import ProactiveReroutingEngine
from core.self_healing.cascading_containment_engine import CascadingContainmentEngine
from core.self_healing.recovery_state_machine import RecoveryStateMachine
from core.self_healing.reward_engine import RewardEngine
from core.self_healing.recovery_reward_engine import RecoveryRewardEngine
from core.self_healing.degraded_operation_manager import DegradedOperationManager

class TestSelfHealingMaturity(unittest.TestCase):
    def setUp(self):
        # Mock telemetry
        self.mock_telemetry = {
            "state": {
                "buses": {
                    f"Bus_{i+1}": {
                        "voltage_pu": 1.0, 
                        "frequency_hz": 60.0,
                        "is_load": i in [4, 5, 7], 
                        "is_gen": i in [0, 1, 2], 
                        "P_mw": 50.0 if i in [4, 5, 7] else (100.0 if i in [0, 1, 2] else 0.0), 
                        "Q_mvar": 10.0
                    }
                    for i in range(9)
                },
                "lines": {
                    line_id: {"capacity_pct": 30.0}
                    for line_id in ["L1_4", "L2_7", "L3_9", "L4_5", "L4_9", "L5_6", "L6_7", "L7_8", "L8_9"]
                },
                "breakers": {
                    line_id: "CLOSED"
                    for line_id in ["L1_4", "L2_7", "L3_9", "L4_5", "L4_9", "L5_6", "L6_7", "L8_9"]
                }
            }
        }
        self.mock_telemetry["state"]["breakers"]["L7_8"] = "OPEN" # normally open tie-breaker

    def test_islanding_balancing_and_shielding(self):
        """Verify generation-load balancing, critical load priorities, and boundary split safeguards."""
        engine = IslandingEngine()

        # Deficient generation scenario
        deficient_telemetry = json.loads(json.dumps(self.mock_telemetry))
        # High loads, low generation
        deficient_telemetry["state"]["buses"]["Bus_5"]["P_mw"] = 150.0
        deficient_telemetry["state"]["buses"]["Bus_1"]["P_mw"] = 30.0
        
        # Trigger compromise on Bus 9 to cause instability
        attack_status = {"compromised_nodes": {"Bus_9": "voltage"}}

        res = engine.analyze_islanding(deficient_telemetry, attack_status)
        self.assertEqual(len(res["active_islands"]), 1)
        island = res["active_islands"][0]
        
        self.assertTrue(island["is_deficient"])
        self.assertEqual(island["survival_mode"], "SURVIVAL_CRITICAL") # Bus 5 is in this island
        self.assertTrue(island["is_unstable"])
        
        # Verify Bus_5 is shielded from splitting commands (boundary cuts)
        splitting_targets = [cmd["target"] for cmd in res["splitting_commands"]]
        self.assertNotIn("L4_5", splitting_targets) # L4_5 feeds Bus_5 from Gen 1

    def test_context_aware_restoration_planning(self):
        """Verify multi-objective path scoring prioritizing critical loads and blocking unsafe restorations."""
        planner = RestorationPlanner()

        # Isolate Bus 5 (hospital) by opening L4_5 and L5_6
        isolated_telemetry = json.loads(json.dumps(self.mock_telemetry))
        isolated_telemetry["state"]["breakers"]["L4_5"] = "OPEN"
        isolated_telemetry["state"]["breakers"]["L5_6"] = "OPEN"
        isolated_telemetry["state"]["buses"]["Bus_5"]["voltage_pu"] = 0.40 # de-energized
        
        # Option 1: Restoring L4_5 connects Bus_5 (critical)
        # Option 2: Restoring L5_6 connects Bus_6 (less critical)
        
        # 1. Test scoring priorities
        seq = planner.plan_restoration(isolated_telemetry)
        self.assertTrue(len(seq) > 0)
        # First recommendation target should be L4_5 (highest critical reward +50)
        self.assertEqual(seq[0]["target"], "L4_5")

        # 2. Test Trust-based Gating Block
        low_trust = {
            "bus_trust": {
                "Bus_5": 30.0 # distrusted
            },
            "line_trust": {
                "L4_5": 100.0
            }
        }
        seq_blocked = planner.plan_restoration(isolated_telemetry, trust_scores=low_trust)
        # Should not recommend L4_5 due to Bus_5 trust < 50%
        targets = [step["target"] for step in seq_blocked]
        self.assertNotIn("L4_5", targets)

    def test_proactive_rerouting_congestion(self):
        """Verify congestion-aware path selection and rerouting confidence scores."""
        engine = ProactiveReroutingEngine()

        overloaded_telemetry = json.loads(json.dumps(self.mock_telemetry))
        overloaded_telemetry["state"]["lines"]["L1_4"]["capacity_pct"] = 95.0 # overloaded path
        
        predictive = {
            "predicted_overloads": [{"line_id": "L1_4", "predicted_time_to_trip": 10.0}]
        }

        res = engine.analyze_rerouting(overloaded_telemetry, predictive)
        self.assertTrue(res["proactive_rerouting_active"])
        self.assertEqual(res["recommended_rerouting"][0]["target"], "L7_8")
        self.assertTrue(res["rerouting_confidence"] > 0.0)

    def test_cascading_containment_scoring(self):
        """Verify cascading risk score calculations and preemptive trip recommendations."""
        engine = CascadingContainmentEngine()

        heavy_overload = json.loads(json.dumps(self.mock_telemetry))
        heavy_overload["state"]["lines"]["L1_4"]["capacity_pct"] = 125.0 # extreme overload

        res = engine.analyze_cascading_risk(heavy_overload)
        self.assertTrue(res["cascading_risk_score"] > 0.5)
        self.assertTrue(res["stabilization_first_required"])
        self.assertTrue(len(res["preemptive_trips"]) > 0)
        self.assertEqual(res["preemptive_trips"][0]["target"], "L1_4")

    def test_recovery_state_machine_staged_and_cooldown(self):
        """Verify the multi-stage recovery sequencer, critical partial phase, and switching cooldowns."""
        fsm = RecoveryStateMachine()
        
        class MockClient:
            def __init__(self):
                self.published = []
            def publish(self, topic, payload):
                self.published.append((topic, json.loads(payload)))

        client = MockClient()

        # Outage detected
        outage_telemetry = json.loads(json.dumps(self.mock_telemetry))
        outage_telemetry["state"]["breakers"]["L4_5"] = "OPEN"
        outage_telemetry["state"]["breakers"]["L5_6"] = "OPEN" # fully isolate Bus 5
        outage_telemetry["state"]["buses"]["Bus_5"]["voltage_pu"] = 0.30 # de-energized load
        
        # 1. State Machine Progression through stages
        fsm.update(outage_telemetry, client)
        self.assertEqual(fsm.state, "DETECTION")
        
        fsm.state_timer = 2
        fsm.update(outage_telemetry, client) # state timer ticks
        self.assertEqual(fsm.state, "ISOLATE")
        
        fsm.state_timer = 2
        fsm.update(outage_telemetry, client)
        self.assertEqual(fsm.state, "STABILIZE")
        
        fsm.state_timer = 3
        fsm.update(outage_telemetry, client)
        self.assertEqual(fsm.state, "REROUTE")
        
        # Reroute calculations should formulate critical vs non-critical steps
        fsm.update(outage_telemetry, client)
        self.assertEqual(fsm.state, "RESTORE")
        self.assertEqual(fsm.recovery_phase, "NONE")
        self.assertTrue(len(fsm.critical_steps) > 0)
        
        # 2. Check Switching Cooldown Block
        # Trigger progressive command
        fsm.update(outage_telemetry, client)
        self.assertEqual(fsm.recovery_phase, "PARTIAL")
        last_executed = fsm.executed_sequence[-1]["target"]
        
        # Attempt to issue another command immediately on the same target (should be cooldown-blocked)
        allowed = fsm._check_cooldown_and_allowed("CLOSE", last_executed)
        self.assertFalse(allowed)

        # 3. Check Operator Override Block
        fsm.override.trigger_emergency_stop()
        cmds = fsm.update(outage_telemetry, client)
        self.assertEqual(len(cmds), 0)

    def test_rl_reward_engine_unsafe_actions(self):
        """Verify reward shaping penalties for unsafe actions and restoration efficiency bonuses."""
        engine = RewardEngine()

        # Base nominal vectors (all breakers closed)
        nom_state = np.ones(72, dtype=np.float32)
        nom_state[0:9] = 1.0     # nominal voltages
        nom_state[18:36] = 0.2   # safe loadings
        nom_state[36:45] = 1.0   # closed breakers
        nom_state[45:63] = 1.0   # high trust
        nom_state[70] = 0.0      # no islanding

        # Case 1: Unsafe action was blocked (breakers and voltages unchanged)
        # Compute reward with action_id=2 (Reconnect Line) but state unchanged
        reward_blocked, details = engine.compute_reward(
            prev_state=nom_state,
            curr_state=nom_state,
            action_id=2,
            step_count=1
        )
        self.assertEqual(details["penalty_unsafe_action"], -25.0)

        # Case 2: Complete restoration with efficiency
        prev_islanded = nom_state.copy()
        prev_islanded[70] = 1.0 # islanded
        prev_islanded[0:9] = 0.75 # voltage collapse
        
        curr_restored = nom_state.copy() # nominal state
        
        # Step count 1 (extremely efficient)
        _, details_restored = engine.recovery_reward_engine.evaluate_restoration_quality(
            prev_state=prev_islanded,
            curr_state=curr_restored,
            action_id=2,
            rollback_occurred=False,
            step_count=1
        )
        self.assertEqual(details_restored["reward_recovery_complete"], 50.0)
        self.assertEqual(details_restored["reward_restoration_efficiency"], 16.0) # 20 - 4 * 1

    def test_degraded_operation_microgrid_formulation(self):
        """Verify partial-grid microgrid survival and load-shedding priority in DegradedOperationManager."""
        manager = DegradedOperationManager()

        # Outage with Gen 2 and Gen 3 active but Gen 1 offline
        degraded_telemetry = json.loads(json.dumps(self.mock_telemetry))
        degraded_telemetry["state"]["buses"]["Bus_1"]["voltage_pu"] = 0.0 # offline
        degraded_telemetry["state"]["buses"]["Bus_1"]["P_mw"] = 0.0
        
        # Break L4_5 and L4_9 to isolate Bus_5 (hospital) from Gen 1 completely
        degraded_telemetry["state"]["breakers"]["L1_4"] = "OPEN"
        degraded_telemetry["state"]["breakers"]["L4_5"] = "OPEN"
        degraded_telemetry["state"]["breakers"]["L4_9"] = "OPEN"
        # Close L7_8 to allow Gen 2 to feed Bus_5/Bus_8
        degraded_telemetry["state"]["breakers"]["L7_8"] = "CLOSED"

        res = manager.evaluate_grid_survival(degraded_telemetry)
        self.assertTrue(res["active_degraded_mode"])
        self.assertTrue(res["partial_grid_survival_active"])
        self.assertTrue(len(res["secured_microgrids"]) > 0)
        self.assertEqual(res["secured_microgrids"][0]["priority_load"], "Bus_5")

if __name__ == "__main__":
    unittest.main()
