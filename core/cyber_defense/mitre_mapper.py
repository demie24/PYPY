import logging
from typing import Dict, Any, List

logger = logging.getLogger("cyber_defense.mitre_mapper")

class MitreMapper:
    """
    Maps real-time grid alerts and telemetry indicators to MITRE ICS ATT&CK techniques.
    """
    def __init__(self):
        # Technique mapping repository
        self.TECHNIQUES = {
            "T0814": {
                "name": "Data Injection",
                "description": "Active tampering of sensor measurements and digital state parameters (FDIA/Sensor Spoofing).",
                "tactic": "Impair Process Control"
            },
            "T0809": {
                "name": "Data Replay",
                "description": "Capture and replay of historical telemetry packets to mask current grid operational state.",
                "tactic": "Evasion"
            },
            "T0883": {
                "name": "Denial of Service",
                "description": "Disruption of communications channels between telemetry agents, SCADA, or controllers.",
                "tactic": "Inhibit Response Function"
            },
            "T0861": {
                "name": "Restoration Interception",
                "description": "Interference with FLISR/RL autonomous restoration loops (unauthorized tripping of closing lines).",
                "tactic": "Inhibit Response Function"
            },
            "T0812": {
                "name": "Command Generation",
                "description": "Injection of unauthorized command execution payloads targeting line breakers or regulators.",
                "tactic": "Impair Process Control"
            }
        }

    def map_alerts_to_techniques(self, alerts: List[Dict[str, Any]], events: List[Dict[str, Any]]) -> List[str]:
        """
        Translates a list of alerts and events into active MITRE techniques.
        """
        techniques = set()
        
        # 1. Evaluate Alert signatures
        for alert in alerts:
            atk_type = alert.get("type", "UNKNOWN")
            
            if "FDIA" in atk_type or "SPOOF" in atk_type or "SENSOR_ANOMALY" in atk_type:
                techniques.add("T0814")
            elif "REPLAY" in atk_type:
                techniques.add("T0809")
            elif "DOS" in atk_type or "JAMMING" in atk_type or "COMM_LOSS" in atk_type:
                techniques.add("T0883")
            elif "INTERCEPT" in atk_type or "RESTORE" in atk_type:
                techniques.add("T0861")
            elif "UNAUTHORIZED" in atk_type or "COMMAND" in atk_type:
                techniques.add("T0812")

        # 2. Evaluate Event anomalies
        for event in events:
            evt_str = event.get("event", "")
            
            if "compromise" in evt_str.lower() or "compromised" in evt_str.lower():
                techniques.add("T0812")
            if "failed" in evt_str.lower() and ("restor" in evt_str.lower() or "heal" in evt_str.lower()):
                techniques.add("T0861")
            if "dos" in evt_str.lower() or "jam" in evt_str.lower():
                techniques.add("T0883")
            if "fdia" in evt_str.lower() or "spoof" in evt_str.lower():
                techniques.add("T0814")
                
        return sorted(list(techniques))

    def get_technique_details(self, tech_id: str) -> Dict[str, str]:
        """Returns details for a mapped MITRE ATT&CK technique."""
        return self.TECHNIQUES.get(tech_id, {
            "name": "Unknown",
            "description": "Unmapped cyber-physical threat indicator.",
            "tactic": "Unknown"
        })
