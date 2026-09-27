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

    // ── Drug Info ─────────────────────────────────────────────
    public string DrugName { get; set; } = string.Empty;
    public string? GenericName { get; set; }
    public string? Manufacturer { get; set; }
    public string? Barcode { get; set; }
    public string? DosageForm { get; set; }         // Tablet, Syrup, Shampoo, Injection
    public string? Strength { get; set; }            // e.g. "500mg", "250mg/5ml"
    public string? Indication { get; set; }          // What it treats
    public string? SideEffects { get; set; }         // JSON array string
    public string? Warnings { get; set; }            // JSON array string
    public string? DrugInteractions { get; set; }    // JSON array string
    public string? Contraindications { get; set; }
    public string? StorageInfo { get; set; }

    // ── AI Analysis ───────────────────────────────────────────
    public string? AiAnalysis { get; set; }          // GPT-4o safety analysis
    public bool HasSafetyWarning { get; set; } = false;

    // ── Image / Scan ──────────────────────────────────────────
    public string? ImageUrl { get; set; }
    public string? ImageBlobName { get; set; }

    // ── Input metadata ────────────────────────────────────────
    public MedicationInputMethod InputMethod { get; set; }
    public bool IsPrescription { get; set; } = false;
    public string? PrescribedBy { get; set; }
    public DateTime? PrescribedDate { get; set; }

    // ── Prescription FK (optional) ────────────────────────────
    public Guid? PrescriptionRecordId { get; set; }
    public PrescriptionRecord? PrescriptionRecord { get; set; }

    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
    public bool IsDeleted { get; set; } = false;

    // Navigation
    public ApplicationUser? User { get; set; }
}
