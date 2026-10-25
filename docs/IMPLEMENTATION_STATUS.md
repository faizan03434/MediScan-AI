# Implementation status — 10 October 2026

**Newest reassessment (26 October): [60/100 complete, 40/100 remaining](COMPLETION_AUDIT_2026_10_26.md).** This is an engineering estimate, not medical accuracy. The checkpoints below are historical; the 65 milestone and independent medical acceptance remain unfinished.

**Current checkpoint:** [account deletion/readiness](ACCOUNT_DELETION_AND_READINESS.md) — password/email-code confirmation, durable account cleanup, private status receipt, media inventory and dependency probes are implemented. 66 backend/87 AI tests and mobile checks pass; the running synthetic-account worker removed its fixture and physical photo. Estimate: 51/100 complete, 49/100 remaining. Backups, cloud/device acceptance and clinical validation remain open.

**Latest checkpoint:** [delivery ledger](DELIVERY_STRATEGY.md) — 49/100 complete and 51/100 remaining by the same engineering rubric; 54 backend tests pass. Persistent encrypted OTP, account exports, all-device logout, opt-in deleted-record purge, Docker privacy/persistence and stale Expo host recovery are implemented. Live SMTP still fails; physical-device, Google and clinical acceptance remain open.

**Latest audit: [19 October completion assessment](COMPLETION_AUDIT_2026_10_19.md)** — 45/100 complete and 55/100 remaining by a documented engineering rubric for the full production medical product. New stored-photo sanitization, capture response validation and bounded image processing are implemented; 41 backend and 86 AI tests pass. The dated details below are historical. Clinical inference remains disabled.

This is a development preview, not a validated diagnostic product. Working infrastructure and research experiments must not be presented as clinical capabilities.

Latest integration: email login, registration OTP, password-reset OTP, Google identity/linking and protected media workflows are included in source publication. Ignored server `.env` configuration is now supported; the Gmail sender is configured with an empty password awaiting the developer's app password. Shared Android/iPhone preview links and QR replace the iPhone-only wording. 33 backend and 78 AI tests pass. Mobile type/lint and platform bundle checks are tracked in the current publication verification. OAuth/live SMTP and physical devices remain unverified; clinical inference remains disabled. See [auth setup](AUTH_SETUP.md) and [mobile preview](MOBILE_PREVIEW.md). Historical dated figures below are research results, not newly validated clinical performance.

Additional 8 October research runs: completed 50 epochs each for conjunctival anemia (348 cleaned images), one conjunctivitis mirror (303 retained images), and wound binary segmentation (439 train / 109 validation masks). Internal image-level test balanced accuracy is 59.16% for anemia and 97.92% for conjunctivitis (53 and 46 test images respectively); these are not patient-independent or clinical accuracy estimates. Wound validation Dice is 0.4521 and IoU 0.3460, with no provider test masks. All three saved checkpoint forward checks passed. Three new split/hash tests and eight readiness/capture tests passed; changed source passes Ruff. The model-status endpoint exposes actual research artifact status while keeping diagnosis disabled. Retinal intake/training is a separate resumable pipeline; tongue/posture clinical datasets remain missing. [Details](MEDICAL_TRAINING_RUNS.md), [aggregate metrics](MEDICAL_TRAINING_RESULTS.json).

8 October: completed a 30-epoch last-block MobileNet skin fine-tuning experiment. Best validation balanced accuracy is 38.96%, compared with 37.38% for the frozen baseline. No test images were evaluated in this run. Checkpoint load/inference smoke check and four split-integrity tests passed; changed training source passes Ruff. This remains research-only and does not enable clinical diagnosis. See [training progress](TRAINING_PROGRESS.md) and [per-class results](SKIN_FINETUNING_RESULTS.json).

