namespace MediScan.Core.Entities;

public enum ConsentStatus
{
    Pending,
    Granted,
    Revoked
}

/// <summary>
/// Records a patient's consent for a specific doctor to view their scans.
/// HIPAA requirement: explicit written consent before any data sharing.
/// </summary>
public class PatientConsent
{
    public Guid Id { get; set; } = Guid.NewGuid();

    public string PatientUserId { get; set; } = string.Empty;
    public string DoctorUserId  { get; set; } = string.Empty;

    public ConsentStatus Status { get; set; } = ConsentStatus.Pending;

    /// <summary>Which scan types the doctor can access. Null = all types.</summary>
    public string? AllowedScanTypesJson { get; set; }

    public string? ConsentMessage { get; set; }   // Doctor's request message
    public string? PatientNote { get; set; }       // Patient's note when granting/revoking

    public DateTime RequestedAt { get; set; } = DateTime.UtcNow;
    public DateTime? RespondedAt { get; set; }
    public DateTime? ExpiresAt   { get; set; }     // Optional: consent can expire
    public DateTime? RevokedAt   { get; set; }

    public bool IsActive =>
        Status == ConsentStatus.Granted &&
        (ExpiresAt == null || ExpiresAt > DateTime.UtcNow) &&
        RevokedAt == null;

    // Navigation
    public ApplicationUser? Patient { get; set; }
    public ApplicationUser? Doctor  { get; set; }
}
