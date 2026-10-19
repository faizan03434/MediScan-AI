using MediScan.Infra.Data;
using MediScan.Core.Entities;
using Microsoft.EntityFrameworkCore;
using Npgsql;
using MediScan.API.Services;
using Microsoft.AspNetCore.DataProtection;
using MediScan.Infra.Repositories;
using MediScan.Core.Interfaces;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.AspNetCore.Identity;
using MediScan.API.Controllers;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using System.Security.Claims;

namespace MediScan.Tests;

public sealed class PostgresFactAttribute : FactAttribute
{
    public PostgresFactAttribute()
    {
        if (string.IsNullOrWhiteSpace(Environment.GetEnvironmentVariable("MEDISCAN_TEST_POSTGRES")))
            Skip = "Set MEDISCAN_TEST_POSTGRES for isolated PostgreSQL integration tests.";
    }
}

public class PostgresIntegrationTests
{
    private static ServiceProvider AuthProvider(string connection)
    {
        var services = new ServiceCollection(); services.AddLogging(); services.AddDataProtection();
        services.AddSingleton<IConfiguration>(new ConfigurationBuilder().AddInMemoryCollection(new Dictionary<string, string?> {
            ["Jwt:Secret"] = "test-only-256-bit-secret-not-for-production-123456789", ["Jwt:Issuer"] = "tests", ["Jwt:Audience"] = "tests" }).Build());
        services.AddDbContext<AppDbContext>(o => DatabaseOptions.Configure(o, connection, "postgresql", Directory.GetCurrentDirectory()));
        services.AddIdentityCore<ApplicationUser>().AddRoles<IdentityRole>().AddEntityFrameworkStores<AppDbContext>();
        services.AddScoped<IAuthService, AuthService>();
        return services.BuildServiceProvider();
    }

    [PostgresFact]
    public async Task ConcurrentRefreshClientsCanConsumeBearerOnlyOnce()
    {
        await using var fixture = new Database(); await fixture.Initialize();
        await using var provider = AuthProvider(fixture.ConnectionString);
        string refresh;
        using (var setup = provider.CreateScope())
        {
            await setup.ServiceProvider.GetRequiredService<RoleManager<IdentityRole>>().CreateAsync(new("User"));
            refresh = (await setup.ServiceProvider.GetRequiredService<IAuthService>().RegisterAsync(new() {
                Email = "synthetic@example.com", FullName = "Synthetic", Password = "Password123!", ConfirmPassword = "Password123!" })).RefreshToken;
        }
        var results = await Task.WhenAll(Enumerable.Range(0, 8).Select(async _ => {
            using var scope = provider.CreateScope();
            try { return (await scope.ServiceProvider.GetRequiredService<IAuthService>().RefreshTokenAsync(refresh)).RefreshToken; }
            catch (UnauthorizedAccessException) { return null; }
        }));
        var rotated = Assert.Single(results, result => result != null)!;
        await using var db = fixture.Context();
        var tokens = await db.RefreshTokens.AsNoTracking().ToListAsync();
        Assert.Equal(2, tokens.Count); Assert.Single(tokens, t => t.RevokedAt == null);
        Assert.DoesNotContain(tokens, t => t.Token == refresh || t.Token == rotated);
    }

    [PostgresFact]
    public async Task ConcurrentSelfDemotionsCannotRemoveBothAdministrators()
    {
        await using var fixture = new Database(); await fixture.Initialize();
        await using var provider = AuthProvider(fixture.ConnectionString);
        var actors = new List<(string Id, string Stamp)>();
        using (var setup = provider.CreateScope())
        {
            var roles = setup.ServiceProvider.GetRequiredService<RoleManager<IdentityRole>>();
            foreach (var role in new[] { "User", "Admin" }) Assert.True((await roles.CreateAsync(new(role))).Succeeded);
            var users = setup.ServiceProvider.GetRequiredService<UserManager<ApplicationUser>>();
            foreach (var email in new[] { "one@example.com", "two@example.com" })
            {
                var user = new ApplicationUser { UserName = email, Email = email, FullName = "Synthetic", Role = "Admin", IsActive = true };
                Assert.True((await users.CreateAsync(user)).Succeeded); Assert.True((await users.AddToRoleAsync(user, "Admin")).Succeeded);
                actors.Add((user.Id, user.SecurityStamp!));
            }
        }
        var statuses = await Task.WhenAll(actors.Select(async actor => {
            using var scope = provider.CreateScope(); var db = scope.ServiceProvider.GetRequiredService<AppDbContext>();
            var controller = new AdminController(db, scope.ServiceProvider.GetRequiredService<UserManager<ApplicationUser>>(), new AuditService(db)) {
                ControllerContext = new() { HttpContext = new DefaultHttpContext { User = new ClaimsPrincipal(new ClaimsIdentity([
                    new Claim(ClaimTypes.NameIdentifier, actor.Id), new Claim("sst", actor.Stamp) ], "test")) } } };
            return Assert.IsAssignableFrom<ObjectResult>(await controller.UpdateUserRole(actor.Id, new() { Role = "User" })).StatusCode;
        }));
        Assert.Single(statuses, status => status == 200); Assert.Single(statuses, status => status == 409);
        await using var verify = fixture.Context(); Assert.Equal(1, await verify.Users.CountAsync(u => u.IsActive && u.Role == "Admin"));
    }
    private sealed class Clock : TimeProvider
    {
        public DateTimeOffset Now = DateTimeOffset.UtcNow;
        public override DateTimeOffset GetUtcNow() => Now;
    }
    private sealed class Database : IAsyncDisposable
    {
        private readonly string adminConnection;
        private readonly string name = "mediscan_test_" + Guid.NewGuid().ToString("N");
        public string ConnectionString { get; private set; } = "";
        public Database() => adminConnection = Environment.GetEnvironmentVariable("MEDISCAN_TEST_POSTGRES")!;
        public AppDbContext Context()
        {
            var options = new DbContextOptionsBuilder<AppDbContext>();
            DatabaseOptions.Configure(options, ConnectionString, "postgresql", Directory.GetCurrentDirectory());
            return new(options.Options);
        }
        public async Task Initialize()
        {
            await using var connection = new NpgsqlConnection(adminConnection); await connection.OpenAsync();
            await using var command = new NpgsqlCommand($"CREATE DATABASE \"{name}\"", connection); await command.ExecuteNonQueryAsync();
            var settings = new NpgsqlConnectionStringBuilder(adminConnection) { Database = name, Pooling = false };
            ConnectionString = settings.ToString();
            await using var db = Context(); await db.Database.MigrateAsync();
        }
        public async ValueTask DisposeAsync()
        {
            if (!name.StartsWith("mediscan_test_", StringComparison.Ordinal) || name.Length != 46) throw new InvalidOperationException("Unsafe test database name.");
            await using var connection = new NpgsqlConnection(adminConnection); await connection.OpenAsync();
            await using var command = new NpgsqlCommand($"DROP DATABASE IF EXISTS \"{name}\" WITH (FORCE)", connection); await command.ExecuteNonQueryAsync();
        }
    }

