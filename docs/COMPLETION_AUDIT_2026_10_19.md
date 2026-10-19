# MediScan completion audit — 19 October 2026

**Newest checkpoint:** [operations and session evidence](OPERATIONS_AND_SESSION_CHECKPOINT.md) updates the same rubric to **57/100 complete, 43/100 remaining**. The 65 milestone has not been reached. 95 backend tests and 87 AI checks pass; clinical acceptance is still incomplete. The checkpoints below are historical.

**Current checkpoint:** [account deletion/readiness evidence](ACCOUNT_DELETION_AND_READINESS.md) and [delivery ledger](DELIVERY_STRATEGY.md) update the engineering estimate to **51/100 complete, 49/100 remaining**, with 66 backend/87 AI tests passing. Earlier estimates below are historical; clinical validation is still incomplete.

**Later checkpoint:** [Delivery strategy and implementation ledger](DELIVERY_STRATEGY.md) records persistent OTP, account exports/all-device sign-out, opt-in deleted-record cleanup, deployment exclusions/volumes and preview host recovery. The updated engineering estimate is **49/100 complete, 51/100 remaining**. The 45/100 assessment below is the earlier baseline; clinical acceptance remains incomplete.

**Engineering estimate: 45/100 complete, 55/100 remaining for the requested production medical product.** This is a manually weighted delivery estimate, not measured model accuracy, a clinical approval score or a promise of remaining calendar time. The app foundation is further along than medical validation. A working capture/history screen does not constitute disease detection.

## Basis of the estimate

| Deliverable | Weight | Earned | Remaining evidence or implementation |
| --- | ---: | ---: | --- |
| Mobile UX, navigation, camera/gallery and live framing | 20 | 16 | Physical Android/iPhone camera and auto-capture QA, accessibility, network recovery and anatomy-specific detectors |
| Login, registration/reset OTP and Google access | 10 | 6 | Successful live email delivery, OAuth client IDs and actual sign-in, restart-safe/shared OTP budgets and abuse review |
| Records, history, documents and privacy | 15 | 10 | Consent/retention operations, complete deletion verification, handwriting and clinician medication review, production storage controls |
| Dataset intake and research models | 20 | 11 | Task-specific labels/rights and subject identity, reliable skin/anemia/wound improvements, verified tongue/scoliosis data, independent splits |
| Independent clinical validation and release acceptance | 25 | 0 | Clinician reference labels, reserved calibration and unknown-condition tests, Pakistan external cohorts, task-specific acceptance and approval |
| Production deployment and release operations | 10 | 2 | HTTPS deployment, signed mobile releases, backups/restore, monitoring, secrets/key rotation and deployed security testing |
| **Total** | **100** | **45** | **55 remaining** |

Weights reflect the requested diagnostic product, with substantial effort assigned to actual clinical evidence. Frameworks and protocol documents receive credit in foundation/research areas; they do not receive credit as completed clinical validation. Reassess against completed deliverables, rather than adding points for each commit or image downloaded.

## Implemented in this audit

- New scan and prescription photo writes now pass through an authenticated internal image normalizer before storage. It validates the decoded format/resolution, applies EXIF orientation and saves RGB PNG without original EXIF/location/text/profile metadata. Decoded RGB samples are saved losslessly; this is not color calibration. Existing retained uploads are not migrated by this change.
- Storage rejects unavailable or malformed normalizer responses without falling back to raw uploads. Input/output byte budgets and a processing deadline bound this path. Normalization now depends on the internal AI service being available, including for uploads whose diagnosis deliberately abstains.
- Both local and Azure-backed writes return the owner-authorized media URL. Azure reads now return a bounded, seekable stream for media type checks. Azure cloud behavior has not been integration-tested with a real account.
- A shared two-job limit per AI worker process covers live guidance and photo normalization. Overflow returns a busy response. This is not a distributed capacity limit for all OCR/inference endpoints.
- Mobile capture validates response types, rectangle bounds, the 64-value motion signal and nonclinical status. Contradictory evidence cannot authorize auto-capture; posture requires a verified person detector. Other modules still use explicitly labelled framing guidance rather than trained anatomy detectors.
- The local integration smoke check now verifies metadata-free stored images and removes every synthetic scan it creates.

## Verification performed

- **41 backend tests passed**; API build succeeded. Existing NuGet warning: requested JWT package 8.3.3 resolves to 8.4.0; dependency pin cleanup remains separate work.
- **86 AI tests passed**; full AI Ruff checks passed.
- Mobile TypeScript, ESLint and capture stability/schema checks passed; a fresh production web bundle exported successfully.
- Running local API + AI service: all six external-photo modules saved/read synthetic images, remained medically inconclusive, enforced owner isolation, applied orientation, removed metadata and rejected empty/corrupt uploads. All six test records were deleted; their photo routes then returned unavailable.
- These checks use synthetic data. They do not test clinical performance, a physical phone camera, live Google OAuth or a cloud storage account. Remote GitHub CI results require separate confirmation.

## Current capabilities and limits

The light-themed app has email login, OTP/reset flows, Google integration code, profile/dashboard, camera/gallery capture, history/comparison, protected photos, printed-English OCR review, medicine reference lookup and audit events. Retina/fundus upload is separate from ordinary external-eye phone capture.

Live capture is sampled server-assisted framing. Posture has a real COCO YOLO person rectangle; that detector does not diagnose scoliosis. Eye/nail/skin/wound/tongue anatomy detection remains untrained. Research disease models exist for several tasks, but **clinical inference remains disabled**; scan completion means the upload workflow completed. It does not mean a disease was detected or excluded. Automated prescriptions and clinical medicine suitability verification are not available.

No new model training, clinician label review or independent clinical testing was completed in this audit. Earlier internal research scores, including the small conjunctivitis result, cannot establish 97% performance for every disease. More images require correct modality, labels, rights and independent subjects; duplicates and unrelated modalities do not count as new clinical evidence. Tongue/posture clinical permissions and verified disease labels remain outstanding.

SMTP settings are configured locally. The last actual delivery attempt documented on 10 October failed; delivery was not retried in this audit. Google OAuth IDs and real-device sign-in remain outstanding. OTP budgets are currently single-process memory and need an atomic persistent/shared store for production.

Development records are stored in `backend/MediScan.API/mediscan_dev.db`; photos are under `backend/MediScan.API/wwwroot/uploads/`. This is local storage on the development computer. Database, uploads, secrets, datasets and model weights are excluded from the current source publication. Historical Git contents have not been rewritten. No HIPAA certification or production security approval is claimed.

## Remaining implementation sequence

1. Persist OTP challenges/send/failure budgets atomically, verify live SMTP and configure/test Google OAuth.
2. Test signed Android/iPhone builds on real devices: permissions, overlay alignment, auto-capture, camera/gallery failures and slow/offline networks.
3. Complete consent, retention/account deletion, backup/restore and production access/storage controls; deploy API/AI behind HTTPS.
4. Resolve each dataset's modality, commercial rights, annotations and subject splits; obtain missing tongue and scoliosis reference labels. Improve weak models using reserved selection data, preserving untouched external cohorts.
5. With clinicians, collect/reference-label Pakistan external cases; fit calibration on separate subjects, test unfamiliar conditions and evaluate task-specific metrics with uncertainty. Enable a clinical task only after its own acceptance evidence is complete.

The final item is a clinical evidence program, not a software switch that can be completed by enabling an unvalidated checkpoint.
