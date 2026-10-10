# MediScan AI: implementation audit and delivery strategy

Updated 2 October 2026. This document supersedes the attached aspirational strategy and earlier README claims.

## Product scope

Pakistan-first mobile health photo journal and clinician-assisted screening. Six capture workflows, medication label lookup, prescription records, history, consent and progress review. No promise of perfect diagnosis. A one-month target is an engineering prototype, not a clinically validated release.

## Existing work versus actual capability

| Area | Existing implementation | Remaining work |
| --- | --- | --- |
| Repository | Existing GitHub remote: faizan03434/MediScan-AI | Review changes and CI before publishing |
| API | .NET 9, Identity/JWT, SQLite development database, controllers | Authentication/security review, production PostgreSQL migration verification |
| Mobile | Expo Router, onboarding/auth/profile, six scan screens, history, doctor screens | Physical iPhone verification, complete error states, accessible UX, Urdu copy |
| AI | Six gated capture workflows; SCIN pilot and research CNN checkpoint, no validated clinical model | Broader task-specific data, research inference loaders and independent clinical validation |
| Camera | Camera preview, still capture, gallery upload | Actual live ROI detection/frame inference requires a development build and validated models |
| Medication | Exact OpenFDA references, barcode camera/unknown handling, actual offline OCR with confirmation and private prescription storage | Pakistan barcode/product registry, formulation matching and clinician verification |
| Recommendations | Rule/LLM scaffolding | Clinician-reviewed condition-specific content and red-flag policies; no automatic prescribing |
| History | Saved records and photo comparison | Validated measurements for progression; confidence changes do not measure recovery |
| Privacy | Identity, role checks, some audit events, local storage | Read audits everywhere, server consent versioning, retention/deletion/export, 2FA, encryption, threat review |

## Changes made for the first runnable milestone

Expo SDK 54 / React 19 / React Native 0.81 compatible dependency alignment; missing asset references removed; unsupported/unused native packages removed; camera hook order fixed; browser session storage and uploads supported; device API host derived from Metro; enum JSON strings aligned with TypeScript; AI snake-case reminder parsing fixed; invalid scans rejected; owner-authenticated local image delivery added; nonvalidated inference abstains for every module; misleading HIPAA, Pakistan registry and recovery claims corrected.

The legacy model routes remain as research code but are not mounted. Merely adding a .pt file must not enable clinical predictions. Preview captures return inconclusive with no clinical probability or clinical rescan schedule.

## Second engineering milestone

White/gray mobile theme with a restrained green accent; safe-area header and icon navigation; responsive authentication screens; registration and password-reset email OTP; Google ID-token verification and optional native plugin; profile editing and explicit Google account linking; paginated scan history; meaningful help/privacy screens; cross-account query-cache clearing; refresh-token ownership correction; password-reset security-stamp invalidation; per-IP auth limits. The QR now opens a standard HTTP handoff page instead of requiring direct Camera recognition of an Expo URL.

Email delivery still needs the sender's app password in ignored local server configuration. Google needs Web/iOS client IDs and an iPhone development build. See `AUTH_SETUP.md`. No real external email or Google exchange has been verified. See `DATASETS.md` for the missing data and the legacy candidate audit. Physical iPhone camera, QR handoff and native permissions still require the user's device test.

## Model strategy

| Module | First defensible goal | Data and release requirement |
| --- | --- | --- |
| Anemia | Pallor research and referral support | Same-patient hemoglobin/CBC labels, capture/color calibration, representative Pakistan cohort. A photo cannot confirm/exclude anemia. |
| Skin | Narrow, clinician-labeled common-condition study | Phone photos labeled for the actual eczema/fungal/acne targets. HAM10000 is dermoscopy of seven pigmented lesion categories, not the proposed common-rash dataset. |
| Posture | Pose symmetry and ergonomic observations | Physiotherapist annotations and repeatable capture protocol. Do not report camera-derived scoliosis diagnosis/Cobb angles without suitable clinical validation. |
| Eye | Separate externally observable eye-sign studies | Ophthalmologist labels, lighting/device controls, distinct cataract/redness/jaundice tasks; do not equate scleral color with diagnosis. |
| Wound | Calibrated planar area and clinician photo review | Known reference marker in the wound plane, validated segmentation, measurement error evaluation. No cm estimate from an uncalibrated image; healing stage requires clinical evidence. |
| Tongue | Document visible features for review | Narrow clinician-labeled findings, quality and out-of-distribution rejection. No unvalidated deficiency inference or traditional diagnostic claims. |

