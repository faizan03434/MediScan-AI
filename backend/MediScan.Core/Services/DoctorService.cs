using System.Text.Json;
using MediScan.Core.DTOs.Doctor;
using MediScan.Core.DTOs.Scan;
using MediScan.Core.Entities;
using MediScan.Core.Interfaces;
using Microsoft.AspNetCore.Identity;
using Microsoft.EntityFrameworkCore;

namespace MediScan.Core.Services;

public class DoctorService : IDoctorService
{
    private readonly IAppDbContext _db;
    private readonly UserManager<ApplicationUser> _userManager;
    private readonly IAuditService _audit;

    public DoctorService(
        IAppDbContext db,
        UserManager<ApplicationUser> userManager,
        IAuditService audit)
    {
        _db = db;
        _userManager = userManager;
        _audit = audit;
    }

    // ── Request consent ───────────────────────────────────────
    public async Task<ConsentSummaryDto> RequestConsentAsync(string doctorUserId, RequestConsentDto dto)
    {
        var doctor = await _userManager.FindByIdAsync(doctorUserId)
            ?? throw new KeyNotFoundException("Doctor not found.");

        if (doctor.Role != "Doctor")
            throw new UnauthorizedAccessException("Only users with Doctor role can request patient access.");

        var patient = await _userManager.FindByEmailAsync(dto.PatientEmail)
            ?? throw new KeyNotFoundException($"No patient found with email: {dto.PatientEmail}");

        if (patient.Id == doctorUserId)
            throw new ArgumentException("A doctor cannot request consent from themselves.");

        // Check for existing active/pending consent
        var existing = await _db.PatientConsents
            .FirstOrDefaultAsync(c =>
                c.DoctorUserId == doctorUserId &&
                c.PatientUserId == patient.Id &&
                (c.Status == ConsentStatus.Pending || c.Status == ConsentStatus.Granted));

        if (existing != null)
            throw new InvalidOperationException(
                existing.Status == ConsentStatus.Pending
                    ? "A consent request is already pending for this patient."
                    : "You already have active consent from this patient.");

        var consent = new PatientConsent
        {
            DoctorUserId    = doctorUserId,
            PatientUserId   = patient.Id,
            Status          = ConsentStatus.Pending,
            ConsentMessage  = dto.Message,
            AllowedScanTypesJson = dto.ScanTypes?.Count > 0
                ? JsonSerializer.Serialize(dto.ScanTypes) : null,
            ExpiresAt       = dto.ExpiryDays.HasValue
                ? DateTime.UtcNow.AddDays(dto.ExpiryDays.Value) : null,
            RequestedAt     = DateTime.UtcNow,
        };

        _db.PatientConsents.Add(consent);
        await _db.SaveChangesAsync();

        await _audit.LogAsync("Doctor.RequestConsent", "PatientConsent",
            consent.Id.ToString(), doctorUserId,
            newValues: $"patientId={patient.Id}");

        return MapToDto(consent, patient, doctor);
    }

    // ── Respond to consent ────────────────────────────────────
    public async Task<ConsentSummaryDto> RespondToConsentAsync(
        string patientUserId, Guid consentId, RespondConsentDto dto)
    {
        var consent = await _db.PatientConsents
            .FirstOrDefaultAsync(c => c.Id == consentId && c.PatientUserId == patientUserId)
            ?? throw new KeyNotFoundException("Consent request not found.");

        if (consent.Status != ConsentStatus.Pending)
            throw new InvalidOperationException("This consent request has already been responded to.");

        consent.Status      = dto.Grant ? ConsentStatus.Granted : ConsentStatus.Revoked;
        consent.PatientNote = dto.Note;
        consent.RespondedAt = DateTime.UtcNow;

        if (!dto.Grant)
            consent.RevokedAt = DateTime.UtcNow;

        await _db.SaveChangesAsync();

        var patient = await _userManager.FindByIdAsync(patientUserId)!;
        var doctor  = await _userManager.FindByIdAsync(consent.DoctorUserId)!;

        await _audit.LogAsync(
            dto.Grant ? "Patient.GrantConsent" : "Patient.DenyConsent",
            "PatientConsent", consentId.ToString(), patientUserId);

        return MapToDto(consent, patient!, doctor!);
    }

