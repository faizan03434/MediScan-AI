namespace MediScan.Core.Entities;

public enum PrescriptionStatus
{
    Active,
    Completed,
    Cancelled,
    Expired
}

/// <summary>
/// Stores an OCR-scanned or manually entered prescription.
/// One prescription can contain multiple medication items.
/// </summary>
public class PrescriptionRecord
{
    public Guid Id { get; set; } = Guid.NewGuid();
    public string UserId { get; set; } = string.Empty;

    public string? DoctorName { get; set; }
    public string? DoctorSpecialty { get; set; }
    public string? ClinicName { get; set; }
    public DateTime? PrescribedDate { get; set; }
    public DateTime? ExpiryDate { get; set; }
    public string? Diagnosis { get; set; }          // OCR extracted or manual
    public string? Notes { get; set; }
    public string? ImageUrl { get; set; }           // Azure Blob URL of prescription photo
    public string? ImageBlobName { get; set; }

    // OCR raw extracted text
    public string? OcrRawText { get; set; }

    // GPT-4o parsed output
    public string? AiParsedJson { get; set; }       // JSON: list of parsed medicines
    public string? AiAnalysis { get; set; }         // GPT-4o safety analysis text
    public bool HasSafetyWarnings { get; set; } = false;

    public PrescriptionStatus Status { get; set; } = PrescriptionStatus.Active;
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
    public bool IsDeleted { get; set; } = false;

    // Navigation
    public ApplicationUser? User { get; set; }
    public ICollection<MedicationRecord> Medications { get; set; } = new List<MedicationRecord>();
}
