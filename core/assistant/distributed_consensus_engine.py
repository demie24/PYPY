import time
import logging
from typing import Dict, Any, List

logger = logging.getLogger("assistant.distributed_consensus_engine")

class DistributedConsensusEngine:
    def __init__(self):
        self.agent_name = "DistributedConsensusEngine"
        self.status = "NOMINAL"
        self.consensus_state = "IDLE"
        self.consensus_score = 1.0
        self.consensus_drift = 0.0
        self.votes: Dict[str, Dict[str, Any]] = {}
        self.drift_history: List[Dict[str, Any]] = []
        self.consensus_logs: List[str] = []

    def arbitrate_consensus(self, node_votes: Dict[str, Dict[str, Any]], simulation_mode: str = None) -> Dict[str, Any]:
        """Arbitrates node votes to calculate consensus confidence and detect consensus drift."""
        self.votes = node_votes
        self.consensus_logs.clear()

        # Handle simulation modes
        if simulation_mode == "consensus_instability":
            self.consensus_state = "BLOCKED (INSTABILITY)"
            self.consensus_score = 0.45
            self.consensus_drift = 0.65
            self._update_drift_history(0.65)
            self.consensus_logs.append("[Consensus]: Blok akibat ketidakstabilan pengundian.")
            self.status = "DEGRADED"
            return self.get_status_summary()

        if simulation_mode == "distributed_drift_escalation":
            self.consensus_state = "BLOCKED (DRIFT)"
            self.consensus_score = 0.35
            self.consensus_drift = 0.85
            self._update_drift_history(0.85)
            self.consensus_logs.append("[Consensus]: Drift eskalasi tinggi dikesan di seluruh grid mesh.")
            self.status = "CRITICAL"
            return self.get_status_summary()

        if simulation_mode == "swarm_consensus_instability":
            self.consensus_state = "BLOCKED (SWARM_INSTABILITY)"
            self.consensus_score = 0.50
            self.consensus_drift = 0.70
            self._update_drift_history(0.70)
            self.consensus_logs.append("[Consensus]: Swarm cognition tidak mencapai persefahaman.")
            self.status = "DEGRADED"
            return self.get_status_summary()

        if not node_votes:
            self.consensus_state = "IDLE"
            self.consensus_score = 1.0
            self.consensus_drift = 0.0
            self._update_drift_history(0.0)
            self.status = "NOMINAL"
            return self.get_status_summary()

        # Consensus score = fraction of nodes in agreement on the winning decision
        decisions = [v.get("decision", "NONE") for v in node_votes.values()]
        decision_counts = {}
        for d in decisions:
            decision_counts[d] = decision_counts.get(d, 0) + 1

        total_nodes = len(node_votes)
        if total_nodes == 0:
            majority_decision = "NONE"
            agreement_ratio = 1.0
        else:
            majority_decision = max(decision_counts, key=decision_counts.get)
            agreement_ratio = decision_counts[majority_decision] / total_nodes

        # Calculate consensus confidence (average of confidence scores of nodes in agreement)
        agreeing_confidences = [
            v.get("confidence", 1.0) for v in node_votes.values() if v.get("decision") == majority_decision
        ]
        mean_confidence = sum(agreeing_confidences) / len(agreeing_confidences) if agreeing_confidences else 1.0
        
        # Combined score = agreement_ratio * mean_confidence
        self.consensus_score = agreement_ratio * mean_confidence

        # Consensus drift: measures standard deviation or range of vote confidence
        all_confidences = [v.get("confidence", 1.0) for v in node_votes.values()]
        if all_confidences:
            avg_conf = sum(all_confidences) / len(all_confidences)
            variance = sum((c - avg_conf) ** 2 for c in all_confidences) / len(all_confidences)
            self.consensus_drift = min(1.0, (variance ** 0.5) * 2.0)  # scale up for visibility
        else:
            self.consensus_drift = 0.0

        self._update_drift_history(self.consensus_drift)

        # Enforce threshold gate: e.g. score >= 0.80 and at least 4/5 (or majority if fewer than 5) agreement
        required_nodes_agree = min(4, total_nodes)
        actual_agree = decision_counts.get(majority_decision, 0)

        # Check for conflicts: e.g. split votes (50/50 or close)
        is_conflict = (len(decision_counts) > 1 and actual_agree <= total_nodes / 2)

        if is_conflict:
            self.consensus_state = "BLOCKED (CONFLICT)"
            self.consensus_logs.append("SEKATAN KONSENSUS: Undian tersekat akibat konflik pengundian 50/50.")
            self.status = "CRITICAL"
        elif self.consensus_drift > 0.40:
            self.consensus_state = "BLOCKED (DRIFT)"
            self.consensus_logs.append(f"SEKATAN KONSENSUS: Drift pengundian ({self.consensus_drift:.2f}) melebihi threshold 0.40.")
            self.status = "DEGRADED"
        elif self.consensus_score < 0.80:
            self.consensus_state = "BLOCKED (LOW_CONFIDENCE)"
            self.consensus_logs.append(f"SEKATAN KONSENSUS: Skor keyakinan {self.consensus_score:.2f} di bawah paras threshold 0.80.")
            self.status = "DEGRADED"
        elif actual_agree < required_nodes_agree:
            self.consensus_state = "BLOCKED (INSUFFICIENT_NODES)"
            self.consensus_logs.append(f"SEKATAN KONSENSUS: Hanya {actual_agree}/{total_nodes} nod bersetuju (min {required_nodes_agree} diperlukan).")
            self.status = "DEGRADED"
        else:
            self.consensus_state = "APPROVED"
            self.consensus_logs.append(f"KONSENSUS DILULUSKAN: Swarm bersetuju dengan tindakan '{majority_decision}' (Skor: {self.consensus_score:.2f}).")
            self.status = "NOMINAL"

        return self.get_status_summary()

    def _update_drift_history(self, drift_val: float):
        self.drift_history.append({
            "timestamp": time.time(),
            "drift": drift_val
        })
        if len(self.drift_history) > 30:
            self.drift_history.pop(0)

    def get_status_summary(self) -> Dict[str, Any]:
        return {
            "agent_name": self.agent_name,
            "status": self.status,
            "consensus_state": self.consensus_state,
            "consensus_score": round(self.consensus_score, 2),
            "consensus_drift": round(self.consensus_drift, 2),
            "votes": self.votes,
            "drift_history": self.drift_history,
            "consensus_logs": self.consensus_logs
        }

    def reset_engine(self):
        self.status = "NOMINAL"
        self.consensus_state = "IDLE"
        self.consensus_score = 1.0
        self.consensus_drift = 0.0
        self.votes.clear()
        self.drift_history.clear()
        self.consensus_logs.clear()
