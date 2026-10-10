"""
Tongue Diagnosis Model Training
================================
Dataset: Tongue Disease Dataset (Kaggle) + supplementary
  kaggle datasets download -d salvatorerace/tongue-diseases

Classes:
  0 - Normal (healthy pink tongue)
  1 - Pale appearance (does not establish anemia or B12 deficiency)
  2 - White coating appearance (does not establish thrush)
  3 - Yellow coating appearance
  4 - Red appearance
  5 - Cracked appearance

Legacy folder-label experiment only; no clinically verified diagnostic targets.

Architecture: MobileNetV3-Large (fast, mobile-friendly, suits subtle color diff)

Usage:
  python training/train_tongue.py --data_dir ./datasets/tongue --epochs 40
"""
import argparse
import os
import json
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms
from PIL import Image, ImageEnhance
import timm
from pathlib import Path
from sklearn.model_selection import train_test_split

TONGUE_CLASSES = {
    0: "Normal",
    1: "Pale",
    2: "WhiteCoat",
    3: "YellowCoat",
    4: "RedInflamed",
    5: "DryCracked",
}

# Alternate directory names for different dataset versions
CLASS_DIR_ALIASES = {
    "Normal":       ["Normal", "normal", "healthy"],
    "Pale":         ["Pale", "pale"],
    "WhiteCoat":    ["WhiteCoat", "white_coat", "white coat"],
    "YellowCoat":   ["YellowCoat", "yellow_coat", "yellow coat"],
    "RedInflamed":  ["RedInflamed", "red", "inflamed", "Red"],
    "DryCracked":   ["DryCracked", "dry", "cracked", "dry_cracked"],
}


class TongueDataset(Dataset):
    def __init__(self, samples: list, split: str = "train"):
        self.samples = samples
        augment = split == "train"
        self.transform = transforms.Compose([
            transforms.Resize((256, 256)),
            *([
                transforms.RandomHorizontalFlip(),
                transforms.RandomRotation(8),
                # Strong color augmentation — tongue color IS the feature
                transforms.ColorJitter(brightness=0.4, contrast=0.5, saturation=0.4, hue=0.08),
                transforms.RandomAffine(degrees=0, translate=(0.05, 0.05)),
            ] if augment else []),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
        ])

    def __len__(self): return len(self.samples)

    def __getitem__(self, idx):
        path, label = self.samples[idx]
        img = Image.open(path).convert("RGB")
        # Slight contrast enhancement to emphasize tongue color
        img = ImageEnhance.Contrast(img).enhance(1.1)
        return self.transform(img), label


def load_samples(data_dir: str):
    base = Path(data_dir)
    samples = []
    for label, cls in TONGUE_CLASSES.items():
        aliases = CLASS_DIR_ALIASES.get(cls, [cls])
        for alias in aliases:
            for root in [base, base / "train", base / "data", base / "images"]:
                cls_dir = root / alias
                if cls_dir.exists():
                    for ext in ["*.jpg", "*.png", "*.jpeg"]:
                        for p in cls_dir.glob(ext):
                            samples.append((str(p), label))
                    break
    return samples


def train(data_dir: str, epochs: int = 40, batch_size: int = 32, lr: float = 1e-4, legacy_unvalidated=False):
    if not legacy_unvalidated:
        raise ValueError('Legacy folder labels are not clinical diagnoses. Use audited tongue annotations; exploratory execution requires --legacy-unvalidated.')
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")

    all_samples = load_samples(data_dir)
    if not all_samples:
        print(f"No tongue images found in {data_dir}. Run dataset_setup.py first.")
        return

    print(f"Total tongue images: {len(all_samples)}")
    classes_found = set(s[1] for s in all_samples)
    print(f"Classes found: {[TONGUE_CLASSES[c] for c in sorted(classes_found)]}")

    labels_list = [s[1] for s in all_samples]
    train_s, val_s = train_test_split(
        all_samples, test_size=0.2, stratify=labels_list, random_state=42
    )

    train_dl = DataLoader(TongueDataset(train_s, "train"), batch_size=batch_size, shuffle=True, num_workers=4)
    val_dl   = DataLoader(TongueDataset(val_s, "val"),     batch_size=batch_size, shuffle=False, num_workers=4)

    # MobileNetV3 — fast, good for color-based classification
    model = timm.create_model("mobilenetv3_large_100", pretrained=True, num_classes=len(TONGUE_CLASSES))
    model = model.to(device)

    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
    criterion = nn.CrossEntropyLoss(label_smoothing=0.05)

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
            correct += out.detach().argmax(1).eq(labels_b).sum().item()
            total += labels_b.size(0)
        scheduler.step()

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
            torch.save(model.state_dict(), "models/tongue_mobilenetv3.pt")
            print(f"  Saved (val_acc={val_acc:.4f})")

    print(f"Best Val Accuracy: {best_val_acc:.4f}")
    with open("models/tongue_training_history.json", "w") as f:
        json.dump({"best_val_acc": best_val_acc, "classes": TONGUE_CLASSES}, f)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data_dir", type=str, default="./datasets/tongue")
    parser.add_argument("--epochs", type=int, default=40)
    parser.add_argument("--batch_size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument('--legacy-unvalidated', action='store_true')
    args = parser.parse_args()
    train(args.data_dir, args.epochs, args.batch_size, args.lr, args.legacy_unvalidated)