    // ── Revoke consent ────────────────────────────────────────
    public async Task RevokeConsentAsync(string patientUserId, Guid consentId)
    {
        var consent = await _db.PatientConsents
            .FirstOrDefaultAsync(c => c.Id == consentId && c.PatientUserId == patientUserId)
            ?? throw new KeyNotFoundException("Consent not found.");

        if (consent.Status != ConsentStatus.Granted)
            throw new InvalidOperationException("Only active consents can be revoked.");

        consent.Status    = ConsentStatus.Revoked;
        consent.RevokedAt = DateTime.UtcNow;
        await _db.SaveChangesAsync();

        await _audit.LogAsync("Patient.RevokeConsent", "PatientConsent",
            consentId.ToString(), patientUserId);
    }

    // ── Get doctor's consents ─────────────────────────────────
    public async Task<List<ConsentSummaryDto>> GetDoctorConsentsAsync(string doctorUserId)
    {
        var consents = await _db.PatientConsents
            .Include(c => c.Patient)
            .Include(c => c.Doctor)
            .Where(c => c.DoctorUserId == doctorUserId)
            .OrderByDescending(c => c.RequestedAt)
            .ToListAsync();

        return consents.Select(c => MapToDto(c, c.Patient!, c.Doctor!)).ToList();
    }

    // ── Get patient's consents ────────────────────────────────
    public async Task<List<ConsentSummaryDto>> GetPatientConsentsAsync(string patientUserId)
    {
        var consents = await _db.PatientConsents
            .Include(c => c.Patient)
            .Include(c => c.Doctor)
            .Where(c => c.PatientUserId == patientUserId)
            .OrderByDescending(c => c.RequestedAt)
            .ToListAsync();

        return consents.Select(c => MapToDto(c, c.Patient!, c.Doctor!)).ToList();
    }

    // ── My patients ───────────────────────────────────────────
    public async Task<List<PatientSummaryDto>> GetMyPatientsAsync(string doctorUserId)
    {
        var activeConsents = await _db.PatientConsents
            .Include(c => c.Patient)
            .Where(c =>
                c.DoctorUserId == doctorUserId &&
                c.Status == ConsentStatus.Granted &&
                c.RevokedAt == null &&
                (c.ExpiresAt == null || c.ExpiresAt > DateTime.UtcNow))
            .ToListAsync();

        var result = new List<PatientSummaryDto>();
        foreach (var consent in activeConsents)
        {
            var patient = consent.Patient!;
            var lastScan = await _db.ScanRecords
                .Where(s => s.UserId == patient.Id)
                .OrderByDescending(s => s.CreatedAt)
                .FirstOrDefaultAsync();

            var totalScans = await _db.ScanRecords
                .CountAsync(s => s.UserId == patient.Id);

            var age = patient.DateOfBirth.HasValue
                ? (int)((DateTime.UtcNow - patient.DateOfBirth.Value).TotalDays / 365.25)
                : (int?)null;

            List<string> allowedTypes = new();
            if (!string.IsNullOrEmpty(consent.AllowedScanTypesJson))
            {
                try { allowedTypes = JsonSerializer.Deserialize<List<string>>(consent.AllowedScanTypesJson) ?? new(); }
                catch { }
            }

            result.Add(new PatientSummaryDto
            {
                UserId          = patient.Id,
                FullName        = patient.FullName,
                Email           = patient.Email!,
                Gender          = patient.Gender,
                AgeYears        = age,
                BloodGroup      = patient.BloodGroup,
                TotalScans      = totalScans,
                LastScanResult  = lastScan?.DetectionResult,
                LastScanDate    = lastScan?.CreatedAt,
                AllowedScanTypes = allowedTypes,
                ConsentGrantedAt = consent.RespondedAt ?? consent.RequestedAt,
                ConsentExpiresAt = consent.ExpiresAt,
            });
        }

        return result;
    }

