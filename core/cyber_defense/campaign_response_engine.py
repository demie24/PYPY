import time
import logging
from typing import Dict, Any, List

logger = logging.getLogger("cyber_defense.campaign_engine")

class CampaignResponseEngine:
    """
    Detects and classifies coordinated, multi-stage cyber campaigns.
    Tracks timelines and relations to recommend containment strategies and operational modes.
    """
    def __init__(self):
        # Current active campaigns: list of dicts
        self.active_campaigns = {}
        # Campaign ID counter
        self.campaign_id_seq = 1000

    def analyze_campaigns(self, alerts: List[Dict[str, Any]], events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Correlates raw alerts and events into stateful multi-stage campaign tracks.
        """
        now = time.time()
        
        # Parse inputs to discover active campaigns
        new_intrusions = []
        for alert in alerts:
            new_intrusions.append({
                "timestamp": alert.get("timestamp", int(now * 1000)),
                "type": alert.get("type", "UNKNOWN"),
                "target": alert.get("suspect_node") or alert.get("target", "SYSTEM"),
                "severity": alert.get("severity", "WARNING")
            })

        for event in events:
            # Look for compromise events
            evt_str = event.get("event", "")
            src = event.get("source", "")
            if "compromise" in evt_str.lower() or "compromised" in evt_str.lower():
                new_intrusions.append({
                    "timestamp": event.get("timestamp", int(now * 1000)),
                    "type": "CYBER_COMPROMISE",
                    "target": src or "SYSTEM",
                    "severity": event.get("severity", "WARNING")
                })
            elif "trip" in evt_str.lower() or "tripped" in evt_str.lower():
                new_intrusions.append({
                    "timestamp": event.get("timestamp", int(now * 1000)),
                    "type": "BREAKER_TRIP",
                    "target": src or "SYSTEM",
                    "severity": "CRITICAL" if event.get("severity") == "CRITICAL" else "HIGH"
                })

        # Group intrusions by correlation windows (e.g. 60 seconds)
        if len(new_intrusions) > 0:
            campaign_key = self._find_or_create_campaign(new_intrusions, now)
            campaign = self.active_campaigns[campaign_key]
            
            # Update campaign elements
            for intrusion in new_intrusions:
                # Add unique target/type to campaign
                if intrusion["target"] not in campaign["targets"]:
                    campaign["targets"].append(intrusion["target"])
                if intrusion["type"] not in campaign["attack_types"]:
                    campaign["attack_types"].append(intrusion["type"])
                
            campaign["last_updated"] = now
            campaign["severity"] = self._calculate_campaign_severity(campaign)
            campaign["stage"] = self._determine_campaign_stage(campaign)
        
        # Prune campaigns inactive for more than 120s
        inactive_campaigns = []
        for cid, camp in self.active_campaigns.items():
            if now - camp["last_updated"] > 120.0:
                inactive_campaigns.append(cid)
        for cid in inactive_campaigns:
            self.active_campaigns.pop(cid)

        # 4. Formulate global strategy and mode based on campaigns
        campaign_list = list(self.active_campaigns.values())
        max_severity = 0
        campaign_detected = False
        containment_strategy = "NOMINAL_MONITORING"
        trusted_op_mode = "NOMINAL"
        active_campaign_types = []

        if len(campaign_list) > 0:
            campaign_detected = True
            max_severity = max(c["severity"] for c in campaign_list)
            # Find the most advanced stage
            stages = [c["stage"] for c in campaign_list]
            active_campaign_types = list(set(c["classification"] for c in campaign_list))
            
            if "CASCADE_TRIGGERED" in stages or max_severity >= 75:
                containment_strategy = "LOCKDOWN_ALL_SECTORS_AND_PRESERVE"
                trusted_op_mode = "EMERGENCY_LOCK"
            elif "COORDINATED_STRIKE" in stages or max_severity >= 50:
                containment_strategy = "ISOLATE_COMPROMISED_ZONES_AND_HALT_AUTO_FLISR"
                trusted_op_mode = "RULE_BASED_RESTRICTED"
            else:
                containment_strategy = "TELEMETRY_FILTERING_AND_MONITORING"
                trusted_op_mode = "NOMINAL"

        return {
            "campaign_detected": campaign_detected,
            "campaign_severity_score": int(max_severity),
            "containment_strategy": containment_strategy,
            "trusted_operational_mode": trusted_op_mode,
            "active_campaigns": campaign_list,
            "active_campaign_types": active_campaign_types
        }

    def _find_or_create_campaign(self, intrusions: List[Dict[str, Any]], now: float) -> int:
        """Finds matching campaign within active window or creates a new track."""
        for cid, camp in self.active_campaigns.items():
            # If within 60s of last update, classify as same campaign
            if now - camp["last_updated"] < 60.0:
                return cid
                
        # Create new campaign
        cid = self.campaign_id_seq
        self.campaign_id_seq += 1
        
        # Classification guess
        types = [i["type"] for i in intrusions]
        classification = "STEALTHY_INTRA_GRID_ATTACK"
        if any("FDIA" in t for t in types):
            classification = "COORDINATED_FDIA"
        elif any("REPLAY" in t for t in types):
            classification = "REPLAY_CHAIN"
        elif any("DOS" in t for t in types) or any("JAMMING" in t for t in types):
            classification = "CASCADING_CYBER_ATTACK"
        elif any("TRIP" in t or "BREAKER" in t for t in types):
            classification = "TOPOLOGY_MANIPULATION"

        self.active_campaigns[cid] = {
            "campaign_id": cid,
            "start_time": int(now * 1000),
            "last_updated": now,
            "targets": [],
            "attack_types": [],
            "severity": 10.0,
            "stage": "RECONNAISSANCE",
            "classification": classification
        }
        return cid

    def _calculate_campaign_severity(self, campaign: dict) -> float:
        """Calculates stateful severity based on target count and categories."""
        score = 10.0
        # Target count scaling
        score += min(35, len(campaign["targets"]) * 10)
        # Type variety scaling
        score += min(25, len(campaign["attack_types"]) * 8)
        
        # Critical action indicators
        if "COORDINATED_TRIP" in campaign["attack_types"] or "BREAKER_TRIP" in campaign["attack_types"]:
            score += 20
        if "SLACK_TRIP" in campaign["attack_types"]:
            score += 30
            
        return min(100.0, score)

    def _determine_campaign_stage(self, campaign: dict) -> str:
        """Determines active stage of the campaign sequence."""
        target_count = len(campaign["targets"])
        type_count = len(campaign["attack_types"])
        
        if target_count >= 4 or "SLACK_TRIP" in campaign["attack_types"]:
            return "CASCADE_TRIGGERED"
        elif target_count >= 2 and type_count >= 2:
            return "COORDINATED_STRIKE"
        elif target_count >= 2:
            return "LATERAL_PROPAGATION"
        elif target_count == 1:
            return "INITIAL_COMPROMISE"
            
        return "RECONNAISSANCE"
