import pytest
from core.assistant.workflow_agent import WorkflowAgent

def test_workflow_agent_initial_state():
    agent = WorkflowAgent()
    summary = agent.get_status_summary()
    assert summary["agent_name"] == "WorkflowAgent"
    assert summary["status"] == "NOMINAL"
    assert summary["confidence_score"] == 1.0
    assert not summary["alerts"]
    assert not summary["recovery_plans"]
    assert not summary["escalations"]

def test_workflow_agent_workflow_failure():
    agent = WorkflowAgent()
    workflows_summary = {
        "completed_workflows": [
            {"workflow_name": "system_status_check", "status": "FAILED"}
        ]
    }
    agent.analyze_workflows(workflows_summary, {})
    assert agent.status == "HIGH_ANOMALY"
    assert len(agent.workflow_alerts) == 1
    assert agent.workflow_alerts[0]["issue"] == "WORKFLOW_FAILURE"
    assert agent.workflow_alerts[0]["workflow"] == "system_status_check"
    
    assert len(agent.recovery_plans) == 1
    assert agent.recovery_plans[0]["action"] == "RETRY_WORKFLOW_SYSTEM_STATUS_CHECK"
    assert "Jalankan semula" in agent.recovery_plans[0]["suggestion"]

def test_workflow_agent_chain_failure():
    agent = WorkflowAgent()
    task_chains_summary = {
        "completed_chains": [
            {"chain_id": "chain_123", "status": "FAILED"}
        ]
    }
    agent.analyze_workflows({}, task_chains_summary)
    assert agent.status == "HIGH_ANOMALY"
    assert len(agent.workflow_alerts) == 1
    assert agent.workflow_alerts[0]["issue"] == "CHAIN_FAILURE"
    
    assert len(agent.escalations) == 1
    assert agent.escalations[0]["type"] == "AUTOMATION_FAIL_ESCALATION"
    assert "manual" in agent.escalations[0]["suggestion"]

def test_workflow_agent_chain_timeout():
    agent = WorkflowAgent()
    task_chains_summary = {
        "completed_chains": [
            {"chain_id": "chain_123", "status": "TIMEOUT"}
        ]
    }
    agent.analyze_workflows({}, task_chains_summary)
    assert agent.status == "CRITICAL_ANOMALY"
    assert len(agent.workflow_alerts) == 1
    assert agent.workflow_alerts[0]["issue"] == "CHAIN_TIMEOUT"
    
    assert len(agent.escalations) == 1
    assert agent.escalations[0]["type"] == "AUTOMATION_TIMEOUT_ESCALATION"
    assert "mengambil alih kawalan manual" in agent.escalations[0]["suggestion"]

def test_workflow_agent_chain_stalled():
    agent = WorkflowAgent()
    task_chains_summary = {
        "active_chains": [
            {"chain_id": "chain_active", "elapsed_sec": 25.0}
        ]
    }
    agent.analyze_workflows({}, task_chains_summary)
    assert agent.status == "CRITICAL_ANOMALY"
    assert len(agent.workflow_alerts) == 1
    assert agent.workflow_alerts[0]["issue"] == "CHAIN_STALLED"
    
    assert len(agent.escalations) == 1
    assert agent.escalations[0]["type"] == "AUTOMATION_STALL_ESCALATION"
    assert "reset chain state" in agent.escalations[0]["suggestion"]

def test_workflow_agent_reset():
    agent = WorkflowAgent()
    workflows_summary = {
        "completed_workflows": [
            {"workflow_name": "system_status_check", "status": "FAILED"}
        ]
    }
    agent.analyze_workflows(workflows_summary, {})
    assert agent.status == "HIGH_ANOMALY"
    
    agent.reset_agent()
    assert agent.status == "NOMINAL"
    assert not agent.workflow_alerts
    assert not agent.recovery_plans
    assert not agent.escalations
