"""
MultiGridTopology — Universal grid topology factory for PYPY V10.6.

Accepts grid_name in: "ieee14", "ieee39", "ieee57", "ieee118"
Returns a GridTopology-compatible object with identical API:
  .num_buses, .slack_bus, .generators, .loads, .lines

This allows all downstream engines (CascadingFailureSimulator, PtdfEngine,
UnifiedGridEncoder, etc.) to operate transparently on any grid size.
"""
import os
import sys
import logging

logger = logging.getLogger("digital_twin.multi_grid_topology")

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, project_root)


SUPPORTED_GRIDS = ["ieee14", "ieee39", "ieee57", "ieee118"]

# Maximum number of lines across all supported grids — used for zero-padded attack vectors
MAX_LINES = 186  # IEEE 118-bus has the most lines


class MultiGridTopology:
    """
    Universal grid topology object compatible with GridTopology API.
    Supports IEEE 14, 39, 57, and 118 bus systems.
    """

    def __init__(self, grid_name: str = "ieee39"):
        grid_name = grid_name.lower().strip()
        if grid_name not in SUPPORTED_GRIDS:
            raise ValueError(f"Unknown grid '{grid_name}'. Supported: {SUPPORTED_GRIDS}")

        self.grid_name = grid_name
        self._load_grid(grid_name)

    def _load_grid(self, grid_name: str):
        """Load the pandapower network and build the topology structures."""
        if grid_name == "ieee14":
            try:
                from core.digital_twin.grid_loader_ieee14 import IEEE14BusLoader
            except ModuleNotFoundError:
                from grid_loader_ieee14 import IEEE14BusLoader
            loader = IEEE14BusLoader()
        elif grid_name == "ieee39":
            try:
                from core.digital_twin.grid_loader import IEEE39BusLoader
            except ModuleNotFoundError:
                from grid_loader import IEEE39BusLoader
            loader = IEEE39BusLoader()
        elif grid_name == "ieee57":
            try:
                from core.digital_twin.grid_loader_ieee57 import IEEE57BusLoader
            except ModuleNotFoundError:
                from grid_loader_ieee57 import IEEE57BusLoader
            loader = IEEE57BusLoader()
        elif grid_name == "ieee118":
            try:
                from core.digital_twin.grid_loader_ieee118 import IEEE118BusLoader
            except ModuleNotFoundError:
                from grid_loader_ieee118 import IEEE118BusLoader
            loader = IEEE118BusLoader()
        else:
            raise ValueError(f"Unknown grid: {grid_name}")

        self.loader = loader
        self.net = loader.get_net()
        self.num_buses = loader.num_buses

        # Slack bus — from ext_grid
        self.slack_bus = int(self.net.ext_grid.bus.values[0]) if len(self.net.ext_grid) > 0 else 0

        # Build generators mapping
        self.generators = {}
        for idx, row in self.net.gen.iterrows():
            bus = int(row.bus)
            self.generators[bus] = {
                "name": f"Gen_Bus_{bus}",
                "P_nom": float(row.p_mw) / 100.0,
                "Q_nom": float(row.q_mvar) / 100.0 if hasattr(row, "q_mvar") and row.q_mvar == row.q_mvar else 0.0,
                "V_set": float(row.vm_pu) if hasattr(row, "vm_pu") and row.vm_pu == row.vm_pu else 1.0,
            }
        # Slack generator (ext_grid)
        for idx, row in self.net.ext_grid.iterrows():
            bus = int(row.bus)
            p_nom = 6.7787 if grid_name == "ieee39" else 5.0  # heuristic for other grids
            self.generators[bus] = {
                "name": f"Gen_Slack_Bus_{bus}",
                "P_nom": p_nom,
                "Q_nom": 2.0,
                "V_set": float(row.vm_pu) if hasattr(row, "vm_pu") and row.vm_pu == row.vm_pu else 1.0,
            }

        # Build loads mapping
        self.loads = {}
        for idx, row in self.net.load.iterrows():
            bus = int(row.bus)
            self.loads[bus] = {
                "name": f"Load_Bus_{bus}",
                "P_nom": float(row.p_mw) / 100.0,
                "Q_nom": float(row.q_mvar) / 100.0 if hasattr(row, "q_mvar") and row.q_mvar == row.q_mvar else 0.0,
            }

        # Build lines list (lines + transformers)
        self.lines = []
        for idx, row in self.net.line.iterrows():
            r_total = float(row.r_ohm_per_km * row.length_km) if hasattr(row, "length_km") else 0.01
            x_total = float(row.x_ohm_per_km * row.length_km) if hasattr(row, "length_km") else 0.1
            # Normalize to per-unit (rough heuristic: divide by base_kv^2/baseMVA ~= 1 for normalized grids)
            # Clamp X to avoid near-zero division
            x_total = max(x_total, 1e-4)
            self.lines.append({
                "from": int(row.from_bus),
                "to": int(row.to_bus),
                "R": r_total,
                "X": x_total,
                "id": f"L_line_{idx}",
                "name": str(row.get("name", f"Line {row.from_bus}-{row.to_bus}")),
            })

        for idx, row in self.net.trafo.iterrows():
            x_trafo = float(row.vk_percent / 100.0)
            x_trafo = max(x_trafo, 1e-4)
            self.lines.append({
                "from": int(row.hv_bus),
                "to": int(row.lv_bus),
                "R": 0.0,
                "X": x_trafo,
                "id": f"L_trafo_{idx}",
                "name": str(row.get("name", f"Trafo {row.hv_bus}-{row.lv_bus}")),
            })

        self.num_lines = len(self.lines)
        logger.info(
            f"MultiGridTopology({grid_name}): {self.num_buses} buses, "
            f"{self.num_lines} lines, {len(self.generators)} generators, "
            f"{len(self.loads)} loads"
        )

    def get_line_ids(self) -> list:
        """Returns list of all line IDs."""
        return [l["id"] for l in self.lines]

    def get_summary(self) -> dict:
        return {
            "grid": self.grid_name,
            "num_buses": self.num_buses,
            "num_lines": self.num_lines,
            "num_generators": len(self.generators),
            "num_loads": len(self.loads),
            "slack_bus": self.slack_bus,
        }


def create_grid(grid_name: str) -> MultiGridTopology:
    """Convenience factory function."""
    return MultiGridTopology(grid_name)


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    for g in SUPPORTED_GRIDS:
        topo = MultiGridTopology(g)
        print(topo.get_summary())
