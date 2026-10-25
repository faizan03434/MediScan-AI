# Research training update — 25 October 2026

**Nine new experiments completed on CPU. All new results below are validation results, not new independent test accuracy. No clinical task was enabled, and 90%+ across diseases has not been established.**

| Task | Previous validation result | New experiment | Decision |
| --- | ---: | ---: | --- |
| Conjunctival anemia | Balanced accuracy 62.88% | MobileNet + raw color features: 64.55%; ResNet/color candidate: 55.00% | Preserve the improvement as research only; 53-image old test not reused |
| SkinDisNet, six classes | Balanced accuracy 38.96% | MobileNet feature candidate: 37.07%; ResNet candidate: 27.96% | Neither replaces the existing best |
| Conjunctivitis | Balanced accuracy 97.83% | 97.83% | No validation improvement; 46-image old test not reused |
| Retina/fundus, four classes | Balanced accuracy 84.84% | 86.18% | Research candidate; 492-image old test not reused |
| Wound U-Net | Original-mask validation Dice 0.66664 | 0.69830; IoU 0.54485 → 0.57752 | Matched original-resolution comparison on 109 validation masks; no test masks available |
| Sitting upper/lower posture | Balanced accuracy 93.15% / 96.86% | 97.47% / 99.67% | Validation has only two provider subjects; four-subject test not reused; not scoliosis |
| SCIN, three skin classes | Balanced accuracy 58.33% | 66.67% after expansion | Only eight validation cases; highly uncertain and not comparable to the six-class SkinDisNet task |

These selection results reuse existing validation cohorts. An improvement is not an external performance estimate or a statistical significance finding. Wound Dice is segmentation overlap, not disease-classification accuracy. The wound run's resized 128×128 validation Dice is 0.69806; the comparison above evaluates both checkpoints against the same original-resolution masks to avoid mixing evaluation resolutions.

## Training changes

- Wound: verified warm start from the existing checkpoint, 128×128 inputs, per-image Dice plus BCE loss, matched quarter-turn/flip augmentation, 30 epochs at learning rate 0.0001. Best resized-mask checkpoint was epoch 26. Old weights/results remain unchanged.
- Classification: frozen ImageNet MobileNetV3 or ResNet18 features, RGB/Lab summary descriptors, train-only standardization and class-balanced logistic regression. A predeclared four-value regularization grid and three feature modes are selected only on validation. No clinical color calibration is claimed. Worse experiments are retained and reported rather than promoted.
- Sitting posture: hip-centered, torso-length-normalized landmark coordinates followed by the existing two-head MLP; train-only standardization, 80 epochs, validation selection. The normalization schema is checked and degenerate geometry rejected. This research experiment uses provider coordinate data; it is not a validated live-camera scoliosis pipeline.
- Numeric classifier checkpoints are stored as tensors rather than executable estimator pickles. The offline prediction tool checks weight/backbone hashes and reports uncalibrated research scores with `diagnosis: null` and `clinical_inference: false`. Float32/float64 compatibility is regression-tested.
- The quality evaluator now accepts an explicit `--target 0.90`. External testing, patient identity, clinical reference labels, class sensitivity/specificity and confidence-bound requirements remain in place. None of the supplied model evidence meets the complete independent 90% target. The evaluator never grants clinical deployment approval.

## Data acquired and blocked

**103 additional high-consensus SCIN cases were downloaded from the original public source.** The expanded research cohort has 154 images: 137 training / 8 validation / 9 test. Classes are Acne 15, Eczema 127 and Tinea 12. The expansion preserved every original case assignment, put new cases in training only, checked file/decoded-pixel identities and screened cross-split near duplicates. No new image was quarantined in this particular expansion. Most added cases are eczema; this does not solve acne/tinea scarcity or establish verified patient identities. Original images and per-case metadata remain outside Git. Attribution/source: [Google Research SCIN](https://github.com/google-research-datasets/scin); its dataset-specific license still applies.

Original [FUSeg](https://github.com/uwm-bigdata/wound-segmentation) intake was attempted both per-file and as a pinned repository ZIP. Connection/streaming errors prevented completion. A partial archive is retained locally, **not counted as acquired or used for training**. Provider patient mapping, mask audit and source permissions still require review after a complete download. Terminal download failures now persist `download_failed` rather than leaving a misleading `downloading` state.

No new tongue diagnostic training was performed: authoritative disease labels and suitable permissions remain unresolved. Fingernail photos without verified anemia labels/Hb mapping were not converted into diagnoses. Restricted scoliosis data was not accessed by bypassing an agreement.

## Verification and remaining work

**97 AI unittest checks passed; full-tree Ruff E/F/W checks passed.** All nine new checkpoint hashes were verified. The seven feature-classifier checkpoints passed actual offline load/forward checks on training samples; those checks are not performance evaluations. Wound checkpoints passed the original-mask forward comparison. Unit tests cover normalization invariance, source/split preservation, duplicate quarantine, warm-start integrity, numeric checkpoint predictions, the 90% evidence gate and download-failure state.

Next: resolve label/source bottlenecks for weak tasks, obtain task-appropriate independent subjects and healthy/unknown-condition coverage, train and calibrate using reserved development cohorts, then evaluate untouched external Pakistan/device cohorts with clinicians. More images or additional epochs alone do not establish 90% clinical accuracy. SMTP/Google/device/cloud delivery work from the prior product checkpoint remains outstanding; this research batch does not complete it.

[Aggregate checkpoint/results evidence](TRAINING_UPDATE_2026_10_25.json) · [90% evidence gate](QUALITY_90_2026_10_25.json)

Reproduce from `ai-server` with new output directories:

```powershell
.venv/Scripts/python.exe training/expand_scin_research.py --output datasets/scin/expanded_manifest_20261025.json
.venv/Scripts/python.exe training/train_feature_research.py --task anemia --output models/research/<new-run>
.venv/Scripts/python.exe training/train_feature_research.py --task skin --backbone resnet18 --output models/research/<new-run>
.venv/Scripts/python.exe training/train_wound_unet_research.py --epochs 30 --patience 10 --size 128 --initial models/research/wound-unet-v1 --learning-rate 0.0001 --per-image-dice --spatial-augmentation --output models/research/<new-run>
.venv/Scripts/python.exe training/train_sitting_posture_research.py --epochs 80 --normalize-pose --skip-test --output models/research/<new-run>
.venv/Scripts/python.exe training/evaluate_quality_target.py --target 0.90 --include-experiments --output ../docs/<new-evidence-report>.json
```

The expanded manifest already exists locally and is immutable; the acquisition command above deliberately refuses to overwrite it. `--task scin` uses that pinned expanded cohort. ResNet18 requires the official checksum-verified pretrained file at `models/pretrained/resnet18-f37072fd.pth`; its backbone/normalization recipe follows [Torchvision](https://docs.pytorch.org/vision/stable/models/generated/torchvision.models.resnet18.html). Earlier reports/checkpoints are preserved. No training job remains active after this batch.
