import os
import sys
import torch
import torch.nn as nn
import numpy as np

# Add parent directories to sys.path to import grid_topology
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(current_dir))
sys.path.append(os.path.join(os.path.dirname(current_dir), "digital_twin"))

from grid_topology import GridTopology

class IEEE39PhysicsLoss(nn.Module):
    def __init__(self, device="cpu"):
        super(IEEE39PhysicsLoss, self).__init__()
        self.device = device
        self.num_buses = 39
        
        # 1. Load topology and construct mapped Y_bus matrix from pandapower
        topo = GridTopology()
        net = topo.net
        import pandapower as pp
        pp.runpp(net)
        
        ppc = net._ppc
        Ybus_sparse = ppc['internal']['Ybus']
        Ybus_dense = Ybus_sparse.todense()
        
        ppc_bus_idx = ppc['bus'][:, 0].astype(int)
        ext_to_int = {ext: i for i, ext in enumerate(ppc_bus_idx)}
        
        self.Y_bus = np.zeros((self.num_buses, self.num_buses), dtype=np.complex128)
        for i in range(self.num_buses):
            for j in range(self.num_buses):
                int_i = ext_to_int[i]
                int_j = ext_to_int[j]
                self.Y_bus[i, j] = Ybus_dense[int_i, int_j]
                
        self.Y_bus_torch = torch.tensor(self.Y_bus, dtype=torch.complex64).to(self.device)


    def to(self, device):
        self.device = device
        self.Y_bus_torch = self.Y_bus_torch.to(device)
        return self

    def forward(self, pred_P, pred_Q, pred_V, pred_theta, 
                w_volt=1.0, w_angle=1.0, w_balance=1.0):
        """
        Computes the physical loss constraints.
        Inputs:
            pred_P: Predicted active power injections in MW (batch, 39)
            pred_Q: Predicted reactive power injections in Mvar (batch, 39)
            pred_V: Predicted voltage magnitudes in pu (batch, 39)
            pred_theta: Predicted voltage angles in radians (batch, 39)
        Returns:
            loss_physics: Total physics loss scalar
            breakdown: Dict of individual constraints loss
        """
        # 1. Voltage boundary penalty: V must be in [0.85, 1.15] pu
        loss_volt_low = torch.clamp(0.85 - pred_V, min=0.0)
        loss_volt_high = torch.clamp(pred_V - 1.15, min=0.0)
        loss_volt = torch.mean(loss_volt_low**2 + loss_volt_high**2)
        
        # 2. Angle boundary penalty: theta must be in [-pi, pi] radians
        loss_angle_low = torch.clamp(-np.pi - pred_theta, min=0.0)
        loss_angle_high = torch.clamp(pred_theta - np.pi, min=0.0)
        loss_angle = torch.mean(loss_angle_low**2 + loss_angle_high**2)
        
        # 3. Power balance consistency (AC Power Flow equations)
        # V_complex = V * e^(j * theta)
        # Cos/Sin conversion for complex representation
        cos_theta = torch.cos(pred_theta)
        sin_theta = torch.sin(pred_theta)
        V_complex = torch.complex(pred_V * cos_theta, pred_V * sin_theta)
        
        # I_calc = Y_bus @ V_complex
        # Reshape to (batch, 39, 1) for matrix multiplication
        V_complex_uns = V_complex.unsqueeze(-1)
        I_calc = torch.matmul(self.Y_bus_torch, V_complex_uns).squeeze(-1)
        
        # S_calc = V_complex * conj(I_calc)
        S_calc = V_complex * torch.conj(I_calc)
        
        # P_calc = Re(S_calc), Q_calc = Im(S_calc)
        P_calc = torch.real(S_calc)
        Q_calc = torch.imag(S_calc)
        
        # Power injections in p.u. (MVA Base = 100)
        P_pred_pu = pred_P / 100.0
        Q_pred_pu = pred_Q / 100.0
        
        # In injection model, load is positive and generation is negative,
        # but in S_calc, generation is positive and load is negative.
        # Thus, P_pred_pu + P_calc = 0
        loss_bal_P = torch.mean((P_pred_pu + P_calc)**2)
        loss_bal_Q = torch.mean((Q_pred_pu + Q_calc)**2)
        loss_balance = loss_bal_P + loss_bal_Q
        
        # Total physics loss
        total_physics_loss = w_volt * loss_volt + w_angle * loss_angle + w_balance * loss_balance
        
        return total_physics_loss, {
            "loss_volt_bound": loss_volt.item(),
            "loss_angle_bound": loss_angle.item(),
            "loss_bal_P": loss_bal_P.item(),
            "loss_bal_Q": loss_bal_Q.item(),
            "loss_power_balance": loss_balance.item(),
            "total_physics_loss": total_physics_loss.item()
        }
