from unittest.mock import patch

import numpy as np
import pandas as pd

from core.digital_twin.solver import GridACSolver


def test_solver_uses_flat_start_after_previous_non_convergence():
    solver = GridACSolver()
    solver.net.converged = False
    solver.net.res_bus.loc[:, "vm_pu"] = np.nan

    calls = []

    def successful_runpp(net, **kwargs):
        calls.append(kwargs)
        net.converged = True
        net.res_bus.loc[:, "vm_pu"] = 1.0
        net.res_bus.loc[:, "va_degree"] = 0.0
        net.res_bus.loc[:, "p_mw"] = 0.0
        net.res_bus.loc[:, "q_mvar"] = 0.0
        net.res_line = pd.DataFrame(0.0, index=net.line.index, columns=["p_from_mw", "q_from_mvar", "i_ka"])
        net.res_trafo = pd.DataFrame(0.0, index=net.trafo.index, columns=["p_hv_mw", "q_hv_mvar", "i_hv_ka"])
        net._ppc = {"iterations": 1}

    with patch("core.digital_twin.solver.pp.runpp", side_effect=successful_runpp):
        *_, status = solver.solve_ac({}, {}, {}, {})

    assert calls[0]["init"] == "flat"
    assert status == {"converged": True, "mode": "converged", "iterations": 1}


def test_solver_fallback_never_reuses_failed_results():
    solver = GridACSolver()
    calls = []

    def runpp_with_fallback(net, **kwargs):
        calls.append(kwargs)
        if kwargs["algorithm"] == "nr":
            raise RuntimeError("forced NR failure")
        net.converged = True
        net.res_bus.loc[:, ["vm_pu", "va_degree", "p_mw", "q_mvar"]] = 0.0
        net.res_line = pd.DataFrame(0.0, index=net.line.index, columns=["p_from_mw", "q_from_mvar", "i_ka"])
        net.res_trafo = pd.DataFrame(0.0, index=net.trafo.index, columns=["p_hv_mw", "q_hv_mvar", "i_hv_ka"])
        net._ppc = {"iterations": 2}

    with patch("core.digital_twin.solver.pp.runpp", side_effect=runpp_with_fallback):
        *_, status = solver.solve_ac({}, {}, {}, {})

    assert calls[1]["init"] == "flat"
    assert status["mode"] == "fallback_decoupled"
