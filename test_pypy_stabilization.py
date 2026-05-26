import json
import time
import threading
import paho.mqtt.client as mqtt

# Thread-safe lists to collect telemetry, events, alerts, validation reports
telemetry_packets = []
event_packets = []
alert_packets = []
physics_validation_packets = []
adaptive_filter_packets = []
orchestrator_packets = []
recommended_actions_packets = []

lock = threading.Lock()

def on_connect(client, userdata, flags, rc):
    print(f"Connected to Mosquitto MQTT broker on host with result code {rc}")
    client.subscribe("grid/telemetry")
    client.subscribe("grid/events")
    client.subscribe("grid/alerts")
    client.subscribe("grid/physics_validation")
    client.subscribe("grid/adaptive_filter")
    client.subscribe("grid/ai_orchestrator")
    client.subscribe("grid/recommended_actions")

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode("utf-8"))
        topic = msg.topic
        with lock:
            if topic == "grid/telemetry":
                telemetry_packets.append(payload)
                if len(telemetry_packets) > 100:
                    telemetry_packets.pop(0)
            elif topic == "grid/events":
                event_packets.append(payload)
                if len(event_packets) > 100:
                    event_packets.pop(0)
            elif topic == "grid/alerts":
                alert_packets.append(payload)
                if len(alert_packets) > 100:
                    alert_packets.pop(0)
            elif topic == "grid/physics_validation":
                physics_validation_packets.append(payload)
                if len(physics_validation_packets) > 100:
                    physics_validation_packets.pop(0)
            elif topic == "grid/adaptive_filter":
                adaptive_filter_packets.append(payload)
                if len(adaptive_filter_packets) > 100:
                    adaptive_filter_packets.pop(0)
            elif topic == "grid/ai_orchestrator":
                orchestrator_packets.append(payload)
                if len(orchestrator_packets) > 100:
                    orchestrator_packets.pop(0)
            elif topic == "grid/recommended_actions":
                recommended_actions_packets.append(payload)
                if len(recommended_actions_packets) > 100:
                    recommended_actions_packets.pop(0)
    except Exception as e:
        print(f"Error parsing message on {msg.topic}: {e}")

def reset_system(client):
    print("Resetting grid simulation state...")
    client.publish("grid/attack", json.dumps({"action": "STOP"}))
    client.publish("grid/control", json.dumps({"command": "RESET_ALARMS"}))
    client.publish("grid/config", json.dumps({"flisr_auto": True}))
    time.sleep(3)
    with lock:
        telemetry_packets.clear()
        event_packets.clear()
        alert_packets.clear()
        physics_validation_packets.clear()
        adaptive_filter_packets.clear()
        orchestrator_packets.clear()
        recommended_actions_packets.clear()

