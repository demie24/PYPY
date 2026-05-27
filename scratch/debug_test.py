import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "core", "self_healing")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "core", "digital_twin")))

from recovery_state_machine import RecoveryStateMachine
fsm = RecoveryStateMachine()

breakers = {line["id"]: "CLOSED" for line in fsm.topo_engine.topo.lines}
breakers["L7_8"] = "OPEN"
breakers["L8_9"] = "OPEN"

# Dry run CLOSE L7_8
breakers_dry = breakers.copy()
breakers_dry["L7_8"] = "CLOSED"

connected_dry = fsm.validator.sandbox.physics._get_connected_buses(breakers_dry)
print("Connected buses in dry run:", connected_dry)

# Let's print the actual result from dry_run_action
telemetry = {
    "state": {
        "breakers": breakers,
        "buses": {f"Bus_{i+1}": {"voltage_pu": 1.0 if i != 7 else 0.0} for i in range(9)},
        "lines": {line["id"]: {"capacity_pct": 20.0} for line in fsm.topo_engine.topo.lines}
    }
}
fsm.validator.sandbox.reset_to_state(telemetry)
res = fsm.validator.sandbox.dry_run_action("REROUTE_FLOW", "L7_8")
print("dry_run_action output Voltages:", res["predicted_voltages"])
print("dry_run_action output Loadings:", res["predicted_loadings"])
