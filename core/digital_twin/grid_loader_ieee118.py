"""
IEEE 118-Bus Grid Loader for PYPY V10.6 Cross-Grid Transfer Learning.
Uses pandapower's standard IEEE 118-bus case.
"""
import pandapower as pp
import pandapower.networks as pn
import logging

logger = logging.getLogger("digital_twin.grid_loader_ieee118")


class IEEE118BusLoader:
    """Loads the standard IEEE 118-bus test case via pandapower."""

    def __init__(self):
        logger.info("Initializing IEEE 118-Bus system via pandapower...")
        try:
            self.net = pn.case118()
            logger.info("IEEE 118-Bus network loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load IEEE 118-Bus network: {e}")
            raise e

        self.num_buses = len(self.net.bus)
        self.num_lines = len(self.net.line)
        self.num_generators = len(self.net.gen)
        self.num_loads = len(self.net.load)
        self.num_trafos = len(self.net.trafo)
        self.num_ext_grids = len(self.net.ext_grid)

    def get_net(self):
        return self.net

    def get_summary(self) -> dict:
        return {
            "grid": "IEEE118",
            "buses": self.num_buses,
            "lines": self.num_lines,
            "generators": self.num_generators,
            "loads": self.num_loads,
            "transformers": self.num_trafos,
            "external_grids": self.num_ext_grids,
        }
