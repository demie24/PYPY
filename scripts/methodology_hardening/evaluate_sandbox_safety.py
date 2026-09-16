#!/usr/bin/env python3
"""Exercise explicit restoration-sandbox rejection modes."""

import json, sys, time
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from core.self_healing.restoration_sandbox import RestorationSandbox


class Physics:
    def __init__(self, voltage=1.0, current=.1, converged=True, nonfinite=False):
        self.voltage, self.current, self.nonfinite = voltage, current, nonfinite
        self.last_solver_status = {"converged": converged, "mode": "test" if converged else "failed"}
    def solve(self, breakers, *_):
        n = getattr(self, "n", 9)
        v = np.full(n, self.voltage)
        if self.nonfinite: v[0] = np.nan
        flows = {key: {"P_flow": 0., "Q_flow": 0., "current": self.current} for key in breakers}
        return v, np.zeros(n), np.zeros(n), np.zeros(n), flows


def run(name, physics, target=None):
    started = time.perf_counter()
    sandbox = RestorationSandbox(physics=physics)
    physics.n = sandbox.topo.num_buses
    target = target or next(iter(sandbox.breakers))
    result = sandbox.dry_run_action("OPEN", target)
    return {"case": name, "elapsed_ms": (time.perf_counter() - started) * 1000,
            "solver_converged": result["solver_converged"], "finite_state": result["finite_state"],
            "voltage_safe": result["voltage_safe"], "thermal_safe": result["thermal_safe"],
            "cascade_safe": result["cascade_safe"], "topology_valid": result["topology_valid"],
            "overall_safe": result["overall_safe"], "rejection_reason": result["rejection_reason"]}


def main():
    cases = [run("safe", Physics()), run("non_convergent", Physics(converged=False)),
             run("non_finite", Physics(nonfinite=True)), run("voltage_violation", Physics(voltage=.8)),
             run("thermal_violation", Physics(current=4.)), run("invalid_topology", Physics(), "INVALID")]
    report = {"schema_version": "pypy.sandbox-safety.v1", "cases": cases,
              "all_negative_cases_rejected": all(not row["overall_safe"] for row in cases[1:]),
              "safe_case_accepted": cases[0]["overall_safe"]}
    out = ROOT / "evaluation/methodology_hardening/sandbox_safety_report.json"
    out.write_text(json.dumps(report, indent=2) + "\n"); print(out)


if __name__ == "__main__": main()
