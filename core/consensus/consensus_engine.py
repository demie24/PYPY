from typing import Dict, Any, List
import logging

from .trust_fusion import TrustFusionEngine
from .regional_agent import RegionalAgent
from .leader_agent import LeaderAgent

logger = logging.getLogger("consensus.consensus_engine")

class ConsensusEngine:
    """
    Orchestrates the entire Hierarchical Consensus Layer.
    Initializes Regional Agents, manages trust scores, and directs the Leader Agent.
    """
    def __init__(self):
        self.trust_fusion = TrustFusionEngine()
        self.leader = LeaderAgent(self.trust_fusion)
        self.regions = self._setup_regions()

    def _setup_regions(self) -> List[RegionalAgent]:
        # Define bus partition for the 4 regions of IEEE 39-Bus Grid
        r1_buses = list(range(0, 10))
        r2_buses = list(range(10, 20))
        r3_buses = list(range(20, 30))
        r4_buses = list(range(30, 39))

        # Dynamically allocate lines to regions based on the source bus
        r1_lines = []
        r2_lines = []
        r3_lines = []
        r4_lines = []

        try:
            import os
            import sys
            current_dir = os.path.dirname(os.path.abspath(__file__))
            parent_dir = os.path.dirname(current_dir)
            sys.path.append(os.path.join(parent_dir, "digital_twin"))
            
            from core.digital_twin.grid_topology import GridTopology
            topo = GridTopology()
            for line in topo.lines:
                from_bus = line["from"]
                line_id = line["id"]
                if from_bus in r1_buses:
                    r1_lines.append(line_id)
                elif from_bus in r2_buses:
                    r2_lines.append(line_id)
                elif from_bus in r3_buses:
                    r3_lines.append(line_id)
                else:
                    r4_lines.append(line_id)
        except Exception as e:
            logger.warning(f"Could not load GridTopology dynamically, using empty lines fallback: {e}")
            # Fallback to empty lines if grid loader dependencies are not available
            pass

        return [
            RegionalAgent(1, "North", r1_buses, r1_lines),
            RegionalAgent(2, "East", r2_buses, r2_lines),
            RegionalAgent(3, "South", r3_buses, r3_lines),
            RegionalAgent(4, "West", r4_buses, r4_lines)
        ]

    def run_consensus(self, 
                      pinn_outputs: Any, 
                      lstm_outputs: Any, 
                      gnn_outputs: Any, 
                      stgnn_outputs: Any) -> Dict[str, Any]:
        """
        Executes a single cycle of regional evaluation and leader consensus formulation.
        
        Args:
            pinn_outputs: Physics validity score / violations
            lstm_outputs: LSTM anomalies/attack predictions
            gnn_outputs: GNN criticality/topology scores
            stgnn_outputs: ST-GNN future risks
            
        Returns:
            Dict containing the final decision, confidence, threat level, and logs.
        """
        # 1. Determine model confidences for Trust Fusion
        # If float inputs, they act as confidence indices. If dictionaries, we look for a 'confidence' key or use defaults.
        pinn_conf = self._extract_confidence(pinn_outputs, default=0.90, key="physics_validation_score")
        lstm_conf = self._extract_confidence(lstm_outputs, default=0.85, key="anomaly_probability")
        gnn_conf = self._extract_confidence(gnn_outputs, default=0.85, key="confidence")
        stgnn_conf = self._extract_confidence(stgnn_outputs, default=0.85, key="confidence")

        # 2. Evaluate each Regional Agent
        regional_decisions = []
        for r in self.regions:
            decision = r.evaluate(pinn_outputs, lstm_outputs, gnn_outputs, stgnn_outputs)
            regional_decisions.append(decision)

        # 3. Leader Agent Consensus
        consensus = self.leader.evaluate_consensus(
            regional_decisions,
            pinn_conf,
            lstm_conf,
            gnn_conf,
            stgnn_conf
        )

        return {
            "decision": consensus["final_decision"],
            "threat_score": consensus["global_threat_score"],
            "threat_level": consensus["threat_level"],
            "confidence_score": consensus["global_confidence_score"],
            "action_logits": consensus["action_logits"],
            "regional_reports": regional_decisions,
            "distribution_summary": consensus["regional_recommendations"]
        }

    def _extract_confidence(self, val: Any, default: float, key: str) -> float:
        if isinstance(val, (int, float)):
            return float(val)
        elif isinstance(val, dict):
            # Try specified key first, then 'confidence', then default
            return float(val.get(key, val.get("confidence", default)))
        return default
