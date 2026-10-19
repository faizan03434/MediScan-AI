# Operator runbook

These commands do not deploy the product or enable clinical inference. Work against a disposable environment before using them with health data. Never put secrets, databases, keyrings, archives, uploads or raw datasets in Git.

## Fresh database bootstrap

Set `ASPNETCORE_ENVIRONMENT=Production`, `Database__Provider=postgresql` and a separately supplied `ConnectionStrings__DefaultConnection`. Production also requires:

- A random `Jwt__Secret` of at least 64 characters; explicit issuer/audience and an expiry of 1–60 minutes.
- A separately generated `AiServer__ApiKey` of at least 32 characters, matching the AI service key.
- `AllowedOrigins__0=https://<browser-host>` and further numbered origins if needed; explicit semicolon-separated `AllowedHosts` without wildcards.
- A protected, durable Data Protection keyring. Outside Windows configure `Authentication__DataProtection__CertificatePath` and its privately supplied password. Windows defaults to DPAPI for the service OS user; retaining the files alone does not make them decryptable on another host/user.

Run the published API with `--initialize-database` before starting API workers. It acquires the local maintenance lease, applies the selected provider's migrations, provisions three roles, initializes the independent deletion ledger and exits. It does not create an admin account or demo accounts. Administrator enrollment/transfer remains an operator-controlled task; there is no public role-promotion registration parameter.

The PostgreSQL migration chain is a **fresh schema baseline**. Do not apply it blindly over an older database built from the historical mixed-provider migrations. Inventory that schema and plan/test its upgrade separately. Production runtime does not automatically run migrations. Development still runs migrations and seeds clearly documented demo accounts.

Configure TLS at the server/ingress and verify HTTPS, allowed-host behavior, readiness and correct client-IP handling. Trusted reverse-proxy forwarding and deployment-specific network policies still require configuration/review; do not assume local HTTP preview is production HTTPS.

## SQLite backup/restore

Supported layout: application content root containing the main SQLite database, default `.auth/verification.db`, `.auth/keys`, `.privacy/deletions.db` and `wwwroot/uploads`. Alternate configured paths are not automatically discovered by this tool.

Build/publish `backend/MediScan.Tools`. Stop **all** workers for that application root; same-host API leases block maintenance. Independently retain the current `.privacy/deletions.db` and matching protection keys with a separately managed latest checkpoint, recovery permissions and replication/expiry policy.

Supply `MEDISCAN_BACKUP_KEY` privately as Base64 of **32 cryptographically random bytes**. Keep it in managed secret storage; do not print it or store it next to the archive. With certificate-protected keys, supply `MEDISCAN_DATA_PROTECTION_CERTIFICATE` and its password environment variable as well. Windows recovery requires the original DPAPI user context unless certificate protection was explicitly configured and tested.

```text
dotnet MediScan.Tools.dll backup <application-root> <relative-sqlite-file> <new-archive-outside-root>
dotnet MediScan.Tools.dll restore <archive> <current-application-root> <new-unused-root>
```

Archive creation refuses to overwrite a file. Restore refuses an existing destination, requires the independently current source ledger/keyring, merges protection keys, verifies signatures and rejects incompatible/missing ledger history. The backup format streams AES-256-CBC plus HMAC-SHA256 with independent HKDF-derived keys; the header and ciphertext are authenticated before plaintext extraction. No independent cryptographic audit is claimed.

Restore reapplies recorded deletion intents and removes their unshared local files, invalidates all old sessions/codes and checks SQLite integrity before publishing the new directory. Configuration copies appear under `restore-configuration/`; explicitly review/reconfigure connection strings, roots, secrets, TLS and environment before starting there. Keep the restored deletion ledger/keyring durable. Users must sign in again.

Archive size/extraction budgets are 10 GiB/100,000 entries. Source/destination trees must be private and contain no symlinks/reparse points. Maintenance creates plaintext staging directories temporarily, with restricted Unix modes and inherited Windows ACLs; restrict the application/restore parent ACLs. Cleanup is bounded to tool-created staging directories. Snapshotting an active database externally, cloning an older ledger, or restoring object-storage versions independently bypasses these protections.

This is not a PostgreSQL/pg_dump or Azure snapshot tool. For those providers, implement provider-native encrypted backups, current-ledger reconciliation, global maintenance coordination and a real restore drill before production use. Apply retention to archived ciphertext, replicas and object versions separately; restore-time erasure does not destroy old backup bytes.

## Local evidence commands

```text
dotnet build backend/MediScan.sln
python infrastructure/smoke_maintenance.py
dotnet test backend/MediScan.Tests/MediScan.Tests.csproj
```

The maintenance smoke command creates synthetic data only under ignored `.preview/maintenance-drills/` and retains private drill logs. Its temporary encryption key is not retained, so the fixture archive is not an operator recovery backup. PostgreSQL integration tests run only when `MEDISCAN_TEST_POSTGRES` identifies a disposable-capable server; they create/drop uniquely named `mediscan_test_<random>` databases and require suitable privileges. Without that environment variable they skip explicitly.

After startup, `/api/v1/health` is cheap liveness and `/api/v1/health/ready` checks schema queries plus the image service's liveness. Readiness does not validate SMTP, Google credentials, model accuracy or clinical release. Monitor readiness failures, OTP delivery errors, deletion cleanup retries, archive/ledger replication age and restore outcomes without logging patient data or credentials. Public cloud monitoring/alert delivery and key rotation drills remain pending.
