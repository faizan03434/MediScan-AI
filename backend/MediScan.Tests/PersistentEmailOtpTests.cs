using MediScan.API.Services;
using MediScan.Core.Entities;
using Microsoft.AspNetCore.DataProtection;

namespace MediScan.Tests;

public sealed class PersistentEmailOtpTests : IDisposable
{
    private readonly string directory = Path.Combine(Path.GetTempPath(), "mediscan-otp-" + Guid.NewGuid().ToString("N"));
    private sealed class Clock : TimeProvider
    {
        public DateTimeOffset Now = DateTimeOffset.UtcNow;
        public override DateTimeOffset GetUtcNow() => Now;
    }
    private readonly Clock clock = new();
    private PersistentEmailOtpStore Store() => new(Path.Combine(directory, "otp.db"), clock,
        DataProtectionProvider.Create(new DirectoryInfo(Path.Combine(directory, "keys"))));
    public void Dispose() { if (Directory.Exists(directory)) Directory.Delete(directory, true); }

    [Fact]
    public void RestartPreservesCodeEncryptedPayloadAndSingleUse()
    {
        var original = Store();
        var issued = original.Issue("a@example.com", "registration", new ApplicationUser {
            Email = "a@example.com", FullName = "Private Name", PasswordHash = "salted-private-hash" });
        var bytes = System.Text.Encoding.UTF8.GetString(File.ReadAllBytes(Path.Combine(directory, "otp.db")));
        Assert.DoesNotContain(issued.Code, bytes); Assert.DoesNotContain("a@example.com", bytes);
        Assert.DoesNotContain("salted-private-hash", bytes); Assert.DoesNotContain("Private Name", bytes);
        var restored = Assert.IsType<ApplicationUser>(Store().Consume(issued.ChallengeId, " A@example.com ", "registration", issued.Code));
        Assert.Equal("salted-private-hash", restored.PasswordHash);
        Assert.Throws<ArgumentException>(() => Store().Consume(issued.ChallengeId, "a@example.com", "registration", issued.Code));
    }

    [Fact]
    public void RestartCannotBypassCooldownOrSendBudget()
    {
        for (int i = 0; i < 3; i++)
        {
            var issued = Store().Issue("a@example.com", "password_reset", "id");
            Store().Consume(issued.ChallengeId, "a@example.com", "password_reset", issued.Code);
            Assert.Throws<ArgumentException>(() => Store().Issue("a@example.com", "password_reset", null));
            clock.Now += TimeSpan.FromSeconds(60);
        }
        Assert.Throws<ArgumentException>(() => Store().Issue("a@example.com", "password_reset", null));
        clock.Now += TimeSpan.FromMinutes(15);
        Assert.NotNull(Store().Issue("a@example.com", "password_reset", null));
    }

    [Fact]
    public void FailureBudgetSurvivesRestartAndResend()
    {
        var issued = Store().Issue("a@example.com", "password_reset", "id");
        for (int i = 0; i < 3; i++)
            Assert.Throws<ArgumentException>(() => Store().Consume(issued.ChallengeId, "a@example.com", "password_reset", "wrong"));
        clock.Now += TimeSpan.FromSeconds(60);
        var next = Store().Issue("a@example.com", "password_reset", "id");
        for (int i = 0; i < 2; i++)
            Assert.Throws<ArgumentException>(() => Store().Consume(next.ChallengeId, "a@example.com", "password_reset", "wrong"));
        Assert.Throws<ArgumentException>(() => Store().Consume(next.ChallengeId, "a@example.com", "password_reset", next.Code));
        clock.Now += TimeSpan.FromSeconds(60);
        Assert.Throws<ArgumentException>(() => Store().Issue("a@example.com", "password_reset", "id"));
    }

    [Fact]
    public async Task SeparateWorkersCannotConsumeCodeTwice()
    {
        var first = Store(); var second = Store();
        var issued = first.Issue("a@example.com", "password_reset", "id");
        async Task<bool> Attempt(PersistentEmailOtpStore store) => await Task.Run(() => {
            try { return (string?)store.Consume(issued.ChallengeId, "a@example.com", "password_reset", issued.Code) == "id"; }
            catch (ArgumentException) { return false; }
        });
        var results = await Task.WhenAll(Attempt(first), Attempt(second));
        Assert.Single(results, v => v);
    }

    [Fact]
    public async Task SeparateWorkersCannotBypassIssueCooldown()
    {
        var first = Store(); var second = Store();
        Task<bool> Attempt(PersistentEmailOtpStore store) => Task.Run(() => {
            try { store.Issue("a@example.com", "password_reset", "id"); return true; }
            catch (ArgumentException) { return false; }
        });
        var results = await Task.WhenAll(Attempt(first), Attempt(second));
        Assert.Single(results, v => v);
    }

    [Fact]
    public void CancellationKeepsBudgetAndExpiryRejectsCode()
    {
        var issued = Store().Issue("a@example.com", "password_reset", "id");
        Store().Cancel(issued.ChallengeId);
        Assert.Throws<ArgumentException>(() => Store().Consume(issued.ChallengeId, "a@example.com", "password_reset", issued.Code));
        Assert.Throws<ArgumentException>(() => Store().Issue("a@example.com", "password_reset", "id"));
        clock.Now += TimeSpan.FromSeconds(60);
        var next = Store().Issue("a@example.com", "password_reset", "id");
        clock.Now += TimeSpan.FromMinutes(10);
        Assert.Throws<ArgumentException>(() => Store().Consume(next.ChallengeId, "a@example.com", "password_reset", next.Code));
    }

    [Fact]
    public void EmailPurposeAndReplacementAreBound()
    {
        var issued = Store().Issue("a@example.com", "password_reset", "id");
        Assert.Throws<ArgumentException>(() => Store().Consume(issued.ChallengeId, "b@example.com", "password_reset", issued.Code));
        Assert.Throws<ArgumentException>(() => Store().Consume(issued.ChallengeId, "a@example.com", "registration", issued.Code));
        clock.Now += TimeSpan.FromSeconds(60);
        var next = Store().Issue("a@example.com", "password_reset", "new");
        Assert.Throws<ArgumentException>(() => Store().Consume(issued.ChallengeId, "a@example.com", "password_reset", issued.Code));
        Assert.Equal("new", Store().Consume(next.ChallengeId, "a@example.com", "password_reset", next.Code));
    }

    [Fact]
    public void WrongKeyRingFailsClosed()
    {
        var issued = Store().Issue("a@example.com", "password_reset", "id");
        var other = new PersistentEmailOtpStore(Path.Combine(directory, "otp.db"), clock, new EphemeralDataProtectionProvider());
        Assert.Throws<ArgumentException>(() => other.Consume(issued.ChallengeId, "a@example.com", "password_reset", issued.Code));
        Assert.Throws<ArgumentException>(() => Store().Consume(issued.ChallengeId, "a@example.com", "password_reset", issued.Code));
    }
}