| Area | Implemented | Required next evidence/work |
| --- | --- | --- |
| Mobile experience | Light theme, navigation, profile, scan capture, history, photo/OCR review | Physical iPhone QA and accessibility/device testing |
| Account access | Email OTP flows, password reset, Google sign-in integration | User-configured SMTP credentials and Google OAuth client IDs; real delivery/sign-in testing |
| Medical captures | Seven photo workflows including fundus upload, protected owner-specific photos/history | Trained and independently validated models; current results deliberately abstain |
| Medicine documents | Offline printed-English OCR, editable confirmation, exact reference-name lookup | Handwriting support, Pakistan registration/source integration, clinician prescription verification |
| Skin data | Versioned Kaggle intake, SCIN expansion, hash/decode/duplicate audits, patient-group research split | Source identity/ID semantics review, label review, commercial permissions and external Pakistan cohort |
| Skin training | Six-class CNN baseline and frozen MobileNet transfer experiment, hashed model cards, engineer-only inference | Further training/validation development; healthy/other-condition rejection, calibration and external evaluation |
| Other five medical modules | Capture and safe abstention; anemia/fingernail/wound dataset intake and audits | Resolve data quality/rights/mappings; obtain remaining task-specific clinical labels and evaluate each target separately |
| Production/privacy | Development access controls and audit events | Deployment configuration, security review, retention/consent operations and applicable compliance assessment |

## Research training commands

The 20-epoch cached run completed on 4 October. Validation balanced accuracy was **31.4%**, held-out test balanced accuracy **35.5%**, and ordinary test accuracy **30.8%**. Atopic Dermatitis and Eczema recall were **0%**; Tinea Corporis recall was **50%**. These are failure findings for a simple baseline, not release evidence. [Full results](SKINDISNET_RESEARCH_RESULTS.json) preserve the six-class confusion matrix and per-class metrics. The older SCIN pilot uses a different cohort and class scheme, so its score cannot establish improvement or regression for this model.

Verification: 18 backend and 35 AI tests pass. Mobile type checking and the iOS production bundle export pass; physical iPhone testing remains pending. AI verification includes patient/pixel split leakage, incomplete checkpoint rejection, checkpoint tampering, cross-source duplicates, Hb metadata conflicts, wound mask/split checks, OCR confirmation and all six clinical workflows remaining inconclusive. Full AI source Ruff checks pass. Backend builds retain the existing NU1603 JWT dependency-resolution warning.

## Additional implementation and acquisition — 4 October

The mobile profile now opens an authenticated, paginated account activity screen. Its owner-filtered API returns action/category/time/success only, with private/no-store caching; raw medical payloads, IP addresses and error details are excluded. Scan and medicine read/history actions are recorded and covered by owner-isolation tests. This is a development activity record, not proof of a complete security audit or compliance.

A frozen ImageNet MobileNetV3 Small transfer-learning experiment completed 45 epochs, selecting epoch 30 using validation only. Validation balanced accuracy is **37.4%**, ordinary validation accuracy **43.7%**. The reserved test images were not opened or evaluated by this run. These scores cannot establish clinical improvement; validation was used to select the checkpoint. [Transfer model card](SKIN_TRANSFER_RESULTS.json). Research inference supports both CNN and MobileNet checkpoints and never returns a clinical diagnosis. The model status API distinguishes validation-only training from completed internal testing.

Three additional public Kaggle mirrors are downloaded and audited: CP-AnemiC, Ghana fingernails and CO2Wounds. Duplicate/Hb conflicts, missing independent patient mappings and source-license issues prevent training or product release. [Exact counts, sources and next gates](MEDICAL_DATA_INTAKE.md). Files include masks, copies and augmentations; asset counts are not independent patient counts.

The legacy six-module pipeline now refuses to run without explicit `--legacy-unvalidated`. Its synthetic posture targets and unreviewed data cannot silently become deployed medical models.

Reproducible commands from `ai-server`:

```powershell
.venv/Scripts/python.exe training/acquire_medical_research.py --dataset cp_anemic
.venv/Scripts/python.exe training/acquire_medical_research.py --dataset ghana_fingernails
.venv/Scripts/python.exe training/acquire_medical_research.py --dataset co2wounds
.venv/Scripts/python.exe training/audit_anemia_metadata.py
.venv/Scripts/python.exe training/audit_wound_annotations.py
.venv/Scripts/python.exe training/train_skin_transfer.py --output models/research/skindisnet-mobilenet-v2
```

