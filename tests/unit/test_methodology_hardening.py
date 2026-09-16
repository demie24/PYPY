import numpy as np
import pandas as pd

from core.ai_training.temporal_split import chronological_label_partitions, overlap_report, window_spans
from core.self_healing.restoration_sandbox import RestorationSandbox
from core.threat_engine.scorer import ThreatScoringEngine


class PhysicsStub:
    def __init__(self, voltage=1.0, current=0.1, status=None, nonfinite=False):
        self.voltage = voltage
        self.current = current
        self.last_solver_status = status or {"converged": True, "mode": "test"}
        self.nonfinite = nonfinite

    def solve(self, breakers, loads, gen_p, gen_q):
        n = 9
        v = np.full(n, self.voltage)
        if self.nonfinite:
            v[0] = np.nan
        flows = {key: {"P_flow": 0.0, "Q_flow": 0.0, "current": self.current} for key in breakers}
        return v, np.zeros(n), np.zeros(n), np.zeros(n), flows


def test_corrected_temporal_split_has_no_raw_overlap():
    df = pd.DataFrame({"label": ["A"] * 100 + ["B"] * 100})
    partitions = chronological_label_partitions(df)
    spans = {name: window_spans(part.raw_indices, 20, 5) for name, part in partitions.items()}
    report = overlap_report(spans)
    assert all(item["overlapping_raw_observations"] == 0 for item in report["pairwise_overlap"].values())


def test_sandbox_rejects_non_converged_solution():
    sandbox = RestorationSandbox(physics=PhysicsStub(status={"converged": False, "mode": "failed"}))
    result = sandbox.dry_run_action("OPEN", "L1_4")
    assert not result["overall_safe"]
    assert result["rejection_reason"] == "solver_non_convergence"


def test_sandbox_rejects_nonfinite_solution():
    sandbox = RestorationSandbox(physics=PhysicsStub(nonfinite=True))
    result = sandbox.dry_run_action("OPEN", "L1_4")
    assert not result["finite_state"]
    assert result["rejection_reason"] == "non_finite_state"


def test_sandbox_rejects_voltage_thermal_and_invalid_topology():
    voltage = RestorationSandbox(physics=PhysicsStub(voltage=0.80)).dry_run_action("OPEN", "L1_4")
    thermal = RestorationSandbox(physics=PhysicsStub(current=2.0)).dry_run_action("OPEN", "L1_4")
    topology = RestorationSandbox(physics=PhysicsStub()).dry_run_action("OPEN", "DOES_NOT_EXIST")
    assert voltage["rejection_reason"] == "voltage_violation"
    assert thermal["rejection_reason"] == "thermal_violation"
    assert topology["rejection_reason"] == "invalid_topology_target"


def test_blind_threat_mode_ignores_attack_ground_truth():
    telemetry = {"state": {"buses": {}, "lines": {}, "breakers": {}},
                 "attack_status": {"active_attack": "FDIA", "compromised_nodes": {"Bus_5": {}}}}
    blind = ThreatScoringEngine("blind").calculate_threat(telemetry)
    aware = ThreatScoringEngine("experiment_aware").calculate_threat(telemetry)
    assert blind["evaluation_mode"] == "blind"
    assert aware["threat_score"] > blind["threat_score"]


def test_ieee39_current_contract_exposes_canonical_units():
    source = open("core/digital_twin/main.py", encoding="utf-8").read()
    assert '"current_ka"' in source
    assert '"current_loading_pu"' in source
