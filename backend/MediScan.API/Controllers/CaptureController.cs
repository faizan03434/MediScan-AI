using System.Net.Http.Headers;
using System.Security.Claims;
using System.Text.Json;
using MediScan.Core.DTOs.Common;
using MediScan.Core.Entities;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.RateLimiting;

namespace MediScan.API.Controllers;

[ApiController, Authorize, Route("api/v1/capture")]
public sealed class CaptureController(IHttpClientFactory clients, IConfiguration config) : ControllerBase
{
    // Transient previews are neither scan records nor stored medical photos.
    [HttpPost("guide"), RequestSizeLimit(2 * 1024 * 1024), EnableRateLimiting("capture")]
    public async Task<IActionResult> Guide([FromForm] ScanType scanType, IFormFile image, CancellationToken cancellationToken)
    {
        var module = scanType switch { ScanType.Anemia => "anemia", ScanType.SkinDisease => "skin",
            ScanType.EyeDisease => "eye", ScanType.Posture => "posture", ScanType.Wound => "wound",
            ScanType.TongueDiagnosis => "tongue", _ => null };
        if (module == null || image.Length == 0 || image.Length > 1024 * 1024)
            return BadRequest(ApiResponse<object>.Fail("Use a valid capture module and preview under 1 MB."));
        if (!new[] { "image/jpeg", "image/png", "image/webp" }.Contains(image.ContentType.ToLowerInvariant()))
            return BadRequest(ApiResponse<object>.Fail("JPEG, PNG or WebP required."));
        Response.Headers.CacheControl = "no-store";
        try
        {
            using var client = clients.CreateClient("capture-guide");
            using var request = new HttpRequestMessage(HttpMethod.Post,
                $"{config["AiServer:Url"]?.TrimEnd('/')}/api/v1/capture/{module}");
            request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", config["AiServer:ApiKey"]);
            await using var stream = image.OpenReadStream();
            using var multipart = new MultipartFormDataContent();
            var file = new StreamContent(stream); file.Headers.ContentType = new MediaTypeHeaderValue(image.ContentType);
            multipart.Add(file, "image", "preview.jpg"); request.Content = multipart;
            using var response = await client.SendAsync(request, cancellationToken);
            if ((int)response.StatusCode == 429)
                return StatusCode(429, ApiResponse<object>.Fail("Live framing is busy. Wait a moment or use manual capture."));
            if ((int)response.StatusCode is 400 or 413 or 415 or 422)
                return BadRequest(ApiResponse<object>.Fail("Preview could not be read. Use a smaller, clear photo."));
            response.EnsureSuccessStatusCode();
            var data = await response.Content.ReadFromJsonAsync<JsonElement>(cancellationToken: cancellationToken);
            return Ok(ApiResponse<JsonElement>.Ok(data));
        }
        catch (HttpRequestException) { return StatusCode(503, ApiResponse<object>.Fail("Live framing unavailable. Manual capture still works.")); }
        catch (TaskCanceledException) when (!cancellationToken.IsCancellationRequested)
        { return StatusCode(503, ApiResponse<object>.Fail("Live framing timed out. Manual capture still works.")); }
    }
}
