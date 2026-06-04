import time
from typing import Dict, Any, List

class CampaignSimulator:
    def __init__(self):
        pass

    def simulate_campaign(
        self, 
        campaign: Dict[str, Any], 
        active_defenses: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Simulate adaptive campaign execution against active cyber defenses.
        """
        campaign_type = campaign.get("campaign_type", "TELEMETRY_MANIPULATION")
        target = campaign.get("target", "Bus_5")
        start_ms = campaign.get("timestamp", int(time.time() * 1000))

        simulated_events = []
        simulated_telemetry = []

        # Base nominal state to progress
        base_state = {
            "buses": {f"Bus_{i}": {"voltage_pu": 1.0, "frequency_hz": 60.0} for i in range(1, 10)},
            "lines": {l: {"capacity_pct": 50.0, "current_pu": 0.5} for l in [
                "L1_4", "L2_7", "L3_9", "L4_5", "L4_9", "L5_6", "L6_7", "L7_8", "L8_9"
            ]}
        }

        # Step 0: Campaign started
        simulated_events.append({
            "timestamp": start_ms,
            "source": "ADVERSARIAL",
            "event": f"Adversarial campaign {campaign.get('campaign_id')} of type {campaign_type} launched targeting {target}.",
            "severity": "WARNING"
        })

        # Step 1: Attack begins to impact grid
        attack_ms = start_ms + 2000
        simulated_events.append({
            "timestamp": attack_ms,
            "source": "GRID_ATTACK",
            "event": f"Exploited telemetry sensor validation node on {target}.",
            "severity": "ERROR"
        })

        # Generate telemetry with voltage drops from the attack sequence
        t1 = {
            "timestamp": attack_ms,
            "state": {
                "buses": {
                    **base_state["buses"],
                    target: {"voltage_pu": 0.88 if campaign_type == "FDIA_ESCALATION" else 0.94, "frequency_hz": 60.0}
                },
                "lines": base_state["lines"]
            }
        }
        simulated_telemetry.append(t1)

        # Step 2: Detection engine alerts
        detect_ms = start_ms + 6000
        simulated_events.append({
            "timestamp": detect_ms,
            "source": "DETECTION",
            "event": f"ANOMALY DETECTED: Cyber threat alert score elevated on node {target}.",
            "severity": "CRITICAL"
        })

        # Step 3: Defense isolation response
        isolate_ms = start_ms + 12000
        simulated_events.append({
            "timestamp": isolate_ms,
            "source": "DEFENSE",
            "event": f"GRID ISOLATED: Breaker controls activated to quarantine target bus {target}.",
            "severity": "INFO"
        })

        # Step 4: Self-healing restoration
        restore_ms = start_ms + 24000
        simulated_events.append({
            "timestamp": restore_ms,
            "source": "SELF_HEALING",
            "event": "NORMAL OPERATIONS: Grid topology rerouted and stabilized.",
            "severity": "INFO"
        })

        # Final telemetry showing recovered voltage and bypassed quarantined line
        t2 = {
            "timestamp": restore_ms,
            "state": {
                "buses": {
                    **base_state["buses"],
                    target: {"voltage_pu": 1.0, "frequency_hz": 60.0}
                },
                "lines": {
                    **base_state["lines"],
                    "L4_5": {"capacity_pct": 0.0, "current_pu": 0.0}  # Quarantined/isolated
                }
            }
        }
        simulated_telemetry.append(t2)

        return {
            "simulated_events": simulated_events,
            "simulated_telemetry": simulated_telemetry
        }
