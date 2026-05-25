import numpy as np

class PhysicsFilter:
    def __init__(self, kcl_validator, kvl_validator):
        self.kcl_validator = kcl_validator
        self.kvl_validator = kvl_validator

    def validate(self, telemetry):
        """
        Executes complete physical laws validation and checks for impossible states.
        """
        try:
            buses_data = telemetry["state"]["buses"]
            lines_data = telemetry["state"]["lines"]
            breakers = telemetry["state"]["breakers"]
        except KeyError as e:
            raise KeyError(f"Invalid telemetry structure: missing key {e}")

        # 1. Run KCL/KVL Validators
        kcl_report = self.kcl_validator.validate(telemetry)
        kvl_report = self.kvl_validator.validate(telemetry)

        # 2. Check for impossible states
        impossible_violations = []
        impossible_state_flag = False

        # Check A: Open breaker but active flow/current
        for lid, status in breakers.items():
            if status == "OPEN":
                line_m = lines_data.get(lid, {})
                i_pu = float(line_m.get("current_pu", 0.0))
                p_mw = float(line_m.get("P_mw", 0.0))
                
                if i_pu > 0.02 or abs(p_mw) > 2.0:
                    impossible_violations.append(
                        f"Inconsistent Breaker: Line {lid} is OPEN but has active current ({i_pu:.3f} p.u.) or flow ({p_mw:.1f} MW)"
                    )
                    impossible_state_flag = True

        # Check B: Out-of-bounds voltage magnitudes
        for bus_name, bus_m in buses_data.items():
            v_pu = float(bus_m.get("voltage_pu", 1.0))
            if v_pu < 0.0 or v_pu > 1.30:
                impossible_violations.append(
                    f"Out of Bounds Voltage: {bus_name} voltage magnitude is physically impossible ({v_pu:.4f} p.u.)"
                )
                impossible_state_flag = True

        # Check C: Current measurement inconsistency
        # I = sqrt(P^2 + Q^2) / V_from
        for line in self.kvl_validator.lines:
            lid = line["id"]
            breaker_status = breakers.get(lid, "CLOSED")
            
            if breaker_status == "CLOSED":
                line_m = lines_data.get(lid, {})
                measured_i = float(line_m.get("current_pu", 0.0))
                p_pu = float(line_m.get("P_mw", 0.0)) / 100.0
                q_pu = float(line_m.get("Q_mvar", 0.0)) / 100.0
                
                f_idx = line["from"]
                bus_f = buses_data.get(f"Bus_{f_idx+1}", {})
                v_f = float(bus_f.get("voltage_pu", 1.0))
                
                if v_f > 0.1:
                    calculated_i = np.sqrt(p_pu**2 + q_pu**2) / v_f
                    deviation = abs(measured_i - calculated_i)
                    if deviation > 0.10: # threshold of 0.1 p.u.
                        impossible_violations.append(
                            f"Current Mismatch on {lid}: Measured={measured_i:.4f} p.u., Calculated={calculated_i:.4f} p.u. (dev={deviation:.4f})"
                        )
                        impossible_state_flag = True

        # 3. Calculate Physics Anomaly Score (0 - 100)
        score = 0
        
        # KCL error contribution
        kcl_val = kcl_report["total_mismatch_val"]
        if kcl_val > 5.0: # threshold of 5 MW/MVAR
            score += min(40, 20 + int(kcl_val * 2))
            
        # KVL error contribution
        kvl_val = kvl_report["total_mismatch_val"]
        if kvl_val > 0.02: # threshold of 0.02 p.u.
            score += min(40, 20 + int(kvl_val * 1000))
            
        # Impossible state contribution
        if impossible_state_flag:
            score += 40
            
        physics_anomaly_score = min(100, score)

        return {
            "physics_anomaly_score": physics_anomaly_score,
            "impossible_state": impossible_state_flag,
            "impossible_violations": impossible_violations,
            "kcl_error": kcl_report["total_mismatch_val"],
            "kvl_error": kvl_report["total_mismatch_val"],
            "kcl_details": kcl_report,
            "kvl_details": kvl_report
        }
