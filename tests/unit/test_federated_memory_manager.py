import pytest
import time
from core.assistant.federated_memory_manager import FederatedMemoryManager

def test_federated_memory_initial_state():
    mgr = FederatedMemoryManager()
    summary = mgr.get_status_summary()
    assert summary["agent_name"] == "FederatedMemoryManager"
    assert summary["status"] == "NOMINAL"
    assert summary["sync_status"] == "SYNCED"
    assert summary["lamport_clock"] == 0
    assert summary["sync_count"] == 0
    assert not summary["conflict_logs"]

def test_federated_memory_update_local():
    mgr = FederatedMemoryManager()
    mgr.update_local_memory("key1", "val1")
    assert mgr.lamport_clock == 1
    assert mgr.local_memory["key1"]["value"] == "val1"
    assert mgr.shared_memory["key1"]["value"] == "val1"

def test_federated_memory_sync_resolution():
    mgr = FederatedMemoryManager()
    # Populate local key
    mgr.update_local_memory("shared_key", "local_val")
    
    # 1. Sync remote with HIGHER clock (remote should win)
    remote_mem = {
        "shared_key": {"value": "remote_val_newer", "clock": 5, "timestamp": time.time()}
    }
    summary = mgr.synchronize_memory("esp32_node1", remote_mem)
    assert mgr.shared_memory["shared_key"]["value"] == "remote_val_newer"
    assert mgr.lamport_clock == 6 # max(1, 5) + 1
    
    # 2. Sync remote with LOWER clock (local should win, remote ignored)
    remote_mem_older = {
        "shared_key": {"value": "remote_val_older", "clock": 3, "timestamp": time.time()}
    }
    mgr.synchronize_memory("esp32_node1", remote_mem_older)
    assert mgr.shared_memory["shared_key"]["value"] == "remote_val_newer"

def test_federated_memory_sync_tie_resolution():
    mgr = FederatedMemoryManager()
    mgr.update_local_memory("shared_key", "local_val") # clock = 1
    
    # Remote has same clock but newer timestamp
    remote_mem = {
        "shared_key": {"value": "remote_val_winner", "clock": 1, "timestamp": time.time() + 10.0}
    }
    mgr.synchronize_memory("esp32_node1", remote_mem)
    assert mgr.shared_memory["shared_key"]["value"] == "remote_val_winner"

def test_federated_memory_sync_storm_prevention():
    mgr = FederatedMemoryManager()
    mgr.sync_status = "OUT_OF_SYNC"
    mgr.sync_cooldown = 10.0 # set high cooldown
    mgr.last_sync_time = time.time()
    
    # Immediate sync should trigger storm prevention
    summary = mgr.synchronize_memory("esp32_node1", {}, simulation_mode="synchronization_storms")
    assert summary["sync_status"] == "STORM_PREVENTED"
    assert summary["status"] == "STORM_MITIGATED"
    assert len(summary["conflict_logs"]) == 1

def test_federated_memory_reset():
    mgr = FederatedMemoryManager()
    mgr.update_local_memory("k", "v")
    mgr.reset_agent()
    assert mgr.lamport_clock == 0
    assert not mgr.local_memory
    assert not mgr.shared_memory
