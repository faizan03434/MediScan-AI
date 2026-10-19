using System.Text.Json;
using Microsoft.Data.Sqlite;

namespace MediScan.Operations.Privacy;

internal static class RestoreErasure
{
    public static int Apply(string root, string databasePath, string[] hashes)
    {
        var erased = hashes.ToHashSet(StringComparer.Ordinal);
        using var db = new SqliteConnection(new SqliteConnectionStringBuilder {
            DataSource = SnapshotArchive.SafePath(root, databasePath), ForeignKeys = true, Pooling = false }.ToString()); db.Open();
        var users = new List<(string Id, string? Email)>();
        using (var query = db.CreateCommand())
        {
            query.CommandText = "SELECT Id,Email FROM AspNetUsers";
            using var reader = query.ExecuteReader();
            while (reader.Read()) if (erased.Contains(DeletionLedger.SubjectHash(reader.GetString(0))))
                users.Add((reader.GetString(0), reader.IsDBNull(1) ? null : reader.GetString(1)));
        }
        foreach (var (id, email) in users)
        {
            var blobs = Values(db, """
                SELECT ImageBlobName FROM ScanRecords WHERE UserId=$id AND ImageBlobName IS NOT NULL
                UNION SELECT ImageBlobName FROM MedicationRecords WHERE UserId=$id AND ImageBlobName IS NOT NULL
                UNION SELECT ImageBlobName FROM PrescriptionRecords WHERE UserId=$id AND ImageBlobName IS NOT NULL
                UNION SELECT BlobName FROM StoredMedia WHERE UserId=$id
                """, id);
            // Include old interrupted local uploads in the subject's own folders.
            foreach (var kind in new[] { "scans", "prescriptions" })
            {
                var folder = SnapshotArchive.SafePath(root, $"wwwroot/uploads/{kind}/{id}");
                if (Directory.Exists(folder)) blobs.AddRange(Directory.EnumerateFiles(folder, "*", SearchOption.AllDirectories)
                    .Select(path => Path.GetRelativePath(Path.Combine(root, "wwwroot/uploads"), path).Replace('\\', '/')));
            }
            foreach (var blob in blobs.Distinct(StringComparer.Ordinal))
            {
                using var shared = db.CreateCommand(); shared.CommandText = """
                    SELECT EXISTS(SELECT 1 FROM ScanRecords WHERE UserId<>$id AND ImageBlobName=$blob
                    UNION ALL SELECT 1 FROM MedicationRecords WHERE UserId<>$id AND ImageBlobName=$blob
                    UNION ALL SELECT 1 FROM PrescriptionRecords WHERE UserId<>$id AND ImageBlobName=$blob
                    UNION ALL SELECT 1 FROM StoredMedia WHERE UserId<>$id AND BlobName=$blob)
                    """;
                shared.Parameters.AddWithValue("$id", id); shared.Parameters.AddWithValue("$blob", blob);
                if (Convert.ToInt64(shared.ExecuteScalar()) == 0)
                    File.Delete(SnapshotArchive.SafePath(root, "wwwroot/uploads/" + blob));
            }
            var ids = Values(db, """
                SELECT Id FROM ScanRecords WHERE UserId=$id UNION SELECT Id FROM MedicationRecords WHERE UserId=$id
                UNION SELECT Id FROM PrescriptionRecords WHERE UserId=$id
                UNION SELECT Id FROM PatientConsents WHERE PatientUserId=$id OR DoctorUserId=$id
                """, id).Select(value => value.ToLowerInvariant()).ToArray();
            using (var transaction = db.BeginTransaction())
            {
                using var delete = db.CreateCommand(); delete.Transaction = transaction;
                delete.CommandText = """
                    DELETE FROM MedicationRecords WHERE UserId=$id;
                    DELETE FROM PrescriptionRecords WHERE UserId=$id;
                    DELETE FROM ScanRecords WHERE UserId=$id;
                    DELETE FROM PatientConsents WHERE PatientUserId=$id OR DoctorUserId=$id;
                    DELETE FROM RefreshTokens WHERE UserId=$id;
                    DELETE FROM StoredMedia WHERE UserId=$id;
                    DELETE FROM AuditLogs WHERE UserId=$id OR EntityId=$id OR lower(EntityId) IN (SELECT value FROM json_each($entities));
                    UPDATE AccountDeletionJobs SET UserId=NULL,CompletedAt=$now,LeaseUntil=NULL,LeaseToken=NULL WHERE UserId=$id;
                    DELETE FROM AspNetUsers WHERE Id=$id;
                    """;
                delete.Parameters.AddWithValue("$id", id); delete.Parameters.AddWithValue("$entities", JsonSerializer.Serialize(ids));
                delete.Parameters.AddWithValue("$now", DateTime.UtcNow); delete.ExecuteNonQuery(); transaction.Commit();
            }
            var authPath = SnapshotArchive.SafePath(root, ".auth/verification.db");
            if (email != null && File.Exists(authPath))
            {
                using var auth = new SqliteConnection(new SqliteConnectionStringBuilder { DataSource = authPath, Pooling = false }.ToString()); auth.Open();
                foreach (var purpose in new[] { "registration", "password_reset", "account_deletion" })
                {
                    var scope = DeletionLedger.SubjectHash(purpose + ":" + email.Trim().ToUpperInvariant());
                    using var clear = auth.CreateCommand(); clear.CommandText = "DELETE FROM EmailVerification WHERE Scope=$scope";
                    clear.Parameters.AddWithValue("$scope", scope); clear.ExecuteNonQuery();
                }
                using var compact = auth.CreateCommand(); compact.CommandText = "VACUUM"; compact.ExecuteNonQuery();
            }
        }
        // Old backup sessions must never regain validity after restore, including surviving accounts.
        using (var invalidate = db.CreateCommand())
        {
            invalidate.CommandText = "DELETE FROM RefreshTokens; UPDATE AspNetUsers SET SecurityStamp=lower(hex(randomblob(16))),ConcurrencyStamp=lower(hex(randomblob(16))); VACUUM;";
            invalidate.ExecuteNonQuery();
        }
        var verificationPath = SnapshotArchive.SafePath(root, ".auth/verification.db");
        if (File.Exists(verificationPath))
        {
            using var auth = new SqliteConnection(new SqliteConnectionStringBuilder { DataSource = verificationPath, Pooling = false }.ToString()); auth.Open();
            using var invalidate = auth.CreateCommand();
            invalidate.CommandText = "UPDATE EmailVerification SET Challenge=NULL,Payload=NULL; VACUUM"; invalidate.ExecuteNonQuery();
        }
        using (var integrity = db.CreateCommand())
        {
            integrity.CommandText = "PRAGMA integrity_check";
            if ((string?)integrity.ExecuteScalar() != "ok") throw new InvalidDataException("Restored SQLite database failed integrity check.");
        }
        return users.Count;
    }
    private static List<string> Values(SqliteConnection db, string sql, string id)
    {
        using var command = db.CreateCommand(); command.CommandText = sql; command.Parameters.AddWithValue("$id", id);
        using var reader = command.ExecuteReader(); var values = new List<string>();
        while (reader.Read()) values.Add(reader.GetString(0)); return values;
    }
}
