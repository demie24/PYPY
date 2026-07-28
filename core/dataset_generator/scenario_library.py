import os
import sys
import random
import copy
import numpy as np

# Ensure digital_twin is in path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(os.path.dirname(current_dir), "digital_twin"))

from grid_topology import GridTopology

class GridScenarioLibrary:
    def __init__(self, topo: GridTopology = None):
        self.topo = topo if topo is not None else GridTopology()
        self.num_buses = self.topo.num_buses
        self.slack_bus = self.topo.slack_bus
        
    def get_base_state(self):
        """
        Returns the base operational state of the grid.
        """
        # Breakers CLOSED by default
        breakers = {line["id"]: "CLOSED" for line in self.topo.lines}
        
        # Nominal loads
        active_loads = {}
        for bus, load in self.topo.loads.items():
            active_loads[bus] = {
                "P": load["P_nom"],
                "Q": load["Q_nom"]
            }
            
        # Nominal generators
        generator_P = {}
        generator_Q = {}
        generators_online = {}
        for bus, gen in self.topo.generators.items():
            generator_P[bus] = gen["P_nom"]
            generator_Q[bus] = gen["Q_nom"]
            generators_online[bus] = True
            
        return breakers, active_loads, generator_P, generator_Q, generators_online

    def generate_normal(self, num_samples: int) -> list:
        """
        Generates normal operation samples with high diversity load/gen variations.
        """
        samples = []
        for i in range(num_samples):
            breakers, active_loads, generator_P, generator_Q, generators_online = self.get_base_state()
            
            # Diverse global load profile representing peak, normal, and off-peak dispatch
            global_scale = random.uniform(0.70, 1.20)
            
            # Vary active loads independently at each bus with noise
            for bus in active_loads:
                bus_noise = random.uniform(0.92, 1.08)
                active_loads[bus]["P"] *= global_scale * bus_noise
                active_loads[bus]["Q"] *= global_scale * bus_noise
                
            # Adjust generators proportionally to balance the load, with noise
            for bus in generator_P:
                if bus != self.slack_bus:
                    bus_noise = random.uniform(0.95, 1.05)
                    generator_P[bus] *= global_scale * bus_noise
                    
            samples.append({
                "breakers": breakers,
                "active_loads": active_loads,
                "generator_P": generator_P,
                "generator_Q": generator_Q,
                "generators_online": generators_online,
                "attack": None,
                "label": "NORMAL",
                "scenario_type": "NORMAL_OPERATION"
            })
        return samples

    def generate_n1_line(self, num_samples: int) -> list:
        """
        Generates N-1 line or transformer outage samples with diverse load profiles.
        """
        samples = []
        line_ids = [line["id"] for line in self.topo.lines]
        
        for i in range(num_samples):
            breakers, active_loads, generator_P, generator_Q, generators_online = self.get_base_state()
            
            # Diverse load/generation variation
            global_scale = random.uniform(0.75, 1.15)
            for bus in active_loads:
                active_loads[bus]["P"] *= global_scale * random.uniform(0.95, 1.05)
                active_loads[bus]["Q"] *= global_scale * random.uniform(0.95, 1.05)
            for bus in generator_P:
                if bus != self.slack_bus:
                    generator_P[bus] *= global_scale * random.uniform(0.97, 1.03)
                    
            # Trip one random line/transformer
            tripped_line = random.choice(line_ids)
            breakers[tripped_line] = "OPEN"
            
            samples.append({
                "breakers": breakers,
                "active_loads": active_loads,
                "generator_P": generator_P,
                "generator_Q": generator_Q,
                "generators_online": generators_online,
                "attack": None,
                "label": "N1_LINE",
                "scenario_type": "PHYSICAL_CONTINGENCY"
            })
        return samples

    def generate_n1_generator(self, num_samples: int) -> list:
        """
        Generates N-1 generator trip samples with diverse dispatch.
        """
        samples = []
        gen_buses = [bus for bus in self.topo.generators.keys() if bus != self.slack_bus]
        
        for i in range(num_samples):
            breakers, active_loads, generator_P, generator_Q, generators_online = self.get_base_state()
            
            # Diverse load/generation variation
            global_scale = random.uniform(0.75, 1.10)
            for bus in active_loads:
                active_loads[bus]["P"] *= global_scale * random.uniform(0.95, 1.05)
                active_loads[bus]["Q"] *= global_scale * random.uniform(0.95, 1.05)
            for bus in generator_P:
                if bus != self.slack_bus:
                    generator_P[bus] *= global_scale * random.uniform(0.97, 1.03)
                    
            # Trip one random generator
            tripped_gen = random.choice(gen_buses)
            generators_online[tripped_gen] = False
            generator_P[tripped_gen] = 0.0
            
            samples.append({
                "breakers": breakers,
                "active_loads": active_loads,
                "generator_P": generator_P,
                "generator_Q": generator_Q,
                "generators_online": generators_online,
                "attack": None,
                "label": "N1_GENERATOR",
                "scenario_type": "PHYSICAL_CONTINGENCY"
            })
        return samples

    def generate_n2(self, num_samples: int) -> list:
        """
        Generates N-2 contingency samples with high diversity.
        """
        samples = []
        line_ids = [line["id"] for line in self.topo.lines]
        gen_buses = [bus for bus in self.topo.generators.keys() if bus != self.slack_bus]
        
        for i in range(num_samples):
            breakers, active_loads, generator_P, generator_Q, generators_online = self.get_base_state()
            
            global_scale = random.uniform(0.75, 1.10)
            for bus in active_loads:
                active_loads[bus]["P"] *= global_scale * random.uniform(0.95, 1.05)
                active_loads[bus]["Q"] *= global_scale * random.uniform(0.95, 1.05)
            for bus in generator_P:
                if bus != self.slack_bus:
                    generator_P[bus] *= global_scale * random.uniform(0.97, 1.03)
                    
            # Choose N-2 tripped elements
            cont_type = random.choice([0, 1, 2])
            if cont_type == 0:
                # Two lines
                tripped = random.sample(line_ids, 2)
                breakers[tripped[0]] = "OPEN"
                breakers[tripped[1]] = "OPEN"
            elif cont_type == 1:
                # Line + Gen
                tripped_line = random.choice(line_ids)
                tripped_gen = random.choice(gen_buses)
                breakers[tripped_line] = "OPEN"
                generators_online[tripped_gen] = False
                generator_P[tripped_gen] = 0.0
            else:
                # Two Gens
                tripped_gens = random.sample(gen_buses, 2)
                for g in tripped_gens:
                    generators_online[g] = False
                    generator_P[g] = 0.0
                    
            samples.append({
                "breakers": breakers,
                "active_loads": active_loads,
                "generator_P": generator_P,
                "generator_Q": generator_Q,
                "generators_online": generators_online,
                "attack": None,
                "label": "N2",
                "scenario_type": "PHYSICAL_CONTINGENCY"
            })
        return samples

    def generate_voltage_instability(self, num_samples: int) -> list:
        """
        Generates progressive loading voltage instability samples.
        We scale up loads to push the grid into a low-voltage stressed state
        (targeting [0.85, 0.90] pu) without causing solver divergence.
        """
        samples = []
        for i in range(num_samples):
            breakers, active_loads, generator_P, generator_Q, generators_online = self.get_base_state()
            
            # Progressively load the grid (between 1.18 and 1.24 scale)
            scale = random.uniform(1.18, 1.24)
            for bus in active_loads:
                active_loads[bus]["P"] *= scale * random.uniform(0.98, 1.02)
                active_loads[bus]["Q"] *= scale * random.uniform(0.98, 1.02)
                
            samples.append({
                "breakers": breakers,
                "active_loads": active_loads,
                "generator_P": generator_P,
                "generator_Q": generator_Q,
                "generators_online": generators_online,
                "attack": None,
                "label": "VOLTAGE_INSTABILITY",
                "scenario_type": "PHYSICAL_CONTINGENCY"
            })
        return samples

    def generate_fdia(self, num_samples: int) -> list:
        """
        Generates False Data Injection Attack samples with random magnitudes and targets.
        """
        samples = []
        for i in range(num_samples):
            breakers, active_loads, generator_P, generator_Q, generators_online = self.get_base_state()
            
            global_scale = random.uniform(0.80, 1.20)
            for bus in active_loads:
                active_loads[bus]["P"] *= global_scale * random.uniform(0.95, 1.05)
                active_loads[bus]["Q"] *= global_scale * random.uniform(0.95, 1.05)
            for bus in generator_P:
                if bus != self.slack_bus:
                    generator_P[bus] *= global_scale * random.uniform(0.97, 1.03)
            
            # Target random buses (1 to 8) to inject fake voltages or active power
            num_targets = random.randint(1, 8)
            target_buses = random.sample(range(self.num_buses), num_targets)
            
            attack_config = {
                "type": "FDIA",
                "targets": []
            }
            for bus in target_buses:
                # Stealthy offsets and scales designed to shift metrics but remain within boundaries
                attack_config["targets"].append({
                    "bus_id": bus,
                    "v_scale": random.uniform(0.90, 1.10),
                    "v_bias": random.uniform(-0.08, 0.08),
                    "p_scale": random.uniform(0.7, 1.3),
                    "q_scale": random.uniform(0.7, 1.3)
                })
                
            samples.append({
                "breakers": breakers,
                "active_loads": active_loads,
                "generator_P": generator_P,
                "generator_Q": generator_Q,
                "generators_online": generators_online,
                "attack": attack_config,
                "label": "FDIA",
                "scenario_type": "CYBER_ATTACK"
            })
        return samples

    def generate_replay(self, num_samples: int) -> list:
        """
        Generates Replay Attack samples.
        """
        samples = []
        for i in range(num_samples):
            breakers, active_loads, generator_P, generator_Q, generators_online = self.get_base_state()
            
            global_scale = random.uniform(0.80, 1.20)
            for bus in active_loads:
                active_loads[bus]["P"] *= global_scale * random.uniform(0.95, 1.05)
                active_loads[bus]["Q"] *= global_scale * random.uniform(0.95, 1.05)
            for bus in generator_P:
                if bus != self.slack_bus:
                    generator_P[bus] *= global_scale * random.uniform(0.97, 1.03)
                    
            samples.append({
                "breakers": breakers,
                "active_loads": active_loads,
                "generator_P": generator_P,
                "generator_Q": generator_Q,
                "generators_online": generators_online,
                "attack": {"type": "REPLAY"},
                "label": "REPLAY",
                "scenario_type": "CYBER_ATTACK"
            })
        return samples

    def generate_dos(self, num_samples: int) -> list:
        """
        Generates DoS Attack samples.
        """
        samples = []
        for i in range(num_samples):
            breakers, active_loads, generator_P, generator_Q, generators_online = self.get_base_state()
            
            global_scale = random.uniform(0.80, 1.20)
            for bus in active_loads:
                active_loads[bus]["P"] *= global_scale * random.uniform(0.95, 1.05)
                active_loads[bus]["Q"] *= global_scale * random.uniform(0.95, 1.05)
            for bus in generator_P:
                if bus != self.slack_bus:
                    generator_P[bus] *= global_scale * random.uniform(0.97, 1.03)
                    
            samples.append({
                "breakers": breakers,
                "active_loads": active_loads,
                "generator_P": generator_P,
                "generator_Q": generator_Q,
                "generators_online": generators_online,
                "attack": {"type": "DOS"},
                "label": "DOS",
                "scenario_type": "CYBER_ATTACK"
            })
        return samples
