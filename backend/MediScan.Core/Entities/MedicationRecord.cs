namespace MediScan.Core.Entities;

public enum MedicationInputMethod
{
    BarcodeScanner,
    OcrScan,
    ManualEntry
}

public class MedicationRecord
{
    public Guid Id { get; set; } = Guid.NewGuid();
    public string UserId { get; set; } = string.Empty;

    public string DrugName { get; set; } = string.Empty;
    public string? GenericName { get; set; }
    public string? Manufacturer { get; set; }
    public string? Barcode { get; set; }
    public string? DosageForm { get; set; }       // Tablet, Syrup, Shampoo, etc.
    public string? Strength { get; set; }          // e.g. "500mg"
    public string? Indication { get; set; }        // What it treats
    public string? SideEffects { get; set; }       // JSON list
    public string? Warnings { get; set; }          // JSON list
    public string? DrugInteractions { get; set; }  // JSON list
    public string? AiAnalysis { get; set; }        // GPT-4o analysis of prescription
    public string? ImageUrl { get; set; }          // Prescription/box image

    public MedicationInputMethod InputMethod { get; set; }
    public bool IsPrescription { get; set; } = false;
    public string? PrescribedBy { get; set; }
    public DateTime? PrescribedDate { get; set; }

    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
    public bool IsDeleted { get; set; } = false;

    // Navigation
    public ApplicationUser? User { get; set; }
}
