import os
import json
import logging
from typing import Dict, Any, List

logger = logging.getLogger("adversarial.memory")

class AdversarialMemory:
    def __init__(self, persistence_file: str = None):
        if persistence_file is None:
            adv_dir = os.path.dirname(os.path.abspath(__file__))
            self.persistence_file = os.path.join(adv_dir, "persistence", "adversarial_memory.json")
        else:
            self.persistence_file = persistence_file

        self.campaigns: List[Dict[str, Any]] = []
        self.node_weaknesses: Dict[str, Dict[str, Any]] = {}
        
        # Load from disk if it exists
        self.load()

    def record_simulation(
        self, 
        campaign: Dict[str, Any], 
        eval_metrics: Dict[str, Any], 
        resilience_metrics: Dict[str, Any]
    ):
        """
        Records the outcomes of a simulated adversarial campaign.
        """
        record = {
            "campaign_id": campaign.get("campaign_id"),
            "campaign_type": campaign.get("campaign_type"),
            "target": campaign.get("target"),
            "timestamp": campaign.get("timestamp"),
            "eval_metrics": eval_metrics,
            "resilience_metrics": resilience_metrics
        }
        self.campaigns.append(record)

        # Update node weakness profile statistics
        node = campaign.get("target", "Bus_5")
        if node not in self.node_weaknesses:
            self.node_weaknesses[node] = {
                "attempts": 0,
                "mitigation_failures": 0,
                "total_detection_delay": 0.0,
                "total_restoration_delay": 0.0
            }

        stats = self.node_weaknesses[node]
        stats["attempts"] += 1
        
        if not eval_metrics.get("mitigation_success", True):
            stats["mitigation_failures"] += 1

        stats["total_detection_delay"] += eval_metrics.get("detection_delay", 15.0)
        stats["total_restoration_delay"] += eval_metrics.get("restoration_delay", 30.0)

        self.save()

    def get_weakness_summary(self) -> Dict[str, Any]:
        """
        Identify high-risk nodes, slow recovery paths, and weak trust zones.
        """
        high_risk_nodes = []
        slow_recovery_paths = []
        weak_trust_zones = []

        for node, stats in self.node_weaknesses.items():
            attempts = stats["attempts"]
            if attempts == 0:
                continue

            fail_rate = stats["mitigation_failures"] / attempts
            avg_detect = stats["total_detection_delay"] / attempts
            avg_restore = stats["total_restoration_delay"] / attempts

            if fail_rate > 0.40 or avg_detect > 10.0:
                high_risk_nodes.append({
                    "node": node,
                    "failure_rate": round(fail_rate, 2),
                    "avg_detection_delay": round(avg_detect, 2)
                })

            if avg_restore > 20.0:
                slow_recovery_paths.append({
                    "path_or_node": node,
                    "avg_restoration_delay": round(avg_restore, 2)
                })

            # Check for slow trust recovery zones
            if avg_detect > 8.0:
                weak_trust_zones.append(node)

        # Default fallback values for cold-start cases
        if not high_risk_nodes:
            high_risk_nodes.append({"node": "Bus_5", "failure_rate": 0.0, "avg_detection_delay": 4.0})
        if not slow_recovery_paths:
            slow_recovery_paths.append({"path_or_node": "Bus_5", "avg_restoration_delay": 12.0})

        return {
            "high_risk_nodes": high_risk_nodes,
            "slow_recovery_paths": slow_recovery_paths,
            "weak_trust_zones": weak_trust_zones
        }

    def load(self):
        """
        Load historical records from persistence JSON.
        """
        if os.path.exists(self.persistence_file):
            try:
                with open(self.persistence_file, "r") as f:
                    data = json.load(f)
                    self.campaigns = data.get("campaigns", [])
                    self.node_weaknesses = data.get("node_weaknesses", {})
                logger.info(f"Adversarial memory loaded successfully from {self.persistence_file}")
            except Exception as e:
                logger.error(f"Failed to load adversarial memory: {e}")
        else:
            self.campaigns = []
            self.node_weaknesses = {}

    def save(self):
        """
        Serialize historical records to persistence JSON.
        Skip writing if running inside a pytest environment.
        """
        if "PYTEST_CURRENT_TEST" in os.environ:
            return
            
        try:
            os.makedirs(os.path.dirname(self.persistence_file), exist_ok=True)
            with open(self.persistence_file, "w") as f:
                json.dump({
                    "campaigns": self.campaigns,
                    "node_weaknesses": self.node_weaknesses
                }, f, indent=4)
        except Exception as e:
            logger.error(f"Failed to save adversarial memory: {e}")
