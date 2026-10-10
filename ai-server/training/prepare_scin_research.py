"""Small three-label research cohort; class/case split is not clinical validation."""
import argparse
import ast
import csv
import hashlib
import io
import json
import random
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from PIL import Image
from fetch_scin import BASE, ROOT, fetch

CLASSES = ["Acne", "Eczema", "Tinea"]


def eligible_cases(directory):
    with (directory / "scin_cases.csv").open(encoding="utf-8-sig", newline="") as f:
        cases = {r["case_id"]: r for r in csv.DictReader(f)}
    with (directory / "scin_labels.csv").open(encoding="utf-8-sig", newline="") as f:
        labels = list(csv.DictReader(f))
    selected = []
    for row in labels:
        weights = ast.literal_eval(row["weighted_skin_condition_label"] or "{}")
        if not weights:
            continue
        label = max(weights, key=weights.get)
        if label not in CLASSES or float(weights[label]) < .7:
            continue
        case = cases[row["case_id"]]
        # Avoid downloading intimate-area images for this first camera research workflow.
        if any(case.get(k, "").lower() in {"true", "yes", "1"} for k in ("body_parts_genitalia_or_groin", "body_parts_buttocks")):
            continue
        path = case["image_1_path"]
        if not path.startswith("dataset/images/") or ".." in path:
            continue
        selected.append({"case_id": row["case_id"], "label": label,
                         "label_weight": float(weights[label]), "source": BASE + path})
    return selected


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", type=Path, default=ROOT / "datasets" / "scin")
    parser.add_argument("--per-class", type=int, default=24)
    args = parser.parse_args()
    if not 12 <= args.per_class <= 1000:
        parser.error("Choose 12–1000 cases per class")
    rng = random.Random(42)
    eligible = eligible_cases(args.directory)
    cohort = []
    for label in CLASSES:
        rows = sorted([r for r in eligible if r["label"] == label], key=lambda r: r["case_id"])
        rng.shuffle(rows)
        cohort.extend(rows[:args.per_class])
    print("Eligible cases:", dict(Counter(r["label"] for r in eligible)), flush=True)

    def acquire(row):
        name = hashlib.sha256((row["case_id"] + row["source"]).encode()).hexdigest()[:24] + ".jpg"
        path = args.directory / "images" / name
        try:
            fetch(row["source"], path)
            raw = path.read_bytes()
            with Image.open(io.BytesIO(raw)) as image:
                image.verify()
            return {**row, "path": "images/" + name, "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
        except Exception as error:
            print("Download skipped:", type(error).__name__, flush=True)
            return None

    with ThreadPoolExecutor(max_workers=4) as pool:
        acquired = [r for r in pool.map(acquire, cohort) if r]
    seen = set()
    records = []
    for label in CLASSES:
        rows = []
        for row in [r for r in acquired if r["label"] == label]:
            if row["sha256"] in seen:
                continue
            seen.add(row["sha256"])
            rows.append(row)
        if len(rows) < 12:
            raise RuntimeError(f"Not enough acquired cases for {label}; rerun to resume")
        n = len(rows)
        train_end = int(n * .7)
        val_end = int(n * .85)
        for i, row in enumerate(rows):
            row["split"] = "train" if i < train_end else "val" if i < val_end else "test"
            records.append(row)
    manifest = {"dataset": "SCIN", "classes": CLASSES, "seed": 42, "clinical_ready": False,
                "split_unit": "case_id", "deduplicated_by": "sha256", "label_min_weight": .7,
                "limitations": ["research pilot sample", "US cohort", "case-disjoint is not proven patient-disjoint", "three labels cannot represent all skin conditions", "no clinical release"], "records": records}
    (args.directory / "research_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print("Acquired pilot images:", len(records), "splits:", dict(Counter(r["split"] for r in records)), flush=True)


if __name__ == "__main__":
    main()
