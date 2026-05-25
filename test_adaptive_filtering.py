import json
import time
import threading
import numpy as np
import paho.mqtt.client as mqtt

# Thread-safe lists to collect telemetry, validation, trust and filter packets
telemetry_packets = []
validation_packets = []
trust_packets = []
filter_packets = []

lock = threading.Lock()

def on_connect(client, userdata, flags, rc):
    print(f"Connected to MQTT broker with result code {rc}")
    client.subscribe("grid/telemetry")
    client.subscribe("grid/physics_validation")
    client.subscribe("grid/trust_scores")
    client.subscribe("grid/adaptive_filter")

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode("utf-8"))
        topic = msg.topic
        with lock:
            if topic == "grid/telemetry":
                telemetry_packets.append(payload)
            elif topic == "grid/physics_validation":
                validation_packets.append(payload)
            elif topic == "grid/trust_scores":
                trust_packets.append(payload)
            elif topic == "grid/adaptive_filter":
                filter_packets.append(payload)
    except Exception as e:
        print(f"Error parsing message on {msg.topic}: {e}")

def run_direct_unit_tests(client):
    global telemetry_packets, validation_packets, trust_packets, filter_packets
    
    print("\n==================================================")
    print("RUNNING ADAPTIVE FILTERING DIRECT UNIT TESTS")
    print("==================================================")
    
    # Wait for a baseline telemetry packet
    timeout = 10
    start_t = time.time()
    while len(telemetry_packets) == 0:
        time.sleep(0.5)
        if time.time() - start_t > timeout:
            raise TimeoutError("No baseline telemetry packets received for direct injection test")
            
    with lock:
        base_telemetry = json.loads(json.dumps(telemetry_packets[-1])) # deep copy
        
    print("Baseline telemetry received. Testing trust metrics and filtering actions...")

    # Test 1: Verify Nominal state has high trust and global confidence
    print("\nTest 1: Verify Nominal State (High trust and confidence)")
    client.publish("grid/control", json.dumps({"command": "RESET_ALARMS"}))
    time.sleep(1.0)
    
    test_tel = json.loads(json.dumps(base_telemetry))
            
    with lock:
        trust_packets.clear()
        filter_packets.clear()
        
    client.publish("grid/telemetry", json.dumps(test_tel))
    time.sleep(2)
    
    with lock:
        assert len(trust_packets) > 0, "No trust packets received on grid/trust_scores"
        assert len(filter_packets) > 0, "No filter packets received on grid/adaptive_filter"
        
        latest_trust = trust_packets[-1]
        latest_filter = filter_packets[-1]
        
        bus5_trust = latest_trust["bus_trust"]["Bus_5"]
        confidence = latest_filter["global_grid_confidence"]
        
        print(f" -> Bus_5 Trust Score: {bus5_trust}%")
        print(f" -> Global Grid Confidence: {confidence}%")
        
        assert bus5_trust > 90.0, f"Expected Bus_5 trust > 90%, got {bus5_trust}%"
        assert confidence > 90.0, f"Expected global confidence > 90%, got {confidence}%"
        print(" -> SUCCESS: Nominal state metrics verified!")

    # Test 2: Verify Trust Degradation & Telemetry Rejection under FDIA
    print("\nTest 2: Trust Degradation & Telemetry Rejection (Bus_5 FDIA)")
    # Set high AI threat probability
    client.publish("grid/ai_threat_forecast", json.dumps({"cyber_instability_probability": 0.85}))
    time.sleep(0.5)
    
    # Inject bad voltage measurement on Bus_5
    test_tel = json.loads(json.dumps(base_telemetry))
    test_tel["state"]["buses"]["Bus_5"]["voltage_pu"] = 1.15
    
    with lock:
        trust_packets.clear()
        filter_packets.clear()
        
    # Publish multiple times to verify fast decay
    for _ in range(3):
        client.publish("grid/telemetry", json.dumps(test_tel))
        time.sleep(1.0)
        
    with lock:
        latest_trust = trust_packets[-1]
        latest_filter = filter_packets[-1]
        
        bus5_trust = latest_trust["bus_trust"]["Bus_5"]
        confidence = latest_filter["global_grid_confidence"]
        bus5_action = latest_filter["filter_actions"]["Bus_5"]["action"]
        filtered_v = latest_filter["filtered_telemetry"]["state"]["buses"]["Bus_5"]["voltage_pu"]
        
        print(f" -> Bus_5 Trust Score: {bus5_trust}%")
        print(f" -> Global Grid Confidence: {confidence}%")
        print(f" -> Bus_5 Filter Action: {bus5_action}")
        print(f" -> Bus_5 Filtered Voltage: {filtered_v} p.u. (Raw was 1.15)")
        
        assert bus5_trust < 50.0, f"Expected Bus_5 trust to degrade < 50%, got {bus5_trust}%"
        assert bus5_action == "REJECTED", f"Expected Bus_5 action to be REJECTED, got {bus5_action}"
        assert abs(filtered_v - 1.15) > 0.05, f"Expected filter to reject raw 1.15 pu and use LKG, got {filtered_v}"
        print(" -> SUCCESS: Trust degradation and REJECTION behavior verified!")

    # Test 3: Verify Recovery after Stabilization
    print("\nTest 3: Verify Trust Recovery after stabilization")
    client.publish("grid/ai_threat_forecast", json.dumps({"cyber_instability_probability": 0.0}))
    time.sleep(0.5)
    
    test_tel = json.loads(json.dumps(base_telemetry))
            
    # Publish multiple times to let trust score recover slowly
    recovered = False
    for i in range(1, 11):
        with lock:
            trust_packets.clear()
        client.publish("grid/telemetry", json.dumps(test_tel))
        time.sleep(1.0)
        
        with lock:
            if trust_packets:
                bus5_trust = trust_packets[-1]["bus_trust"]["Bus_5"]
                print(f"   Frame {i}: Bus_5 Trust recovered to {bus5_trust:.1f}%")
                if bus5_trust > 60.0:
                    recovered = True
                    break
                    
    assert recovered, "Expected Bus_5 trust to recover above 60% after 10 nominal cycles"
    print(" -> SUCCESS: Slow trust recovery verified!")

    # Test 4: Check for NaN/Inf in all logs
    print("\nTest 4: Verify NaN/Inf safety across all telemetry and trust outputs")
    for topic, packets in [("trust", trust_packets), ("filter", filter_packets)]:
        for p in packets:
            p_str = json.dumps(p)
            assert "nan" not in p_str.lower(), f"NaN value found in {topic} payload: {p_str}"
            assert "inf" not in p_str.lower(), f"Inf value found in {topic} payload: {p_str}"
    print(" -> SUCCESS: Complete NaN/Inf safety verified!")

