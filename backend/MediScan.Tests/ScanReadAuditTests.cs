using MediScan.Core.Entities;
using MediScan.Core.Services;
using MediScan.Infra.Data;
using MediScan.Infra.Repositories;
using Microsoft.Data.Sqlite;
using Microsoft.EntityFrameworkCore;

namespace MediScan.Tests;

public class ScanReadAuditTests
{
    [Fact]
    public async Task ReadsAreOwnedAndAuditContainsNoMedicalPayload()
    {
        await using var connection = new SqliteConnection("Data Source=:memory:");
        await connection.OpenAsync();
        await using var db = new AppDbContext(new DbContextOptionsBuilder<AppDbContext>().UseSqlite(connection).Options);
        await db.Database.EnsureCreatedAsync();
        db.Users.AddRange(new ApplicationUser { Id = "owner", FullName = "Owner" },
            new ApplicationUser { Id = "other", FullName = "Other" });
        var own = new ScanRecord { UserId = "owner", ScanType = ScanType.SkinDisease, DetectionResult = "private symptom" };
        var other = new ScanRecord { UserId = "other", ScanType = ScanType.SkinDisease };
        db.ScanRecords.AddRange(own, other); await db.SaveChangesAsync();
        var service = new ScanService(db, null!, null!, null!, new AuditService(db));
        Assert.NotNull(await service.GetScanByIdAsync(own.Id, "owner"));
        Assert.Null(await service.GetScanByIdAsync(other.Id, "owner"));
        var history = await service.GetScanHistoryAsync("owner", null, 1, 10);
        Assert.Single(history.Scans);
        var recent = await service.GetRecentScansAsync("owner");
        Assert.Single(recent);
        var medication = new MedicationRecord { UserId = "owner", DrugName = "Private test drug" };
        db.MedicationRecords.Add(medication); await db.SaveChangesAsync();
        var medicineService = new MedicationService(db, null!, null!, null!, new AuditService(db));
        Assert.NotNull(await medicineService.GetByIdAsync(medication.Id, "owner"));
        Assert.Null(await medicineService.GetByIdAsync(medication.Id, "other"));
        Assert.Single((await medicineService.GetHistoryAsync("owner")).Items);
        Assert.Empty(await medicineService.GetPrescriptionsAsync("owner"));
        Assert.Null(await medicineService.GetPrescriptionByIdAsync(Guid.NewGuid(), "owner"));
        var logs = await db.AuditLogs.ToListAsync();
        Assert.Equal(9, logs.Count);
        Assert.All(logs, log => { Assert.Null(log.NewValues); Assert.Null(log.OldValues); });
        Assert.Contains(logs, log => log.Action == "Scan.Read" && !log.Success && log.EntityId == null);
        Assert.Contains(logs, log => log.Action == "Medication.Read" && log.UserId == "other" && !log.Success && log.EntityId == null);
    }
}
