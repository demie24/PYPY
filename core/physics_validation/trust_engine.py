import numpy as np
import logging

logger = logging.getLogger("physics_validation.trust_engine")

class TrustEngine:
    def __init__(self, window_size=15):
        self.window_size = window_size
        
        # Grid layout names
        self.buses = [f"Bus_{i}" for i in range(1, 10)]
        self.lines = ["L1_4", "L2_7", "L3_9", "L4_5", "L4_9", "L5_6", "L6_7", "L7_8", "L8_9"]
        
        # Stateful buffers for signal analysis (voltages for buses, currents/flows for lines)
        self.bus_voltage_history = {b: [] for b in self.buses}
        self.line_current_history = {l: [] for l in self.lines}
        
        # State metrics (0.0 to 1.0)
        self.trust_scores = {node: 1.0 for node in self.buses + self.lines}
        self.stability_scores = {node: 1.0 for node in self.buses + self.lines}
        self.consistency_scores = {node: 1.0 for node in self.buses + self.lines}
        self.suspicion_scores = {node: 0.0 for node in self.buses + self.lines}
        
        # Rolling anomaly frequencies
        self.anomaly_frequencies = {node: 0.0 for node in self.buses + self.lines}
        
        # Recovery/Decay rates
        self.recovery_alpha = 0.05
        
        # Transient suppression states
        self.prev_breakers = {}
        self.transient_suppression_counter = 3
        
        # Stateful operator telemetry rejections
        self.distrusted_nodes = set()

        
    def update(self, telemetry, physics_report, ai_threat_prob):
        """
        Updates trust scores based on live telemetry, physics reports, and AI threat scores.
        """
        try:
            buses_data = telemetry["state"]["buses"]
            lines_data = telemetry["state"]["lines"]
            breakers = telemetry["state"]["breakers"]
        except KeyError as e:
            logger.error(f"Cannot update trust score, missing telemetry key: {e}")
            return
            
        # Check for breaker switching transients to suppress false anomaly detections
        if self.prev_breakers:
            changes = sum(1 for lid, stat in breakers.items() if self.prev_breakers.get(lid) and self.prev_breakers[lid] != stat)
            if changes > 0:
                self.transient_suppression_counter = 2
        self.prev_breakers = breakers.copy()

        transient_active = False
        if self.transient_suppression_counter > 0:
            self.transient_suppression_counter -= 1
            transient_active = True
            
        kcl_details = physics_report.get("kcl_details", {})
        kvl_details = physics_report.get("kvl_details", {})
        bus_mismatches = kcl_details.get("bus_mismatches", {})
        line_mismatches = kvl_details.get("line_mismatches", {})
        impossible_violations = physics_report.get("impossible_violations", [])
        
        # Parse which nodes are flagged in impossible violations
        impossible_buses = set()
        impossible_lines = set()
        for violation in impossible_violations:
            for b in self.buses:
                if b in violation:
                    impossible_buses.add(b)
            for l in self.lines:
                if l in violation:
                    impossible_lines.add(l)
                    
        # 1. Update Bus trust metrics
        for bus in self.buses:
            bus_data = buses_data.get(bus, {})
            v_pu = float(bus_data.get("voltage_pu", 1.0))
            
            # Update history and calculate stability
            history = self.bus_voltage_history[bus]
            history.append(v_pu)
            if len(history) > self.window_size:
                history.pop(0)
                
            if len(history) >= 3:
                var = float(np.var(history))
                # Scale variance to score: var of 0.005 pu^2 -> 0.5 stability reduction
                self.stability_scores[bus] = max(0.0, 1.0 - min(0.5, var * 100))
            else:
                self.stability_scores[bus] = 1.0
                
            # Physics Consistency based on KCL mismatch (P_mismatch_mw) and bounds check
            p_mismatch = abs(bus_mismatches.get(bus, {}).get("P_mismatch_mw", 0.0))
            # 10 MW active power mismatch drops consistency to 0
            kcl_cons = max(0.0, 1.0 - p_mismatch / 10.0)
            
            # If bus voltage is out of bounds or flagged in impossible states
            if v_pu < 0.94 or v_pu > 1.07 or bus in impossible_buses:
                kcl_cons = 0.0
                
            self.consistency_scores[bus] = kcl_cons
            
            # Cyber Suspicion: Fuses AI Threat probability and local physics discrepancy
            # Suspicion increases if grid is threatened and this node is physically inconsistent
            node_inconsistent = 1.0 - kcl_cons
            self.suspicion_scores[bus] = ai_threat_prob * node_inconsistent
            
            # Target Trust
            target_trust = self.stability_scores[bus] * self.consistency_scores[bus] * (1.0 - self.suspicion_scores[bus])
            if bus in self.distrusted_nodes:
                target_trust = 0.0
            
            # Asymmetric decay/recovery
            current_trust = self.trust_scores[bus]
            if transient_active:
                target_trust = current_trust
            if target_trust < current_trust:
                # Fast degradation
                self.trust_scores[bus] = target_trust
            else:
                # Slow recovery
                self.trust_scores[bus] = current_trust + self.recovery_alpha * (target_trust - current_trust)
                
            # Rolling anomaly frequency
            is_anomalous = 1.0 if (self.consistency_scores[bus] < 0.90 or self.stability_scores[bus] < 0.90) else 0.0
            self.anomaly_frequencies[bus] = self.anomaly_frequencies[bus] + 0.1 * (is_anomalous - self.anomaly_frequencies[bus])
            
        # 2. Update Line trust metrics
        for line in self.lines:
            line_data = lines_data.get(line, {})
            i_pu = float(line_data.get("current_pu", 0.0))
            
            # Update history and calculate stability
            history = self.line_current_history[line]
            history.append(i_pu)
            if len(history) > self.window_size:
                history.pop(0)
                
            if len(history) >= 3:
                var = float(np.var(history))
                # Scale variance to score: var of 0.05 pu^2 -> 0.5 stability reduction
                self.stability_scores[line] = max(0.0, 1.0 - min(0.5, var * 10))
            else:
                self.stability_scores[line] = 1.0
                
            # Physics Consistency based on KVL mismatch
            line_miss = line_mismatches.get(line, {})
            v_miss = abs(line_miss.get("Q_mismatch_pu", 0.0))
            p_miss = abs(line_miss.get("P_mismatch_pu", 0.0))
            tot_miss = v_miss + p_miss
            
            # 0.05 p.u. active/reactive mismatch drops consistency to 0
            kvl_cons = max(0.0, 1.0 - tot_miss / 0.05)
            
            # If line is in impossible violation (e.g. open line with flow)
            if line in impossible_lines:
                kvl_cons = 0.0
                
            self.consistency_scores[line] = kvl_cons
            
            # Cyber suspicion
            node_inconsistent = 1.0 - kvl_cons
            self.suspicion_scores[line] = ai_threat_prob * node_inconsistent
            
            # Target Trust
            target_trust = self.stability_scores[line] * self.consistency_scores[line] * (1.0 - self.suspicion_scores[line])
            if line in self.distrusted_nodes:
                target_trust = 0.0
            
            # Asymmetric decay/recovery
            current_trust = self.trust_scores[line]
            if transient_active:
                target_trust = current_trust
            if target_trust < current_trust:
                self.trust_scores[line] = target_trust
            else:
                self.trust_scores[line] = current_trust + self.recovery_alpha * (target_trust - current_trust)
                
            # Rolling anomaly frequency
            is_anomalous = 1.0 if (self.consistency_scores[line] < 0.90 or self.stability_scores[line] < 0.90) else 0.0
            self.anomaly_frequencies[line] = self.anomaly_frequencies[line] + 0.1 * (is_anomalous - self.anomaly_frequencies[line])

    def reject_node(self, node: str):
        """
        Manually forces a node's trust score to 0 statefully.
        """
        self.distrusted_nodes.add(node)
        self.trust_scores[node] = 0.0

    def get_scores(self):
        """
        Returns compiled trust and health metrics for the HMI dashboard.
        """
        details = {}
        for node in self.buses + self.lines:
            details[node] = {
                "trust_score": round(self.trust_scores[node] * 100, 2),
                "stability_score": round(self.stability_scores[node] * 100, 2),
                "physics_consistency_score": round(self.consistency_scores[node] * 100, 2),
                "cyber_suspicion_score": round(self.suspicion_scores[node] * 100, 2),
                "anomaly_frequency": round(self.anomaly_frequencies[node] * 100, 2)
            }
        return {
            "bus_trust": {b: round(self.trust_scores[b] * 100, 1) for b in self.buses},
            "line_trust": {l: round(self.trust_scores[l] * 100, 1) for l in self.lines},
            "details": details
        }
