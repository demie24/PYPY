import logging
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger("hardware.profiles")

class DeploymentProfiles:
    def __init__(self):
        # Deployment Profiles Registry
        self.profiles: Dict[str, Dict[str, Any]] = {
            "esp32_zone1": {
                "device_type": "microcontroller",
                "interface": "serial",
                "physical_address": "/dev/ttyUSB0",
                "capabilities": ["GPIO_WRITE", "GPIO_READ", "SERIAL_CONSOLE"],
                "timing_accuracy_ms": 5.0,
                "default_safe_states": {
                    "L1_4": "CLOSED",
                    "L2_7": "CLOSED"
                },
                "pin_mappings": {
                    "L1_4": {"coil": "pin_4", "feedback": "pin_21"},
                    "L2_7": {"coil": "pin_5", "feedback": "pin_22"}
                }
            },
            "esp32_zone2": {
                "device_type": "microcontroller",
                "interface": "serial",
                "physical_address": "/dev/ttyUSB1",
                "capabilities": ["GPIO_WRITE", "GPIO_READ", "SERIAL_CONSOLE"],
                "timing_accuracy_ms": 5.0,
                "default_safe_states": {
                    "L3_9": "CLOSED",
                    "L4_5": "CLOSED"
                },
                "pin_mappings": {
                    "L3_9": {"coil": "pin_6", "feedback": "pin_23"},
                    "L4_5": {"coil": "pin_12", "feedback": "pin_25"}
                }
            },
            "esp32_zone3": {
                "device_type": "microcontroller",
                "interface": "serial",
                "physical_address": "/dev/ttyUSB2",
                "capabilities": ["GPIO_WRITE", "GPIO_READ", "SERIAL_CONSOLE"],
                "timing_accuracy_ms": 5.0,
                "default_safe_states": {
                    "L4_9": "CLOSED",
                    "L5_6": "CLOSED"
                },
                "pin_mappings": {
                    "L4_9": {"coil": "pin_13", "feedback": "pin_26"},
                    "L5_6": {"coil": "pin_14", "feedback": "pin_27"}
                }
            },
            "plc_primary": {
                "device_type": "plc",
                "interface": "ethernet_tcp",
                "physical_address": "192.168.1.10:502",
                "capabilities": ["MODBUS_COIL_WRITE", "MODBUS_COIL_READ", "MODBUS_REGISTER_READ"],
                "timing_accuracy_ms": 1.0,
                "default_safe_states": {
                    "L6_7": "CLOSED",
                    "L7_8": "OPEN",
                    "L8_9": "CLOSED"
                },
                "pin_mappings": {
                    "L6_7": {"coil": 7, "feedback": "pin_32"},
                    "L7_8": {"coil": 8, "feedback": "pin_33"},
                    "L8_9": {"coil": 9, "feedback": "pin_34"}
                }
            },
            "esp32_backup": {
                "device_type": "microcontroller",
                "interface": "serial",
                "physical_address": "/dev/ttyUSB3",
                "capabilities": ["GPIO_WRITE", "GPIO_READ"],
                "timing_accuracy_ms": 8.0,
                "default_safe_states": {
                    "L1_4": "CLOSED",
                    "L2_7": "CLOSED",
                    "L3_9": "CLOSED",
                    "L4_5": "CLOSED",
                    "L4_9": "CLOSED",
                    "L5_6": "CLOSED"
                },
                "pin_mappings": {}  # Dynamically routed mapping in failover
            },
            "plc_backup": {
                "device_type": "plc",
                "interface": "ethernet_tcp",
                "physical_address": "192.168.1.11:502",
                "capabilities": ["MODBUS_COIL_WRITE", "MODBUS_COIL_READ"],
                "timing_accuracy_ms": 2.0,
                "default_safe_states": {
                    "L6_7": "CLOSED",
                    "L7_8": "OPEN",
                    "L8_9": "CLOSED"
                },
                "pin_mappings": {}  # Dynamically routed mapping in failover
            }
        }

    def get_profile(self, device_id: str) -> Optional[Dict[str, Any]]:
        """
        Returns the deployment profile for a specific device.
        """
        return self.profiles.get(device_id)

    def validate_command_compatibility(self, device_id: str, command: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validates if the command and target breaker match the device's capability profile.
        """
        profile = self.get_profile(device_id)
        if not profile:
            return False, f"Device profile {device_id} not registered."

        cmd_type = command.get("command")
        target = command.get("target")

        # Map commands to required capability classes
        if cmd_type in ["OPEN", "CLOSE", "CLOSED"]:
            # Check if this device supports output execution
            required_cap = "MODBUS_COIL_WRITE" if profile["device_type"] == "plc" else "GPIO_WRITE"
            if required_cap not in profile["capabilities"]:
                return False, f"Device {device_id} lacks capability: {required_cap} required for relay switching."
        else:
            return False, f"Unknown command type: {cmd_type}"

        # If it is a backup, it can map dynamically, so skip mapping verification
        if "backup" in device_id:
            return True, "Dynamic capability mapped for standby device."

        # Verify target mapping exists on primary devices
        if target and target not in profile["pin_mappings"]:
            # PLC can backup ESP32 in some loops
            if profile["device_type"] == "plc" and "MODBUS_COIL_WRITE" in profile["capabilities"]:
                return True, "Cross-device Modbus routing enabled."
            return False, f"Target {target} not mapped in {device_id} profile configuration."

        return True, f"Capability validated: {device_id} is compatible with {cmd_type} action."

    def get_telemetry_payload(self) -> Dict[str, Any]:
        """
        Returns serialization of registered capabilities.
        """
        return {
            "devices_count": len(self.profiles),
            "interfaces": list(set(d["interface"] for d in self.profiles.values())),
            "capabilities_map": {k: v["capabilities"] for k, v in self.profiles.items()}
        }
