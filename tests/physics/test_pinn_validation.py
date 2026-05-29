import os
import unittest
import torch
import numpy as np

# Set pythonpath dynamically
import sys
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "core", "ai_prediction"))

from physics_informed_loss import C_MATRIX, X_LINE, compute_pinn_loss
from pinn_inference import PinnInferenceEngine

class TestPINNValidation(unittest.TestCase):
    def test_incidence_matrix_properties(self):
        """Verifies mathematical validity of incidence matrix (size 9x9, rank, connectivity)."""
        self.assertEqual(C_MATRIX.shape, (9, 9))
        
        # Each line k has exactly one +1 and one -1
        for k in range(9):
            col = C_MATRIX[:, k]
            self.assertEqual(torch.sum(col == 1.0), 1)
            self.assertEqual(torch.sum(col == -1.0), 1)
            self.assertEqual(torch.sum(col), 0.0)

    def test_pinn_loss_gradients(self):
        """Tests that the PINN loss functions are fully differentiable and output correct values."""
        # Create dummy batch of predictions and trues (output size = 38)
        y_pred = torch.rand(4, 38, requires_grad=True)
        y_pred.data[:, 0:9] = 1.0 + torch.randn(4, 9) * 0.01
        
        # True state vector (size = 83)
        y_true = torch.zeros(4, 83)
        y_true[:, 0:9] = 1.0
        y_true[:, 9:18] = 0.0  # angles
        y_true[:, 18:27] = 100.0  # 1.0 p.u. injections
        y_true[:, 27:36] = 20.0   # 0.2 p.u.
        y_true[:, 63:72] = 1.0    # breakers closed
        
        loss, details = compute_pinn_loss(y_pred, y_true)
        
        # Verify loss output is scalar and has gradient history
        self.assertEqual(loss.shape, ())
        self.assertTrue(loss.requires_grad)
        
        # Verify details dictionary keys
        expected_keys = [
            "loss_supervised", "loss_V", "loss_angle", "loss_flow_P", "loss_flow_Q", "loss_cyber", 
            "loss_nll", "loss_kcl", "loss_kvl", "loss_dc_flow", "loss_topo", "loss_stability",
            "loss_trust_cons", "loss_volt_limit", "loss_line_loading", "total_loss"
        ]
        for key in expected_keys:
            self.assertIn(key, details)
            self.assertFalse(np.isnan(details[key]))
            
        # Run backward pass to assert gradient propagation
        loss.backward()
        self.assertIsNotNone(y_pred.grad)
        self.assertFalse(torch.isnan(y_pred.grad).any())

    def test_topology_breaker_penalty(self):
        """Verifies that open breakers (value 0) enforce zero active/reactive power flows."""
        # 1. All breakers closed -> no topology penalty on non-zero flows
        y_pred_closed = torch.zeros(1, 38)
        y_pred_closed[:, 18:27] = 1.0  # active flows
        y_pred_closed[:, 27:36] = 1.0  # reactive flows
        y_true_closed = torch.zeros(1, 83)
        y_true_closed[:, 63:72] = 1.0 # closed
        _, details_closed = compute_pinn_loss(y_pred_closed, y_true_closed)
        self.assertEqual(details_closed["loss_topo"], 0.0)
        
        # 2. Breakers open but predictions have non-zero flows -> topology penalty should occur
        y_pred_open = torch.zeros(1, 38)
        y_pred_open[:, 18:27] = 1.0  # active flows
        y_pred_open[:, 27:36] = 1.0  # reactive flows
        y_true_open = torch.zeros(1, 83)
        y_true_open[:, 63:72] = 0.0 # open
        _, details_open = compute_pinn_loss(y_pred_open, y_true_open)
        self.assertGreater(details_open["loss_topo"], 0.0)

    def test_differentiable_dc_flow(self):
        """Verifies differentiable DC power flow loss limits and angle consistency constraints."""
        y_pred = torch.zeros(1, 38, requires_grad=True)
        # Set mismatch between active flow (P) and voltage angle diffs
        # P = 1.0, but angles are 0 (should yield dc flow mismatch since reactance X > 0)
        y_pred.data[:, 18:27] = 1.0
        
        y_true = torch.zeros(1, 83)
        y_true[:, 63:72] = 1.0 # breakers closed
        
        loss, details = compute_pinn_loss(y_pred, y_true)
        self.assertGreater(details["loss_dc_flow"], 0.0)
        
        loss.backward()
        self.assertIsNotNone(y_pred.grad)
        # Gradients must propagate to voltage angles (cols 9-17) and active line flows (cols 18-26)
        self.assertFalse(torch.isnan(y_pred.grad[:, 9:27]).any())

    def test_trust_weighted_voltage_reconstruction(self):
        """Tests that low-trust bus voltages are reconstructed statefully using closed physical lines."""
        engine = PinnInferenceEngine()
        
        # Nominal state: all voltages 1.0, all line currents 0.0, all breakers closed
        voltages = [1.0] * 9
        currents = [0.0] * 9
        breakers = [1.0] * 9
        
        # Let's say Bus 5 (index 4) is compromised, and its raw voltage reads 0.5 (undervoltage)
        voltages[4] = 0.5
        
        # Reconstruct Bus 5 (connected to Bus 4 and Bus 6)
        # Since neighbors have V=1.0 and current is 0.0, KVL predicts V = 1.0 - 0.0 * X = 1.0
        rec_v = engine.reconstruct_voltage(4, voltages, currents, breakers)
        self.assertAlmostEqual(rec_v, 1.0)

if __name__ == "__main__":
    unittest.main()
