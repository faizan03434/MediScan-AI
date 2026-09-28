"""
MediScan AI -- Dataset Download & Setup Script
==============================================
Downloads and prepares all 6 training datasets.

Usage:
    python training/dataset_setup.py --dataset all
    python training/dataset_setup.py --dataset anemia
    python training/dataset_setup.py --dataset skin

Kaggle setup (one-time):
    1. Go to https://www.kaggle.com/account -> Create API token
    2. Place kaggle.json at: ~/.kaggle/kaggle.json
"""

import argparse
import os
import sys
import zipfile
import shutil
import subprocess
from pathlib import Path

DATASETS_DIR = Path("datasets")
DATASETS_DIR.mkdir(exist_ok=True)

DATASET_CONFIGS = {
    "anemia": {
        "name": "Anemia Detection (Eye Pallor)",
        "kaggle_id": "minhajuddinmohiuddin/anemia-detection",
        "output_dir": "datasets/anemia",
        "size": "~150 MB",
        "notes": "Binary: anemic vs normal eyelid/nail images",
        "train_script": "training/train_anemia.py",
    },
    "skin": {
        "name": "HAM10000 Skin Lesion",
        "kaggle_id": "kmader/skin-lesion-analysis-toward-melanoma-detection",
        "output_dir": "datasets/ham10000",
        "size": "~2.4 GB",
        "notes": "10,015 dermoscopic images, 7 classes",
        "train_script": "training/train_skin.py",
    },
    "eye": {
        "name": "Eye Disease Classification",
        "kaggle_id": "gunavenkatdoddi/eye-diseases-classification",
        "output_dir": "datasets/eye",
        "size": "~1.2 GB",
        "notes": "4 classes: Normal, Cataract, Diabetic Retinopathy, Glaucoma",
        "train_script": "training/train_eye.py",
    },
    "wound": {
        "name": "Wound Healing Stages",
        "kaggle_id": "syedaadnanali99/wound-healing-stages",
        "output_dir": "datasets/wound",
        "size": "~300 MB",
        "notes": "Chronic, Fresh, Granulating, Infected, Healed stages",
        "train_script": "training/train_wound.py",
    },
    "tongue": {
        "name": "Tongue Disease Dataset",
        "kaggle_id": "salvatorerace/tongue-diseases",
        "output_dir": "datasets/tongue",
        "size": "~200 MB",
        "notes": "Tongue color/coating classification",
        "train_script": "training/train_tongue.py",
    },
    "posture": {
        "name": "Human Pose / Posture Dataset",
        "kaggle_id": "niharika41298/yoga-poses-dataset",
        "output_dir": "datasets/posture",
        "size": "~100 MB",
        "notes": "Used for posture angle calibration alongside MediaPipe",
        "train_script": "training/train_posture.py",
    },
}


def check_kaggle():
    """Verify kaggle CLI is available and configured."""
    try:
        result = subprocess.run(["kaggle", "--version"], capture_output=True, text=True)
        if result.returncode != 0:
            raise FileNotFoundError
        print(f"Kaggle CLI: {result.stdout.strip()}")
        return True
    except FileNotFoundError:
        print("Kaggle CLI not found. Installing...")
        subprocess.run([sys.executable, "-m", "pip", "install", "kaggle", "-q"])
        kaggle_json = Path.home() / ".kaggle" / "kaggle.json"
        if not kaggle_json.exists():
            print("\nKaggle API key not found!")
            print("Please:")
            print("  1. Go to https://www.kaggle.com/account")
            print("  2. Click 'Create New API Token'")
            print("  3. Place the downloaded kaggle.json at:", kaggle_json)
            return False
        return True


def download_dataset(key: str, config: dict) -> bool:
    """Download a single dataset using kaggle CLI."""
    output_dir = Path(config["output_dir"])

    if output_dir.exists() and any(output_dir.iterdir()):
        print(f"  [SKIP] {config['name']} already downloaded at {output_dir}")
        return True

    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n  Downloading: {config['name']}")
    print(f"  Size: {config['size']}")
    print(f"  Kaggle ID: {config['kaggle_id']}")

    result = subprocess.run(
        ["kaggle", "datasets", "download", "-d", config["kaggle_id"],
         "--path", str(output_dir), "--unzip"],
        capture_output=False,
    )

    if result.returncode != 0:
        print(f"  [FAIL] Download failed for {config['name']}")
        return False

    print(f"  [OK] {config['name']} downloaded to {output_dir}")
    return True


def prepare_anemia_dataset(base_dir: str):
    """
    Ensures anemia dataset has train/val split structure.
    Expected: train/anemic/, train/normal/, val/anemic/, val/normal/
    """
    base = Path(base_dir)
    required = [
        base / "train" / "anemic",
        base / "train" / "normal",
        base / "val" / "anemic",
        base / "val" / "normal",
    ]
    all_exist = all(d.exists() for d in required)

    if all_exist:
        print("  Anemia dataset structure OK")
        return

    print("  Organizing anemia dataset into train/val split...")
    import random

    for class_name in ["anemic", "normal"]:
        class_dir = base / class_name
        if not class_dir.exists():
            print(f"  WARNING: {class_dir} not found. Check dataset structure.")
            continue

        images = list(class_dir.glob("*.jpg")) + list(class_dir.glob("*.png"))
        random.shuffle(images)
        split = int(len(images) * 0.8)

        train_dir = base / "train" / class_name
        val_dir   = base / "val"   / class_name
        train_dir.mkdir(parents=True, exist_ok=True)
        val_dir.mkdir(parents=True, exist_ok=True)

        for img in images[:split]:
            shutil.copy(img, train_dir / img.name)
        for img in images[split:]:
            shutil.copy(img, val_dir / img.name)

        print(f"  {class_name}: {split} train, {len(images)-split} val")


def print_summary(datasets: list):
    print("\n" + "="*60)
    print("DATASET SUMMARY")
    print("="*60)
    for key in datasets:
        cfg = DATASET_CONFIGS[key]
        output = Path(cfg["output_dir"])
        status = "READY" if output.exists() and any(output.iterdir()) else "MISSING"
        files = sum(1 for _ in output.rglob("*") if _.is_file()) if output.exists() else 0
        print(f"  {status:8} | {cfg['name']:35} | {files:6} files | {cfg['size']}")

    print("\nTraining commands:")
    for key in datasets:
        cfg = DATASET_CONFIGS[key]
        print(f"  python {cfg['train_script']} --data_dir {cfg['output_dir']}")


def main():
    parser = argparse.ArgumentParser(description="MediScan AI Dataset Setup")
    parser.add_argument(
        "--dataset", type=str, default="all",
        choices=["all"] + list(DATASET_CONFIGS.keys()),
        help="Which dataset to download"
    )
    parser.add_argument(
        "--skip-download", action="store_true",
        help="Skip download, just show status"
    )
    args = parser.parse_args()

    target = list(DATASET_CONFIGS.keys()) if args.dataset == "all" else [args.dataset]

    print("MediScan AI — Dataset Setup")
    print("="*60)

    if not args.skip_download:
        if not check_kaggle():
            print("\nSetup kaggle.json first, then re-run this script.")
            sys.exit(1)

        for key in target:
            cfg = DATASET_CONFIGS[key]
            ok = download_dataset(key, cfg)
            if ok and key == "anemia":
                prepare_anemia_dataset(cfg["output_dir"])

    print_summary(target)


if __name__ == "__main__":
    main()
