# Label and permission gap work — 25 October 2026

**The technical tongue class-map gap is resolved. Clinical ground-truth and external written-permission gaps are not all resolved.** No permission, patient identity, diagnosis or clinical release is inferred from an email attempt, source filename, successful parser or test result.

## Tongue

The checksum-verified original [Zenodo archive](https://zenodo.org/records/20970467) contains `images/data.yaml`. The earlier extracted-image inventory missed this file. Its source mapping is:

| Source class ID | Exact provider label | Appearance gloss |
| --- | --- | --- |
| 0 | abu abu | grey |
| 1 | hitam | black |
| 2 | kuning | yellow |
| 3 | normal | provider normal appearance; not a confirmed healthy diagnosis |
| 4 | putih | white |
| 5 | ungu | purple |

The original archive SHA-256 is `acfead7112b7cb6e506028f74dead326b1c0ce31f598c67b5675ccfb09cf56d7`; the class-map file SHA-256 is `e0256128e9be4a0a5cd82e0faa784c75a2c1bdf88f0e0ba2e03af9af7b56d485`. The archive/YAML declare CC BY 4.0. That declaration does not establish clinical labels, patient consent review or downstream product acceptance.

Audit found **5,803 images**, **5,804 polygon instances and one box instance**, no invalid coordinate rows, no missing image pairs and no exact-file cross-split duplicates. The appearance preparation separately quarantines mixed/ambiguous geometry, cross-split/hash/export-family conflicts and near-duplicate concerns. The retained **5,614 images** split into **3,954 train / 1,108 validation / 552 test**; 189 images/annotations are quarantined. Retained counts are white 1,899; yellow 995; grey 715; black 110; normal 1,534; purple 361. The private manifest retains exact original source labels and hashes.

This supports **appearance research only**. It supplies no confirmed thrush, infection, B12 deficiency, anemia or organ-disease ground truth. Duplicate/export-family grouping is not verified patient identity. The first frozen-MobileNet/color-feature experiment completed with **49.09% validation balanced accuracy** on 1,108 validation images; the selected representation was color descriptors. All 552 test images remain unevaluated by this model. The score is validation-selected, not independent clinical performance. No model was enabled for diagnosis.

[TongueDx](https://github.com/tonguedx/tonguedx) still states academic/noncommercial-only conditions. The earlier independent-developer/commercial-exception inquiry is recorded as submitted; no author approval is available in project evidence. No restricted access or commercial exception is assumed.

## Fingernail anemia

The [original author deposit](https://data.mendeley.com/datasets/2xx4j3kjg2/1) declares CC BY 4.0 and describes laboratory-derived categories in young children. Its public file inventory identifies `Fingernails.rar`, 27,451,390 bytes, SHA-256 `641ef99dd2b343eb00d0fc71b5062ba0a903046228440ab6b6311f81b0dc59ed`. The original archive is now fully downloaded and checksum-verified. All **4,260 original/mirror image files match byte-for-byte**, with zero mismatches. This resolves original/mirror image provenance and confirms the source's license declaration; it does not establish clinical truth or blanket product approval. The original archive contains images only: no Hb spreadsheet or patient-mapping file was found.

The local mirror has 4,260 assets but only **2,087 unique decoded images**. Filename audit recovers **2,487 Anemic** and **113 Non-anemic** source-category candidates. **1,660 remain unresolved**: 1,581 use `Non-Anrmic`, and 79 have other unsupported spelling/suffix patterns. These are quarantined rather than silently normalized. The parser conservatively identifies 492 filename/augmentation families; they are **not** 492 verified patients. No exact-pixel conflict was found among the explicitly recovered categories; that does not settle the unresolved categories or clinical truth.

Remaining: obtain provider clarification of naming aliases, independently map views to subjects, and obtain authoritative image-to-Hb/reference metadata and appropriate clinical label review. Original source descriptions do not justify copying conjunctival Hb rows onto nail filenames. No fingernail diagnostic model is trained on guessed Hb values or unknown labels.

## Scoliosis

The current [Scoliosis1K procedure](https://zhouzi180.github.io/Scoliosis1K/) and [release agreement](https://zhouzi180.github.io/Scoliosis1K/static/resources/Scoliosis1k_release_agreement.pdf) require institutional academic-use authorization; the standard terms prohibit commercial use. Independent-developer eligibility and a separate commercial exception require a real author response. No agreement was signed, institutional affiliation invented, archive decrypted or restricted data used.

The owner explicitly authorized sending the prepared eligibility/commercial-permission inquiry to the published contact. **One SMTP attempt returned `SMTPServerDisconnected`; delivery was not confirmed.** A private receipt is retained under `.preview/permission_requests/`. No automatic duplicate was sent because the delivery stage is unconfirmed. Email delivery is not dataset approval even if later confirmed. The original `.eml` remains available locally for manual submission after checking delivery/account status.

An alternative [paired phone-photo study](https://pmc.ncbi.nlm.nih.gov/articles/PMC11592223/) states that data are available on request; its photographs are not an unrestricted downloadable commercial source. The open [Jordan radiograph dataset](https://data.mendeley.com/datasets/xkt857dsxk/1) has a different modality and was not substituted for ordinary camera labels. Existing sitting-pose performance remains sitting-pose research, not scoliosis diagnosis.

## Implemented intake and evidence controls

- `audit_missing_labels.py`: checks the original tongue archive/class mapping/annotation geometry and nail image hashes/provider filename candidates; exports aggregate evidence without patient images.
- `prepare_tongue_appearance.py`: immutable source-labelled appearance manifest, preserved provider splits, hash/pixel/export-family checks and cross-split near-duplicate quarantine. It never maps appearance to disease.
- `train_feature_research.py --task tongue_appearance`: the audited appearance manifest is explicitly required; test image bytes are excluded from model selection and clinical flags remain false.
- `acquire_original_nails.py`: bounded parallel byte-range acquisition, immutable expected original digest and final whole-file verification. Download progress is not clinical permission.
- [Reference-label intake guide](REFERENCE_LABEL_INTAKE.md) and five empty templates cover tongue appearance/disease, nail laboratory reference, phone scoliosis screening and paired radiographic reference. Pending permission, uncovered intended use, invalid evidence hashes, subject leakage, wrong modality, missing Hb context and unsupported appearance-to-disease conversion are rejected. Passing structure checks does not authenticate reviewers, prove consent, interpret legal rights or approve a model.

See [aggregate label audit](LABEL_GAP_AUDIT_2026_10_25.json) and [permission evidence status](DATASET_PERMISSION_STATUS_2026_10_25.json). These replace vague “labels missing” notes with the exact recoverable information, excluded data and outstanding decisions. No diagnostic task is enabled by this checkpoint.

Verification: **108 AI unittest checks passed**, including label-map parsing, ambiguous filename handling, annotation geometry, archive path safety, subject/hash separation, evidence integrity, reviewer-reference requirements, and modality/label scope. Full-tree Ruff E/F/W checks passed. The tongue checkpoint's hash and actual training-sample load/forward check passed with six uncalibrated appearance scores and `diagnosis: null`. No new clinical test accuracy is claimed.

Reproduce from `ai-server` using the private downloaded source evidence and new immutable destinations where needed:

```text
python training/acquire_original_nails.py
python training/compare_original_nails.py
python training/audit_missing_labels.py
python training/prepare_tongue_appearance.py
python training/train_feature_research.py --task tongue_appearance --output models/research/<new-run>
python training/clinical_label_contracts.py --manifest <private-reference-manifest> --evidence-root <private-evidence-root>
```

The existing appearance manifest is immutable and its preparation command refuses to overwrite it. Original RAR comparison uses the inspected BSD-tar listing format available on this Windows host and rejects unsupported readers/layouts. Raw archives, extracted photos, source-page state, individual metadata, reference evidence, SMTP secrets and delivery receipts are excluded from this publication.
