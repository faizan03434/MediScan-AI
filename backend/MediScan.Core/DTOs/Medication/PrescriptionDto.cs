namespace MediScan.Core.DTOs.Medication;

/// <summary>Request to submit a prescription image for OCR + GPT-4o analysis</summary>
public class SubmitPrescriptionRequest
{
    public string? DoctorName { get; set; }
    public string? DoctorSpecialty { get; set; }
    public string? ClinicName { get; set; }
    public DateTime? PrescribedDate { get; set; }
    public string? Notes { get; set; }
    // Image comes as IFormFile in controller
}

/// <summary>Parsed drug item extracted from prescription by GPT-4o</summary>
public class ParsedPrescriptionDrug
{
    public string DrugName { get; set; } = string.Empty;
    public string? DosageForm { get; set; }
    public string? Strength { get; set; }
    public string? Frequency { get; set; }    // e.g. "3x daily after meals"
    public string? Duration { get; set; }     // e.g. "7 days"
    public string? Instructions { get; set; }
    public bool IsKnownDrug { get; set; }     // Whether we found it in OpenFDA/DAP
    public DrugInfoDto? DrugInfo { get; set; }
}

/// <summary>Full prescription analysis result</summary>
public class PrescriptionAnalysisDto
{
    public Guid Id { get; set; }
    public string? DoctorName { get; set; }
    public string? Diagnosis { get; set; }
    public DateTime? PrescribedDate { get; set; }
    public string? ImageUrl { get; set; }

    public List<ParsedPrescriptionDrug> Medications { get; set; } = new();
    public string? AiAnalysis { get; set; }         // Overall safety summary
    public bool HasSafetyWarnings { get; set; }
    public List<string> Warnings { get; set; } = new();
    public List<string> Interactions { get; set; } = new(); // Drug-drug interactions found

    public string OcrRawText { get; set; } = string.Empty;
    public DateTime CreatedAt { get; set; }

    public string Disclaimer { get; set; } =
        "This AI analysis is for informational purposes only. Always follow your doctor's instructions. Consult a pharmacist if you have concerns about your medications.";
}

/// <summary>Prescription list item for history view</summary>
public class PrescriptionSummaryDto
{
    public Guid Id { get; set; }
    public string? DoctorName { get; set; }
    public string? Diagnosis { get; set; }
    public int MedicationCount { get; set; }
    public bool HasSafetyWarnings { get; set; }
    public string? ImageUrl { get; set; }
    public DateTime CreatedAt { get; set; }
    public string Status { get; set; } = "Active";
}
