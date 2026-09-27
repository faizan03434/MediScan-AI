"""
Anemia Detection Model Training
────────────────────────────────────────────────────────────────
Dataset: Kaggle "Anemia Detection - Eye Pallor"
  kaggle datasets download -d minhajuddinmohiuddin/anemia-detection

Architecture:
  - YOLOv8n: detect eye/nail ROI
  - EfficientNet-B4: binary classify Anemic vs Non-Anemic

Usage:
  python training/train_anemia.py --data_dir ./datasets/anemia --epochs 50
────────────────────────────────────────────────────────────────
"""
import argparse
import os
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms
from PIL import Image
import timm
from pathlib import Path
import json


class AnemiaDataset(Dataset):
    """
    Expects folder structure:
    data_dir/
      train/
        anemic/   (images)
        normal/   (images)
      val/
        anemic/
        normal/
    """
    def __init__(self, data_dir: str, split: str = "train"):
        self.data_dir = Path(data_dir) / split
        self.transform = transforms.Compose([
            transforms.Resize((380, 380)),
            transforms.RandomHorizontalFlip(),
            transforms.RandomRotation(10),
            transforms.ColorJitter(brightness=0.2, contrast=0.3, saturation=0.2),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                 std=[0.229, 0.224, 0.225]),
        ])
        self.val_transform = transforms.Compose([
            transforms.Resize((380, 380)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                 std=[0.229, 0.224, 0.225]),
        ])
        self.is_train = split == "train"

        self.samples = []
        for label, class_name in enumerate(["normal", "anemic"]):
            class_dir = self.data_dir / class_name
            if class_dir.exists():
                for img_path in class_dir.glob("*.jpg"):
                    self.samples.append((str(img_path), label))
                for img_path in class_dir.glob("*.png"):
                    self.samples.append((str(img_path), label))

        print(f"[{split}] Loaded {len(self.samples)} images")

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        img_path, label = self.samples[idx]
        img = Image.open(img_path).convert("RGB")
        transform = self.transform if self.is_train else self.val_transform
        return transform(img), label


def train(data_dir: str, epochs: int = 50, batch_size: int = 32, lr: float = 1e-4):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    # Datasets
    train_ds = AnemiaDataset(data_dir, "train")
    val_ds   = AnemiaDataset(data_dir, "val")
    train_dl = DataLoader(train_ds, batch_size=batch_size, shuffle=True, num_workers=4)
    val_dl   = DataLoader(val_ds,   batch_size=batch_size, shuffle=False, num_workers=4)

    # Model: EfficientNet-B4 pretrained
    model = timm.create_model("efficientnet_b4", pretrained=True, num_classes=2)
    model = model.to(device)

    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
    criterion = nn.CrossEntropyLoss()

    best_val_acc = 0.0
    history = []

    for epoch in range(epochs):
        # ── Train ─────────────────────────────────────────
        model.train()
        train_loss = 0.0
        correct = 0
        total = 0

        for imgs, labels in train_dl:
            imgs, labels = imgs.to(device), labels.to(device)
            optimizer.zero_grad()
            outputs = model(imgs)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()

            train_loss += loss.item()
            _, predicted = outputs.max(1)
            correct += predicted.eq(labels).sum().item()
            total += labels.size(0)

        train_acc = correct / total
        scheduler.step()

        # ── Validate ───────────────────────────────────────
        model.eval()
        val_loss = 0.0
        val_correct = 0
        val_total = 0

        with torch.no_grad():
            for imgs, labels in val_dl:
                imgs, labels = imgs.to(device), labels.to(device)
                outputs = model(imgs)
                loss = criterion(outputs, labels)
                val_loss += loss.item()
                _, predicted = outputs.max(1)
                val_correct += predicted.eq(labels).sum().item()
                val_total += labels.size(0)

        val_acc = val_correct / val_total

        print(f"Epoch {epoch+1}/{epochs} | "
              f"Train Loss: {train_loss/len(train_dl):.4f} Acc: {train_acc:.4f} | "
              f"Val Loss: {val_loss/len(val_dl):.4f} Acc: {val_acc:.4f}")

        history.append({"epoch": epoch + 1, "train_acc": train_acc, "val_acc": val_acc})

        # Save best model
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            os.makedirs("models", exist_ok=True)
            torch.save(model.state_dict(), "models/anemia_efficientnet_b4.pt")
            print(f"  ✅ New best model saved (val_acc={val_acc:.4f})")

    print(f"\nTraining complete. Best Val Accuracy: {best_val_acc:.4f}")

    # Save training history
    with open("models/anemia_training_history.json", "w") as f:
        json.dump({"best_val_acc": best_val_acc, "history": history}, f, indent=2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data_dir", type=str, default="./datasets/anemia")
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--batch_size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=1e-4)
    args = parser.parse_args()
    train(args.data_dir, args.epochs, args.batch_size, args.lr)
