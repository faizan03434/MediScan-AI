using System.Security.Claims;
using MediScan.Core.DTOs.Common;
using MediScan.Core.Entities;
using MediScan.Core.Interfaces;
using MediScan.Infra.Data;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.RateLimiting;
using Microsoft.EntityFrameworkCore;

namespace MediScan.API.Controllers;

[ApiController, Authorize, Route("api/v1/account")]
[ResponseCache(NoStore = true, Location = ResponseCacheLocation.None)]
public sealed class AccountDataController(AppDbContext db, UserManager<ApplicationUser> users, IAuditService audit) : ControllerBase
{
    // Explicit projections prevent credentials, internal blob paths and navigation graphs entering exports.
    [HttpGet("export/{section}"), EnableRateLimiting("account-export")]
    public async Task<IActionResult> Export(string section, int page = 1, int pageSize = 100,
        CancellationToken cancellationToken = default)
    {
        var id = User.FindFirstValue(ClaimTypes.NameIdentifier);
        if (string.IsNullOrEmpty(id)) return Unauthorized();
        if (page < 1 || page > 100000 || pageSize < 1 || pageSize > 100)
            return BadRequest(ApiResponse<object>.Fail("Use page 1–100000 and page size 1–100."));
        Response.Headers.CacheControl = "private, no-store";
        IActionResult result = section switch {
            "profile" => await Page(db.Users.AsNoTracking().Where(u => u.Id == id).Select(u => new {
                u.FullName, u.Email, u.Gender, u.DateOfBirth, u.WeightKg, u.HeightCm, u.BloodGroup,
                u.MedicalHistory, u.Role, u.CreatedAt }), page, pageSize, cancellationToken),
            "scans" => await Page(db.ScanRecords.IgnoreQueryFilters().AsNoTracking().Where(s => s.UserId == id)
                .OrderBy(s => s.CreatedAt).ThenBy(s => s.Id).Select(s => new {
                    s.Id, s.ScanType, s.Status, s.DetectionResult, s.ConfidenceScore, s.DetectionDetails,
                    s.AiRecommendation, s.NextScanRecommendation, s.NextScanDate, s.CreatedAt, s.CompletedAt, s.IsDeleted }), page, pageSize, cancellationToken),
            "medications" => await Page(db.MedicationRecords.IgnoreQueryFilters().AsNoTracking().Where(m => m.UserId == id)
                .OrderBy(m => m.CreatedAt).ThenBy(m => m.Id).Select(m => new {
                    m.Id, m.DrugName, m.GenericName, m.Manufacturer, m.Barcode, m.DosageForm, m.Strength,
                    m.Indication, m.SideEffects, m.Warnings, m.DrugInteractions, m.Contraindications, m.StorageInfo,
                    m.AiAnalysis, m.HasSafetyWarning, m.InputMethod, m.IsPrescription, m.PrescribedBy, m.PrescribedDate,
                    m.PrescriptionRecordId, m.CreatedAt, m.IsDeleted }), page, pageSize, cancellationToken),
            "prescriptions" => await Page(db.PrescriptionRecords.IgnoreQueryFilters().AsNoTracking().Where(p => p.UserId == id)
                .OrderBy(p => p.CreatedAt).ThenBy(p => p.Id).Select(p => new {
                    p.Id, p.DoctorName, p.DoctorSpecialty, p.ClinicName, p.PrescribedDate, p.ExpiryDate,
                    p.Diagnosis, p.Notes, p.OcrRawText, p.AiParsedJson, p.AiAnalysis, p.HasSafetyWarnings,
                    p.Status, p.CreatedAt, p.IsDeleted }), page, pageSize, cancellationToken),
            "consents" => await Page(db.PatientConsents.AsNoTracking().Where(c => c.PatientUserId == id)
                .OrderBy(c => c.RequestedAt).ThenBy(c => c.Id).Select(c => new {
                    c.Id, c.DoctorUserId, c.Status, c.AllowedScanTypesJson, c.ConsentMessage, c.PatientNote,
                    c.RequestedAt, c.RespondedAt, c.ExpiresAt, c.RevokedAt }), page, pageSize, cancellationToken),
            _ => BadRequest(ApiResponse<object>.Fail("Choose profile, scans, medications, prescriptions or consents."))
        };
        if (result is OkObjectResult && page == 1)
            await audit.LogAsync("Account.Export", "Account", section, id);
        return result;
    }

    [HttpPost("sessions/revoke-all"), EnableRateLimiting("auth")]
    public async Task<IActionResult> RevokeAll(CancellationToken cancellationToken)
    {
        var id = User.FindFirstValue(ClaimTypes.NameIdentifier);
        var user = id == null ? null : await users.FindByIdAsync(id);
        if (user == null) return Unauthorized();
        await using var transaction = await db.Database.BeginTransactionAsync(cancellationToken);
        var result = await users.UpdateSecurityStampAsync(user);
        if (!result.Succeeded) throw new InvalidOperationException("Session invalidation failed.");
        foreach (var token in await db.RefreshTokens.Where(t => t.UserId == id && t.RevokedAt == null).ToListAsync(cancellationToken))
            token.RevokedAt = DateTime.UtcNow;
        await db.SaveChangesAsync(cancellationToken);
        await audit.LogAsync("Auth.RevokeAll", "User", id, id);
        await transaction.CommitAsync(cancellationToken);
        Response.Headers.CacheControl = "private, no-store";
        return Ok(ApiResponse<object>.Ok(null!, "Signed out of all devices. Sign in again."));
    }

    private async Task<IActionResult> Page<T>(IQueryable<T> query, int page, int size, CancellationToken ct)
    {
        var count = await query.CountAsync(ct);
        var items = await query.Skip((page - 1) * size).Take(size).ToListAsync(ct);
        return Ok(ApiResponse<PagedResponse<T>>.Ok(new() { Items = items, TotalCount = count, Page = page, PageSize = size }));
    }
}
