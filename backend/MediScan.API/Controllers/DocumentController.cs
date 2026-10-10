using System.Security.Claims;
using MediScan.Core.DTOs.Common;
using MediScan.Core.Interfaces;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.RateLimiting;

namespace MediScan.API.Controllers;

[ApiController, Authorize, Route("api/v1/documents")]
public sealed class DocumentController(IDocumentOcrService ocr, IAuditService audit) : ControllerBase
{
    [HttpPost("ocr"), RequestSizeLimit(11 * 1024 * 1024), EnableRateLimiting("auth")]
    public async Task<IActionResult> Extract(IFormFile image, CancellationToken cancellationToken)
    {
        if (image.Length == 0 || image.Length > 10 * 1024 * 1024)
            return BadRequest(ApiResponse<object>.Fail("Choose an image under 10 MB."));
        if (!new[] { "image/jpeg", "image/png", "image/webp" }.Contains(image.ContentType.ToLowerInvariant()))
            return BadRequest(ApiResponse<object>.Fail("Only JPEG, PNG and WebP images are supported."));
        try
        {
            await using var stream = image.OpenReadStream();
            var result = await ocr.ExtractAsync(stream, image.ContentType, cancellationToken);
            await audit.LogAsync("Document.Ocr", "Document", userId: User.FindFirstValue(ClaimTypes.NameIdentifier));
            Response.Headers.CacheControl = "no-store";
            return Ok(ApiResponse<DocumentOcrResult>.Ok(result));
        }
        catch (HttpRequestException)
        { return StatusCode(503, ApiResponse<object>.Fail("Text extraction is temporarily unavailable. You can enter the medicine details manually.")); }
        catch (TaskCanceledException) when (!cancellationToken.IsCancellationRequested)
        { return StatusCode(503, ApiResponse<object>.Fail("Text extraction took too long. Try a smaller, clearer photo or enter details manually.")); }
    }
}
