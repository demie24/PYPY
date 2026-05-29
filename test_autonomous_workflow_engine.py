import pytest
import time
from core.assistant.autonomous_workflow_engine import AutonomousWorkflowEngine

def test_workflow_cooldown():
    # Cooldown of 2 seconds
    engine = AutonomousWorkflowEngine(workflow_cooldown=2.0)
    
    def mock_step_fn(wf, step):
        return {"status": "SUCCESS"}
        
    # First execution succeeds
    res1 = engine.execute_workflow("system_status_check", {}, mock_step_fn)
    assert res1["status"] == "SUCCESS"
    
    # Second execution immediately fails with cooldown
    res2 = engine.execute_workflow("system_status_check", {}, mock_step_fn)
    assert res2["status"] == "FAILED"
    assert res2["error"] == "cooldown_active"
    
    # Wait out the cooldown and try again
    time.sleep(2.1)
    res3 = engine.execute_workflow("system_status_check", {}, mock_step_fn)
    assert res3["status"] == "SUCCESS"

def test_recursive_loop_prevention():
    engine = AutonomousWorkflowEngine(workflow_cooldown=0.0)
    
    # Define a step function that recursively calls execute_workflow again!
    def recursive_step_fn(wf, step):
        if step == "nominal_step":
            # Attempt to recursively enter same workflow
            return engine.execute_workflow("recursive_wf", {}, recursive_step_fn)
        return {"status": "SUCCESS"}
        
    # Execute workflow that runs the recursive step function
    # The engine should detect that "recursive_wf" is in active_call_stack and return recursive_loop_prevented status
    engine.active_call_stack.append("recursive_wf") # simulate active running
    res = engine.execute_workflow("recursive_wf", {}, recursive_step_fn)
    assert res["status"] == "FAILED"
    assert res["error"] == "recursive_loop_prevented"
    engine.active_call_stack.pop()

def test_max_call_depth_exceeded():
    engine = AutonomousWorkflowEngine(workflow_cooldown=0.0, max_call_depth=3)
    
    # Simulate a deep call stack
    engine.active_call_stack.extend(["wf_1", "wf_2", "wf_3"])
    
    def mock_step_fn(wf, step):
        return {"status": "SUCCESS"}
        
    res = engine.execute_workflow("wf_4", {}, mock_step_fn)
    assert res["status"] == "FAILED"
    assert res["error"] == "max_depth_exceeded"
    
    engine.active_call_stack.clear()

def test_confidence_gate():
    engine = AutonomousWorkflowEngine(workflow_cooldown=0.0)
    
    def mock_step_fn(wf, step):
        return {"status": "SUCCESS"}
        
    # Critical workflow (emergency_load_shed) requires threat confidence >= 0.50
    # Case A: Low confidence (0.40) -> REJECTED
    grid_state_low = {"threat": {"confidence": 0.40}}
    res_low = engine.execute_workflow("emergency_load_shed", grid_state_low, mock_step_fn)
    assert res_low["status"] == "FAILED"
    assert res_low["error"] == "Confidence score too low (less than 0.50). Load shed rejected."
    
    # Case B: Sufficient confidence (0.60) -> SUCCESS
    grid_state_high = {"threat": {"confidence": 0.60}}
    res_high = engine.execute_workflow("emergency_load_shed", grid_state_high, mock_step_fn)
    assert res_high["status"] == "SUCCESS"

def test_schedule_and_tick_delayed_tasks():
    engine = AutonomousWorkflowEngine()
    
    task_fired = False
    payload_received = None
    
    def mock_callback(payload):
        nonlocal task_fired, payload_received
        task_fired = True
        payload_received = payload
        return "callback_success"
        
    # Schedule task
    task_id = engine.schedule_delayed_task(
        name="delayed_status",
        delay_sec=0.05,
        callback=mock_callback,
        payload={"param": 123}
    )
    
    assert task_id.startswith("task_")
    assert len(engine.delayed_tasks) == 1
    
    # Tick immediately - should not fire
    triggered = engine.tick()
    assert len(triggered) == 0
    assert not task_fired
    
    # Wait for delay and tick
    time.sleep(0.06)
    triggered = engine.tick()
    assert len(triggered) == 1
    assert triggered[0]["task_id"] == task_id
    assert triggered[0]["result"] == "callback_success"
    assert task_fired
    assert payload_received == {"param": 123}
    assert len(engine.delayed_tasks) == 0
