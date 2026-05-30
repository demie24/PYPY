import unittest
import sys
import os

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

from core.hardware.deployment_profiles import DeploymentProfiles

class TestDeploymentProfiles(unittest.TestCase):
    def setUp(self):
        self.profiles = DeploymentProfiles()

    def test_profile_retrieval(self):
        profile = self.profiles.get_profile("esp32_zone1")
        self.assertIsNotNone(profile)
        self.assertEqual(profile["device_type"], "microcontroller")
        self.assertEqual(profile["interface"], "serial")

        # Non-existing profile
        self.assertIsNone(self.profiles.get_profile("non_existing"))

    def test_validate_command_compatibility(self):
        # Compatible write command on microcontroller
        compat, msg = self.profiles.validate_command_compatibility(
            "esp32_zone1",
            {"command": "OPEN", "target": "L1_4"}
        )
        self.assertTrue(compat)
        self.assertIn("Capability validated", msg)

        # Incompatible target (unmapped breaker)
        compat, msg = self.profiles.validate_command_compatibility(
            "esp32_zone1",
            {"command": "OPEN", "target": "L6_7"}
        )
        self.assertFalse(compat)
        self.assertIn("not mapped in esp32_zone1", msg)

        # Standby device maps dynamically
        compat, msg = self.profiles.validate_command_compatibility(
            "esp32_backup",
            {"command": "CLOSE", "target": "L1_4"}
        )
        self.assertTrue(compat)
        self.assertIn("Dynamic capability mapped", msg)

        # Invalid command type
        compat, msg = self.profiles.validate_command_compatibility(
            "esp32_zone1",
            {"command": "READ_VOLTAGE", "target": "L1_4"}
        )
        self.assertFalse(compat)
        self.assertIn("Unknown command type", msg)

    def test_telemetry_payload(self):
        payload = self.profiles.get_telemetry_payload()
        self.assertIn("devices_count", payload)
        self.assertEqual(payload["devices_count"], 6)
        self.assertIn("serial", payload["interfaces"])
        self.assertIn("ethernet_tcp", payload["interfaces"])
        self.assertIn("esp32_zone1", payload["capabilities_map"])

if __name__ == "__main__":
    unittest.main()
