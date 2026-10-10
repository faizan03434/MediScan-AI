"""
MediScan AI -- Full Training Pipeline Orchestrator
====================================================
Legacy exploratory scripts for unreviewed tasks. Default execution is blocked.
Use the audited intake and research training commands in docs/IMPLEMENTATION_STATUS.md.

Usage:
  # Full pipeline (all models):
  python training/run_pipeline.py

  # Single model:
  python training/run_pipeline.py --model anemia

  # Skip dataset download (already done):
  python training/run_pipeline.py --skip-download

  # Only evaluate existing models:
  python training/run_pipeline.py --eval-only

Requirements:
  pip install kaggle torch torchvision timm onnx onnxruntime
  scikit-learn matplotlib seaborn pandas tqdm
"""

import argparse
import subprocess
import sys
import os
import json
from pathlib import Path
from datetime import datetime

PIPELINE_STAGES = [
    {
        "model": "posture",
        "dataset_key": "posture",
        "train_script": "training/train_posture.py",
        "data_dir": "datasets/posture",
        "output_model": "models/posture_mlp.pt",
        "epochs": 100,
        "note": "Fast — synthetic data, MLP, no GPU needed",
    },
    {
        "model": "anemia",
        "dataset_key": "anemia",
        "train_script": "training/train_anemia.py",
        "data_dir": "datasets/anemia",
        "output_model": "models/anemia_efficientnet_b4.pt",
        "epochs": 50,
        "note": "Binary classification, EfficientNet-B4",
    },
    {
        "model": "tongue",
        "dataset_key": "tongue",
        "train_script": "training/train_tongue.py",
        "data_dir": "datasets/tongue",
        "output_model": "models/tongue_mobilenetv3.pt",
        "epochs": 40,
        "note": "MobileNetV3, color-sensitive augmentation",
    },
    {
        "model": "wound",
        "dataset_key": "wound",
        "train_script": "training/train_wound.py",
        "data_dir": "datasets/wound",
        "output_model": "models/wound_efficientnet_b3.pt",
        "epochs": 40,
        "note": "5-class wound stage classification",
    },
    {
        "model": "eye",
        "dataset_key": "eye",
        "train_script": "training/train_eye.py",
        "data_dir": "datasets/eye",
        "output_model": "models/eye_efficientnet_b4.pt",
        "epochs": 50,
        "note": "4-class eye disease detection",
    },
    {
        "model": "skin",
        "dataset_key": "skin",
        "train_script": "training/train_skin.py",
        "data_dir": "datasets/ham10000",
        "output_model": "models/skin_efficientnet_b3.pt",
        "epochs": 60,
        "note": "HAM10000, heaviest dataset — run last",
    },
]


def run_cmd(cmd: list, label: str) -> bool:
    """Run subprocess, return True on success."""
    print(f"\n{'='*60}")
    print(f"  Running: {label}")
    print(f"  Command: {' '.join(cmd)}")
    print(f"{'='*60}")
    result = subprocess.run(cmd)
    success = result.returncode == 0
    print(f"  {'OK' if success else 'FAILED'}: {label}")
    return success


def check_gpu():
    try:
        import torch
        if torch.cuda.is_available():
            name = torch.cuda.get_device_name(0)
            mem = torch.cuda.get_device_properties(0).total_memory / 1e9
            print(f"GPU: {name} ({mem:.1f} GB VRAM)")
            return True
        else:
            print("No GPU found. Training will use CPU (slower but works).")
            print("Tip: Use Google Colab (free GPU) for faster training.")
            return False
    except ImportError:
        print("PyTorch not installed.")
        return False


def print_training_plan(stages: list):
    print("\nTraining Plan:")
    print(f"{'Model':15} {'Dataset':25} {'Epochs':8} {'Note'}")
    print("-" * 75)
    for s in stages:
        model_exists = Path(s["output_model"]).exists()
        status = "PRESENT_UNVALIDATED" if model_exists else "MISSING"
        print(f"  [{status}] {s['model']:12} {s['data_dir']:25} {s['epochs']:6}  {s['note']}")


