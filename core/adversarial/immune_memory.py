import os
import json
import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import time
from typing import Dict, Any, List, Tuple

class VAE(nn.Module):
    """
    Variational Autoencoder to compress telemetric deviation vectors 
    (124 dimensions) into a low-dimensional latent space (16 dimensions).
    """
    def __init__(self, input_dim: int = 124, latent_dim: int = 16):
        super(VAE, self).__init__()
        
        # Encoder
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, 64),
            nn.ReLU(),
            nn.Linear(64, 32),
            nn.ReLU()
        )
        self.fc_mu = nn.Linear(32, latent_dim)
        self.fc_logvar = nn.Linear(32, latent_dim)
        
        # Decoder
        self.decoder = nn.Sequential(
            nn.Linear(latent_dim, 32),
            nn.ReLU(),
            nn.Linear(32, 64),
            nn.ReLU(),
            nn.Linear(64, input_dim),
            nn.Tanh() # dev values normalized roughly in [-1, 1]
        )

    def encode(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        h = self.encoder(x)
        return self.fc_mu(h), self.fc_logvar(h)

    def reparameterize(self, mu: torch.Tensor, logvar: torch.Tensor) -> torch.Tensor:
        std = torch.exp(0.5 * logvar)
        eps = torch.randn_like(std)
        return mu + eps * std

    def decode(self, z: torch.Tensor) -> torch.Tensor:
        return self.decoder(z)

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        mu, logvar = self.encode(x)
        z = self.reparameterize(mu, logvar)
        return self.decode(z), mu, logvar

class ImmuneMemory:
    """
    Manages the Key-Value Immune Memory (Memory B/T Cells) storing 
    antigen embeddings (latent keys) and matching antibody actions.
    """
    def __init__(self, persistence_file: str = None, threshold: float = 0.85):
        self.threshold = threshold
        
        if persistence_file is None:
            adv_dir = os.path.dirname(os.path.abspath(__file__))
            self.persistence_file = os.path.join(adv_dir, "immune_memory.json")
        else:
            self.persistence_file = persistence_file
            
        self.memory_keys: List[np.ndarray] = []
        self.memory_values: List[Dict[str, Any]] = []
        
        # Load VAE model
        self.device = torch.device("cpu")
        self.vae = VAE()
        self.vae_loaded = self.load_vae()
        
        self.load()

    def load_vae(self) -> bool:
        adv_dir = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(adv_dir, "vae_immune_memory.pt")
        if os.path.exists(path):
            try:
                checkpoint = torch.load(path, map_location=self.device)
                self.vae.load_state_dict(checkpoint["state_dict"])
                self.vae.eval()
                return True
            except Exception as e:
                print(f"Error loading VAE state: {e}")
        return False

    def save_vae(self):
        adv_dir = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(adv_dir, "vae_immune_memory.pt")
        torch.save({"state_dict": self.vae.state_dict()}, path)
        self.vae_loaded = True

    def train_vae(self, data: np.ndarray, epochs: int = 50, batch_size: int = 16, lr: float = 1e-3):
        """
        Trains the VAE on historical grid deviation trajectories.
        """
        print(f"Training VAE on {len(data)} samples...")
        self.vae.train()
        optimizer = optim.Adam(self.vae.parameters(), lr=lr)
        
        dataset_size = len(data)
        data_t = torch.FloatTensor(data)
        
        for epoch in range(epochs):
            indices = np.arange(dataset_size)
            np.random.shuffle(indices)
            
            epoch_loss = 0.0
            for start_idx in range(0, dataset_size, batch_size):
                batch_idx = indices[start_idx : start_idx + batch_size]
                x = data_t[batch_idx]
                
                recon_x, mu, logvar = self.vae(x)
                
                # VAE loss = Recon Loss + KL Divergence
                recon_loss = nn.MSELoss(reduction="sum")(recon_x, x)
                kld_loss = -0.5 * torch.sum(1 + logvar - mu.pow(2) - logvar.exp())
                loss = recon_loss + kld_loss
                
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
                
                epoch_loss += loss.item()
                
        self.vae.eval()
        self.save_vae()
        print("VAE training complete. Model saved.")

    def get_embedding(self, telemetry_dev: np.ndarray) -> np.ndarray:
        """
        Compresses a 124-dimensional SCADA deviation vector into a 16-dimensional latent key.
        """
        if not self.vae_loaded:
            # Fallback to simple random/nominal mapping if VAE is not loaded/trained yet
            return np.zeros(16, dtype=np.float32)
            
        t_dev = torch.FloatTensor(telemetry_dev).unsqueeze(0).to(self.device)
        with torch.no_grad():
            mu, _ = self.vae.encode(t_dev)
        return mu.squeeze(0).numpy()

    def query(self, telemetry_dev: np.ndarray) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Queries the database for matches against telemetry deviation vector.
        Returns:
            recall_flags: 6-dimensional one-hot category recall flag vector
            matching_action: dict representing the matched antibody action, or None
        """
        recall_flags = np.zeros(6, dtype=np.float32)
        if not self.memory_keys:
            return recall_flags, None
            
        z_query = self.get_embedding(telemetry_dev)
        norm_q = np.linalg.norm(z_query)
        if norm_q < 1e-8:
            return recall_flags, None
            
        best_sim = -1.0
        best_idx = -1
        
        for idx, z_key in enumerate(self.memory_keys):
            norm_k = np.linalg.norm(z_key)
            if norm_k < 1e-8:
                continue
            sim = np.dot(z_query, z_key) / (norm_q * norm_k)
            if sim > best_sim:
                best_sim = sim
                best_idx = idx
                
        if best_sim >= self.threshold:
            val = self.memory_values[best_idx]
            category = val.get("category", 0)
            if 0 <= category < 6:
                recall_flags[category] = 1.0
            return recall_flags, val.get("mitigation")
            
        return recall_flags, None

    def store(self, telemetry_dev: np.ndarray, category: int, mitigation_action: Dict[str, Any], score: float = 0.0):
        """
        Stores a new key-value pair of Antigen signature -> Mitigation antibody.
        """
        z_key = self.get_embedding(telemetry_dev)
        
        # Check if already present to avoid duplicate clutter
        _, matched = self.query(telemetry_dev)
        if matched is not None:
            return
            
        self.memory_keys.append(z_key)
        self.memory_values.append({
            "category": int(category),
            "mitigation": mitigation_action,
            "score": float(score),
            "timestamp": int(time.time() * 1000)
        })
        
        # Implement memory score ranking and keep only Top-K highest quality memories
        K = 50
        zipped = list(zip(self.memory_keys, self.memory_values))
        # Sort descending by quality score
        zipped.sort(key=lambda x: x[1].get("score", 0.0), reverse=True)
        zipped = zipped[:K]
        
        self.memory_keys = [item[0] for item in zipped]
        self.memory_values = [item[1] for item in zipped]
            
        self.save()

    def load(self):
        if os.path.exists(self.persistence_file):
            try:
                with open(self.persistence_file, "r") as f:
                    db = json.load(f)
                self.memory_keys = [np.array(item["key"], dtype=np.float32) for item in db]
                self.memory_values = [item["value"] for item in db]
            except Exception as e:
                print(f"Error loading immune memory: {e}")
                self.memory_keys = []
                self.memory_values = []
        else:
            self.memory_keys = []
            self.memory_values = []

    def save(self):
        try:
            db = []
            for k, v in zip(self.memory_keys, self.memory_values):
                db.append({
                    "key": k.tolist(),
                    "value": v
                })
            with open(self.persistence_file, "w") as f:
                json.dump(db, f, indent=4)
        except Exception as e:
            print(f"Error saving immune memory: {e}")
