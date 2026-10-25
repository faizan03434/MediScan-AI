# Delivery strategy and implementation ledger — 19 October 2026

**Newest checkpoint:** [26 October reassessment](COMPLETION_AUDIT_2026_10_26.md) records **60/100 complete, 40/100 remaining** using the same rubric after original-source/reference training and operator/TLS work. The 65 target is not yet reached. See [operator runbook](OPERATIONS_RUNBOOK.md). Earlier checkpoints below are preserved as history.

**Latest checkpoint:** [account deletion and readiness](ACCOUNT_DELETION_AND_READINESS.md) adds re-authenticated live-account cleanup, durable recovery/receipts, upload inventory and dependency readiness. 66 backend and 87 AI tests pass, plus mobile checks, web export and a running synthetic-account deletion check. Updated engineering estimate: **51/100 complete, 49/100 remaining**. Against the table below, records/privacy advances from 12 to 13 and release operations from 3 to 4; all other scores remain unchanged. Backup/restore erasure and deployed/clinical evidence remain open. The earlier 49/100 checkpoint is preserved below.

The full medical product has six work streams. Build in dependency order, with a runnable checkpoint and evidence for each change. Clinical approval is a separate evidence requirement; changing UI or a readiness flag cannot finish it. [The original 45/100 assessment](COMPLETION_AUDIT_2026_10_19.md) is the baseline. After this checkpoint the same manually weighted engineering estimate is **49/100 complete, 51/100 remaining**, not measured model accuracy or remaining calendar time.

| Deliverable | Weight | Current earned | Change from baseline |
| --- | ---: | ---: | --- |
| Mobile/capture | 20 | 16 | 0; physical-device QA remains open |
| Account access | 10 | 7 | +1 for tested persistent OTP; live email/Google still incomplete |
| Records/privacy | 15 | 12 | +2 for owner exports/session controls and tested opt-in deleted-record cleanup |
| Data/model research | 20 | 11 | 0; no new training evidence |
| Clinical acceptance | 25 | 0 | 0; no independent clinical validation completed |
| Release operations | 10 | 3 | +1 for persistent storage/key configuration and build-context exclusions; deployed verification remains open |
| **Total** | **100** | **49** | **+4; 51 remaining** |

## Checkpoint implemented now

1. **Persistent OTP:** encrypted challenges/pending registration data, hashed account scopes and keyed digests in a local SQLite store; atomic send/failure budgets and single-use consumption across workers. Restarts preserve the store and Data Protection keys. Eight added tests cover recovery, cooldowns, resends, expiry, cancellation, concurrent issue/consume and wrong-key failure. Existing production instances using the former memory store lose outstanding challenges when switching; request new codes once.
2. **Account data controls:** profile navigation to My Data & Sessions; paginated, owner-only text exports for profile/scans/medications/prescriptions/patient consents. No passwords, stamps, tokens, photo bytes or internal blob paths. Web downloads JSON; native uses the text share sheet, with a 1-million-character source-data limit. Larger exports require further server tooling. Export is not a transactional snapshot while records are changing.
3. **All-device sign out:** rotates the security stamp and revokes owner refresh tokens in a database transaction, with a minimal audit event. Current access tokens fail the existing per-request stamp check; unrelated users remain signed in. Session-rotation races under production load still need review.
4. **Deleted-record cleanup:** opt-in worker removes soft-deleted records and their last photo reference. Storage failures keep rows for idempotent retries. Shared photos stay while another record references them. It handles scan/medication/prescription rows in batches and writes minimal purge audit events. It is **off by default** and was tested on synthetic fixtures only. It is not a full account deletion or backup erasure workflow.
5. **Deployment groundwork:** persistent auth/upload volumes, writable non-root container directories, encrypted Data Protection keys on Windows or configured certificate outside development on other platforms; nonzero startup failure exit code. Backend/AI Docker build contexts exclude secrets, keys, patient databases/uploads and large dataset/model files. Weights must be mounted separately. Docker is unavailable locally, so container builds/volume ownership still require CI/deployed verification.
6. **Email deadline:** asynchronous SMTP now has a cancellation deadline. A real 19 October password-reset attempt returned 503; a separate authentication transport probe ended with `SMTPServerDisconnected`, without printing credentials. Delivery is still unresolved.
7. **Preview network recovery:** fixed a stale Expo bundle host after the computer changed network address. The preview script verifies the manifest, restarts only this project's verified Expo listener when needed and regenerates the current-address QR. The running iOS manifest now advertises `192.168.1.215`, verified locally; no physical-device success is claimed.

