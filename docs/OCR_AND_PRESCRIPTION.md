# Printed document OCR and prescription reference review

Implemented 2 October 2026. OCR extracts printed English text; it does not recognize a prescription as clinically appropriate. Handwritten prescriptions, Urdu handwriting, dose correctness, combined interactions, counterfeit detection and Pakistan product registration are not verified.

## App workflow

Open Medication → Box text or Prescription → take/choose a photo. Review the original, approve server processing, then extract text. Enter the exact medicine names separately from the OCR output. Confirm names, strength and form before lookup/save. OCR output is never automatically converted into a medication list. Failed/empty OCR allows manual entry. Prescription photos, confirmed names and raw OCR are saved only after confirmation; standalone OCR uploads are not permanently saved.

The local Windows host uses the installed `Windows.Media.Ocr` English recognizer as an offline fallback. Its API does not return per-line confidence: this field is null, and every line requires review. A synthetic label containing “PARACETAMOL”, “500 mg TABLETS” and “MEDISCAN TEST LABEL” was extracted through the authenticated .NET gateway. This is a plumbing check, not a real-world OCR accuracy study. Native iPhone camera behavior still needs physical device testing.

For Linux/container deployments, install the pinned EasyOCR dependency and explicitly fetch its official models:

```powershell
ai-server/.venv/Scripts/python.exe -m pip install easyocr==1.7.2
ai-server/.venv/Scripts/python.exe ai-server/training/prepare_ocr.py
```

GitHub release asset downloads stalled on this network; EasyOCR weights are not prepared here. Inference never downloads models. If no local engine is ready, the API returns 503 and the app offers manual entry. Windows OCR requires the installed en-US OCR language feature and access to the process's temporary directory. Image files in temporary storage are removed after extraction. No document content is sent to a cloud OCR service.

## Reference matching

Only exact OpenFDA brand/generic matches are accepted. Broad full-text fallback and GPT prescription safety claims have been removed. A result exposes its source, retrieval time and original DailyMed label when supplied by OpenFDA. Different strengths/forms sharing the same name remain unresolved. Only explicitly formatted US NDC identifiers are looked up in the NDC source; Pakistani EAN/GTIN and arbitrary QR payloads have no verified mapping yet.

Every prescription response carries `prescriptionVerified=false` and `verificationStatus=requires_clinician_review`. Unknown names remain unknown and are retained in the user's history. Label warnings and interaction text are excerpts, not an exhaustive or patient-specific interaction check. DRAP registration needs a separate authoritative integration.

## Endpoints and protection

- `.NET POST /api/v1/documents/ocr`: authenticated multipart `image`, JPEG/PNG/WebP ≤10 MB, no-store response, audit event without raw OCR content.
- `FastAPI POST /api/v1/documents/ocr`: internal bearer API key; bounded decoding ≤20 megapixels, serial local OCR, 35-second Windows subprocess limit.
- `.NET POST /api/v1/medication/prescription`: multipart image and confirmed `notes`, `inputConfirmed=true`, optional `ocrRawText`, `fromOcr`. At most ten names. Owner-only saved photo and record access.
- `FastAPI GET /api/v1/models/status`: internal model/artifact readiness; all six clinical modules remain disabled regardless of research checkpoint metadata.

Official references: [Microsoft OCR API](https://learn.microsoft.com/en-us/uwp/api/windows.media.ocr.ocrengine.recognizeasync), [EasyOCR](https://github.com/JaidedAI/EasyOCR), [OpenFDA query syntax](https://open.fda.gov/apis/query-syntax/).
