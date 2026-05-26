import numpy as np
from typing import Dict, Any, List

class StateVectorDebugger:
    """
    Deconstructs and translates the flat 72-dimensional Gymnasium state vector
    into descriptive, human-readable telemetry classifications for the SCADA HMI.
    """
    def __init__(self):
        self.bus_names = [f"Bus_{i}" for i in range(1, 10)]
        self.line_names = ["L1_4", "L2_7", "L3_9", "L4_5", "L4_9", "L5_6", "L6_7", "L7_8", "L8_9"]
        self.flisr_states = {0.0: "NORMAL", 1.0: "FAULT_DETECTED", 2.0: "ISOLATION", 3.0: "RESTORATION", 4.0: "RESTORED"}
        self.severity_states = {0.0: "LOW", 0.33: "MEDIUM", 0.66: "HIGH", 1.0: "CRITICAL"}

    def deconstruct(self, state_vector: np.ndarray) -> Dict[str, Any]:
        """
        Parses a 72-element state vector into structured dictionaries and flags.
        """
        if len(state_vector) != 72:
            return {
                "error": f"Invalid state vector size: expected 72, got {len(state_vector)}",
                "trusted_state_quality": 0.0,
                "warnings": ["Invalid state length"]
            }

        # Handle potential NaNs safely
        state = np.nan_to_num(state_vector, nan=0.0)

        # 1. Slice vector segments
        voltages = state[0:9]
        angles = state[9:18]
        active_load = state[18:27]
        reactive_load = state[27:36]
        breakers = state[36:45]
        bus_trust = state[45:54]
        line_trust = state[54:63]
        
        anomaly = state[63]
        pinn_conf = state[64]
        cascade_risk = state[65]
        flisr_code = state[66]
        observability = state[67]
        cyber_prob = state[68]
        threat_sev_code = state[69]
        islanding = state[70]
        override_active = state[71]

        # 2. Re-construct named maps
        voltage_map = {self.bus_names[i]: round(float(voltages[i]), 3) for i in range(9)}
        angle_map = {self.bus_names[i]: round(float(angles[i]), 3) for i in range(9)}
        loading_map = {self.line_names[i]: round(float(np.sqrt(active_load[i]**2 + reactive_load[i]**2)), 3) for i in range(9)}
        breaker_map = {self.line_names[i]: "CLOSED" if breakers[i] > 0.5 else "OPEN" for i in range(9)}
        
        bus_trust_map = {self.bus_names[i]: round(float(bus_trust[i] * 100.0), 1) for i in range(9)}
        line_trust_map = {self.line_names[i]: round(float(line_trust[i] * 100.0), 1) for i in range(9)}

        # 3. Compute telemetry quality indicators
        total_elements = 18 # 9 buses + 9 lines
        trusted_elements = sum(1 for t in bus_trust if t >= 0.80) + sum(1 for t in line_trust if t >= 0.80)
        trusted_state_quality = round((trusted_elements / total_elements) * 100.0, 1)

        # 4. Compile diagnostics and warnings
        warnings = []
        
        # Voltage violations
        for bus, v in voltage_map.items():
            if v < 0.85:
                warnings.append(f"CRITICAL: Severe undervoltage on {bus} ({v:.3f} p.u.)")
            elif v < 0.90:
                warnings.append(f"WARNING: Voltage dip on {bus} ({v:.3f} p.u.)")
            elif v > 1.15:
                warnings.append(f"CRITICAL: Severe overvoltage on {bus} ({v:.3f} p.u.)")
            elif v > 1.10:
                warnings.append(f"WARNING: Voltage swell on {bus} ({v:.3f} p.u.)")

        # Line overloads
        for line, l in loading_map.items():
            if l > 1.20:
                warnings.append(f"CRITICAL: Line overload on {line} ({l*100:.1f}%)")
            elif l > 1.00:
                warnings.append(f"WARNING: Line loading margin exceeded on {line} ({l*100:.1f}%)")

        # Islanding flag
        if islanding > 0.5:
            warnings.append("CRITICAL: Islanding detected! Load disconnected from generators.")

        # Obs degradation
        if observability < 0.5:
            warnings.append("WARNING: SCADA state observability is degraded.")

        # Cyber anomaly alerts
        if anomaly > 0.40:
            warnings.append(f"WARNING: High physics anomaly detected ({anomaly*100:.1f}%)")
        if cyber_prob > 0.50:
            warnings.append(f"WARNING: Attacking activity detected ({cyber_prob*100:.1f}%)")

        return {
            "voltages": voltage_map,
            "angles": angle_map,
            "loadings": loading_map,
            "breakers": breaker_map,
            "bus_trust": bus_trust_map,
            "line_trust": line_trust_map,
            "anomaly_score": round(float(anomaly), 3),
            "pinn_confidence": round(float(pinn_conf), 3),
            "cascade_risk": round(float(cascade_risk), 3),
            "flisr_state": self.flisr_states.get(float(flisr_code), "UNKNOWN"),
            "observability": "DEGRADED" if observability < 0.5 else "NOMINAL",
            "cyber_instability_probability": round(float(cyber_prob), 3),
            "threat_severity": self.severity_states.get(float(threat_sev_code), "LOW"),
            "islanding_active": islanding > 0.5,
            "override_active": override_active > 0.5,
            "trusted_state_quality": trusted_state_quality,
            "warnings": warnings
        }
