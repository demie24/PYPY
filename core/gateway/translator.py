import time
import logging
from typing import Dict, Any

logger = logging.getLogger("gateway.translator")

# Mapping definitions from 39-Bus AC indices to legacy 9-Bus nodes
BUS_MAPPING = {
    "Bus_1": 30,  # 39-bus slack generator bus
    "Bus_2": 31,  # 39-bus generator bus
    "Bus_3": 32,  # 39-bus generator bus
    "Bus_4": 3,   # 39-bus junction bus
    "Bus_5": 14,  # 39-bus load bus
    "Bus_6": 15,  # 39-bus load bus
    "Bus_7": 7,   # 39-bus junction bus
    "Bus_8": 24,  # 39-bus load bus
    "Bus_9": 8    # 39-bus junction bus
}

LINE_MAPPING = {
    "L1_4": "L_trafo_0",   # Maps Bus 1 to Bus 4 equivalent (Trafo connecting Gen to grid)
    "L2_7": "L_trafo_1",   # Maps Bus 2 to Bus 7 equivalent
    "L3_9": "L_trafo_2",   # Maps Bus 3 to Bus 9 equivalent
    "L4_5": "L_line_2",    # Junction to load line
    "L4_9": "L_line_4",    # Junction to junction line
    "L5_6": "L_line_8",    # Load to load line
    "L6_7": "L_line_10",   # Load to junction line
    "L7_8": "L_line_15",   # Junction to load line
    "L8_9": "L_line_18"    # Load to junction line
}

class TelemetryTranslator:
    def __init__(self):
        # Cache for latest 39-bus telemetry fields
        self.buses_cache: Dict[int, Dict[str, Any]] = {}
        self.lines_cache: Dict[str, Dict[str, Any]] = {}
        self.gens_cache: Dict[int, Dict[str, Any]] = {}

    def update_bus(self, data: Dict[str, Any]):
        bus_id = data.get("bus_id")
        if bus_id is not None:
            self.buses_cache[bus_id] = data

    def update_line(self, data: Dict[str, Any]):
        line_id = data.get("line_id")
        if line_id is not None:
            self.lines_cache[line_id] = data

    def update_gen(self, data: Dict[str, Any]):
        gen_id = data.get("generator_id")
        if gen_id is not None:
            self.gens_cache[gen_id] = data

    def build_legacy_telemetry(self) -> Dict[str, Any]:
        """
        Builds a legacy-compliant 9-bus telemetry payload from the cached 39-bus values.
        """
        timestamp = int(time.time() * 1000)
        
        legacy_state = {
            "timestamp": timestamp,
            "state": {
                "buses": {},
                "lines": {},
                "breakers": {},
                "generators_online": {}
            },
            "attack_status": {
                "active_attack": None,
                "compromised_nodes": {},
                "stages": []
            }
        }

        # 1. Map Buses
        for legacy_name, mapped_id in BUS_MAPPING.items():
            bus_data = self.buses_cache.get(mapped_id, {})
            # Check if this bus acts as a generator
            is_gen = legacy_name in ["Bus_1", "Bus_2", "Bus_3"]
            is_load = legacy_name in ["Bus_5", "Bus_6", "Bus_8"]
            
            # Map P and Q injection / consumption values
            p_val = bus_data.get("active_power", 0.0)
            q_val = bus_data.get("reactive_power", 0.0)
            
            # Convert injection to consumption representation for loads
            if is_load:
                p_val = abs(p_val)
                q_val = abs(q_val)
                
            legacy_state["state"]["buses"][legacy_name] = {
                "voltage_pu": bus_data.get("voltage_magnitude", 1.0),
                "angle_rad": bus_data.get("voltage_angle", 0.0),
                "is_load": is_load,
                "is_gen": is_gen,
                "frequency_hz": 60.0,
                "P_mw": p_val,
                "Q_mvar": q_val
            }

        # 2. Map Lines and Breakers
        for legacy_id, mapped_line_id in LINE_MAPPING.items():
            line_data = self.lines_cache.get(mapped_line_id, {})
            
            # Formulate current_pu from active/reactive power flow
            p_flow = line_data.get("active_power_flow", 0.0)
            q_flow = line_data.get("reactive_power_flow", 0.0)
            s_flow = (p_flow**2 + q_flow**2)**0.5
            current_pu = s_flow / 100.0 # base rating
            
            loading = line_data.get("loading_percent", 0.0)
            
            # Reconstruct legacy line flow fields
            legacy_state["state"]["lines"][legacy_id] = {
                "current_pu": round(current_pu, 4),
                "current_amp": round(current_pu * 500.0, 2),
                "P_mw": p_flow,
                "Q_mvar": q_flow,
                "capacity_pct": loading,
                "overcurrent": loading > 100.0
            }
            
            # Reconstruct breaker states (CLOSED=1, OPEN=0)
            # Default to CLOSED if active power flow is non-zero, or default to CLOSED
            # Or use active loading: if loading_percent > 0 or s_flow > 0, it is CLOSED
            is_closed = (s_flow > 0.01) or (loading > 0.1)
            legacy_state["state"]["breakers"][legacy_id] = "CLOSED" if is_closed else "OPEN"

        # 3. Map Generators Online
        legacy_state["state"]["generators_online"] = {
            "Bus_1": True,
            "Bus_2": True,
            "Bus_3": True
        }

        return legacy_state
