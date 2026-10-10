using System.Security.Claims;
using MediScan.Core.Interfaces;
using MediScan.Infra.Data;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;

namespace MediScan.API.Controllers;

[ApiController, Authorize, Route("api/v1/media")]
public class MediaController(AppDbContext db, IStorageService storage, IAuditService audit) : ControllerBase
{
    [HttpGet("{**blobName}")]
    public async Task<IActionResult> Get(string blobName)
    {
        var userId = User.FindFirstValue(ClaimTypes.NameIdentifier)!;
        var ownsScan = await db.ScanRecords.AnyAsync(s => s.UserId == userId && s.ImageBlobName == blobName);
        var ownsPrescription = await db.PrescriptionRecords.AnyAsync(s => s.UserId == userId && s.ImageBlobName == blobName);
        if (!ownsScan && !ownsPrescription) return NotFound();
        var stream = await storage.DownloadAsync(blobName);
        await audit.LogAsync("Media.Read", "Media", blobName, userId);
        Response.Headers.CacheControl = "no-store";
        // Detect the format from its signature; stored names may use .jpg for PNG/WebP uploads.
        var bytes = new byte[12];
        var count = await stream.ReadAsync(bytes);
        stream.Position = 0;
        var mime = count >= 8 && bytes[0] == 137 && bytes[1] == 80 ? "image/png"
            : count >= 12 && bytes[0] == 82 && bytes[8] == 87 ? "image/webp" : "image/jpeg";
        return File(stream, mime);
    }
}
