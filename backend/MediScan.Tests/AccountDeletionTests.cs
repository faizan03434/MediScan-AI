using System.Text.Json;
using MediScan.API.Services;
using MediScan.Core.Entities;
using MediScan.Core.Interfaces;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging.Abstractions;

namespace MediScan.Tests;

public partial class AccountAccessTests
{
    private sealed class DeletionStorage : IStorageService
    {
        public bool Fail;
        public int Uploads;
        public readonly HashSet<string> Files = ["scan.png", "medicine.png", "prescription.png", "inventory-only.png", "shared.png"];
        public Task DeleteAsync(string name) { if (Fail) throw new IOException("fixture"); Files.Remove(name); return Task.CompletedTask; }
        public Task<Stream> DownloadAsync(string name) => throw new NotSupportedException();
        public Task<(string Url, string BlobName)> UploadAsync(Stream stream, string name, string type, string folder = "scans")
        { Uploads++; Files.Add("uploaded.png"); return Task.FromResult(("/media/uploaded.png", "uploaded.png")); }
    }
    private static AccountDeletionService Deletion(Fixture f) => new(f.Db, f.Users, f.Codes, f.Mail, f.Clock);
    private static AccountDeletionProcessor Processor(Fixture f, IStorageService storage) => new(f.Db, storage, f.Codes, f.Clock, NullLogger<AccountDeletionProcessor>.Instance);
    private static DeleteAccountRequest Confirm(string? password = "Password123") => new() { Confirmation = "DELETE", Password = password };

    [Fact]
    public async Task DeletionRequiresConfirmationAndFreshProof()
    {
        await using var f = new Fixture(); await f.Initialize();
        var owner = await f.Auth.RegisterAsync(Registration());
        await Assert.ThrowsAsync<ArgumentException>(() => Deletion(f).RequestAsync(owner.User.Id, new() { Password = "Password123" }));
        await Assert.ThrowsAsync<ArgumentException>(() => Deletion(f).RequestAsync(owner.User.Id, Confirm("wrong password")));
        await Assert.ThrowsAsync<ArgumentException>(() => Deletion(f).RequestAsync(owner.User.Id, Confirm(null)));
        Assert.True((await f.Users.FindByIdAsync(owner.User.Id))!.IsActive);
        Assert.Empty(await f.Db.AccountDeletionJobs.ToListAsync());
        Assert.Equal(owner.User.Id, (await f.Auth.RefreshTokenAsync(owner.RefreshToken)).User.Id);
    }

