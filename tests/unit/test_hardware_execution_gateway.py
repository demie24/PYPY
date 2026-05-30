import unittest
import sys
import os

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

from core.hardware.hardware_state_manager import HardwareStateManager
from core.hardware.edge_device_manager import EdgeDeviceManager
from core.hardware.deployment_profiles import DeploymentProfiles
from core.hardware.edge_reliability_monitor import EdgeReliabilityMonitor
from core.hardware.safe_relay_guard import SafeRelayGuard
from core.hardware.relay_controller import RelayController
from core.hardware.esp32_bridge import ESP32Bridge
from core.hardware.plc_interface import PLCInterface
from core.hardware.hardware_command_router import HardwareCommandRouter
from core.hardware.hardware_execution_gateway import HardwareExecutionGateway

class TestHardwareExecutionGateway(unittest.TestCase):
    def setUp(self):
        self.state_mgr = HardwareStateManager()
        self.device_mgr = EdgeDeviceManager(self.state_mgr)
        self.profiles = DeploymentProfiles()
        self.safety_guard = SafeRelayGuard()
        self.reliability_monitor = EdgeReliabilityMonitor()
        
        self.relay_ctrl = RelayController(self.state_mgr)
        self.esp_bridge = ESP32Bridge(self.state_mgr, self.relay_ctrl)
        self.plc_inter = PLCInterface(self.state_mgr, self.relay_ctrl)
        self.router = HardwareCommandRouter(self.state_mgr, self.esp_bridge, self.plc_inter, self.relay_ctrl)
        
        self.gateway = HardwareExecutionGateway(
            device_manager=self.device_mgr,
            profiles=self.profiles,
            safety_guard=self.safety_guard,
            reliability_monitor=self.reliability_monitor,
            command_router=self.router
        )

    def test_permission_authorization(self):
        # Authorized source: SCADA_OPERATOR
        success, reason = self.gateway.execute_command({
            "command": "OPEN",
            "target": "L4_9",
            "source": "SCADA_OPERATOR"
        })
        self.assertTrue(success)

        # Unauthorized source: MALICIOUS_HACKER
        success, reason = self.gateway.execute_command({
            "command": "OPEN",
            "target": "L4_9",
            "source": "MALICIOUS_HACKER"
        })
        self.assertFalse(success)
        self.assertIn("PERMISSION_DENIED", reason)

    def test_quarantined_zone_blocking(self):
        # Initially, execute is successful
        success, _ = self.gateway.execute_command({
            "command": "OPEN",
            "target": "L4_9",
            "source": "SCADA_OPERATOR"
        })
        self.assertTrue(success)

        # Mark zone_3 as compromised
        self.gateway.set_zone_compromised("zone_3", True)

        # Control from SCADA operator should now be blocked
        success, reason = self.gateway.execute_command({
            "command": "OPEN",
            "target": "L4_9",
            "source": "SCADA_OPERATOR"
        })
        self.assertFalse(success)
        self.assertIn("quarantined/compromised", reason)

        # But safety guard emergency override commands are still allowed
        success, _ = self.gateway.execute_command({
            "command": "CLOSED",
            "target": "L5_6",
            "source": "SAFETY_GUARD"
        })
        self.assertTrue(success)

    def test_device_quarantine_blocking(self):
        # Quarantine all potential controllers for zone_3 to ensure it cannot fail over to a clean one
        self.device_mgr.set_device_quarantine("esp32_zone3", True)
        self.device_mgr.set_device_quarantine("esp32_backup", True)
        self.device_mgr.set_device_quarantine("plc_primary", True)

        # SCADA command targeting a breaker on esp32_zone3 should be blocked
        success, reason = self.gateway.execute_command({
            "command": "OPEN",
            "target": "L4_9",
            "source": "SCADA_OPERATOR"
        })
        self.assertFalse(success)
        self.assertIn("quarantined/compromised", reason)

    def test_command_validation_chain(self):
        # 1. Capability check fails: remove GPIO_WRITE capability from esp32_zone3 profile
        self.profiles.profiles["esp32_zone3"]["capabilities"] = []
        success, reason = self.gateway.execute_command({
            "command": "OPEN",
            "target": "L4_9",
            "source": "SCADA_OPERATOR"
        })
        self.assertFalse(success)
        self.assertIn("INCOMPATIBLE", reason)

        # Restore capability
        self.profiles.profiles["esp32_zone3"]["capabilities"] = ["GPIO_WRITE", "GPIO_READ", "SERIAL_CONSOLE"]

        # 2. Safety Interlock check fails: opening generator line L1_4
        success, reason = self.gateway.execute_command({
            "command": "OPEN",
            "target": "L1_4",
            "source": "SCADA_OPERATOR"
        })
        self.assertFalse(success)
        self.assertIn("SAFETY_VIOLATION", reason)

    def test_execution_logging_and_reliability_registration(self):
        # Normal execution
        self.gateway.execute_command({
            "command": "OPEN",
            "target": "L4_9",
            "source": "SCADA_OPERATOR"
        })

        # Verify entry appended to log queue
        log = self.gateway.execution_log
        self.assertEqual(len(log), 1)
        self.assertEqual(log[0]["command"], "OPEN")
        self.assertEqual(log[0]["status"], "EXECUTED")

        # Verify registered in reliability monitor for feedback tracking
        self.assertEqual(len(self.reliability_monitor.pending_relay_commands), 1)
        self.assertIn("L4_9", self.reliability_monitor.pending_relay_commands)

if __name__ == "__main__":
    unittest.main()
