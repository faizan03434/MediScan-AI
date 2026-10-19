using System.Security.Cryptography;
using System.Text;

namespace MediScan.API.Services;

public record IssuedOtp(string ChallengeId, string Code, DateTimeOffset ExpiresAt);

public interface IEmailOtpStore
{
    IssuedOtp Issue(string email, string purpose, object? payload);
    object? Consume(string id, string email, string purpose, string code);
    void Cancel(string id);
    void ForgetAccount(string email);
}

// Single-process development store. Production must share atomic challenges across instances.
public sealed class EmailOtpStore(TimeProvider clock) : IEmailOtpStore
{
    private sealed record Entry(string Email, string Purpose, byte[] Hash, DateTimeOffset Expires,
        object? Payload) { public int Attempts { get; set; } }
    private readonly Dictionary<string, Entry> _entries = new();
    private readonly Dictionary<string, DateTimeOffset> _cooldowns = new();
    private sealed class Budget(DateTimeOffset expires)
    { public DateTimeOffset Expires { get; } = expires; public int Sends; public int Failures; }
    private readonly Dictionary<string, Budget> _budgets = new();
    private readonly byte[] _hashKey = RandomNumberGenerator.GetBytes(32);
    private readonly object _gate = new();
    public const int LifetimeMinutes = 10;
    public const int ResendSeconds = 60;

    public IssuedOtp Issue(string email, string purpose, object? payload)
    {
        email = email.Trim().ToUpperInvariant();
        lock (_gate)
        {
            var now = clock.GetUtcNow();
            foreach (var id in _entries.Where(p => p.Value.Expires <= now).Select(p => p.Key).ToArray()) _entries.Remove(id);
            foreach (var key in _cooldowns.Where(p => p.Value <= now).Select(p => p.Key).ToArray()) _cooldowns.Remove(key);
            foreach (var key in _budgets.Where(p => p.Value.Expires <= now).Select(p => p.Key).ToArray()) _budgets.Remove(key);
            var scope = purpose + ":" + email;
            if (!_budgets.TryGetValue(scope, out var budget))
            {
                if (_budgets.Count >= 5000) throw new AuthConfigurationException("Verification is busy. Please retry later.");
                _budgets[scope] = budget = new Budget(now.AddMinutes(15));
            }
            if (budget.Sends >= 3 || budget.Failures >= 5)
                throw new ArgumentException("Verification limit reached. Try again after 15 minutes.");
            if (_cooldowns.TryGetValue(scope, out var until) && until > now)
                throw new ArgumentException("Wait 60 seconds before requesting another code.");
            if (_entries.Count >= 5000) throw new AuthConfigurationException("Verification is busy. Please retry later.");
            foreach (var id in _entries.Where(p => p.Value.Email == email && p.Value.Purpose == purpose).Select(p => p.Key).ToArray()) _entries.Remove(id);
            var idNew = Guid.NewGuid().ToString("N");
            var code = RandomNumberGenerator.GetInt32(0, 1_000_000).ToString("D6");
            var expires = now.AddMinutes(LifetimeMinutes);
            _entries[idNew] = new Entry(email, purpose, Hash(idNew, code), expires, payload);
            _cooldowns[scope] = now.AddSeconds(ResendSeconds);
            budget.Sends++;
            return new IssuedOtp(idNew, code, expires);
        }
    }

    public object? Consume(string id, string email, string purpose, string code)
    {
        lock (_gate)
        {
            if (!_entries.TryGetValue(id, out var entry)) throw Invalid();
            if (entry.Expires <= clock.GetUtcNow()) { _entries.Remove(id); throw Invalid(); }
            var scope = entry.Purpose + ":" + entry.Email;
            if (_budgets.TryGetValue(scope, out var budget) && budget.Expires > clock.GetUtcNow() && budget.Failures >= 5)
            { _entries.Remove(id); throw Invalid(); }
            entry.Attempts++;
            var valid = entry.Email == email.Trim().ToUpperInvariant() && entry.Purpose == purpose
                && code.Length == 6 && code.All(char.IsAsciiDigit)
                && CryptographicOperations.FixedTimeEquals(entry.Hash, Hash(id, code));
            if (!valid)
            {
                if (budget != null && budget.Expires > clock.GetUtcNow()) budget.Failures++;
                if (entry.Attempts >= 5 || budget?.Failures >= 5) _entries.Remove(id);
                throw Invalid();
            }
            _entries.Remove(id);
            return entry.Payload;
        }
    }

    public void Cancel(string id) { lock (_gate) _entries.Remove(id); }
    public void ForgetAccount(string email)
    {
        email = email.Trim().ToUpperInvariant();
        lock (_gate)
        {
            foreach (var id in _entries.Where(e => e.Value.Email == email).Select(e => e.Key).ToArray()) _entries.Remove(id);
            foreach (var key in _budgets.Keys.Where(k => k.EndsWith(":" + email, StringComparison.Ordinal)).ToArray()) _budgets.Remove(key);
            foreach (var key in _cooldowns.Keys.Where(k => k.EndsWith(":" + email, StringComparison.Ordinal)).ToArray()) _cooldowns.Remove(key);
        }
    }
    private byte[] Hash(string id, string code) => HMACSHA256.HashData(_hashKey, Encoding.UTF8.GetBytes(id + ":" + code));
    private static ArgumentException Invalid() => new("Invalid or expired code. Request a new code if needed.");
}
