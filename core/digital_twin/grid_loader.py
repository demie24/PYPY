import pandapower as pp
import pandapower.networks as pn
import logging

logger = logging.getLogger("digital_twin.grid_loader")

class IEEE39BusLoader:
    def __init__(self):
        logger.info("Initializing IEEE 39-Bus New England System via pandapower...")
        try:
            # Load the standard IEEE 39-Bus case from pandapower networks
            self.net = pn.case39()
            logger.info("IEEE 39-Bus network loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load IEEE 39-Bus network: {e}")
            raise e

        # Expose baseline dimensions
        self.num_buses = len(self.net.bus)
        self.num_lines = len(self.net.line)
        self.num_generators = len(self.net.gen)
        self.num_loads = len(self.net.load)
        self.num_trafos = len(self.net.trafo)
        self.num_ext_grids = len(self.net.ext_grid)

    def get_net(self):
        """Returns the raw pandapowerNet object."""
        return self.net

    def get_buses(self):
        """Returns the buses dataframe containing name, vn_kv, zone, etc."""
        return self.net.bus

    def get_lines(self):
        """Returns the lines dataframe detailing line parameters and connections."""
        return self.net.line

    def get_generators(self):
        """Returns the generators dataframe (PV control points)."""
        return self.net.gen

    def get_loads(self):
        """Returns the loads dataframe detailing demand setpoints."""
        return self.net.load

    def get_transformers(self):
        """Returns the transformers (two-winding trafos) dataframe."""
        return self.net.trafo

    def get_external_grids(self):
        """Returns the external grid (slack bus connection) dataframe."""
        return self.net.ext_grid

    def get_summary(self) -> dict:
        """Returns a structural summary of the loaded network topology."""
        return {
            "buses": self.num_buses,
            "lines": self.num_lines,
            "generators": self.num_generators,
            "loads": self.num_loads,
            "transformers": self.num_trafos,
            "external_grids": self.num_ext_grids
        }

if __name__ == "__main__":
    # Self-test diagnostic
    logging.basicConfig(level=logging.INFO)
    loader = IEEE39BusLoader()
    print("Topology Summary:", loader.get_summary())
