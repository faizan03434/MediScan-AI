using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using MediScan.Core.Entities;
using Microsoft.AspNetCore.DataProtection;
using Microsoft.Data.Sqlite;

namespace MediScan.API.Services;

// One SQLite file and Data Protection key ring must be shared by workers on this host.
// BEGIN IMMEDIATE serializes read/check/write across processes, not just C# threads.
public sealed class PersistentEmailOtpStore : IEmailOtpStore
{
    private readonly string connectionString;
    private readonly TimeProvider clock;
    private readonly IDataProtector protector;
    private sealed record Payload(byte[] Key, byte[] Hash, string? UserId, ApplicationUser? Registration);

    public PersistentEmailOtpStore(string path, TimeProvider clock, IDataProtectionProvider protection)
    {
        Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(path))!);
        connectionString = new SqliteConnectionStringBuilder { DataSource = path, DefaultTimeout = 10, Pooling = false }.ToString();
        this.clock = clock;
        protector = protection.CreateProtector("MediScan.EmailOtp.v1");
        using var db = Open();
        using var command = db.CreateCommand();
        command.CommandText = """
            CREATE TABLE IF NOT EXISTS EmailVerification (
                Scope TEXT PRIMARY KEY, Challenge TEXT, Payload TEXT, Expires INTEGER NOT NULL,
                WindowEnd INTEGER NOT NULL, Sends INTEGER NOT NULL, Failures INTEGER NOT NULL,
                Cooldown INTEGER NOT NULL);
            CREATE INDEX IF NOT EXISTS IX_EmailVerification_Challenge ON EmailVerification(Challenge);
            """;
        command.ExecuteNonQuery();
    }

    public IssuedOtp Issue(string email, string purpose, object? payload)
    {
        if (payload is not null and not string and not ApplicationUser) throw new ArgumentException("Unsupported verification payload.");
        var now = clock.GetUtcNow(); var seconds = now.ToUnixTimeSeconds();
        var scope = Scope(email, purpose);
        using var db = Open(); using var tx = db.BeginTransaction(deferred: false);
        Execute(db, tx, "DELETE FROM EmailVerification WHERE WindowEnd <= $now", ("$now", seconds));
        var row = Read(db, tx, scope);
        if (row != null && (row.Value.Sends >= 3 || row.Value.Failures >= 5))
            throw new ArgumentException("Verification limit reached. Try again after 15 minutes.");
        if (row != null && row.Value.Cooldown > seconds)
            throw new ArgumentException("Wait 60 seconds before requesting another code.");
        using (var count = db.CreateCommand())
        {
            count.Transaction = tx; count.CommandText = "SELECT COUNT(*) FROM EmailVerification";
            if (row == null && Convert.ToInt64(count.ExecuteScalar()) >= 5000)
                throw new AuthConfigurationException("Verification is busy. Please retry later.");
        }
        var id = Guid.NewGuid().ToString("N");
        var code = RandomNumberGenerator.GetInt32(0, 1_000_000).ToString("D6");
        var key = RandomNumberGenerator.GetBytes(32);
        var envelope = new Payload(key, Hash(key, id, code), payload as string, payload as ApplicationUser);
        var expires = now.AddMinutes(EmailOtpStore.LifetimeMinutes);
        Execute(db, tx, """
            INSERT INTO EmailVerification VALUES ($scope,$id,$payload,$expires,$window,1,0,$cooldown)
            ON CONFLICT(Scope) DO UPDATE SET Challenge=$id,Payload=$payload,Expires=$expires,
                Sends=Sends+1,Cooldown=$cooldown
            """, ("$scope", scope), ("$id", id), ("$payload", protector.Protect(JsonSerializer.Serialize(envelope))),
            ("$expires", expires.ToUnixTimeSeconds()), ("$window", seconds + 900), ("$cooldown", seconds + EmailOtpStore.ResendSeconds));
        tx.Commit();
        return new(id, code, expires);
    }

    public object? Consume(string id, string email, string purpose, string code)
    {
        using var db = Open(); using var tx = db.BeginTransaction(deferred: false);
        var scope = Scope(email, purpose); var row = Read(db, tx, scope);
        if (row == null || row.Value.Challenge != id || row.Value.Payload == null) throw Invalid();
        var value = row.Value;
        if (value.Expires <= clock.GetUtcNow().ToUnixTimeSeconds() || value.Failures >= 5)
        { Clear(db, tx, scope); tx.Commit(); throw Invalid(); }
        Payload envelope;
        try { envelope = JsonSerializer.Deserialize<Payload>(protector.Unprotect(value.Payload)) ?? throw Invalid(); }
        catch (CryptographicException) { Clear(db, tx, scope); tx.Commit(); throw Invalid(); }
        var valid = code.Length == 6 && code.All(char.IsAsciiDigit)
            && CryptographicOperations.FixedTimeEquals(envelope.Hash, Hash(envelope.Key, id, code));
        if (!valid)
        {
            Execute(db, tx, "UPDATE EmailVerification SET Failures=Failures+1 WHERE Scope=$scope", ("$scope", scope));
            if (value.Failures + 1 >= 5) Clear(db, tx, scope);
            tx.Commit(); throw Invalid();
        }
        Clear(db, tx, scope); tx.Commit();
        return (object?)envelope.Registration ?? envelope.UserId;
    }

    public void Cancel(string id)
    {
        using var db = Open(); using var tx = db.BeginTransaction(deferred: false);
        Execute(db, tx, "UPDATE EmailVerification SET Challenge=NULL,Payload=NULL WHERE Challenge=$id", ("$id", id));
        tx.Commit();
    }

    public void ForgetAccount(string email)
    {
        using var db = Open(); using var tx = db.BeginTransaction(deferred: false);
        foreach (var purpose in new[] { "registration", "password_reset", "account_deletion" })
            Execute(db, tx, "DELETE FROM EmailVerification WHERE Scope=$scope", ("$scope", Scope(email, purpose)));
        tx.Commit();
    }

    private SqliteConnection Open() { var db = new SqliteConnection(connectionString); db.Open(); return db; }
    private static string Scope(string email, string purpose) => Convert.ToHexString(SHA256.HashData(
        Encoding.UTF8.GetBytes(purpose + ":" + email.Trim().ToUpperInvariant())));
    private static byte[] Hash(byte[] key, string id, string code) => HMACSHA256.HashData(key, Encoding.UTF8.GetBytes(id + ":" + code));
    private static ArgumentException Invalid() => new("Invalid or expired code. Request a new code if needed.");
    private static void Clear(SqliteConnection db, SqliteTransaction tx, string scope) =>
        Execute(db, tx, "UPDATE EmailVerification SET Challenge=NULL,Payload=NULL WHERE Scope=$scope", ("$scope", scope));
    private static void Execute(SqliteConnection db, SqliteTransaction tx, string sql, params (string Name, object Value)[] values)
    {
        using var command = db.CreateCommand(); command.Transaction = tx; command.CommandText = sql;
        foreach (var (name, value) in values) command.Parameters.AddWithValue(name, value);
        command.ExecuteNonQuery();
    }
    private static (string? Challenge, string? Payload, long Expires, int Sends, int Failures, long Cooldown)? Read(
        SqliteConnection db, SqliteTransaction tx, string value)
    {
        using var command = db.CreateCommand(); command.Transaction = tx;
        command.CommandText = "SELECT Challenge,Payload,Expires,Sends,Failures,Cooldown FROM EmailVerification WHERE Scope=$value";
        command.Parameters.AddWithValue("$value", value);
        using var reader = command.ExecuteReader();
        return reader.Read() ? (reader.IsDBNull(0) ? null : reader.GetString(0), reader.IsDBNull(1) ? null : reader.GetString(1),
            reader.GetInt64(2), reader.GetInt32(3), reader.GetInt32(4), reader.GetInt64(5)) : null;
    }
}
