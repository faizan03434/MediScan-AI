# Skin data acquisition and audit

Started 3 October 2026. This stage collects and audits data; it does not enable patient diagnosis or claim 90–100% performance.

## Completed intake — 3 October 2026

The pinned Kaggle mirror has been downloaded and decoded: **1,710 images**, six original folder classes and metadata for **416 patient IDs**. No corrupt images, exact file duplicates or identical decoded images were found within this source. Archive SHA-256: `dc0c7c77966d6ea4a2984a5019f8d54a2830052a42a7b34b54ea02f4ff84e9a3`.

The audit flagged **42 near-duplicate candidate pairs**, including two pairs with different labels. All **77 candidate endpoints** are excluded from research splitting while the raw files remain available for review. The remaining **1,633 images / 412 groups** are split into **1,143 training, 263 validation and 227 test images**, stratified by patient-group label signature. Every class appears in every split. File hashes and exact metadata coverage were checked. Patient ID semantics still require confirmation against original documentation.

SCIN expansion is complete: **154 images** (15 Acne, 127 Eczema, 12 Tinea), with no corrupt or exact/near duplicate images found within this intake. This total includes the original 51-image pilot; it is not 154 additional images. The old pilot manifest remains unchanged. SCIN expansion remains quarantined because case IDs do not establish independent patient identities. The sources retain separate label schemes. On 4 October, cross-source RGB hash and pHash comparison found **1,864 distinct decoded images, zero cross-source exact groups and zero cross-source near-match candidates**. This is not a per-disease count or evidence of patient independence.

A six-class research CNN has now completed 20 epochs on 4 October: validation balanced accuracy 31.4%, final held-out test balanced accuracy 35.5% and ordinary test accuracy 30.8%. Eczema and Atopic Dermatitis recall are both zero. See [recorded model card](SKINDISNET_RESEARCH_RESULTS.json). This source-cohort test is now examined and must not be used for subsequent parameter selection. The original SkinDisNet noncommercial license remains applicable; commercial product use is not cleared by the mirror's different license declaration. Clinical inference remains disabled.

## Reviewed sources

| Source | Verified publisher information | Current handling |
| --- | --- | --- |
| [Kaggle Dermnet](https://www.kaggle.com/datasets/shubhamgoel27/dermnet) | Public API: version 1, about 1.85 GB uncompressed, CC BY-NC-ND 4.0. Uploader reports about 19,500 images, not 100,000 per disease. | Not acquired. Original image rights and AI training permission need review. Combined acne/rosacea and fungal categories do not provide exact acne or Tinea labels. |
| [Kaggle skin-diseases-image-dataset](https://www.kaggle.com/datasets/ismailpromus/skin-diseases-image-dataset) | Public API: about 5.58 GB, “Data files © Original Authors”. | Not acquired: this statement does not establish permission for our intended training/product use. |
| [Original SkinDisNet v2](https://data.mendeley.com/datasets/yj3md44hxg/2) | Publisher reports 1,710 original images, 416 patients, six conditions, smartphone photos and patient metadata; 11,970 augmented images; CC BY-NC 4.0. | Appropriate research candidate for dermatitis/eczema/Tinea, not an acne dataset. Original page/file API returned 403 on this network. No restriction bypass attempted. |
| [Kaggle SkinDisNet_3 mirror](https://www.kaggle.com/datasets/samurarahman14/skindisnet-3) | Mirror version 1, compressed archive 222,809,189 bytes; mirror declares Apache 2.0. | Pinned acquisition in quarantine. The mirror declaration does not override the original CC BY-NC license. Original identity and metadata must be checked; no commercial release permission is assumed. |
| [Official SCIN](https://github.com/google-research-datasets/scin) | Existing downloaded metadata/license; strict dominant-label weight ≥0.7 gives 15 Acne, 127 Eczema and 12 Tinea eligible cases after the existing body-area exclusions. | Expand intake without changing the previously evaluated 51-image pilot manifest. New intake is quarantined until audit/split review. Case IDs are not verified patient IDs. |

The [DermNet NZ image license](https://dermnetnz.org/image-licence) separately prohibits AI training/testing of its freely available website images. The Kaggle Dermnet uploader references `dermnet.com`; do not automatically equate these publishers or assume one license clears all mirrors. Original provenance must be established.

## Reproducible acquisition

From repository root:

```powershell
# Public Kaggle download with resumable, checked range chunks; then automatic image audit
ai-server/.venv/Scripts/python.exe ai-server/training/acquire_skin_kaggle.py --parallel

# Acquire missing SCIN cases; retain the existing pilot split unchanged
ai-server/.venv/Scripts/python.exe ai-server/training/expand_scin_intake.py

# Audit the actual acquired SCIN images with their manifest labels
ai-server/.venv/Scripts/python.exe ai-server/training/skin_data_audit.py --directory ai-server/datasets/scin/images --output ai-server/datasets/scin/expansion_audit --manifest ai-server/datasets/scin/expansion_intake.json

# Verify mirror metadata, quarantine near-match candidates and create the research split
ai-server/.venv/Scripts/python.exe ai-server/training/prepare_skindisnet_research.py

# Compare source indexes without merging their label definitions
ai-server/.venv/Scripts/python.exe ai-server/training/audit_skin_overlap.py
```

Local data resides in ignored `ai-server/datasets/`. The Kaggle acquisition pins version 1, limits archive size, confirms range offsets/ETag, hashes each completed chunk, checks ZIP CRC, rejects unsafe paths/symlinks and limits extraction. Completed chunks survive interruptions. `download_progress.json` records transfer status; completed downloads create `acquisition.json` and `audit/audit.json`.

## Count and split rules

The audit records decoded images, SHA-256 unique files, unique RGB pixel images, class counts, corrupt images, augmented exclusions, exact duplicate groups and pHash near-duplicate candidates. Near matches are review candidates, not proof of identity and not automatically removed. Folder labels are retained verbatim; we do not silently map mixed categories to one diagnosis.

The patient splitter requires a metadata CSV and explicitly named image/patient columns. It rejects incomplete or ambiguous mappings and conflicting labels on duplicates. Patient IDs are namespaced and hashed. Connected patient/exact-duplicate groups stay in one split; roughly 70/15/15 of groups are assigned, and every class must appear in every split. Patient ID semantics, near-duplicate review and site overlap still require verification. A successful CSV mapping alone is not clinical validation.

```powershell
ai-server/.venv/Scripts/python.exe ai-server/training/build_patient_skin_split.py --index PATH_TO_IMAGE_INDEX --metadata PATH_TO_ORIGINAL_METADATA --image-column ACTUAL_IMAGE_COLUMN --patient-column ACTUAL_PATIENT_COLUMN --namespace SkinDisNet_original_v2 --image-root PATH_TO_RAW_IMAGES --output PATH_TO_NEW_MANIFEST
```

The existing examined pilot test is not a fresh external test. Augmentation belongs after splitting and only in training. More pictures, mirror copies and augmentation do not automatically create more independent patients. A Pakistan cohort, healthy/other-condition controls, calibration and clinician review remain required for clinical use. Research-only licenses need separate permission before commercial use.
