# Integration verification — 10 October 2026

Published integration targets Android, iPhone and browser development previews. It includes email login, verified registration/reset OTP, Google identity/linking, light UI, camera/gallery, protected images, OCR confirmation and research tools. Native Google OAuth still requires configured clients and signed custom builds; real SMTP delivery awaits the developer's Gmail app password.

Completed local checks:

- 33 backend tests passed (including auth/reset, OTP budgets, storage paths and server dotenv).
- 78 AI tests passed; full-source Ruff passed.
- Mobile TypeScript and ESLint passed without reported errors or warnings after cleanup.
- Expo exports completed for Android, iOS and web. These are JS/Hermes bundles, not signed APK/IPA builds or physical-device validation.
- Running API health and Android/iPhone handoff page passed. Six synthetic capture workflows, saved history, owner-only photos, invalid captures, comparison isolation and deleted-photo access passed the integration smoke check.
- Staged secret-pattern/private-artifact checks passed. The local database was removed from tracking while preserved on disk; older Git history was not rewritten. Current SMTP secrets, uploads, model weights, datasets and access correspondence are excluded.

Server settings: edit `backend/MediScan.API/.env`, set `Email__Smtp__Password`, and restart the API. See [auth setup](AUTH_SETUP.md) and [mobile preview](MOBILE_PREVIEW.md). CI now runs on `codex/**` branches, but local results do not establish remote CI results or pinned production dependency compatibility. The existing NU1603 JWT resolution warning remains.

Clinical inference remains unavailable. Clinician label review, independent Pakistan testing, real-model calibration, unfamiliar-condition validation, production shared OTP storage, retained-photo metadata sanitization, encryption and operational retention remain unfinished. Raw training artifacts and private/local reports have not been published with source.
