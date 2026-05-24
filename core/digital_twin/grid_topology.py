class GridTopology:
    def __init__(self):
        # 9-Bus topology index map (0-indexed)
        # Bus 1, 2, 3 -> Generators
        # Bus 5, 6, 8 -> Loads
        # Bus 4, 7, 9 -> Junctions
        self.num_buses = 9
        
        # Slack bus index (Bus 1)
        self.slack_bus = 0
        
        # Generators: (Bus Index, Nominal Active Power P_pu, Nominal Reactive Power Q_pu, Voltage Setpoint)
        self.generators = {
            0: {"name": "Gen_1", "P_nom": 0.72, "Q_nom": 0.27, "V_set": 1.04},   # Slack
            1: {"name": "Gen_2", "P_nom": 1.63, "Q_nom": 0.06, "V_set": 1.025},
            2: {"name": "Gen_3", "P_nom": 0.85, "Q_nom": -0.10, "V_set": 1.025}
        }
        
        # Loads: (Bus Index, Nominal P_pu, Nominal Q_pu)
        self.loads = {
            4: {"name": "Load_5", "P_nom": 1.25, "Q_nom": 0.50},
            5: {"name": "Load_6", "P_nom": 0.90, "Q_nom": 0.30},
            7: {"name": "Load_8", "P_nom": 1.00, "Q_nom": 0.35}
        }
        
        # Transmission Lines: (From, To, R, X, Line ID, Name)
        # On 100 MVA Base
        self.lines = [
            {"from": 0, "to": 3, "R": 0.0,    "X": 0.0576, "id": "L1_4", "name": "Gen 1 Transformer"},
            {"from": 1, "to": 6, "R": 0.0,    "X": 0.0625, "id": "L2_7", "name": "Gen 2 Transformer"},
            {"from": 2, "to": 8, "R": 0.0,    "X": 0.0586, "id": "L3_9", "name": "Gen 3 Transformer"},
            {"from": 3, "to": 4, "R": 0.010,  "X": 0.085,  "id": "L4_5", "name": "Line 4-5"},
            {"from": 3, "to": 8, "R": 0.017,  "X": 0.092,  "id": "L4_9", "name": "Line 4-9"},
            {"from": 4, "to": 5, "R": 0.032,  "X": 0.161,  "id": "L5_6", "name": "Line 5-6"},
            {"from": 5, "to": 6, "R": 0.0085, "X": 0.072,  "id": "L6_7", "name": "Line 6-7"},
            {"from": 6, "to": 7, "R": 0.032,  "X": 0.161,  "id": "L7_8", "name": "Line 7-8"},
            {"from": 7, "to": 8, "R": 0.0119, "X": 0.1008, "id": "L8_9", "name": "Line 8-9"}
        ]
