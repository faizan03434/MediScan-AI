using MediScan.Core.DTOs.Common;
using MediScan.Core.DTOs.Medication;
using MediScan.Core.Interfaces;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using System.Security.Claims;

namespace MediScan.API.Controllers;

[ApiController]
[Route("api/v1/[controller]")]
[Authorize]
[Produces("application/json")]
public class MedicationController : ControllerBase
{
    private readonly IMedicationService _medicationService;
    private readonly IAuditService _audit;

    public MedicationController(IMedicationService medicationService, IAuditService audit)
    {
        _medicationService = medicationService;
        _audit = audit;
    }

    // ── Drug search ───────────────────────────────────────────

    /// <summary>Search drug by name — fetches from OpenFDA + Pakistan DAP</summary>
    [HttpGet("search")]
    [ProducesResponseType(typeof(ApiResponse<DrugInfoDto>), 200)]
    public async Task<IActionResult> SearchByName(
        [FromQuery] string q,
        [FromQuery] string? country = null)
    {
        if (string.IsNullOrWhiteSpace(q) || q.Length < 2)
            return BadRequest(ApiResponse<object>.Fail("Search query must be at least 2 characters."));

        var result = await _medicationService.SearchByNameAsync(q, country);
        return Ok(ApiResponse<DrugInfoDto>.Ok(result));
    }

    /// <summary>Search drug by barcode (EAN-13, EAN-8, QR code)</summary>
    [HttpGet("barcode/{barcode}")]
    [ProducesResponseType(typeof(ApiResponse<DrugInfoDto>), 200)]
    public async Task<IActionResult> SearchByBarcode(string barcode)
    {
        if (string.IsNullOrWhiteSpace(barcode))
            return BadRequest(ApiResponse<object>.Fail("Barcode is required."));

        var result = await _medicationService.SearchByBarcodeAsync(barcode);
        return Ok(ApiResponse<DrugInfoDto>.Ok(result));
    }

    // ── Medication history ────────────────────────────────────

    /// <summary>Save a drug to medication history</summary>
    [HttpPost]
    [ProducesResponseType(typeof(ApiResponse<MedicationRecordDto>), 200)]
    public async Task<IActionResult> SaveMedication([FromBody] SaveMedicationRequest request)
    {
        var userId = User.FindFirstValue(ClaimTypes.NameIdentifier)!;
        var result = await _medicationService.SaveMedicationAsync(userId, request);
        return Ok(ApiResponse<MedicationRecordDto>.Ok(result, "Medication saved successfully."));
    }

    /// <summary>Get user's medication history with pagination</summary>
    [HttpGet("history")]
    [ProducesResponseType(typeof(ApiResponse<MedicationHistoryDto>), 200)]
    public async Task<IActionResult> GetHistory(
        [FromQuery] int page = 1,
        [FromQuery] int pageSize = 20)
    {
        if (page < 1) page = 1;
        if (pageSize < 1 || pageSize > 50) pageSize = 20;

        var userId = User.FindFirstValue(ClaimTypes.NameIdentifier)!;
        var result = await _medicationService.GetHistoryAsync(userId, page, pageSize);
        return Ok(ApiResponse<MedicationHistoryDto>.Ok(result));
    }

    /// <summary>Get a single medication record by ID</summary>
    [HttpGet("{id:guid}")]
    public async Task<IActionResult> GetById(Guid id)
    {
        var userId = User.FindFirstValue(ClaimTypes.NameIdentifier)!;
        var result = await _medicationService.GetByIdAsync(id, userId);
        if (result == null)
            return NotFound(ApiResponse<object>.Fail("Medication record not found."));
        return Ok(ApiResponse<MedicationRecordDto>.Ok(result));
    }

    /// <summary>Delete (soft delete) a medication record</summary>
    [HttpDelete("{id:guid}")]
    public async Task<IActionResult> Delete(Guid id)
    {
        var userId = User.FindFirstValue(ClaimTypes.NameIdentifier)!;
        await _medicationService.DeleteAsync(id, userId);
        return Ok(ApiResponse<object>.Ok(null!, "Medication record deleted."));
    }

    // ── Prescriptions ─────────────────────────────────────────

    /// <summary>
    /// Submit a prescription photo for OCR + GPT-4o analysis.
    /// Send image as multipart/form-data. Include drug names in 'notes' field
    /// (one per line) for manual entry, or let OCR handle it automatically.
    /// </summary>
    [HttpPost("prescription")]
    [RequestSizeLimit(10 * 1024 * 1024)]
    [ProducesResponseType(typeof(ApiResponse<PrescriptionAnalysisDto>), 200)]
    public async Task<IActionResult> AnalyzePrescription(
        [FromForm] SubmitPrescriptionRequest request,
        IFormFile? image)
    {
        var userId = User.FindFirstValue(ClaimTypes.NameIdentifier)!;

        Stream? imageStream = null;
        string contentType = "image/jpeg";

        if (image != null)
        {
            var allowedTypes = new[] { "image/jpeg", "image/png", "image/webp" };
            if (!allowedTypes.Contains(image.ContentType.ToLower()))
                return BadRequest(ApiResponse<object>.Fail("Only JPEG, PNG, and WebP images are allowed."));

            imageStream = image.OpenReadStream();
            contentType = image.ContentType;
        }

        await using var ownedImageStream = imageStream;
        var result = await _medicationService.AnalyzePrescriptionAsync(
            userId, request, imageStream ?? Stream.Null, contentType);

        return Ok(ApiResponse<PrescriptionAnalysisDto>.Ok(result, "Confirmed prescription record saved. Clinician verification remains required."));
    }

    /// <summary>Get all prescriptions for current user</summary>
    [HttpGet("prescriptions")]
    [ProducesResponseType(typeof(ApiResponse<List<PrescriptionSummaryDto>>), 200)]
    public async Task<IActionResult> GetPrescriptions()
    {
        var userId = User.FindFirstValue(ClaimTypes.NameIdentifier)!;
        var result = await _medicationService.GetPrescriptionsAsync(userId);
        return Ok(ApiResponse<List<PrescriptionSummaryDto>>.Ok(result));
    }

    /// <summary>Get a single prescription with full analysis</summary>
    [HttpGet("prescriptions/{id:guid}")]
    public async Task<IActionResult> GetPrescription(Guid id)
    {
        var userId = User.FindFirstValue(ClaimTypes.NameIdentifier)!;
        var result = await _medicationService.GetPrescriptionByIdAsync(id, userId);
        if (result == null)
            return NotFound(ApiResponse<object>.Fail("Prescription not found."));
        return Ok(ApiResponse<PrescriptionAnalysisDto>.Ok(result));
    }
}
