import unittest
import json
import time
import os
from typing import Dict, Any, List

from core.cyber_defense.threat_correlation import ThreatCorrelationEngine, Incident
from core.cyber_defense.incident_lifecycle import IncidentLifecycleManager, AUDIT_LOG_PATH
from core.cyber_defense.trust_fusion import TrustFusionEngine
from core.cyber_defense.mitre_mapper import MitreMapper
from core.cyber_defense.attribution_engine import AttributionEngine
from core.cyber_defense.defense_orchestrator import DefenseOrchestrator

class TestCyberDefenseMaturity(unittest.TestCase):
    def setUp(self):
        # Ensure clean state before each test
        if os.path.exists(AUDIT_LOG_PATH):
            os.remove(AUDIT_LOG_PATH)
            
        self.mock_telemetry = {
            "timestamp": int(time.time() * 1000),
            "state": {
                "buses": {
                    f"Bus_{i}": {"voltage_pu": 1.0} for i in range(1, 10)
                },
                "lines": {
                    lid: {"capacity_pct": 50.0} for lid in ["L1_4", "L2_7", "L3_9", "L4_5", "L4_9", "L5_6", "L6_7", "L7_8", "L8_9"]
                },
                "breakers": {
                    lid: "CLOSED" for lid in ["L1_4", "L2_7", "L3_9", "L4_5", "L4_9", "L5_6", "L6_7", "L7_8", "L8_9"]
                }
            },
            "attack_status": {
                "active_attack": False,
                "compromised_nodes": {}
            }
        }

    def tearDown(self):
        if os.path.exists(AUDIT_LOG_PATH):
            os.remove(AUDIT_LOG_PATH)

    def test_threat_correlation_engine(self):
        """Verify correlation of raw alerts, events, and validation signals into unified incidents."""
        engine = ThreatCorrelationEngine()
        
        alerts = [
            {"type": "TARGETED_FDIA", "suspect_node": "Bus_5", "severity": "HIGH", "timestamp": int(time.time() * 1000)}
        ]
        events = [
            {"event": "Breaker tripped dynamically due to fault", "source": "L4_5", "severity": "HIGH"}
        ]
        
        incidents = engine.correlate_signals(alerts, events, {}, {})
        self.assertEqual(len(incidents), 1)
        incident = incidents[0]
        self.assertEqual(incident.state, "CORRELATE")
        self.assertTrue("Bus_5" in incident.affected_assets)
        self.assertTrue("L4_5" in incident.affected_assets)
        self.assertEqual(len(incident.correlated_alerts), 1)
        self.assertEqual(len(incident.events_list), 1)

    def test_mitre_attack_mapping(self):
        """Verify mapping of cyber alerts and physical grid anomalies to MITRE ATT&CK techniques."""
        mapper = MitreMapper()
        
        alerts = [
            {"type": "TARGETED_FDIA", "suspect_node": "Bus_5"},
            {"type": "DOS_JAMMING", "suspect_node": "Bus_6"}
        ]
        events = [
            {"event": "Unauthorized breaker command compromise payload", "source": "L4_5"}
        ]
        
        techs = mapper.map_alerts_to_techniques(alerts, events)
        self.assertTrue("T0814" in techs)  # Data Injection
        self.assertTrue("T0883" in techs)  # Denial of Service
        self.assertTrue("T0812" in techs)  # Command Generation
        
        details = mapper.get_technique_details("T0814")
        self.assertEqual(details["name"], "Data Injection")

    def test_attribution_confidence_engine(self):
        """Verify research-grade confidence-based attribution of campaigns to actor profiles."""
        engine = AttributionEngine()
        
        # Test Case 1: Targeted FDIA mapping
        techs = ["T0814"]
        physics_val = {"physics_anomaly_score": 50.0}
        alerts = [{"type": "TARGETED_FDIA", "suspect_node": "Bus_5"}]
        
        res1 = engine.attribute_campaign(techs, alerts, physics_val)
        self.assertEqual(res1["threat_actor"], "APT-GRID-TAMPERER")
        self.assertTrue(res1["confidence"] > 0.50)
        self.assertTrue("High KCL Mismatch" in res1["indicators_matched"])

        # Test Case 2: DoS Jamming mapping
        techs2 = ["T0883", "T0861"]
        alerts2 = [{"type": "DOS_JAMMING", "suspect_node": "Bus_6"}]
        
        res2 = engine.attribute_campaign(techs2, alerts2, {})
        self.assertEqual(res2["threat_actor"], "APT-GRID-DISRUPTOR")
        self.assertTrue(res2["confidence"] >= 0.35)

    def test_trust_fusion_engine(self):
        """Verify unified stateful node and asset trust calculations."""
        engine = TrustFusionEngine()
        
        # Nominal state: trust remains high
        trust_summary = engine.compute_trust(self.mock_telemetry, [], {}, {})
        self.assertEqual(trust_summary["bus_trust"]["Bus_5"], 100.0)
        
        # Tampered state: inject alert and KCL validation failure
        alerts = [{"type": "TARGETED_FDIA", "suspect_node": "Bus_5"}]
        physics_val = {
            "kcl_mismatches": {"Bus_5": 25.0},
            "violations": ["Impossible breaker current flow observed on L4_5"]
        }
        
        trust_summary = engine.compute_trust(self.mock_telemetry, alerts, physics_val, {})
        
        # Bus_5 trust should degrade instantly
        self.assertTrue(trust_summary["bus_trust"]["Bus_5"] < 100.0)
        
        # Incident confidence score check
        conf = engine.calculate_incident_confidence(alerts, physics_val)
        self.assertTrue(conf > 0.40)

    def test_incident_lifecycle_manager(self):
        """Verify the stateful lifecycle progression and audit log trail generation."""
        lifecycle = IncidentLifecycleManager()
        
        incident = Incident(101, time.time())
        incident.affected_assets.add("Bus_5")
        incident.correlated_alerts.append({"type": "TARGETED_FDIA", "suspect_node": "Bus_5"})
        
        # Ticks progression check
        lifecycle.evaluate_lifecycle([incident], self.mock_telemetry, {}, {}, {})
        self.assertEqual(incident.state, "VALIDATE")
        
        # Pass degraded trust to trigger validation progression to CORRELATE
        lifecycle.evaluate_lifecycle([incident], self.mock_telemetry, {}, {"bus_trust": {"Bus_5": 50.0}}, {})
        self.assertEqual(incident.state, "CORRELATE")
        
        # Verify audit trails written
        trail = lifecycle.get_audit_trail()
        self.assertTrue(len(trail) > 0)
        self.assertEqual(trail[-1]["incident_id"], 101)

    def test_orchestrator_integration_and_stale_feeds(self):
        """Verify the global orchestrator run tick, payload schema, and stale-feed resilience fallback."""
        orchestrator = DefenseOrchestrator()
        
        # Mock MQTT client
        class MockClient:
            def __init__(self):
                self.published = []
            def publish(self, topic, payload):
                self.published.append((topic, json.loads(payload)))
                
        client = MockClient()
        
        # Trigger run tick under nominal conditions
        orchestrator.run_tick(client)
        self.assertEqual(len(client.published), 1)
        topic, payload = client.published[0]
        self.assertEqual(topic, "grid/defense")
        self.assertEqual(payload["escalation_level"], "ADVISORY")
        self.assertEqual(len(payload["active_incidents"]), 0)
        
        # Trigger stale feed check
        orchestrator.last_pinn_time = time.time() - 15.0  # 15s ago
        orchestrator.run_tick(client)
        
        # Check that bus trust score was penalized due to stale feeds
        self.assertTrue(orchestrator.trust_fusion.bus_trust["Bus_5"] < 100.0)

if __name__ == "__main__":
    unittest.main()
