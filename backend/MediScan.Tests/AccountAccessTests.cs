using System.IdentityModel.Tokens.Jwt;
using System.Security.Claims;
using System.Text.Json;
using MediScan.API.Controllers;
using MediScan.API.Services;
using MediScan.Core.DTOs.Auth;
using MediScan.Core.Entities;
using MediScan.Core.Interfaces;
using MediScan.Infra.Data;
using MediScan.Infra.Repositories;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Data.Sqlite;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;

namespace MediScan.Tests;

public partial class AccountAccessTests
{
    private sealed class TestClock : TimeProvider
    {
        public DateTimeOffset Now = DateTimeOffset.UtcNow;
        public override DateTimeOffset GetUtcNow() => Now;
    }
    private sealed class CapturedMail : IVerificationEmailSender
    {
        public bool IsConfigured { get; set; } = true;
        public bool Fail { get; set; }
        public List<(string Email, string Code, string Purpose)> Messages { get; } = [];
        public Task SendCodeAsync(string email, string code, string purpose)
        {
            if (Fail) throw new Exception("Simulated delivery failure");
            Messages.Add((email, code, purpose)); return Task.CompletedTask;
        }
    }
    private sealed class Google : IGoogleIdentityVerifier
    {
        public GoogleIdentity Identity { get; set; } = new("google-subject", "google@example.com", "Google Member");
        public Task<GoogleIdentity> VerifyAsync(string token) => Task.FromResult(Identity);
    }
    private sealed class Fixture : IAsyncDisposable
    {
        private readonly SqliteConnection connection = new("Data Source=:memory:");
        private ServiceProvider provider = null!;
        public readonly CapturedMail Mail = new();
        public readonly Google Google = new();
        public readonly TestClock Clock = new();
        public IEmailOtpStore Codes => provider.GetRequiredService<IEmailOtpStore>();
        public AccountAccessService Access => provider.GetRequiredService<AccountAccessService>();
        public IAuthService Auth => provider.GetRequiredService<IAuthService>();
        public UserManager<ApplicationUser> Users => provider.GetRequiredService<UserManager<ApplicationUser>>();
        public AppDbContext Db => provider.GetRequiredService<AppDbContext>();
        public async Task Initialize()
        {
            await connection.OpenAsync();
            var services = new ServiceCollection(); services.AddLogging(); services.AddDataProtection();
            services.AddSingleton<IConfiguration>(new ConfigurationBuilder().AddInMemoryCollection(new Dictionary<string, string?> {
                ["Jwt:Secret"] = "test-only-256-bit-secret-not-for-production-123456789", ["Jwt:Issuer"] = "tests", ["Jwt:Audience"] = "tests" }).Build());
            services.AddDbContext<AppDbContext>(o => o.UseSqlite(connection));
            services.AddIdentityCore<ApplicationUser>(o => { o.User.RequireUniqueEmail = true; o.Password.RequiredLength = 8; o.Password.RequireNonAlphanumeric = false; })
                .AddRoles<IdentityRole>().AddEntityFrameworkStores<AppDbContext>().AddDefaultTokenProviders();
            services.AddSingleton<TimeProvider>(Clock); services.AddSingleton<IEmailOtpStore, EmailOtpStore>();
            services.AddSingleton<IVerificationEmailSender>(Mail); services.AddSingleton<IGoogleIdentityVerifier>(Google);
            services.AddScoped<IAuthService, AuthService>(); services.AddScoped<AccountAccessService>();
            provider = services.BuildServiceProvider(); await Db.Database.EnsureCreatedAsync();
            await provider.GetRequiredService<RoleManager<IdentityRole>>().CreateAsync(new IdentityRole("User"));
        }
        public async ValueTask DisposeAsync() { await provider.DisposeAsync(); await connection.DisposeAsync(); }
    }
    private static RegisterDto Registration(string email = "member@example.com") => new() { Email = email, FullName = "Test Member", Password = "Password123", ConfirmPassword = "Password123" };
    private static AccountDataController DataController(Fixture f, string? id) => new(f.Db, f.Users, new AuditService(f.Db)) {
        ControllerContext = new ControllerContext { HttpContext = new DefaultHttpContext {
            User = new ClaimsPrincipal(new ClaimsIdentity(id == null ? [] : [new Claim(ClaimTypes.NameIdentifier, id)], "test")) } } };

