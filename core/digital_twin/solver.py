import pandapower as pp
import numpy as np
import logging
from grid_loader import IEEE39BusLoader

logger = logging.getLogger("digital_twin.solver")

class GridACSolver:
    def __init__(self, loader: IEEE39BusLoader = None):
        if loader is None:
            self.loader = IEEE39BusLoader()
        else:
            self.loader = loader
        self.net = self.loader.get_net()

    def solve_ac(self, breakers: dict, active_loads: dict, generator_P: dict, generator_Q: dict, generators_online: dict = None):
        """
        Executes AC Power Flow using pandapower with solver cascading.
        Returns:
            V (np.ndarray): Voltage magnitudes in p.u.
            theta (np.ndarray): Voltage angles in radians.
            P (np.ndarray): Nodal active power injection in p.u. (MVA Base = 100).
            Q (np.ndarray): Nodal reactive power injection in p.u.
            line_flows (dict): Flows and currents per branch.
            status (dict): Convergence logs ("converged", "mode", "iterations").
        """
        if generators_online is None:
            generators_online = {}

        # 1. Update line and transformer breaker states (in_service)
        for idx in self.net.line.index:
            line_id = f"L_line_{idx}"
            self.net.line.at[idx, "in_service"] = (breakers.get(line_id, "CLOSED") == "CLOSED")

        for idx in self.net.trafo.index:
            trafo_id = f"L_trafo_{idx}"
            self.net.trafo.at[idx, "in_service"] = (breakers.get(trafo_id, "CLOSED") == "CLOSED")

        # 2. Update active loads demand
        # active_loads keys are 0-indexed bus numbers
        for idx, row in self.net.load.iterrows():
            bus = int(row.bus)
            if bus in active_loads:
                # v8.0 active_loads input is in p.u. -> convert to MW/Mvar
                self.net.load.at[idx, "p_mw"] = float(active_loads[bus]["P"]) * 100.0
                self.net.load.at[idx, "q_mvar"] = float(active_loads[bus]["Q"]) * 100.0

        # 3. Update generator setpoints and statuses
        for idx, row in self.net.gen.iterrows():
            bus = int(row.bus)
            if bus in generator_P:
                self.net.gen.at[idx, "p_mw"] = float(generator_P[bus]) * 100.0
            if bus in generators_online:
                self.net.gen.at[idx, "in_service"] = bool(generators_online[bus])

        for idx, row in self.net.ext_grid.iterrows():
            bus = int(row.bus)
            if bus in generators_online:
                self.net.ext_grid.at[idx, "in_service"] = bool(generators_online[bus])

        # 4. Execute Solver Cascade
        status = {
            "converged": False,
            "mode": "failed",
            "iterations": 0
        }

        try:
            # Step A: Newton-Raphson solver (Standard)
            pp.runpp(self.net, algorithm="nr", init="results", numba=True)
            status["converged"] = True
            status["mode"] = "converged"
            status["iterations"] = self.net._ppc["iterations"]
        except (pp.LoadflowNotConverged, Exception):
            logger.warning("Newton-Raphson AC solver failed. Attempting Decoupled NR fallback...")
            try:
                # Step B: Fast Decoupled AC solver
                pp.runpp(self.net, algorithm="fdpf", init="results")
                status["converged"] = True
                status["mode"] = "fallback_decoupled"
                status["iterations"] = self.net._ppc["iterations"]
            except (pp.LoadflowNotConverged, Exception):
                logger.error("AC Power flow non-convergence. Running State Estimation fallback...")
                try:
                    # Step C: Run State Estimation to approximate metrics
                    pp.runse(self.net)
                    status["converged"] = False
                    status["mode"] = "fallback_se"
                    status["iterations"] = 0
                except Exception as se_err:
                    logger.error(f"State Estimation fallback also failed: {se_err}")
                    # Revert to flat-start zero values or default
                    status["converged"] = False
                    status["mode"] = "failed"

        # 5. Extract calculated state variables
        num_buses = len(self.net.bus)
        V = np.ones(num_buses)
        theta = np.zeros(num_buses)
        P = np.zeros(num_buses)
        Q = np.zeros(num_buses)
        line_flows = {}

        if status["mode"] != "failed":
            # Extract bus voltages and angles
            # Note: res_bus contains vm_pu and va_degree results sorted by bus index
            V = self.net.res_bus.vm_pu.values
            theta = np.radians(self.net.res_bus.va_degree.values)
            
            # Active/reactive injections in p.u. (MVA Base = 100)
            P = self.net.res_bus.p_mw.values / 100.0
            Q = self.net.res_bus.q_mvar.values / 100.0

            # Extract line flows
            for idx in self.net.line.index:
                line_id = f"L_line_{idx}"
                if self.net.line.at[idx, "in_service"]:
                    p_from = self.net.res_line.p_from_mw.at[idx] / 100.0
                    q_from = self.net.res_line.q_from_mvar.at[idx] / 100.0
                    i_ka = self.net.res_line.i_ka.at[idx]
                else:
                    p_from, q_from, i_ka = 0.0, 0.0, 0.0

                line_flows[line_id] = {
                    "P_flow": float(p_from),
                    "Q_flow": float(q_from),
                    "current": float(i_ka)
                }

            # Extract transformer flows
            for idx in self.net.trafo.index:
                trafo_id = f"L_trafo_{idx}"
                if self.net.trafo.at[idx, "in_service"]:
                    p_from = self.net.res_trafo.p_hv_mw.at[idx] / 100.0
                    q_from = self.net.res_trafo.q_hv_mvar.at[idx] / 100.0
                    i_ka = self.net.res_trafo.i_hv_ka.at[idx]
                else:
                    p_from, q_from, i_ka = 0.0, 0.0, 0.0

                line_flows[trafo_id] = {
                    "P_flow": float(p_from),
                    "Q_flow": float(q_from),
                    "current": float(i_ka)
                }
        else:
            # Failure state outputs (flat profiles)
            V = np.zeros(num_buses)
            theta = np.zeros(num_buses)
            P = np.zeros(num_buses)
            Q = np.zeros(num_buses)
            for idx in self.net.line.index:
                line_flows[f"L_line_{idx}"] = {"P_flow": 0.0, "Q_flow": 0.0, "current": 0.0}
            for idx in self.net.trafo.index:
                line_flows[f"L_trafo_{idx}"] = {"P_flow": 0.0, "Q_flow": 0.0, "current": 0.0}

        return V, theta, P, Q, line_flows, status
