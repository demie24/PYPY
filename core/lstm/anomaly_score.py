import torch
import torch.nn.functional as F
import numpy as np

def compute_anomaly_score(logits_or_probs, is_logits=True):
    """
    Computes the anomaly score representing the deviation from normal behavior.
    Anomaly score = 1.0 - P(NORMAL)
    NORMAL class is assumed to be at index 0.
    Input can be a torch.Tensor or numpy.ndarray.
    """
    if isinstance(logits_or_probs, np.ndarray):
        # Convert to torch tensor for unified operations
        tensor_in = torch.tensor(logits_or_probs, dtype=torch.float32)
        was_numpy = True
    else:
        tensor_in = logits_or_probs
        was_numpy = False
        
    if is_logits:
        probs = F.softmax(tensor_in, dim=-1)
    else:
        probs = tensor_in
        
    # Get P(NORMAL) at index 0
    p_normal = probs[..., 0]
    score = 1.0 - p_normal
    
    if was_numpy:
        return score.numpy()
    return score
