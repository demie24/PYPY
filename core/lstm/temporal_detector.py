import os
import sys
import torch
import torch.nn.functional as F
import numpy as np

# Setup path to import sibling modules
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from lstm_model import IEEE39LSTMClassifier
from anomaly_score import compute_anomaly_score
from lstm_evaluator import INV_LABEL_MAP

class TemporalAnomalyDetector:
    def __init__(self, model_path=None, device="cpu"):
        self.device = device
        if model_path is None:
            model_path = os.path.join(current_dir, "trained_lstm_model.pt")
            
        # Initialize model architecture
        self.model = IEEE39LSTMClassifier(
            input_dim=156,
            hidden_dim=64,
            num_layers=2,
            num_classes=8,
            dropout=0.2
        )
        
        # Load state dict
        if os.path.exists(model_path):
            self.model.load_state_dict(torch.load(model_path, map_location=device))
            print(f"Loaded trained LSTM model from: {model_path}")
        else:
            print(f"Warning: Trained model not found at {model_path}. Detector initialized with default weights.")
            
        self.model.to(device)
        self.model.eval()
        
    def get_probabilities(self, seq):
        """
        Takes a sequence (seq_len, 156) or batch of sequences (batch, seq_len, 156).
        Returns the probability distribution over classes.
        """
        if isinstance(seq, np.ndarray):
            x = torch.tensor(seq, dtype=torch.float32).to(self.device)
        else:
            x = seq.to(self.device)
            
        # Ensure x is at least 3D (batch, seq_len, input_dim)
        if x.dim() == 2:
            x = x.unsqueeze(0)
            
        with torch.no_grad():
            logits = self.model(x)
            probs = F.softmax(logits, dim=-1)
        return probs
        
    def predict_sequence(self, seq):
        """
        Returns class probabilities for the sequence.
        """
        probs = self.get_probabilities(seq).squeeze(0)
        return probs.cpu().numpy()
        
    def anomaly_score(self, seq):
        """
        Returns the anomaly score (1.0 - P(NORMAL)) for the sequence.
        """
        probs = self.get_probabilities(seq).squeeze(0)
        score = compute_anomaly_score(probs, is_logits=False)
        return float(score.cpu().item()) if isinstance(score, torch.Tensor) else float(score)
        
    def classification(self, seq):
        """
        Returns predicted class label string(s) for the sequence.
        """
        probs = self.get_probabilities(seq).squeeze(0)
        if probs.dim() == 1:
            pred = torch.argmax(probs, dim=-1).cpu().item()
            return INV_LABEL_MAP[int(pred)]
        else:
            preds = torch.argmax(probs, dim=-1).cpu().numpy()
            return [INV_LABEL_MAP[int(p)] for p in preds]

# Singleton instance for easy import-and-use
_detector = None

def _get_detector():
    global _detector
    if _detector is None:
        _detector = TemporalAnomalyDetector()
    return _detector

def predict_sequence(seq):
    return _get_detector().predict_sequence(seq)

def anomaly_score(seq):
    return _get_detector().anomaly_score(seq)

def classification(seq):
    return _get_detector().classification(seq)
