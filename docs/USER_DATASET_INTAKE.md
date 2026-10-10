# User-provided Kaggle archives — 4 October 2026

Both Downloads ZIPs were read, copied into ignored local research intake directories, safely extracted and fully decoded. Archive scripts were not executed. The one `.ashx` entry in the skin ZIP was skipped. Original Downloads files remain unchanged. Exact Kaggle URLs, original-source licenses and independent patient metadata were absent from both ZIPs and remain pending.

| Archive | Image assets | Unique decoded pixels | New relevant research candidates |
| --- | ---: | ---: | ---: |
| archive.zip — nails | 4,260 | 2,087 | 0: all images already appear in the acquired Ghana fingernail collection |
| archive (1).zip — skin | 6,304 | 5,815 | 2,351 after scope/duplicate/review exclusions |

The nail ZIP hash differs from the previously acquired ZIP but its entire decoded image inventory is already present. Packaging hashes alone do not identify independent medical data. It contains no Hb/class workbook or patient mapping and adds no new labeled anemia cohort.

Skin candidates preserve source **folder labels**, not verified diagnoses:

- Acne: 1,724
- Eczema Photos: 305
- Tinea Ringworm Candidiasis and other Fungal Infections: 322

The mixed fungal folder must not be relabeled as pure Tinea Corporis. Skin-type labels such as oily/dry and the normal folder do not establish clinical healthy controls. Other disease folders are preserved in raw intake, outside this common-skin candidate scope.

The skin inventory has 488 exact duplicate groups and 78 within-source near-match candidates, including six near-match pairs with differing folder labels. No image was rejected for decoding. Against the existing audited Ghana nails, CP-AnemiC, SkinDisNet and SCIN sources, exact overlap is zero and one cross-source near-match pair was flagged. Near-match flags require visual/source review, not automatic identity claims. Exact groups with differing folder labels are excluded in full; no arbitrary label is selected.

The skin candidate view contains 2,351 unique images, 3,863 quarantined/out-of-scope assets and 90 redundant consistent copies; these sum to all 6,304 images. Quarantine includes scope exclusions, not only defective data. No random image-level patient split was created. Source rights, label review and patient grouping must precede training; clinical and commercial inference remain disabled.

Local paths:

- `ai-server/datasets/user_uploads/user_fingernails_20261004/`
- `ai-server/datasets/user_uploads/user_skin_20261004/`

Each retains `source.zip`, `raw/`, image/duplicate audit files, acquisition hashes, cross-source near flags and `research_candidate_manifest.json`. Raw images/manifests are excluded from Git. [Aggregate results](USER_DATASET_INTAKE_RESULTS.json).

Validation: all manifest rows are accounted for; retained candidates have unique pixel hashes. Thirty AI tests pass, including a new rule that conflicting folder labels cannot be resolved by filename sort order. Ruff checks pass.
