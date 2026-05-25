class KCLValidator:
    def __init__(self):
        # 9-Bus topology index mapping (0-indexed)
        # Bus indices in telemetry are 1-indexed, so we map appropriately
        self.num_buses = 9
        
        # Generators: (Bus index)
        self.generators = {0, 1, 2}
        
        # Loads: (Bus index)
        self.loads = {4, 5, 7}
        
        # Transmission Lines mapping: list of dict with from, to, and line id
        self.lines = [
            {"from": 0, "to": 3, "id": "L1_4"},
            {"from": 1, "to": 6, "id": "L2_7"},
            {"from": 2, "to": 8, "id": "L3_9"},
            {"from": 3, "to": 4, "id": "L4_5"},
            {"from": 3, "to": 8, "id": "L4_9"},
            {"from": 4, "to": 5, "id": "L5_6"},
            {"from": 5, "to": 6, "id": "L6_7"},
            {"from": 6, "to": 7, "id": "L7_8"},
            {"from": 7, "to": 8, "id": "L8_9"}
        ]

    def validate(self, telemetry):
        """
        Validates telemetry KCL consistency and returns mismatches in MW/MVAR.
        """
        try:
            buses_data = telemetry["state"]["buses"]
            lines_data = telemetry["state"]["lines"]
            breakers = telemetry["state"]["breakers"]
        except KeyError as e:
            raise KeyError(f"Invalid telemetry structure: missing key {e}")

        mismatches = {}
        total_p_mismatch = 0.0
        total_q_mismatch = 0.0

        for i in range(self.num_buses):
            bus_name = f"Bus_{i+1}"
            bus_metrics = buses_data.get(bus_name, {})
            
            # 1. Determine injection at bus
            # Generators: positive injection
            # Loads: negative injection
            # Junctions: zero
            p_inject = 0.0
            q_inject = 0.0
            
            if i in self.generators:
                p_inject = float(bus_metrics.get("P_mw", 0.0))
                q_inject = float(bus_metrics.get("Q_mvar", 0.0))
            elif i in self.loads:
                p_inject = -float(bus_metrics.get("P_mw", 0.0))
                q_inject = -float(bus_metrics.get("Q_mvar", 0.0))
                
            # 2. Compute outgoing flows
            p_out = 0.0
            q_out = 0.0
            
            for line in self.lines:
                lid = line["id"]
                line_metrics = lines_data.get(lid, {})
                breaker_status = breakers.get(lid, "CLOSED")
                
                if breaker_status == "CLOSED":
                    p_flow = float(line_metrics.get("P_mw", 0.0))
                    q_flow = float(line_metrics.get("Q_mvar", 0.0))
                    
                    if line["from"] == i:
                        p_out += p_flow
                        q_out += q_flow
                    elif line["to"] == i:
                        p_out -= p_flow
                        q_out -= q_flow
                        
            # KCL mismatch = inject - out
            p_mismatch = p_inject - p_out
            q_mismatch = q_inject - q_out
            
            mismatches[bus_name] = {
                "P_mismatch_mw": round(p_mismatch, 2),
                "Q_mismatch_mvar": round(q_mismatch, 2)
            }
            
            total_p_mismatch += abs(p_mismatch)
            total_q_mismatch += abs(q_mismatch)
            
        return {
            "total_p_mismatch_mw": round(total_p_mismatch, 2),
            "total_q_mismatch_mvar": round(total_q_mismatch, 2),
            "total_mismatch_val": round(total_p_mismatch, 2),
            "bus_mismatches": mismatches
        }
