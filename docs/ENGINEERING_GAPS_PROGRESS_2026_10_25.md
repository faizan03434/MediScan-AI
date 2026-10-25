# Remaining-gap implementation checkpoint — 25 October 2026

This checkpoint closes specific engineering gaps. It does not establish clinical acceptance, permission approval, a production deployment, or a new percentage of product completion. The previous weighted audit remains historical; a fresh full acceptance audit is needed before changing its score.

## Implemented

- Backend release policy now independently prevents every current scan task from returning an unvalidated diagnosis, treatment, healing comparison, confidence percentage or automatic clinical follow-up date. An upstream `clinical_inference` flag or an injected inference service cannot enable diagnosis. New records store unassessed confidence as null. Historical scan displays receive the same safe policy without rewriting their source database fields. Scan-triggered LLM treatment advice has been removed from this path.
- Image-service metadata is bounded to 64 KiB, including streaming responses without Content-Length, with a 45-second deadline, JSON depth and field/type/task checks. Authorization is attached per request; responses, request content and controller upload streams are disposed.
- Failed scan audit records use generic error codes. Unexpected API exceptions log exception type and trace ID without their message/body. Request logging now wraps the exception boundary so handled failures do not expose upstream exception payloads through Serilog. Aborted client requests do not generate misleading internal-error responses. A success-audit failure no longer changes a persisted completed scan to failed. This is targeted hardening, not a claim that every deployment log has been independently audited.
- Native protected navigation now covers private scan/record/profile/doctor modals and removes their navigation history when authentication ends. A route-inventory test checks that private screens are protected. OS scan notifications contain generic text without condition names, recommendations or scan IDs. Scheduled and presented scan reminders are cleared on session end, old-format reminders are removed at startup, and serial operations/session checks cover account-switch races. Physical OS behavior still needs device acceptance testing.
- Added an operator-only initial administrator command. It requires separately verified email ownership, a strong private password, initialized roles and no existing administrator/account at that address. It uses maintenance/account locks and transactional Identity role creation. No public bootstrap endpoint or default production credentials were added. See [operator instructions](OPERATIONS_RUNBOOK.md).
- Added a repeatable synthetic Production-mode HTTPS/admin/readiness drill with isolated certificate trust, no real patient data and no system certificate-store changes.

## Verification completed

| Check | Observed result |
| --- | --- |
| Backend Release tests, disposable PostgreSQL enabled | 110 passed, 0 failed, 0 skipped |
| Current API builds | Release and Debug builds passed, 0 warnings/errors |
| Mobile privacy/navigation/session regression checks | Passed |
| Mobile capture stability/contradictory evidence checks | Passed |
| Mobile TypeScript and lint | Passed |
| Expo web production export | Passed; ignored `.preview/mobile-web-release-boundary/` |
| Synthetic Production HTTPS drill | Passed |
| Python lint for the new TLS smoke command | Passed |

The HTTPS drill observed zero bootstrap demo users, three roles, rejected unverified/repeated admin creation, authenticated admin login/access, anonymous admin rejection, verified TLS hostname/certificate and a 503 readiness response for the intentionally missing image dependency. Clinical inference remained false. This is local Production-mode evidence, not public cloud or phone acceptance.

## Still requires external evidence or configuration

| Gap | Current status / next requirement |
| --- | --- |
| Diagnostic labels and clinical performance | Clinician-reviewed labels, real subject grouping, independent Pakistan/device cohorts, calibration and unfamiliar-condition evaluation remain necessary. No universal 90% or 97% diagnostic accuracy is established. |
| Tongue | Original appearance classes recovered and research pilot trained; color/appearance classes do not establish disease. TongueDx permissions and clinical reference labels remain open. |
| Fingernail anemia | Original archive verified against mirror; it contains no Hb spreadsheet or patient mapping. Conflicting/unresolved names remain excluded rather than treated as verified clinical labels. Obtain paired clinical Hb/date/subject references. |
| Scoliosis | Standard source terms are institutional/noncommercial. Independent-developer commercial eligibility/exception remains unconfirmed. Posture research is not a scoliosis diagnostic substitute. |
| Permission email | The authorized Scoliosis1K inquiry previously ended with delivery unconfirmed. No additional inquiry was sent this checkpoint. Read-only TCP checks to smtp.gmail.com ports 587 and 465 both timed out before authentication; receipt/approval cannot be claimed. Avoid duplicate resends until delivery status is resolved. |
| SMTP / OTP | Real outbound transport and end-to-end delivery remain unverified. The connection timeout does not prove the supplied password is incorrect. |
| Google login | Real OAuth Web/iOS configuration and provider/device acceptance are still required; SMTP credentials cannot supply OAuth client IDs. |
| Mobile / deployment | Physical Android/iPhone camera, background/session/notification tests, signed releases, public trusted HTTPS, provider-native cloud restore and operational alert/secret-rotation drills remain pending. |

All seven current scan task types remain clinically disabled. Camera/upload/history workflows and research training are separate from accepted medical diagnosis. The dataset provenance and reference-label intake work is recorded in [label/permission progress](LABEL_PERMISSION_PROGRESS_2026_10_25.md); do not use this checkpoint to claim missing permissions or clinician review have been obtained.
