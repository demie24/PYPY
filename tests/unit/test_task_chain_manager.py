import pytest
import time
from core.assistant.task_chain_manager import TaskChainManager

def test_submit_and_tick_nominal():
    manager = TaskChainManager(max_active_chains=3)
    
    plan = {
        "plan_id": "plan_test_123",
        "original_query": "check latency",
        "steps": [
            {
                "step_id": "plan_test_123_s1",
                "objective": "MEASURE_LATENCY",
                "description": "Measure latency",
                "status": "PENDING",
                "dependencies": [],
                "parameters": {}
            },
            {
                "step_id": "plan_test_123_s2",
                "objective": "TRIGGER_WORKFLOW",
                "description": "Trigger status checks",
                "status": "PENDING",
                "dependencies": ["plan_test_123_s1"],
                "parameters": {}
            }
        ]
    }
    
    # Submit
    res = manager.submit_chain(plan)
    assert res["status"] == "SUBMITTED"
    assert len(manager.active_chains) == 1
    
    # Tick callback simulator
    execution_log = []
    def mock_execute_step(chain_id, step):
        execution_log.append(step["objective"])
        return {"status": "SUCCESS"}
        
    # First tick -> starts step 1
    ticks = manager.tick(mock_execute_step, {})
    assert len(execution_log) == 1
    assert execution_log[0] == "MEASURE_LATENCY"
    
    # Second tick -> starts step 2 (since step 1 succeeded)
    ticks = manager.tick(mock_execute_step, {})
    assert len(execution_log) == 2
    assert execution_log[1] == "TRIGGER_WORKFLOW"
    
    # The chain should now be completed and popped to completed list
    assert len(manager.active_chains) == 0
    assert len(manager.completed_chains) == 1
    assert manager.completed_chains[0]["status"] == "COMPLETED"

def test_recursive_chain_prevention():
    manager = TaskChainManager()
    
    plan = {
        "plan_id": "plan_1",
        "original_query": "check latency please",
        "steps": [{"step_id": "p1_s1", "objective": "CHECK", "description": "check", "status": "PENDING", "dependencies": [], "parameters": {}}]
    }
    
    # Submit first time -> accepted
    res1 = manager.submit_chain(plan)
    assert res1["status"] == "SUBMITTED"
    
    # Submit second time with same query -> rejected
    res2 = manager.submit_chain(plan)
    assert res2["status"] == "REJECTED"
    assert res2["error"] == "recursive_chain_prevented"

def test_runaway_chain_prevention():
    manager = TaskChainManager(max_active_chains=2)
    
    p1 = {"plan_id": "p1", "original_query": "q1", "steps": []}
    p2 = {"plan_id": "p2", "original_query": "q2", "steps": []}
    p3 = {"plan_id": "p3", "original_query": "q3", "steps": []}
    
    assert manager.submit_chain(p1)["status"] == "SUBMITTED"
    assert manager.submit_chain(p2)["status"] == "SUBMITTED"
    
    # 3rd active chain is blocked
    res = manager.submit_chain(p3)
    assert res["status"] == "REJECTED"
    assert res["error"] == "runaway_chain_prevention"

def test_chain_step_timeout():
    # 0.1s timeout
    manager = TaskChainManager(step_timeout_sec=0.1)
    
    plan = {
        "plan_id": "plan_timeout",
        "original_query": "check delay",
        "steps": [
            {
                "step_id": "s1",
                "objective": "MEASURE_LATENCY",
                "description": "Measure latency",
                "status": "PENDING",
                "dependencies": [],
                "parameters": {}
            }
        ]
    }
    
    manager.submit_chain(plan)
    
    # Mock executing step returns RUNNING to keep it active
    def mock_execute_running(chain_id, step):
        return {"status": "RUNNING"}
        
    # Start step 1
    manager.tick(mock_execute_running, {})
    assert manager.active_chains["plan_timeout"]["status"] == "EXECUTING"
    
    # Wait for timeout to expire
    time.sleep(0.15)
    
    # Tick again -> should trigger timeout fail
    completed = manager.tick(mock_execute_running, {})
    assert len(completed) == 1
    assert completed[0]["status"] == "TIMEOUT"
    assert len(manager.active_chains) == 0
    assert len(manager.completed_chains) == 1
    assert manager.completed_chains[0]["status"] == "FAILED"
