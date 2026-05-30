import logging
import json
import time
from typing import Dict, Any, List

# Setup logger
logger = logging.getLogger("self_healing.orchestrator_agent")

from core.self_healing.cyber_defense_agent import CyberDefenseAgent
from core.self_healing.restoration_agent import RestorationAgent
from core.self_healing.stabilization_agent import StabilizationAgent
from core.self_healing.survival_agent import SurvivalAgent
from core.self_healing.prediction_agent import PredictionAgent

class OrchestratorAgent:
    """
    Coordinates specialized AI agents, runs consensus voting, resolves conflicts,
    manages dynamic coordination weights and agent trust.
    """
    def __init__(self, fsm=None, memory=None, guard=None):
        self.agent_name = "OrchestratorAgent"
        self.agents = {
            "CyberDefenseAgent": CyberDefenseAgent(),
            "RestorationAgent": RestorationAgent(fsm=fsm, memory=memory),
            "StabilizationAgent": StabilizationAgent(),
            "SurvivalAgent": SurvivalAgent(guard=guard),
            "PredictionAgent": PredictionAgent()
        }

        # Initialize trust scores (nominal = 1.0)
        self.agent_trust = {name: 1.0 for name in self.agents.keys()}
        # Initialize dynamic weights
        self.agent_weights = {name: 1.0 for name in self.agents.keys()}
        
        # Conflict registry & active locks
        self.active_lockdowns = set()
        self.proposal_history = []

    def update_dynamic_weights(self, context: Dict[str, Any]):
        """
        Dynamically adjusts agent voting weights based on active grid state.
        """
        active_attack = context.get("active_attack")
        avg_freq = context.get("avg_freq", 60.0)
        stability_score = context.get("stability_score", 100.0)

        # Reset weights to nominal
        for name in self.agents.keys():
            self.agent_weights[name] = 1.0

        # Cyber attack escalation
        if active_attack:
            self.agent_weights["CyberDefenseAgent"] = 2.5
            logger.info("Dynamic Weights Coordination: Active attack detected. Scaled CyberDefenseAgent weight to 2.5")

        # Stability/Frequency collapse escalation
        if stability_score < 70.0 or avg_freq < 59.5:
            self.agent_weights["StabilizationAgent"] = 2.0
            self.agent_weights["SurvivalAgent"] = 2.0
            logger.info("Dynamic Weights Coordination: Grid stress/low stability detected. Scaled StabilizationAgent and SurvivalAgent weights to 2.0")

    def adapt_trust(self, rolled_back_sequence: List[Dict[str, Any]] = None, safety_violation_cmd: Dict[str, Any] = None, success_sequence: List[Dict[str, Any]] = None):
        """
        Adapts trust scores statefully based on step outcomes.
        """
        # 1. Penalize on rollback
        if rolled_back_sequence:
            for step in rolled_back_sequence:
                source = step.get("source", "")
                # Map source to agent name
                agent_name = self._map_source_to_agent(source)
                if agent_name:
                    old_trust = self.agent_trust[agent_name]
                    self.agent_trust[agent_name] = max(0.1, old_trust - 0.2)
                    logger.warning(f"Trust Adjustment: Rollback occurred. Penalized {agent_name} trust: {old_trust:.2f} -> {self.agent_trust[agent_name]:.2f}")
            # RestorationAgent is also penalized if a sequence fails
            self.agent_trust["RestorationAgent"] = max(0.1, self.agent_trust["RestorationAgent"] - 0.1)

        # 2. Penalize on safety violation
        if safety_violation_cmd:
            source = safety_violation_cmd.get("source", "")
            agent_name = self._map_source_to_agent(source)
            if agent_name:
                old_trust = self.agent_trust[agent_name]
                self.agent_trust[agent_name] = max(0.1, old_trust - 0.15)
                logger.warning(f"Trust Adjustment: Safety violation occurred. Penalized {agent_name} trust: {old_trust:.2f} -> {self.agent_trust[agent_name]:.2f}")

        # 3. Reward on successful restoration
        if success_sequence:
            # Reward RestorationAgent
            self.agent_trust["RestorationAgent"] = min(1.0, self.agent_trust["RestorationAgent"] + 0.05)
            # Reward all other agents slightly for successful cooperation
            for name in self.agents.keys():
                if name != "RestorationAgent":
                    self.agent_trust[name] = min(1.0, self.agent_trust[name] + 0.02)
            logger.info("Trust Adjustment: Restoration sequence successful. Rewarded agent trust levels.")

    def _map_source_to_agent(self, source: str) -> str:
        if "cyber" in source.lower() or source == "DEFENSE":
            return "CyberDefenseAgent"
        elif "restore" in source.lower() or source in ["FLISR", "BLACKSTART_ENGINE"]:
            return "RestorationAgent"
        elif "stabil" in source.lower() or source == "AUTONOMOUS_BALANCER":
            return "StabilizationAgent"
        elif "surviv" in source.lower():
            return "SurvivalAgent"
        elif "predict" in source.lower():
            return "PredictionAgent"
        return None

    def evaluate_and_publish(self, telemetry: Dict[str, Any], client) -> List[Dict[str, Any]]:
        """
        Coordinates evaluations, executes consensus voting, arbitrates conflicts, and publishes topics.
        """
        if not telemetry:
            return []

        timestamp_ms = int(time.time() * 1000)
        
        # 1. Run individual evaluations
        agent_evals = {}
        all_proposals = []
        confidences = {}

        for name, agent in self.agents.items():
            res = agent.evaluate(telemetry)
            agent_evals[name] = res
            confidences[name] = res.get("confidence", 1.0)
            
            # Collect proposals and tag source agent name
            for p in res.get("proposals", []):
                p["source_agent"] = name
                all_proposals.append(p)

        # 2. Build consensus context
        state_data = telemetry.get("state", {})
        buses = state_data.get("buses", {})
        lines = state_data.get("lines", {})
        
        # Compute avg frequency and voltage deviation for voting context
        avg_freq = 60.0
        freq_count = 0
        v_dev_sum = 0.0
        v_count = 0
        for b_data in buses.values():
            if "frequency_hz" in b_data:
                avg_freq = min(avg_freq, b_data["frequency_hz"])
            v = b_data.get("voltage_pu", 1.0)
            if v > 0.0:
                v_dev_sum += abs(1.0 - v)
                v_count += 1
        avg_v_dev = v_dev_sum / v_count if v_count > 0 else 0.0

        ai_orchestrator_summary = telemetry.get("ai_prediction", {}) # placeholder
        stability_score = telemetry.get("ai_orchestrator", {}).get("stability_score", 100.0)

        context = {
            "telemetry": telemetry,
            "active_attack": telemetry.get("attack_status", {}).get("active_attack"),
            "collapsed": agent_evals["RestorationAgent"].get("collapsed", False),
            "avg_freq": avg_freq,
            "avg_v_dev": avg_v_dev,
            "stability_score": stability_score,
            "predicted_overloads": agent_evals["PredictionAgent"].get("predicted_overloads", []),
            "collapse_probability": agent_evals["PredictionAgent"].get("collapse_probability", 0.0),
            "success_probability": agent_evals["PredictionAgent"].get("success_probability", 100.0)
        }

        # 3. Dynamic weights coordination
        self.update_dynamic_weights(context)

        # 4. Consensus Voting on Proposals
        consensus_results = []
        approved_proposals = []
        conflicts = []

        # Deduplicate proposals by command + target
        unique_proposals = []
        seen_proposals = set()
        for p in all_proposals:
            key = (p["command"], p["target"])
            if key not in seen_proposals:
                seen_proposals.add(key)
                unique_proposals.append(p)

        # Handle active lockdowns from CyberDefense proposals
        new_lockdowns = set()
        for p in unique_proposals:
            if p["command"] == "LOCKDOWN_BREAKER":
                new_lockdowns.add(p["target"])
        self.active_lockdowns = new_lockdowns

        for p in unique_proposals:
            vote_res = self.vote_on_proposal(p, context)
            consensus_results.append(vote_res)
            
            if vote_res["approved"]:
                # Check for active cyber lockdown conflict before execution approval
                if p["target"] in self.active_lockdowns and p["command"] in ["CLOSE", "RECONNECT_LINE", "REROUTE_FLOW"]:
                    conflicts.append({
                        "proposal": p,
                        "type": "CYBER_LOCKDOWN_CONFLICT",
                        "arbitration": f"Vetoed Close command on {p['target']} because the node is under active cyber lockdown."
                    })
                    vote_res["approved"] = False
                    vote_res["reason"] = "Arbitrated: Blocked by active cyber lockdown."
                else:
                    approved_proposals.append(p)

        # 5. Distributed States classification
        distributed_state = "STANDBY"
        active_coordination_mode = "NOMINAL"

        if context["active_attack"]:
            distributed_state = "LOCKDOWN"
            active_coordination_mode = "CYBER_PRESERVATION"
        elif context["stability_score"] < 70.0 or context["avg_freq"] < 59.5:
            distributed_state = "CONSENSUS_STABILIZING"
            active_coordination_mode = "PHYSICAL_PRESERVATION"
        elif len(approved_proposals) > 0:
            distributed_state = "COOPERATIVE_RECOVERY"
            active_coordination_mode = "NOMINAL"

        # 6. Publish MQTT payloads
        # Topic 1: grid/l6_agents
        agents_list = []
        for name in self.agents.keys():
            agents_list.append({
                "agent_name": name,
                "confidence": confidences[name],
                "trust": round(self.agent_trust[name], 2),
                "weight": self.agent_weights[name]
            })
        
        client.publish("grid/l6_agents", json.dumps({
            "timestamp": timestamp_ms,
            "agents": agents_list,
            "proposals": unique_proposals
        }))

        # Topic 2: grid/l6_agent_consensus
        client.publish("grid/l6_agent_consensus", json.dumps({
            "timestamp": timestamp_ms,
            "consensus_results": consensus_results
        }))

        # Topic 3: grid/l6_agent_conflicts
        client.publish("grid/l6_agent_conflicts", json.dumps({
            "timestamp": timestamp_ms,
            "conflicts": conflicts
        }))

        # Topic 4: grid/l6_distributed_state
        client.publish("grid/l6_distributed_state", json.dumps({
            "timestamp": timestamp_ms,
            "distributed_state": distributed_state,
            "active_coordination_mode": active_coordination_mode
        }))

        # Topic 5: grid/l6_agent_confidence
        client.publish("grid/l6_agent_confidence", json.dumps({
            "timestamp": timestamp_ms,
            "confidences": confidences
        }))

        # Return approved actions for execution
        return approved_proposals

    def vote_on_proposal(self, proposal: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Coordinates voting for a single proposal.
        """
        # Normalize command (e.g. CLOSED -> CLOSE, OPENED -> OPEN)
        norm_cmd = proposal.get("command", "")
        if norm_cmd == "CLOSED":
            norm_cmd = "CLOSE"
        elif norm_cmd == "OPENED":
            norm_cmd = "OPEN"
        
        normalized_proposal = proposal.copy()
        normalized_proposal["command"] = norm_cmd

        votes = {}
        total_weighted_vote = 0.0
        total_weight = 0.0
        has_veto = False
        vetoed_by = []

        for name, agent in self.agents.items():
            vote = agent.vote(normalized_proposal, context)
            weight = self.agent_weights.get(name, 1.0)
            trust = self.agent_trust.get(name, 1.0)
            
            votes[name] = {
                "vote": vote,
                "weight": weight,
                "trust": trust
            }

            if vote == -1.0:
                has_veto = True
                vetoed_by.append(name)
            
            # Compute dynamic weighted vote
            total_weighted_vote += vote * weight * trust
            total_weight += weight

        consensus_score = (total_weighted_vote / total_weight) if total_weight > 0 else 0.0
        
        # Proposal approved if:
        # (a) weighted score >= 0.15 and no vetoes are present, OR
        # (b) the score is >= 0.0, there are no vetoes, and the grid is completely nominal (no active attack and stability >= 90).
        is_nominal = (context.get("active_attack") is None) and (context.get("stability_score", 100.0) >= 90.0)
        approved = (consensus_score >= 0.15 or (consensus_score >= 0.0 and is_nominal)) and not has_veto

        return {
            "proposal": proposal,
            "votes": votes,
            "consensus_score": round(consensus_score, 2),
            "has_veto": has_veto,
            "vetoed_by": vetoed_by,
            "approved": approved
        }
