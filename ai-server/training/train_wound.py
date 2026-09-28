"""
Wound Healing Stage Classification Training
============================================
Dataset: Wound Healing Stages (Kaggle)
  kaggle datasets download -d syedaadnanali99/wound-healing-stages

Classes:
  0 - Chronic (non-healing)
  1 - Fresh / Acute
  2 - Granulating (healing)
  3 - Infected
  4 - Healed

Architecture: EfficientNet-B3 (lighter — wound features need less depth)

Usage:
  python training/train_wound.py --data_dir ./datasets/wound --epochs 40
"""
import argparse
import os
import json
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms
from PIL import Image
import timm
from pathlib import Path
from sklearn.model_selection import train_test_split

WOUND_CLASSES = {0: "Chronic", 1: "Fresh", 2: "Granulating", 3: "Infected", 4: "Healed"}
CLASS_DIRS = ["Chronic", "Fresh", "Granulating", "Infected", "Healed"]
# Also try alternate spellings from different dataset versions
ALT_CLASS_DIRS = {
    "Chronic": ["Chronic", "chronic", "CHRONIC", "Non-Healing"],
    "Fresh":   ["Fresh", "Acute", "acute", "fresh"],
    "Granulating": ["Granulating", "Granulation", "granulating"],
    "Infected":    ["Infected", "infected", "INFECTED"],
    "Healed":      ["Healed", "Healing", "healed"],
}


class WoundDataset(Dataset):
    def __init__(self, samples: list, split: str = "train"):
        self.samples = samples
        augment = split == "train"
        self.transform = transforms.Compose([
            transforms.Resize((300, 300)),
            *([
                transforms.RandomHorizontalFlip(),
                transforms.RandomRotation(15),
                transforms.ColorJitter(brightness=0.4, contrast=0.4, saturation=0.3, hue=0.05),
                transforms.RandomAffine(degrees=0, translate=(0.1, 0.1)),
            ] if augment else []),
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
        candidates = ALT_CLASS_DIRS[cls]
        for candidate in candidates:
            for search_root in [base, base / "train", base / "data"]:
                cls_dir = search_root / candidate
                if cls_dir.exists():
                    for ext in ["*.jpg", "*.png", "*.jpeg"]:
                        for p in cls_dir.glob(ext):
                            samples.append((str(p), label))
                    break
    return samples


def train(data_dir: str, epochs: int = 40, batch_size: int = 32, lr: float = 1e-4):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")

    all_samples = load_samples(data_dir)
    if not all_samples:
        print(f"No images found in {data_dir}. Run dataset_setup.py first.")
        return

    print(f"Total wound images: {len(all_samples)}")
    labels = [s[1] for s in all_samples]
    train_s, val_s = train_test_split(all_samples, test_size=0.2, stratify=labels, random_state=42)

    train_dl = DataLoader(WoundDataset(train_s, "train"), batch_size=batch_size, shuffle=True, num_workers=4)
    val_dl   = DataLoader(WoundDataset(val_s, "val"),     batch_size=batch_size, shuffle=False, num_workers=4)

    model = timm.create_model("efficientnet_b3", pretrained=True, num_classes=len(WOUND_CLASSES))
    model = model.to(device)

    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.OneCycleLR(
        optimizer, max_lr=lr * 10, steps_per_epoch=len(train_dl), epochs=epochs
    )
    criterion = nn.CrossEntropyLoss(label_smoothing=0.1)

    best_val_acc = 0.0

    for epoch in range(epochs):
        model.train()
        correct = total = 0
        for imgs, labels_b in train_dl:
            imgs, labels_b = imgs.to(device), labels_b.to(device)
            optimizer.zero_grad()
            out = model(imgs)
            loss = criterion(out, labels_b)
            loss.backward()
            optimizer.step()
            scheduler.step()
            correct += out.detach().argmax(1).eq(labels_b).sum().item()
            total += labels_b.size(0)

        model.eval()
        vc = vt = 0
        with torch.no_grad():
            for imgs, labels_b in val_dl:
                imgs, labels_b = imgs.to(device), labels_b.to(device)
                vc += model(imgs).argmax(1).eq(labels_b).sum().item()
                vt += labels_b.size(0)

        val_acc = vc / vt
        print(f"Epoch {epoch+1}/{epochs} | Train: {correct/total:.4f} | Val: {val_acc:.4f}")

        if val_acc > best_val_acc:
            best_val_acc = val_acc
            os.makedirs("models", exist_ok=True)
            torch.save(model.state_dict(), "models/wound_efficientnet_b3.pt")
            print(f"  Saved (val_acc={val_acc:.4f})")

    print(f"Best Val Accuracy: {best_val_acc:.4f}")
    with open("models/wound_training_history.json", "w") as f:
        json.dump({"best_val_acc": best_val_acc, "classes": WOUND_CLASSES}, f)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data_dir", type=str, default="./datasets/wound")
    parser.add_argument("--epochs", type=int, default=40)
    parser.add_argument("--batch_size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=1e-4)
    args = parser.parse_args()
    train(args.data_dir, args.epochs, args.batch_size, args.lr)
