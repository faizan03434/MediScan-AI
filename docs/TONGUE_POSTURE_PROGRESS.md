# Tongue and posture — 10 October 2026

**25 October update:** [Label/permission progress](LABEL_PERMISSION_PROGRESS_2026_10_25.md) records the recovered six-class tongue appearance map, audited 5,614-image research cohort and completed 49.09% validation pilot. The original fingernail archive is now checksum-verified and all 4,260 mirror files match. Scoliosis1K inquiry sending was authorized and attempted, but SMTP delivery was not confirmed. Clinical labels, verified subject mapping and required written exceptions remain open. The entries below preserve the earlier checkpoint.

Applicant details supplied by the owner: Muhammad Faizan, independent developer in Pakistan, contact iamfaizan884@gmail.com. No institutional affiliation has been claimed.

## Tongue

- TongueDx eligibility/separate-commercial-permission inquiry submitted through the authors' [request form](https://forms.gle/GJfuYKZwjYTRUdJH6). Google Forms confirmed “Your response has been recorded”. This is a submitted inquiry, not access approval. The noncommercial-only license answer was **No**, with the intended product use explained and a separate permission review requested. No agreement was accepted. Human oversight/uncertainty answer was **Yes**.
- [Zenodo tongue-coating record 20970467](https://zenodo.org/records/20970467): open, CC BY 4.0, pinned `images.zip` 130,365,716 bytes, provider MD5 `6f2e6d716376e3f5f92671a66f82435b`. Download in progress. Acquisition verifies size/checksum before extraction; permission metadata does not establish clinically verified diagnosis labels. The description only supports coating-detection research; annotation presence and provenance must be audited from the full files.
- [Dryad TMC-Tongue](https://datadryad.org/dataset/doi:10.5061/dryad.1c59zw48r): original-author deposit with 2.34 GB ZIP and source SHA-256. Metadata/files inventory acquired. [Dryad terms](https://datadryad.org/terms) describe CC0 dataset reuse, but actual downloads return HTTP 401 through the API and 403 via the public file link. No authentication or restrictions were bypassed. Source labels describe TCM appearance/morphology; they cannot be converted into modern anemia/B12/infection diagnoses.

## Posture

- [MultiPosture original record 14230872](https://zenodo.org/records/14230872): open CC BY 4.0; describes 13 participants and 4,800 manually labelled sitting frames. Full CSV acquired: 9,327,935 bytes, provider MD5 `7efbc94d653acf32eefecec3ff26d6c6` verified. Actual audit finds **4,794 rows / 13 subjects**, rather than the description's rounded 4,800. Full source SHA-256 and separate receipt saved locally.
- Actual CSV header exposes **99 coordinates (33 joints ×3)** rather than the description's 33-coordinate subset. The new intake checks this actual schema, finite coordinates, supported upper/lower sitting labels, nonempty provider subject IDs and exact cross-split feature overlap. Splits are deterministic by provider subject, never by individual frame.
- The new two-head MLP completed **50 epochs** with real upper/lower labels, train-only standardization, weighted loss and validation checkpoint selection. Provider-subject partitions are **7 train / 2 validation / 4 test**, with 2,094 / 930 / 1,770 frames. Reserved test evaluated once: **upper-body balanced accuracy 90.18%; lower-body 87.52%**. Correlated test frames do not count as 1,770 independent patients. No synthetic data or scoliosis labels used. [Complete result](SITTING_POSTURE_RESULTS.json), [intake counts](SITTING_POSTURE_INTAKE.json).
- [Scoliosis1K](https://zhouzi180.github.io/Scoliosis1K/) still requires a signed institutional academic-use agreement. Independent developer details do not satisfy that institutional procedure automatically. No agreement is signed and no restricted archive is decrypted. The personalized [eligibility/commercial-permission email draft](SCOLIOSIS_PERMISSION_REQUEST.eml) is ready; no connected email sender is currently available, so it has not been sent.

## Reproducible commands

From `ai-server`:

```powershell
.venv/Scripts/python.exe training/acquire_tongue_posture_open.py --source tongue_coating
.venv/Scripts/python.exe training/acquire_tongue_posture_open.py --source sitting_posture
.venv/Scripts/python.exe training/prepare_sitting_posture.py
.venv/Scripts/python.exe training/train_sitting_posture_research.py
```

Default direct execution of the old tongue/posture trainers is now blocked. Explicit `--legacy-unvalidated` is required for those legacy experiments. Old tongue aliases no longer treat folders named anemia/thrush as interchangeable with pale/white appearance. Clinical inference remains disabled until appropriate labels, independent evaluation and clinical review exist. A dataset license or model score alone cannot authorize disease diagnosis.

Verification: ten targeted source-license, pinned identity, resume-integrity, subject-separation and model-readiness tests pass; changed research Python files pass Ruff and legacy edits compile. The selected sitting-posture checkpoint SHA-256, saved normalization and finite 5/7-class forward outputs were rechecked after training.
