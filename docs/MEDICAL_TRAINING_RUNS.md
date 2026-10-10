# Medical research training — 8 October 2026

`training/train_medical_pilots.py` implements actual checkpoint training for cleaned conjunctival anemia labels, one independently retained conjunctivitis mirror, binary wound segmentation and an acquired/audited retinal mirror. These experiments are separate from the protected capture API, which continues to abstain from diagnosis.

## Classification pilots

The anemia and conjunctivitis experiments use audited unique images with prior near-duplicate candidates quarantined. Frozen ImageNet MobileNetV3Small features feed a class-weighted classifier trained for 50 epochs. A seeded 70/15/15 stratified **image-level** split is created. Patient IDs are missing; this is explicitly not a patient-independent split. Source hashes are checked before feature extraction. The best checkpoint is selected on validation balanced accuracy, then the internal test is evaluated once. Model cards include per-class recall/precision/F1, confusion matrices and binary ROC AUC. ROC AUC refers to class index 1 in the stored class order, which may be the non-anemic class; it is not automatically anemia sensitivity.

Neither folder labels nor high internal accuracy establish clinical validity. Conjunctivitis testing excludes alternative red-eye diagnoses, and the small single-source test may contain source/capture cues. The two eye mirrors are not pooled. Anemia conjunctival training does not train fingernail detection or certify Hb estimation. No confidence calibration or external Pakistani cohort validation has been completed.

## Wound segmentation

The wound pilot uses only the retained provider train/validation images with actual binary masks. Image/mask hashes, equal dimensions and binary values are checked; masks are resized with nearest-neighbour interpolation. A small fully convolutional model is trained at 96×96 for 50 epochs using BCE + soft Dice loss. The checkpoint is selected on mean per-image validation Dice with a fixed 0.5 threshold; IoU is recorded separately. Dice is overlap, not disease-classification accuracy.

Provider test masks are unavailable and patient identities are unverified. No held-out test Dice, healing-stage classifier or centimetre measurement is claimed. The low-resolution model is a research baseline. CO2Wounds original license restrictions still exclude commercial release without clearance.

## Retina pipeline

Command: `python training/train_medical_pilots.py --module retina --epochs 50`.

This resumes bounded download chunks, verifies the ZIP, extracts safely, audits images, quarantines exact conflicts and near duplicates, then trains a separate fundus classifier. It requires successful intake and nonempty valid classes. A partial download is not a trained model. The pinned aggregated source's original labels, permissions and patient grouping remain unresolved. Fundus output is never applied to external-eye phone photographs.

For slow range connections, append `--serial-intake`. The continuous stream is seeded only with hash-verified contiguous chunks after checking remote ETag and byte-count identity. Completed chunks remain available. Failed range jobs cancel queued requests, record incomplete status and can resume; active chunk bodies have a 90-second budget. ZIP integrity is checked before extraction. Two serial-resume tests and a queue-cancellation regression test pass, along with five existing network/range tests.

Current completed runs: anemia test balanced accuracy 59.16% (53 images), conjunctivitis 97.92% (46 images), wound validation Dice 0.4521 / IoU 0.3460. Skin fine-tuning is documented separately with validation balanced accuracy 38.96%. Saved checkpoint forward checks pass. These values evaluate different tasks/splits and should not be averaged or compared as a common disease-detection accuracy. Retinal results are added to the aggregate report only after its full intake and training complete.

## Remaining unavailable training targets

Tongue disease training still needs suitable external tongue images and verified disease labels; supplied NuInsSeg/PACO data does not meet that task. Posture requires real pose measurements and clinician/physiotherapist ground truth. Existing synthetic pose data and colour-to-disease tongue aliases are not clinical ground truth and are not used by this pipeline.

Artifacts: `ai-server/models/research/*-pilot-v1/`. Aggregate results: [MEDICAL_TRAINING_RESULTS.json](MEDICAL_TRAINING_RESULTS.json). Model readiness API reports research artifact integrity and keeps clinical/commercial approval false. All source images and per-image manifests remain outside the aggregate report.
