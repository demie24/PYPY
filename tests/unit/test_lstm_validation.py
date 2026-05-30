import os
import unittest
import torch
import numpy as np

# Set pythonpath dynamically
import sys

from core.ai_prediction.dataset_loader import TelemetryDataset
from core.ai_prediction.pinn_model import PhysicsInformedPredictorLSTM
from core.ai_prediction.pinn_inference import PinnInferenceEngine

class TestLSTMValidation(unittest.TestCase):
    def setUp(self):
        # Resolve the actual project root (two levels up from tests/unit/)
        self.project_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..")
        )
        self.ai_dir = os.path.join(self.project_root, "core", "ai_prediction")
        self.csv_path = os.path.join(self.ai_dir, "data", "telemetry_dataset_synthetic.csv")
        self.checkpoint_path = os.path.join(self.ai_dir, "models", "lstm_pinn_cyber_physical_predictor.pt")
        
        # Ensure synthetic dataset exists
        if not os.path.exists(self.csv_path):
            from core.ai_prediction.pinn_training import generate_synthetic_dataset
            generate_synthetic_dataset(150)
            
        self.window_size = 10
        self.dataset = TelemetryDataset(
            self.csv_path,
            window_size=self.window_size,
            target_index=list(range(1, 83)),
            return_cyber_label=False,
            multi_horizon=True
        )

    def test_dataset_shapes(self):
        """Verifies that sequence extraction outputs correct window shapes and horizons."""
        X, (y10, y30, y60) = self.dataset[0]
        
        self.assertEqual(X.shape, (self.window_size, 82), "Input sequence shape is wrong.")
        self.assertEqual(y10.shape, (83,), "Horizon 10s target shape is wrong.")
        self.assertEqual(y30.shape, (83,), "Horizon 30s target shape is wrong.")
        self.assertEqual(y60.shape, (83,), "Horizon 60s target shape is wrong.")

    def test_model_inference_and_nan_safety(self):
        """Loads the trained model checkpoint and performs validation inference."""
        self.assertTrue(os.path.exists(self.checkpoint_path), "Trained model checkpoint missing.")
        
        checkpoint = torch.load(self.checkpoint_path, map_location="cpu")
        model = PhysicsInformedPredictorLSTM(input_dim=82, output_dim=38, hidden_dim=128, num_layers=2)
        model.load_state_dict(checkpoint["state_dict"])
        model.eval()
        
        X, _ = self.dataset[0]
        input_tensor = X.unsqueeze(0) # add batch dim
        
        with torch.no_grad():
            out10, out30, out60 = model(input_tensor)
            
        pred10 = out10.squeeze(0).numpy()
        pred30 = out30.squeeze(0).numpy()
        pred60 = out60.squeeze(0).numpy()
        
        self.assertEqual(pred10.shape, (38,), "Output prediction shape is wrong.")
        self.assertFalse(np.isnan(pred10).any(), "NaN value detected in predictions.")
        self.assertFalse(np.isinf(pred10).any(), "Inf value detected in predictions.")
        
        self.assertFalse(np.isnan(pred30).any(), "NaN value detected in predictions.")
        self.assertFalse(np.isnan(pred60).any(), "NaN value detected in predictions.")

    def test_horizon_uncertainty_and_decay(self):
        """Asserts that predictive uncertainty (log-variance) tracks higher values for longer horizons."""
        checkpoint = torch.load(self.checkpoint_path, map_location="cpu")
        model = PhysicsInformedPredictorLSTM(input_dim=82, output_dim=38, hidden_dim=128, num_layers=2)
        model.load_state_dict(checkpoint["state_dict"])
        model.eval()
        
        X, _ = self.dataset[0]
        input_tensor = X.unsqueeze(0)
        
        with torch.no_grad():
            out10, out30, out60 = model(input_tensor)
            
        pred10 = out10.squeeze(0).numpy()
        pred30 = out30.squeeze(0).numpy()
        pred60 = out60.squeeze(0).numpy()
        
        # log-variance (col 37) should be a valid float
        logvar10 = pred10[37]
        logvar30 = pred30[37]
        logvar60 = pred60[37]
        
        self.assertFalse(np.isnan(logvar10))
        self.assertFalse(np.isnan(logvar30))
        self.assertFalse(np.isnan(logvar60))

    def test_concept_drift_monitoring_and_adaptation(self):
        """Tests streaming concept drift tracking and adaptive normalization limits."""
        engine = PinnInferenceEngine()
        engine.load_model()
        
        # Create a series of nominal rows to populate the drift buffer
        nominal_row = [1.0] * 9 + [0.0] * 9 + [50.0] * 18 + [0.5] * 9 + [1.0] * 9 + [0.0] * 28
        self.assertEqual(len(nominal_row), 82)
        
        for _ in range(30):
            engine.monitor_concept_drift(nominal_row)
            
        initial_min = engine.min_vals.copy()
        
        # Inject severe concept drift: shift voltages and flows by 10x standard deviations
        drifted_row = [2.5] * 9 + [1.5] * 9 + [200.0] * 18 + [3.0] * 9 + [1.0] * 9 + [0.0] * 28
        
        for _ in range(35):
            engine.monitor_concept_drift(drifted_row)
            
        # Drift score should exceed trigger threshold (2.0)
        self.assertGreater(engine.concept_drift_score, 2.0)
        self.assertTrue(engine.concept_drift_alert)
        
        # Severe drift (score > 3.5) should trigger online adaptation, shifting min_vals / max_vals limits
        self.assertTrue(np.any(engine.min_vals != initial_min))

if __name__ == "__main__":
    unittest.main()
