"""
MediScan AI -- ONNX Export Script
===================================
Converts all trained .pt PyTorch models to .onnx format.

Why ONNX?
  - 2-4x faster inference than PyTorch (CPU)
  - Works on any platform without PyTorch installed
  - Required for mobile/edge deployment
  - Supports quantization for even faster inference

Usage:
  python training/export_onnx.py                    # export all
  python training/export_onnx.py --model anemia     # export one
  python training/export_onnx.py --quantize         # export + int8 quantize
"""

import argparse
import os
import sys
import json
from pathlib import Path

try:
    import torch
    import torch.nn as nn
    import timm
    import onnx
    import onnxruntime as ort
    import numpy as np
except ImportError:
    print("Installing ONNX dependencies...")
    os.system(f"{sys.executable} -m pip install onnx onnxruntime timm -q")
    import torch
    import timm
    import onnx
    import onnxruntime as ort
    import numpy as np

MODELS_DIR = Path("models")

# Model configs: name -> (architecture, num_classes, input_size, pt_file, onnx_file)
MODEL_CONFIGS = {
    "anemia": {
        "arch":        "efficientnet_b4",
        "num_classes": 2,
        "input_size":  (1, 3, 380, 380),
        "pt_file":     "anemia_efficientnet_b4.pt",
        "onnx_file":   "anemia_efficientnet_b4.onnx",
        "input_names": ["eye_or_nail_image"],
        "output_names": ["class_probabilities"],
    },
    "skin": {
        "arch":        "efficientnet_b3",
        "num_classes": 12,
        "input_size":  (1, 3, 300, 300),
        "pt_file":     "skin_efficientnet_b3.pt",
        "onnx_file":   "skin_efficientnet_b3.onnx",
        "input_names": ["skin_image"],
        "output_names": ["class_probabilities"],
    },
    "eye": {
        "arch":        "efficientnet_b4",
        "num_classes": 4,
        "input_size":  (1, 3, 380, 380),
        "pt_file":     "eye_efficientnet_b4.pt",
        "onnx_file":   "eye_efficientnet_b4.onnx",
        "input_names": ["eye_image"],
        "output_names": ["class_probabilities"],
    },
    "wound": {
        "arch":        "efficientnet_b3",
        "num_classes": 5,
        "input_size":  (1, 3, 300, 300),
        "pt_file":     "wound_efficientnet_b3.pt",
        "onnx_file":   "wound_efficientnet_b3.onnx",
        "input_names": ["wound_image"],
        "output_names": ["class_probabilities"],
    },
    "tongue": {
        "arch":        "mobilenetv3_large_100",
        "num_classes": 6,
        "input_size":  (1, 3, 256, 256),
        "pt_file":     "tongue_mobilenetv3.pt",
        "onnx_file":   "tongue_mobilenetv3.onnx",
        "input_names": ["tongue_image"],
        "output_names": ["class_probabilities"],
    },
    "posture": {
        "arch":        "mlp",
        "num_classes": 3,
        "input_size":  (1, 99),  # 33 landmarks x 3
        "pt_file":     "posture_mlp.pt",
        "onnx_file":   "posture_mlp.onnx",
        "input_names": ["pose_landmarks"],
        "output_names": ["class_probabilities"],
    },
}


class PostureMLP(nn.Module):
    """Must match training definition exactly."""
    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(99, 256), nn.BatchNorm1d(256), nn.ReLU(), nn.Dropout(0.3),
            nn.Linear(256, 128), nn.BatchNorm1d(128), nn.ReLU(), nn.Dropout(0.2),
            nn.Linear(128, 64), nn.ReLU(),
            nn.Linear(64, 3),
        )

    def forward(self, x):
        return self.net(x)


def load_model(name: str, cfg: dict) -> nn.Module:
    """Load PyTorch model from .pt file."""
    pt_path = MODELS_DIR / cfg["pt_file"]
    if not pt_path.exists():
        raise FileNotFoundError(f"Model not found: {pt_path}\nRun training first.")

    if cfg["arch"] == "mlp":
        model = PostureMLP()
    else:
        model = timm.create_model(cfg["arch"], pretrained=False, num_classes=cfg["num_classes"])

    state = torch.load(str(pt_path), map_location="cpu", weights_only=True)
    model.load_state_dict(state)
    model.eval()
    print(f"  Loaded: {pt_path}")
    return model


def export_to_onnx(name: str, cfg: dict) -> Path:
    """Export a single model to ONNX."""
    onnx_path = MODELS_DIR / cfg["onnx_file"]

    print(f"\nExporting: {name}")
    print(f"  Architecture: {cfg['arch']} | Classes: {cfg['num_classes']}")
    print(f"  Input size:  {cfg['input_size']}")

    model = load_model(name, cfg)

    # Create dummy input
    dummy = torch.randn(*cfg["input_size"])

    # Export
    torch.onnx.export(
        model,
        dummy,
        str(onnx_path),
        input_names=cfg["input_names"],
        output_names=cfg["output_names"],
        dynamic_axes={
            cfg["input_names"][0]:  {0: "batch_size"},
            cfg["output_names"][0]: {0: "batch_size"},
        },
        opset_version=17,
        do_constant_folding=True,
    )

    # Validate with onnx checker
    onnx_model = onnx.load(str(onnx_path))
    onnx.checker.check_model(onnx_model)

    size_mb = onnx_path.stat().st_size / 1e6
    print(f"  Exported: {onnx_path} ({size_mb:.1f} MB)")

    return onnx_path


