using System.ComponentModel.DataAnnotations;
using System.Security.Cryptography;
using System.Text;
using MediScan.Core.Entities;
using MediScan.Core.Interfaces;
using MediScan.Infra.Data;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.WebUtilities;
using Microsoft.EntityFrameworkCore;

namespace MediScan.API.Services;

public sealed class DeleteAccountRequest
{
    [Required, RegularExpression("^DELETE$")] public string Confirmation { get; set; } = "";
    [StringLength(100)] public string? Password { get; set; }
    [StringLength(32, MinimumLength = 32)] public string? ChallengeId { get; set; }
    [RegularExpression("^[0-9]{6}$")] public string? Code { get; set; }
}
public sealed record DeletionReceipt(string Receipt, string Status, DateTime RequestedAt);
public sealed record DeletionStatus(string Status, DateTime RequestedAt, DateTime? CompletedAt);

public sealed class AccountDeletionService(AppDbContext db, UserManager<ApplicationUser> users,
    IEmailOtpStore codes, IVerificationEmailSender email, TimeProvider clock)
{
    public async Task<OtpChallenge> SendCodeAsync(string userId)
    {
        var user = await users.FindByIdAsync(userId);
        if (user?.IsActive != true || string.IsNullOrEmpty(user.Email)) throw new UnauthorizedAccessException();
        if (!email.IsConfigured) throw new AuthConfigurationException("Email delivery is not configured.");
        var issued = codes.Issue(user.Email, "account_deletion", user.Id);
        try { await email.SendCodeAsync(user.Email, issued.Code, "account_deletion"); }
        catch { codes.Cancel(issued.ChallengeId); throw new AuthConfigurationException("Email delivery failed. Your account has not been deleted."); }
        return new(issued.ChallengeId, issued.ExpiresAt, EmailOtpStore.ResendSeconds, "Check your email for the deletion verification code.");
    }

    public async Task<DeletionReceipt> RequestAsync(string userId, DeleteAccountRequest request)
    {
        if (request.Confirmation != "DELETE") throw new ArgumentException("Type DELETE to confirm account deletion.");
        var user = await users.FindByIdAsync(userId);
        if (user?.IsActive != true) throw new UnauthorizedAccessException("Account is inactive.");
        if (!string.IsNullOrEmpty(request.Password))
        {
            if (await users.IsLockedOutAsync(user)) throw new ArgumentException("Account is temporarily locked.");
            if (!await users.CheckPasswordAsync(user, request.Password))
            {
                await users.AccessFailedAsync(user);
                throw new ArgumentException("Password could not be verified.");
            }
            await users.ResetAccessFailedCountAsync(user);
        }
        else if (string.IsNullOrEmpty(user.Email) || string.IsNullOrEmpty(request.ChallengeId) || string.IsNullOrEmpty(request.Code)
            || (codes.Consume(request.ChallengeId, user.Email, "account_deletion", request.Code) as string) != user.Id)
            throw new ArgumentException("Verify your current password or a fresh email code.");
        if (user.Role == "Admin" && await db.Users.CountAsync(u => u.Role == "Admin" && u.IsActive) < 2)
            throw new ArgumentException("The last administrator requires an operator-managed account transfer before deletion.");
        var now = clock.GetUtcNow().UtcDateTime;
        var receipt = WebEncoders.Base64UrlEncode(RandomNumberGenerator.GetBytes(32));
        await using var transaction = await db.Database.BeginTransactionAsync();
        user.IsActive = false; user.UpdatedAt = now;
        var updated = await users.UpdateSecurityStampAsync(user);
        if (!updated.Succeeded) throw new InvalidOperationException("Account could not be disabled.");
        await db.RefreshTokens.Where(t => t.UserId == userId).ExecuteDeleteAsync();
        await db.PatientConsents.Where(c => c.PatientUserId == userId || c.DoctorUserId == userId)
            .ExecuteUpdateAsync(update => update.SetProperty(c => c.Status, ConsentStatus.Revoked).SetProperty(c => c.RevokedAt, now));
        db.AccountDeletionJobs.Add(new AccountDeletionJob { UserId = userId, ReceiptHash = ReceiptHash(receipt),
            RequestedAt = now, NextAttemptAt = now.AddMinutes(2) });
        db.AuditLogs.Add(new AuditLog { UserId = userId, Action = "Account.DeletionRequested", EntityType = "User" });
        await db.SaveChangesAsync();
        await transaction.CommitAsync();
        return new(receipt, "pending", now);
    }

    public async Task<DeletionStatus?> StatusAsync(string receipt)
    {
        if (receipt.Length != 43) return null;
        var hash = ReceiptHash(receipt);
        return await db.AccountDeletionJobs.AsNoTracking().Where(j => j.ReceiptHash == hash)
            .Select(j => new DeletionStatus(j.CompletedAt == null ? "pending" : "completed", j.RequestedAt, j.CompletedAt)).SingleOrDefaultAsync();
    }
    private static string ReceiptHash(string receipt) => Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(receipt)));
}

