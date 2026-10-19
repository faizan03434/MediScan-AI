using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using MediScan.Core.Entities;
using Microsoft.AspNetCore.DataProtection;
using Npgsql;

namespace MediScan.API.Services;

// Transaction-level advisory lock coordinates all API hosts; no in-memory fallback.
// A shared Data Protection key ring/certificate is also required across those hosts.
public sealed class PostgresEmailOtpStore(string connectionString, TimeProvider clock, IDataProtectionProvider protection) : IEmailOtpStore
{
    private readonly IDataProtector protector = protection.CreateProtector("MediScan.EmailOtp.v1");
    private sealed record Payload(byte[] Key, byte[] Hash, string? UserId, ApplicationUser? Registration);
    private sealed record Row(string? Id, string? Payload, long Expires, int Sends, int Failures, long Cooldown);
    private sealed record Consumed(bool Valid, object? Payload);

    public IssuedOtp Issue(string email, string purpose, object? payload)
    {
        if (payload is not null and not string and not ApplicationUser) throw new ArgumentException("Unsupported verification payload.");
        return Locked((db, tx) => {
            var now = clock.GetUtcNow(); var seconds = now.ToUnixTimeSeconds(); var scope = Scope(email, purpose);
            Execute(db, tx, "DELETE FROM email_verification WHERE window_end <= @now", ("now", seconds));
            var row = Read(db, tx, scope);
            if (row != null && (row.Sends >= 3 || row.Failures >= 5)) throw new ArgumentException("Verification limit reached. Try again after 15 minutes.");
            if (row != null && row.Cooldown > seconds) throw new ArgumentException("Wait 60 seconds before requesting another code.");
            if (row == null)
            {
                using var count = new NpgsqlCommand("SELECT COUNT(*) FROM email_verification", db, tx);
                if (Convert.ToInt64(count.ExecuteScalar()) >= 5000) throw new AuthConfigurationException("Verification is busy. Please retry later.");
            }
            var id = Guid.NewGuid().ToString("N"); var code = RandomNumberGenerator.GetInt32(0, 1_000_000).ToString("D6");
            var key = RandomNumberGenerator.GetBytes(32); var expires = now.AddMinutes(EmailOtpStore.LifetimeMinutes);
            var encrypted = protector.Protect(JsonSerializer.Serialize(new Payload(key, Hash(key, id, code), payload as string, payload as ApplicationUser)));
            Execute(db, tx, """
                INSERT INTO email_verification VALUES (@scope,@id,@payload,@expires,@window,1,0,@cooldown)
                ON CONFLICT(scope) DO UPDATE SET challenge=@id,payload=@payload,expires=@expires,sends=email_verification.sends+1,cooldown=@cooldown
                """, ("scope", scope), ("id", id), ("payload", encrypted), ("expires", expires.ToUnixTimeSeconds()),
                ("window", seconds + 900), ("cooldown", seconds + EmailOtpStore.ResendSeconds));
            return new IssuedOtp(id, code, expires);
        });
    }

    public object? Consume(string id, string email, string purpose, string code)
    {
        var result = Locked((db, tx) => {
            var scope = Scope(email, purpose); var row = Read(db, tx, scope);
            if (row == null || row.Id != id || row.Payload == null) return new Consumed(false, null);
            if (row.Expires <= clock.GetUtcNow().ToUnixTimeSeconds() || row.Failures >= 5)
            { Clear(db, tx, scope); return new Consumed(false, null); }
            Payload envelope;
            try { envelope = JsonSerializer.Deserialize<Payload>(protector.Unprotect(row.Payload)) ?? throw new CryptographicException(); }
            catch (CryptographicException) { Clear(db, tx, scope); return new Consumed(false, null); }
            var valid = code.Length == 6 && code.All(char.IsAsciiDigit)
                && CryptographicOperations.FixedTimeEquals(envelope.Hash, Hash(envelope.Key, id, code));
            if (!valid)
            {
                Execute(db, tx, "UPDATE email_verification SET failures=failures+1 WHERE scope=@scope", ("scope", scope));
                if (row.Failures + 1 >= 5) Clear(db, tx, scope);
                return new Consumed(false, null);
            }
            Clear(db, tx, scope); return new Consumed(true, (object?)envelope.Registration ?? envelope.UserId);
        });
        if (!result.Valid) throw new ArgumentException("Invalid or expired code. Request a new code if needed.");
        return result.Payload;
    }
    public void Cancel(string id) => Locked((db, tx) => Execute(db, tx, "UPDATE email_verification SET challenge=NULL,payload=NULL WHERE challenge=@id", ("id", id)));
    public void ForgetAccount(string email) => Locked((db, tx) => {
        foreach (var purpose in new[] { "registration", "password_reset", "account_deletion" })
            Execute(db, tx, "DELETE FROM email_verification WHERE scope=@scope", ("scope", Scope(email, purpose)));
        return 0;
    });
    private T Locked<T>(Func<NpgsqlConnection, NpgsqlTransaction, T> action)
    {
        try
        {
            var settings = new NpgsqlConnectionStringBuilder(connectionString) { Timeout = 5, CommandTimeout = 10 };
            using var db = new NpgsqlConnection(settings.ToString()); db.Open(); using var tx = db.BeginTransaction();
            using var locked = new NpgsqlCommand("SELECT pg_advisory_xact_lock(5571871320559866960)", db, tx); locked.ExecuteNonQuery();
            var result = action(db, tx); tx.Commit(); return result;
        }
        catch (NpgsqlException) { throw new AuthConfigurationException("Verification service is temporarily unavailable. Please retry later."); }
    }
    private static Row? Read(NpgsqlConnection db, NpgsqlTransaction tx, string scope)
    {
        using var query = new NpgsqlCommand("SELECT challenge,payload,expires,sends,failures,cooldown FROM email_verification WHERE scope=@scope", db, tx);
        query.Parameters.AddWithValue("scope", scope); using var reader = query.ExecuteReader();
        return reader.Read() ? new(reader.IsDBNull(0) ? null : reader.GetString(0), reader.IsDBNull(1) ? null : reader.GetString(1),
            reader.GetInt64(2), reader.GetInt32(3), reader.GetInt32(4), reader.GetInt64(5)) : null;
    }
    private static void Clear(NpgsqlConnection db, NpgsqlTransaction tx, string scope) => Execute(db, tx,
        "UPDATE email_verification SET challenge=NULL,payload=NULL WHERE scope=@scope", ("scope", scope));
    private static string Scope(string email, string purpose) => Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(purpose + ":" + email.Trim().ToUpperInvariant())));
    private static byte[] Hash(byte[] key, string id, string code) => HMACSHA256.HashData(key, Encoding.UTF8.GetBytes(id + ":" + code));
    private static int Execute(NpgsqlConnection db, NpgsqlTransaction tx, string sql, params (string Name, object Value)[] parameters)
    {
        using var command = new NpgsqlCommand(sql, db, tx);
        foreach (var (name, value) in parameters) command.Parameters.AddWithValue(name, value);
        return command.ExecuteNonQuery();
    }
}
