# Dataset acquisition and model readiness

Updated 4 October 2026. **Skin intake now contains 1,710 Kaggle SkinDisNet mirror images and 154 SCIN images (including the historical 51-image pilot).** After quarantining near-match candidates, 1,633 SkinDisNet images have a metadata-based patient-group research split. See [acquisition and audit results](SKIN_DATA_ACQUISITION.md) for source licenses, counts and reproducible commands. A 20-epoch six-class CNN has completed training and testing on this split: held-out balanced accuracy **35.5%**, ordinary accuracy **30.8%**; no validated clinical checkpoint is available. [Full new results](SKINDISNET_RESEARCH_RESULTS.json). The generic `yolov8n.pt` file is not an eye/nail/disease model.

| Workflow | Candidate or missing evidence | Current decision |
| --- | --- | --- |
| Anemia | CP-AnemiC and Ghana fingernail mirrors acquired and audited | 710 CP images and 4,260 fingernail assets; duplicates, conflicting Hb and missing patient/augmentation mapping keep both quarantined. See [intake report](MEDICAL_DATA_INTAKE.md). |
| Common skin conditions | [Google SCIN repository and data-use license](https://github.com/google-research-datasets/scin) | Candidate phone-photo research data. Review diagnostic uncertainty and label coverage for eczema/fungal/acne. Do not attempt re-identification. External Pakistan validation remains required. |
| Skin lesions | [HAM10000 original paper](https://www.nature.com/articles/sdata2018161) | Dermoscopy of seven pigmented lesion categories; unsuitable as the only data for the requested common-rash phone-camera classifier. |
| Posture | No approved physiotherapy-labeled cohort | Yoga pose images do not establish scoliosis diagnosis or clinical spinal angles. |
| Cataract / red eye / jaundice | Two conjunctivitis mirrors acquired/audited; sclera inventory and four samples reviewed | Candidate views remain unverified; four shared exact groups and 71 cross-source near pairs require review. Retinal datasets are excluded from phone external-eye training. See [eye review](EYE_DATASET_REVIEW.md). |
| Wounds | CO2Wounds acquired: 764 canonical photos and 607 masks | Eight pixel groups cross provider splits; patient mapping and conflicting noncommercial licenses need review. Masks provide neither centimeter scale nor longitudinal healing labels. |
| Tongue | No approved clinically labeled cohort | Color/coating photos alone do not establish deficiency or infection diagnosis. |

The existing `training/dataset_setup.py` contains **legacy, unverified Kaggle IDs and research preparation code**. They are not evidence of acquired data, correct labels or suitable licenses. Its image-level anemia split is not the patient-level split required for clinical research. Default downloads are now gated to prevent treating these placeholders as a ready clinical pipeline. `--skip-download` reports local presence; `--allow-unreviewed` is only an explicit research exploration override, not approval for training or deployment.

For each approved acquisition, record the exact source/version, license text, attribution, intended permitted use, patient/site identifier, label definition, image SHA-256 and acquisition date. Keep raw medical images outside Git. Deduplicate before patient/site splits; keep an untouched external test cohort. Downloads from private Kaggle collections require the user's own configured access credentials. Do not paste keys into chat.

Clinical models remain disabled until preprocessing, trained checkpoint loading, patient-disjoint evaluation, calibration, subgroup performance, quality rejection and clinician review are documented. Training completion or a high validation score alone does not enable predictions.

## Acquired SCIN pilot — 2 October 2026

Official metadata contains 5,033 cases and 5,033 label rows. The downloaded license and schema are retained in `ai-server/datasets/scin/`. The image pilot contains 15 Acne, 24 Eczema and 12 Tinea cases whose dominant label weight is at least 0.7; intimate-area cases were excluded. SHA-256 duplicate checking precedes case-disjoint train/validation/test splits of 34/8/9. Case identity does not prove patient-disjointness. The metadata acquisition manifest describes the metadata phase; `research_manifest.json` describes the actual acquired image cohort.

A seeded 20-epoch CPU CNN baseline is saved under `ai-server/models/research/skin-cnn-v1/`. Best validation balanced accuracy was 58.3%; untouched pilot test balanced accuracy was **36.1%**, with Tinea recall **0/2**. These nine test images establish neither efficacy nor calibration. The checkpoint is **research-only and disabled for live patient inference**. Do not tune against this test split; use a larger cohort and a new untouched external test for future development.

Commands from repository root:

```powershell
ai-server/.venv/Scripts/python.exe ai-server/training/fetch_scin.py
ai-server/.venv/Scripts/python.exe ai-server/training/prepare_scin_research.py --per-class 24
ai-server/.venv/Scripts/python.exe ai-server/training/train_skin_research.py --epochs 20
```

Source attribution: Google Research SCIN and original contributors, https://github.com/google-research-datasets/scin. Retain the SCIN Data Use License; do not attempt re-identification. This US volunteer pilot does not validate Pakistan use. Anemia and the other four workflows still need task-appropriate licensed data and clinical labels.