Verification: **54 backend tests passed**, mobile TypeScript/ESLint passed, fresh web bundle exported. Running local demo API checks passed for account export, expired sessions after all-device sign out, fresh login and unaffected other account. The six-module synthetic upload/privacy smoke check also passed and deleted its fixtures. No disease model was retrained or clinically approved in this checkpoint.

## Remaining work in order

| Stream | Next concrete deliverable | Completion evidence |
| --- | --- | --- |
| Account access | Resolve SMTP account/network delivery, configure actual Google OAuth IDs; central OTP store for multiple hosts | Delivered/verified email, real Google sign-in on signed Android/iOS/web, restart/multi-host abuse testing |
| Privacy lifecycle | Retention decision, backup expiry/restore reconciliation and data subject operations; live account deletion now implemented | Backup-aware erasure/restore drill and production failure/load tests |
| Release infrastructure | HTTPS deployment, migration/role provisioning, monitoring and secret management; dependency readiness now implemented | Successful clean deployment, restart and restore drills; no demo credentials in production |
| Mobile/device QA | Signed builds and real-device camera focus, permissions, rectangle alignment, auto-capture and failure recovery | Android and iPhone acceptance checklist with device/version evidence |
| Data/model research | Resolve rights, actual modality/labels, subject mapping; improve weak models using reserved selection data | Reproducible manifests/checkpoints, no cross-subject split leakage, task-specific results; untouched external test |
| Clinical acceptance | Clinical lead, verified reference labels, separate Pakistan cohort, calibration and unfamiliar-condition evaluation | Per-task acceptance report with independent subjects and uncertainty; enable only accepted tasks |

Software streams can progress while dataset access/clinical review is pending. Repeated or augmented images cannot replace independent subjects. No universal 97% result or completion date is promised.

## Operating the cleanup worker

`DataRetention__DeletedRecordPurgeEnabled=true` opts into irreversible cleanup of existing `IsDeleted` records and their last referenced photos, starting at worker startup and then every five minutes. Leave it absent/false until the operator has established the appropriate retention policy. This checkpoint did not enable it for the existing development database. Each pass considers up to 50 rows per type; repeated failures are retained and logged by category. Monitor failures and capacity rather than assuming one pass completes all cleanup. Backups and cloud object version history require separate expiry controls.

Removing a row/file is not a secure wipe of disks, WAL/free pages, provider versions or previous backups. Pending verification payloads expire after ten minutes and are pruned as expired account windows are processed on subsequent issuance; old encrypted bytes can persist in SQLite pages/backups. Treat the auth database and key ring as private operational data.

## Configuration and local verification

All `.auth`, database, upload and key files stay outside Git/build contexts. For containers, retain both the auth volume and the matching encryption certificate/key material; retaining only one prevents challenge recovery. Do not put the SQLite auth database on a network filesystem or give different hosts independent copies and call them shared limits. Windows DPAPI recovery also depends on the operating-system user/key protection context.

Run `infrastructure/smoke_account_controls.py` only against local demo accounts: it revokes seeded patient sessions and exports data without printing it. `infrastructure/smoke_preview.py` creates six synthetic uploads, verifies privacy/metadata handling and deletes the generated records. Physical phone behavior and production/cloud operation are not covered by these checks.
