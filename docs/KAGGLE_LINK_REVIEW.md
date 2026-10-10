# Five user Kaggle links — 4 October 2026

Metadata, versions and available archive inventories were checked. Image decoding/duplicate audits apply only to archives explicitly acquired below; an inventory is not an image-quality audit. No new clinical model is enabled.

| Link | Pinned version / mirror license | Result |
| --- | --- | --- |
| [Skin analysis tool](https://www.kaggle.com/datasets/abhayyadav1074/skin-disease-classification-for-skin-analysis-tool) | v1 / MIT | Member path/size/CRC inventory matches the user's existing skin ZIP. Its 2,351 relevant candidates are already retained; no duplicate download |
| [Comprehensive skin + cancer](https://www.kaggle.com/datasets/anieetorudofia/skin-diseases-cancer-comprehensive-dataset) | v8 / CC0 declaration | ZIP inventory: 13,358 image assets in 24 folders, no metadata files. Acne 619, Eczema 1,022, Tinea 947. Original source, independent patients and class definitions are not established. Image payloads not acquired or merged |
| [Balanced skin classification](https://www.kaggle.com/datasets/zyrexa303/skin-disease-classification-dataset) | v2 / Unknown | Publisher claims 27 classes × 2,000 images, explicitly using oversampling/rotation/flips/color jitter/crops. These are not 54,000 verified independent originals. Full archive not downloaded; original/augmentation family mapping and original rights remain missing |
| [Fingernail 22nd May](https://www.kaggle.com/datasets/abhinavgolla/fingernail-anemia-22ndmay) | v1 / Other, empty description | Member inventory matches the user nail ZIP; 4,260 assets already overlap Ghana nails completely. No new cohort or Hb metadata |
| [Fingernail detection](https://www.kaggle.com/datasets/abhinavgolla/fingernail-anemia-detection) | v1 / Unknown | Downloaded and audited: 9,069 images, 4,154 unique pixel images, mixed prior-source content and label conflicts; quarantined candidate view only |

## New nail mirror findings

Archive size: 79,800,765 bytes. SHA-256: `73fc493d5186ecdda728427416a2b27aaef5df9b1b6320a242064e49bacc0903`.

All 9,069 image assets decode; folder asset counts are 5,390 Anemic and 3,679 NonAnemic. There are 3,024 exact duplicate groups and 414 near-match candidate pairs, including 144 pairs with differing folder labels. Exact conflicting folder labels affect 15 assets in the reviewed view.

Exact pixel overlap includes **all 2,087 unique Ghana fingernail images and all 485 unique CP-AnemiC conjunctiva images**. Therefore the mirror's name does not describe a pure nail dataset. An overlapping CP image was inspected and is a segmented conjunctival region. No lab Hb values, patient identifiers, source license or original-versus-augmentation lineage is included.

After excluding existing pixels, whole conflicting-label groups and near-match review flags, 1,316 new pixel candidates remain: 741 source-folder Anemic and 575 NonAnemic. These are **unverified labels and body-area candidates**, not 1,316 independent patients. Counts: 6,150 quarantined assets + 1,603 redundant consistent copies + 1,316 candidates = 9,069. Transformed cross-source copies may still exist; exact comparison does not prove independence.

The ignored local directory `ai-server/datasets/kaggle/golla_fingernail_detection_v1/` retains source ZIP, pinned metadata, hash receipt, raw files, image audits, review summary and candidate manifest. Source/clinical/body-area review must precede training. All readiness flags remain false.

## Use decisions

The already acquired first skin dataset remains useful as a research candidate pool after source/label review, separately from existing train/test cohorts. Comprehensive skin data needs original attribution and patient mapping; its CC0 mirror declaration alone does not establish authority to relicense aggregated images. The balanced augmented dataset is deferred in favor of original-source cohorts with traceable patient and augmentation families. The new nail mirror is retained for provenance review, not trained as pure nail anemia.

Thirty-three AI tests pass, including bounded remote ZIP reads that reject ignored ranges, oversized/truncated bodies, conflicting duplicate labels and patient/pixel leakage. Ruff checks pass. No medicine recommendation or accuracy improvement follows from these acquisitions.
