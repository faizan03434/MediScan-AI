using MediScan.Core.DTOs.Common;
using MediScan.Core.DTOs.Scan;
using MediScan.Core.Entities;
using MediScan.Core.Interfaces;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using System.Security.Claims;

namespace MediScan.API.Controllers;

[ApiController]
[Route("api/v1/[controller]")]
[Authorize]
[Produces("application/json")]
public class ScanController : ControllerBase
{
    private readonly IScanService _scanService;

    public ScanController(IScanService scanService)
    {
        _scanService = scanService;
    }

    /// <summary>Submit a new scan (image upload)</summary>
    [HttpPost]
    [RequestSizeLimit(10 * 1024 * 1024)] // 10MB max
    public async Task<IActionResult> CreateScan(
        [FromForm] ScanType scanType,
        IFormFile? image)
    {
        var userId = User.FindFirstValue(ClaimTypes.NameIdentifier)!;

        if (!Enum.IsDefined(scanType) || image == null || image.Length == 0)
            return BadRequest(ApiResponse<object>.Fail("A valid scan type and image are required."));

        Stream? imageStream = null;
        string? contentType = null;

        if (image != null)
        {
            // Validate image
            var allowedTypes = new[] { "image/jpeg", "image/png", "image/webp" };
            if (!allowedTypes.Contains(image.ContentType.ToLower()))
                return BadRequest(ApiResponse<object>.Fail("Only JPEG, PNG, and WebP images are allowed."));

            if (image.Length > 10 * 1024 * 1024)
                return BadRequest(ApiResponse<object>.Fail("Image size must be under 10MB."));

            imageStream = image.OpenReadStream();
            contentType = image.ContentType;
        }

        var dto = new CreateScanDto { ScanType = scanType };
        var result = await _scanService.CreateScanAsync(userId, dto, imageStream, contentType);

        return Ok(ApiResponse<ScanResultDto>.Ok(result, "Scan submitted successfully."));
    }

    /// <summary>Get a specific scan by ID</summary>
    [HttpGet("{id:guid}")]
    public async Task<IActionResult> GetScan(Guid id)
    {
        var userId = User.FindFirstValue(ClaimTypes.NameIdentifier)!;
        var scan = await _scanService.GetScanByIdAsync(id, userId);

        if (scan == null)
            return NotFound(ApiResponse<object>.Fail("Scan not found."));

        return Ok(ApiResponse<ScanResultDto>.Ok(scan));
    }

    /// <summary>Get scan history with optional type filter and pagination</summary>
    [HttpGet("history")]
    public async Task<IActionResult> GetHistory(
        [FromQuery] ScanType? type = null,
        [FromQuery] int page = 1,
        [FromQuery] int pageSize = 10)
    {
        if (page < 1) page = 1;
        if (pageSize < 1 || pageSize > 50) pageSize = 10;

        var userId = User.FindFirstValue(ClaimTypes.NameIdentifier)!;
        var history = await _scanService.GetScanHistoryAsync(userId, type, page, pageSize);

        return Ok(ApiResponse<ScanHistoryDto>.Ok(history));
    }

    /// <summary>Get recent scans for dashboard</summary>
    [HttpGet("recent")]
    public async Task<IActionResult> GetRecent([FromQuery] int count = 5)
    {
        if (count < 1 || count > 20) count = 5;
        var userId = User.FindFirstValue(ClaimTypes.NameIdentifier)!;
        var scans = await _scanService.GetRecentScansAsync(userId, count);
        return Ok(ApiResponse<List<ScanResultDto>>.Ok(scans));
    }

    /// <summary>Compare two scans of the same type</summary>
    [HttpGet("compare")]
    public async Task<IActionResult> Compare(
        [FromQuery] Guid scan1Id,
        [FromQuery] Guid scan2Id)
    {
        var userId = User.FindFirstValue(ClaimTypes.NameIdentifier)!;
        var result = await _scanService.CompareScanAsync(scan1Id, scan2Id, userId);
        return Ok(ApiResponse<ScanResultDto>.Ok(result, "Comparison complete."));
    }

    /// <summary>Soft-delete a scan</summary>
    [HttpDelete("{id:guid}")]
    public async Task<IActionResult> DeleteScan(Guid id)
    {
        var userId = User.FindFirstValue(ClaimTypes.NameIdentifier)!;
        await _scanService.DeleteScanAsync(id, userId);
        return Ok(ApiResponse<object>.Ok(null!, "Scan deleted."));
    }
}
