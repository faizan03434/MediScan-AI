using System.ComponentModel.DataAnnotations;

namespace MediScan.Core.DTOs.Medication;

/// <summary>Search by drug name (manual entry)</summary>
public class DrugSearchRequest
{
    [Required, MinLength(2)]
    public string Query { get; set; } = string.Empty;

    /// <summary>"PK" for Pakistan DAP first, "US" for OpenFDA first, null = try both</summary>
    public string? Country { get; set; }
}

/// <summary>Search by barcode (EAN-13, EAN-8, QR)</summary>
public class BarcodeSearchRequest
{
    [Required]
    public string Barcode { get; set; } = string.Empty;
}

/// <summary>Unified drug info response — same shape regardless of source</summary>
public class DrugInfoDto
{
    public string BrandName { get; set; } = string.Empty;
    public string? GenericName { get; set; }
    public string? Manufacturer { get; set; }
    public string? DosageForm { get; set; }
    public string? Strength { get; set; }
    public string? Indication { get; set; }
    public List<string> SideEffects { get; set; } = new();
    public List<string> Warnings { get; set; } = new();
    public List<string> Interactions { get; set; } = new();
    public List<string> Contraindications { get; set; } = new();
    public string? StorageInfo { get; set; }
    public string? Source { get; set; }             // "OpenFDA" | "PakistanDAP" | "Cache"
    public string? CountryOfOrigin { get; set; }
    public string? AiAnalysis { get; set; }         // GPT-4o enrichment (if enabled)
    public bool HasSafetyWarning { get; set; }
    public string Disclaimer { get; set; } =
        "This information is for reference only. Always consult your doctor or pharmacist before taking any medication.";
}

/// <summary>Save a searched/scanned drug to user's medication history</summary>
public class SaveMedicationRequest
{
    [Required]
    public string DrugName { get; set; } = string.Empty;
    public string? GenericName { get; set; }
    public string? Barcode { get; set; }
    public string? DosageForm { get; set; }
    public string? Strength { get; set; }
    public string InputMethod { get; set; } = "ManualEntry";
    public bool IsPrescription { get; set; } = false;
    public string? PrescribedBy { get; set; }
    public DateTime? PrescribedDate { get; set; }
    public Guid? PrescriptionRecordId { get; set; }
}

/// <summary>Medication record returned to client</summary>
public class MedicationRecordDto
{
    public Guid Id { get; set; }
    public string DrugName { get; set; } = string.Empty;
    public string? GenericName { get; set; }
    public string? Manufacturer { get; set; }
    public string? DosageForm { get; set; }
    public string? Strength { get; set; }
    public string? Indication { get; set; }
    public List<string> SideEffects { get; set; } = new();
    public List<string> Warnings { get; set; } = new();
    public string? AiAnalysis { get; set; }
    public bool HasSafetyWarning { get; set; }
    public string? ImageUrl { get; set; }
    public string InputMethod { get; set; } = string.Empty;
    public bool IsPrescription { get; set; }
    public string? PrescribedBy { get; set; }
    public DateTime? PrescribedDate { get; set; }
    public DateTime CreatedAt { get; set; }
}

public class MedicationHistoryDto
{
    public List<MedicationRecordDto> Items { get; set; } = new();
    public int TotalCount { get; set; }
    public int Page { get; set; }
    public int PageSize { get; set; }
}