public sealed class AccountDeletionProcessor(AppDbContext db, IStorageService storage, IEmailOtpStore codes,
    TimeProvider clock, ILogger<AccountDeletionProcessor> logger)
{
    public async Task<int> RunAsync(CancellationToken ct)
    {
        var now = clock.GetUtcNow().UtcDateTime; var completed = 0;
        var ids = await db.AccountDeletionJobs.AsNoTracking().Where(j => j.CompletedAt == null && j.NextAttemptAt <= now
            && (j.LeaseUntil == null || j.LeaseUntil <= now)).OrderBy(j => j.NextAttemptAt).Take(10).Select(j => j.Id).ToListAsync(ct);
        foreach (var id in ids)
        {
            var leaseToken = Guid.NewGuid().ToString("N");
            var claimed = await db.AccountDeletionJobs.Where(j => j.Id == id && j.CompletedAt == null
                && (j.LeaseUntil == null || j.LeaseUntil <= now)).ExecuteUpdateAsync(update =>
                update.SetProperty(j => j.LeaseUntil, now.AddMinutes(10)).SetProperty(j => j.LeaseToken, leaseToken)
                    .SetProperty(j => j.Attempts, j => j.Attempts + 1), ct);
            if (claimed == 0) continue;
            var job = await db.AccountDeletionJobs.SingleAsync(j => j.Id == id, ct);
            await db.Entry(job).ReloadAsync(ct);
            try
            {
                await PurgeAsync(job, ct); completed++;
            }
            catch (OperationCanceledException) when (ct.IsCancellationRequested) { throw; }
            catch (Exception)
            {
                db.ChangeTracker.Clear();
                await db.AccountDeletionJobs.Where(j => j.Id == id && j.CompletedAt == null && j.LeaseToken == leaseToken).ExecuteUpdateAsync(update =>
                    update.SetProperty(j => j.LeaseUntil, (DateTime?)null).SetProperty(j => j.LeaseToken, (string?)null)
                        .SetProperty(j => j.NextAttemptAt, now.AddMinutes(5)), ct);
                logger.LogWarning("Account deletion cleanup failed; durable request will retry.");
            }
        }
        return completed;
    }

    private async Task PurgeAsync(AccountDeletionJob job, CancellationToken ct)
    {
        var owner = job.UserId ?? throw new InvalidOperationException("Missing deletion subject.");
        var user = await db.Users.AsNoTracking().SingleOrDefaultAsync(u => u.Id == owner, ct);
        if (user?.IsActive == true) throw new InvalidOperationException("Active account cannot be purged.");
        var scans = db.ScanRecords.IgnoreQueryFilters().Where(s => s.UserId == owner);
        var medicines = db.MedicationRecords.IgnoreQueryFilters().Where(m => m.UserId == owner);
        var prescriptions = db.PrescriptionRecords.IgnoreQueryFilters().Where(p => p.UserId == owner);
        var consents = db.PatientConsents.Where(c => c.PatientUserId == owner || c.DoctorUserId == owner);
        var blobs = await scans.Select(s => s.ImageBlobName).Union(medicines.Select(m => m.ImageBlobName))
            .Union(prescriptions.Select(p => p.ImageBlobName)).Union(db.StoredMedia.Where(m => m.UserId == owner).Select(m => (string?)m.BlobName))
            .Where(b => b != null).ToListAsync(ct);
        foreach (var blob in blobs)
        {
            ct.ThrowIfCancellationRequested();
            await RenewLease(job, ct);
            var shared = await db.ScanRecords.IgnoreQueryFilters().AnyAsync(s => s.UserId != owner && s.ImageBlobName == blob, ct)
                || await db.MedicationRecords.IgnoreQueryFilters().AnyAsync(m => m.UserId != owner && m.ImageBlobName == blob, ct)
                || await db.PrescriptionRecords.IgnoreQueryFilters().AnyAsync(p => p.UserId != owner && p.ImageBlobName == blob, ct)
                || await db.StoredMedia.AnyAsync(m => m.UserId != owner && m.BlobName == blob, ct);
            if (!shared) await storage.DeleteAsync(blob!).WaitAsync(TimeSpan.FromSeconds(30), ct);
        }
        if (user?.Email != null) codes.ForgetAccount(user.Email);
        var entityIds = (await scans.Select(s => s.Id).ToListAsync(ct))
            .Concat(await medicines.Select(m => m.Id).ToListAsync(ct)).Concat(await prescriptions.Select(p => p.Id).ToListAsync(ct))
            .Concat(await consents.Select(c => c.Id).ToListAsync(ct)).Select(id => id.ToString()).ToArray();
        await using var transaction = await db.Database.BeginTransactionAsync(ct);
        await RenewLease(job, ct);
        await medicines.ExecuteDeleteAsync(ct); await prescriptions.ExecuteDeleteAsync(ct); await scans.ExecuteDeleteAsync(ct);
        await consents.ExecuteDeleteAsync(ct);
        await db.RefreshTokens.Where(t => t.UserId == owner).ExecuteDeleteAsync(ct);
        await db.AuditLogs.Where(a => a.UserId == owner || a.EntityId == owner || (a.EntityId != null && entityIds.Contains(a.EntityId))).ExecuteDeleteAsync(ct);
        await db.StoredMedia.Where(m => m.UserId == owner).ExecuteDeleteAsync(ct);
        await db.Users.Where(u => u.Id == owner && !u.IsActive).ExecuteDeleteAsync(ct);
        job.UserId = null; job.CompletedAt = clock.GetUtcNow().UtcDateTime; job.LeaseUntil = null; job.LeaseToken = null;
        db.AuditLogs.Add(new AuditLog { Action = "Account.DeletionCompleted", EntityType = "DeletionJob", EntityId = job.Id.ToString() });
        await db.SaveChangesAsync(ct); await transaction.CommitAsync(ct);
    }

    private async Task RenewLease(AccountDeletionJob job, CancellationToken ct)
    {
        var renewed = await db.AccountDeletionJobs.Where(j => j.Id == job.Id && j.CompletedAt == null && j.LeaseToken == job.LeaseToken)
            .ExecuteUpdateAsync(update => update.SetProperty(j => j.LeaseUntil, clock.GetUtcNow().UtcDateTime.AddMinutes(10)), ct);
        if (renewed != 1) throw new InvalidOperationException("Deletion lease lost.");
    }
}

public sealed class AccountDeletionWorker(IServiceScopeFactory scopes, ILogger<AccountDeletionWorker> logger) : BackgroundService
{
    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        using var timer = new PeriodicTimer(TimeSpan.FromMinutes(1));
        do
        {
            try { using var scope = scopes.CreateScope(); await scope.ServiceProvider.GetRequiredService<AccountDeletionProcessor>().RunAsync(stoppingToken); }
            catch (OperationCanceledException) when (stoppingToken.IsCancellationRequested) { return; }
            catch (Exception) { logger.LogWarning("Account deletion queue unavailable; will retry."); }
        } while (await timer.WaitForNextTickAsync(stoppingToken));
    }
}
