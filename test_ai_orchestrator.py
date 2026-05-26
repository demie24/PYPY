import json
import time
import threading
import paho.mqtt.client as mqtt

# Thread-safe lists to collect published orchestrator packets
orchestrator_packets = []
recommended_actions_packets = []

lock = threading.Lock()

def on_connect(client, userdata, flags, rc):
    print(f"Connected to MQTT broker with result code {rc}")
    client.subscribe("grid/ai_orchestrator")
    client.subscribe("grid/recommended_actions")

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode("utf-8"))
        topic = msg.topic
        with lock:
            if topic == "grid/ai_orchestrator":
                orchestrator_packets.append(payload)
            elif topic == "grid/recommended_actions":
                recommended_actions_packets.append(payload)
    except Exception as e:
        print(f"Error parsing message on {msg.topic}: {e}")

# Static nominal telemetry template to isolate tests from running simulator
base_telemetry = {
    "timestamp": 0,
    "state": {
        "breakers": {
            "L1_4": "CLOSED",
            "L2_7": "CLOSED",
            "L3_9": "CLOSED",
            "L4_5": "CLOSED",
            "L4_9": "CLOSED",
            "L5_6": "CLOSED",
            "L6_7": "CLOSED",
            "L7_8": "OPEN",
            "L8_9": "CLOSED"
        },
        "buses": {
            "Bus_1": {"voltage_pu": 1.0, "angle_rad": 0.0, "is_load": False, "is_gen": True, "P_mw": 0.0, "Q_mvar": 0.0},
            "Bus_2": {"voltage_pu": 1.0, "angle_rad": 0.0, "is_load": False, "is_gen": True, "P_mw": 0.0, "Q_mvar": 0.0},
            "Bus_3": {"voltage_pu": 1.0, "angle_rad": 0.0, "is_load": False, "is_gen": True, "P_mw": 0.0, "Q_mvar": 0.0},
            "Bus_4": {"voltage_pu": 1.0, "angle_rad": 0.0, "is_load": False, "is_gen": False, "P_mw": 0.0, "Q_mvar": 0.0},
            "Bus_5": {"voltage_pu": 1.0, "angle_rad": 0.0, "is_load": True, "is_gen": False, "P_mw": 125.0, "Q_mvar": 50.0},
            "Bus_6": {"voltage_pu": 1.0, "angle_rad": 0.0, "is_load": True, "is_gen": False, "P_mw": 90.0, "Q_mvar": 30.0},
            "Bus_7": {"voltage_pu": 1.0, "angle_rad": 0.0, "is_load": False, "is_gen": False, "P_mw": 0.0, "Q_mvar": 0.0},
            "Bus_8": {"voltage_pu": 1.0, "angle_rad": 0.0, "is_load": True, "is_gen": False, "P_mw": 100.0, "Q_mvar": 35.0},
            "Bus_9": {"voltage_pu": 1.0, "angle_rad": 0.0, "is_load": False, "is_gen": False, "P_mw": 0.0, "Q_mvar": 0.0}
        },
        "lines": {
            "L1_4": {"current_pu": 0.0, "current_amp": 0.0, "P_mw": 0.0, "Q_mvar": 0.0, "capacity_pct": 40.0, "overcurrent": False},
            "L2_7": {"current_pu": 0.0, "current_amp": 0.0, "P_mw": 0.0, "Q_mvar": 0.0, "capacity_pct": 40.0, "overcurrent": False},
            "L3_9": {"current_pu": 0.0, "current_amp": 0.0, "P_mw": 0.0, "Q_mvar": 0.0, "capacity_pct": 40.0, "overcurrent": False},
            "L4_5": {"current_pu": 0.0, "current_amp": 0.0, "P_mw": 0.0, "Q_mvar": 0.0, "capacity_pct": 40.0, "overcurrent": False},
            "L4_9": {"current_pu": 0.0, "current_amp": 0.0, "P_mw": 0.0, "Q_mvar": 0.0, "capacity_pct": 40.0, "overcurrent": False},
            "L5_6": {"current_pu": 0.0, "current_amp": 0.0, "P_mw": 0.0, "Q_mvar": 0.0, "capacity_pct": 40.0, "overcurrent": False},
            "L6_7": {"current_pu": 0.0, "current_amp": 0.0, "P_mw": 0.0, "Q_mvar": 0.0, "capacity_pct": 40.0, "overcurrent": False},
            "L7_8": {"current_pu": 0.0, "current_amp": 0.0, "P_mw": 0.0, "Q_mvar": 0.0, "capacity_pct": 0.0, "overcurrent": False},
            "L8_9": {"current_pu": 0.0, "current_amp": 0.0, "P_mw": 0.0, "Q_mvar": 0.0, "capacity_pct": 40.0, "overcurrent": False}
        }
    },
    "attack_status": {"active_attack": None, "compromised_nodes": {}}
}

