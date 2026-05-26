import numpy as np

class StateEncoder:
    def __init__(self):
        self.state_dim = 72

    def encode_state(self, 
                     telemetry=None, 
                     threat_data=None, 
                     ai_prediction=None, 
                     multi_bus=None, 
                     threat_aware=None, 
                     pinn_forecast=None, 
                     physics_val=None, 
                     trust_scores=None, 
                     adaptive_filter=None, 
                     orchestrator_data=None,
                     override_active=0.0) -> np.ndarray:
        """
        Encodes all live cyber-physical smart grid variables into a standardized 72-dimensional float32 vector.
        """
        vec = np.zeros(self.state_dim, dtype=np.float32)
        
        # Helper variables
        bus_keys = [f"Bus_{i}" for i in range(1, 10)]
        line_keys = ["L1_4", "L2_7", "L3_9", "L4_5", "L4_9", "L5_6", "L6_7", "L7_8", "L8_9"]
        
        # 1. Bus voltages (9): index 0-8 (Default 1.0 p.u.)
        voltages = [1.0] * 9
        if telemetry and "state" in telemetry and "buses" in telemetry["state"]:
            for i, b_key in enumerate(bus_keys):
                voltages[i] = telemetry["state"]["buses"].get(b_key, {}).get("voltage_pu", 1.0)
        vec[0:9] = voltages
        
        # 2. Bus voltage angles (9): index 9-17 (Default 0.0 rad)
        angles = [0.0] * 9
        if telemetry and "state" in telemetry and "buses" in telemetry["state"]:
            for i, b_key in enumerate(bus_keys):
                angles[i] = telemetry["state"]["buses"].get(b_key, {}).get("angle_rad", 0.0)
        vec[9:18] = angles
        
        # 3. Active Line Loading (9): index 18-26 (Default 0.0 MW -> p.u.)
        line_P = [0.0] * 9
        if telemetry and "state" in telemetry and "lines" in telemetry["state"]:
            for i, l_key in enumerate(line_keys):
                line_P[i] = telemetry["state"]["lines"].get(l_key, {}).get("P_mw", 0.0) / 100.0
        vec[18:27] = line_P
        
        # 4. Reactive Line Loading (9): index 27-35 (Default 0.0 MVar -> p.u.)
        line_Q = [0.0] * 9
        if telemetry and "state" in telemetry and "lines" in telemetry["state"]:
            for i, l_key in enumerate(line_keys):
                line_Q[i] = telemetry["state"]["lines"].get(l_key, {}).get("Q_mvar", 0.0) / 100.0
        vec[27:36] = line_Q
        
        # 5. Breaker States (9): index 36-44 (1.0 CLOSED, 0.0 OPEN, Default CLOSED)
        breakers = [1.0] * 9
        if telemetry and "state" in telemetry and "breakers" in telemetry["state"]:
            for i, l_key in enumerate(line_keys):
                status = telemetry["state"]["breakers"].get(l_key, "CLOSED")
                breakers[i] = 1.0 if status == "CLOSED" else 0.0
        vec[36:45] = breakers
        
        # 6. Bus Trust Scores (9): index 45-53 (Default 100.0 -> normalized 0.0 to 1.0)
        bus_trusts = [1.0] * 9
        if trust_scores and "bus_trust" in trust_scores:
            for i, b_key in enumerate(bus_keys):
                bus_trusts[i] = trust_scores["bus_trust"].get(b_key, 100.0) / 100.0
        vec[45:54] = bus_trusts
        
        # 7. Line Trust Scores (9): index 54-62 (Default 100.0 -> normalized 0.0 to 1.0)
        line_trusts = [1.0] * 9
        if trust_scores and "line_trust" in trust_scores:
            for i, l_key in enumerate(line_keys):
                line_trusts[i] = trust_scores["line_trust"].get(l_key, 100.0) / 100.0
        vec[54:63] = line_trusts
        
        # 8. Anomaly Score (1): index 63 (Default 0.0)
        anomaly_score = 0.0
        if physics_val:
            anomaly_score = physics_val.get("physics_anomaly_score", 0.0) / 100.0
        vec[63] = anomaly_score
        
        # 9. PINN Confidence (1): index 64 (Default 1.0)
        pinn_conf = 1.0
        if pinn_forecast:
            pinn_conf = pinn_forecast.get("global_physics_confidence", 1.0)
        vec[64] = pinn_conf
        
        # 10. Cascading Risk (1): index 65 (Default 0.0)
        cascade_prob = 0.0
        if threat_data:
            cascade_prob = threat_data.get("cascade_probability", 0.0)
        vec[65] = cascade_prob
        
        # 11. FLISR State code (1): index 66 (Default 0.0)
        # NORMAL=0.0, FAULT_DETECTED=1.0, ISOLATION=2.0, RESTORATION=3.0, RESTORED=4.0
        flisr_mapping = {"NORMAL": 0.0, "FAULT_DETECTED": 1.0, "ISOLATION": 2.0, "RESTORATION": 3.0, "RESTORED": 4.0}
        flisr_state = 0.0
        if orchestrator_data:
            state_str = orchestrator_data.get("global_state", "NORMAL")
            # Fallback mapping
            flisr_state = flisr_mapping.get(state_str, 0.0)
        elif telemetry:
            state_str = telemetry.get("flisr_state", "NORMAL")
            flisr_state = flisr_mapping.get(state_str, 0.0)
        vec[66] = flisr_state
        
        # 12. Observability Quality (1): index 67 (Default 1.0)
        observability = 1.0
        if pinn_forecast:
            # 1.0 if not degraded, 0.0 if degraded
            observability = 0.0 if pinn_forecast.get("degraded_observability", False) else 1.0
        vec[67] = observability
        
        # 13. Attack Probability / Cyber logit (1): index 68 (Default 0.0)
        cyber_prob = 0.0
        if threat_aware:
            cyber_prob = threat_aware.get("cyber_instability_probability", 0.0)
        vec[68] = cyber_prob
        
        # 14. Threat Severity (1): index 69 (Default 0.0)
        # LOW=0.0, MEDIUM=0.33, HIGH=0.66, CRITICAL=1.0
        sev_mapping = {"LOW": 0.0, "MEDIUM": 0.33, "HIGH": 0.66, "CRITICAL": 1.0}
        threat_sev = 0.0
        if threat_data:
            sev_str = threat_data.get("severity", "LOW").upper()
            threat_sev = sev_mapping.get(sev_str, 0.0)
        vec[69] = threat_sev
        
        # 15. Islanding State (1): index 70 (Default 0.0)
        # 1.0 if any bus is islanded (undervoltage < 0.20), else 0.0
        islanding_active = 0.0
        if any(v < 0.20 for v in voltages):
            islanding_active = 1.0
        vec[70] = islanding_active
        
        # 16. Operator Override Active (1): index 71 (Default 0.0)
        vec[71] = float(override_active)
        
        # Protect against NaNs or Infs
        vec = np.nan_to_num(vec, nan=0.0, posinf=1.0, neginf=0.0)
        
        return vec
