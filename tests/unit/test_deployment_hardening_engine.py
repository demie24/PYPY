import unittest
import sys
import os

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

from core.hardware.deployment_hardening_engine import DeploymentHardeningEngine

class TestDeploymentHardeningEngine(unittest.TestCase):
    def setUp(self):
        self.engine = DeploymentHardeningEngine()

    def test_initial_state(self):
        # All 5 checks are initially True, score = 100%, SECURE
        self.assertEqual(self.engine.compliance_score, 100.0)
        self.assertEqual(self.engine.deployment_safety_status, "SECURE")
        self.assertTrue(self.engine.network_segmentation_valid)
        self.assertEqual(self.engine.readiness_status, "READINESS_VERIFIED")
        self.assertEqual(self.engine.unhardened_features, [])

    def test_compliance_score_deduction(self):
        # Disable SECURE_BOOT_ENABLED -> score should be 80% (4 out of 5 passed)
        # Safety status should drop to WARNING
        self.engine.set_check_state("SECURE_BOOT_ENABLED", False)
        
        self.assertEqual(self.engine.compliance_score, 80.0)
        self.assertEqual(self.engine.deployment_safety_status, "WARNING")
        self.assertEqual(self.engine.readiness_status, "READINESS_VERIFIED")
        self.assertEqual(self.engine.unhardened_features, ["SECURE_BOOT_ENABLED"])

    def test_critical_failure_network_segmentation(self):
        # Disable PORT_SECTOR_SEGMENTATION -> critical failure
        # Safety status drops to INSECURE, readiness status drops to NOT_READY
        self.engine.set_check_state("PORT_SECTOR_SEGMENTATION", False)
        
        self.assertEqual(self.engine.deployment_safety_status, "INSECURE")
        self.assertEqual(self.engine.readiness_status, "NOT_READY")
        self.assertFalse(self.engine.network_segmentation_valid)

    def test_critical_failure_default_credentials(self):
        # Disable DEFAULT_CREDENTIALS_CHANGED -> critical failure
        # Safety status drops to INSECURE, readiness status drops to NOT_READY
        self.engine.set_check_state("DEFAULT_CREDENTIALS_CHANGED", False)
        
        self.assertEqual(self.engine.deployment_safety_status, "INSECURE")
        self.assertEqual(self.engine.readiness_status, "NOT_READY")

    def test_low_compliance_score(self):
        # Let's disable multiple checks to drop compliance score < 70% but not critical checks
        self.engine.set_check_state("SECURE_BOOT_ENABLED", False)
        self.engine.set_check_state("ENCRYPTED_COMMS_ONLY", False)
        # 3/5 = 60.0% score -> drops to INSECURE & NOT_READY even without critical failures
        self.assertEqual(self.engine.compliance_score, 60.0)
        self.assertEqual(self.engine.deployment_safety_status, "INSECURE")
        self.assertEqual(self.engine.readiness_status, "NOT_READY")

if __name__ == "__main__":
    unittest.main()
