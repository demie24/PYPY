#!/usr/bin/env python3
"""
Digital Twin Grid Simulator
Simulates voltages, currents, and power flows.
"""
import time
import json
import random

class GridSimulator:
    def __init__(self):
        # Initial grid state (buses, voltage levels, breaker status)
        self.grid_state = {
            "buses": {
                "bus1": {"voltage": 1.0, "type": "slack"},
                "bus2": {"voltage": 0.99, "type": "load", "load_mw": 10.0},
                "bus3": {"voltage": 0.98, "type": "load", "load_mw": 15.0}
            },
            "breakers": {
                "brk_1_2": "CLOSED",
                "brk_2_3": "CLOSED"
            }
        }
    
    def calculate_power_flow(self):
        """
        Placeholder for solving grid power flow.
        Calculates values based on breaker states and loads.
        """
        # Simple dynamic calculation based on breaker state
        if self.grid_state["breakers"]["brk_1_2"] == "OPEN":
            self.grid_state["buses"]["bus2"]["voltage"] = 0.0
            self.grid_state["buses"]["bus3"]["voltage"] = 0.0
        elif self.grid_state["breakers"]["brk_2_3"] == "OPEN":
            self.grid_state["buses"]["bus2"]["voltage"] = 0.98 + random.uniform(-0.01, 0.01)
            self.grid_state["buses"]["bus3"]["voltage"] = 0.0
        else:
            self.grid_state["buses"]["bus2"]["voltage"] = 0.99 + random.uniform(-0.01, 0.01)
            self.grid_state["buses"]["bus3"]["voltage"] = 0.98 + random.uniform(-0.01, 0.01)

    def get_telemetry(self):
        self.calculate_power_flow()
        return {
            "timestamp": int(time.time() * 1000),
            "state": self.grid_state
        }

if __name__ == "__main__":
    sim = GridSimulator()
    print("Starting Digital Twin Simulation...")
    for _ in range(5):
        print(json.dumps(sim.get_telemetry(), indent=2))
        time.sleep(1)
