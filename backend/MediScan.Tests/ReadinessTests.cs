using System.Net;
using MediScan.API.Controllers;
using MediScan.Infra.Data;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Data.Sqlite;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Configuration;

namespace MediScan.Tests;

public class ReadinessTests
{
    private sealed class Handler(bool available) : HttpMessageHandler
    {
        protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken ct) =>
            Task.FromResult(new HttpResponseMessage(available ? HttpStatusCode.OK : HttpStatusCode.ServiceUnavailable));
    }
    private sealed class Clients(bool available) : IHttpClientFactory { public HttpClient CreateClient(string name) => new(new Handler(available)); }
    [Theory]
    [InlineData(true, true, 200)] [InlineData(true, false, 503)] [InlineData(false, true, 503)]
    public async Task ReadinessChecksSchemaAndImageServiceWithoutClaimingClinicalReadiness(bool schema, bool imageService, int expected)
    {
        await using var connection = new SqliteConnection("Data Source=:memory:"); await connection.OpenAsync();
        await using var db = new AppDbContext(new DbContextOptionsBuilder<AppDbContext>().UseSqlite(connection).Options);
        if (schema) await db.Database.EnsureCreatedAsync();
        var config = new ConfigurationBuilder().AddInMemoryCollection(new Dictionary<string, string?> { ["AiServer:Url"] = "http://fixture.invalid" }).Build();
        var controller = new HealthController(db, new Clients(imageService), config) { ControllerContext = new() { HttpContext = new DefaultHttpContext() } };
        var result = Assert.IsType<ObjectResult>(await controller.Ready(default)); Assert.Equal(expected, result.StatusCode);
        var data = Assert.IsType<ReadinessResponse>(result.Value); Assert.Equal(schema, data.Database); Assert.Equal(imageService, data.ImageService);
        Assert.False(data.ClinicalInferenceEnabled); Assert.Equal("no-store", controller.Response.Headers.CacheControl.ToString());
    }

    [Fact]
    public async Task MigrationCreatesDeletionAndInventoryTables()
    {
        await using var connection = new SqliteConnection("Data Source=:memory:"); await connection.OpenAsync();
        await using var db = new AppDbContext(new DbContextOptionsBuilder<AppDbContext>().UseSqlite(connection).Options);
        await db.Database.MigrateAsync();
        Assert.Empty(await db.AccountDeletionJobs.ToListAsync()); Assert.Empty(await db.StoredMedia.ToListAsync());
    }
}
