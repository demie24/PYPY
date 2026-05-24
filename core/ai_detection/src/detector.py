#!/usr/bin/env python3
"""
AI Detection Agent
Analyzes power grid telemetry for cyber-physical attacks.
"""
import json
import time

class AnomalyDetector:
    def __init__(self):
        # Physics-based thresholds and moving averages
        self.voltage_nominal = 1.0 # p.u. (per unit)
        self.threshold = 0.05       # 5% deviation threshold for basic checking

    def analyze(self, telemetry_data):
        """
        Runs anomaly detection algorithms (e.g., residual checking, Autoencoder score).
        """
        state = telemetry_data.get("state", {})
        buses = state.get("buses", {})
        anomalies = []
        
        # 1. Physics-based Anomaly Checking (e.g., state estimation residuals)
        for bus_name, data in buses.items():
            voltage = data.get("voltage", 0.0)
            if voltage > 0.0 and abs(voltage - self.voltage_nominal) > self.threshold:
                anomalies.append({
                    "type": "VOLTAGE_OUT_OF_BOUNDS",
                    "bus": bus_name,
                    "value": voltage,
                    "msg": f"Bus voltage {voltage} p.u. deviates from nominal baseline"
                })
                
        # 2. Machine Learning Anomaly Detection (Placeholder logic)
        # In practice, feed a vector of [voltages, currents, breaker_states] to an IsolationForest or Autoencoder.
        # score = ml_model.decision_function([vector])
        
        is_attack = len(anomalies) > 0
        return {
            "is_anomaly": is_attack,
            "anomalies": anomalies,
            "timestamp": int(time.time() * 1000)
        }

if __name__ == "__main__":
    detector = AnomalyDetector()
    sample_normal = {
        "state": {
            "buses": {
                "bus1": {"voltage": 1.0},
                "bus2": {"voltage": 0.99}
            }
        }
    }
    sample_attack = {
        "state": {
            "buses": {
                "bus1": {"voltage": 1.0},
                "bus2": {"voltage": 0.85} # Severe drop (FDIA or fault)
            }
        }
    }
    
    print("Normal State Analysis:", detector.analyze(sample_normal))
    print("Anomaly State Analysis:", detector.analyze(sample_attack))
