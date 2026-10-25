# Model data and training checkpoint — 25 October 2026

Training does not require adding doctors as app users. Reference testing means comparing predictions with independently established labels, such as measured hemoglobin, rather than treating the model's own predictions as truth. This checkpoint implements research training and reference-data controls; it does not certify medical performance.

Public datasets with appropriate source labels can support research training without appointing a new app doctor. Independent validation of the resulting product, particularly for new patients/devices in Pakistan, is a separate acceptance step; a larger training set alone cannot establish it.

## New original nail/Hb source

[Yakimov et al., Figshare collection](https://figshare.com/collections/_/6760179), dataset DOI `10.6084/m9.figshare.25867432.v1`, describes nail/skin photographs from 250 patients with measured Hb and provider patient IDs. The [original article API](https://api.figshare.com/v2/articles/25867432) declares CC0, version 1. Its original `data.zip` is 91,619,743 bytes with provider MD5 `7bd86daf16c69e370173d9a7a92474b0`. This is a separate cohort; its Hb values must never be assigned to the unrelated Ghana/Kaggle photos.

`training/acquire_hb_reference.py` pins that source identity/license version, resumes bounded byte ranges, verifies the complete checksum, validates archive members before extraction, and preserves originals under ignored `datasets/original/hb_figshare_25867432/`. A partial download is not accepted as the verified archive. The source declaration is evidence of its reuse terms, not proof of clinical acceptance or all participant-level rights.

`training/train_nail_hb_research.py` checks original metadata/photo integrity and patient-to-photo mapping; converts the explicitly documented g/L source unit to g/dL; quarantines exact duplicate and near-match candidates; freezes provider-subject splits before modeling; and selects a small ridge-regression grid on validation MAE only. It saves numeric tensor state and verifies restored-model predictions. Source-supplied nail/skin boxes are required, so this experiment does not establish end-to-end phone detection. The reserved test images are not used to fit/select features or regularization; duplicate auditing may inspect all photos before splitting.

**Acquisition and training completed.** All 91,619,743 bytes match the provider checksum and pinned SHA-256 `447127bd69fba9f6ba78056732343798bfed0c4360ea538e88880f867e3897dd`. The archive has 252 files: 250 photos plus metadata/documentation; the CSV contains 250 uniquely mapped provider patient rows.

The first conservative experiment excluded all 131 near-match candidate photos, retaining 119 cases; validation MAE was 1.849 g/dL on 18 validation subjects. A second experiment grouped all 157 near-match candidate pairs into connected components instead of declaring visually similar fingers to be proven duplicates. Each component stays in one split. All previous train/validation/test assignments were preserved; a component touching multiple prior splits would be quarantined. This retained all 250 source records with 191 training, the same 18 validation and 41 reserved test records. Similarity grouping does not authenticate patient identities or establish that each candidate is/is not a duplicate.

The grouped model selected ridge alpha 10 using validation MAE **1.787 g/dL**. Frozen evaluation then consumed the 41 internal test records once: **MAE 1.538 g/dL**, RMSE **1.983 g/dL**, compared with a training-mean baseline test MAE of **2.003 g/dL**. The approximate cluster-bootstrap 95% MAE interval was **1.145–2.086 g/dL**, resampling 25 near-match groups. This remains one source/site with limited sample size and supplied boxes, not a Pakistan clinical test. This inspected test must not guide further tuning; future acceptance needs fresh external cases. [Aggregate evidence](NAIL_HB_RESEARCH_RESULTS_2026_10_25.json) joins the frozen pre-test model card and later test report without rewriting the original checkpoint/card.

The target is continuous Hb. Age and sex are withheld by the source, so this script deliberately does not invent diagnostic anemia labels or thresholds. Hb error in g/dL is not a disease classification accuracy percentage. Pakistan/device testing, independent references, calibration and unknown-condition tests remain open.

## Tongue experiments completed

| Appearance experiment | Validation balanced accuracy | Decision |
| --- | --- | --- |
| Existing whole-image feature baseline | 49.09% | Preserve as existing baseline |
| Source-polygon color/texture + regularized logistic regression | 46.65% | Does not replace baseline |
| Source-polygon color/texture + fixed ExtraTrees candidate | 42.82% | Does not replace baseline |

Both new candidates used 3,954 training and 1,108 validation images, with 552 test images reserved and not evaluated. They require source-supplied polygons, not an automated live tongue segmenter. They classify the original six provider appearance categories, not infection, deficiency or organ disease. Validation has been reused across research experiments; these are optimistic selection scores, not independent clinical accuracy. Export-family separation is not authenticated patient separation. Numeric forest state was reloaded with `weights_only=True`; restored predictions matched the original estimator on validation inputs.

The [TMC-Tongue Dryad source](https://datadryad.org/dataset/doi:10.5061/dryad.1c59zw48r) is a newly reviewed alternative candidate. Its dataset API declares CC0-1.0. The archive is about 2.34 GB and was not acquired in this checkpoint. The explicit source list has 20 indexed categories despite the abstract saying 21; it mixes appearance labels and traditional organ-related labels. It cannot be silently converted into confirmed modern disease diagnoses or assumed to have verified patient grouping. Any future intake must resolve that class map, inspect original annotations and separate unsupported medical claims.

## Reference-data checks now cover all scan families

The structural validator and empty intake templates now include skin, external eye, retinal fundus, wound segmentation and conjunctival anemia, alongside tongue, nail anemia and scoliosis. Specialist tasks require matching image hashes, modality and reference type/method/status. Wound masks must match the image, binary values and declared wound presence; segmentation masks cannot authorize centimeter measurements or healing claims. See [reference intake](REFERENCE_LABEL_INTAKE.md).

Passing these checks does not authenticate a doctor, label, consent or permission. Two synthetic reviewer IDs in a unit test are not a completed clinical review. Existing TongueDx/Scoliosis1K approvals remain unconfirmed; no additional author email was sent in this checkpoint. Restricted datasets are not unlocked by changing a software flag.

## Reproduce

From the repository root:

```powershell
ai-server/.venv/Scripts/python.exe ai-server/training/acquire_hb_reference.py
ai-server/.venv/Scripts/python.exe ai-server/training/train_nail_hb_research.py --output ai-server/models/research/<new-nail-hb-run>
ai-server/.venv/Scripts/python.exe ai-server/training/train_nail_hb_research.py --baseline-manifest ai-server/models/research/<previous-nail-hb-run>/private_manifest.json --output ai-server/models/research/<new-grouped-nail-hb-run>
ai-server/.venv/Scripts/python.exe ai-server/training/evaluate_nail_hb_research.py --run ai-server/models/research/<frozen-grouped-nail-hb-run>
ai-server/.venv/Scripts/python.exe ai-server/training/train_tongue_roi_research.py --output ai-server/models/research/<new-tongue-run>
ai-server/.venv/Scripts/python.exe ai-server/training/train_tongue_roi_research.py --classifier extra_trees --output ai-server/models/research/<new-tongue-tree-run>
```

For AI tests, run `.venv/Scripts/python.exe -m unittest discover -s tests -v` from `ai-server/`. Use new output directories; checkpoints/manifests/photos and completed patient evidence remain outside Git. No clinical inference route is enabled by these research commands.

The frozen evaluator checks checkpoint/source/metadata integrity, subject and near-group split separation, and the original provider Hb mapping before scoring. It does not fit parameters and refuses to overwrite an existing test report. These controls do not stop a human from inspecting test results and tuning a new experiment; follow the holdout protocol. No independent external clinical performance or universal 90–97% accuracy is established by this checkpoint.

Verification completed: **124 AI unit/regression tests passed** and repository AI Ruff checks passed (`E,F,W`, excluding line length). The real source archive, grouped training, safe checkpoint forward checks and frozen internal test also completed. Unit-test fixtures are synthetic and do not count as medical accuracy evidence. No backend/mobile behavior was changed in this batch.
