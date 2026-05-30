import logging
from typing import Dict, Any, List, Tuple

logger = logging.getLogger("assistant.telemetry_correlation")

class TelemetryCorrelationEngine:
    def __init__(self, window_size: int = 15):
        self.window_size = window_size
        self.history: Dict[str, List[float]] = {}
        self.correlation_matrix: Dict[str, Dict[str, float]] = {}
        self.cascades: List[Dict[str, Any]] = []
        self.linkage_logs: List[str] = []
        self.event_sequence: List[Tuple[str, float]] = [] # (event_desc, timestamp)

    def add_telemetry_snapshot(self, snapshot: Dict[str, Any], current_time: float):
        """Appends new telemetry values to rolling history and recalculates correlations."""
        for key, val in snapshot.items():
            if isinstance(val, (int, float)):
                if key not in self.history:
                    self.history[key] = []
                self.history[key].append(float(val))
                # Keep rolling window size
                if len(self.history[key]) > self.window_size:
                    self.history[key].pop(0)

        self._compute_correlations()
        self._analyze_cascades(snapshot, current_time)

    def _compute_correlations(self):
        """Calculates Pearson correlation coefficients between key telemetry variables."""
        target_keys = [k for k in self.history.keys() if ("_v" in k or "_load" in k)]
        
        for k1 in target_keys:
            if k1 not in self.correlation_matrix:
                self.correlation_matrix[k1] = {}
            for k2 in target_keys:
                if k1 == k2:
                    self.correlation_matrix[k1][k2] = 1.0
                    continue
                
                corr = self._pearson_correlation(self.history[k1], self.history[k2])
                self.correlation_matrix[k1][k2] = corr

    def _pearson_correlation(self, x: List[float], y: List[float]) -> float:
        n = min(len(x), len(y))
        if n < 5: # Require at least 5 points to start correlation analysis
            return 0.0
            
        x_trimmed = x[-n:]
        y_trimmed = y[-n:]
        
        mean_x = sum(x_trimmed) / n
        mean_y = sum(y_trimmed) / n
        
        var_x = sum((xi - mean_x) ** 2 for xi in x_trimmed)
        var_y = sum((yi - mean_y) ** 2 for yi in y_trimmed)
        
        if var_x < 1e-8 or var_y < 1e-8:
            if var_x < 1e-8 and var_y < 1e-8:
                return 1.0 # Both are constant
            return 0.0 # One is constant, other is not
            
        cov = sum((x_trimmed[i] - mean_x) * (y_trimmed[i] - mean_y) for i in range(n))
        return cov / ((var_x * var_y) ** 0.5)

    def _analyze_cascades(self, snapshot: Dict[str, Any], current_time: float):
        """Tracks sequential telemetry events to detect cascading patterns and event linkage scores."""
        # Detect breaker opening or voltage drops
        for k, v in snapshot.items():
            if k.startswith("breaker_") and v == 0.0:
                event_name = f"{k}_OPEN"
                if not any(e[0] == event_name for e in self.event_sequence[-5:]):
                    self.event_sequence.append((event_name, current_time))
                    self.linkage_logs.append(f"[{current_time:.1f}s] Breaker event: {event_name}")
            elif k.startswith("bus_") and k.endswith("_v") and v < 0.90:
                event_name = f"{k}_UNDERVOLTAGE"
                if not any(e[0] == event_name for e in self.event_sequence[-5:]):
                    self.event_sequence.append((event_name, current_time))
                    self.linkage_logs.append(f"[{current_time:.1f}s] Voltage anomaly: {event_name} ({v:.2f} p.u.)")
            elif k.startswith("line_") and k.endswith("_load") and v > 100.0:
                event_name = f"{k}_OVERLOAD"
                if not any(e[0] == event_name for e in self.event_sequence[-5:]):
                    self.event_sequence.append((event_name, current_time))
                    self.linkage_logs.append(f"[{current_time:.1f}s] Overload event: {event_name} ({v:.1f}%)")

        # Prune event sequence to keep last 60 seconds
        self.event_sequence = [e for e in self.event_sequence if current_time - e[1] <= 60.0]
        self.linkage_logs = self.linkage_logs[-15:] # Keep last 15 logs
        
        # Look for sequential linkage: a breaker trip followed by a line overload within 10s
        self.cascades.clear()
        for i in range(len(self.event_sequence)):
            for j in range(i + 1, len(self.event_sequence)):
                e1, t1 = self.event_sequence[i]
                e2, t2 = self.event_sequence[j]
                
                # Linkage logic: Trip -> Overload or Trip -> Undervoltage sequence
                if t2 - t1 <= 10.0 and ("OPEN" in e1 or "OVERLOAD" in e1) and ("UNDERVOLTAGE" in e2 or "OVERLOAD" in e2):
                    linkage_score = 0.90 if "OPEN" in e1 else 0.70
                    self.cascades.append({
                        "cause": e1,
                        "effect": e2,
                        "delay_seconds": round(t2 - t1, 2),
                        "linkage_score": linkage_score
                    })

    def get_status_summary(self) -> Dict[str, Any]:
        """Exposes dynamic correlation list, cascades, and logs."""
        # Find high correlation pairs (absolute correlation > 0.75, excluding self-relations)
        high_correlations = []
        for k1, v in self.correlation_matrix.items():
            for k2, corr in v.items():
                if k1 < k2 and abs(corr) > 0.75:
                    high_correlations.append({
                        "var1": k1,
                        "var2": k2,
                        "correlation": round(corr, 3)
                    })

        return {
            "high_correlations": high_correlations[:10], # Limit to top 10
            "cascades": self.cascades,
            "linkage_logs": self.linkage_logs,
            "correlation_matrix_size": len(self.correlation_matrix)
        }

    def reset_engine(self):
        """Wipes rolling buffer history and linkage event queues."""
        self.history.clear()
        self.correlation_matrix.clear()
        self.cascades.clear()
        self.linkage_logs.clear()
        self.event_sequence.clear()