def publish_mock_states(client, threat_prob=0.0, cascade_prob=0.0, physics_anomaly=0.0, is_impossible=False, trust_degraded=False):
    """
    Helper to publish mock states to all grid subtopics.
    """
    # 1. Trust scores mock
    trust_scores = {
        "bus_trust": {f"Bus_{i}": 100.0 for i in range(1, 10)},
        "details": {f"Bus_{i}": {"trust_score": 100.0} for i in range(1, 10)}
    }
    # Add all lines to avoid missing detail indices in ActionRecommender
    for line_id in ["L1_4", "L2_7", "L3_9", "L4_5", "L4_9", "L5_6", "L6_7", "L7_8", "L8_9"]:
        trust_scores["details"][line_id] = {"trust_score": 100.0}
        
    if trust_degraded:
        trust_scores["bus_trust"]["Bus_5"] = 30.0
        trust_scores["details"]["Bus_5"]["trust_score"] = 30.0
        trust_scores["details"]["L7_8"]["trust_score"] = 30.0
        
    client.publish("grid/trust_scores", json.dumps(trust_scores))
    
    # 2. Physics validation mock
    physics_val = {
        "physics_anomaly_score": physics_anomaly,
        "impossible_state": is_impossible,
        "global_grid_confidence": 100.0 - physics_anomaly,
        "physics_state": "NORMAL" if physics_anomaly < 30.0 else "CYBER_ATTACK_INSTABILITY",
        "kcl_error": physics_anomaly * 0.5,
        "kvl_error": physics_anomaly * 0.001
    }
    client.publish("grid/physics_validation", json.dumps(physics_val))
    
    # 3. Threat forecast mock
    client.publish("grid/ai_threat_forecast", json.dumps({
        "cyber_instability_probability": threat_prob,
        "status": "NORMAL" if threat_prob < 0.50 else "CYBER_ATTACK_INSTABILITY"
    }))
    
    # 4. Threat engine mock
    client.publish("grid/threat", json.dumps({
        "cascade_probability": cascade_prob,
        "threat_score": 50.0 * cascade_prob,
        "severity": "LOW" if cascade_prob < 0.3 else "HIGH",
        "confidence": 1.0,
        "affected_nodes": [],
        "propagation_risk": "LOW",
        "recommendations": []
    }))
    
    # Small sleep to let the orchestrator process these cache updates
    time.sleep(0.15)

