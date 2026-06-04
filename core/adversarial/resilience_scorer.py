import logging
from typing import Dict, Any, List

logger = logging.getLogger("adversarial.resilience_scorer")

class ResilienceScorer:
    def __init__(self):
        pass

    def calculate_resilience(
        self, 
        eval_metrics: Dict[str, Any], 
        telemetry_history: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculate cyber, recovery, trust, and operational resilience metrics in range [0.0 - 1.0].
        """
        # 1. Cyber Resilience
        # High detection accuracy and low detection delay yield higher score
        det_acc = eval_metrics.get("detection_accuracy", 1.0)
        det_delay = eval_metrics.get("detection_delay", 15.0)
        cyber_res = float(max(0.10, min(1.0, det_acc * (1.0 - min(1.0, det_delay / 60.0)))))

        # 2. Recovery Resilience
        # Lower containment and restoration delays yield higher score
        cont_delay = eval_metrics.get("containment_delay", 20.0)
        rest_delay = eval_metrics.get("restoration_delay", 30.0)
        mit_success = eval_metrics.get("mitigation_success", True)
        
        rec_factor = 0.5 * (1.0 - min(1.0, cont_delay / 60.0)) + 0.5 * (1.0 - min(1.0, rest_delay / 90.0))
        if not mit_success:
            rec_factor *= 0.3  # Severe penalty for failed mitigation
        recovery_res = float(max(0.10, min(1.0, rec_factor)))

        # 3. Trust Resilience
        # Faster trust recovery yields higher score
        trust_rec_time = eval_metrics.get("trust_recovery_time", 45.0)
        trust_res = float(max(0.10, min(1.0, 1.0 - min(0.90, trust_rec_time / 120.0))))

        # 4. Operational Resilience
        # Evaluated from telemetry history (deviation of voltage and frequency from normal)
        dev_penalty = 0.0
        cycles_checked = 0
        
        for telemetry in telemetry_history:
            cycles_checked += 1
            buses = telemetry.get("state", {}).get("buses", {})
            for bus_name, data in buses.items():
                v = data.get("voltage_pu", 1.0)
                f = data.get("frequency_hz", 60.0)
                
                # Penalize voltage deviations outside [0.95, 1.05] pu
                if abs(1.0 - v) > 0.05:
                    dev_penalty += abs(1.0 - v) * 2.0
                
                # Penalize frequency deviations outside [59.5, 60.5] Hz
                if abs(60.0 - f) > 0.5:
                    dev_penalty += abs(60.0 - f) * 0.2

        if cycles_checked > 0:
            dev_score = max(0.0, min(0.90, dev_penalty / cycles_checked))
            operational_res = float(round(1.0 - dev_score, 2))
        else:
            operational_res = 0.90

        # Calculate average overall resilience score
        overall = float(round((cyber_res + recovery_res + trust_res + operational_res) / 4.0, 2))

        return {
            "cyber_resilience": float(round(cyber_res, 2)),
            "recovery_resilience": float(round(recovery_res, 2)),
            "trust_resilience": float(round(trust_res, 2)),
            "operational_resilience": operational_res,
            "overall_resilience_score": overall
        }