    // ── Get patient scans (doctor view) ───────────────────────
    public async Task<ScanHistoryDto> GetPatientScansAsync(
        string doctorUserId, string patientUserId, int page = 1, int pageSize = 10)
    {
        await VerifyConsentAsync(doctorUserId, patientUserId);

        var query = _db.ScanRecords.Where(s => s.UserId == patientUserId);
        var total = await query.CountAsync();
        var scans = await query
            .OrderByDescending(s => s.CreatedAt)
            .Skip((page - 1) * pageSize)
            .Take(pageSize)
            .ToListAsync();

        return new ScanHistoryDto
        {
            Scans      = scans.Select(MapScanToDto).ToList(),
            TotalCount = total,
            Page       = page,
            PageSize   = pageSize,
        };
    }

    // ── Get single patient scan ───────────────────────────────
    public async Task<ScanResultDto?> GetPatientScanAsync(
        string doctorUserId, string patientUserId, Guid scanId)
    {
        await VerifyConsentAsync(doctorUserId, patientUserId);
        var scan = await _db.ScanRecords
            .FirstOrDefaultAsync(s => s.Id == scanId && s.UserId == patientUserId);
        return scan == null ? null : MapScanToDto(scan);
    }

    // ── Helpers ───────────────────────────────────────────────
    private async Task VerifyConsentAsync(string doctorUserId, string patientUserId)
    {
        var consent = await _db.PatientConsents
            .FirstOrDefaultAsync(c =>
                c.DoctorUserId  == doctorUserId &&
                c.PatientUserId == patientUserId &&
                c.Status == ConsentStatus.Granted &&
                c.RevokedAt == null &&
                (c.ExpiresAt == null || c.ExpiresAt > DateTime.UtcNow));

        if (consent == null)
            throw new UnauthorizedAccessException(
                "No active patient consent found. The patient must grant access first.");

        await _audit.LogAsync("Doctor.ViewPatientData", "PatientConsent",
            consent.Id.ToString(), doctorUserId,
            newValues: $"patientId={patientUserId}");
    }

    private static ConsentSummaryDto MapToDto(
        PatientConsent c, ApplicationUser patient, ApplicationUser doctor) => new()
    {
        Id             = c.Id,
        PatientUserId  = c.PatientUserId,
        PatientName    = patient.FullName,
        PatientEmail   = patient.Email ?? "",
        DoctorUserId   = c.DoctorUserId,
        DoctorName     = doctor.FullName,
        DoctorEmail    = doctor.Email ?? "",
        Status         = c.Status.ToString(),
        IsActive       = c.IsActive,
        AllowedScanTypes = c.AllowedScanTypesJson,
        ConsentMessage = c.ConsentMessage,
        RequestedAt    = c.RequestedAt,
        RespondedAt    = c.RespondedAt,
        ExpiresAt      = c.ExpiresAt,
    };

    private static ScanResultDto MapScanToDto(ScanRecord s) => new()
    {
        Id                    = s.Id,
        ScanType              = s.ScanType,
        Status                = s.Status,
        ImageUrl              = s.ImageUrl,
        DetectionResult       = s.DetectionResult,
        ConfidenceScore       = s.ConfidenceScore,
        DetectionDetails      = s.DetectionDetails,
        AiRecommendation      = s.AiRecommendation,
        NextScanRecommendation = s.NextScanRecommendation,
        NextScanDate          = s.NextScanDate,
        CreatedAt             = s.CreatedAt,
        CompletedAt           = s.CompletedAt,
    };
}