def verify_onnx_inference(name: str, cfg: dict, onnx_path: Path):
    """Verify ONNX model runs and produces same output as PyTorch."""
    print("  Verifying inference...")

    dummy = np.random.randn(*cfg["input_size"]).astype(np.float32)

    # PyTorch output
    model = load_model(name, cfg)
    with torch.no_grad():
        pt_out = torch.softmax(model(torch.tensor(dummy)), dim=1).numpy()

    # ONNX output
    sess = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    input_name = sess.get_inputs()[0].name
    onnx_logits = sess.run(None, {input_name: dummy})[0]
    onnx_out = np.exp(onnx_logits) / np.exp(onnx_logits).sum(axis=1, keepdims=True)

    max_diff = np.abs(pt_out - onnx_out).max()
    print(f"  Max output diff (PyTorch vs ONNX): {max_diff:.6f}")
    assert max_diff < 0.01, f"Output mismatch too large: {max_diff}"
    print("  Verification PASSED")


def quantize_model(onnx_path: Path) -> Path:
    """Apply INT8 dynamic quantization for even faster CPU inference."""
    try:
        from onnxruntime.quantization import quantize_dynamic, QuantType
        q_path = onnx_path.with_name(onnx_path.stem + "_int8.onnx")
        quantize_dynamic(str(onnx_path), str(q_path), weight_type=QuantType.QInt8)
        size_before = onnx_path.stat().st_size / 1e6
        size_after  = q_path.stat().st_size / 1e6
        print(f"  Quantized: {q_path.name} ({size_before:.1f}MB -> {size_after:.1f}MB)")
        return q_path
    except Exception as e:
        print(f"  Quantization skipped: {e}")
        return onnx_path


def benchmark_model(name: str, cfg: dict, onnx_path: Path, n_runs: int = 50):
    """Benchmark ONNX inference speed."""
    import time
    dummy = np.random.randn(*cfg["input_size"]).astype(np.float32)
    sess = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    input_name = sess.get_inputs()[0].name

    # Warmup
    for _ in range(5):
        sess.run(None, {input_name: dummy})

    # Benchmark
    start = time.perf_counter()
    for _ in range(n_runs):
        sess.run(None, {input_name: dummy})
    elapsed = (time.perf_counter() - start) / n_runs * 1000

    print(f"  Inference speed (CPU): {elapsed:.1f} ms/image")
    return elapsed


def main():
    parser = argparse.ArgumentParser(description="MediScan AI ONNX Export")
    parser.add_argument("--model", type=str, default="all",
                        choices=["all"] + list(MODEL_CONFIGS.keys()))
    parser.add_argument("--quantize", action="store_true",
                        help="Also export INT8 quantized version")
    parser.add_argument("--benchmark", action="store_true",
                        help="Benchmark inference speed after export")
    parser.add_argument("--verify", action="store_true", default=True,
                        help="Verify PyTorch vs ONNX output match")
    args = parser.parse_args()

    MODELS_DIR.mkdir(exist_ok=True)

    targets = list(MODEL_CONFIGS.keys()) if args.model == "all" else [args.model]

    results = {}
    benchmark_results = {}

    print("MediScan AI -- ONNX Export")
    print("=" * 60)

    for name in targets:
        cfg = MODEL_CONFIGS[name]
        pt_path = MODELS_DIR / cfg["pt_file"]

        if not pt_path.exists():
            print(f"\n  [SKIP] {name}: {pt_path} not found. Train model first.")
            results[name] = "skipped"
            continue

        try:
            onnx_path = export_to_onnx(name, cfg)

            if args.verify:
                verify_onnx_inference(name, cfg, onnx_path)

            if args.quantize:
                quantize_model(onnx_path)

            if args.benchmark:
                ms = benchmark_model(name, cfg, onnx_path)
                benchmark_results[name] = f"{ms:.1f}ms"

            results[name] = "exported"

        except FileNotFoundError as e:
            print(f"  [SKIP] {e}")
            results[name] = "skipped"
        except Exception as e:
            print(f"  [FAIL] {name}: {e}")
            results[name] = f"error: {e}"

    # Summary
    print("\n" + "=" * 60)
    print("EXPORT SUMMARY")
    print("=" * 60)
    for name, status in results.items():
        onnx_file = MODELS_DIR / MODEL_CONFIGS[name]["onnx_file"]
        size = f"({onnx_file.stat().st_size/1e6:.1f}MB)" if onnx_file.exists() else ""
        bench = benchmark_results.get(name, "")
        print(f"  {status:10} | {name:10} {size:12} {bench}")

    # Save export manifest
    manifest = {
        "exported_at": __import__("datetime").datetime.utcnow().isoformat(),
        "models": {
            name: {
                "status": results.get(name, "skipped"),
                "onnx_file": MODEL_CONFIGS[name]["onnx_file"],
                "input_size": MODEL_CONFIGS[name]["input_size"],
                "num_classes": MODEL_CONFIGS[name]["num_classes"],
            }
            for name in targets
        }
    }
    with open(str(MODELS_DIR / "onnx_manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)
    print("\nManifest saved: models/onnx_manifest.json")


if __name__ == "__main__":
    main()
