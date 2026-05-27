import os
import sys
import logging
from typing import Dict, Any, List

# Setup import paths
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from topology_recovery_engine import TopologyRecoveryEngine

logger = logging.getLogger("self_healing.proactive_rerouting")

class ProactiveReroutingEngine:
    """
    Executes pre-emptive topology rerouting, recommending alternate power paths before overload,
    reducing cascading collapse risk proactively.
    """
    def __init__(self, topology_engine=None):
        self.topo_engine = topology_engine if topology_engine else TopologyRecoveryEngine()

    def analyze_rerouting(self, telemetry: Dict[str, Any], predictive_stability: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyzes line loadings and predictive stability results.
        Recommends alternate paths if overloads are predicted or active.
        """
        if not telemetry:
            return {
                "proactive_rerouting_active": False,
                "recommended_rerouting": [],
                "reason": "No telemetry data"
            }

        state = telemetry.get("state", {})
        breakers = state.get("breakers", {})
        lines = state.get("lines", {})

        # Find if any line is overloaded (> 80%) or predicted to trip
        overloaded_lines = []
        for line_id, line_data in lines.items():
            if line_data.get("capacity_pct", 0.0) > 80.0:
                overloaded_lines.append(line_id)

        predicted_overloads = [o["line_id"] for o in predictive_stability.get("predicted_overloads", [])]
        high_risk_lines = list(set(overloaded_lines + predicted_overloads))

        if not high_risk_lines:
            return {
                "proactive_rerouting_active": False,
                "recommended_rerouting": [],
                "reason": "Grid loadings within nominal thresholds."
            }

        recommended_rerouting = []
        
        # Check if the tie line L7_8 is open and can be closed proactively
        if breakers.get("L7_8", "OPEN") == "OPEN":
            # Check if there is an active overload on lines that feed Bus 7 or 8 (L2_7, L6_7, L8_9, L3_9)
            # Closing L7_8 would connect Bus 7 and Bus 8, redistributing the power flow between Gen 2 and Gen 3
            # We can formulate a proactive closing recommendation
            recommended_rerouting.append({
                "command": "CLOSE",
                "target": "L7_8",
                "reason": f"Proactive Rerouting: Close tie line L7_8 to relieve overloaded paths: {', '.join(high_risk_lines)}"
            })

        # We can also check if other closed lines can be toggled if we had alternate meshes,
        # but in IEEE 9-bus with L7_8 open, L7_8 is the primary tie line.
        # Let's check if there are other open lines (e.g. manually opened breakers) that can be closed
        for line_id, breaker_status in breakers.items():
            if breaker_status == "OPEN" and line_id != "L7_8":
                # If a line is open but NOT faulty (not compromised/tripped by relay), closing it might help
                # Let's check if closing this line connects a high-risk line's terminal buses to another generator
                line_data = next((l for l in self.topo_engine.topo.lines if l["id"] == line_id), None)
                if line_data:
                    f_bus, t_bus = line_data["from"], line_data["to"]
                    # If this connects to a bus on the high-risk lines, recommend closing it
                    for hr_line in high_risk_lines:
                        hr_data = next((l for l in self.topo_engine.topo.lines if l["id"] == hr_line), None)
                        if hr_data and (f_bus in [hr_data["from"], hr_data["to"]] or t_bus in [hr_data["from"], hr_data["to"]]):
                            recommended_rerouting.append({
                                "command": "CLOSE",
                                "target": line_id,
                                "reason": f"Proactive Rerouting: Close line {line_id} to support alternate path around overloaded {hr_line}"
                            })
                            break

        return {
            "proactive_rerouting_active": len(recommended_rerouting) > 0,
            "recommended_rerouting": recommended_rerouting,
            "reason": f"Active overloads detected on {', '.join(high_risk_lines)}. Recommending path configuration changes."
        }
