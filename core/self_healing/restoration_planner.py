import os
import sys
import logging
from typing import Dict, List, Any, Tuple

# Setup import paths
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(CURRENT_DIR)

from core.self_healing.topology_recovery_engine import TopologyRecoveryEngine
from core.self_healing.restoration_validator import RestorationValidator

logger = logging.getLogger("self_healing.restoration_planner")

class RestorationPlanner:
    """
    Generates multi-step breaker close/open restoration sequences.
    Prioritizes restoration paths using stability-aware heuristics.
    """
    def __init__(self, topology_engine=None, validator=None):
        self.topo_engine = topology_engine if topology_engine else TopologyRecoveryEngine()
        self.validator = validator if validator else RestorationValidator()
        
    def plan_restoration(self, telemetry: Dict[str, Any], faulted_breakers: list = None) -> List[Dict[str, Any]]:
        """
        Generates an ordered sequence of restoration commands.
        """
        if not telemetry:
            return []

        state = telemetry.get("state", {})
        breakers = state.get("breakers", {})
        
        # 1. Run BFS/DFS topology analysis
        topo_analysis = self.topo_engine.analyze_topology(telemetry)
        isolated_segments = topo_analysis["isolated_segments"]
        reroute_options = topo_analysis["reroute_options"]
        
        # Filter out options that are in faulted_breakers
        if faulted_breakers:
            reroute_options = [opt for opt in reroute_options if opt["line_id"] not in faulted_breakers]
        
        # Filter out isolated segments that do not contain loads (e.g. isolated junctions)
        isolated_loads_exist = False
        for comp in isolated_segments:
            if any(self.topo_engine.topo.loads.get(bus) is not None for bus in comp):
                isolated_loads_exist = True
                break
                
        if not isolated_loads_exist:
            logger.info("No isolated loads identified. Active planning bypassed.")
            return []
            
        sequence = []
        
        # 2. Validate and prioritize routing options
        validated_options = []
        for option in reroute_options:
            lid = option["line_id"]
            val_res = self.validator.validate_action(telemetry, "REROUTE_FLOW", lid)
            if val_res["is_safe"]:
                validated_options.append({
                    "line_id": lid,
                    "score": val_res["safety_score"],
                    "confidence": val_res["confidence"]
                })
            else:
                logger.warning(f"Rerouting option {lid} rejected by planner validation: {val_res['violations']}")
                
        # Sort options: higher safety score and confidence first
        validated_options.sort(key=lambda x: (x["score"], x["confidence"]), reverse=True)
        
        for opt in validated_options:
            sequence.append({
                "command": "CLOSE",
                "target": opt["line_id"],
                "reason": f"Reroute flow via tie-breaker {opt['line_id']} to restore de-energized subgrid segment."
            })
            
        # 3. Rehearse the entire multi-step sequence sequentially in the sandbox
        if sequence:
            rehearsal_steps = [(s["command"], s["target"]) for s in sequence]
            self.validator.sandbox.reset_to_state(telemetry)
            all_safe, results = self.validator.sandbox.rehearse_sequence(rehearsal_steps)
            if not all_safe:
                logger.error("Sequential rehearsal validation failed. Trimming unsafe steps...")
                safe_sequence = []
                for idx, step_res in enumerate(results):
                    if step_res["result"]["allowed"]:
                        safe_sequence.append(sequence[idx])
                return safe_sequence
                
        return sequence
