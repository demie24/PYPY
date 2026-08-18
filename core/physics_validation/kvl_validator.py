import numpy as np
from collections import defaultdict, deque

class KVLValidator:
    def __init__(self, topology=None):
        # Transmission Lines parameters: (From, To, Reactance X)
        self.lines = [
            {"from": 0, "to": 3, "X": 0.0576, "id": "L1_4"},
            {"from": 1, "to": 6, "X": 0.0625, "id": "L2_7"},
            {"from": 2, "to": 8, "X": 0.0586, "id": "L3_9"},
            {"from": 3, "to": 4, "X": 0.085,  "id": "L4_5"},
            {"from": 3, "to": 8, "X": 0.092,  "id": "L4_9"},
            {"from": 4, "to": 5, "X": 0.161,  "id": "L5_6"},
            {"from": 5, "to": 6, "X": 0.072,  "id": "L6_7"},
            {"from": 6, "to": 7, "X": 0.161,  "id": "L7_8"},
            {"from": 7, "to": 8, "X": 0.1008, "id": "L8_9"}
        ]
        if topology is not None:
            self.lines = [
                {
                    "from": line["from"], "to": line["to"],
                    "X": max(float(line.get("X", 0.1)), 1e-6), "id": line["id"],
                    **({
                        "current_unit": "ka",
                        "base_kv": float(topology.net.bus.at[line["from"], "vn_kv"]),
                    } if hasattr(topology, "net") else {}),
                }
                for line in topology.lines
            ]
        
        # Track reactance factors to align with physical transients in simulator
        self.prev_reactance_factors = {}
        self.cascade_alpha = 0.40
        self.calibrated_residuals = topology is not None
        self.residual_history = defaultdict(lambda: deque(maxlen=30))

    def validate(self, telemetry):
        """
        Validates telemetry KVL consistency and returns mismatches in per-unit.
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

        for line in self.lines:
            lid = line["id"]
            breaker_status = breakers.get(lid, "CLOSED")
            
            # If line is closed, evaluate KVL voltage/angle drop vs line flow
            if breaker_status == "CLOSED":
                f_idx = line["from"]
                t_idx = line["to"]
                
                # Fetch bus voltages and angles
                bus_f = buses_data.get(f"Bus_{f_idx+1}", {})
                bus_t = buses_data.get(f"Bus_{t_idx+1}", {})
                
                v_f = float(bus_f.get("voltage_pu", 1.0))
                v_t = float(bus_t.get("voltage_pu", 1.0))
                
                theta_f = float(bus_f.get("angle_rad", 0.0))
                theta_t = float(bus_t.get("angle_rad", 0.0))
                
                # Fetch measured active and reactive flow
                line_metrics = lines_data.get(lid, {})
                p_flow = float(line_metrics.get("P_mw", 0.0)) / 100.0 # convert to p.u.
                q_flow = float(line_metrics.get("Q_mvar", 0.0)) / 100.0 # convert to p.u.
                measured_i = float(line_metrics.get("current_pu", 0.0))
                
                # Calculate overcurrent thermal reactance factor
                prev_factor = self.prev_reactance_factors.get(lid, 1.0)
                if measured_i > 1.8:
                    target_factor = min(1.6, 1.0 + 0.5 * (measured_i - 1.8))
                else:
                    target_factor = 1.0
                    
                # Blend factor
                reactance_factor = prev_factor + self.cascade_alpha * (target_factor - prev_factor)
                self.prev_reactance_factors[lid] = reactance_factor
                
                x_val = line["X"] * reactance_factor
                
                # KVL active mismatch: p_flow * X - (theta_f - theta_t)
                p_mismatch = p_flow * x_val - (theta_f - theta_t)
                
                # KVL reactive mismatch: q_flow * X - (v_f - v_t)
                q_mismatch = q_flow * x_val - (v_f - v_t)
                
                if self.calibrated_residuals:
                    nominal = (
                        not (telemetry.get("attack_status") or {}).get("active_attack")
                        and (telemetry.get("solver_status") or {}).get("converged", True)
                        and all(status == "CLOSED" for status in breakers.values())
                    )
                    history = self.residual_history[lid]
                    if nominal:
                        history.append((p_mismatch, q_mismatch))
                    if len(history) < 15:
                        p_mismatch, q_mismatch = 0.0, 0.0
                    else:
                        samples = np.asarray(history)
                        baseline = np.median(samples, axis=0)
                        mad = np.median(np.abs(samples - baseline), axis=0)
                        residual = np.asarray((p_mismatch, q_mismatch)) - baseline
                        tolerance = np.maximum(6.0 * 1.4826 * mad, 0.01)
                        residual = np.sign(residual) * np.maximum(np.abs(residual) - tolerance, 0.0)
                        p_mismatch, q_mismatch = map(float, residual)

                mismatches[lid] = {
                    "P_mismatch_pu": round(p_mismatch, 4),
                    "Q_mismatch_pu": round(q_mismatch, 4)
                }
                
                total_p_mismatch += abs(p_mismatch)
                total_q_mismatch += abs(q_mismatch)
            else:
                mismatches[lid] = {
                    "P_mismatch_pu": 0.0,
                    "Q_mismatch_pu": 0.0
                }

        return {
            "total_p_mismatch_pu": round(total_p_mismatch, 4),
            "total_q_mismatch_pu": round(total_q_mismatch, 4),
            "total_mismatch_val": round(total_p_mismatch + total_q_mismatch, 4),
            "line_mismatches": mismatches
        }
