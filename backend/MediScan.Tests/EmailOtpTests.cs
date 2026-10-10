using MediScan.API.Services;

namespace MediScan.Tests;

public class EmailOtpTests
{
    private sealed class Clock : TimeProvider
    {
        public DateTimeOffset Now { get; set; } = DateTimeOffset.UtcNow;
        public override DateTimeOffset GetUtcNow() => Now;
    }

    [Fact]
    public void CodesAreEmailAndPurposeBoundAndSingleUse()
    {
        var store = new EmailOtpStore(new Clock());
        var issued = store.Issue("a@example.com", "registration", "pending-user");
        Assert.Throws<ArgumentException>(() => store.Consume(issued.ChallengeId, "b@example.com", "registration", issued.Code));
        Assert.Throws<ArgumentException>(() => store.Consume(issued.ChallengeId, "a@example.com", "password_reset", issued.Code));
        Assert.Equal("pending-user", store.Consume(issued.ChallengeId, " A@example.com ", "registration", issued.Code));
        Assert.Throws<ArgumentException>(() => store.Consume(issued.ChallengeId, "a@example.com", "registration", issued.Code));
    }

    [Fact]
    public void ExpiredCodesCannotBeUsed()
    {
        var clock = new Clock(); var store = new EmailOtpStore(clock);
        var issued = store.Issue("a@example.com", "registration", null);
        clock.Now += TimeSpan.FromMinutes(10);
        Assert.Throws<ArgumentException>(() => store.Consume(issued.ChallengeId, "a@example.com", "registration", issued.Code));
    }

    [Fact]
    public void ResendEnforcesCooldownAndInvalidatesPreviousCode()
    {
        var clock = new Clock(); var store = new EmailOtpStore(clock);
        var issued = store.Issue("a@example.com", "registration", null);
        Assert.Throws<ArgumentException>(() => store.Issue("A@example.com", "registration", null));
        clock.Now += TimeSpan.FromSeconds(60);
        var second = store.Issue("a@example.com", "registration", "new");
        Assert.Throws<ArgumentException>(() => store.Consume(issued.ChallengeId, "a@example.com", "registration", issued.Code));
        Assert.Equal("new", store.Consume(second.ChallengeId, "a@example.com", "registration", second.Code));
    }

    [Fact]
    public void FiveFailuresInvalidateEvenTheCorrectCode()
    {
        var store = new EmailOtpStore(new Clock()); var issued = store.Issue("a@example.com", "registration", null);
        for (var i = 0; i < 5; i++) Assert.Throws<ArgumentException>(() => store.Consume(issued.ChallengeId, "a@example.com", "registration", "invalid"));
        Assert.Throws<ArgumentException>(() => store.Consume(issued.ChallengeId, "a@example.com", "registration", issued.Code));
    }

    [Fact]
    public void ResendingDoesNotResetWrongCodeBudget()
    {
        var clock = new Clock(); var store = new EmailOtpStore(clock);
        var first = store.Issue("a@example.com", "registration", null);
        for (int i = 0; i < 3; i++) Assert.Throws<ArgumentException>(() => store.Consume(first.ChallengeId, "a@example.com", "registration", "invalid"));
        clock.Now += TimeSpan.FromSeconds(60);
        var second = store.Issue("a@example.com", "registration", null);
        for (int i = 0; i < 2; i++) Assert.Throws<ArgumentException>(() => store.Consume(second.ChallengeId, "a@example.com", "registration", "invalid"));
        clock.Now += TimeSpan.FromSeconds(60);
        Assert.Throws<ArgumentException>(() => store.Issue("A@example.com", "registration", null));
        clock.Now += TimeSpan.FromMinutes(15);
        var fresh = store.Issue("a@example.com", "registration", "ok");
        Assert.Equal("ok", store.Consume(fresh.ChallengeId, "a@example.com", "registration", fresh.Code));
    }

    [Fact]
    public void MailSendBudgetPersistsAcrossChallengeConsumption()
    {
        var clock = new Clock(); var store = new EmailOtpStore(clock);
        for (int i = 0; i < 3; i++)
        {
            var issued = store.Issue("a@example.com", "password_reset", "ok");
            store.Consume(issued.ChallengeId, "a@example.com", "password_reset", issued.Code);
            clock.Now += TimeSpan.FromSeconds(60);
        }
        Assert.Throws<ArgumentException>(() => store.Issue("a@example.com", "password_reset", null));
        Assert.NotNull(store.Issue("b@example.com", "password_reset", null));
        Assert.NotNull(store.Issue("a@example.com", "registration", null));
    }
}
