# Wound and tongue links reviewed — 2026-10-04

This is an intake review, not a trained or clinically validated model. Metadata, source descriptions and the Rollas remote ZIP inventory were inspected. Full archives have not been acquired by this review.

| Dataset | Pinned version | Finding | Decision |
| --- | --- | --- | --- |
| rollas/wound-segmentation-dataset | 1 | 2,208 train photos + 552 test photos, with the same number of masks; 5,520 PNG assets plus class_info.txt. Archive 700,304,300 bytes. | Register as a quarantined wound segmentation candidate. |
| katjalwenstein/woundhealing | 6 | Microscopic in-vitro scratch-assay images and segmentation annotations. | Exclude from phone-camera clinical wound training. |
| lesves/annotated-wound-healing-assay-segmentations | 1 | 446 microscope cell-migration assay images; mirror license Unknown. | Exclude from phone-camera clinical wound training. |
| ipateam/nuinsseg | 5 | 665 H&E histology patches with nuclear instance masks; includes multiple human/mouse organs. | Exclude from surface-tongue disease training. |
| swaptr/pacolvis-dataset | 1 | Parts and attributes of common objects, based on LVIS/COCO and Ego4D. | Exclude from tongue disease training. |

## Rollas next gates

One paired sample (`fusc_0002.png`) was downloaded and visually inspected: both image and mask are 512×512. The mask contains exactly RGB black (0,0,0), blue (0,0,255), and red (255,0,0). The downloaded class definitions identify these as background, human skin and wound/burn respectively. Although the text mentions `*_labels/` training maps, the actual archive inventory has only image/mask folders; generate integer maps from verified RGB colours rather than assuming those label files exist. This single sample is not a full annotation-quality audit.

Inventory counts do not establish independent patients, correct labels or absence of leakage. The mirror advertises three-class masks; verify actual pixel values and class definitions across every mask before choosing the training decoder. Existing binary CO2Wounds mask handling cannot be assumed compatible.

Before training: acquire and hash the archive; verify image-mask pairing, dimensions, allowed classes and nonempty wound regions; audit decoded-pixel duplicates and near duplicates across train/test and existing CO2Wounds; obtain patient/visit grouping or document its absence. Do not reuse the provider split as a validated patient-independent test set without this audit.

The mirror declares MIT, but cites a derived Kaggle source, Medetec and wound research. Medetec calls its collection free stock images; the reviewed landing page does not establish a complete commercial ML redistribution license. Original permissions remain unresolved. No scale reference, calibrated centimetre labels or longitudinal healing-stage ground truth was established. Segmentation alone cannot supply those outputs.

## Tongue data still needed

Look for external tongue photographs with tongue-region masks, and separately clinician-confirmed lesion/infection labels with patient grouping. Search terms: `tongue segmentation masks`, `clinical tongue lesion dataset`, `oral lesion tongue photographs`. Tongue colour alone does not establish a deficiency diagnosis. NuInsSeg's tongue tissue patches are microscope images, not the same input modality.

## Sources and evidence

- [Rollas Kaggle dataset](https://www.kaggle.com/datasets/rollas/wound-segmentation-dataset)
- [Medetec original image collection](https://www.medetec.co.uk/files/medetec-image-databases.html)
- [Wound scratch-assay paper](https://arxiv.org/abs/2407.02187)
- [Annotated wound-healing assays](https://www.kaggle.com/datasets/lesves/annotated-wound-healing-assay-segmentations)
- [NuInsSeg original paper](https://arxiv.org/abs/2308.01760)
- [PACO author repository](https://github.com/facebookresearch/paco)

Ignored local evidence: `ai-server/datasets/catalog/wound_tongue_links/`, including pinned Kaggle metadata and `wound_rollas_inventory.json`. Training, clinical readiness and commercial release remain disabled.