    [Fact]
    public async Task AccountExportIsOwnerScopedAndExcludesCredentialsAndBlobPaths()
    {
        await using var f = new Fixture(); await f.Initialize();
        var owner = await f.Auth.RegisterAsync(Registration());
        var other = await f.Auth.RegisterAsync(Registration("other@example.com"));
        f.Db.ScanRecords.AddRange(new ScanRecord { UserId = owner.User.Id, DetectionResult = "owner retained", IsDeleted = true, ImageBlobName = "private-internal-path" },
            new ScanRecord { UserId = other.User.Id, DetectionResult = "other private result" });
        f.Db.MedicationRecords.AddRange(new MedicationRecord { UserId = owner.User.Id, DrugName = "owner medicine" },
            new MedicationRecord { UserId = other.User.Id, DrugName = "other private medicine" });
        f.Db.PrescriptionRecords.AddRange(new PrescriptionRecord { UserId = owner.User.Id, Notes = "owner notes" },
            new PrescriptionRecord { UserId = other.User.Id, Notes = "other private notes" });
        await f.Db.SaveChangesAsync();
        var controller = DataController(f, owner.User.Id);
        foreach (var section in new[] { "profile", "scans", "medications", "prescriptions", "consents" })
        {
            var result = Assert.IsType<OkObjectResult>(await controller.Export(section));
            var json = JsonSerializer.Serialize(result.Value);
            Assert.DoesNotContain("other private", json); Assert.DoesNotContain("other@example.com", json);
            Assert.DoesNotContain("PasswordHash", json); Assert.DoesNotContain("SecurityStamp", json);
            Assert.DoesNotContain("RefreshToken", json); Assert.DoesNotContain("private-internal-path", json);
            if (section == "scans") Assert.Contains("owner retained", json);
        }
        Assert.Equal("private, no-store", controller.Response.Headers.CacheControl.ToString());
        Assert.Equal(5, await f.Db.AuditLogs.CountAsync(a => a.UserId == owner.User.Id && a.Action == "Account.Export"));
        Assert.IsType<BadRequestObjectResult>(await controller.Export("credentials"));
        Assert.IsType<BadRequestObjectResult>(await controller.Export("scans", pageSize: 101));
        Assert.IsType<BadRequestObjectResult>(await controller.Export("scans", page: 0));
        Assert.IsType<UnauthorizedResult>(await DataController(f, null).Export("scans"));
    }

    [Fact]
    public async Task AllDeviceLogoutRotatesStampAndRevokesOnlyOwnersSessions()
    {
        await using var f = new Fixture(); await f.Initialize();
        var owner = await f.Auth.RegisterAsync(Registration());
        var second = await f.Auth.IssueTokensAsync(owner.User.Id);
        var other = await f.Auth.RegisterAsync(Registration("other@example.com"));
        var oldStamp = (await f.Users.FindByIdAsync(owner.User.Id))!.SecurityStamp;
        Assert.IsType<OkObjectResult>(await DataController(f, owner.User.Id).RevokeAll(default));
        Assert.NotEqual(oldStamp, (await f.Users.FindByIdAsync(owner.User.Id))!.SecurityStamp);
        await Assert.ThrowsAsync<UnauthorizedAccessException>(() => f.Auth.RefreshTokenAsync(owner.RefreshToken));
        await Assert.ThrowsAsync<UnauthorizedAccessException>(() => f.Auth.RefreshTokenAsync(second.RefreshToken));
        Assert.Equal(other.User.Id, (await f.Auth.RefreshTokenAsync(other.RefreshToken)).User.Id);
        Assert.Single(await f.Db.AuditLogs.Where(a => a.UserId == owner.User.Id && a.Action == "Auth.RevokeAll").ToListAsync());
        Assert.IsType<UnauthorizedResult>(await DataController(f, null).RevokeAll(default));
    }