The transfer command creates a **new** experiment, not a resume or overwrite. Repeating experiments needs a recorded research rationale. TongueAtlas access is restricted; TongueDx requires a request and has noncommercial terms; BioHit's mirror declaration does not establish an original dataset license. No tongue infection/deficiency or external-eye disease dataset has yet been cleared. SMTP/OAuth setup, physical device testing, clinician review and independent Pakistan evaluation remain outstanding.

Run from `ai-server` after acquisition/preparation:

```powershell
.venv/Scripts/python.exe training/train_skin_research.py --manifest datasets/kaggle/skindisnet_3_v1/research_patient_manifest.json --epochs 20 --cache-images --output models/research/skindisnet-cnn-v2
```

Output directories with existing checkpoints cannot be overwritten. Use a new run directory for subsequent experiments and record why the experiment changed. The original pilot is preserved. The initial uncached SkinDisNet attempt was interrupted after three epochs and has no final model card; it is not a completed experiment.

The cached run uses the same seeded CNN baseline, original six class labels, 1,143/263/227 images and patient-group assignments. Image caching changes loading cost, not the dataset or split. Roughly 306 MiB is needed for all float32 128×128 RGB tensors, plus framework and training memory.

`models/research/skindisnet-cnn-v2/model_card.json` is written only after completed training and final testing. It records classes, split counts, held-out balanced accuracy, confusion matrix, class-wise precision/recall, checkpoint/manifest hashes and limitations. `/api/v1/models/status` reports this separately from the historical pilot and never enables clinical inference. Research scores are not calibrated disease probabilities.

The internal held-out test measures this source cohort only. Once examined, it must not become a parameter-selection target. A fresh independent clinical test is still needed. No target accuracy is guaranteed, and noncommercial dataset permissions remain a product-release constraint.

## Clean views

Known conflicting Hb/labels and duplicate groups are quarantined; cleaned anemia retains 348 unique images. Cleaned wounds retain 704 photos with zero exact-pixel overlap across provider splits. Patient identity and license gates remain unresolved. [Cleaning results](DATA_CLEANING_RESULTS.md), [Kaggle collection guide](KAGGLE_DATASET_GUIDE.md).

## Saved-photo upload

All six scan workflows now expose a saved-photo picker directly on the consent screen, without requiring camera access. Camera and gallery photos enter a review screen before explicit upload/save; failed uploads return to review for retry. JPEG/PNG/WebP and a 10 MB picker limit are checked; HEIC requires JPEG export if the picker does not convert it. Processing copy describes upload/image checks/storage rather than claiming classification. Type checking and iOS bundle export pass; physical iPhone QA remains pending. This feature does not enable clinical inference: current results remain inconclusive.

## User-provided archives

Two user Kaggle ZIPs are safely extracted and audited. The 4,260 nail assets add zero new pixels beyond the existing Ghana collection. The skin ZIP adds 2,351 common-skin research candidates after exclusions (1,724 Acne, 305 Eczema, 322 mixed fungal). These remain separate from existing training/test cohorts, with source license, clinical labels and patient grouping unverified. [Full intake report](USER_DATASET_INTAKE.md).

## Five Kaggle links

User links confirm the previously uploaded skin/nail mirrors. A second nail mirror is acquired: 9,069 assets, 4,154 unique pixels; it contains all existing Ghana nail and CP-AnemiC conjunctiva pixels. Only 1,316 unverified new candidates remain after exclusions, with original license/Hb/patient/body-area review still required. Two larger skin links are metadata/inventory reviewed, not image-audited or merged. [Review and decisions](KAGGLE_LINK_REVIEW.md).

## Eye dataset intake

Six eye links reviewed. Two conjunctivitis mirrors acquired and audited: per-source clean candidates 303 and 601; 4 shared exact-pixel groups and 71 cross-source near-match flags remain for review. No pooled clinical training split is created. Fundus datasets are kept outside phone external-eye training; sclera data is inventory/sample-reviewed with unverified family/patient/clinical labels. Annotation-review CSVs are prepared and clinical inference stays disabled. [Eye report](EYE_DATASET_REVIEW.md).

