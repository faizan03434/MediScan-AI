using System.Security.Cryptography;
using System.Text;
using Microsoft.AspNetCore.DataProtection;
using Microsoft.Data.Sqlite;

namespace MediScan.Operations.Privacy;

public sealed record LedgerSnapshot(string Id, string[] SubjectHashes);
public interface IDeletionLedger
{
    void Record(string userId, DateTime requestedAt);
    LedgerSnapshot Snapshot();
}

// Kept independently of restorable application backups. Stores signed hashes, not email/medical data.
public sealed class DeletionLedger : IDeletionLedger
{
    private readonly string connectionString;
    private readonly byte[] signingKey;
    private readonly string ledgerId;
    public DeletionLedger(string path, IDataProtectionProvider protection)
    {
        Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(path))!);
        connectionString = new SqliteConnectionStringBuilder { DataSource = path, DefaultTimeout = 10, Pooling = false }.ToString();
        var protector = protection.CreateProtector("MediScan.DeletionLedger.SigningKey.v1");
        using var db = Open(); using var tx = db.BeginTransaction(deferred: false);
        using var schema = db.CreateCommand(); schema.Transaction = tx;
        schema.CommandText = """
            CREATE TABLE IF NOT EXISTS LedgerMetadata (Name TEXT PRIMARY KEY, Value BLOB NOT NULL);
            CREATE TABLE IF NOT EXISTS Deletions (SubjectHash TEXT PRIMARY KEY, RequestedTicks INTEGER NOT NULL, Signature BLOB NOT NULL);
            """;
        schema.ExecuteNonQuery();
        var key = ReadMetadata(db, tx, "key");
        if (key == null)
        {
            signingKey = RandomNumberGenerator.GetBytes(32);
            ledgerId = Guid.NewGuid().ToString("N");
            WriteMetadata(db, tx, "key", protector.Protect(signingKey));
            WriteMetadata(db, tx, "id", Encoding.UTF8.GetBytes(ledgerId));
        }
        else
        {
            signingKey = protector.Unprotect(key);
            ledgerId = Encoding.UTF8.GetString(ReadMetadata(db, tx, "id") ?? throw new CryptographicException("Incomplete deletion ledger."));
        }
        tx.Commit();
        Snapshot(); // Corruption or wrong key must fail before processing deletion/restore.
    }

    public static string SubjectHash(string id) => Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(id)));
    public void Record(string userId, DateTime requestedAt)
    {
        var hash = SubjectHash(userId); var ticks = requestedAt.ToUniversalTime().Ticks;
        using var db = Open(); using var command = db.CreateCommand();
        command.CommandText = "INSERT OR IGNORE INTO Deletions VALUES ($hash,$ticks,$signature)";
        command.Parameters.AddWithValue("$hash", hash); command.Parameters.AddWithValue("$ticks", ticks);
        command.Parameters.AddWithValue("$signature", Sign(hash, ticks)); command.ExecuteNonQuery();
    }

    public LedgerSnapshot Snapshot()
    {
        var hashes = new List<string>();
        using var db = Open(); using var command = db.CreateCommand();
        command.CommandText = "SELECT SubjectHash,RequestedTicks,Signature FROM Deletions ORDER BY SubjectHash";
        using var reader = command.ExecuteReader();
        while (reader.Read())
        {
            var hash = reader.GetString(0); var ticks = reader.GetInt64(1); var signature = (byte[])reader[2];
            if (!CryptographicOperations.FixedTimeEquals(signature, Sign(hash, ticks)))
                throw new CryptographicException("Deletion ledger integrity validation failed.");
            hashes.Add(hash);
        }
        return new(ledgerId, hashes.ToArray());
    }

    public static void RequireCurrentLedger(LedgerSnapshot archived, LedgerSnapshot current)
    {
        var currentHashes = current.SubjectHashes.ToHashSet(StringComparer.Ordinal);
        if (archived.Id != current.Id || archived.SubjectHashes.Any(hash => !currentHashes.Contains(hash)))
            throw new InvalidOperationException("Current deletion ledger is missing, unrelated or older than this backup.");
    }
    private byte[] Sign(string hash, long ticks) => HMACSHA256.HashData(signingKey, Encoding.UTF8.GetBytes(hash + ":" + ticks.ToString(System.Globalization.CultureInfo.InvariantCulture)));
    private SqliteConnection Open() { var db = new SqliteConnection(connectionString); db.Open(); return db; }
    private static byte[]? ReadMetadata(SqliteConnection db, SqliteTransaction tx, string name)
    {
        using var command = db.CreateCommand(); command.Transaction = tx;
        command.CommandText = "SELECT Value FROM LedgerMetadata WHERE Name=$name"; command.Parameters.AddWithValue("$name", name);
        return command.ExecuteScalar() as byte[];
    }
    private static void WriteMetadata(SqliteConnection db, SqliteTransaction tx, string name, byte[] value)
    {
        using var command = db.CreateCommand(); command.Transaction = tx;
        command.CommandText = "INSERT INTO LedgerMetadata VALUES ($name,$value)";
        command.Parameters.AddWithValue("$name", name); command.Parameters.AddWithValue("$value", value); command.ExecuteNonQuery();
    }
}
