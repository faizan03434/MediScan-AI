using System.ComponentModel.DataAnnotations;

namespace MediScan.Core.DTOs.Doctor;

// ── Consent DTOs ──────────────────────────────────────────────

/// <summary>Doctor sends this to request access to a patient's data.</summary>
public class RequestConsentDto
{
    [Required, EmailAddress]
    public string PatientEmail { get; set; } = string.Empty;

    [MaxLength(500)]
    public string? Message { get; set; }

    /// <summary>e.g. ["Anemia","EyeDisease"] — null means all scan types</summary>
    public List<string>? ScanTypes { get; set; }

    /// <summary>Days until this consent expires. Null = no expiry.</summary>
    public int? ExpiryDays { get; set; }
}

/// <summary>Patient responds to a consent request.</summary>
public class RespondConsentDto
{
    [Required]
    public bool Grant { get; set; }

    [MaxLength(300)]
    public string? Note { get; set; }
}

public class ConsentSummaryDto
{
    public Guid Id { get; set; }
    public string PatientUserId { get; set; } = string.Empty;
    public string PatientName  { get; set; } = string.Empty;
    public string PatientEmail { get; set; } = string.Empty;
    public string DoctorUserId { get; set; } = string.Empty;
    public string DoctorName   { get; set; } = string.Empty;
    public string DoctorEmail  { get; set; } = string.Empty;
    public string Status       { get; set; } = string.Empty;
    public bool   IsActive     { get; set; }
    public string? AllowedScanTypes { get; set; }
    public string? ConsentMessage   { get; set; }
    public DateTime RequestedAt  { get; set; }
    public DateTime? RespondedAt { get; set; }
    public DateTime? ExpiresAt   { get; set; }
}

// ── Patient scan view ─────────────────────────────────────────

public class PatientSummaryDto
{
    public string UserId   { get; set; } = string.Empty;
    public string FullName { get; set; } = string.Empty;
    public string Email    { get; set; } = string.Empty;
    public string? Gender  { get; set; }
    public int?   AgeYears { get; set; }
    public string? BloodGroup { get; set; }
    public int    TotalScans { get; set; }
    public string? LastScanResult { get; set; }
    public DateTime? LastScanDate { get; set; }
    public List<string> AllowedScanTypes { get; set; } = new();
    public DateTime ConsentGrantedAt { get; set; }
    public DateTime? ConsentExpiresAt { get; set; }
}
