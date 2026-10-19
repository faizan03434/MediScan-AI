using MediScan.Core.Entities;
using MediScan.Core.Interfaces;
using MediScan.Infra.Data;
using Microsoft.EntityFrameworkCore;

namespace MediScan.API.Services;

// Explicitly opt-in. Existing IsDeleted rows are a durable retry queue until purged.
public sealed class DeletedRecordPurger(AppDbContext db, IStorageService storage, ILogger<DeletedRecordPurger> logger)
{
    public async Task<int> RunAsync(CancellationToken ct)
    {
        var removed = 0;
        foreach (var scan in await db.ScanRecords.IgnoreQueryFilters().Where(s => s.IsDeleted).OrderBy(s => s.Id).Take(50).ToListAsync(ct))
            if (await Purge(scan, scan.Id, scan.UserId, scan.ImageBlobName, ct)) removed++;
        foreach (var medication in await db.MedicationRecords.IgnoreQueryFilters().Where(s => s.IsDeleted).OrderBy(s => s.Id).Take(50).ToListAsync(ct))
            if (await Purge(medication, medication.Id, medication.UserId, medication.ImageBlobName, ct)) removed++;
        foreach (var prescription in await db.PrescriptionRecords.IgnoreQueryFilters().Where(s => s.IsDeleted).OrderBy(s => s.Id).Take(50).ToListAsync(ct))
            if (await Purge(prescription, prescription.Id, prescription.UserId, prescription.ImageBlobName, ct)) removed++;
        return removed;
    }

    private async Task<bool> Purge(object record, Guid id, string owner, string? blob, CancellationToken ct)
    {
        try
        {
            ct.ThrowIfCancellationRequested();
            // A shared image remains until its last record reference is removed, even across owners.
            if (blob != null && !await ReferencedElsewhere(record, id, blob, ct)) await storage.DeleteAsync(blob);
            db.Remove(record);
            db.AuditLogs.Add(new AuditLog { UserId = owner, Action = "Retention.Purge", EntityType = record.GetType().Name,
                EntityId = id.ToString(), Success = true });
            await db.SaveChangesAsync(ct);
            return true;
        }
        catch (OperationCanceledException) when (ct.IsCancellationRequested) { throw; }
        catch (Exception)
        {
            // No successful deletion event or row removal on a failed storage operation.
            // Missing files are an idempotent success in both storage providers on retry.
            db.ChangeTracker.Clear();
            logger.LogWarning("Deleted-record purge failed; retained row will be retried. Category: {Category}", record.GetType().Name);
            return false;
        }
    }

    private async Task<bool> ReferencedElsewhere(object record, Guid id, string blob, CancellationToken ct) =>
        await db.ScanRecords.IgnoreQueryFilters().AnyAsync(s => s.ImageBlobName == blob && (!(record is ScanRecord) || s.Id != id), ct)
        || await db.MedicationRecords.IgnoreQueryFilters().AnyAsync(s => s.ImageBlobName == blob && (!(record is MedicationRecord) || s.Id != id), ct)
        || await db.PrescriptionRecords.IgnoreQueryFilters().AnyAsync(s => s.ImageBlobName == blob && (!(record is PrescriptionRecord) || s.Id != id), ct);
}

public sealed class DeletedRecordPurgeWorker(IServiceScopeFactory scopes, ILogger<DeletedRecordPurgeWorker> logger) : BackgroundService
{
    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        using var timer = new PeriodicTimer(TimeSpan.FromMinutes(5));
        do
        {
            try
            {
                using var scope = scopes.CreateScope();
                var count = await scope.ServiceProvider.GetRequiredService<DeletedRecordPurger>().RunAsync(stoppingToken);
                if (count > 0) logger.LogInformation("Deleted-record purge completed: {Count} rows", count);
            }
            catch (OperationCanceledException) when (stoppingToken.IsCancellationRequested) { return; }
            catch (Exception) { logger.LogError("Deleted-record purge batch unavailable; will retry."); }
        } while (await timer.WaitForNextTickAsync(stoppingToken));
    }
}
