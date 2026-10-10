# Live capture and storage — 10 October 2026

## Camera changes

CameraView no longer contains overlay children; overlays are positioned as sibling views, matching the installed Expo camera implementation. The screen waits for camera readiness, handles mount errors and denied/permanently denied permission, unmounts on background/unfocused screens, and offers a system-camera fallback. Mobile HTTP browser preview explicitly directs users to Expo Go or the system camera; browser live camera requires HTTPS/localhost.

Opt-in live mode samples compressed 640-pixel frames serially, with at least 1.2 seconds between completed requests. Frames pass through an authenticated, separately rate-limited backend route to the internal AI service. The AI service does not save them or create scan records. Local temporary probe files are deleted after each request. Clear/adequately lit and sufficiently similar consecutive frames trigger a final higher-quality capture through the normal saved-scan pipeline. This is sampled server-assisted guidance, not a 30 fps native frame processor.

Posture framing uses the existing local `ai-server/yolov8n.pt` COCO **person** detector, producing a normalized rectangle. Missing weights/dependencies, no person, multiple people and clipped boxes cannot authorize person auto-capture. Weights are not published; model/library licensing must be reviewed for commercial deployment. Other modules have a visibly labelled framing guide and development quality/stability heuristics only: no trained eye/nail/skin/wound/tongue ROI detection is claimed. A green person box establishes neither scoliosis nor any disease.

Capture thresholds and box-to-preview cover mapping need physical-device validation. Quality/stability passage does not authenticate the selected anatomy, prove adequate clinical framing or validate a diagnosis. Clinical detection, medicine suitability and automated prescriptions remain unavailable.

## Current data location

- Account/profile, scan metadata/results, medicine/prescription records and audit data: local SQLite `backend/MediScan.API/mediscan_dev.db`, selected by the configured development connection string.
- Uploaded scan/prescription photos: `backend/MediScan.API/wwwroot/uploads/`, accessed through authenticated owner-scoped media routes; not public static files.
- Research datasets and model files: ignored directories under `ai-server/datasets/` and `ai-server/models/`; separate from patient records.

Database and uploads are local to this computer, not a cloud deployment. Changing the configured database/storage provider changes these locations. The current database is excluded from Git tracking; older Git history has not been rewritten.

## Email test

The server reads a configured 16-character SMTP password without displaying it. SMTP probes failed: port 587 connect timeout/disconnect; port 465 authentication-stage disconnect. An actual API password-reset request for the existing developer account returned HTTP 503, `Email delivery failed`. A configured flag is not evidence of delivery, and no successful email arrival is claimed. Gmail account/app-password and network access still need resolution; do not paste the password in chat. Registration/reset unit tests pass with captured test mail, independently of live transport.

## Verification

33 backend and 82 AI tests pass, including authenticated preview, invalid/oversized frames, nonclinical quality results, missing/clipped/multiple-person rejection. Full AI Ruff and mobile TypeScript/ESLint pass; Android/iOS/web bundle exports completed. Capture stability checks reject motion, malformed signals and missing person verification. Actual local YOLO weights reject a blank frame and a multi-person public example; a single-person crop returns a real rectangle. Running authenticated preview returns HTTP 200; unauthenticated preview returns 401, and preview requests leave scan-row/photo counts unchanged. Physical Android/iPhone camera, focus, overlay alignment and real auto-capture still need device checks.
