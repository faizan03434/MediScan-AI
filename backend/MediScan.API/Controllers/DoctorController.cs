using MediScan.Core.DTOs.Common;
using MediScan.Core.DTOs.Doctor;
using MediScan.Core.DTOs.Scan;
using MediScan.Core.Interfaces;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using System.Security.Claims;

namespace MediScan.API.Controllers;

/// <summary>
/// Doctor role endpoints — requires Role = "Doctor" or "Admin".
///
/// Flow:
///   1. Doctor calls POST /doctor/consent/request  → sends request to patient
///   2. Patient calls POST /doctor/consent/{id}/respond → grants or denies
///   3. Doctor calls GET  /doctor/patients          → sees their patients
///   4. Doctor calls GET  /doctor/patients/{id}/scans → views patient scans
/// </summary>
[ApiController]
[Route("api/v1/[controller]")]
[Authorize]
[Produces("application/json")]
public class DoctorController : ControllerBase
{
    private readonly IDoctorService _doctorService;

    public DoctorController(IDoctorService doctorService)
    {
        _doctorService = doctorService;
    }

    private string UserId => User.FindFirstValue(ClaimTypes.NameIdentifier)!;
    private string UserRole => User.FindFirstValue(ClaimTypes.Role) ?? "User";

    // ── Consent: Doctor actions ───────────────────────────────

    /// <summary>
    /// Doctor requests access to a patient's scan data.
    /// Patient will receive a notification to accept/deny.
    /// </summary>
    [HttpPost("consent/request")]
    [Authorize(Roles = "Doctor,Admin")]
    [ProducesResponseType(typeof(ApiResponse<ConsentSummaryDto>), 200)]
    public async Task<IActionResult> RequestConsent([FromBody] RequestConsentDto dto)
    {
        var result = await _doctorService.RequestConsentAsync(UserId, dto);
        return Ok(ApiResponse<ConsentSummaryDto>.Ok(result,
            "Consent request sent. The patient will be notified."));
    }

    /// <summary>Get all consent requests this doctor has sent (and their status).</summary>
    [HttpGet("consent/sent")]
    [Authorize(Roles = "Doctor,Admin")]
    [ProducesResponseType(typeof(ApiResponse<List<ConsentSummaryDto>>), 200)]
    public async Task<IActionResult> GetSentConsents()
    {
        var result = await _doctorService.GetDoctorConsentsAsync(UserId);
        return Ok(ApiResponse<List<ConsentSummaryDto>>.Ok(result));
    }

    // ── Consent: Patient actions ──────────────────────────────

    /// <summary>Get all consent requests this patient has received from doctors.</summary>
    [HttpGet("consent/received")]
    [ProducesResponseType(typeof(ApiResponse<List<ConsentSummaryDto>>), 200)]
    public async Task<IActionResult> GetReceivedConsents()
    {
        var result = await _doctorService.GetPatientConsentsAsync(UserId);
        return Ok(ApiResponse<List<ConsentSummaryDto>>.Ok(result));
    }

    /// <summary>
    /// Patient responds to a doctor's consent request.
    /// Set Grant = true to allow, false to deny.
    /// </summary>
    [HttpPost("consent/{consentId:guid}/respond")]
    [ProducesResponseType(typeof(ApiResponse<ConsentSummaryDto>), 200)]
    public async Task<IActionResult> RespondToConsent(
        Guid consentId, [FromBody] RespondConsentDto dto)
    {
        var result = await _doctorService.RespondToConsentAsync(UserId, consentId, dto);
        var msg = dto.Grant
            ? "Consent granted. The doctor can now view your scan history."
            : "Consent denied. The doctor will not have access to your data.";
        return Ok(ApiResponse<ConsentSummaryDto>.Ok(result, msg));
    }

    /// <summary>Patient revokes a previously granted consent.</summary>
    [HttpDelete("consent/{consentId:guid}")]
    public async Task<IActionResult> RevokeConsent(Guid consentId)
    {
        await _doctorService.RevokeConsentAsync(UserId, consentId);
        return Ok(ApiResponse<object>.Ok(null!, "Consent revoked. The doctor can no longer access your data."));
    }

    // ── Doctor: Patient data ──────────────────────────────────

    /// <summary>Get list of patients who have granted active consent to this doctor.</summary>
    [HttpGet("patients")]
    [Authorize(Roles = "Doctor,Admin")]
    [ProducesResponseType(typeof(ApiResponse<List<PatientSummaryDto>>), 200)]
    public async Task<IActionResult> GetMyPatients()
    {
        var result = await _doctorService.GetMyPatientsAsync(UserId);
        return Ok(ApiResponse<List<PatientSummaryDto>>.Ok(result));
    }

    /// <summary>
    /// Get scan history for a specific patient.
    /// Requires active consent from the patient.
    /// </summary>
    [HttpGet("patients/{patientId}/scans")]
    [Authorize(Roles = "Doctor,Admin")]
    [ProducesResponseType(typeof(ApiResponse<ScanHistoryDto>), 200)]
    [ProducesResponseType(typeof(ApiResponse<object>), 403)]
    public async Task<IActionResult> GetPatientScans(
        string patientId,
        [FromQuery] int page = 1,
        [FromQuery] int pageSize = 10)
    {
        if (page < 1) page = 1;
        if (pageSize < 1 || pageSize > 20) pageSize = 10;

        var result = await _doctorService.GetPatientScansAsync(UserId, patientId, page, pageSize);
        return Ok(ApiResponse<ScanHistoryDto>.Ok(result));
    }

    /// <summary>Get a specific scan for a patient. Requires active consent.</summary>
    [HttpGet("patients/{patientId}/scans/{scanId:guid}")]
    [Authorize(Roles = "Doctor,Admin")]
    [ProducesResponseType(typeof(ApiResponse<ScanResultDto>), 200)]
    public async Task<IActionResult> GetPatientScan(string patientId, Guid scanId)
    {
        var result = await _doctorService.GetPatientScanAsync(UserId, patientId, scanId);
        if (result == null)
            return NotFound(ApiResponse<object>.Fail("Scan not found."));
        return Ok(ApiResponse<ScanResultDto>.Ok(result));
    }
}