def run_orchestrator_tests(client):
    global orchestrator_packets, recommended_actions_packets
    
    print("\n==================================================")
    print("RUNNING AI ORCHESTRATOR DECISION & ADVISORY TESTS")
    print("==================================================")
    print("Starting tests using isolated nominal telemetry template...")

    # Test 1: Verify Nominal Grid Behavior
    print("\nTest 1: Verify Nominal Grid State (State: NORMAL, Risk: LOW, Actions: Empty)")
    client.publish("grid/control", json.dumps({"command": "RESET_ALARMS"}))
    time.sleep(0.5)
    
    test_tel = json.loads(json.dumps(base_telemetry))
    test_tel["timestamp"] = int(time.time() * 1000)

    with lock:
        orchestrator_packets.clear()
        recommended_actions_packets.clear()

    # Publish clean mock states, then trigger cycle
    publish_mock_states(client, threat_prob=0.0, cascade_prob=0.0, physics_anomaly=0.0)
    client.publish("grid/telemetry", json.dumps(test_tel))
    time.sleep(2.0)

    with lock:
        assert len(orchestrator_packets) > 0, "No orchestrator packets received on grid/ai_orchestrator"
        assert len(recommended_actions_packets) > 0, "No recommended actions packets received on grid/recommended_actions"
        
        latest_orchestrator = orchestrator_packets[-1]
        latest_actions = recommended_actions_packets[-1]
        
        g_state = latest_orchestrator["global_state"]
        risk = latest_orchestrator["global_risk_level"]
        stability = latest_orchestrator["stability_score"]
        confidence = latest_orchestrator["restoration_confidence"]
        
        print(f" -> Global State: {g_state}")
        print(f" -> Global Risk Level: {risk}")
        print(f" -> Cyber-Physical Stability: {stability}%")
        print(f" -> Restoration Confidence: {confidence}%")
        print(f" -> Actions Count: {len(latest_actions['recommendations'])}")
        for act in latest_actions["recommendations"]:
            print(f"    * Action: {act['action']} | Target: {act['target']} | Reason: {act['reasoning']}")
        
        assert g_state == "NORMAL", f"Expected state NORMAL, got {g_state}"
        assert risk == "LOW", f"Expected risk LOW, got {risk}"
        assert stability >= 90.0, f"Expected high stability index, got {stability}%"
        assert len(latest_actions["recommendations"]) == 0, "Expected no actions for nominal grid state"
        print(" -> SUCCESS: Nominal grid state verified!")

    # Test 2: Verify Cyber-Attack Detection
    print("\nTest 2: Verify Cyber-Attack State Transition (FDIA or High Probability threat forecast)")
    
    test_tel = json.loads(json.dumps(base_telemetry))
    test_tel["timestamp"] = int(time.time() * 1000)
    test_tel["attack_status"] = {
        "active_attack": "FDIA",
        "compromised_nodes": {"Bus_5": "voltage"}
    }

    with lock:
        orchestrator_packets.clear()
        recommended_actions_packets.clear()

    # Publish high cyber threat probability, then trigger telemetry
    publish_mock_states(client, threat_prob=0.85, cascade_prob=0.0, physics_anomaly=0.0)
    client.publish("grid/telemetry", json.dumps(test_tel))
    time.sleep(2.0)

    with lock:
        latest_orchestrator = orchestrator_packets[-1]
        latest_actions = recommended_actions_packets[-1]
        
        g_state = latest_orchestrator["global_state"]
        risk = latest_orchestrator["global_risk_level"]
        
        print(f" -> Global State: {g_state}")
        print(f" -> Global Risk Level: {risk}")
        
        assert g_state == "CYBER_ATTACK", f"Expected state CYBER_ATTACK, got {g_state}"
        print(" -> SUCCESS: Cyber attack transition verified!")

    # Test 3: Verify Cascade Risk Detection and Advisory Action
    print("\nTest 3: Verify Cascade Risk State & Transmission Overload Advisory Actions")
    
    test_tel = json.loads(json.dumps(base_telemetry))
    test_tel["timestamp"] = int(time.time() * 1000)
    # Overload transmission lines to drop stability below 75%
    test_tel["state"]["lines"]["L5_6"]["capacity_pct"] = 160.0
    test_tel["state"]["lines"]["L4_5"]["capacity_pct"] = 160.0

    with lock:
        orchestrator_packets.clear()
        recommended_actions_packets.clear()

    # Publish high cascade probability, then trigger telemetry
    publish_mock_states(client, threat_prob=0.0, cascade_prob=0.60, physics_anomaly=0.0)
    client.publish("grid/telemetry", json.dumps(test_tel))
    time.sleep(2.0)

    with lock:
        latest_orchestrator = orchestrator_packets[-1]
        latest_actions = recommended_actions_packets[-1]
        
        g_state = latest_orchestrator["global_state"]
        stability = latest_orchestrator["stability_score"]
        actions = latest_actions["recommendations"]
        
        print(f" -> Global State: {g_state}")
        print(f" -> Cyber-Physical Stability: {stability}%")
        print(f" -> Recommended Actions:")
        for act in actions:
            print(f"    * Action: {act['action']} | Target: {act['target']} | Priority: {act['priority']}")
            
        assert g_state == "CASCADE_RISK", f"Expected state CASCADE_RISK, got {g_state}"
        assert any(act["action"] == "ISOLATE_LINE" and act["target"] == "L5_6" for act in actions), "Expected isolate line recommendation for line L5_6"
        print(" -> SUCCESS: Cascade risk and overload isolations verified!")

    # Test 4: Verify Emergency Mode State & Escalation
    print("\nTest 4: Verify Emergency Mode State & Operator Escalation (Low Stability)")
    
    test_tel = json.loads(json.dumps(base_telemetry))
    test_tel["timestamp"] = int(time.time() * 1000)
    # Open multiple breakers to collapse stability score below 40%
    test_tel["state"]["breakers"]["L1_4"] = "OPEN"
    test_tel["state"]["breakers"]["L3_6"] = "OPEN"
    test_tel["state"]["breakers"]["L5_6"] = "OPEN"
    test_tel["state"]["breakers"]["L8_9"] = "OPEN"
    # Set extreme voltage deviations on load buses
    for bus_id in ["Bus_5", "Bus_6", "Bus_8"]:
        test_tel["state"]["buses"][bus_id]["voltage_pu"] = 0.20

    with lock:
        orchestrator_packets.clear()
        recommended_actions_packets.clear()

    # Publish high physics anomaly (low grid confidence), then trigger telemetry
    publish_mock_states(client, threat_prob=0.0, cascade_prob=0.0, physics_anomaly=75.0)
    client.publish("grid/telemetry", json.dumps(test_tel))
    time.sleep(2.0)

    with lock:
        latest_orchestrator = orchestrator_packets[-1]
        latest_actions = recommended_actions_packets[-1]
        
        g_state = latest_orchestrator["global_state"]
        risk = latest_orchestrator["global_risk_level"]
        stability = latest_orchestrator["stability_score"]
        actions = latest_actions["recommendations"]
        
        print(f" -> Global State: {g_state}")
        print(f" -> Global Risk Level: {risk}")
        print(f" -> Cyber-Physical Stability: {stability}%")
        print(f" -> Recommended Actions:")
        for act in actions:
            print(f"    * Action: {act['action']} | Target: {act['target']} | Priority: {act['priority']}")
            
        assert g_state == "EMERGENCY_MODE", f"Expected state EMERGENCY_MODE, got {g_state}"
        assert risk == "CRITICAL", f"Expected risk CRITICAL, got {risk}"
        assert any(act["action"] == "OPERATOR_ESCALATION" for act in actions), "Expected manual override escalation advisory"
        print(" -> SUCCESS: Emergency mode operator escalation verified!")

    # Test 5: NaN/Inf Safety Verification
    print("\nTest 5: Verify NaN/Inf safety across all published output states")
    with lock:
        for p in orchestrator_packets + recommended_actions_packets:
            p_str = json.dumps(p)
            assert "nan" not in p_str.lower(), f"NaN value found in packet: {p_str}"
            assert "inf" not in p_str.lower(), f"Inf value found in packet: {p_str}"
    print(" -> SUCCESS: NaN/Inf safety check passed!")

def main():
    client = mqtt.Client(client_id="smart_grid_orchestrator_test_suite")
    client.on_connect = on_connect
    client.on_message = on_message
    
    print("Connecting to local Mosquitto broker on port 1884...")
    client.connect("localhost", 1884, 60)
    
    client.loop_start()
    time.sleep(1)
    
    try:
        run_orchestrator_tests(client)
        print("\nALL AI ORCHESTRATOR DECISION ENGINE AND RECOMMENDATION TESTS PASSED SUCCESSFULLY!")
    finally:
        client.loop_stop()
        client.disconnect()

if __name__ == "__main__":
    main()
