# Training progress — 2026-10-08

## Skin fine-tuning experiment

`ai-server/training/finetune_skin_research.py` starts from the existing audited MobileNetV3Small frozen-feature checkpoint and fine-tunes its last feature block and classifier for 30 epochs. The immutable output directory is `ai-server/models/research/skindisnet-finetuned-v1/`.

- Training: 1,143 images; validation: 263; internal test: 227.
- Validate patient-group, file-hash and decoded-pixel separation before training.
- Recheck training/validation file hashes and the initial checkpoint/manifest hashes.
- Freeze the prefix and pretrained batch-normalization statistics; cache prefix maps for CPU training.
- Use class-weighted loss, separate learning rates for the last block/head and feature-map horizontal flips.
- Select the checkpoint using validation balanced accuracy; do not read test image pixels during this run.
- Record confusion matrix and per-class precision, recall and F1. Validation is used for selection and is not an independent performance estimate.

Patient grouping supplied by the dataset has not been independently clinically verified. SkinDisNet original images are noncommercial. This experiment remains research-only regardless of its score. Healthy skin and unknown conditions are not covered. No claim of 90–100% accuracy or clinical reliability is warranted.

Completed result: 30 epochs, best checkpoint at epoch 29. Validation balanced accuracy improved from 37.3812% to 38.9563% (+1.5751 percentage points). This small change has not been established as statistically significant and is not a held-out test result. Four existing split-integrity tests passed. Full per-class results and checkpoint integrity verification are recorded in `SKIN_FINETUNING_RESULTS.json`.

The engineer-only prediction tool supports this checkpoint architecture and continues to return no clinical diagnosis. Public patient inference remains disabled.

## Other modules and remaining gates

| Module | Current prerequisite before reliable training/evaluation |
| --- | --- |
| Anemia | 348 retained CP-AnemiC images; resolve patient identities, original image permissions and clinician-confirmed Hb/label mapping. No fabricated Hb corrections or random patient-independent split claims. |
| Wound | 704 retained CO2Wounds photos; 439 provider train / 109 validation / 156 test. Patient identity unverified; provider test masks unavailable. Resolve source permissions and create a clinician-annotated, patient-disjoint test set. Rollas remains a separately reviewed candidate, not yet fully acquired. |
| External eye | Separate reviewed conjunctivitis candidates; unresolved cross-source near duplicates, modality/diagnosis annotations and patient grouping. |
| Retina | Fundus upload workflow exists; full retinal dataset acquisition and appropriate patient-grouped training/evaluation remain pending. |
| Tongue | Supplied NuInsSeg/PACO links do not provide surface-tongue disease photographs and labels. Acquire a suitable source. |
| Posture | Define pose measurement ground truth and repeatability testing; do not infer scoliosis diagnosis from an ordinary phone photo alone. |

More images help only when their labels, modality, provenance and independent patient coverage are appropriate. Augmented or duplicate images do not increase the number of independent patients. Checkpoints are not deployed merely because training finishes.

## Wound architecture improvement — 10 October 2026

The same hash-checked retained CO2Wounds provider training/validation splits now have a completed U-Net experiment: 60 epochs, best epoch 58, validation Dice **0.6663054** and IoU **0.5444564**. Previous CNN Dice was **0.4520797** (increase **0.2142257**, not classification-accuracy percentage points). Both use 96×96 images/masks; the comparison reuses validation and is optimistic. Provider test masks and verified patient grouping remain missing. Wound size in centimetres and healing-stage prediction are unsupported.

The selected immutable checkpoint has a matching SHA-256 and passes load/forward shape and finiteness checks. Fifteen targeted tests and changed-file Ruff checks pass. [Result](WOUND_UNET_RESULTS.json), [aggregate research report](MEDICAL_TRAINING_RESULTS.json), [validation curve](WOUND_TRAINING_CURVE.png).

The >97% checker now includes approximate simultaneous Wilson confidence bounds for each class recall/specificity; a tiny perfect internal sample cannot pass. All current models fail the complete external-evidence target. Retina acquisition/training and original FUSeg acquisition remain in progress, not completed results. Tongue/posture original sources and truthful, unsubmitted access drafts are recorded in [the expansion strategy](DATASET_EXPANSION_STRATEGY.md).
