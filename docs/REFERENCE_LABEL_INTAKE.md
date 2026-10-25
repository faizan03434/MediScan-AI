# Clinical reference intake

The validator in `ai-server/training/clinical_label_contracts.py` checks supplied record structure, evidence-file hashes and subject/split separation. It does **not** authenticate a clinician, prove consent or legal authority, establish ground truth, or authorize clinical release. Empty templates deliberately fail validation until real evidence and records are supplied.

Use the templates in [reference_label_templates](reference_label_templates). Keep completed manifests, consent/privacy reviews, lab/radiology reports and reviewer identity mappings in restricted storage outside Git. The existing `ai-server/datasets/` and `.preview/` trees are ignored; do not put patient evidence in `docs/`. Use project-specific hashed/pseudonymized subject keys, not patient names, emails, phone numbers or hospital record numbers. Actual identity verification, ethics/privacy approval and clinician review require appropriate people and systems.

Every dataset needs its task/modality, intended use, reviewed source terms or actual written permission, a clinician annotation protocol, a documented data-use basis and a privacy review. Evidence paths are relative to a private evidence root and must have matching SHA-256 digests. A submitted request, an email draft or a software license for an unrelated repository is not dataset permission. The intended commercial/research use must be explicitly covered by the supplied reviewed evidence; the validator cannot interpret legal scope on its own.

Every record needs `subject_pseudonym` and `image_sha256` as 64-character hexadecimal identifiers, an explicit split, matching modality, `review_status: adjudicated`, two distinct reviewer references and a reference evidence file/hash. All visits and views of a subject stay in one split. An export filename/folder or duplicated image does not establish a real independent patient.

| Template/task | Required reference | Labels and limits |
| --- | --- | --- |
| `tongue_appearance` | Reviewed appearance annotations | Boolean `pale`, `tip_side_red`, `red_spots`, `ecchymosis`, `cracks`, `tooth_marks`, `thick_coating`, `yellow_coating`; no appearance-to-organ/disease conversion |
| `tongue_disease` | Separate clinician diagnostic report | Clinician-provided `clinical_label`; clinical protocol must specify supporting examination/tests and uncertainty. A color/coating label is insufficient. |
| `fingernail_anemia` | `laboratory_hb_report` | Actual finite `hb_g_dl`, `hb_unit: g/dL`, age in months, timezone-aware capture/reference dates, protocol-reviewed timing and clinician label `anemic`, `non_anemic` or `indeterminate`. The validator does not assign diagnostic Hb cutoffs. |
| `scoliosis_phone_screening` | `clinician_screening` | Back-photo modality; `screen_positive`, `screen_negative` or `indeterminate`. These are screening outcomes, not radiographically confirmed diagnoses. |
| `scoliosis_radiographic_reference` | `radiologist_report` paired to back photo | Actual reported Cobb angle as a reference; no guessed value from a camera photo. This is a back-photo research cohort with a radiologist reference, not a radiograph-only model. The clinical protocol defines interpretation/timing. |

For nail records, use `reference_kind`, `hb_g_dl`, `hb_unit`, `clinical_label`, `age_months`, `captured_at`, `reference_at` and `timing_reviewed_under_protocol`. Dates must include timezone information; checking a flag is not independent proof that review occurred. Reviewer references must be checked against a real clinician credential/assignment registry outside this structural validator. Controlled terminology, reviewer agreement, adjudication and label versioning must be owned by the clinical team.

The eight reviewer attributes in this intake are a different schema from the recovered six source-color categories. The research manifest keeps those original six categories verbatim. Neither white color nor the provider's normal category is automatically converted into a thick-coating, deficiency or confirmed-healthy reference label.

```text
python training/clinical_label_contracts.py --manifest <private-manifest.json> --evidence-root <private-directory> --output <new-aggregate-report.json>
```

Output contains aggregate validation counts and permanently false `clinical_approved`/`deployment_authorized` values. Passing this intake does not switch on a model. Independent calibration, unfamiliar-condition rejection, reserved external patient/device/site evaluation and clinical acceptance remain separate requirements.
