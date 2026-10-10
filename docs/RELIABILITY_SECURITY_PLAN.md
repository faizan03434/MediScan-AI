# Reliability and security work — 10 October 2026

## Implemented in this change

AI image utilities validate the actual image format, reject animated images, and check a 20-million-pixel / 10,000-pixel-edge budget before pixel decoding. OpenCV callers use the same bounded decoder. EXIF orientation is applied and metadata is removed from the returned decoded image; this does **not** prove that original files retained by the backend have had location metadata removed. Storage sanitization and deletion/retention still need a separate review.

API-key comparison uses `secrets.compare_digest`, handles Unicode without a server error, and rejects empty configured credentials. This does not replace production key provisioning/rotation, HTTPS or private network access. The existing development default key remains unsuitable for production.

Eight regression tests cover allocation before decode, corrupt/unsupported uploads, EXIF orientation/privacy, OpenCV bounds/color order, and empty/wrong/valid credentials. All **69 local AI tests** pass, including clinical abstention and research checkpoint readiness. Changed utility/test files pass Ruff. The dedicated GitHub workflow runs the eight upload-security tests against production-pinned utility dependencies; remote CI results must be checked separately. Local packages are newer than the pinned deployment dependencies, so local passage alone does not validate that deployment environment.

## Model reliability work

Follow-up implementation: reserved-subject temperature calibration, calibration metrics, unknown-condition rejection reporting and clinical-cohort metadata checks are now available. The cohort checker requires consent/rights claims, two distinct reviewers, resolved adjudication, reference standards and separate Pakistan external-test subjects; it never grants clinical approval. See [clinical validation workflow](CLINICAL_VALIDATION_WORKFLOW.md). No actual clinician review, independent Pakistan recruitment or real-model calibration has been completed by these tools. All 78 local AI tests pass, including nine new calibration/cohort checks.

1. Obtain labels and rights suited to each exact task. Sitting-posture labels do not establish scoliosis; tongue morphology does not establish B12 deficiency/infection. Review annotations with clinicians and verify subject grouping.
2. Keep training/validation selection separate from a newly collected independent clinical test. Include Pakistan participants, phone/device variation, lighting, skin tone, and alternative conditions. Previously inspected tests cannot be reused to tune a headline score.
3. Add capture-quality feedback and separately validate blur/exposure/ROI thresholds before using them to reject patient images. Do not use arbitrary quality heuristics as disease evidence.
4. Fit probability calibration using reserved calibration data only; measure calibration error, per-class sensitivity/specificity, confidence intervals and unfamiliar-condition rejection on independent data. Confidence is not diagnostic certainty.
5. Define task-specific metrics: Dice/IoU and physical scale error for wounds; repeated-measurement angle error for posture. Do not call every metric “accuracy”. Preserve failed experiments and checkpoint/data hashes.

## App and deployment work

Review retained-upload sanitization, access/owner isolation, credential/OTP abuse limits, clinician consent/revocation, retention/deletion, encrypted transport/storage and audit-log exclusions. Audit dependencies and production configuration in the actual deployed environment. These changes are incremental safeguards, not evidence of HIPAA certification or complete medical validation.

Integrated backend follow-up: OTP digests use keyed HMAC; three sends and five failures per account/purpose per 15 minutes survive resending within the process. Storage upload/read/delete now reject escaping paths, alternate streams and existing symlinks/junctions. The API now reads ignored server `.env` settings; all 33 backend tests pass. Distributed/restart-persistent OTP budgets, storage encryption/metadata sanitization and operational retention remain pending.

## GitHub publication scope

Publication now includes the existing mobile/backend/research source integration, login/email OTP/reset/Google flows, authenticated media access, light UI, camera/gallery and Android/iPhone preview setup, alongside reliability tools and CI checks. The development database has been removed from source tracking while preserved locally. Raw images, patient databases, access correspondence, datasets and model weights are excluded. GitHub publication is distinct from deploying or enabling clinical inference; physical-device/live OAuth and SMTP tests remain pending configuration.
