"""
Eye Disease Detection Model Training
=====================================
Dataset: Eye Diseases Classification (Kaggle)
  kaggle datasets download -d gunavenkatdoddi/eye-diseases-classification

Classes:
  0 - Normal
  1 - Cataract
  2 - Diabetic Retinopathy
  3 - Glaucoma

Architecture: EfficientNet-B4 + Color analysis head

Usage:
  python training/train_eye.py --data_dir ./datasets/eye --epochs 50
"""
import argparse
import os
import json
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms
from PIL import Image
import timm
from pathlib import Path
from sklearn.model_selection import train_test_split

EYE_CLASSES = {0: "Normal", 1: "Cataract", 2: "Diabetic_Retinopathy", 3: "Glaucoma"}
CLASS_DIRS = ["Normal", "Cataract", "Diabetic_Retinopathy", "Glaucoma"]


class EyeDataset(Dataset):
    def __init__(self, samples: list, split: str = "train"):
        self.samples = samples
        self.transform = self._get_transform(split)

    def _get_transform(self, split: str):
        if split == "train":
            return transforms.Compose([
                transforms.Resize((380, 380)),
                transforms.RandomHorizontalFlip(),
                transforms.RandomRotation(10),
                transforms.ColorJitter(brightness=0.3, contrast=0.4, saturation=0.2),
                transforms.ToTensor(),
                transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
            ])
        return transforms.Compose([
            transforms.Resize((380, 380)),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
        ])

    def __len__(self): return len(self.samples)

    def __getitem__(self, idx):
        path, label = self.samples[idx]
        img = Image.open(path).convert("RGB")
        return self.transform(img), label


def load_samples(data_dir: str):
    base = Path(data_dir)
    samples = []
    for label, cls in enumerate(CLASS_DIRS):
        for pattern in ["*.jpg", "*.png", "*.jpeg"]:
            # Try nested dataset folder structure
            for root_path in [base / cls, base / "dataset" / cls, base / "train" / cls]:
                if root_path.exists():
                    for p in root_path.glob(pattern):
                        samples.append((str(p), label))
    return samples


def train(data_dir: str, epochs: int = 50, batch_size: int = 32, lr: float = 1e-4):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")

    all_samples = load_samples(data_dir)
    if not all_samples:
        print(f"No images found in {data_dir}. Run dataset_setup.py first.")
        return

    print(f"Total images: {len(all_samples)}")
    labels = [s[1] for s in all_samples]
    train_s, val_s = train_test_split(all_samples, test_size=0.2, stratify=labels, random_state=42)

    train_dl = DataLoader(EyeDataset(train_s, "train"), batch_size=batch_size, shuffle=True, num_workers=4)
    val_dl   = DataLoader(EyeDataset(val_s, "val"),     batch_size=batch_size, shuffle=False, num_workers=4)

    model = timm.create_model("efficientnet_b4", pretrained=True, num_classes=len(EYE_CLASSES))
    model = model.to(device)

    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
    criterion = nn.CrossEntropyLoss(label_smoothing=0.1)

    best_val_acc = 0.0

    for epoch in range(epochs):
        model.train()
        correct = total = 0
        for imgs, labels in train_dl:
            imgs, labels = imgs.to(device), labels.to(device)
            optimizer.zero_grad()
            loss = criterion(model(imgs), labels)
            loss.backward()
            optimizer.step()
            correct += model(imgs).detach().argmax(1).eq(labels).sum().item()
            total += labels.size(0)
        scheduler.step()

        model.eval()
        vc = vt = 0
        with torch.no_grad():
            for imgs, labels in val_dl:
                imgs, labels = imgs.to(device), labels.to(device)
                vc += model(imgs).argmax(1).eq(labels).sum().item()
                vt += labels.size(0)

        val_acc = vc / vt
        print(f"Epoch {epoch+1}/{epochs} | Train: {correct/total:.4f} | Val: {val_acc:.4f}")

        if val_acc > best_val_acc:
            best_val_acc = val_acc
            os.makedirs("models", exist_ok=True)
            torch.save(model.state_dict(), "models/eye_efficientnet_b4.pt")
            print(f"  Saved (val_acc={val_acc:.4f})")

    print(f"Best Val Accuracy: {best_val_acc:.4f}")
    with open("models/eye_training_history.json", "w") as f:
        json.dump({"best_val_acc": best_val_acc, "classes": EYE_CLASSES}, f)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data_dir", type=str, default="./datasets/eye")
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--batch_size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=1e-4)
    args = parser.parse_args()
    train(args.data_dir, args.epochs, args.batch_size, args.lr)
