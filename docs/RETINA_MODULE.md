# Retina / Fundus workflow

The seventh photo workflow is now available in Medical Scans and history filters. It accepts a saved JPEG/PNG/WebP fundus image, asks the user to review and confirm it, then saves it through the same authenticated owner-specific scan/media/history pipeline. Gallery selection disables cropping for this workflow. Ordinary camera capture is hidden because a front-eye phone picture does not capture the retina.

The backend appends `Retina` to the existing ScanType enum, preserving older numeric values. Its AI route is `/api/v1/detect/retina`, separate from `/api/v1/detect/eye`. Model readiness reports retina as validation_required. Responses record expected modality `fundus`, explicitly mark modality unverified, return zero confidence/inconclusive and do not schedule a medical rescan or prescribe treatment. Image decode/size checks and private access still apply. The confirmation does not automatically prove that the uploaded image is fundus.

## Research acquisition

The existing [eye dataset review](EYE_DATASET_REVIEW.md) remains accurate for **external-eye** phone tasks. Fundus sources are now candidates for a separate retinal research task:

- `gunavenkatdoddi/eye-diseases-classification`, pinned v1: normal/cataract/glaucoma/diabetic-retinopathy aggregated retinal photos. Registered in `training/acquire_medical_research.py` as `retina_eye_classification` for quarantined acquisition.
- ODIR5K, pinned v2: paired fundus images and diagnostic keywords; patient-level/multilabel handling is needed. Original license remains unspecified in the mirror.
- `jr2ngb/cataractdataset`, pinned v2: inventory shows two matching copies of 601 retina images. Do not count both copies or merge them into independently acquired train/test partitions.

These **full retinal archives have not yet been downloaded or trained**. The registered acquisition command is `.venv/Scripts/python.exe training/acquire_medical_research.py --dataset retina_eye_classification` from `ai-server`. It keeps source/version/hash/duplicate audits and never enables clinical deployment. Original image permissions, patient/source grouping, class definition review, cross-source deduplication, calibration and independent evaluation must precede clinical use.

Delivered scope is the upload/history workflow and safe endpoint integration. Disease classification, automatic fundus-modality rejection, retinal ROI/quality models and independently validated clinical predictions remain outstanding. Physical iPhone QA remains pending.

Validation: 18 backend tests and 35 AI tests pass. A backend transport test verifies the separate retina route, multipart image content and inconclusive response. AI tests verify expected fundus modality remains unverified. Mobile typecheck, changed-file lint and iOS production bundle export pass. The backend retains the existing NU1603 JWT dependency warning.
