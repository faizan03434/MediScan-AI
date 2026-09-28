"""
Posture / Scoliosis Detection Training
========================================
Approach: MediaPipe Pose gives landmarks directly.
Train a lightweight MLP on landmark features (no raw image needed).

Input:  33 pose landmarks (x, y, visibility) = 99 features
Output: 3 classes: Normal, MildImbalance, SignificantDeviation

Usage:
  python training/train_posture.py --epochs 100
"""
import argparse
import os
import json
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

POSTURE_CLASSES = {0: "Normal", 1: "MildImbalance", 2: "SignificantDeviation"}
FEATURE_DIM = 99  # 33 landmarks x 3 (x, y, visibility)


class PostureMLP(nn.Module):
    """Lightweight MLP for pose landmark classification."""
    def __init__(self, input_dim: int = FEATURE_DIM, num_classes: int = 3):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, 256),
            nn.BatchNorm1d(256),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(256, 128),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, num_classes),
        )

    def forward(self, x):
        return self.net(x)


def generate_synthetic_poses(n_samples: int = 8000):
    """
    Generates synthetic landmark vectors with injected postural deviations.
    Class 0 (Normal): balanced shoulders/hips, < 2% deviation
    Class 1 (MildImbalance): 2-4% shoulder/hip imbalance
    Class 2 (SignificantDeviation): > 4% lateral deviation (scoliosis risk)
    """
    np.random.seed(42)
    features = []
    labels = []

    per_class = n_samples // 3

    for cls in range(3):
        for _ in range(per_class):
            # Base symmetric pose (normalized 0-1)
            lm = np.random.normal(0.5, 0.1, FEATURE_DIM).clip(0, 1)

            # Shoulder landmarks: left=11, right=12 (y coords)
            # Hip landmarks: left=23, right=24 (y coords)
            shoulder_imbalance = 0.0
            hip_imbalance = 0.0
            lateral_dev = 0.0

            if cls == 0:  # Normal
                shoulder_imbalance = np.random.uniform(0.0, 0.02)
                hip_imbalance = np.random.uniform(0.0, 0.02)
                lateral_dev = np.random.uniform(0.0, 0.02)
            elif cls == 1:  # Mild
                shoulder_imbalance = np.random.uniform(0.02, 0.04)
                hip_imbalance = np.random.uniform(0.01, 0.03)
                lateral_dev = np.random.uniform(0.02, 0.04)
            else:  # Significant
                shoulder_imbalance = np.random.uniform(0.04, 0.10)
                hip_imbalance = np.random.uniform(0.03, 0.08)
                lateral_dev = np.random.uniform(0.04, 0.12)

            # Inject deviations into landmark positions
            lm[11 * 3 + 1] += shoulder_imbalance   # left shoulder y
            lm[23 * 3] += lateral_dev               # left hip x
            lm[24 * 3] -= lateral_dev               # right hip x
            lm[23 * 3 + 1] += hip_imbalance

            # Add noise
            lm += np.random.normal(0, 0.01, FEATURE_DIM)
            lm = lm.clip(0, 1)

            features.append(lm)
            labels.append(cls)

    return np.array(features, dtype=np.float32), np.array(labels, dtype=np.int64)


def load_real_poses_if_available(data_dir: str):
    """Load real MediaPipe extracted landmark CSVs if available."""
    from pathlib import Path
    poses_file = Path(data_dir) / "poses.npy"
    labels_file = Path(data_dir) / "labels.npy"
    if poses_file.exists() and labels_file.exists():
        X = np.load(str(poses_file))
        y = np.load(str(labels_file))
        print(f"Loaded {len(X)} real pose samples from {data_dir}")
        return X.astype(np.float32), y.astype(np.int64)
    return None, None


def train(data_dir: str = "./datasets/posture", epochs: int = 100, batch_size: int = 128, lr: float = 1e-3):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")

    # Try loading real data, fall back to synthetic
    X_real, y_real = load_real_poses_if_available(data_dir)
    X_syn, y_syn = generate_synthetic_poses(8000)

    if X_real is not None:
        X = np.concatenate([X_real, X_syn])
        y = np.concatenate([y_real, y_syn])
        print(f"Combined: {len(X_real)} real + {len(X_syn)} synthetic = {len(X)} total")
    else:
        X, y = X_syn, y_syn
        print(f"Using {len(X)} synthetic samples (no real data found)")

    # Shuffle + split
    idx = np.random.permutation(len(X))
    X, y = X[idx], y[idx]
    split = int(len(X) * 0.8)
    X_train, X_val = X[:split], X[split:]
    y_train, y_val = y[:split], y[split:]

    train_ds = TensorDataset(torch.tensor(X_train), torch.tensor(y_train))
    val_ds   = TensorDataset(torch.tensor(X_val),   torch.tensor(y_val))
    train_dl = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
    val_dl   = DataLoader(val_ds,   batch_size=batch_size)

    model = PostureMLP().to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
    criterion = nn.CrossEntropyLoss()

    best_val_acc = 0.0

    for epoch in range(epochs):
        model.train()
        correct = total = 0
        for feats, lbls in train_dl:
            feats, lbls = feats.to(device), lbls.to(device)
            optimizer.zero_grad()
            out = model(feats)
            loss = criterion(out, lbls)
            loss.backward()
            optimizer.step()
            correct += out.detach().argmax(1).eq(lbls).sum().item()
            total += lbls.size(0)
        scheduler.step()

        model.eval()
        vc = vt = 0
        with torch.no_grad():
            for feats, lbls in val_dl:
                feats, lbls = feats.to(device), lbls.to(device)
                vc += model(feats).argmax(1).eq(lbls).sum().item()
                vt += lbls.size(0)

        val_acc = vc / vt
        if (epoch + 1) % 10 == 0:
            print(f"Epoch {epoch+1}/{epochs} | Train: {correct/total:.4f} | Val: {val_acc:.4f}")

        if val_acc > best_val_acc:
            best_val_acc = val_acc
            os.makedirs("models", exist_ok=True)
            torch.save(model.state_dict(), "models/posture_mlp.pt")

    print(f"Best Val Accuracy: {best_val_acc:.4f}")
    with open("models/posture_training_history.json", "w") as f:
        json.dump({"best_val_acc": best_val_acc, "classes": POSTURE_CLASSES,
                   "input_dim": FEATURE_DIM, "note": "MLP on MediaPipe landmarks"}, f)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data_dir", type=str, default="./datasets/posture")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--batch_size", type=int, default=128)
    parser.add_argument("--lr", type=float, default=1e-3)
    args = parser.parse_args()
    train(args.data_dir, args.epochs, args.batch_size, args.lr)
