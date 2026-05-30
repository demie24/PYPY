import pytest
from core.assistant.conversational_planning_engine import ConversationalPlanningEngine

def test_plan_decomposition_latency():
    engine = ConversationalPlanningEngine()
    
    # Target phrase 1: Latency check
    plan = engine.create_plan(
        "check latency lepas tu kalau tinggi trigger recovery workflow",
        {"category": "CHECK_LATENCY", "action": "measure"}
    )
    
    assert plan["status"] == "CREATED"
    assert len(plan["steps"]) == 3
    assert plan["steps"][0]["objective"] == "MEASURE_LATENCY"
    assert plan["steps"][1]["objective"] == "CHECK_LIMIT"
    assert plan["steps"][2]["objective"] == "TRIGGER_WORKFLOW"

def test_plan_decomposition_dashboard():
    engine = ConversationalPlanningEngine()
    
    # Target phrase 2: HMI Dashboard monitor
    plan = engine.create_plan(
        "buka dashboard dan monitor relay sampai stabil",
        {"category": "NAVIGATE", "action": "open_dashboard"}
    )
    
    assert len(plan["steps"]) == 3
    assert plan["steps"][0]["objective"] == "OPEN_DASHBOARD"
    assert plan["steps"][1]["objective"] == "MONITOR_RELAY"
    assert plan["steps"][2]["objective"] == "AWAIT_STABILITY"

def test_runaway_chain_prevention():
    # Set max steps to 2
    engine = ConversationalPlanningEngine(max_steps=2)
    
    plan = engine.create_plan(
        "check latency lepas tu kalau tinggi trigger recovery workflow",
        {"category": "CHECK_LATENCY", "action": "measure"}
    )
    
    # Should truncate from 3 to 2
    assert len(plan["steps"]) == 2
    assert plan["steps"][0]["objective"] == "MEASURE_LATENCY"
    assert plan["steps"][1]["objective"] == "CHECK_LIMIT"

def test_plan_step_status_updates():
    engine = ConversationalPlanningEngine()
    plan = engine.create_plan(
        "check latency lepas tu kalau tinggi trigger recovery workflow",
        {"category": "CHECK_LATENCY", "action": "measure"}
    )
    plan_id = plan["plan_id"]
    
    # Update step 1 to SUCCESS
    success = engine.update_step_status(plan_id, f"{plan_id}_s1", "SUCCESS", "Step 1 completed")
    assert success is True
    assert engine.get_plan(plan_id)["steps"][0]["status"] == "SUCCESS"
    assert engine.get_plan(plan_id)["status"] == "CREATED"
    
    # Update step 2 to FAILED
    success_fail = engine.update_step_status(plan_id, f"{plan_id}_s2", "FAILED", "Step 2 failed limits")
    assert success_fail is True
    # If any step fails, plan transitions to FAILED
    assert engine.active_plans.get(plan_id) is None # popped to history
    assert engine.plan_history[-1]["status"] == "FAILED"