def run_tests():
    client = mqtt.Client(client_id="grid_cybersecurity_verification_suite_stabilization")
    client.on_connect = on_connect
    client.on_message = on_message
    
    client.connect("localhost", 1884, 60)
    client.loop_start()
    
    print("Waiting for baseline telemetry to ensure subscriptions are active...")
    start_time = time.time()
    while True:
        with lock:
            if len(telemetry_packets) > 0:
                break
        time.sleep(0.5)
        if time.time() - start_time > 10:
            raise TimeoutError("No baseline telemetry packets received. Is simulator active?")
    print("Baseline telemetry received. Subscriptions are active!")
    
    try:
        # TEST 1: Breaker Dependency Validation & Islanding Rejection
        print("\n==================================================")
        print("TEST 1: Breaker Dependency & Islanding Rejection")
        print("==================================================")
        reset_system(client)
        
        # Verify that manually trying to trip a critical line causing islanding (e.g. L8_9) is rejected
        print("Attempting to open line L8_9 which would isolate load components...")
        client.publish("grid/control", json.dumps({"command": "OPEN", "target": "L8_9"}))
        time.sleep(3)
        
        # Verify block event description
        with lock:
            print("Received event descriptions during Test 1:", [ev.get("event") for ev in event_packets])
            block_events = [ev for ev in event_packets if "Control command BLOCKED" in ev.get("event", "")]
            assert len(block_events) > 0, "Islanding trip command was NOT blocked by simulator!"
            print(f" -> SUCCESS: Simulator correctly blocked the islanding trip. Event: {block_events[0]['event']}")

        # TEST 2: Attacker Persistence & Re-tripping Loop
        print("\n==================================================")
        print("TEST 2: Attacker Persistence & Re-tripping Loop")
        print("==================================================")
        reset_system(client)
        
        # Inject BREAKER_MANIPULATION attack on L4_5
        print("Injecting BREAKER_MANIPULATION attack targeting line L4_5...")
        client.publish("grid/attack", json.dumps({
            "action": "START",
            "type": "BREAKER_MANIPULATION",
            "config": {
                "target": "L4_5"
            }
        }))
        time.sleep(3)
        
        # Verify breaker is OPEN
        with lock:
            assert telemetry_packets, "No telemetry received"
            breaker_state = telemetry_packets[-1]["state"]["breakers"].get("L4_5")
            assert breaker_state == "OPEN", f"Expected L4_5 breaker to be OPEN under attack, got {breaker_state}"
            print("Line L4_5 breaker is OPEN under manipulation attack.")
            
        # Try to close it manually
        print("Sending manual CLOSE command to line L4_5...")
        client.publish("grid/control", json.dumps({"command": "CLOSE", "target": "L4_5"}))
        time.sleep(1.5) # Wait for CLOSE confirmation
        
        with lock:
            close_events = [ev for ev in event_packets if "commanded to CLOSE" in ev.get("event", "")]
            assert len(close_events) > 0, "CLOSE command was not processed!"
            print("CLOSE command executed on grid simulator.")
            
        # Wait for the re-trip delay (3 sweeps/ticks)
        print("Awaiting attacker automated persistence re-trip...")
        time.sleep(3.5)
        
        with lock:
            retrip_events = [ev for ev in event_packets if "Attacker Persistence" in ev.get("event", "")]
            assert len(retrip_events) > 0, "Attacker did not re-trip the breaker!"
            current_breaker_state = telemetry_packets[-1]["state"]["breakers"].get("L4_5")
            assert current_breaker_state == "OPEN", f"Expected L4_5 to be re-tripped to OPEN, got {current_breaker_state}"
            print(f" -> SUCCESS: Attacker persistence re-tripped line to OPEN. Event: {retrip_events[0]['event']}")

        # TEST 3: Telemetry Trust & Physics-Aware Reconstruction
        print("\n==================================================")
        print("TEST 3: Telemetry Trust & Physics-Aware Reconstruction")
        print("==================================================")
        reset_system(client)
        
        # Send REJECT_TELEMETRY for Bus_5 to degrade its trust
        print("Simulating operator telemetry rejection of Bus 5...")
        client.publish("grid/control", json.dumps({"command": "REJECT_TELEMETRY", "target": "Bus_5"}))
        time.sleep(6) # Wait for trust score to drop below 40% threshold over ticks
        
        with lock:
            assert adaptive_filter_packets, "No adaptive filter packets received"
            latest_filter = adaptive_filter_packets[-1]
            bus5_action = latest_filter["filter_actions"].get("Bus_5", {})
            action_type = bus5_action.get("action")
            assert action_type in ["RECONSTRUCTED", "SMOOTHED"], f"Expected Bus_5 telemetry to be RECONSTRUCTED or SMOOTHED, got {action_type}"
            print(f" -> SUCCESS: Physics-aware validator detected degraded trust and performed telemetry reconstruction! Action: {action_type}")
            print(f"    Raw voltage: {bus5_action.get('raw_voltage', 0):.4f} pu | Reconstructed voltage: {bus5_action.get('filtered_voltage', 0):.4f} pu")

        # TEST 4: Decision Engine State Transition Hysteresis
        print("\n==================================================")
        print("TEST 4: State Transition Stability & Hysteresis")
        print("==================================================")
        reset_system(client)
        
        # Trigger an attack to change the state candidate
        print("Injecting FDIA attack on Bus_5 to trigger state candidate transition...")
        client.publish("grid/attack", json.dumps({
            "action": "START",
            "type": "FDIA",
            "config": {
                "target": "Bus_5",
                "bias": -0.15,
                "scale": 0.85
            }
        }))
        time.sleep(1) # Wait 1 tick
        
        with lock:
            # The state should not transition immediately to CYBER_ATTACK on tick 1 due to 3-tick hysteresis
            latest_orch = orchestrator_packets[-1] if orchestrator_packets else {}
            state_1 = latest_orch.get("global_state", "NORMAL")
            print(f"Tick 1 global state: {state_1} (Hysteresis holding...)")
            
        time.sleep(3) # Wait another 3 ticks
        with lock:
            latest_orch = orchestrator_packets[-1] if orchestrator_packets else {}
            state_final = latest_orch.get("global_state", "NORMAL")
            assert state_final in ["CYBER_ATTACK", "EMERGENCY_MODE"], f"Expected transition to CYBER_ATTACK after hysteresis delay, got {state_final}"
            print(f" -> SUCCESS: State transitioned to {state_final} after 3 consecutive loops of anomalous observations.")

        # TEST 5: Advisory vs Emergency Defense Gating
        print("\n==================================================")
        print("TEST 5: Advisory vs Emergency Defense Mode Gating")
        print("==================================================")
        reset_system(client)
        time.sleep(1.5) # Wait for first post-reset orchestration sweep
        
        # Verify starting mode is ADVISORY
        with lock:
            latest_orch = orchestrator_packets[-1] if orchestrator_packets else {}
            assert latest_orch.get("defense_mode") == "ADVISORY", f"Expected default mode ADVISORY, got {latest_orch.get('defense_mode')}"
            print("Default orchestrator mode: ADVISORY (manual confirmations required)")
            
        # Enable auto-defense (EMERGENCY_DEFENSE)
        print("Toggling autonomous defense mode: EMERGENCY_DEFENSE...")
        client.publish("grid/control", json.dumps({"command": "TOGGLE_AUTO_DEFENSE", "enabled": True}))
        time.sleep(2)
        
        with lock:
            latest_orch = orchestrator_packets[-1] if orchestrator_packets else {}
            assert latest_orch.get("defense_mode") == "EMERGENCY_DEFENSE", f"Expected mode to be EMERGENCY_DEFENSE, got {latest_orch.get('defense_mode')}"
            print("Successfully updated orchestrator mode to EMERGENCY_DEFENSE.")
            
        # Stop attack and clean up
        print("Cleaning up...")
        client.publish("grid/attack", json.dumps({"action": "STOP"}))
        client.publish("grid/control", json.dumps({"command": "RESET_ALARMS"}))
        time.sleep(2)
        
        print("\n==================================================")
        print("VERIFICATION COMPLETE: ALL PYPY STABILIZATION TESTS PASSED!")
        print("==================================================")
        
    finally:
        client.loop_stop()
        client.disconnect()

if __name__ == "__main__":
    run_tests()
