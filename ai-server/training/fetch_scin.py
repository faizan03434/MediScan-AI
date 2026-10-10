"""Bounded, resumable SCIN research acquisition with provenance; never enables inference."""
import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://storage.googleapis.com/dx-scin-public-data/"
SOURCES = {
    "scin_cases.csv": BASE + "dataset/scin_cases.csv",
    "scin_labels.csv": BASE + "dataset/scin_labels.csv",
    "LICENSE": "https://raw.githubusercontent.com/google-research-datasets/scin/main/LICENSE",
    "dataset_schema.md": "https://raw.githubusercontent.com/google-research-datasets/scin/main/dataset_schema.md",
}


def fetch(url, path, limit=20 * 1024 * 1024):
    if path.exists():
        return
    with urlopen(url, timeout=45) as response:
        raw = response.read(limit + 1)
    if len(raw) > limit:
        raise ValueError("Download exceeds size budget")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".part")
    temporary.write_bytes(raw)
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "datasets" / "scin")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    records = []
    for filename, url in SOURCES.items():
        path = args.output / filename
        fetch(url, path)
        records.append({"file": filename, "source": url, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "bytes": path.stat().st_size})
    counts = {}
    for filename in ("scin_cases.csv", "scin_labels.csv"):
        with (args.output / filename).open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
        counts[filename] = len(rows)
        print(filename, "rows:", len(rows), "fields:", list(rows[0]) if rows else [])
    (args.output / "acquisition.json").write_text(json.dumps({
        "dataset": "SCIN", "acquired_at": datetime.now(timezone.utc).isoformat(),
        "license": "SCIN Data Use License", "attribution": "Google Research SCIN dataset and original contributors; https://github.com/google-research-datasets/scin",
        "files": records, "metadata_rows": counts, "images_downloaded": 0,
        "clinical_ready": False, "limitations": ["US volunteer cohort", "diagnostic uncertainty", "no independent Pakistan validation", "case IDs do not prove patient identity"]
    }, indent=2), encoding="utf-8")
    print("Metadata acquired; images and clinical validation are separate steps.")


if __name__ == "__main__":
    main()
