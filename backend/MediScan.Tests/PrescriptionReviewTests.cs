using MediScan.Core.DTOs.Medication;
using MediScan.Core.Entities;
using MediScan.Core.Interfaces;
using MediScan.Core.Services;
using MediScan.Infra.Data;
using Microsoft.Data.Sqlite;
using Microsoft.EntityFrameworkCore;

namespace MediScan.Tests;

public class PrescriptionReviewTests
{
    private sealed class UnknownDrug : IDrugDataService
    {
        public Task<DrugInfoDto?> FetchByNameAsync(string name, string? country = null) => Task.FromResult<DrugInfoDto?>(null);
        public Task<DrugInfoDto?> FetchByBarcodeAsync(string barcode) => Task.FromResult<DrugInfoDto?>(null);
    }
    private sealed class Audit : IAuditService
    {
        public Task LogAsync(string action, string entityType, string? entityId = null, string? userId = null,
            string? oldValues = null, string? newValues = null, bool success = true, string? errorMessage = null,
            string? ipAddress = null, string? userAgent = null) => Task.CompletedTask;
        public Task<List<AuditLog>> GetLogsAsync(string? userId = null, string? action = null,
            DateTime? from = null, DateTime? to = null, int page = 1, int pageSize = 50) => Task.FromResult(new List<AuditLog>());
    }
    [Fact]
    public async Task UnconfirmedInputCannotCreateRecord()
    {
        var service = new MedicationService(null!, null!, null!, null!, null!);
        await Assert.ThrowsAsync<ArgumentException>(() => service.AnalyzePrescriptionAsync("user", new() { Notes = "Drug" }, Stream.Null, "image/png"));
    }
    [Fact]
    public async Task EmptyConfirmedListCannotCreateRecord()
    {
        var service = new MedicationService(null!, null!, null!, null!, null!);
        await Assert.ThrowsAsync<ArgumentException>(() => service.AnalyzePrescriptionAsync("user", new() { InputConfirmed = true }, Stream.Null, "image/png"));
    }
    [Fact]
    public async Task UnknownNameRemainsUnverifiedAndIsRetainedInHistory()
    {
        await using var connection = new SqliteConnection("Data Source=:memory:");
        await connection.OpenAsync();
        await using var db = new AppDbContext(new DbContextOptionsBuilder<AppDbContext>().UseSqlite(connection).Options);
        await db.Database.EnsureCreatedAsync();
        db.Users.Add(new ApplicationUser { Id = "user", FullName = "Synthetic test" });
        await db.SaveChangesAsync();
        var service = new MedicationService(db, new UnknownDrug(), null!, null!, new Audit());
        var result = await service.AnalyzePrescriptionAsync("user", new() { Notes = "Unknown Medicine", InputConfirmed = true,
            FromOcr = true, OcrRawText = "Printed OCR source" }, Stream.Null, "image/png");
        Assert.False(result.PrescriptionVerified);
        Assert.Equal("requires_clinician_review", result.VerificationStatus);
        Assert.False(Assert.Single(result.Medications).IsKnownDrug);
        Assert.Equal("Printed OCR source", result.OcrRawText);
        Assert.Equal(MedicationInputMethod.OcrScan, (await db.MedicationRecords.SingleAsync()).InputMethod);
        Assert.Equal(1, Assert.Single(await service.GetPrescriptionsAsync("user")).MedicationCount);
        Assert.Null(await service.GetPrescriptionByIdAsync(result.Id, "other-user"));
        await Assert.ThrowsAsync<ArgumentException>(() => service.SaveMedicationAsync("other-user", new() { DrugName = "Drug", PrescriptionRecordId = result.Id }));
    }
}
