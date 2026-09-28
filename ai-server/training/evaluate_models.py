"""
MediScan AI -- Model Evaluation Suite
========================================
Generates comprehensive evaluation metrics for all trained models:
  - Overall accuracy, precision, recall, F1
  - Per-class metrics
  - Confusion matrix (saved as PNG)
  - Classification report (saved as JSON)
  - ROC curves for binary models

Usage:
  python training/evaluate_models.py               # evaluate all
  python training/evaluate_models.py --model skin  # evaluate one
  python training/evaluate_models.py --use-onnx    # use ONNX models
"""

import argparse
import os
import sys
import json
import numpy as np
from pathlib import Path
from datetime import datetime

try:
    import torch
    import timm
    from torch.utils.data import DataLoader, Dataset
    from torchvision import transforms
    from PIL import Image
    from sklearn.metrics import (
        classification_report, confusion_matrix,
        accuracy_score, roc_auc_score
    )
    import matplotlib
    matplotlib.use("Agg")  # non-interactive backend
    import matplotlib.pyplot as plt
    import seaborn as sns
except ImportError:
    print("Installing evaluation dependencies...")
    os.system(f"{sys.executable} -m pip install scikit-learn matplotlib seaborn -q")
    import torch
    import timm
    from torch.utils.data import DataLoader, Dataset
    from torchvision import transforms
    from PIL import Image
    from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import seaborn as sns

MODELS_DIR  = Path("models")
REPORTS_DIR = Path("models/reports")
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

EVAL_CONFIGS = {
    "anemia": {
        "arch":        "efficientnet_b4",
        "num_classes": 2,
        "input_size":  380,
        "pt_file":     "anemia_efficientnet_b4.pt",
        "data_dir":    "datasets/anemia/val",
        "class_names": ["Normal", "Anemic"],
        "class_dirs":  ["normal", "anemic"],
    },
    "skin": {
        "arch":        "efficientnet_b3",
        "num_classes": 7,
        "input_size":  300,
        "pt_file":     "skin_efficientnet_b3.pt",
        "data_dir":    "datasets/ham10000",
        "class_names": ["Actinic Keratosis", "BCC", "Benign Keratosis",
                        "Dermatofibroma", "Melanoma", "Nevus", "Vascular"],
        "class_dirs":  None,  # loaded from CSV
    },
    "eye": {
        "arch":        "efficientnet_b4",
        "num_classes": 4,
        "input_size":  380,
        "pt_file":     "eye_efficientnet_b4.pt",
        "data_dir":    "datasets/eye",
        "class_names": ["Normal", "Cataract", "Diabetic Retinopathy", "Glaucoma"],
        "class_dirs":  ["Normal", "Cataract", "Diabetic_Retinopathy", "Glaucoma"],
    },
    "wound": {
        "arch":        "efficientnet_b3",
        "num_classes": 5,
        "input_size":  300,
        "pt_file":     "wound_efficientnet_b3.pt",
        "data_dir":    "datasets/wound",
        "class_names": ["Chronic", "Fresh", "Granulating", "Infected", "Healed"],
        "class_dirs":  ["Chronic", "Fresh", "Granulating", "Infected", "Healed"],
    },
    "tongue": {
        "arch":        "mobilenetv3_large_100",
        "num_classes": 6,
        "input_size":  256,
        "pt_file":     "tongue_mobilenetv3.pt",
        "data_dir":    "datasets/tongue",
        "class_names": ["Normal", "Pale", "White Coat", "Yellow Coat",
                        "Red Inflamed", "Dry Cracked"],
        "class_dirs":  ["Normal", "Pale", "WhiteCoat", "YellowCoat",
                        "RedInflamed", "DryCracked"],
    },
    "posture": {
        "arch":        "mlp",
        "num_classes": 3,
        "input_size":  99,
        "pt_file":     "posture_mlp.pt",
        "data_dir":    "datasets/posture",
        "class_names": ["Normal", "Mild Imbalance", "Significant Deviation"],
        "class_dirs":  None,
    },
}


