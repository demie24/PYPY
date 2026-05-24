#!/usr/bin/env python3
"""
Attack Simulator Engine
Modifies grid telemetry to simulate False Data Injection (FDIA) and unauthorized trips.
"""
import json
import copy

class AttackSimulator:
    def inject_fdia(self, normal_telemetry, target_bus, voltage_bias):
        """
        False Data Injection Attack: Modifies the voltage reading on a target bus.
        """
        attack_data = copy.deepcopy(normal_telemetry)
        buses = attack_data.get("state", {}).get("buses", {})
        if target_bus in buses:
            orig = buses[target_bus]["voltage"]
            buses[target_bus]["voltage"] += voltage_bias
            print(f"[ATTACK ENGINE] FDIA Injected on {target_bus}: {orig} -> {buses[target_bus]['voltage']}")
        return attack_data

    def spoof_remote_trip(self, target_breaker):
        """
        Sends an unauthorized trip command to a circuit breaker.
        """
        print(f"[ATTACK ENGINE] Spawning unauthorized Remote Trip on breaker: {target_breaker}")
        return {
            "command": "TRIP_BREAKER",
            "breaker": target_breaker,
            "authorized": False,
            "signature": "EXPIRED_OR_INVALID"
        }

if __name__ == "__main__":
    engine = AttackSimulator()
    sample_telemetry = {
        "state": {
            "buses": {
                "bus1": {"voltage": 1.0},
                "bus2": {"voltage": 0.99}
            }
        }
    }
    
    print("Normal:", sample_telemetry)
    # Inject 0.15 p.u. bias to trigger overvoltage/undervoltage anomalies
    attacked = engine.inject_fdia(sample_telemetry, "bus2", -0.15)
    print("Attacked (FDIA):", attacked)
    
    trip_cmd = engine.spoof_remote_trip("brk_1_2")
    print("Spoof Trip Command:", trip_cmd)
