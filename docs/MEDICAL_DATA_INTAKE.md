# Medical research intake — 4 October 2026

All three acquisitions below are pinned public Kaggle version 1 mirrors. Archives were downloaded with resumable chunks, hashed, safely extracted and decoded. Raw files, source metadata and image indexes remain outside Git under `ai-server/datasets/kaggle/`. Acquisition does not authorize training or clinical/commercial use. No patient-level records are reproduced in this document.

| Intake | Downloaded assets | Verified findings | Current gate |
| --- | --- | --- | --- |
| CP-AnemiC | 710 images and one metadata workbook | 485 unique decoded images; 710 rows match image IDs; 86 identical-pixel groups carry differing Hb values; one exact duplicate group crosses anemia labels | Resolve provenance/annotation conflicts and verify patient identity; pediatric Ghana scope does not validate Pakistan adults |
| Ghana fingernails | 4,260 images in one folder | 2,087 unique decoded images, 1,400 duplicate groups, 148 near-match candidates; no annotation workbook/CSV or verified patient mapping in acquired mirror | Recover original/augmentation lineage and clinical labels before any split or training |
| CO2Wounds | 2,742 image assets plus COCO annotation JSON | 764 canonical photos, 737 unique photo pixels, 607 binary masks, 971 annotated regions; split copies and masks explain the larger asset total | Resolve license disagreement, verify patient grouping and eliminate split leakage; no calibrated size/healing labels |

CP-AnemiC folder labels contain 424 Anemic and 286 Non-anemic assets. Unique pixel counts per folder are 242 and 243; one pixel group appears under both labels, so summing these folder counts exceeds the global unique count. Metadata IMAGE_ID is an image identifier, not verified patient identity. Hb values are reviewed for presence/finite positivity only; this audit assigns no diagnosis or medical thresholds.

CO2Wounds provider splits contain 485 training, 122 validation and 157 test photos. **Eight pixel groups cross those provider splits.** All 607 masks match their canonical photo dimensions, contain binary 0/1 values and are nonempty. All split copies match canonical photo pixels; no orphan annotation region or missing mask was found. These structural checks do not verify clinical segmentation quality. Patient identity remains unverified, and a mask cannot establish centimeters without calibration.

## Sources and retained permissions

- CP-AnemiC mirror: `karankumar4090/cp-anemic-dataset-same`. [Original v1](https://data.mendeley.com/datasets/m53vz6b7fx/1), [latest original v2](https://data.mendeley.com/datasets/m53vz6b7fx/2). Original terms include academic-use/commercial restrictions; the mirror's Apache declaration does not override them.
- Ghana fingernails mirror: `kritagyadev/anemia-using-fingernails-image-datasets-from-ghana`. [Original source](https://data.mendeley.com/datasets/2xx4j3kjg2/1) declares CC BY 4.0 and describes 710 originals plus augmentation. Mirror license is Unknown; original-source identity, attribution and augmentation lineage still need review.
- CO2Wounds mirror: `orvile/leprosy-chronic-wound-images-co2wounds-v2`. [Original repository](https://data.mendeley.com/datasets/s2w7rjwz49/2) declares CC BY-NC 3.0; [project repository](https://github.com/simatec-uis/CO2Wounds-V2) states CC BY-NC-ND. The disagreement is retained rather than selecting a convenient license.

| Archive | Bytes | SHA-256 |
| --- | ---: | --- |
| CP-AnemiC | 8,304,739 | `56ee5c40b549d528107043ba37ce183a75f40e4e9bd40fe466653fd3cb37eb78` |
| Ghana fingernails | 27,740,417 | `807ef1dde6dc8142c808c816a43489650c3e18f456876797c0aeaba1d0bc2f19` |
| CO2Wounds | 115,190,951 | `c64a2c198203e173d69213c1de13a857090578b69740f02246117ff56e441ccd` |

Aggregate machine-readable results are preserved in [MEDICAL_DATA_INTAKE_RESULTS.json](MEDICAL_DATA_INTAKE_RESULTS.json). No new anemia or wound model has been trained from these intakes. No commercial or clinical checkpoint is enabled.