def run_test_scenario(client, scenario_name, duration=15):
    global trust_packets, filter_packets
    
    print(f"\n==================================================")
    print(f"RUNNING SCENARIO VERIFICATION: {scenario_name}")
    print(f"==================================================")
    
    client.publish("grid/control", json.dumps({"command": "RESET_ALARMS"}))
    time.sleep(3)
    
    with lock:
        trust_packets.clear()
        filter_packets.clear()
        
    print(f"Triggering attack scenario '{scenario_name}'...")
    client.publish("grid/attack", json.dumps({
        "action": "START_SCENARIO",
        "scenario_name": scenario_name
    }))
    
    # Observe trust scores drop
    degraded_seen = False
    for sec in range(1, duration + 1):
        time.sleep(1)
        with lock:
            if filter_packets:
                latest = filter_packets[-1]
                if latest.get("degraded_observability") is True:
                    degraded_seen = True
                    
        if sec % 5 == 0 or sec == duration:
            with lock:
                tc = len(trust_packets)
                fc = len(filter_packets)
                conf = filter_packets[-1].get("global_grid_confidence", 100.0) if filter_packets else 100.0
            print(f"   Elapsed: {sec}s | Trust Packets: {tc} | Filter Packets: {fc} | Grid Conf: {conf:.1f}% | Degraded observ seen: {degraded_seen}")
            
    client.publish("grid/attack", json.dumps({"action": "STOP"}))
    client.publish("grid/control", json.dumps({"command": "RESET_ALARMS"}))
    time.sleep(3)
    
    assert degraded_seen, f"Expected to observe degraded observability during scenario '{scenario_name}'"
    print(f" -> SUCCESS: Scenario '{scenario_name}' passed trust scoring verification!")

def main():
    client = mqtt.Client(client_id="grid_cybersecurity_verification_suite_adaptive_filtering")
    client.on_connect = on_connect
    client.on_message = on_message
    
    print("Connecting to local Mosquitto broker on port 1884...")
    client.connect("localhost", 1884, 60)
    
    client.loop_start()
    time.sleep(1)
    
    try:
        # 1. Run direct injection tests
        run_direct_unit_tests(client)
        
        # 2. Run a live cyberattack scenario to verify dynamic trust response
        run_test_scenario(client, "stealthy_fdia", duration=15)
        
        print("\nALL ADAPTIVE FILTERING & TRUST VERIFICATION TESTS PASSED SUCCESSFULLY!")
        
    finally:
        client.loop_stop()
        client.disconnect()

if __name__ == "__main__":
    main()
