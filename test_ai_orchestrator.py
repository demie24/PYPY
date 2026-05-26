import os
import sys
import unittest
import json
import numpy as np

# Set pythonpath dynamically
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "core", "orchestrator"))

from decision_engine import OrchestrationDecisionEngine
from action_recommender import ActionRecommender

class TestAIOrchestrator(unittest.TestCase):
    def setUp(self):
        self.decision_engine = OrchestrationDecisionEngine()
        self.action_recommender = ActionRecommender()
        self.base_telemetry = {
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
                    "L7_8": "OPEN",
                    "L8_9": "CLOSED"
                },
                "buses": {
                    "Bus_1": {"voltage_pu": 1.0, "angle_rad": 0.0, "is_load": False, "is_gen": True, "P_mw": 0.0, "Q_mvar": 0.0},
                    "Bus_2": {"voltage_pu": 1.0, "angle_rad": 0.0, "is_load": False, "is_gen": True, "P_mw": 0.0, "Q_mvar": 0.0},
                    "Bus_3": {"voltage_pu": 1.0, "angle_rad": 0.0, "is_load": False, "is_gen": True, "P_mw": 0.0, "Q_mvar": 0.0},
                    "Bus_4": {"voltage_pu": 1.0, "angle_rad": 0.0, "is_load": False, "is_gen": False, "P_mw": 0.0, "Q_mvar": 0.0},
                    "Bus_5": {"voltage_pu": 1.0, "angle_rad": 0.0, "is_load": True, "is_gen": False, "P_mw": 125.0, "Q_mvar": 50.0},
                    "Bus_6": {"voltage_pu": 1.0, "angle_rad": 0.0, "is_load": True, "is_gen": False, "P_mw": 90.0, "Q_mvar": 30.0},
                    "Bus_7": {"voltage_pu": 1.0, "angle_rad": 0.0, "is_load": False, "is_gen": False, "P_mw": 0.0, "Q_mvar": 0.0},
                    "Bus_8": {"voltage_pu": 1.0, "angle_rad": 0.0, "is_load": True, "is_gen": False, "P_mw": 100.0, "Q_mvar": 35.0},
                    "Bus_9": {"voltage_pu": 1.0, "angle_rad": 0.0, "is_load": False, "is_gen": False, "P_mw": 0.0, "Q_mvar": 0.0}
                },
                "lines": {
                    "L1_4": {"current_pu": 0.0, "current_amp": 0.0, "P_mw": 0.0, "Q_mvar": 0.0, "capacity_pct": 40.0, "overcurrent": False},
                    "L2_7": {"current_pu": 0.0, "current_amp": 0.0, "P_mw": 0.0, "Q_mvar": 0.0, "capacity_pct": 40.0, "overcurrent": False},
                    "L3_9": {"current_pu": 0.0, "current_amp": 0.0, "P_mw": 0.0, "Q_mvar": 0.0, "capacity_pct": 40.0, "overcurrent": False},
                    "L4_5": {"current_pu": 0.0, "current_amp": 0.0, "P_mw": 0.0, "Q_mvar": 0.0, "capacity_pct": 40.0, "overcurrent": False},
                    "L4_9": {"current_pu": 0.0, "current_amp": 0.0, "P_mw": 0.0, "Q_mvar": 0.0, "capacity_pct": 40.0, "overcurrent": False},
                    "L5_6": {"current_pu": 0.0, "current_amp": 0.0, "P_mw": 0.0, "Q_mvar": 0.0, "capacity_pct": 40.0, "overcurrent": False},
                    "L6_7": {"current_pu": 0.0, "current_amp": 0.0, "P_mw": 0.0, "Q_mvar": 0.0, "capacity_pct": 40.0, "overcurrent": False},
                    "L7_8": {"current_pu": 0.0, "current_amp": 0.0, "P_mw": 0.0, "Q_mvar": 0.0, "capacity_pct": 0.0, "overcurrent": False},
                    "L8_9": {"current_pu": 0.0, "current_amp": 0.0, "P_mw": 0.0, "Q_mvar": 0.0, "capacity_pct": 40.0, "overcurrent": False}
                }
            },
            "attack_status": {"active_attack": None, "compromised_nodes": {}}
        }

    def get_mock_state(self, telemetry, threat_prob=0.0, cascade_prob=0.0, physics_anomaly=0.0, is_impossible=False, trust_degraded=False):
        trust_scores = {
            "bus_trust": {f"Bus_{i}": 100.0 for i in range(1, 10)},
            "details": {f"Bus_{i}": {"trust_score": 100.0} for i in range(1, 10)}
        }
        for line_id in ["L1_4", "L2_7", "L3_9", "L4_5", "L4_9", "L5_6", "L6_7", "L7_8", "L8_9"]:
            trust_scores["details"][line_id] = {"trust_score": 100.0}
            
        if trust_degraded:
            trust_scores["bus_trust"]["Bus_5"] = 30.0
            trust_scores["details"]["Bus_5"]["trust_score"] = 30.0
            trust_scores["details"]["L7_8"]["trust_score"] = 30.0
            
        physics_val = {
            "physics_anomaly_score": physics_anomaly,
            "impossible_state": is_impossible,
            "global_grid_confidence": 100.0 - physics_anomaly,
            "physics_state": "NORMAL" if physics_anomaly < 30.0 else "CYBER_ATTACK_INSTABILITY",
            "kcl_error": physics_anomaly * 0.5,
            "kvl_error": physics_anomaly * 0.001
        }
        
        threat_forecast = {
            "cyber_instability_probability": threat_prob,
            "status": "NORMAL" if threat_prob < 0.50 else "CYBER_ATTACK_INSTABILITY"
        }
        
        threat = {
            "cascade_probability": cascade_prob,
            "threat_score": 50.0 * cascade_prob,
            "severity": "LOW" if cascade_prob < 0.3 else "HIGH",
            "confidence": 1.0,
            "affected_nodes": [],
            "propagation_risk": "LOW",
            "recommendations": []
        }
        
        return {
            "telemetry": telemetry,
            "ai_forecast": None,
            "multi_bus_forecast": None,
            "threat_aware_forecast": threat_forecast,
            "physics_validation": physics_val,
            "trust_scores": trust_scores,
            "threat": threat,
            "flisr_state": "NORMAL",
            "flisr_auto": True
        }

    def test_nominal_grid_state(self):
        """Test 1: Verify Nominal Grid State (State: NORMAL, Risk: LOW, Actions: Empty)"""
        mock_state = self.get_mock_state(self.base_telemetry)
        report = self.decision_engine.evaluate(mock_state)
        actions = self.action_recommender.recommend(mock_state, report)
        
        self.assertEqual(report["global_state"], "NORMAL")
        self.assertEqual(report["global_risk_level"], "LOW")
        self.assertGreaterEqual(report["stability_score"], 90.0)
        self.assertEqual(len(actions), 0)

    def test_cyber_attack_state_transition(self):
        """Test 2: Verify Cyber-Attack State Transition (FDIA or High Probability threat forecast)"""
        tel = json.loads(json.dumps(self.base_telemetry))
        tel["attack_status"] = {
            "active_attack": "FDIA",
            "compromised_nodes": {"Bus_5": "voltage"}
        }
        
        mock_state = self.get_mock_state(tel, threat_prob=0.85, cascade_prob=0.0, physics_anomaly=0.0)
        
        # Execute 3 evaluation steps to transition due to state transition hysteresis
        for _ in range(3):
            report = self.decision_engine.evaluate(mock_state)
            
        actions = self.action_recommender.recommend(mock_state, report)
        
        self.assertEqual(report["global_state"], "CYBER_ATTACK")
        self.assertEqual(report["global_risk_level"], "HIGH")

    def test_cascade_risk_state(self):
        """Test 3: Verify Cascade Risk State & Transmission Overload Advisory Actions"""
        tel = json.loads(json.dumps(self.base_telemetry))
        tel["state"]["lines"]["L5_6"]["capacity_pct"] = 160.0
        tel["state"]["lines"]["L4_5"]["capacity_pct"] = 160.0
        
        mock_state = self.get_mock_state(tel, threat_prob=0.0, cascade_prob=0.60, physics_anomaly=0.0)
        
        # Execute 3 evaluation steps for hysteresis
        for _ in range(3):
            report = self.decision_engine.evaluate(mock_state)
            
        actions = self.action_recommender.recommend(mock_state, report)
        
        self.assertEqual(report["global_state"], "CASCADE_RISK")
        self.assertTrue(any(act["action"] == "ISOLATE_LINE" and act["target"] == "L5_6" for act in actions))

    def test_emergency_mode_state(self):
        """Test 4: Verify Emergency Mode State & Operator Escalation (Low Stability)"""
        tel = json.loads(json.dumps(self.base_telemetry))
        tel["state"]["breakers"]["L1_4"] = "OPEN"
        tel["state"]["breakers"]["L3_6"] = "OPEN"
        tel["state"]["breakers"]["L5_6"] = "OPEN"
        tel["state"]["breakers"]["L8_9"] = "OPEN"
        
        for bus_id in ["Bus_5", "Bus_6", "Bus_8"]:
            tel["state"]["buses"][bus_id]["voltage_pu"] = 0.20
            
        mock_state = self.get_mock_state(tel, threat_prob=0.0, cascade_prob=0.0, physics_anomaly=75.0)
        
        # Execute 3 evaluation steps for hysteresis
        for _ in range(3):
            report = self.decision_engine.evaluate(mock_state)
            
        actions = self.action_recommender.recommend(mock_state, report)
        
        self.assertEqual(report["global_state"], "EMERGENCY_MODE")
        self.assertEqual(report["global_risk_level"], "CRITICAL")
        self.assertTrue(any(act["action"] == "OPERATOR_ESCALATION" for act in actions))

    def test_nan_inf_safety(self):
        """Test 5: Verify NaN/Inf safety across all published output states"""
        # Run nominal
        mock_state = self.get_mock_state(self.base_telemetry)
        report = self.decision_engine.evaluate(mock_state)
        actions = self.action_recommender.recommend(mock_state, report)
        
        rep_str = json.dumps(report)
        act_str = json.dumps(actions)
        
        self.assertNotIn("nan", rep_str.lower())
        self.assertNotIn("inf", rep_str.lower())
        self.assertNotIn("nan", act_str.lower())
        self.assertNotIn("inf", act_str.lower())

if __name__ == "__main__":
    unittest.main()
