import pytest
import time
from core.assistant.reminder_manager import ReminderManager

def test_add_and_tick_reminder():
    # Cooldown of 5 seconds for test convenience
    manager = ReminderManager(spam_cooldown=5.0)
    
    # Add a reminder
    res = manager.add_reminder("Check Bus 5", delay_sec=0.1)
    assert res["status"] == "SCHEDULED"
    assert "reminder_id" in res
    
    # Tick immediately, should not trigger yet
    triggered = manager.tick()
    assert len(triggered) == 0
    
    # Wait and tick, should trigger
    time.sleep(0.15)
    triggered = manager.tick()
    assert len(triggered) == 1
    assert triggered[0]["text"] == "Check Bus 5"
    
    # Check history
    summary = manager.get_status_summary()
    assert summary["total_triggered"] == 1
    assert summary["triggered_history"][0]["text"] == "Check Bus 5"

def test_reminder_spam_cooldown():
    manager = ReminderManager(spam_cooldown=2.0)
    
    # Add first reminder
    res1 = manager.add_reminder("Test Spam", delay_sec=1.0)
    assert res1["status"] == "SCHEDULED"
    
    # Add second with same text immediately, should be blocked
    res2 = manager.add_reminder("Test Spam", delay_sec=1.0)
    assert res2["status"] == "BLOCKED"
    assert res2["reason"] == "cooldown_active"
    
    # Wait out the spam cooldown and register again
    time.sleep(2.1)
    res3 = manager.add_reminder("Test Spam", delay_sec=1.0)
    assert res3["status"] == "SCHEDULED"

def test_cancel_reminder():
    manager = ReminderManager()
    
    res = manager.add_reminder("Cancel Target", delay_sec=5.0)
    rem_id = res["reminder_id"]
    
    assert len(manager.reminders) == 1
    
    # Cancel it
    success = manager.cancel_reminder(rem_id)
    assert success is True
    assert len(manager.reminders) == 0
    
    # Cancel non-existent
    success_none = manager.cancel_reminder("fake_id")
    assert success_none is False

def test_clear_all():
    manager = ReminderManager()
    manager.add_reminder("R1", delay_sec=1.0)
    manager.add_reminder("R2", delay_sec=2.0)
    assert len(manager.reminders) == 2
    
    manager.clear_all()
    assert len(manager.reminders) == 0
    assert len(manager.triggered_history) == 0
