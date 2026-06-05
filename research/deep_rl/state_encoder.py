import numpy as np
from typing import Dict, Any, List

class StateEncoder:
    def __init__(self, bus_ids: List[str] = None, line_ids: List[str] = None):
        """
        Initializes the state encoder with optional fixed bus and line identifiers to guarantee output size.
        If not provided, a default IEEE 9-bus template is used.
        """
        self.bus_ids = bus_ids or [f"Bus_{i}" for i in range(1, 10)]
        self.line_ids = line_ids or [
            "L1_4", "L2_7", "L3_9", "L4_5", "L4_9", "L5_6", "L6_7", "L7_8", "L8_9"
        ]

    @property
    def state_dim(self) -> int:
        """
        Returns the exact size of the encoded state vector.
        - Buses: voltage_pu, frequency_hz, trust_score, threat_score, anomaly_count (5 attributes per bus)
        - Lines: capacity_pct, current_pu (2 attributes per line)
        - Global/Status attributes: 4 features (restoration_completed, restoration_step, isolation_active, lockout_time)
        """
        return len(self.bus_ids) * 5 + len(self.line_ids) * 2 + 4

    def encode(self, grid_state: Dict[str, Any]) -> np.ndarray:
        """
        Converts the nested grid state dictionary into a deterministic, normalized 1D NumPy array of shape (state_dim,).
        """
        vector = []

        # 1. Encode Bus States
        buses = grid_state.get("buses", {})
        trust_scores = grid_state.get("trust_scores", {})
        threat_scores = grid_state.get("threat_scores", {})
        anomalies = grid_state.get("anomalies", {})

        for bus_id in self.bus_ids:
            bus_data = buses.get(bus_id, {})
            # Voltage (normally ~1.0 pu)
            voltage = float(bus_data.get("voltage_pu", 1.0))
            # Frequency (normally 60 Hz or 50 Hz, normalized around 1.0)
            freq = float(bus_data.get("frequency_hz", 60.0)) / 60.0
            
            # Trust score (normally 0.0 to 1.0)
            trust = float(trust_scores.get(bus_id, 1.0))
            # Threat score (normally 0.0 to 100.0)
            threat = float(threat_scores.get(bus_id, 0.0)) / 100.0
            # Anomaly indicator (0 or 1)
            anomaly = float(anomalies.get(bus_id, 0))

            vector.extend([voltage, freq, trust, threat, anomaly])

        # 2. Encode Line States
        lines = grid_state.get("lines", {})
        for line_id in self.line_ids:
            line_data = lines.get(line_id, {})
            capacity = float(line_data.get("capacity_pct", 50.0)) / 100.0
            current = float(line_data.get("current_pu", 0.5))
            vector.extend([capacity, current])

        # 3. Encode Global Restoration & Defense Status
        restoration = grid_state.get("restoration_status", {})
        defense = grid_state.get("defense_status", {})

        res_completed = 1.0 if restoration.get("completed", False) else 0.0
        res_step = float(restoration.get("step", 0)) / 10.0
        def_isolation = 1.0 if defense.get("isolation_active", False) else 0.0
        def_lockout = float(defense.get("rollback_lockout", 0.0)) / 60.0

        vector.extend([res_completed, res_step, def_isolation, def_lockout])

        return np.array(vector, dtype=np.float32)
