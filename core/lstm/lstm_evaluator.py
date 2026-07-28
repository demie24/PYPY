import torch
import numpy as np
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix

LABEL_MAP = {
    "NORMAL": 0,
    "N1_LINE": 1,
    "N1_GENERATOR": 2,
    "N2": 3,
    "VOLTAGE_INSTABILITY": 4,
    "FDIA": 5,
    "REPLAY": 6,
    "DOS": 7
}

INV_LABEL_MAP = {v: k for k, v in LABEL_MAP.items()}

def evaluate_lstm_performance(model, data_loader, device="cpu"):
    """
    Evaluates the LSTM model on a dataset.
    Returns a comprehensive metrics dictionary containing:
      - accuracy
      - precision, recall, f1 (macro and weighted)
      - confusion matrix (as list of lists)
      - per-class metrics
    """
    model.eval()
    
    all_targets = []
    all_preds = []
    
    with torch.no_grad():
        for batch_x, batch_y in data_loader:
            batch_x = batch_x.to(device)
            logits = model(batch_x)
            preds = torch.argmax(logits, dim=-1)
            
            all_targets.extend(batch_y.numpy())
            all_preds.extend(preds.cpu().numpy())
            
    all_targets = np.array(all_targets)
    all_preds = np.array(all_preds)
    
    # Calculate global metrics
    accuracy = accuracy_score(all_targets, all_preds)
    precision_macro, recall_macro, f1_macro, _ = precision_recall_fscore_support(
        all_targets, all_preds, average="macro", zero_division=0
    )
    precision_weighted, recall_weighted, f1_weighted, _ = precision_recall_fscore_support(
        all_targets, all_preds, average="weighted", zero_division=0
    )
    
    # Confusion matrix (size 8x8)
    conf_mat = confusion_matrix(all_targets, all_preds, labels=list(range(8)))
    
    # Calculate per-class metrics
    precision_per_class, recall_per_class, f1_per_class, support_per_class = precision_recall_fscore_support(
        all_targets, all_preds, labels=list(range(8)), zero_division=0
    )
    
    per_class_metrics = {}
    for i in range(8):
        class_name = INV_LABEL_MAP[i]
        per_class_metrics[class_name] = {
            "precision": float(precision_per_class[i]),
            "recall": float(recall_per_class[i]),
            "f1_score": float(f1_per_class[i]),
            "support": int(support_per_class[i])
        }
        
    metrics = {
        "accuracy": float(accuracy),
        "precision_macro": float(precision_macro),
        "recall_macro": float(recall_macro),
        "f1_macro": float(f1_macro),
        "precision_weighted": float(precision_weighted),
        "recall_weighted": float(recall_weighted),
        "f1_weighted": float(f1_weighted),
        "confusion_matrix": conf_mat.tolist(),
        "per_class": per_class_metrics
    }
    
    return metrics
