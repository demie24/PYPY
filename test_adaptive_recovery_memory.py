import unittest
import sys
import os

# Setup import paths
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "core", "self_healing")))

from adaptive_recovery_memory import AdaptiveRecoveryMemory

class TestAdaptiveRecoveryMemory(unittest.TestCase):
    def setUp(self):
        self.test_filepath = os.path.join(os.path.dirname(__file__), "test_recovery_memory.json")
        if os.path.exists(self.test_filepath):
            os.remove(self.test_filepath)
        self.memory = AdaptiveRecoveryMemory(filepath=self.test_filepath)

    def tearDown(self):
        if os.path.exists(self.test_filepath):
            os.remove(self.test_filepath)

    def test_record_success_and_failure(self):
        faults = ["L8_9"]
        seq = [{"command": "CLOSED", "target": "L7_8"}]

        # Check default confidence is 1.0 (Laplace smoothing defaults to 1.0 when empty: (0+1)/(0+0+1) = 1.0)
        self.assertEqual(self.memory.get_historical_confidence("L7_8"), 1.0)

        # Record a success
        self.memory.record_success(faults, seq)
        # s=1, f=0 -> (1+1)/(1+0+1) = 1.0
        self.assertEqual(self.memory.get_historical_confidence("L7_8"), 1.0)

        # Record a failure/rollback
        self.memory.record_failure(faults, seq)
        # s=1, f=1 -> (1+1)/(1+1+1) = 2/3 = 0.6666...
        self.assertAlmostEqual(self.memory.get_historical_confidence("L7_8"), 2.0/3.0)

    def test_sequence_recommendation(self):
        faults = ["L8_9"]
        seq1 = [{"command": "CLOSED", "target": "L7_8"}]
        seq2 = [{"command": "CLOSED", "target": "L4_5"}]

        # Record seq1 as successful
        self.memory.record_success(faults, seq1)

        # Suggest best path
        best = self.memory.suggest_best_sequence(faults)
        self.assertEqual(len(best), 1)
        self.assertEqual(best[0]["target"], "L7_8")

        # Now record seq2 as successful too, and make seq1 fail
        self.memory.record_success(faults, seq2)
        self.memory.record_failure(faults, seq1)

        # Now seq2 should be preferred because seq1's confidence collapsed
        best_new = self.memory.suggest_best_sequence(faults)
        self.assertEqual(best_new[0]["target"], "L4_5")

if __name__ == "__main__":
    unittest.main()
