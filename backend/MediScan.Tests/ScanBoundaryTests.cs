using System.Net;
using System.Text;
using MediScan.Core.Entities;
using MediScan.Core.Interfaces;
using MediScan.Core.Services;
using MediScan.Infra.Data;
using MediScan.Infra.External;
using MediScan.Infra.Repositories;
using Microsoft.Data.Sqlite;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Configuration;

namespace MediScan.Tests;

public class ScanBoundaryTests
{
    private sealed class Handler(HttpContent content) : HttpMessageHandler
    {
        public string? Authorization;
        protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken ct)
        {
            Authorization = request.Headers.Authorization?.ToString();
            return Task.FromResult(new HttpResponseMessage(HttpStatusCode.OK) { Content = content });
        }
    }
    private static AiInferenceService Service(HttpClient client) => new(client,
        new ConfigurationBuilder().AddInMemoryCollection(new Dictionary<string, string?> {
            ["AiServer:Url"] = "http://fixture.invalid", ["AiServer:ApiKey"] = "fixture-key" }).Build());
    private sealed class Nonseekable(byte[] bytes) : MemoryStream(bytes) { public override bool CanSeek => false; }

    [Fact]
    public async Task UpstreamClinicalFlagsDrugsAndScoresCannotOverrideReleasePolicy()
    {
        var handler = new Handler(new StringContent("""{"result":"Private diagnosis","confidence":0.999,"details":{"module":"skin","clinical_inference":true,"clinical_approved":true,"private":"private-patient"},"recommendation":"Take private-drug","next_scan_days":1}""", Encoding.UTF8, "application/json"));
        using var client = new HttpClient(handler);
        var response = await Service(client).RunInferenceAsync(ScanType.SkinDisease, new MemoryStream([1]), "image/png");
        Assert.Contains("Inconclusive", response.DetectionResult); Assert.Equal(0, response.ConfidenceScore);
        Assert.Null(response.NextScanDays); Assert.DoesNotContain("private", response.DetectionDetails!);
        Assert.DoesNotContain("private-drug", response.Recommendation!);
        Assert.Equal("Bearer fixture-key", handler.Authorization); Assert.Null(client.DefaultRequestHeaders.Authorization);
    }

    [Theory]
    [InlineData("[]")]
    [InlineData("not-json")]
    [InlineData("{\"result\":\"x\",\"confidence\":\"private\",\"details\":{}}")]
    [InlineData("{\"result\":\"x\",\"confidence\":2,\"details\":{}}")]
    [InlineData("{\"result\":\"x\",\"confidence\":0,\"details\":{\"module\":\"retina\"}}")]
    public async Task InvalidOrWrongTaskMetadataFailsClosed(string body)
    {
        using var client = new HttpClient(new Handler(new StringContent(body)));
        await Assert.ThrowsAsync<HttpRequestException>(() => Service(client).RunInferenceAsync(ScanType.SkinDisease, new MemoryStream([1]), "image/png"));
    }

    [Theory] [InlineData(true)] [InlineData(false)]
    public async Task ResponseBudgetsApplyToDeclaredAndStreamingBodies(bool knownLength)
    {
        var bytes = Encoding.UTF8.GetBytes(new string('x', 65537));
        HttpContent content = knownLength ? new ByteArrayContent(bytes) : new StreamContent(new Nonseekable(bytes));
        using var client = new HttpClient(new Handler(content));
        await Assert.ThrowsAsync<HttpRequestException>(() => Service(client).RunInferenceAsync(ScanType.Anemia, new MemoryStream([1]), "image/png"));
    }

    private sealed class Storage : IStorageService
    {
        public Task<(string Url, string BlobName)> UploadAsync(Stream stream, string file, string contentType, string folder = "scans") => Task.FromResult(("/api/v1/media/fixture.png", "scans/owner/fixture.png"));
        public Task DeleteAsync(string blobName) => Task.CompletedTask;
        public Task<Stream> DownloadAsync(string blobName) => Task.FromResult<Stream>(new MemoryStream([1]));
    }
    private sealed class Ai(bool fail) : IAiInferenceService
    {
        public Task<AiInferenceResult> RunInferenceAsync(ScanType type, Stream stream, string contentType) => fail
            ? throw new HttpRequestException("private-patient-id and private-drug")
            : Task.FromResult(new AiInferenceResult { DetectionResult = "private diagnosis", ConfidenceScore = .99f,
                Recommendation = "Take private-drug", NextScanDays = 1, DetectionDetails = "{\"clinical_inference\":true}" });
    }

    [Theory] [InlineData(false)] [InlineData(true)]
    public async Task PersistenceAndFailureAuditNeverContainUnapprovedMedicalPayloads(bool fail)
    {
        await using var connection = new SqliteConnection("Data Source=:memory:"); await connection.OpenAsync();
        await using var db = new AppDbContext(new DbContextOptionsBuilder<AppDbContext>().UseSqlite(connection).Options);
        await db.Database.EnsureCreatedAsync(); db.Users.Add(new() { Id = "owner", FullName = "Synthetic" }); await db.SaveChangesAsync();
        var service = new ScanService(db, new Storage(), new Ai(fail), new AuditService(db));
        if (fail) await Assert.ThrowsAsync<HttpRequestException>(() => service.CreateScanAsync("owner", new() { ScanType = ScanType.Anemia }, new MemoryStream([1]), "image/png"));
        else await service.CreateScanAsync("owner", new() { ScanType = ScanType.Anemia }, new MemoryStream([1]), "image/png");
        var scan = await db.ScanRecords.SingleAsync(); var log = await db.AuditLogs.SingleAsync();
        Assert.Equal(fail ? ScanStatus.Failed : ScanStatus.Completed, scan.Status);
        Assert.Null(scan.ConfidenceScore); Assert.Null(scan.NextScanDate);
        Assert.DoesNotContain("private", scan.DetectionResult ?? ""); Assert.DoesNotContain("private", scan.AiRecommendation ?? "");
        Assert.DoesNotContain("private", log.ErrorMessage ?? "");
        if (fail) Assert.Equal("scan_processing_failed", log.ErrorMessage);
    }

    [Fact]
    public async Task HistoricalUnvalidatedValuesStayInSourceRecordsButAreNotClinicalDisplayClaims()
    {
        await using var connection = new SqliteConnection("Data Source=:memory:"); await connection.OpenAsync();
        await using var db = new AppDbContext(new DbContextOptionsBuilder<AppDbContext>().UseSqlite(connection).Options);
        await db.Database.EnsureCreatedAsync(); db.Users.Add(new() { Id = "owner", FullName = "Synthetic" });
        var old = new ScanRecord { UserId = "owner", Status = ScanStatus.Completed, DetectionResult = "old-private-claim", ConfidenceScore = .99f, AiRecommendation = "private-drug", NextScanDate = DateTime.UtcNow.AddDays(1) };
        db.ScanRecords.Add(old); await db.SaveChangesAsync();
        var result = await new ScanService(db, null!, null!, new AuditService(db)).GetScanByIdAsync(old.Id, "owner");
        Assert.Contains("Inconclusive", result!.DetectionResult); Assert.Null(result.ConfidenceScore); Assert.Null(result.NextScanDate);
        Assert.Equal("old-private-claim", (await db.ScanRecords.SingleAsync()).DetectionResult);
    }
}
