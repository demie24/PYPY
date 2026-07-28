from typing import Any, Dict
from .consensus_engine import ConsensusEngine

class DecisionEngine:
    """
    Top-level Decision Engine wrapping the Hierarchical Consensus Layer.
    Exposes a unified interface to evaluate multi-model outputs.
    """
    def __init__(self):
        self.engine = ConsensusEngine()

    def evaluate(self, 
                 pinn_outputs: Any, 
                 lstm_outputs: Any, 
                 gnn_outputs: Any, 
                 stgnn_outputs: Any) -> Dict[str, Any]:
        """
        Evaluates input from all four cybersecurity/physics systems.
        
        Args:
            pinn_outputs: PINN validation score or dictionary
            lstm_outputs: LSTM prediction or dictionary
            gnn_outputs: GNN criticality scores or dictionary
            stgnn_outputs: ST-GNN forecasting scores or dictionary
            
        Returns:
            Dict containing unified threat_score, confidence_score, and final decision.
        """
        return self.engine.run_consensus(pinn_outputs, lstm_outputs, gnn_outputs, stgnn_outputs)