def save_pipeline_report(results: dict):
    report = {
        "timestamp": datetime.utcnow().isoformat(),
        "results": results,
        "models_dir": str(Path("models").absolute()),
    }
    with open("models/pipeline_report.json", "w") as f:
        json.dump(report, f, indent=2)
    print("\nPipeline report saved to models/pipeline_report.json")


def main():
    parser = argparse.ArgumentParser(description="MediScan AI Training Pipeline")
    parser.add_argument("--model", type=str, default="all",
                        choices=["all"] + [s["model"] for s in PIPELINE_STAGES])
    parser.add_argument("--skip-download", action="store_true")
    parser.add_argument("--eval-only", action="store_true")
    parser.add_argument("--export-onnx", action="store_true",
                        help="Export to ONNX after training")
    parser.add_argument("--legacy-unvalidated", action="store_true",
                        help="Explicit research-only legacy exploration; not the reviewed product pipeline")
    args = parser.parse_args()
    if not args.legacy_unvalidated:
        parser.error('The legacy all-model pipeline uses unreviewed datasets/synthetic targets. '
            'Use acquire_medical_research.py and train_skin_transfer.py for audited research workflows. '
            'Legacy exploration requires --legacy-unvalidated and never establishes clinical readiness.')

    print("MediScan AI -- Training Pipeline")
    print("="*60)
    check_gpu()

    stages = PIPELINE_STAGES if args.model == "all" else [
        s for s in PIPELINE_STAGES if s["model"] == args.model
    ]

    print_training_plan(stages)

    if args.eval_only:
        print("\nEval-only mode. Run evaluation scripts separately:")
        print("  python training/evaluate_models.py")
        return

    os.makedirs("models", exist_ok=True)
    results = {}

    # Step 1: Dataset download
    if not args.skip_download:
        dataset_keys = list(set(s["dataset_key"] for s in stages))
        for key in dataset_keys:
            ok = run_cmd(
                [sys.executable, "training/dataset_setup.py", "--dataset", key],
                f"Download dataset: {key}"
            )
            results[f"download_{key}"] = ok

    # Step 2: Training
    for stage in stages:
        model_path = Path(stage["output_model"])
        if model_path.exists():
            print(f"\n  [SKIP] {stage['model']} model already exists at {model_path}")
            results[f"train_{stage['model']}"] = True
            continue

        ok = run_cmd(
            [
                sys.executable, stage["train_script"],
                "--data_dir", stage["data_dir"],
                "--epochs", str(stage["epochs"]),
                *(['--legacy-unvalidated'] if stage['model'] in {'posture', 'tongue'} else []),
            ],
            f"Train: {stage['model']}"
        )
        results[f"train_{stage['model']}"] = ok

    # Step 3: ONNX export
    if args.export_onnx:
        ok = run_cmd(
            [sys.executable, "training/export_onnx.py"],
            "Export all models to ONNX"
        )
        results["export_onnx"] = ok

    # Step 4: Evaluation
    eval_script = Path("training/evaluate_models.py")
    if eval_script.exists():
        ok = run_cmd(
            [sys.executable, "training/evaluate_models.py"],
            "Evaluate all models"
        )
        results["evaluate"] = ok

    save_pipeline_report(results)

    # Summary
    print("\n" + "="*60)
    print("PIPELINE SUMMARY")
    print("="*60)
    for key, success in results.items():
        print(f"  {'OK' if success else 'FAIL'} | {key}")

    all_ok = all(results.values())
    print(f"\nPipeline {'COMPLETE' if all_ok else 'COMPLETED WITH ERRORS'}")
    if all_ok:
        print("\nNext steps:")
        print("  1. Copy .pt files from models/ to your deployment environment")
        print("  2. Run: uvicorn main:app --reload --port 8000")
        print("  3. Test endpoints: http://localhost:8000/docs")


if __name__ == "__main__":
    main()
