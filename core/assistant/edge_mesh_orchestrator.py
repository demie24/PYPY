import logging
from typing import Dict, Any, List

logger = logging.getLogger("assistant.edge_mesh_orchestrator")

class EdgeMeshOrchestrator:
    def __init__(self):
        self.agent_name = "EdgeMeshOrchestrator"
        self.status = "NOMINAL"
        self.mesh_status = "CONNECTED"
        
        # Nodes topology layout
        self.nodes: Dict[str, Dict[str, Any]] = {
            "esp32_zone1": {"group": "ZoneA", "links": ["plc_primary", "esp32_zone2"]},
            "esp32_zone2": {"group": "ZoneA", "links": ["plc_primary", "esp32_zone1", "esp32_zone3"]},
            "esp32_zone3": {"group": "ZoneB", "links": ["plc_backup", "esp32_zone2", "esp32_backup"]},
            "plc_primary": {"group": "ZoneA", "links": ["esp32_zone1", "esp32_zone2"]},
            "plc_backup": {"group": "ZoneB", "links": ["esp32_zone3", "esp32_backup"]},
            "esp32_backup": {"group": "ZoneB", "links": ["plc_backup", "esp32_zone3"]}
        }
        
        self.links: List[Dict[str, Any]] = []
        self.partition_failures: List[str] = []
        self.cascade_risk_paths: List[Dict[str, Any]] = []
        self.relay_groups: Dict[str, List[str]] = {
            "ZoneA": ["esp32_zone1", "esp32_zone2", "plc_primary"],
            "ZoneB": ["esp32_zone3", "esp32_backup", "plc_backup"]
        }
        self.worst_node = None
        self.node_states = {}

    def tick_mesh_orchestrator(self, edge_summary: Dict[str, Any], telemetry: Dict[str, Any], simulation_mode: str = None) -> Dict[str, Any]:
        """Analyzes edge mesh connection topologies, link status, and failure cascade propagation risks."""
        self.links.clear()
        self.partition_failures.clear()
        self.cascade_risk_paths.clear()

        node_states = edge_summary.get("nodes", {})
        self.node_states = node_states
        
        # Capture worst node or compute it if missing
        self.worst_node = edge_summary.get("worst_node")
        if not self.worst_node and node_states:
            # Find the node with the lowest health or offline status
            min_health = 1.01
            worst_id = None
            for node_id, state in node_states.items():
                health = state.get("health", 1.0)
                if health < min_health:
                    min_health = health
                    worst_id = node_id
            if min_health < 1.0:
                self.worst_node = worst_id
        
        # Build active links list based on node online status
        seen_pairs = set()
        for node_id, config in self.nodes.items():
            node_online = node_states.get(node_id, {}).get("online", True)
            for target in config["links"]:
                pair_key = tuple(sorted([node_id, target]))
                if pair_key in seen_pairs:
                    continue
                seen_pairs.add(pair_key)
                
                target_online = node_states.get(target, {}).get("online", True)
                
                # Check for simulation overrides
                link_broken = False
                if simulation_mode == "edge_mesh_partition_failures":
                    # Break link connecting ZoneA and ZoneB (esp32_zone2 <-> esp32_zone3)
                    if "esp32_zone2" in pair_key and "esp32_zone3" in pair_key:
                        link_broken = True
                
                link_active = node_online and target_online and not link_broken
                
                self.links.append({
                    "source": node_id,
                    "target": target,
                    "status": "ACTIVE" if link_active else "BROKEN",
                    "reason": "NODE_OFFLINE" if not (node_online and target_online) else ("PARTITION" if link_broken else "NOMINAL")
                })

        # Calculate partition state
        broken_links = [l for l in self.links if l["status"] == "BROKEN"]
        
        if simulation_mode == "edge_mesh_partition_failures":
            self.mesh_status = "PARTITIONED"
            self.status = "CRITICAL"
            self.partition_failures.append("Mesh terpisah (partitioned): Jambatan komunikasi antara ZoneA dan ZoneB terputus.")
        elif len(broken_links) >= 3:
            self.mesh_status = "DEGRADED"
            self.status = "DEGRADED"
            self.partition_failures.append("Pelbagai laluan mesh terputus. Redundansi komunikasi terjejas.")
        else:
            self.mesh_status = "CONNECTED"
            self.status = "NOMINAL"

        # Cascade Risk Analysis
        # If a node has high load or low health, evaluate link propagation path
        for node_id, state in node_states.items():
            health = state.get("health", 1.0)
            latency = state.get("latency_ms", 45.0)
            
            if health < 0.70 or latency > 100.0:
                # Trace connections to compute potential cascade path
                for link in self.links:
                    if link["status"] == "ACTIVE" and (link["source"] == node_id or link["target"] == node_id):
                        peer = link["target"] if link["source"] == node_id else link["source"]
                        risk_level = "HIGH" if health < 0.50 else "MEDIUM"
                        self.cascade_risk_paths.append({
                            "path": f"{node_id} ➔ {peer}",
                            "risk": risk_level,
                            "trigger": "Komunikasi terdegradasi / Latensi tinggi"
                        })

        return self.get_status_summary()

    def get_status_summary(self) -> Dict[str, Any]:
        nodes_summary = {}
        for k, v in self.nodes.items():
            nodes_summary[k] = {
                **v,
                **(self.node_states.get(k, {}))
            }
        return {
            "agent_name": self.agent_name,
            "status": self.status,
            "mesh_status": self.mesh_status,
            "links": self.links,
            "partition_failures": self.partition_failures,
            "cascade_risk_paths": self.cascade_risk_paths,
            "relay_groups": self.relay_groups,
            "worst_node": self.worst_node,
            "nodes": nodes_summary
        }

    def reset_orchestrator(self):
        self.status = "NOMINAL"
        self.mesh_status = "CONNECTED"
        self.links.clear()
        self.partition_failures.clear()
        self.cascade_risk_paths.clear()
        self.worst_node = None
        self.node_states.clear()
