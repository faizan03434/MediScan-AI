-- ============================================================
-- MediScan AI — PostgreSQL Initial Schema
-- Runs once when Docker container starts for the first time.
-- EF Core migrations handle schema changes after initial setup.
-- ============================================================

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";   -- Fast text search

-- ── Roles ─────────────────────────────────────────────────────
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'mediscan_readonly') THEN
    CREATE ROLE mediscan_readonly;
  END IF;
END
$$;

-- ── Schemas ───────────────────────────────────────────────────
CREATE SCHEMA IF NOT EXISTS mediscan;

-- Grant permissions
GRANT USAGE ON SCHEMA mediscan TO mediscan_user;
GRANT USAGE ON SCHEMA public   TO mediscan_user;
GRANT ALL PRIVILEGES ON ALL TABLES    IN SCHEMA public TO mediscan_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO mediscan_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT ALL ON TABLES    TO mediscan_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT ALL ON SEQUENCES TO mediscan_user;

-- ============================================================
-- NOTE: EF Core handles the actual table creation via migrations.
-- This file only sets up extensions, roles, and initial config.
-- Run migrations with:  dotnet ef database update
-- Or via Docker:        the API auto-migrates on startup in dev
-- ============================================================

-- ── Audit trigger function (runs AFTER EF creates tables) ────
-- Called by triggers to auto-fill updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW."UpdatedAt" = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ── Performance indexes (applied after EF migrations) ────────
-- These are created by a separate migration, but documented here
-- for reference:
--
-- CREATE INDEX CONCURRENTLY idx_scan_records_user_id
--   ON "ScanRecords"("UserId");
-- CREATE INDEX CONCURRENTLY idx_scan_records_created_at
--   ON "ScanRecords"("CreatedAt" DESC);
-- CREATE INDEX CONCURRENTLY idx_scan_records_type_status
--   ON "ScanRecords"("ScanType", "Status");
-- CREATE INDEX CONCURRENTLY idx_audit_logs_user_action
--   ON "AuditLogs"("UserId", "Action");
-- CREATE INDEX CONCURRENTLY idx_medication_records_user
--   ON "MedicationRecords"("UserId");
-- CREATE INDEX CONCURRENTLY idx_refresh_tokens_token
--   ON "RefreshTokens"("Token");

-- ── Seed data placeholder (dev only) ─────────────────────────
-- Actual seeding done via .NET DataSeeder on first startup

SELECT 'MediScan AI database initialized successfully.' AS status;