Train ROI detection only where ROI labels exist. Train classification on clinically appropriate labels. Implement each checkpoint loader and preprocessing, then verify export parity before ONNX/device deployment. YOLO's generic COCO classes are not eye/nail medical ROI classes. A training script alone is not working medical inference.

Split by patient/site, not random images; remove duplicates across splits; preserve an untouched external test set. Measure sensitivity/specificity per condition, AUROC, precision/recall, calibration, abstention coverage and confidence intervals. Review skin tone, age, phone, lighting and site subgroups. Set release thresholds with clinicians before evaluation, not after observing metrics. Store model version, input quality, provenance and decision status on each scan. Escalation must never depend solely on a reassuring score.

## Medication and recommendation policy

Barcode identifies a product only when an authoritative mapping exists; US NDC is not universal Pakistani EAN/GTIN. Show unknown and permit exact manual entry. Require confirmation of brand, ingredient, strength and dosage form after OCR. OCR errors and missing interaction warnings must not imply safety.

Use DRAP's official registered-product index for Pakistan registration verification. Current backend uses OpenFDA, a US label source, and must not claim Pakistan approval, availability, price or manufacturer origin from it. Record source URL, retrieval time and exact-match status in a subsequent schema change.

Do not recommend tablets/shampoo as a consequence of unvalidated photo classifications. A disclaimer is insufficient to make automated prescribing reliable. Build clinician-reviewed education, contraindication-aware reference content and pharmacist referral. Lifestyle plans/rescan intervals should be condition-specific, approved and symptom-aware; avoid universal fluid targets. Comparisons need validated task metrics and consistent capture conditions, not classifier confidence.

## Four-week engineering sequence

1. Week 1: finish reproducible local mobile/API setup, contract tests, account isolation, server consent/versioning, error UX, profile/history review and working iPhone camera upload. Review current doctor/admin permissions and remove placeholder affordances.
2. Week 2: exact medicine lookup/provenance, OCR with editable confirmation, prescription upload consent, barcode unknown handling, reminders only for approved plans, clinician-authored reference content.
3. Week 3: one narrow AI module end to end after dataset/license/label review; reproducible training, inference loader, quality rejection, external evaluation. Keep the other five preview workflows visible but nonclinical.
4. Week 4: pilot UX with clinicians, Urdu/localization, accessibility, deletion/export/retention, threat review, CI and mobile development build. Expand to the remaining models only as their evidence supports it.

Each milestone needs a runnable demo and evidence, not five or six unchecked medical modules per day. Clinical dataset collection and validation may take longer than one month.

## Compliance and deployment

HIPAA applicability depends on covered-entity/business-associate relationships; using .NET Identity, Azure or AES does not establish compliance. For US regulated relationships assess BAAs, vendor/subcontractor handling, access controls, incident response, risk assessment and policies. Obtain Pakistan legal/regulatory review for intended medical-device claims and health-data processing. Do not claim approval or compliance while review is pending.

Development currently has local HTTP, SQLite, local photo files and seeded credentials. Use synthetic/test data. Production needs TLS, secret management, private storage, encryption/key management, verified restore backups, rate limits, refresh-token/session review, complete access auditing and agreed retention. The authenticated media endpoint protects local preview files; production Azure access policy still needs independent review.

The development database was already tracked in Git before this work. Ignore rules now exclude new database/photo files, but the tracked database must be removed from version control and any sensitive historical contents reviewed before publication. Local scan records created by smoke tests are synthetic; do not commit the development database.

## Primary references

- [Expo Go version compatibility](https://docs.expo.dev/troubleshooting/expo-go-version-mismatch/)
- [Expo SDK 54 dependency map](https://github.com/expo/expo/blob/sdk-54/packages/expo/bundledNativeModules.json)
- [HAM10000 original dataset paper](https://www.nature.com/articles/sdata2018161)
- [WHO hemoglobin guideline](https://www.who.int/publications-detail-redirect/9789240088542)
- [DRAP registered product index](https://eapp.dra.gov.pk/WebProductIndex.php)
- [HHS HIPAA applicability](https://www.hhs.gov/hipaa/for-professionals/covered-entities/index.html)
