"""
Skin Disease Model Training (HAM10000)
────────────────────────────────────────────────────────────────
Dataset: HAM10000 (10,015 dermoscopic images)
  kaggle datasets download -d kmader/skin-lesion-analysis-toward-melanoma-detection

Architecture: EfficientNet-B3 fine-tuned for 12-class skin condition classification

Usage:
  python training/train_skin.py --data_dir ./datasets/ham10000 --epochs 60
────────────────────────────────────────────────────────────────
"""
import argparse
import os
import json
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset, WeightedRandomSampler
from torchvision import transforms
from PIL import Image
import timm
from pathlib import Path
from collections import Counter
import numpy as np

HAM10000_LABEL_MAP = {
    "akiec": 0,  # Actinic Keratosis
    "bcc":   1,  # Basal Cell Carcinoma
    "bkl":   2,  # Benign Keratosis
    "df":    3,  # Dermatofibroma
    "mel":   4,  # Melanoma
    "nv":    5,  # Melanocytic Nevus
    "vasc":  6,  # Vascular Lesion
}


class HAM10000Dataset(Dataset):
    def __init__(self, csv_path: str, img_dir: str, split: str = "train"):
        df = pd.read_csv(csv_path)

        # 80/20 train/val split
        from sklearn.model_selection import train_test_split
        train_df, val_df = train_test_split(df, test_size=0.2, stratify=df["dx"], random_state=42)
        self.df = train_df if split == "train" else val_df

        self.img_dir = Path(img_dir)
        self.split = split
        self.transform = self._get_transform(split)

    def _get_transform(self, split: str):
        if split == "train":
            return transforms.Compose([
                transforms.Resize((300, 300)),
                transforms.RandomHorizontalFlip(),
                transforms.RandomVerticalFlip(),
                transforms.RandomRotation(15),
                transforms.ColorJitter(brightness=0.3, contrast=0.3, saturation=0.2, hue=0.05),
                transforms.RandomAffine(degrees=0, translate=(0.1, 0.1)),
                transforms.ToTensor(),
                transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
            ])
        return transforms.Compose([
            transforms.Resize((300, 300)),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
        ])

    def __len__(self):
        return len(self.df)

    def __getitem__(self, idx):
        row = self.df.iloc[idx]
        img_path = self.img_dir / f"{row['image_id']}.jpg"
        img = Image.open(img_path).convert("RGB")
        label = HAM10000_LABEL_MAP[row["dx"]]
        return self.transform(img), label


def get_weighted_sampler(dataset: HAM10000Dataset) -> WeightedRandomSampler:
    """Handle class imbalance with weighted sampling."""
    labels = [HAM10000_LABEL_MAP[row["dx"]] for _, row in dataset.df.iterrows()]
    counts = Counter(labels)
    total = sum(counts.values())
    weights = [total / counts[l] for l in labels]
    return WeightedRandomSampler(weights, num_samples=len(weights), replacement=True)


def train(data_dir: str, epochs: int = 60, batch_size: int = 32, lr: float = 5e-5):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    csv_path = os.path.join(data_dir, "HAM10000_metadata.csv")
    img_dir  = os.path.join(data_dir, "images")

    train_ds = HAM10000Dataset(csv_path, img_dir, "train")
    val_ds   = HAM10000Dataset(csv_path, img_dir, "val")

    sampler = get_weighted_sampler(train_ds)
    train_dl = DataLoader(train_ds, batch_size=batch_size, sampler=sampler, num_workers=4)
    val_dl   = DataLoader(val_ds,   batch_size=batch_size, shuffle=False, num_workers=4)

    # EfficientNet-B3 — good balance of accuracy vs speed
    model = timm.create_model("efficientnet_b3", pretrained=True, num_classes=len(HAM10000_LABEL_MAP))
    model = model.to(device)

    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.OneCycleLR(
        optimizer, max_lr=lr * 10, steps_per_epoch=len(train_dl), epochs=epochs
    )
    criterion = nn.CrossEntropyLoss(label_smoothing=0.1)

    best_val_acc = 0.0

    for epoch in range(epochs):
        model.train()
        correct, total, train_loss = 0, 0, 0.0

        for imgs, labels in train_dl:
            imgs, labels = imgs.to(device), labels.to(device)
            optimizer.zero_grad()
            out = model(imgs)
            loss = criterion(out, labels)
            loss.backward()
            optimizer.step()
            scheduler.step()

            train_loss += loss.item()
            correct += out.argmax(1).eq(labels).sum().item()
            total += labels.size(0)

        model.eval()
        val_correct, val_total = 0, 0
        with torch.no_grad():
            for imgs, labels in val_dl:
                imgs, labels = imgs.to(device), labels.to(device)
                out = model(imgs)
                val_correct += out.argmax(1).eq(labels).sum().item()
                val_total += labels.size(0)

        val_acc = val_correct / val_total
        print(f"Epoch {epoch+1}/{epochs} | Train Acc: {correct/total:.4f} | Val Acc: {val_acc:.4f}")

        if val_acc > best_val_acc:
            best_val_acc = val_acc
            os.makedirs("models", exist_ok=True)
            torch.save(model.state_dict(), "models/skin_efficientnet_b3.pt")
            print(f"  ✅ Saved (val_acc={val_acc:.4f})")

    print(f"Best Validation Accuracy: {best_val_acc:.4f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data_dir", type=str, default="./datasets/ham10000")
    parser.add_argument("--epochs", type=int, default=60)
    parser.add_argument("--batch_size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=5e-5)
    args = parser.parse_args()
    train(args.data_dir, args.epochs, args.batch_size, args.lr)
