# Clinical cohort and calibration workflow — 10 October 2026

This is an implemented research workflow and a draft clinical collection protocol. No clinician has reviewed a new Pakistan cohort in this work, no participant recruitment has happened, and no current disease model is newly calibrated or approved by this document. Clinical leadership, consent/access approval and actual reference diagnoses remain external prerequisites.

## Before collecting data

Appoint a licensed clinical lead and settle study purpose, consent, source permissions, secure retention and who can access/link records. Use pseudonymous subject and reviewer IDs in research exports; keep names/contact details and patient linkage in the clinical team's protected system. Do not commit patient manifests/photos/lab reports to GitHub. Define recruitment and device/site/lighting coverage with the clinical team before examining performance. Statistical sample-size planning must count independent subjects, not repeated or augmented frames.

Use task-specific reference standards defined by the clinical lead: measured Hb and reviewed image modality for anemia; reviewed clinical skin/eye diagnoses with alternative conditions; wound masks and a physical calibration reference for size; appropriate clinical/radiographic evidence for scoliosis. Posture positions and tongue appearance must remain appearance/pose tasks unless an actual disease reference is available. A published folder name is not a clinical reference.

## Review and freeze cohorts

For each case record: `subject_id`, `split` (train/selection/calibration/external_test), `decoded_pixel_sha256`, `consent_for_this_use`, `source_rights_reviewed`, `reviewer_ids`, `adjudication`, `reference_standard`, `label`, `label_status` (supported_condition/unknown_condition), `country`, `device_group`, `site_id`, `lighting_group`.

Two independent clinical reviews with resolved disagreements are the proposed annotation workflow. Keep the clinical supporting evidence in a restricted store. Review near duplicates and all views/visits of a subject before assigning a split. Reserve separate calibration and Pakistan external-test subjects; include alternative/unfamiliar conditions. Freeze manifests and model hashes before evaluation. Reviewer/consent booleans remain claims requiring independent evidence, never automatic clinical approval.

The implemented `training/clinical_cohort_review.py --manifest <private-file.json>` checks metadata requirements, known cross-split subject/pixel overlap, separate cohorts and external unknown examples. It emits aggregate counts and requirements without individual case data. An empty/unreviewed cohort fails. Passing schema checks is not a completed clinical trial, statistical adequacy assessment or authenticated diagnosis.

## Calibration and rejection

[Temperature scaling](https://arxiv.org/abs/1706.04599) is implemented in `training/calibration_research.py`, fitting a positive temperature by reserved-cohort negative log-likelihood. Metrics include NLL, multiclass Brier score and expected calibration error. The first implementation requires one observation per calibration subject and rejects subjects listed as used for training, checkpoint selection or prior inspected tests. A supplied registry still requires completeness/provenance review.

Input is an ignored private NPZ with `logits`, integer `labels`, and string `subject_ids` (no pickle arrays). The protocol JSON contains `role: reserved_calibration`, `checkpoint_sha256`, and `previously_used_subjects`. Run:

```powershell
.venv/Scripts/python.exe training/calibration_research.py --input datasets/clinical/calibration_logits.npz --protocol datasets/clinical/calibration_protocol.json --checkpoint models/research/<run>/weights.pt --output models/research/<run>/calibration-v1.json
```

Outputs are immutable aggregate artifacts with checkpoint/input/protocol hashes. Calibration-fit metrics are optimistic and are not independent test performance. Test data must not be supplied to this fitting command. Temperature scaling adjusts probabilities; it does not change the predicted class or rescue a poor classifier's accuracy.

The implemented [maximum-softmax rejection baseline](https://arxiv.org/abs/1610.02136) reports known coverage, error among accepted known cases, and unknown false acceptance. Missing unknown examples produce an unavailable rate, never a false claim of safety. Confidently wrong unknowns can pass this rule. Choose any threshold on reserved calibration data, then freeze it and evaluate independent unknown-condition data. No patient inference route is enabled by these tools.

## App safeguards implemented

OTP challenges now have a keyed HMAC digest and an account/purpose budget of three sends and five failures per 15-minute window in addition to the existing 60-second resend delay and single-use expiry. Resending or consuming a code cannot reset that budget. It is still an in-memory, single-process development store: restarts and multiple instances require a shared atomic store and production rate-limit design. Send budgets can cause temporary throttling; unknown-account reset responses retain generic wording, but full timing-enumeration review remains pending.

Local storage canonicalizes all upload/read/delete paths, rejects traversal/absolute/alternate-stream paths and checks existing paths for symlinks/junctions. Existing owner-scoped media access and no-store caching stay in place. The filesystem root must be application-controlled; path checks do not remove operating-system race conditions if an attacker can modify directories. Original stored-photo EXIF sanitization, encryption-at-rest and operational retention/deletion remain pending. These controls follow [OWASP file-upload guidance](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html) and [reset-token abuse guidance](https://cheatsheetseries.owasp.org/cheatsheets/Forgot_Password_Cheat_Sheet.html).

Verification: 33 backend tests pass, including resend-budget persistence, traversal-safe read/write/delete and server dotenv parsing; all 78 AI tests pass, including nine calibration/cohort tests. The backend still reports the existing NU1603 JWT dependency-resolution warning. No medical improvement percentage is claimed from synthetic unit-test fixtures. Backend safeguards are integrated with the authentication/media source changes for publication. Real SMTP/OAuth and physical-phone tests require configuration and devices.