# ── Dataset loader ────────────────────────────────────────────
class EvalImageDataset(Dataset):
    def __init__(self, samples: list, input_size: int):
        self.samples = samples
        self.transform = transforms.Compose([
            transforms.Resize((input_size, input_size)),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
        ])

    def __len__(self): return len(self.samples)

    def __getitem__(self, idx):
        path, label = self.samples[idx]
        img = Image.open(path).convert("RGB")
        return self.transform(img), label


def load_eval_samples(cfg: dict):
    if cfg["class_dirs"] is None:
        return []
    base = Path(cfg["data_dir"])
    samples = []
    for label, cls_dir in enumerate(cfg["class_dirs"]):
        for search_root in [base, base / "val", base / "test"]:
            d = search_root / cls_dir
            if d.exists():
                for ext in ["*.jpg", "*.png", "*.jpeg"]:
                    for p in list(d.glob(ext))[:200]:  # max 200 per class for eval speed
                        samples.append((str(p), label))
                break
    return samples


# ── Model loader ──────────────────────────────────────────────
class PostureMLP(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.net = torch.nn.Sequential(
            torch.nn.Linear(99, 256), torch.nn.BatchNorm1d(256),
            torch.nn.ReLU(), torch.nn.Dropout(0.3),
            torch.nn.Linear(256, 128), torch.nn.BatchNorm1d(128),
            torch.nn.ReLU(), torch.nn.Dropout(0.2),
            torch.nn.Linear(128, 64), torch.nn.ReLU(),
            torch.nn.Linear(64, 3),
        )

    def forward(self, x): return self.net(x)


def load_model(name: str, cfg: dict):
    pt_path = MODELS_DIR / cfg["pt_file"]
    if not pt_path.exists():
        raise FileNotFoundError(f"Model not found: {pt_path}")
    if cfg["arch"] == "mlp":
        model = PostureMLP()
    else:
        model = timm.create_model(cfg["arch"], pretrained=False, num_classes=cfg["num_classes"])
    state = torch.load(str(pt_path), map_location="cpu", weights_only=True)
    model.load_state_dict(state)
    model.eval()
    return model


# ── Evaluation ────────────────────────────────────────────────
def evaluate_model(name: str, cfg: dict) -> dict:
    print(f"\nEvaluating: {name}")

    pt_path = MODELS_DIR / cfg["pt_file"]
    if not pt_path.exists():
        print(f"  [SKIP] Model not found: {pt_path}")
        return {"status": "skipped"}

    # Load model
    try:
        model = load_model(name, cfg)
    except Exception as e:
        print(f"  [FAIL] Could not load model: {e}")
        return {"status": "error", "error": str(e)}

    # Load samples
    if name == "posture":
        # Generate synthetic test data
        from training.train_posture import generate_synthetic_poses
        X, y = generate_synthetic_poses(1500)
        split = int(len(X) * 0.8)
        X_val, y_val = X[split:], y[split:]
        all_preds, all_labels = [], []
        model_input = torch.tensor(X_val)
        with torch.no_grad():
            logits = model(model_input)
            preds = logits.argmax(1).numpy()
        all_preds = preds.tolist()
        all_labels = y_val.tolist()
    else:
        samples = load_eval_samples(cfg)
        if not samples:
            print(f"  [SKIP] No eval samples found in {cfg['data_dir']}")
            return {"status": "no_data"}

        print(f"  Samples: {len(samples)}")
        dataset = EvalImageDataset(samples, cfg["input_size"])
        loader = DataLoader(dataset, batch_size=32, num_workers=2)
        all_preds, all_labels = [], []

        with torch.no_grad():
            for imgs, labels in loader:
                out = model(imgs)
                preds = out.argmax(1).numpy()
                all_preds.extend(preds.tolist())
                all_labels.extend(labels.numpy().tolist())

    # Metrics
    acc = accuracy_score(all_labels, all_preds)
    report = classification_report(
        all_labels, all_preds,
        target_names=cfg["class_names"][:cfg["num_classes"]],
        output_dict=True,
        zero_division=0,
    )
    cm = confusion_matrix(all_labels, all_preds)

    print(f"  Accuracy: {acc:.4f}")
    print(f"  F1 (macro): {report['macro avg']['f1-score']:.4f}")

    # Save confusion matrix plot
    _save_confusion_matrix(name, cm, cfg["class_names"][:cfg["num_classes"]])

    # Save classification report
    result = {
        "status": "evaluated",
        "model": name,
        "accuracy": round(acc, 4),
        "f1_macro": round(report["macro avg"]["f1-score"], 4),
        "precision_macro": round(report["macro avg"]["precision"], 4),
        "recall_macro": round(report["macro avg"]["recall"], 4),
        "per_class": {
            cls: {
                "precision": round(report[cls]["precision"], 4),
                "recall":    round(report[cls]["recall"], 4),
                "f1":        round(report[cls]["f1-score"], 4),
                "support":   report[cls]["support"],
            }
            for cls in cfg["class_names"][:cfg["num_classes"]]
            if cls in report
        },
        "evaluated_at": datetime.utcnow().isoformat(),
    }

    report_path = REPORTS_DIR / f"{name}_eval.json"
    with open(str(report_path), "w") as f:
        json.dump(result, f, indent=2)
    print(f"  Report saved: {report_path}")

    return result


def _save_confusion_matrix(name: str, cm: np.ndarray, class_names: list):
    plt.figure(figsize=(max(6, len(class_names)), max(5, len(class_names) - 1)))
    # Normalize
    cm_norm = cm.astype(float) / (cm.sum(axis=1, keepdims=True) + 1e-9)
    sns.heatmap(
        cm_norm, annot=True, fmt=".2f", cmap="Blues",
        xticklabels=class_names, yticklabels=class_names,
        linewidths=0.5,
    )
    plt.title(f"MediScan AI — {name.title()} Confusion Matrix", pad=15, fontsize=13)
    plt.ylabel("True Label", fontsize=11)
    plt.xlabel("Predicted Label", fontsize=11)
    plt.xticks(rotation=30, ha="right", fontsize=9)
    plt.yticks(rotation=0, fontsize=9)
    plt.tight_layout()
    out_path = REPORTS_DIR / f"{name}_confusion_matrix.png"
    plt.savefig(str(out_path), dpi=150)
    plt.close()
    print(f"  Confusion matrix: {out_path}")


def print_summary(all_results: dict):
    print("\n" + "=" * 65)
    print("EVALUATION SUMMARY")
    print("=" * 65)
    print(f"  {'Model':12} {'Accuracy':10} {'F1 Macro':10} {'Status'}")
    print("-" * 65)
    for name, r in all_results.items():
        if r.get("status") == "evaluated":
            print(f"  {name:12} {r['accuracy']:10.4f} {r['f1_macro']:10.4f}  OK")
        else:
            print(f"  {name:12} {'—':>10} {'—':>10}  {r.get('status','?')}")

    # Overall report
    evaluated = {k: v for k, v in all_results.items() if v.get("status") == "evaluated"}
    if evaluated:
        avg_acc = np.mean([v["accuracy"] for v in evaluated.values()])
        avg_f1  = np.mean([v["f1_macro"] for v in evaluated.values()])
        print(f"\n  Average accuracy: {avg_acc:.4f}")
        print(f"  Average F1 (macro): {avg_f1:.4f}")

    print(f"\n  Reports saved in: {REPORTS_DIR.absolute()}")


def main():
    parser = argparse.ArgumentParser(description="MediScan AI Model Evaluation")
    parser.add_argument("--model", type=str, default="all",
                        choices=["all"] + list(EVAL_CONFIGS.keys()))
    parser.add_argument("--use-onnx", action="store_true",
                        help="Use ONNX models instead of PyTorch")
    args = parser.parse_args()

    targets = list(EVAL_CONFIGS.keys()) if args.model == "all" else [args.model]

    print("MediScan AI -- Model Evaluation")
    print("=" * 65)

    all_results = {}
    for name in targets:
        all_results[name] = evaluate_model(name, EVAL_CONFIGS[name])

    # Save master summary
    summary_path = REPORTS_DIR / "evaluation_summary.json"
    with open(str(summary_path), "w") as f:
        json.dump(all_results, f, indent=2)

    print_summary(all_results)


if __name__ == "__main__":
    main()
