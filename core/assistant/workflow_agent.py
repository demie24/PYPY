import logging
from typing import Dict, Any, List

logger = logging.getLogger("assistant.workflow_agent")

class WorkflowAgent:
    def __init__(self):
        self.agent_name = "WorkflowAgent"
        self.status = "NOMINAL"
        self.confidence_score = 1.0
        self.workflow_alerts: List[Dict[str, Any]] = []
        self.recovery_plans: List[Dict[str, Any]] = []
        self.escalations: List[Dict[str, Any]] = []

    def analyze_workflows(self, workflows_summary: Dict[str, Any], task_chains_summary: Dict[str, Any]) -> Dict[str, Any]:
        """Analyzes active workflows and task chains to check dependency continuity and handle failures."""
        self.workflow_alerts.clear()
        self.recovery_plans.clear()
        self.escalations.clear()

        # 1. Workflow dependency and status analysis
        # workflows_summary typically contains running_workflows, completed_workflows, supported_workflows
        completed = workflows_summary.get("completed_workflows", [])
        
        for w in completed:
            w_name = w.get("workflow_name", "unknown")
            status = w.get("status", "SUCCESS")
            
            if status == "FAILED":
                desc = f"Workflow '{w_name}' didapati GAGAL semasa pelaksanaan."
                self.workflow_alerts.append({"workflow": w_name, "issue": "WORKFLOW_FAILURE", "description": desc, "severity": "HIGH"})
                
                # Propose recovery plan
                self.recovery_plans.append({
                    "action": f"RETRY_WORKFLOW_{w_name.upper()}",
                    "target": w_name,
                    "suggestion": f"Cadangan: Jalankan semula workflow {w_name} selepas memeriksa sambungan API/n8n.",
                    "severity": "HIGH"
                })

        # 2. Automation chain status analysis
        # task_chains_summary contains active_chains_count, active_chains, completed_chains_count, completed_chains, etc.
        completed_chains = task_chains_summary.get("completed_chains", [])
        active_chains = task_chains_summary.get("active_chains", [])

        # Check for failed task chains in completed chains
        for c in completed_chains:
            chain_id = c.get("chain_id", "unknown")
            status = c.get("status", "SUCCESS")
            
            if status == "FAILED":
                desc = f"Task chain {chain_id} gagal."
                self.workflow_alerts.append({"chain": chain_id, "issue": "CHAIN_FAILURE", "description": desc, "severity": "HIGH"})
                self.escalations.append({
                    "type": "AUTOMATION_FAIL_ESCALATION",
                    "target": chain_id,
                    "suggestion": f"Escalation: Task chain {chain_id} gagal. Sila sahkan secara manual status sistem.",
                    "severity": "HIGH"
                })
            elif status == "TIMEOUT":
                desc = f"Task chain {chain_id} mengalami tamat masa (timeout)."
                self.workflow_alerts.append({"chain": chain_id, "issue": "CHAIN_TIMEOUT", "description": desc, "severity": "CRITICAL"})
                self.escalations.append({
                    "type": "AUTOMATION_TIMEOUT_ESCALATION",
                    "target": chain_id,
                    "suggestion": f"Critical Escalation: Task chain {chain_id} sangkut akibat timeout. Operator digesa mengambil alih kawalan manual.",
                    "severity": "CRITICAL"
                })

        # Check for active stalled chains (e.g. running too long > 20s)
        # Assuming we can inspect active chains and see if elapsed time is high
        for c in active_chains:
            chain_id = c.get("chain_id", "unknown")
            elapsed = c.get("elapsed_sec", 0.0)
            if elapsed > 20.0:
                desc = f"Task chain {chain_id} didapati tersekat (stalled) selama {elapsed:.1f} saat."
                self.workflow_alerts.append({"chain": chain_id, "issue": "CHAIN_STALLED", "description": desc, "severity": "CRITICAL"})
                self.escalations.append({
                    "type": "AUTOMATION_STALL_ESCALATION",
                    "target": chain_id,
                    "suggestion": f"Escalation: Task chain {chain_id} tersangkut. Sila reset chain state.",
                    "severity": "CRITICAL"
                })

        # Set status based on findings
        if any(x["severity"] == "CRITICAL" for x in self.workflow_alerts):
            self.status = "CRITICAL_ANOMALY"
            self.confidence_score = 0.80
        elif any(x["severity"] == "HIGH" for x in self.workflow_alerts):
            self.status = "HIGH_ANOMALY"
            self.confidence_score = 0.90
        elif self.workflow_alerts:
            self.status = "DEGRADED"
            self.confidence_score = 0.95
        else:
            self.status = "NOMINAL"
            self.confidence_score = 1.0

        return self.get_status_summary()

    def get_status_summary(self) -> Dict[str, Any]:
        return {
            "agent_name": self.agent_name,
            "status": self.status,
            "confidence_score": round(self.confidence_score, 2),
            "alerts": self.workflow_alerts,
            "recovery_plans": self.recovery_plans,
            "escalations": self.escalations
        }

    def reset_agent(self):
        self.status = "NOMINAL"
        self.confidence_score = 1.0
        self.workflow_alerts.clear()
        self.recovery_plans.clear()
        self.escalations.clear()
