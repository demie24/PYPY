import logging
from typing import Dict, Any, List

logger = logging.getLogger("self_healing.stabilization_agent")

class StabilizationAgent:
    """
    Responsibilities: voltage stabilization, frequency stabilization, proactive balancing, 
    instability damping, load-generation equilibrium.
    """
    def __init__(self):
        self.agent_name = "StabilizationAgent"
        self.confidence = 1.0

    def evaluate(self, telemetry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyzes bus voltages, line overloads, and island frequencies to compile proposals.
        """
        if not telemetry:
            return {"proposals": [], "confidence": 1.0}

        proposals = []
        state_data = telemetry.get("state", {})
        buses = state_data.get("buses", {})
        lines = state_data.get("lines", {})

        # Compute average frequency and voltage deviation
        avg_freq = 60.0
        freq_count = 0
        v_dev_sum = 0.0
        v_count = 0

        # We also check for any island frequency telemetry
        # telemetry might contain l6_balancing frequencies
        balancing_data = telemetry.get("l6_balancing", {})
        frequencies = balancing_data.get("frequencies", {})
        
        # If we have balancing frequencies, use the lowest one
        if frequencies:
            avg_freq = min(frequencies.values())
        else:
            # Fallback to bus frequencies
            bus_freqs = []
            for b_data in buses.values():
                if "frequency_hz" in b_data:
                    bus_freqs.append(b_data["frequency_hz"])
            if bus_freqs:
                avg_freq = min(bus_freqs)

        for b_data in buses.values():
            v = b_data.get("voltage_pu", 1.0)
            if v > 0.0:
                v_dev_sum += abs(1.0 - v)
                v_count += 1

        avg_v_dev = v_dev_sum / v_count if v_count > 0 else 0.0

        # Calculate agent confidence:
        # High when frequency is 60Hz and voltage deviation is 0
        freq_dev = abs(60.0 - avg_freq)
        self.confidence = max(0.2, 1.0 - (freq_dev * 0.1) - (avg_v_dev * 2.0))

        # 1. Propose adjusting generator output if mismatch is present
        mismatches = balancing_data.get("mismatches", {})
        for island_id, mismatch in mismatches.items():
            if abs(mismatch) > 5.0:
                proposals.append({
                    "command": "ADJUST_GEN",
                    "target": "SYSTEM",
                    "reason": f"StabilizationAgent: Adjust generation output due to island {island_id} mismatch of {mismatch:.1f} MW",
                    "priority": "HIGH"
                })

        # 2. Propose load shedding if frequency is low
        if avg_freq < 59.5:
            # Identify high load buses to shed (e.g. Bus 6 or 8)
            # Find the active load on Bus 6 and Bus 8
            for bus_name in ["Bus_6", "Bus_8"]:
                bus_data = buses.get(bus_name, {})
                if bus_data.get("P_mw", 0.0) > 10.0:
                    proposals.append({
                        "command": "SHED_LOAD",
                        "target": bus_name,
                        "percentage": 20.0,
                        "reason": f"StabilizationAgent: Proposing proactive load shed on {bus_name} to damp frequency decay (freq={avg_freq:.2f}Hz)",
                        "priority": "CRITICAL" if avg_freq < 59.0 else "HIGH"
                    })

        return {
            "proposals": proposals,
            "confidence": round(self.confidence, 2),
            "avg_freq": round(avg_freq, 2),
            "avg_v_dev": round(avg_v_dev, 3)
        }

    def vote(self, proposal: Dict[str, Any], context: Dict[str, Any]) -> float:
        """
        Votes on proposed grid actions.
        """
        command = proposal.get("command")
        target = proposal.get("target")

        # 1. Veto breaker CLOSE commands if they are overloaded or predicted to trip
        telemetry = context.get("telemetry", {})
        if telemetry:
            lines = telemetry.get("state", {}).get("lines", {})
            line_data = lines.get(target)
            if line_data and line_data.get("capacity_pct", 0.0) > 110.0:
                logger.warning(f"[{self.agent_name}] Vetoing {command} on {target} (capacity exceeds 110%)")
                return -1.0

        # 2. Endorse SHED_LOAD if frequency is critically low
        avg_freq = context.get("avg_freq", 60.0)
        if command == "SHED_LOAD" and avg_freq < 59.2:
            return 1.0

        # 3. Endorse ADJUST_GEN under mismatches
        if command == "ADJUST_GEN":
            return 0.8

        return 0.0
