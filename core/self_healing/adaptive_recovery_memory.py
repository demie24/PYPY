import os
import json
import logging
from typing import Dict, Any, List

logger = logging.getLogger("self_healing.adaptive_recovery_memory")

class AdaptiveRecoveryMemory:
    """
    Statefully stores historical restoration outcomes (successes and rollbacks).
    Computes Laplace-smoothed confidence metrics for switches and suggests optimal paths.
    """
    def __init__(self, filepath: str = None):
        if filepath is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            self.filepath = os.path.join(current_dir, "models", "recovery_memory.json")
        else:
            self.filepath = filepath
            
        # Ensure directories exist
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)

        self.successful_sequences: Dict[str, List[List[Dict[str, Any]]]] = {}
        self.failed_attempts: Dict[str, List[List[Dict[str, Any]]]] = {}
        self.breaker_stats: Dict[str, Dict[str, int]] = {}

        self.load_memory()

    def reset(self):
        self.successful_sequences.clear()
        self.failed_attempts.clear()
        self.breaker_stats.clear()
        self.save_memory()
        logger.info("Adaptive Recovery Memory cleared.")

    def get_fault_key(self, faulted_breakers: List[str]) -> str:
        if not faulted_breakers:
            return "NORMAL"
        return ",".join(sorted(faulted_breakers))

    def record_success(self, faulted_breakers: List[str], sequence: List[Dict[str, Any]]):
        if not sequence:
            return
        key = self.get_fault_key(faulted_breakers)
        if key not in self.successful_sequences:
            self.successful_sequences[key] = []
        
        # Avoid duplicates
        if sequence not in self.successful_sequences[key]:
            self.successful_sequences[key].append(sequence)

        # Update stats
        for action in sequence:
            target = action.get("target")
            if target:
                if target not in self.breaker_stats:
                    self.breaker_stats[target] = {"success": 0, "fail": 0}
                self.breaker_stats[target]["success"] += 1
                
        self.save_memory()
        logger.info(f"Recorded successful restoration sequence for fault signature [{key}]")

    def record_failure(self, faulted_breakers: List[str], sequence: List[Dict[str, Any]]):
        if not sequence:
            return
        key = self.get_fault_key(faulted_breakers)
        if key not in self.failed_attempts:
            self.failed_attempts[key] = []
            
        if sequence not in self.failed_attempts[key]:
            self.failed_attempts[key].append(sequence)

        # Update stats
        for action in sequence:
            target = action.get("target")
            if target:
                if target not in self.breaker_stats:
                    self.breaker_stats[target] = {"success": 0, "fail": 0}
                self.breaker_stats[target]["fail"] += 1
                
        self.save_memory()
        logger.warning(f"Recorded failed recovery sequence for fault signature [{key}]")

    def get_historical_confidence(self, breaker_id: str) -> float:
        """
        Calculates Laplace-smoothed confidence score for a specific breaker.
        Default confidence is 1.0 (with success=1, fail=0 default base).
        """
        stats = self.breaker_stats.get(breaker_id, {"success": 0, "fail": 0})
        s = stats["success"]
        f = stats["fail"]
        # Laplace smoothing: (s + 1) / (s + f + 1) -> maps to 1.0 initially
        return (s + 1) / (s + f + 1)

    def get_sequence_confidence(self, sequence: List[Dict[str, Any]]) -> float:
        if not sequence:
            return 1.0
        scores = []
        for step in sequence:
            target = step.get("target")
            if target:
                scores.append(self.get_historical_confidence(target))
        return sum(scores) / len(scores) if scores else 1.0

    def suggest_best_sequence(self, faulted_breakers: List[str]) -> List[Dict[str, Any]]:
        """
        Suggests the historically best sequence for a given fault signature.
        Fills the sequence that has the highest average confidence.
        """
        key = self.get_fault_key(faulted_breakers)
        candidates = self.successful_sequences.get(key, [])
        if not candidates:
            return []
            
        best_candidate = []
        best_confidence = -1.0
        
        for cand in candidates:
            conf = self.get_sequence_confidence(cand)
            # Filter out if this candidate is known to have failed in the past
            if key in self.failed_attempts and cand in self.failed_attempts[key]:
                conf *= 0.5 # Penalty
                
            if conf > best_confidence:
                best_confidence = conf
                best_candidate = cand
                
        return best_candidate

    def load_memory(self):
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r") as f:
                    data = json.load(f)
                    self.successful_sequences = data.get("successful_sequences", {})
                    self.failed_attempts = data.get("failed_attempts", {})
                    self.breaker_stats = data.get("breaker_stats", {})
                logger.info(f"Loaded recovery memory cache from {self.filepath}")
            except Exception as e:
                logger.error(f"Failed to load recovery memory from {self.filepath}: {e}")
        else:
            logger.info("No recovery memory file found. Starting with clean state.")

    def save_memory(self):
        try:
            data = {
                "successful_sequences": self.successful_sequences,
                "failed_attempts": self.failed_attempts,
                "breaker_stats": self.breaker_stats
            }
            with open(self.filepath, "w") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            logger.error(f"Failed to save recovery memory to {self.filepath}: {e}")