    [Fact]
    public async Task RegistrationRequiresDeliveredCodeAndPreservesPasswordHash()
    {
        await using var f = new Fixture(); await f.Initialize();
        var challenge = await f.Access.RequestRegistrationAsync(Registration());
        Assert.Null(await f.Users.FindByEmailAsync("member@example.com"));
        Assert.Single(f.Mail.Messages);
        var response = await f.Access.VerifyRegistrationAsync(new() { Email = "member@example.com", ChallengeId = challenge.ChallengeId, Code = f.Mail.Messages[0].Code });
        var user = await f.Users.FindByIdAsync(response.User.Id);
        Assert.True(user!.EmailConfirmed); Assert.True(await f.Users.CheckPasswordAsync(user, "Password123"));
        Assert.NotEqual("Password123", user.PasswordHash);
        await Assert.ThrowsAsync<ArgumentException>(() => f.Access.VerifyRegistrationAsync(new() { Email = "member@example.com", ChallengeId = challenge.ChallengeId, Code = f.Mail.Messages[0].Code }));
        var rotated = await f.Auth.RefreshTokenAsync(response.RefreshToken);
        Assert.Equal(user.Id, rotated.User.Id);
        await Assert.ThrowsAsync<UnauthorizedAccessException>(() => f.Auth.RefreshTokenAsync(response.RefreshToken));
    }

    [Fact]
    public async Task ResetChangesPasswordStampAndRevokesExistingRefreshTokens()
    {
        await using var f = new Fixture(); await f.Initialize();
        var registered = await f.Auth.RegisterAsync(Registration());
        var stamp = new JwtSecurityTokenHandler().ReadJwtToken(registered.AccessToken).Claims.Single(c => c.Type == "sst").Value;
        var challenge = await f.Access.RequestResetAsync("member@example.com");
        await f.Access.ResetPasswordAsync(new() { Email = "member@example.com", ChallengeId = challenge.ChallengeId, Code = f.Mail.Messages[0].Code, Password = "NewPassword123", ConfirmPassword = "NewPassword123" });
        var user = await f.Users.FindByIdAsync(registered.User.Id);
        Assert.NotEqual(stamp, user!.SecurityStamp);
        Assert.False(await f.Users.CheckPasswordAsync(user, "Password123")); Assert.True(await f.Users.CheckPasswordAsync(user, "NewPassword123"));
        await Assert.ThrowsAsync<UnauthorizedAccessException>(() => f.Auth.RefreshTokenAsync(registered.RefreshToken));
    }

    [Fact]
    public async Task UnknownResetEmailHasSameChallengeShapeButNoMail()
    {
        await using var f = new Fixture(); await f.Initialize();
        var response = await f.Access.RequestResetAsync("unknown@example.com");
        Assert.Equal(32, response.ChallengeId.Length); Assert.Empty(f.Mail.Messages);
        Assert.Contains("If this email", response.Message);
    }

    [Fact]
    public async Task MissingSmtpAndDeliveryFailureNeverCreateUsers()
    {
        await using var f = new Fixture(); await f.Initialize();
        f.Mail.IsConfigured = false;
        await Assert.ThrowsAsync<AuthConfigurationException>(() => f.Access.RequestRegistrationAsync(Registration()));
        f.Mail.IsConfigured = true; f.Mail.Fail = true;
        await Assert.ThrowsAsync<AuthConfigurationException>(() => f.Access.RequestRegistrationAsync(Registration()));
        Assert.Empty(await f.Db.Users.ToListAsync());
    }

    [Fact]
    public async Task GoogleDoesNotAutomaticallyTakeOverPasswordAccounts()
    {
        await using var f = new Fixture(); await f.Initialize();
        var existing = await f.Auth.RegisterAsync(Registration("google@example.com"));
        await Assert.ThrowsAsync<ArgumentException>(() => f.Access.GoogleSignInAsync("verified-by-test-fake"));
        await f.Access.LinkGoogleAsync(existing.User.Id, "verified-by-test-fake");
        Assert.Equal(existing.User.Id, (await f.Access.GoogleSignInAsync("verified-by-test-fake")).User.Id);
        f.Google.Identity = new("another-subject", "different@example.com", "Other");
        await Assert.ThrowsAsync<ArgumentException>(() => f.Access.LinkGoogleAsync(existing.User.Id, "verified-by-test-fake"));
    }
}
