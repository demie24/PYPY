import os
import json
import time
import numpy as np
from typing import Dict, Any, List

class AttackGenome:
    """
    Represents the genome of an attack sequence.
    Provides utility methods to represent and format attack vectors.
    """
    @staticmethod
    def from_steps(steps: List[Dict[str, Any]]) -> List[str]:
        """
        Translates a raw PPO step sequence into a formatted Genome string list.
        """
        genome = []
        for step in steps:
            act_type = int(step.get("type", 0))
            target = int(step.get("target", 0))
            magnitude = float(step.get("magnitude", 0.0))
            
            if act_type == 0:
                genome.append("WAIT")
            elif act_type == 1:
                genome.append(f"FDIA(Bus{target},{magnitude:.2f})")
            elif act_type == 2:
                genome.append(f"REPLAY(Bus{target})")
            elif act_type == 3:
                entity = f"Bus{target}" if target < 39 else f"Line{target-39}"
                genome.append(f"DOS({entity})")
            elif act_type == 4:
                genome.append(f"TRIP_LINE(Line{target})")
            else:
                genome.append("UNKNOWN")
        return genome

class PathogenMemory:
    """
    Manages historical pathogen memories, serializes successful attack genomes,
    and supports ranking/effectiveness checks.
    """
    def __init__(self, persistence_file: str = None):
        if persistence_file is None:
            adv_dir = os.path.dirname(os.path.abspath(__file__))
            self.persistence_file = os.path.join(adv_dir, "attack_memory.json")
        else:
            self.persistence_file = persistence_file

        self.successful_attacks: List[Dict[str, Any]] = []
        self.load()

    def record_episode(self, 
                       steps: List[Dict[str, Any]], 
                       reward: float, 
                       disruption: float, 
                       blackout: bool, 
                       stealth_rate: float):
        """
        Analyzes and records an episode trajectory if it meets success criteria
        (e.g., causes a blackout, high disruption, or high overall reward).
        """
        # Exclude pure waiting steps at the end to isolate the active genome sequence
        active_steps = []
        for s in steps:
            # Keep step if it's an active attack, or if we have already started attacking
            if s.get("type", 0) != 0 or len(active_steps) > 0:
                active_steps.append(s)
                
        # Trim trailing wait steps
        while active_steps and active_steps[-1].get("type", 0) == 0:
            active_steps.pop()

        if not active_steps:
            return

        genome = AttackGenome.from_steps(active_steps)
        
        # Calculate effectiveness score: combination of disruption, blackout success, and stealth
        effectiveness = float(1.0 * disruption + (50.0 if blackout else 0.0) + 10.0 * stealth_rate)

        attack_record = {
            "episode_id": len(self.successful_attacks) + 1,
            "genome": genome,
            "raw_steps": active_steps,
            "reward": float(reward),
            "disruption": float(disruption),
            "blackout": bool(blackout),
            "stealth_rate": float(stealth_rate),
            "effectiveness_score": round(effectiveness, 4),
            "timestamp": int(time.time() * 1000)
        }

        self.successful_attacks.append(attack_record)
        # Keep top 100 most effective genomes
        self.successful_attacks = sorted(
            self.successful_attacks, 
            key=lambda x: x["effectiveness_score"], 
            reverse=True
        )[:100]

        self.save()

    def get_top_genomes(self, top_n: int = 5) -> List[Dict[str, Any]]:
        return self.successful_attacks[:top_n]

    def load(self):
        if os.path.exists(self.persistence_file):
            try:
                with open(self.persistence_file, "r") as f:
                    self.successful_attacks = json.load(f)
            except Exception as e:
                print(f"Error loading attack memory: {e}")
                self.successful_attacks = []
        else:
            self.successful_attacks = []

    def save(self):
        try:
            with open(self.persistence_file, "w") as f:
                json.dump(self.successful_attacks, f, indent=4)
        except Exception as e:
            print(f"Error saving attack memory: {e}")
