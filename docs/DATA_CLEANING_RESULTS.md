# Data cleaning — 4 October 2026

Run from `ai-server`: `.venv/Scripts/python.exe -m training.clean_medical_intake`.

Raw files remain unchanged. `cleaned/manifest.json` references retained representatives and records exclusions/reasons. Private manifests retain original Hb values for review and remain outside Git. Values and conflicting masks were never guessed, averaged or relabeled.

| Source | Input photos | Retained unique | Quarantined assets | Redundant consistent copies |
| --- | ---: | ---: | ---: | ---: |
| CP-AnemiC | 710 | 348 | 361 | 1 |
| CO2Wounds canonical | 764 | 704 | 59 | 1 |

Anemia retains 146 source-labeled Anemic and 202 Non-anemic images. Whole exact-pixel groups with conflicting Hb/labels are excluded. Near-match endpoints and their exact copies are quarantined for review, not declared definitively identical. No patient split is created: IMAGE_ID does not establish patient identity.

Wounds retain provider assignments: 439 train / 109 validation / 156 test. Cross-split exact-pixel groups and conflicting-mask groups are excluded. Remaining exact-pixel split overlap is **zero**. Near-match flags are computed only on canonical photos, excluding masks/split-copy assets from similarity search. Provider test photos have no segmentation masks.

Images are rehashed against the audit index; changed images fail closed. Mask dimensions, binary values, nonempty masks and split-copy pixels are checked. Selection is deterministic and preserves provider partitions; no fresh random test cohort is silently created.

Known conflicts and exact leakage are removed from these clean views. Unknown source labels, missing patient identity and source-license clearance remain unresolved, so training/clinical/commercial readiness stays false.

Verification: 29 AI tests pass, including whole-group quarantine, deterministic deduplication, near-candidate exclusion, masks, patient/pixel leakage and clinical abstention. Ruff passes. [Aggregate results](DATA_CLEANING_RESULTS.json), [Kaggle guide](KAGGLE_DATASET_GUIDE.md).
