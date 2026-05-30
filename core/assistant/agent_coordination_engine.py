import time
import logging
from typing import Dict, Any, List, Optional
from core.assistant.telemetry_agent import TelemetryAgent
from core.assistant.relay_agent import RelayAgent
from core.assistant.workflow_agent import WorkflowAgent
from core.assistant.security_agent import SecurityAgent

logger = logging.getLogger("assistant.coordination")

class AgentCoordinationEngine:
    def __init__(self, telemetry_agent: TelemetryAgent, relay_agent: RelayAgent, workflow_agent: WorkflowAgent, security_agent: SecurityAgent):
        self.agent_name = "AgentCoordinationEngine"
        self.telemetry_agent = telemetry_agent
        self.relay_agent = relay_agent
        self.workflow_agent = workflow_agent
        self.security_agent = security_agent
        
        self.status = "NOMINAL"
        self.consensus_state = "IDLE"
        self.consensus_score = 1.0
        self.delegation_chain: List[str] = []
        self.inter_agent_logs: List[str] = []
        
        # Simulation override targets
        self.simulation_mode: Optional[str] = None
        self.last_update_time = time.time()

    def coordinate_agents(
        self,
        telemetry: Dict[str, Any],
        sync_states: Dict[str, Any],
        relay_summary: Dict[str, Any],
        workflows_summary: Dict[str, Any],
        task_chains_summary: Dict[str, Any],
        threat_summary: Dict[str, Any],
        active_attacks: List[str]
    ) -> Dict[str, Any]:
        """Ticks all individual agents and runs multi-agent coordination, delegation, and consensus checking."""
        self.inter_agent_logs.clear()
        self.delegation_chain.clear()
        
        # 1. Run individual specialized agent analyses
        t_sum = self.telemetry_agent.analyze_telemetry(telemetry, sync_states)
        r_sum = self.relay_agent.analyze_relays(relay_summary, threat_summary.get("confidence", 1.0))
        w_sum = self.workflow_agent.analyze_workflows(workflows_summary, task_chains_summary)
        s_sum = self.security_agent.analyze_security(threat_summary, active_attacks)

        # 2. Multi-Agent Delegation Flow Simulation & Protection
        # We start delegation at TelemetryAgent -> RelayAgent -> SecurityAgent -> WorkflowAgent
        depth = 0
        current_agent = "TelemetryAgent"
        self.delegation_chain.append(current_agent)
        
        # Simulate active anomalies cascading delegation
        if t_sum["anomalies"]:
            # Telemetry flags issues -> asks RelayAgent to verify breakers
            depth += 1
            self.inter_agent_logs.append("[TelemetryAgent ➔ RelayAgent]: Sila periksa status fizikal breaker bagi anomali voltan/beban.")
            self.delegation_chain.append("RelayAgent")
            
            if r_sum["anomalies"]:
                # Relay flags chattering/high wear -> asks SecurityAgent to analyze threat correlation
                depth += 1
                self.inter_agent_logs.append("[RelayAgent ➔ SecurityAgent]: Sila sahkan sama ada kerosakan breaker berpunca daripada serangan siber.")
                self.delegation_chain.append("SecurityAgent")
                
                if s_sum["threat_alerts"]:
                    # Security flags active attack -> asks WorkflowAgent to execute containment
                    depth += 1
                    self.inter_agent_logs.append("[SecurityAgent ➔ WorkflowAgent]: Sila mulakan pelan pemulihan kuarantin port dan sekat arahan automatik.")
                    self.delegation_chain.append("WorkflowAgent")

        # Handle simulation overrides
        if self.simulation_mode == "conflicting_recommendations":
            # Relay recommends LOCKOUT, Security recommends KEEP_ONLINE
            self.inter_agent_logs.append("SIMULASI KONFLIK: RelayAgent mengesyorkan LOCKOUT, SecurityAgent mengesyorkan MONITOR (tiada lockout).")
        elif self.simulation_mode == "delegation_timeout":
            self.inter_agent_logs.append("[Orchestrator]: Delegation tamat masa (timeout) dikesan semasa menunggu maklum balas SecurityAgent.")
        elif self.simulation_mode == "cascading_failures":
            # Simulate infinite delegation loop
            depth = 5 # Force exceed depth
            self.inter_agent_logs.append("PENCETUS CASCADE: Rangkaian delegasi berturutan dikesan.")
            
        # Recursive Agent Loop check: enforce maximum delegation depth of 3
        if depth > 3:
            self.inter_agent_logs.append("ALARM: Delegasi melepasi had kedalaman maksimum (kedalaman > 3). Menghentikan lingkaran delegasi automatik!")
            self.status = "LOOP_PREVENTED"
            self.consensus_state = "BLOCKED (LOOP_PREVENTED)"
            self.consensus_score = 0.0
            return self.get_status_summary()

        # 3. Consensus Arbitration Logic
        recs_count = len(r_sum["recommendations"]) + len(s_sum["recommendations"]) + len(w_sum["recovery_plans"])
        
        if self.simulation_mode == "conflicting_recommendations":
            self.consensus_state = "BLOCKED (CONFLICT)"
            self.consensus_score = 0.40
        elif self.simulation_mode == "consensus_instability":
            self.consensus_state = "BLOCKED (INSTABILITY)"
            self.consensus_score = 0.55
        elif recs_count > 0:
            # Calculate average confidence of the active agents
            active_confidences = []
            if t_sum["status"] != "NOMINAL":
                active_confidences.append(t_sum["confidence_score"])
            if r_sum["status"] != "NOMINAL":
                active_confidences.append(r_sum["confidence_score"])
            if w_sum["status"] != "NOMINAL":
                active_confidences.append(w_sum["confidence_score"])
            if s_sum["status"] != "NOMINAL":
                active_confidences.append(s_sum["confidence_score"])
                
            mean_conf = sum(active_confidences) / len(active_confidences) if active_confidences else 1.0
            self.consensus_score = mean_conf
            
            # Enforce consensus checks
            # Critical suggestions require at least average confidence >= 0.75
            if self.consensus_score >= 0.75:
                self.consensus_state = "APPROVED"
                self.inter_agent_logs.append(f"KONSENSUS: Cadangan dipersetujui dengan skor keyakinan {self.consensus_score:.2f}.")
            else:
                self.consensus_state = "BLOCKED (LOW_CONFIDENCE)"
                self.inter_agent_logs.append(f"SEKATAN KONSENSUS: Skor keyakinan {self.consensus_score:.2f} di bawah paras threshold 0.75.")
        else:
            self.consensus_state = "IDLE"
            self.consensus_score = 1.0

        # Determine agent coordination global status
        agent_statuses = [t_sum["status"], r_sum["status"], w_sum["status"], s_sum["status"]]
        if "CRITICAL_ANOMALY" in agent_statuses:
            self.status = "CRITICAL"
        elif "HIGH_ANOMALY" in agent_statuses:
            self.status = "HIGH"
        elif "DEGRADED" in agent_statuses:
            self.status = "DEGRADED"
        else:
            self.status = "NOMINAL"

        return self.get_status_summary()

    def handle_query(self, query: str) -> Optional[str]:
        """Resolves natural language queries in Malay relating to multi-agent status, drift, and recovery plans."""
        q = query.lower().strip()
        
        # 1. "agent mana detect masalah paling kritikal"
        if "agent mana detect masalah paling kritikal" in q or "ejen mana paling kritikal" in q or "ejen paling problem" in q:
            statuses = {
                "TelemetryAgent": self.telemetry_agent.status,
                "RelayAgent": self.relay_agent.status,
                "WorkflowAgent": self.workflow_agent.status,
                "SecurityAgent": self.security_agent.status
            }
            worst_agent = None
            max_severity = -1
            severity_map = {"CRITICAL_ANOMALY": 3, "HIGH_ANOMALY": 2, "DEGRADED": 1, "NOMINAL": 0}
            
            for agent, stat in statuses.items():
                sev = severity_map.get(stat, 0)
                if sev > max_severity:
                    max_severity = sev
                    worst_agent = agent
                    
            if max_severity > 0:
                return f"Ejen yang mengesan masalah paling kritikal sekarang ialah {worst_agent} dengan status {statuses[worst_agent]}."
            else:
                return "Semua ejen AI melaporkan keadaan grid dalam status NOMINAL."

        # 2. "buat coordinated recovery plan"
        if "buat coordinated recovery plan" in q or "coordinated recovery plan" in q or "pelan pemulihan" in q:
            recs = []
            # Gather recommendations from agents
            for r in self.relay_agent.stabilization_recommendations:
                if not r.get("blocked", False):
                    recs.append(f"- Breaker: {r['suggestion']}")
            for s in self.security_agent.safety_recommendations:
                if not s.get("blocked", False):
                    recs.append(f"- Keselamatan: {s['suggestion']}")
            for w in self.workflow_agent.recovery_plans:
                recs.append(f"- Automasi: {w['suggestion']}")
                
            if recs:
                plan_str = "\n".join(recs)
                return (
                    f"Coordinated Recovery Plan yang dirangka oleh ejen AI:\n{plan_str}\n"
                    f"Status Konsensus Ejen: {self.consensus_state} (Skor: {self.consensus_score:.2f}). "
                    "Nota: Tindakan pemulihan memerlukan pengesahan manual operator SCADA."
                )
            else:
                return "Keadaan grid stabil. Tiada Coordinated Recovery Plan perlu dibina sekarang."

        # 3. "relay agent report status"
        if "relay agent report status" in q or "status relay agent" in q or "ejen relay status" in q:
            anom_count = len(self.relay_agent.relay_anomalies)
            rec_count = len(self.relay_agent.stabilization_recommendations)
            return (
                f"Laporan RelayAgent: Status adalah {self.relay_agent.status}. "
                f"Terdapat {anom_count} anomali breaker dikesan dan {rec_count} cadangan penyelesaian dibuat."
            )

        # 4. "telemetry agent summarize drift"
        if "telemetry agent summarize drift" in q or "drift telemetry agent" in q or "laporan drift" in q:
            summary = self.telemetry_agent.drift_summary
            if summary:
                return (
                    f"Ringkasan Drift TelemetryAgent: {summary['description']}. "
                    f"Drift tertinggi dikesan: {summary.get('max_drift_ms', 0.0):.1f}ms pada {summary.get('max_drift_node')}."
                )
            return "Laporan drift belum tersedia dari TelemetryAgent."

        # 5. "security agent analyze anomaly"
        if "security agent analyze anomaly" in q or "analisis security agent" in q or "security agent lapor" in q:
            alerts = self.security_agent.threat_alerts
            if alerts:
                alerts_str = ", ".join([f"{a['type']} ({a['severity']})" for a in alerts])
                return (
                    f"Analisis SecurityAgent: Status adalah {self.security_agent.status}. "
                    f"Ancaman dikesan: {alerts_str}. Cadangan penolakan arahan/kuarantin dikuatkuasakan."
                )
            return "SecurityAgent melaporkan tiada sebarang ancaman dikesan."

        return None

    def get_status_summary(self) -> Dict[str, Any]:
        return {
            "agent_name": self.agent_name,
            "status": self.status,
            "consensus_state": self.consensus_state,
            "consensus_score": round(self.consensus_score, 2),
            "delegation_chain": self.delegation_chain,
            "inter_agent_logs": self.inter_agent_logs,
            "telemetry_agent": self.telemetry_agent.get_status_summary(),
            "relay_agent": self.relay_agent.get_status_summary(),
            "workflow_agent": self.workflow_agent.get_status_summary(),
            "security_agent": self.security_agent.get_status_summary()
        }

    def reset_engine(self):
        self.status = "NOMINAL"
        self.consensus_state = "IDLE"
        self.consensus_score = 1.0
        self.delegation_chain.clear()
        self.inter_agent_logs.clear()
        self.simulation_mode = None
        self.telemetry_agent.reset_agent()
        self.relay_agent.reset_agent()
        self.workflow_agent.reset_agent()
        self.security_agent.reset_agent()
