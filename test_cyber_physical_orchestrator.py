"""
test_cyber_physical_orchestrator.py
Phase 7.3 — Cyber-Physical Attack Orchestrator Integration Tests

Tests coordinated campaign logic, propagation chain state transitions,
quarantine escalation, and full attack lifecycle execution.
"""
import sys
import time
import unittest

sys.path.insert(0, "core/hardware")

from digispark_attack_engine import DigisparkAttackEngine
from badusb_payload_manager import BadUSBPayloadManager
from rogue_device_monitor import RogueDeviceMonitor
from hardware_intrusion_detector import HardwareIntrusionDetector
from cyber_physical_attack_orchestrator import CyberPhysicalAttackOrchestrator


def make_orchestrator():
    """Factory that creates a fresh CyberPhysicalAttackOrchestrator with its dependencies."""
    digi = DigisparkAttackEngine()
    badusb = BadUSBPayloadManager()
    rogue = RogueDeviceMonitor()
    intrusion = HardwareIntrusionDetector()
    return CyberPhysicalAttackOrchestrator(digi, badusb, rogue, intrusion), digi, badusb, rogue, intrusion


class TestCampaignLifecycle(unittest.TestCase):
    """Tests the coordinated campaign state machine across all three campaigns."""

    def test_coordinated_blackout_starts(self):
        """Launching coordinated_blackout sets active_campaign and step=1."""
        orch, _, _, _, _ = make_orchestrator()
        result = orch.start_campaign("coordinated_blackout")
        self.assertTrue(result)
        self.assertEqual(orch.active_campaign, "coordinated_blackout")
        self.assertEqual(orch.campaign_step, 1)

    def test_stealthy_drift_starts(self):
        result, _, _, _, _ = make_orchestrator()[0].start_campaign("stealthy_calibration_drift"), None, None, None, None
        self.assertTrue(result)

    def test_reconnect_flood_starts(self):
        orch, _, _, _, _ = make_orchestrator()
        result = orch.start_campaign("reconnect_flood_dos")
        self.assertTrue(result)
        self.assertEqual(orch.active_campaign, "reconnect_flood_dos")

    def test_invalid_campaign_rejected(self):
        orch, _, _, _, _ = make_orchestrator()
        result = orch.start_campaign("unknown_campaign_xyz")
        self.assertFalse(result)
        self.assertIsNone(orch.active_campaign)

    def test_blackout_step_1_inserts_rogue_device(self):
        """Step 1 of coordinated_blackout inserts a rogue USB device."""
        orch, _, _, rogue, _ = make_orchestrator()
        orch.start_campaign("coordinated_blackout")
        # Advance past the 2-second tick guard
        orch.campaign_last_tick = 0.0
        orch.tick_campaign()
        # Rogue device should now be in the devices list (trusted=False)
        rogue_devices = [d for d in rogue.connected_devices if not d["trusted"]]
        self.assertGreater(len(rogue_devices), 0, "Expected at least one rogue device after Step 1")

    def test_blackout_step_2_triggers_digispark(self):
        """Step 2 triggers a Digispark keystroke attack."""
        orch, digi, _, _, _ = make_orchestrator()
        orch.start_campaign("coordinated_blackout")
        # Force through step 1 and 2
        orch.campaign_step = 2
        orch.campaign_last_tick = 0.0
        orch.tick_campaign()
        # Digispark should now be ARMED or EXECUTING (not IDLE)
        self.assertNotEqual(digi.attack_state, "IDLE",
            f"Expected Digispark to be armed after step 2, got: {digi.attack_state}")

    def test_campaign_status_idle_when_no_campaign(self):
        """get_campaign_status returns IDLE label when no active campaign."""
        orch, _, _, _, _ = make_orchestrator()
        status = orch.get_campaign_status()
        self.assertIsNone(status["active_campaign"])
        self.assertEqual(status["phase_label"], "IDLE")

    def test_campaign_status_shows_step_when_active(self):
        """get_campaign_status returns step label when campaign active."""
        orch, _, _, _, _ = make_orchestrator()
        orch.start_campaign("coordinated_blackout")
        status = orch.get_campaign_status()
        self.assertEqual(status["active_campaign"], "coordinated_blackout")
        self.assertIn("Step", status["phase_label"])


