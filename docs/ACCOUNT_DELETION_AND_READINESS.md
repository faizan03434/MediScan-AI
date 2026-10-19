# Account deletion and readiness checkpoint — 19 October 2026

Live account deletion and dependency readiness are implemented. **66 backend tests and 87 AI tests pass**, mobile TypeScript/ESLint checks pass, and a fresh production web bundle exports. Clinical inference remains disabled; no new disease model training or clinical validation took place in this checkpoint.

## User flow

Profile → My Data & Sessions → Account deletion options. Export records first if needed. Type `DELETE` and verify the current password or a fresh purpose-bound email code. Email-code deletion depends on working SMTP; the previously documented SMTP disconnection remains unresolved. Password verification does not depend on email delivery. Failed passwords count toward Identity account lockout. The last active administrator cannot self-delete without an administrator transfer.

Accepted requests immediately disable the account, rotate its security stamp, remove refresh sessions and revoke patient/doctor consents. Cleanup is queued with a two-minute delay; the worker polls each minute. The app signs out and opens deletion status. Status uses a random 256-bit receipt in a POST body; only its hash is stored server-side. It never puts the receipt in a URL. Native storage retains the receipt; browser storage is tab-session based. If secure storage fails, status remains available only in the current app process. A lost receipt cannot be recovered through an unauthenticated email lookup.

## Cleanup and recovery

The queue is in the main database. Workers claim a renewable lease with a unique token. A stopped worker's expired lease can be reclaimed. Storage failures retain the disabled account and durable job for a later retry; a failed cleanup is not reported as completed. Successful file deletion is idempotent on retry. Shared images remain if another account still references them.

Cleanup includes active and hidden scan/medication/prescription records, both sides of doctor consents, Identity user data and cascading role/login/token records, refresh tokens, scoped audit references, pending verification payloads and owned media inventory. Completion removes the user link from the job and retains a minimal non-user-linked receipt/status record and completion event.

New uploads hold an owner-row database lock through media inventory commit. Inactive accounts cannot start an upload. Inventory captures successful uploads before a health record links them, while older linked photos are also discovered from existing records. The inventory transaction introduces contention on SQLite; production capacity and PostgreSQL behavior require deployed testing. File/object storage and SQL do not share a distributed transaction: failed compensation, process crashes and legacy untracked objects still require provider inventory reconciliation. This is not a claim of secure disk wiping.

Backups, SQLite free/WAL pages, cloud object versions and copies previously shared outside the app are not automatically erased. Backup expiry, encryption, restore-time deletion reconciliation and external retention decisions remain outstanding. Do not restore an old backup into public service without reconciling deletion requests. The opt-in generic deleted-record purger remains a separate policy-controlled feature; account deletion requests explicitly authorize their own cleanup and do not depend on that switch.

## API contract

| Endpoint | Access | Behavior |
| --- | --- | --- |
| `POST /api/v1/account/deletion/code` | Current account | Send purpose-bound verification code; failure leaves account enabled |
| `POST /api/v1/account/deletion` | Current account + fresh proof | `202` pending receipt; account access disabled |
| `POST /api/v1/account/deletion/status` | Possession of secret receipt | Minimal pending/completed status and timestamps; no identity or medical data |
| `GET /api/v1/health` | Public | API process liveness |
| `GET /api/v1/health/ready` | Public | `200` only if required database schema and image service are available; otherwise `503` |
| AI `GET /health/live` | Internal deployment probe | Cheap process availability; no model/GPU import or clinical readiness claim |

Readiness has a five-second overall deadline and a three-second image-service request timeout. It is not an SMTP, OAuth, model quality, migration/role provisioning or clinical acceptance test. The older AI `/health` GPU diagnostic still exists; availability probes use `/health/live` to avoid a cold PyTorch import. Compose health checks now use these endpoints. Docker/cloud deployments have not been run locally.

## Verification evidence

- Tests cover wrong/missing confirmation and proof, email delivery failure, purpose-bound OTP, last administrator protection, live/hidden records, shared photos, inventory-only images, identity/consent/audit cleanup, OTP removal, storage failure/retry, expired lease recovery, inactive upload rejection and schema/service readiness failures.
- The new additive migration applied to the local development database after a private ignored SQLite snapshot. Migration also passed against a fresh disposable SQLite database. New DDL selects SQLite/PostgreSQL column types; the full historical PostgreSQL migration chain still needs real-provider deployment verification.
- `infrastructure/smoke_account_deletion.py` created one synthetic account from the known demo fixture, uploaded a synthetic image through the running API, verified inventory and re-authentication, confirmed access/refresh rejection, and observed the real background worker remove the identity, records, inventory and physical image. Receipt status then reported completion. No existing user was selected for deletion.
- Six-module upload/privacy and account export/all-device logout smoke checks still pass. Physical iPhone/Android deletion UX and secure receipt persistence are not yet device-verified.

Run the deletion smoke script only against the local development preview. It verifies that the API and seeded fixture database match, never prints tokens/receipts/health data and advances only its synthetic job's schedule. After acceptance, a failed smoke check leaves cleanup to the durable queue; before acceptance it removes only its own fixture.
