# Operations and session checkpoint — 19 October 2026

Engineering estimate: **57/100 complete, 43/100 remaining**. The requested 65/100 milestone has **not** been reached. These are manually weighted delivery estimates using the existing rubric, not model accuracy, clinical approval or a timetable.

| Deliverable | Weight | Previous | Current | Evidence for change |
| --- | ---: | ---: | ---: | --- |
| Mobile/capture | 20 | 16 | 17 | Tested account-switch/logout isolation, stale-result rejection, refresh recovery and preview readiness; physical phone acceptance still missing |
| Account access | 10 | 7 | 8 | Central PostgreSQL OTP and cross-instance budgets; atomic refresh rotation and admin/session invalidation tested on actual PostgreSQL |
| Records/privacy | 15 | 13 | 14 | Signed deletion intents retained separately, startup recovery and deletion-aware encrypted restore tested |
| Data/model research | 20 | 11 | 11 | No new model training or independently verified labels completed |
| Clinical acceptance | 25 | 0 | 0 | No independent clinical acceptance completed |
| Release operations | 10 | 4 | 7 | Provider-specific migrations, clean role/bootstrap command, operator backup CLI/drill, production configuration checks and dependency remediation |
| **Total** | **100** | **51** | **57** | **+6; 43 remaining** |

## Implemented and verified

- Separate PostgreSQL migration assembly for a **fresh** production database. Explicit provider selection preserves SQLite connection options and prevents accidental selection based on `.db` inside a PostgreSQL password/database name. Docker Compose now explicitly selects PostgreSQL. Production bootstrap provisions only User/Doctor/Admin roles and the deletion ledger, with no demo users.
- PostgreSQL OTP uses encrypted payloads and transaction advisory locking. Send/failure/resend budgets and single-use codes survive API restarts and coordinate across API instances sharing the database and protection keyring. This does not make the local deletion ledger or local uploads a multi-host storage system.
- Refresh bearer values are now stored as SHA-256 digests and bound to the account security stamp. Concurrent refresh consumes the old token once. Password/all-device logout, account deletion and admin role/status changes invalidate old sessions. Both provider migrations delete legacy plaintext refresh rows; users must sign in again after upgrading.
- Admin role/status mutations are transactional, check Identity results, recheck the acting admin after acquiring a cross-process database lock and protect the last active administrator. Pending-deletion accounts cannot be reactivated. Account deletion shares this membership lock.
- Mobile token writes are serialized. Refresh cannot resurrect a logged-out session or replace/clear a newer account. Failed refresh clears auth state. Account changes clear scan/prescription/medication stores; late requests from the former account are discarded. Existing root query-cache cleanup is triggered by auth changes. Tests use mocked storage/transport; native secure storage behavior still needs physical-device QA.
- Signed deletion ledger stores subject-ID hashes and timestamps, with its signing key protected by the application keyring. A verified deletion intent is recorded before the main deletion transaction commits. Startup/worker recovery reconstructs missing cleanup jobs before the API serves requests.
- Offline SQLite archives encrypt the database, optional OTP database, default keyring, local uploads and configuration copies. Restore authenticates the complete ciphertext before extraction, rejects unsafe/duplicate/oversized paths, checks the current ledger, reapplies newer deletions and invalidates all restored refresh tokens, security stamps and OTP challenges. Restored configuration is quarantined for review. Shared image references are preserved.
- API runtime and maintenance commands use a same-host file lease. Active API workers block backup/restore. Restore publishes to a new directory only after cleanup and SQLite integrity verification; existing source data is untouched.
- Production startup rejects development signing/internal-service keys, overly long access-token lifetimes, wildcard hosts and non-HTTPS/path-bearing browser origins. This is configuration validation, not a deployed security assessment.
- Removed unused AutoMapper integration and upgraded the native SQLite binary. An official NuGet source audit reported no known vulnerable API dependencies at this checkpoint; the loaded SQLite version is also tested. This is not a general security certification.
- Preview QR generation now waits for API/AI dependency readiness and a manifest advertising the current LAN address. Docker CI now tests actual container liveness and cleans up the test container; its remote result must be checked after pushing.

## Verification evidence

- Backend solution build: **0 warnings, 0 errors**.
- **95 backend tests passed, none skipped**, including actual PostgreSQL 17 migrations, OTP concurrency, 8-way refresh rotation and concurrent last-admin demotion. The private test cluster uses loopback port 55432 and disposable databases, not development patient data.
- **87 AI unittest checks passed**. No AI inference model was retrained in this checkpoint.
- Mobile TypeScript/ESLint, capture schema/stability and session concurrency/privacy checks passed. Production web export also passed; neither a bundle nor unit tests establish physical iPhone/Android acceptance.
- Operator CLI synthetic drill: clean bootstrap created **0 users and 3 roles**; backup/restore passed, restored database integrity was `ok`, old sessions were removed, synthetic files survived and configuration required review. Library tests additionally cover deletion requested after backup, shared-file preservation, wrong keys, tampering, truncation and ZIP traversal.
- Running development API/AI smoke checks passed for six synthetic uploads, metadata removal/orientation, owner isolation, saved history and inconclusive clinical status. Generated scan rows were soft-deleted and photo routes became unavailable; physical cleanup follows the configured retention policy.
- Live account-control smoke checks passed for owner-only exports and rejection of old access/refresh tokens after all-device logout. No email was sent by these smoke checks.

## What still prevents the 65 milestone

The remaining eight points to the next milestone must come from completed deliverables, not changing weights or counting downloaded/duplicated images. Next available engineering work includes deployed HTTPS/monitoring/secret rotation and cloud restore drills, further access/storage review and signed phone builds with acceptance results. Data research needs verified task labels/rights and demonstrable improvements to weak models. Real SMTP delivery and configured Google OAuth sign-in remain incomplete. External clinical reference labels, calibration/unknown-condition evaluation, permissions and independent Pakistan cohorts remain outstanding.

Clinical inference stays disabled. A scan marked completed means the image workflow completed. No 97% clinical performance, universal disease exclusion, medicine suitability verification or automated prescribing is established by this checkpoint.

## Backup and deployment limits

See [operator runbook](OPERATIONS_RUNBOOK.md). This CLI supports the **default, same-layout, offline, single-host SQLite/local-file deployment**. Custom external key/OTP/upload paths, Azure object versions, PostgreSQL snapshots, multi-host quiescence and cloud key recovery need separate implementation and drills. A shared PostgreSQL OTP store alone does not solve those requirements.

The independent ledger and matching protection keys must be retained and replicated separately from application archives. Signatures detect changed entries, not deletion/rollback of the entire latest ledger. Restore can reject a ledger older than the archive's recorded snapshot, but cannot prove no later deletion was lost without an independently retained latest checkpoint. Existing encrypted archives may still contain historical erased bytes; backup expiry, replicas and provider versions need their own retention policy. No disk secure wipe or HIPAA certification is claimed.
