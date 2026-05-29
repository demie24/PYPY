import time
import logging
from typing import Dict, Any, List

logger = logging.getLogger("hardware.hardening")

class DeploymentHardeningEngine:
    def __init__(self):
        # Configuration checks database
        self.compliance_checks = {
            "SECURE_BOOT_ENABLED": True,
            "ENCRYPTED_COMMS_ONLY": True,
            "DEFAULT_CREDENTIALS_CHANGED": True,
            "PORT_SECTOR_SEGMENTATION": True,  # Network segmentation state
            "ACCESS_CONTROL_ENFORCED": True
        }
        self.compliance_score = 100.0
        self.deployment_safety_status = "SECURE"  # SECURE, WARNING, INSECURE
        self.network_segmentation_valid = True
        self.readiness_status = "READINESS_VERIFIED"  # READINESS_VERIFIED, NOT_READY
        self.unhardened_features: List[str] = []
        
    def evaluate_compliance(self) -> float:
        """
        Runs checks to evaluate deployment hardening and calculates the compliance score.
        Enforces strict penalty if network segmentation or default credentials fail.
        """
        self.unhardened_features = []
        passed = 0
        total = len(self.compliance_checks)
        
        for check, state in self.compliance_checks.items():
            if state:
                passed += 1
            else:
                self.unhardened_features.append(check)
                
        self.compliance_score = round((passed / total) * 100.0, 1)
        
        # Enforce network segmentation state directly
        self.network_segmentation_valid = self.compliance_checks.get("PORT_SECTOR_SEGMENTATION", False)
        
        # Security state classification & Penalties
        # Proposal: If segmentation is invalid or default credentials not changed, mark as INSECURE
        critical_fail = not self.network_segmentation_valid or not self.compliance_checks.get("DEFAULT_CREDENTIALS_CHANGED", False)
        
        if critical_fail:
            self.deployment_safety_status = "INSECURE"
            self.readiness_status = "NOT_READY"
            if not self.network_segmentation_valid:
                logger.error("HARDENING_COMPLIANCE_CRITICAL_FAILURE: Port network segmentation validation failed!")
            if not self.compliance_checks.get("DEFAULT_CREDENTIALS_CHANGED", False):
                logger.error("HARDENING_COMPLIANCE_CRITICAL_FAILURE: Default admin credentials detected!")
        else:
            if self.compliance_score >= 90.0:
                self.deployment_safety_status = "SECURE"
                self.readiness_status = "READINESS_VERIFIED"
            elif self.compliance_score >= 70.0:
                self.deployment_safety_status = "WARNING"
                self.readiness_status = "READINESS_VERIFIED"
            else:
                self.deployment_safety_status = "INSECURE"
                self.readiness_status = "NOT_READY"
                
        return self.compliance_score

    def set_check_state(self, check_name: str, state: bool):
        """
        Dynamically updates compliance check states.
        """
        if check_name in self.compliance_checks:
            self.compliance_checks[check_name] = state
            self.evaluate_compliance()
            logger.info(f"Hardening Compliance check {check_name} updated to {state}. New Compliance Score: {self.compliance_score}%")

    def get_telemetry_payload(self) -> Dict[str, Any]:
        """
        Serializes current hardening compliance status.
        """
        return {
            "timestamp": int(time.time() * 1000),
            "compliance_score": self.compliance_score,
            "unhardened_features": self.unhardened_features,
            "deployment_safety_status": self.deployment_safety_status,
            "network_segmentation_valid": self.network_segmentation_valid,
            "readiness_status": self.readiness_status,
            "checks": self.compliance_checks
        }
