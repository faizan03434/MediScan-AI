using MediScan.API.Services;
using MediScan.Core.Entities;
using MediScan.Core.Interfaces;
using MediScan.Infra.Data;
using Microsoft.Data.Sqlite;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging.Abstractions;

namespace MediScan.Tests;

public sealed class DeletedRecordPurgeTests
{
    private sealed class Storage : IStorageService
    {
        public bool Fail;
        public readonly HashSet<string> Files = ["scan.png", "medicine.png", "prescription.png", "shared.png"];
        public Task DeleteAsync(string name) { if (Fail) throw new IOException("fixture failure"); Files.Remove(name); return Task.CompletedTask; }
        public Task<Stream> DownloadAsync(string name) => throw new NotSupportedException();
        public Task<(string Url, string BlobName)> UploadAsync(Stream stream, string fileName, string contentType, string folder = "scans") => throw new NotSupportedException();
    }

    private sealed class Fixture : IAsyncDisposable
    {
        private readonly SqliteConnection connection = new("Data Source=:memory:");
        public AppDbContext Db = null!;
        public readonly Storage Storage = new();
        public DeletedRecordPurger Purger => new(Db, Storage, NullLogger<DeletedRecordPurger>.Instance);
        public async Task Initialize()
        {
            await connection.OpenAsync(); Db = new(new DbContextOptionsBuilder<AppDbContext>().UseSqlite(connection).Options);
            await Db.Database.EnsureCreatedAsync();
            Db.Users.AddRange(new ApplicationUser { Id = "owner" }, new ApplicationUser { Id = "other" });
            await Db.SaveChangesAsync();
        }
        public async ValueTask DisposeAsync() { await Db.DisposeAsync(); await connection.DisposeAsync(); }
    }

    [Fact]
    public async Task PurgesOnlyDeletedRecordsAndFilesWithMinimalAudit()
    {
        await using var f = new Fixture(); await f.Initialize();
        f.Db.ScanRecords.AddRange(new ScanRecord { UserId = "owner", IsDeleted = true, ImageBlobName = "scan.png", DetectionResult = "private result" },
            new ScanRecord { UserId = "other", IsDeleted = false, ImageBlobName = "shared.png" });
        f.Db.MedicationRecords.Add(new MedicationRecord { UserId = "owner", IsDeleted = true, ImageBlobName = "medicine.png", DrugName = "private medicine" });
        f.Db.PrescriptionRecords.Add(new PrescriptionRecord { UserId = "owner", IsDeleted = true, ImageBlobName = "prescription.png" });
        await f.Db.SaveChangesAsync();
        Assert.Equal(3, await f.Purger.RunAsync(default));
        Assert.Single(await f.Db.ScanRecords.IgnoreQueryFilters().ToListAsync());
        Assert.Empty(await f.Db.MedicationRecords.IgnoreQueryFilters().ToListAsync());
        Assert.Empty(await f.Db.PrescriptionRecords.IgnoreQueryFilters().ToListAsync());
        Assert.Single(f.Storage.Files); Assert.Contains("shared.png", f.Storage.Files);
        var audit = await f.Db.AuditLogs.ToListAsync(); Assert.Equal(3, audit.Count);
        Assert.All(audit, a => { Assert.Equal("Retention.Purge", a.Action); Assert.Null(a.NewValues); Assert.Null(a.OldValues); });
        Assert.Equal(0, await f.Purger.RunAsync(default));
    }

    [Fact]
    public async Task StorageFailureRetainsRowForRetryWithoutSuccessAudit()
    {
        await using var f = new Fixture(); await f.Initialize();
        f.Db.ScanRecords.Add(new ScanRecord { UserId = "owner", IsDeleted = true, ImageBlobName = "scan.png" }); await f.Db.SaveChangesAsync();
        f.Storage.Fail = true;
        Assert.Equal(0, await f.Purger.RunAsync(default));
        Assert.Single(await f.Db.ScanRecords.IgnoreQueryFilters().ToListAsync()); Assert.Empty(await f.Db.AuditLogs.ToListAsync());
        Assert.Contains("scan.png", f.Storage.Files);
        f.Storage.Fail = false;
        Assert.Equal(1, await f.Purger.RunAsync(default)); Assert.DoesNotContain("scan.png", f.Storage.Files);
    }

    [Fact]
    public async Task SharedPhotoSurvivesUntilLastRecordReferenceIsDeleted()
    {
        await using var f = new Fixture(); await f.Initialize();
        f.Db.ScanRecords.Add(new ScanRecord { UserId = "owner", IsDeleted = true, ImageBlobName = "shared.png" });
        var active = new PrescriptionRecord { UserId = "other", ImageBlobName = "shared.png" };
        f.Db.PrescriptionRecords.Add(active); await f.Db.SaveChangesAsync();
        Assert.Equal(1, await f.Purger.RunAsync(default)); Assert.Contains("shared.png", f.Storage.Files);
        active.IsDeleted = true; await f.Db.SaveChangesAsync();
        Assert.Equal(1, await f.Purger.RunAsync(default)); Assert.DoesNotContain("shared.png", f.Storage.Files);
    }
}
