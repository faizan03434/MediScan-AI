using Microsoft.AspNetCore.Mvc;
using MediScan.Infra.Data;
using Microsoft.EntityFrameworkCore;

namespace MediScan.API.Controllers;

public sealed record ReadinessResponse(string Status, bool Database, bool ImageService, bool ClinicalInferenceEnabled);

[ApiController]
[Route("api/v1/[controller]")]
public class HealthController(AppDbContext db, IHttpClientFactory clients, IConfiguration config) : ControllerBase
{
    /// <summary>API health check</summary>
    [HttpGet]
    public IActionResult Check() =>
        Ok(new { Status = "Healthy", Timestamp = DateTime.UtcNow, Version = "1.0.0" });

    [HttpGet("ready")]
    public async Task<IActionResult> Ready(CancellationToken cancellationToken)
    {
        Response.Headers.CacheControl = "no-store";
        using var deadline = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
        deadline.CancelAfter(TimeSpan.FromSeconds(5));
        var database = false; var imageService = false;
        try
        {
            await db.Users.AsNoTracking().AnyAsync(deadline.Token);
            await db.AccountDeletionJobs.AsNoTracking().AnyAsync(deadline.Token);
            database = true;
        }
        catch (Exception) when (!cancellationToken.IsCancellationRequested) { }
        try
        {
            using var client = clients.CreateClient("readiness");
            using var response = await client.GetAsync($"{config["AiServer:Url"]?.TrimEnd('/')}/health/live", HttpCompletionOption.ResponseHeadersRead, deadline.Token);
            imageService = response.IsSuccessStatusCode;
        }
        catch (Exception) when (!cancellationToken.IsCancellationRequested) { }
        var ready = database && imageService;
        return StatusCode(ready ? 200 : 503, new ReadinessResponse(ready ? "ready" : "unavailable", database, imageService, false));
    }
}
