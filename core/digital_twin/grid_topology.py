from grid_loader import IEEE39BusLoader

class GridTopology:
    def __init__(self):
        # Load the 39-bus network using the dedicated loader
        self.loader = IEEE39BusLoader()
        self.net = self.loader.get_net()
        
        # Dimensions
        self.num_buses = self.loader.num_buses
        self.slack_bus = int(self.net.ext_grid.bus.values[0]) if len(self.net.ext_grid) > 0 else 30
        
        # Build generators mapping (merging PV gen and slack ext_grid)
        self.generators = {}
        # PV generators
        for idx, row in self.net.gen.iterrows():
            bus = int(row.bus)
            self.generators[bus] = {
                "name": f"Gen_Bus_{bus}",
                "P_nom": float(row.p_mw) / 100.0, 
                "Q_nom": float(row.q_mvar) / 100.0 if hasattr(row, 'q_mvar') else 0.0,
                "V_set": float(row.vm_pu)
            }
        # Slack Generator (ext_grid)
        for idx, row in self.net.ext_grid.iterrows():
            bus = int(row.bus)
            self.generators[bus] = {
                "name": f"Gen_Slack_Bus_{bus}",
                "P_nom": 6.7787, 
                "Q_nom": 2.2157,
                "V_set": float(row.vm_pu) if hasattr(row, 'vm_pu') else 1.0
            }

        # Build loads mapping
        self.loads = {}
        for idx, row in self.net.load.iterrows():
            bus = int(row.bus)
            self.loads[bus] = {
                "name": f"Load_Bus_{bus}",
                "P_nom": float(row.p_mw) / 100.0,
                "Q_nom": float(row.q_mvar) / 100.0
            }
            
        # Build lines/transformers list (lines represent lines + transformers in old logic)
        self.lines = []
        # Lines
        for idx, row in self.net.line.iterrows():
            self.lines.append({
                "from": int(row.from_bus),
                "to": int(row.to_bus),
                "R": float(row.r_ohm_per_km * row.length_km),
                "X": float(row.x_ohm_per_km * row.length_km),
                "id": f"L_line_{idx}",
                "name": str(row.name) if row.name else f"Line {row.from_bus}-{row.to_bus}"
            })
        # Transformers (trafos)
        for idx, row in self.net.trafo.iterrows():
            self.lines.append({
                "from": int(row.hv_bus),
                "to": int(row.lv_bus),
                "R": 0.0, 
                "X": float(row.vk_percent / 100.0), 
                "id": f"L_trafo_{idx}",
                "name": str(row.name) if row.name else f"Trafo {row.hv_bus}-{row.lv_bus}"
            })
