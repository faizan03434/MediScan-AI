# Eye dataset review — 4 October 2026

The six user links cover different acquisition modalities. Phone external-eye photos cannot be substituted with fundus photographs. This review does not validate diagnoses or enable live inference.

| Source | Version / mirror license | Decision |
| --- | --- | --- |
| [Eye diseases classification](https://www.kaggle.com/datasets/gunavenkatdoddi/eye-diseases-classification) | v1 / database license with original-author contents | Publisher explicitly describes retinal images collected from IDRiD, ODIR, HRF and other sources. Not acquired for the external-eye phone task |
| [Cataract dataset](https://www.kaggle.com/datasets/jr2ngb/cataractdataset) | v2 / Unknown | Inventory has 1,202 PNG assets: two matching copies of 601 retina images, plus two README files. Original [retina repository](https://github.com/yiweichen04/retina_dataset) confirms retinal scope. Not merged into the phone task |
| [ODIR5K](https://www.kaggle.com/datasets/andrewmvd/ocular-disease-recognition-odir5k) | v2 / Other; source license unspecified | Publisher describes paired color fundus photos, clinician keywords and 5,000 patients. Useful for a separate fundus task, not current phone external-eye capture. Full archive not acquired |
| [Alisofiya conjunctivitis](https://www.kaggle.com/datasets/alisofiya/conjunctivitis) | v1 / Unknown | Acquired and decoded; healthy_eye/infected_eye source folders. Research quarantine |
| [Revengerdna conjunctivitis](https://www.kaggle.com/datasets/revengerdna/conjunctivitis-dataset) | v1 / MIT mirror | Acquired for independent image/label/overlap review. Original image rights are not established by the mirror declaration |
| [Diseased sclera data](https://www.kaggle.com/datasets/navinxqz/diseased-data) | v1 / Unknown | Inventory and four image samples reviewed. External-eye/full-face modality candidates; source/lineage/clinical labels still unverified. Full archive not acquired |

## Sclera inventory and sampling

The ZIP has 5,610 JPG assets: Cataract 1,531, Jaundice 1,151, Normal_Eye 1,281, Pterygium 1,647. Filename prefixes before `.rf.` form 272 / 531 / 452 / 338 families, totaling 1,593. A filename family is not a patient ID or verified original. Multiple variants per prefix require original/augmentation lineage review before splitting; otherwise transformed images may cross partitions.

Four bounded sample files were acquired and visually inspected. They include external-eye and full-face photographs, rather than a uniform isolated-sclera capture protocol. Samples do not establish quality or correct diagnosis of the entire cohort. The archive inventory contains no clinical metadata files, bilirubin measurements or patient/site mapping. Color augmentation, lighting and editing need review for a jaundice task; no bilirubin value or diagnosis is inferred from these samples.

The cataract archive's dataset and repository-copy entries match member names, sizes and CRCs for 601 images. This is ZIP-inventory duplication evidence, not a complete pixel audit. Bounded cataract sampling encountered a network wall-time limit; its retinal scope is established from the original repository, not a successful sample image inspection.

## Conjunctivitis use gates

| Mirror | Decoded assets | Unique pixels before exclusions | Retained candidates | Source-folder candidate counts |
| --- | ---: | ---: | ---: | --- |
| Alisofiya | 358 | 342 | 303 | healthy_eye 146, infected_eye 157 |
| Revengerdna | 1,357 | 767 | 601 | Normal 343, Effected 258 |

Both archives decode without rejected images. Before cleaning, Alisofiya has 14 exact duplicate groups and 24 near-match pairs (one cross-folder pair); Revengerdna has 463 duplicate groups and 127 near-match pairs (two cross-folder pairs). Across both raw mirrors there are 1,715 assets but only **1,105 unique pixel images**, including four shared exact-pixel groups and 71 cross-source near-match candidate pairs. Do not sum candidate counts as independent patients. Per-source candidate views are for review only; cross-source flags remain unresolved and no pooled training split is created.

Archives are retained in ignored `ai-server/datasets/kaggle/eye_conjunctivitis_alisofiya_v1/` and `eye_conjunctivitis_revengerdna_v1/`. SHA-256 receipts:

- Alisofiya, 34,077,785 bytes: `57426b94c903ba56ea8b076c7f61e6380345b9064e89cbe74fe8f0666edb1aeb`
- Revengerdna, 40,864,464 bytes: `d7dd09e54f0b3b02d8ad62e83704976827a37f3887435cf39c116d610a15b36f`

Retained manifests preserve folder labels as unverified source claims. Exact-pixel duplicates are represented once within each mirror, whole groups with differing labels are quarantined, and near-match candidates remain excluded pending review. Mirrors remain separate; cross-source matches must not create new independent patients or silently be counted twice.

`annotation_review.csv` files are prepared in the ignored local intake folders. Clinician review should fill body area, reviewed diagnosis, quality status, pseudonymous patient group, reviewer reference and date. Never infer a patient ID from filename/sequence or fill a diagnosis based only on folder names. Filling a review sheet alone does not establish release readiness: original permissions, patient/site-separated evaluation, unknown red-eye causes, capture quality rejection, calibration and external testing remain separate gates.

Reproduce completed intake review from `ai-server` with `.venv/Scripts/python.exe -m training.review_eye_intake`. The model status and live-capture workflows continue to abstain from clinical prediction. [Machine-readable results](EYE_DATASET_REVIEW_RESULTS.json).

Verification: 35 AI tests pass; bounded connection/header retry tests were added after transient Kaggle failures. Existing verified chunks were reused on retry. Full AI source Ruff checks pass. No model training or clinical accuracy result was produced by this intake.