class TestPropagationChain(unittest.TestCase):
    """Tests the dynamic propagation chain node/link status computation."""

    def test_nominal_propagation_all_nominal(self):
        """In nominal state all nodes are NOMINAL and links are ACTIVE."""
        orch, _, _, _, _ = make_orchestrator()
        chain = orch.get_propagation_chain()
        self.assertIn("nodes", chain)
        self.assertIn("links", chain)
        for node in chain["nodes"]:
            self.assertEqual(node["status"], "NOMINAL",
                f"Node {node['id']} should be NOMINAL but got {node['status']}")
        for link in chain["links"]:
            self.assertEqual(link["status"], "ACTIVE",
                f"Link {link['source']}->{link['target']} should be ACTIVE")

    def test_low_trust_compromises_usb_node(self):
        """When hardware_trust_score < 1.0, USB_Port_7 should be COMPROMISED."""
        orch, _, _, rogue, _ = make_orchestrator()
        rogue.hardware_trust_score = 0.60  # Below 1.0 but above 0.40
        chain = orch.get_propagation_chain()
        usb_node = next(n for n in chain["nodes"] if n["id"] == "USB_Port_7")
        self.assertEqual(usb_node["status"], "COMPROMISED")

    def test_high_intrusion_score_compromises_relay(self):
        """Intrusion score >= 70 should mark Breaker_Relays as COMPROMISED."""
        orch, _, _, _, intrusion = make_orchestrator()
        intrusion.intrusion_score = 75.0
        chain = orch.get_propagation_chain()
        relay_node = next(n for n in chain["nodes"] if n["id"] == "Breaker_Relays")
        self.assertEqual(relay_node["status"], "COMPROMISED")

    def test_quarantine_blocks_link_and_marks_node(self):
        """Quarantining Port 7 marks USB_Port_7 as QUARANTINED and link as BLOCKED."""
        orch, _, _, _, _ = make_orchestrator()
        orch.execute_quarantine("Port 7")
        chain = orch.get_propagation_chain()
        usb_node = next(n for n in chain["nodes"] if n["id"] == "USB_Port_7")
        self.assertEqual(usb_node["status"], "QUARANTINED")
        first_link = chain["links"][0]
        self.assertEqual(first_link["status"], "BLOCKED")

    def test_chain_has_correct_structure(self):
        """Propagation chain has exactly 4 nodes and 3 links."""
        orch, _, _, _, _ = make_orchestrator()
        chain = orch.get_propagation_chain()
        self.assertEqual(len(chain["nodes"]), 4)
        self.assertEqual(len(chain["links"]), 3)
        self.assertIn("timestamp", chain)


class TestEscalationStateMachine(unittest.TestCase):
    """Tests the evaluate_escalation_state state machine transitions."""

    def test_nominal_state_default(self):
        """Default state is NOMINAL when everything is clean."""
        orch, _, _, _, _ = make_orchestrator()
        orch.evaluate_escalation_state()
        self.assertEqual(orch.attack_escalation_state, "NOMINAL")

    def test_intrusion_detected_on_low_trust(self):
        """Trust below 1.0 with moderate intrusion triggers INTRUSION_DETECTED."""
        orch, _, _, rogue, intrusion = make_orchestrator()
        rogue.hardware_trust_score = 0.70
        intrusion.intrusion_score = 30.0
        orch.evaluate_escalation_state()
        self.assertIn(orch.attack_escalation_state, ["INTRUSION_DETECTED", "COMPROMISED"])

    def test_active_hid_injection_state(self):
        """Digispark in ARMED state triggers ACTIVE_HID_INJECTION."""
        orch, digi, badusb, _, _ = make_orchestrator()
        script = badusb.get_payload_script("recon_discovery")
        digi.trigger_attack("keystroke_bypass", steps=script)
        # Now digi.attack_state is ARMED
        self.assertEqual(digi.attack_state, "ARMED")
        orch.evaluate_escalation_state()
        self.assertEqual(orch.attack_escalation_state, "ACTIVE_HID_INJECTION")

    def test_compromised_state_on_critical_scores(self):
        """Trust below 0.40 triggers COMPROMISED state."""
        orch, _, _, rogue, _ = make_orchestrator()
        rogue.hardware_trust_score = 0.30
        orch.evaluate_escalation_state()
        self.assertIn(orch.attack_escalation_state, ["PORT_QUARANTINED", "COMPROMISED"])

    def test_autonomous_quarantine_triggered_on_critical_trust(self):
        """Autonomous quarantine fires when trust ≤ 0.40."""
        orch, _, _, rogue, _ = make_orchestrator()
        rogue.hardware_trust_score = 0.35
        orch.evaluate_escalation_state()
        self.assertIn("Port 7", orch.quarantined_ports)

    def test_port_quarantined_state(self):
        """Manually quarantining a port moves state to PORT_QUARANTINED."""
        orch, _, _, _, _ = make_orchestrator()
        orch.execute_quarantine("Port 7")
        orch.evaluate_escalation_state()
        self.assertEqual(orch.attack_escalation_state, "PORT_QUARANTINED")