    [PostgresFact]
    public async Task FreshProductionSchemaMigratesAndRoundTripsActualProviderTypes()
    {
        await using var fixture = new Database(); await fixture.Initialize();
        await using var db = fixture.Context();
        Assert.False((await db.Database.GetPendingMigrationsAsync()).Any());
        var owner = new ApplicationUser { Id = Guid.NewGuid().ToString(), FullName = "Synthetic", IsActive = true };
        db.Users.Add(owner); await db.SaveChangesAsync();
        var scan = new ScanRecord { UserId = owner.Id, ScanType = ScanType.Retina, CreatedAt = DateTime.UtcNow };
        db.ScanRecords.Add(scan); db.AccountDeletionJobs.Add(new AccountDeletionJob { UserId = owner.Id, ReceiptHash = new string('A', 64),
            RequestedAt = DateTime.UtcNow, NextAttemptAt = DateTime.UtcNow });
        await db.SaveChangesAsync(); db.ChangeTracker.Clear();
        Assert.True((await db.Users.SingleAsync()).IsActive); Assert.Equal(ScanType.Retina, (await db.ScanRecords.SingleAsync()).ScanType);
        Assert.Equal(DateTimeKind.Utc, (await db.AccountDeletionJobs.SingleAsync()).RequestedAt.Kind);
        Assert.Empty(await db.PatientConsents.ToListAsync());
    }

    [PostgresFact]
    public async Task CentralOtpSurvivesInstancesAndSharesFailureAndResendBudgets()
    {
        await using var fixture = new Database(); await fixture.Initialize(); var clock = new Clock();
        var provider = new EphemeralDataProtectionProvider();
        PostgresEmailOtpStore Store() => new(fixture.ConnectionString, clock, provider);
        var first = Store().Issue("a@example.com", "password_reset", "private-user-id");
        Assert.Equal("private-user-id", Store().Consume(first.ChallengeId, "a@example.com", "password_reset", first.Code));
        Assert.Throws<ArgumentException>(() => Store().Issue("a@example.com", "password_reset", null));
        clock.Now += TimeSpan.FromSeconds(61);
        var second = Store().Issue("a@example.com", "password_reset", "private-user-id");
        for (int i = 0; i < 5; i++) Assert.Throws<ArgumentException>(() => Store().Consume(second.ChallengeId, "a@example.com", "password_reset", "wrong"));
        Assert.Throws<ArgumentException>(() => Store().Consume(second.ChallengeId, "a@example.com", "password_reset", second.Code));
        clock.Now += TimeSpan.FromSeconds(61);
        Assert.Throws<ArgumentException>(() => Store().Issue("a@example.com", "password_reset", null));
        clock.Now += TimeSpan.FromMinutes(15);
        var fresh = Store().Issue("a@example.com", "password_reset", "private-user-id");
        await using (var connection = new NpgsqlConnection(fixture.ConnectionString))
        {
            await connection.OpenAsync(); await using var query = new NpgsqlCommand("SELECT payload FROM email_verification", connection);
            var encrypted = (string)(await query.ExecuteScalarAsync())!;
            Assert.DoesNotContain("private-user-id", encrypted); Assert.DoesNotContain(fresh.Code, encrypted);
        }
        Store().ForgetAccount(" A@example.com ");
        Assert.Throws<ArgumentException>(() => Store().Consume(fresh.ChallengeId, "a@example.com", "password_reset", fresh.Code));
    }

    [PostgresFact]
    public async Task ConcurrentCentralOtpClientsCannotDoubleIssueOrConsume()
    {
        await using var fixture = new Database(); await fixture.Initialize(); var provider = new EphemeralDataProtectionProvider();
        PostgresEmailOtpStore Store() => new(fixture.ConnectionString, TimeProvider.System, provider);
        var issued = await Task.WhenAll(Enumerable.Range(0, 8).Select(_ => Task.Run(() => {
            try { return Store().Issue("a@example.com", "account_deletion", "id"); } catch (ArgumentException) { return null; }
        })));
        var challenge = Assert.Single(issued, value => value != null)!;
        var consumed = await Task.WhenAll(Enumerable.Range(0, 8).Select(_ => Task.Run(() => {
            try { return Store().Consume(challenge.ChallengeId, "a@example.com", "account_deletion", challenge.Code) as string; }
            catch (ArgumentException) { return null; }
        })));
        Assert.Equal("id", Assert.Single(consumed, value => value != null));
    }
}