    [Fact]
    public async Task AccountDeletionPurgesLiveAndHiddenRecordsInventoryConsentsIdentityAndOtp()
    {
        await using var f = new Fixture(); await f.Initialize(); var storage = new DeletionStorage();
        var owner = await f.Auth.RegisterAsync(Registration());
        var other = await f.Auth.RegisterAsync(Registration("other@example.com"));
        f.Db.ScanRecords.Add(new ScanRecord { UserId = owner.User.Id, ImageBlobName = "scan.png", IsDeleted = true });
        f.Db.MedicationRecords.Add(new MedicationRecord { UserId = owner.User.Id, DrugName = "private medicine", ImageBlobName = "medicine.png" });
        f.Db.PrescriptionRecords.AddRange(new PrescriptionRecord { UserId = owner.User.Id, ImageBlobName = "prescription.png" },
            new PrescriptionRecord { UserId = owner.User.Id, ImageBlobName = "shared.png" },
            new PrescriptionRecord { UserId = other.User.Id, ImageBlobName = "shared.png" });
        f.Db.StoredMedia.Add(new StoredMedia { UserId = owner.User.Id, BlobName = "inventory-only.png" });
        f.Db.PatientConsents.Add(new PatientConsent { PatientUserId = owner.User.Id, DoctorUserId = other.User.Id, Status = ConsentStatus.Granted });
        f.Db.AuditLogs.Add(new AuditLog { UserId = owner.User.Id, NewValues = "private payload" });
        await f.Db.SaveChangesAsync();
        var otp = f.Codes.Issue(owner.User.Email, "password_reset", owner.User.Id);
        var otherOtp = f.Codes.Issue(other.User.Email, "password_reset", other.User.Id);
        var receipt = await Deletion(f).RequestAsync(owner.User.Id, Confirm());
        Assert.Equal(43, receipt.Receipt.Length); Assert.Equal("pending", receipt.Status);
        Assert.False((await f.Users.FindByIdAsync(owner.User.Id))!.IsActive);
        Assert.Equal(ConsentStatus.Revoked, (await f.Db.PatientConsents.AsNoTracking().SingleAsync()).Status);
        await Assert.ThrowsAsync<UnauthorizedAccessException>(() => f.Auth.RefreshTokenAsync(owner.RefreshToken));
        Assert.Equal(0, await Processor(f, storage).RunAsync(default));
        f.Clock.Now += TimeSpan.FromMinutes(3);
        Assert.Equal(1, await Processor(f, storage).RunAsync(default));
        f.Db.ChangeTracker.Clear();
        Assert.Null(await f.Users.FindByIdAsync(owner.User.Id)); Assert.NotNull(await f.Users.FindByIdAsync(other.User.Id));
        Assert.Empty(await f.Db.ScanRecords.IgnoreQueryFilters().ToListAsync());
        Assert.Empty(await f.Db.MedicationRecords.IgnoreQueryFilters().ToListAsync());
        Assert.Single(await f.Db.PrescriptionRecords.IgnoreQueryFilters().ToListAsync());
        Assert.Empty(await f.Db.PatientConsents.ToListAsync()); Assert.Empty(await f.Db.StoredMedia.ToListAsync());
        Assert.Empty(await f.Db.RefreshTokens.Where(t => t.UserId == owner.User.Id).ToListAsync());
        Assert.Empty(await f.Db.AuditLogs.Where(a => a.UserId == owner.User.Id).ToListAsync());
        Assert.Equal(new[] { "shared.png" }, storage.Files.ToArray());
        Assert.Throws<ArgumentException>(() => f.Codes.Consume(otp.ChallengeId, owner.User.Email, "password_reset", otp.Code));
        Assert.Equal(other.User.Id, f.Codes.Consume(otherOtp.ChallengeId, other.User.Email, "password_reset", otherOtp.Code));
        var job = await f.Db.AccountDeletionJobs.SingleAsync(); Assert.Null(job.UserId); Assert.Null(job.LeaseToken);
        Assert.Equal("completed", (await Deletion(f).StatusAsync(receipt.Receipt))!.Status);
        Assert.DoesNotContain(owner.User.Email, JsonSerializer.Serialize(await Deletion(f).StatusAsync(receipt.Receipt)));
        Assert.Null(await Deletion(f).StatusAsync(new string('x', 43)));
        Assert.Equal(0, await Processor(f, storage).RunAsync(default));
    }

    [Fact]
    public async Task FailedDeletionKeepsInactiveAccountAndDurableJobThenRetries()
    {
        await using var f = new Fixture(); await f.Initialize(); var storage = new DeletionStorage { Fail = true };
        var owner = await f.Auth.RegisterAsync(Registration());
        f.Db.StoredMedia.Add(new StoredMedia { UserId = owner.User.Id, BlobName = "inventory-only.png" }); await f.Db.SaveChangesAsync();
        var receipt = await Deletion(f).RequestAsync(owner.User.Id, Confirm()); f.Clock.Now += TimeSpan.FromMinutes(3);
        Assert.Equal(0, await Processor(f, storage).RunAsync(default));
        Assert.Equal("pending", (await Deletion(f).StatusAsync(receipt.Receipt))!.Status);
        Assert.False((await f.Users.FindByIdAsync(owner.User.Id))!.IsActive);
        Assert.Single(await f.Db.StoredMedia.ToListAsync()); Assert.Contains("inventory-only.png", storage.Files);
        Assert.Equal(0, await Processor(f, storage).RunAsync(default));
        storage.Fail = false; f.Clock.Now += TimeSpan.FromMinutes(6);
        Assert.Equal(1, await Processor(f, storage).RunAsync(default));
        Assert.DoesNotContain("inventory-only.png", storage.Files);
    }