class TestQuarantineManagement(unittest.TestCase):
    """Tests quarantine management API."""

    def test_quarantine_port_adds_to_list(self):
        orch, _, _, _, _ = make_orchestrator()
        result = orch.execute_quarantine("ESP32")
        self.assertTrue(result)
        self.assertIn("ESP32", orch.quarantined_ports)

    def test_double_quarantine_returns_false(self):
        orch, _, _, _, _ = make_orchestrator()
        orch.execute_quarantine("ESP32")
        result = orch.execute_quarantine("ESP32")
        self.assertFalse(result)

    def test_release_quarantine_removes_port(self):
        orch, _, _, _, _ = make_orchestrator()
        orch.execute_quarantine("ESP32")
        result = orch.remove_quarantine("ESP32")
        self.assertTrue(result)
        self.assertNotIn("ESP32", orch.quarantined_ports)

    def test_release_non_quarantined_returns_false(self):
        orch, _, _, _, _ = make_orchestrator()
        result = orch.remove_quarantine("ESP32")
        self.assertFalse(result)


class TestOrchestrationPayload(unittest.TestCase):
    """Tests orchestration payload structure and content."""

    def test_payload_has_required_keys(self):
        orch, _, _, _, _ = make_orchestrator()
        payload = orch.get_orchestration_payload()
        required_keys = [
            "timestamp", "attack_escalation_state", "quarantined_ports",
            "hardware_trust", "intrusion_score", "digispark_state", "campaign"
        ]
        for key in required_keys:
            self.assertIn(key, payload, f"Missing key: {key}")

    def test_payload_values_are_valid_types(self):
        orch, _, _, _, _ = make_orchestrator()
        payload = orch.get_orchestration_payload()
        self.assertIsInstance(payload["timestamp"], int)
        self.assertIsInstance(payload["hardware_trust"], float)
        self.assertIsInstance(payload["intrusion_score"], float)
        self.assertIsInstance(payload["quarantined_ports"], list)
        self.assertIsInstance(payload["campaign"], dict)

    def test_payload_trust_clamped_to_range(self):
        orch, _, _, rogue, _ = make_orchestrator()
        rogue.hardware_trust_score = 0.55
        payload = orch.get_orchestration_payload()
        self.assertGreaterEqual(payload["hardware_trust"], 0.0)
        self.assertLessEqual(payload["hardware_trust"], 1.0)


class TestReset(unittest.TestCase):
    """Tests that reset() fully clears all attack orchestrator state."""

    def test_reset_clears_campaign(self):
        orch, _, _, _, _ = make_orchestrator()
        orch.start_campaign("coordinated_blackout")
        orch.reset()
        self.assertIsNone(orch.active_campaign)
        self.assertEqual(orch.campaign_step, 0)

    def test_reset_clears_quarantine(self):
        orch, _, _, _, _ = make_orchestrator()
        orch.execute_quarantine("Port 7")
        orch.reset()
        self.assertEqual(len(orch.quarantined_ports), 0)

    def test_reset_returns_nominal_state(self):
        orch, _, _, rogue, intrusion = make_orchestrator()
        rogue.hardware_trust_score = 0.10
        intrusion.intrusion_score = 90.0
        orch.evaluate_escalation_state()
        orch.reset()
        self.assertEqual(orch.attack_escalation_state, "NOMINAL")


if __name__ == "__main__":
    unittest.main(verbosity=2)