## Retina / Fundus workflow

Upload-only Retina workflow added to scan list, review/save flow, history filter, backend scan type and separate AI preview route. Fundus gallery selection preserves framing by disabling cropping. Modality verification and disease inference remain unavailable. Retinal acquisition is registered but full fundus archives are not yet acquired/trained. Typecheck, changed-file lint, iOS bundle export, 18 backend tests and 35 AI tests pass. [Retina scope and research gates](RETINA_MODULE.md).

## Research expansion — 10 October 2026

The earlier paused acquisition processes were no longer running. Retina serial acquisition and the pinned original FUSeg snapshot have been restarted with saved download state; full source integrity checks and extraction must complete before either is counted as acquired. FUSeg may restart a partial ZIP when its source ignores byte-range requests. Download progress is not a completed training result.

Completed exploratory classifiers include conjunctiva anemia (internal balanced accuracy **59.16%**) and conjunctivitis (**97.92%**, only 46 internal test images). The skin fine-tune achieved **38.96% validation balanced accuracy**. These results use different tasks/cohorts and cannot be averaged as an overall product accuracy. The original wound CNN achieved **0.4521 validation Dice**. The encoder/decoder U-Net completed 60 epochs on the same retained 439 train / 109 validation masks, selecting epoch 58: **0.6663 validation Dice / 0.5445 IoU**, a Dice increase of 0.2142. Selected checkpoint integrity and finite forward output pass. Validation is reused, with unverified patient identities and no provider test masks; this is not independent clinical improvement. [U-Net model card](WOUND_UNET_RESULTS.json), [learning curve](WOUND_TRAINING_CURVE.png).

The quality checker now rejects a tiny perfect classification sample as evidence of the >97% target. In addition to external test/clinical-ground-truth/patient-independence metadata and checkpoint integrity, it requires every class sensitivity/specificity and their approximate simultaneous Wilson confidence lower bounds to exceed 97%. Supplied metadata still requires independent verification. Neither numerical passage nor training completion enables patient diagnosis.

Fifteen targeted tests pass for U-Net spatial/gradient behavior, Dice calculations, confidence bounds, target evaluation and model readiness. Changed Python files pass Ruff. [Expansion strategy](DATASET_EXPANSION_STRATEGY.md) records original sources and unsuitable/restricted sources; [access-request drafts](DATA_ACCESS_REQUEST_DRAFTS.md) are prepared but have not been submitted. Tongue and posture are not yet trained on approved clinical disease ground truth. [Aggregate training results](MEDICAL_TRAINING_RESULTS.json) and [target checks](QUALITY_TARGET_RESULTS.json) distinguish incomplete jobs from completed research models.

Latest tongue/posture work: TongueDx independent-developer/commercial-permission inquiry submitted and receipt verified; approval pending. Open CC BY 4.0 MultiPosture CSV acquired and checksum-verified: 4,794 frames from 13 provider subjects. Sitting-posture two-head MLP completed 50 epochs with subject-disjoint splits; internal test balanced accuracy 90.18% upper / 87.52% lower on four test subjects. This does not support scoliosis diagnosis. Open Zenodo tongue-coating ZIP acquisition is in progress; Dryad downloads require authentication/return 403. [Full current status](TONGUE_POSTURE_PROGRESS.md) supersedes the earlier unsent-request status. Six new intake/split/resume tests pass. Legacy direct tongue/posture trainers require explicit unvalidated execution and no longer silently treat appearance folders as anemia/thrush.

Retina acquisition/audit and the 50-epoch exploratory frozen-feature classifier also completed during this work: **84.10% internal image-level test balanced accuracy**, with unresolved patient independence and original image permissions. This supersedes the earlier download-pending status; fundus clinical inference stays disabled. [Aggregate results](MEDICAL_TRAINING_RESULTS.json).