    [Fact]
    public async Task EmailCodeDeletionIsPurposeBoundAndDeliveryFailureDoesNotDisableAccount()
    {
        await using var f = new Fixture(); await f.Initialize(); var owner = await f.Auth.RegisterAsync(Registration());
        f.Mail.Fail = true;
        await Assert.ThrowsAsync<AuthConfigurationException>(() => Deletion(f).SendCodeAsync(owner.User.Id));
        Assert.True((await f.Users.FindByIdAsync(owner.User.Id))!.IsActive); Assert.Empty(await f.Db.AccountDeletionJobs.ToListAsync());
        f.Clock.Now += TimeSpan.FromSeconds(60); f.Mail.Fail = false;
        var challenge = await Deletion(f).SendCodeAsync(owner.User.Id);
        var request = Confirm(null); request.ChallengeId = challenge.ChallengeId; request.Code = f.Mail.Messages.Last().Code;
        Assert.Throws<ArgumentException>(() => f.Codes.Consume(challenge.ChallengeId, owner.User.Email, "password_reset", request.Code));
        Assert.Equal("pending", (await Deletion(f).RequestAsync(owner.User.Id, request)).Status);
    }

    [Fact]
    public async Task ExpiredWorkerLeaseIsRecoverableAfterRestart()
    {
        await using var f = new Fixture(); await f.Initialize(); var owner = await f.Auth.RegisterAsync(Registration());
        await Deletion(f).RequestAsync(owner.User.Id, Confirm());
        var job = await f.Db.AccountDeletionJobs.SingleAsync(); job.LeaseUntil = f.Clock.Now.UtcDateTime.AddMinutes(5); job.LeaseToken = "old-worker";
        await f.Db.SaveChangesAsync(); f.Clock.Now += TimeSpan.FromMinutes(3);
        Assert.Equal(0, await Processor(f, new DeletionStorage()).RunAsync(default));
        f.Clock.Now += TimeSpan.FromMinutes(3);
        Assert.Equal(1, await Processor(f, new DeletionStorage()).RunAsync(default));
    }

    [Fact]
    public async Task LastAdministratorCannotSelfDelete()
    {
        await using var f = new Fixture(); await f.Initialize(); var owner = await f.Auth.RegisterAsync(Registration());
        var user = (await f.Users.FindByIdAsync(owner.User.Id))!; user.Role = "Admin"; await f.Users.UpdateAsync(user);
        await Assert.ThrowsAsync<ArgumentException>(() => Deletion(f).RequestAsync(owner.User.Id, Confirm()));
        Assert.Empty(await f.Db.AccountDeletionJobs.ToListAsync()); Assert.True(user.IsActive);
    }

    [Fact]
    public async Task UploadInventoryCommitsBeforeReturnAndInactiveAccountsCannotUpload()
    {
        await using var f = new Fixture(); await f.Initialize(); var owner = await f.Auth.RegisterAsync(Registration());
        var storage = new DeletionStorage(); var guarded = new AccountStorageService(storage, f.Db);
        await guarded.UploadAsync(new MemoryStream([1]), "x.png", "image/png", "scans/" + owner.User.Id);
        Assert.Equal("uploaded.png", (await f.Db.StoredMedia.SingleAsync()).BlobName);
        await Deletion(f).RequestAsync(owner.User.Id, Confirm());
        await Assert.ThrowsAsync<UnauthorizedAccessException>(() => guarded.UploadAsync(new MemoryStream([1]), "x.png", "image/png", "scans/" + owner.User.Id));
        Assert.Equal(1, storage.Uploads);
    }
}
